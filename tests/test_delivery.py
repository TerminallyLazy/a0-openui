import asyncio
import copy
import json
import smtplib
import threading
from types import SimpleNamespace

import pytest
from usr.plugins.openui.helpers import delivery, mail_html, mailbox

CONFIG = {'username': 'owner@example.test', 'password': 'synthetic-secret', 'smtp_server': 'smtp.example.test', 'smtp_port': 587}


@pytest.fixture
def setup(monkeypatch, tmp_path):
    agent = SimpleNamespace(context=SimpleNamespace(id='chat'), number=0, config=SimpleNamespace(profile='default'))
    artifact = {'id': 'draft', 'revision': 1, 'source': 'synthetic program'}
    data = {'revision': 1, 'account': 'account', 'to': 'Person <person@example.test>', 'cc': '', 'bcc': 'hidden@example.test', 'subject': 'Hello', 'html': '<h1 style="color:#123456">Hello</h1><p>Rich mail <a href="https://example.test/">link</a></p>'}
    monkeypatch.setattr(delivery, 'directory', lambda: tmp_path)
    monkeypatch.setattr(mailbox, 'configuration', lambda *args: copy.deepcopy(CONFIG))
    monkeypatch.setattr(delivery.artifacts, 'mask', lambda context, value: value)
    delivery.PENDING.clear()
    return agent, artifact, data


def test_html_preserves_email_layout_but_removes_active_content_and_tracking_css():
    result = mail_html.sanitize('''<head><meta http-equiv="refresh" content="0;url=https://evil.test"></head>
      <table cellpadding="10"><tr><td style="color:#123456;padding:16px;background:url(https://evil.test)">
      <b>Hello</b><script>secret()</script><img src="https://example.test/image.png" onerror="alert(1)">
      <a href="javascript:alert(1)" onclick="alert(1)">Unsafe</a><a href="https://example.test/">Safe</a>
      <svg><a href="evil">svg</a></svg><form><input></form></td></tr></table>''')
    assert '<table cellpadding="10">' in result and 'color:#123456;padding:16px' in result
    for bad in ['javascript:', 'onclick', 'onerror', 'secret()', '<svg', '<form', 'url(', 'evil.test']:
        assert bad not in result
    assert 'noopener noreferrer' in result and 'https://example.test/image.png' in result


@pytest.mark.parametrize('field,value', [('to','alice@example.test\nBcc: hidden@example.test'), ('to','missing-domain'), ('to','a@example.test,,b@example.test'), ('subject','Injected\r\nX-Header: bad'), ('to','')])
def test_header_injection_and_bad_recipients_are_rejected(setup, field, value):
    agent, artifact, data = setup
    data[field] = value
    with pytest.raises(ValueError): delivery.prepare(agent, artifact, data)


def test_review_is_frozen_and_recipient_lists_are_explicit(setup):
    agent, artifact, data = setup
    review = delivery.prepare(agent, artifact, data)
    assert review['from'] == 'owner@example.test'
    assert review['to'] == ['person@example.test'] and review['bcc'] == ['hidden@example.test']
    assert 'Rich mail' in review['text'] and '(https://example.test/)' in review['text']
    data['to'] = 'changed@example.test'
    assert delivery.PENDING[review['token']]['to'] == ['person@example.test']
    assert 'synthetic-secret' not in json.dumps(review)


def test_expired_changed_profile_or_revision_review_cannot_send(setup, monkeypatch):
    agent, artifact, data = setup
    review = delivery.prepare(agent, artifact, data)
    def unexpected(*a): raise AssertionError('SMTP must not run')
    monkeypatch.setattr(delivery, 'smtp_send', unexpected)
    for key, value in [('revision', 2), ('source', 'changed')]:
        changed = {**artifact, key: value}
        with pytest.raises(PermissionError): asyncio.run(delivery.send(agent, changed, review['token']))
    agent.config.profile = 'other'
    with pytest.raises(PermissionError): asyncio.run(delivery.send(agent, artifact, review['token']))
    agent.config.profile = 'default'
    delivery.PENDING[review['token']]['expires'] = 0
    with pytest.raises(ValueError, match='expired'): asyncio.run(delivery.send(agent, artifact, review['token']))


def test_reconfigured_or_revoked_account_cannot_send(setup, monkeypatch):
    agent, artifact, data = setup
    review = delivery.prepare(agent, artifact, data)
    monkeypatch.setattr(mailbox, 'configuration', lambda *args: {**CONFIG, 'smtp_server':'different.test'})
    with pytest.raises(ValueError, match='account changed'): asyncio.run(delivery.send(agent, artifact, review['token']))
    def denied(*args): raise PermissionError('disabled')
    monkeypatch.setattr(mailbox, 'configuration', denied)
    with pytest.raises(PermissionError): asyncio.run(delivery.send(agent, artifact, review['token']))


