"""Human-reviewed rich mail, using the existing integration's SMTP credentials.

Preparation is transient. A private durable receipt is claimed before SMTP, so
retries, restarts and chat time travel cannot re-send an artifact automatically.
No delivery operation is exposed by the agent's openui_mail tool.
"""
import asyncio
import copy
import hashlib
import json
import os
from pathlib import Path
import re
import secrets
import smtplib
import ssl
import threading
import time
from email.message import EmailMessage
from email.policy import default
from email.utils import formatdate, make_msgid

from helpers import files
from usr.plugins.openui.helpers import artifacts, mailbox, mail_html

LOCK = threading.RLock()
PENDING = {}
TTL = 600


def directory():
    return Path(files.get_abs_path('usr/openui/deliveries'))


def receipt_path(context, artifact):
    key = hashlib.sha256((context.id + '/' + artifact['id']).encode()).hexdigest()
    return directory() / (key + '.json')


def status(context, artifact):
    path = receipt_path(context, artifact)
    if not path.exists():
        return {'status': 'draft'}
    try:
        return json.loads(path.read_text())
    except (OSError, ValueError):
        raise ValueError('The send receipt could not be read. Check your mail provider before trying another draft.') from None


def addresses(value, required=False):
    artifacts.text(value, 2000, 'recipient list')
    if any(ord(c) < 32 for c in value):
        raise ValueError('Use email addresses separated by commas.')
    if not value.strip():
        if required:
            raise ValueError('Add at least one recipient.')
        return []
    header = default.header_factory('To', value)
    found = list(header.addresses)
    if header.defects or not found or len(found) > 20 or any(
        not a.username or not a.domain or not re.fullmatch(r'[A-Za-z0-9.!#$%&\x27*+/=?^_`{|}~-]+@[A-Za-z0-9.-]+', a.addr_spec)
        for a in found
    ):
        raise ValueError('Enter valid email addresses, separated by commas (up to 20).')
    return list(dict.fromkeys(a.addr_spec for a in found))


def connection(config):
    # Password rotation is allowed; a different server/account requires review again.
    return hashlib.sha256(json.dumps([config.get(k) for k in ('username', 'smtp_server', 'smtp_port')]).encode()).hexdigest()


def prepare(agent, artifact, data):
    if data.get('revision') != artifact['revision']:
        raise ValueError('This draft changed. Reopen it before reviewing.')
    if status(agent.context, artifact)['status'] != 'draft':
        raise ValueError('This draft already has a send attempt. Check its receipt before creating another draft.')
    config = mailbox.configuration(agent, data.get('account'))
    if not config.get('smtp_server'):
        raise ValueError('Add the outgoing SMTP server in Agent Zero Email Integration first.')
    subject = artifacts.text(data.get('subject'), 500, 'email subject').strip()
    if not subject or any(ord(c) < 32 for c in subject):
        raise ValueError('Add a subject without line breaks.')
    sender = addresses(config.get('username', ''), True)
    if len(sender) != 1:
        raise ValueError('This account needs one valid sender address.')
    to, cc, bcc = (addresses(data.get(key, ''), key == 'to') for key in ('to', 'cc', 'bcc'))
    if len(set(to + cc + bcc)) > 20:
        raise ValueError('Send to at most 20 recipients at once.')
    rich = mail_html.sanitize(artifacts.mask(agent.context, data.get('html')))
    body = mail_html.plain(rich)
    if not body.strip():
        raise ValueError('Add email content before sending.')
    origin = artifact.get('email_context') or {}
    parent = origin.get('message_id', '') if origin.get('account') == data.get('account') else ''
    if not re.fullmatch(r'<[^<>\s]{1,490}>', parent):
        parent = ''
    prepared = {'from': sender[0], 'to': to, 'cc': cc, 'bcc': bcc, 'subject': subject,
                'html': rich, 'text': body, 'in_reply_to': parent}
    token = secrets.token_urlsafe(32)
    entry = {**prepared, 'context': agent.context.id, 'artifact': artifact['id'],
             'revision': artifact['revision'], 'profile': agent.config.profile, 'agent_number': agent.number,
             'account': data['account'], 'connection': connection(config),
             'source_hash': hashlib.sha256(artifact['source'].encode()).hexdigest(),
             'expires': time.time() + TTL}
    with LOCK:
        for key, value in list(PENDING.items()):
            if value['expires'] < time.time() or (value['context'], value['artifact']) == (entry['context'], entry['artifact']):
                del PENDING[key]
        if len(PENDING) >= 100:
            raise ValueError('Too many email reviews are open. Try again shortly.')
        PENDING[token] = entry
    return {**prepared, 'token': token, 'expires': entry['expires']}