def test_concurrent_clicks_and_restart_do_not_resend(setup, monkeypatch):
    agent, artifact, data = setup
    review = delivery.prepare(agent, artifact, data)
    entered, release = threading.Event(), threading.Event()
    calls = []
    def smtp(config, prepared):
        calls.append(prepared)
        assert delivery.receipt_path(agent.context, artifact).exists()
        entered.set();assert release.wait(5)
        return {'status':'sent', 'accepted':prepared['to']+prepared['bcc'], 'refused':[]}
    monkeypatch.setattr(delivery, 'smtp_send', smtp)
    async def attempt():
        first = asyncio.create_task(delivery.send(agent, artifact, review['token']))
        await asyncio.to_thread(entered.wait, 5)
        second = await delivery.send(agent, artifact, review['token'])
        assert second['status'] == 'sending'
        release.set()
        return await first
    assert asyncio.run(attempt())['status'] == 'sent'
    delivery.PENDING.clear()
    assert asyncio.run(delivery.send(agent, artifact, review['token']))['status'] == 'sent'
    with pytest.raises(ValueError, match='already has a send attempt'): delivery.prepare(agent, artifact, data)
    assert len(calls) == 1
    assert delivery.receipt_path(agent.context, artifact).stat().st_mode & 0o777 == 0o600


def test_unsaved_claim_never_sends(setup, monkeypatch):
    agent, artifact, data = setup
    review = delivery.prepare(agent, artifact, data)
    bad = delivery.directory() / 'not-a-directory';bad.write_text('x')
    monkeypatch.setattr(delivery, 'directory', lambda: bad)
    monkeypatch.setattr(delivery, 'smtp_send', lambda *a: pytest.fail('must not send'))
    with pytest.raises(OSError): asyncio.run(delivery.send(agent, artifact, review['token']))


class FakeSMTP:
    calls = []
    failure = None
    refused = {}
    def __init__(self, host, port, **kwargs): self.calls.append(('connect',host,port,kwargs))
    def ehlo(self): self.calls.append(('ehlo',))
    def starttls(self, **kwargs): self.calls.append(('tls',kwargs))
    def login(self, username, password): self.calls.append(('login',username))
    def send_message(self, message, **kwargs):
        self.calls.append(('send',message,kwargs))
        if self.failure: raise self.failure
        return self.refused
    def quit(self): raise OSError('quit failed after acceptance')
    def close(self): pass


def smtp_fixture(setup, monkeypatch):
    agent, artifact, data = setup
    prepared = delivery.prepare(agent, artifact, data)
    prepared['message_id'] = '<synthetic@example.test>'
    FakeSMTP.calls=[];FakeSMTP.failure=None;FakeSMTP.refused={}
    monkeypatch.setattr(delivery.smtplib, 'SMTP', FakeSMTP)
    monkeypatch.setattr(delivery.smtplib, 'SMTP_SSL', FakeSMTP)
    return prepared


def test_smtp_sends_multipart_with_tls_and_envelope_only_bcc(setup, monkeypatch):
    prepared = smtp_fixture(setup, monkeypatch)
    result = delivery.smtp_send(CONFIG, prepared)
    assert result['status'] == 'sent'
    assert [c[0] for c in FakeSMTP.calls] == ['connect','ehlo','tls','ehlo','login','send']
    context = FakeSMTP.calls[2][1]['context']
    assert context.check_hostname
    _, msg, kwargs = FakeSMTP.calls[-1]
    assert msg.get_content_type() == 'multipart/alternative'
    assert msg.get_body(preferencelist=('html',)).get_content().strip() == prepared['html']
    assert 'Bcc' not in msg and kwargs['to_addrs'] == ['person@example.test','hidden@example.test']
    assert msg['From'] == 'owner@example.test'
    assert msg.get_body(preferencelist=('plain',)).get_content().strip() == prepared['text']


def test_smtp_465_uses_tls_from_connection(setup, monkeypatch):
    prepared = smtp_fixture(setup, monkeypatch)
    assert delivery.smtp_send({**CONFIG,'smtp_port':465}, prepared)['status'] == 'sent'
    assert 'context' in FakeSMTP.calls[0][3]
    assert 'tls' not in [c[0] for c in FakeSMTP.calls]


def test_partial_and_ambiguous_send_never_claim_full_success(setup, monkeypatch):
    prepared = smtp_fixture(setup, monkeypatch)
    FakeSMTP.refused={'hidden@example.test':(550,b'refused')}
    result = delivery.smtp_send(CONFIG, prepared)
    assert result['status']=='partial' and result['accepted']==['person@example.test']
    FakeSMTP.failure=TimeoutError('synthetic-secret echoed')
    result = delivery.smtp_send(CONFIG, prepared)
    assert result['status']=='unknown' and 'synthetic-secret' not in str(result)
    FakeSMTP.failure=smtplib.SMTPRecipientsRefused({'person@example.test':(550,b'refused')})
    assert delivery.smtp_send(CONFIG, prepared)['status']=='failed'