def smtp_send(config, prepared):
    message = EmailMessage()
    for name, value in [('From', prepared['from']), ('To', ', '.join(prepared['to'])),
                        ('Cc', ', '.join(prepared['cc'])), ('Subject', prepared['subject'])]:
        if value:
            message[name] = value
    message['Date'] = formatdate(localtime=False)
    message['Message-ID'] = prepared['message_id']
    if prepared['in_reply_to']:
        message['In-Reply-To'] = prepared['in_reply_to']
        message['References'] = prepared['in_reply_to']
    message.set_content(prepared['text'])
    message.add_alternative(prepared['html'], subtype='html')
    recipients = list(dict.fromkeys(prepared['to'] + prepared['cc'] + prepared['bcc']))
    client = None
    transmitting = False
    try:
        port = int(config.get('smtp_port', 587))
        secure = ssl.create_default_context()
        if port == 465:
            client = smtplib.SMTP_SSL(config['smtp_server'], port, timeout=30, context=secure)
        else:
            client = smtplib.SMTP(config['smtp_server'], port, timeout=30)
            client.ehlo()
            client.starttls(context=secure)
            client.ehlo()
        client.login(config['username'], config['password'])
        transmitting = True
        refused = client.send_message(message, from_addr=prepared['from'], to_addrs=recipients)
        return {'status': 'partial' if refused else 'sent',
                'accepted': [r for r in recipients if r not in refused], 'refused': [r for r in recipients if r in refused]}
    except (smtplib.SMTPRecipientsRefused, smtplib.SMTPSenderRefused, smtplib.SMTPDataError):
        return {'status': 'failed', 'detail': 'The mail server refused this message. Nothing was accepted for delivery.'}
    except Exception:
        return {'status': 'unknown' if transmitting else 'failed', 'detail':
                'The connection ended without a delivery receipt. Check your mail provider before sending another draft.' if transmitting else
                'The outgoing connection failed before the message was submitted. Check Email Integration settings.'}
    finally:
        if client:
            # A QUIT failure must not turn a successfully accepted message into a retry.
            try:
                client.quit()
            except Exception:
                try:
                    client.close()
                except Exception:
                    pass


def finish(path, config, prepared, receipt):
    result = {**receipt, **smtp_send(config, prepared), 'completed_at': time.time()}
    temp = path.with_suffix('.tmp')
    with open(temp, 'w', opener=lambda p, flags: os.open(p, flags, 0o600)) as stream:
        json.dump(result, stream)
        stream.flush()
        os.fsync(stream.fileno())
    os.replace(temp, path)
    return result


async def send(agent, artifact, token):
    artifacts.text(token, 100, 'email review token')
    with LOCK:
        existing = status(agent.context, artifact)
        if existing['status'] != 'draft':
            return existing
        prepared = PENDING.get(token)
        if not prepared or prepared['expires'] < time.time():
            raise ValueError('This review expired. Review the email again before sending.')
        if (prepared['context'], prepared['artifact'], prepared['revision'], prepared['profile'], prepared['agent_number'], prepared['source_hash']) != (
            agent.context.id, artifact['id'], artifact['revision'], agent.config.profile, agent.number, hashlib.sha256(artifact['source'].encode()).hexdigest()
        ):
            raise PermissionError('This review no longer matches the current draft and agent.')
        config = mailbox.configuration(agent, prepared['account'])
        if connection(config) != prepared['connection']:
            raise ValueError('The sending account changed. Review the email again.')
        prepared = copy.deepcopy(prepared)
        prepared['message_id'] = make_msgid()
        receipt = {k: prepared[k] for k in ('from', 'to', 'cc', 'bcc', 'subject', 'html', 'text', 'message_id')}
        receipt.update(status='sending', started_at=time.time())
        path = receipt_path(agent.context, artifact)
        path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
        # O_EXCL is the cross-process duplicate-send fence; never rely on chat snapshots.
        try:
            with open(path, 'x', opener=lambda p, flags: os.open(p, flags, 0o600)) as stream:
                json.dump(receipt, stream)
                stream.flush()
                os.fsync(stream.fileno())
        except FileExistsError:
            return status(agent.context, artifact)
        del PENDING[token]
    return await asyncio.to_thread(finish, path, config, prepared, receipt)
