import asyncio
from types import SimpleNamespace

import pytest
from usr.plugins.openui.helpers import mailbox

CONFIG = {"name": "Test mailbox", "enabled": True, "account_type": "imap", "imap_server": "mail.example.test",
          "username": "owner@example.test", "password": "synthetic-password"}
RAW = b'From: Sender <sender@example.test>\r\nReply-To: replies@example.test\r\nSubject: Example\r\nDate: Fri, 23 Oct 2026 12:00:00 +0000\r\nMessage-ID: <synthetic@example.test>\r\nContent-Type: text/plain; charset=utf-8\r\n\r\nA synthetic message.'


class Client:
    def __init__(self, raw=RAW):
        self.raw = raw
        self.calls = []

    def select_folder(self, folder, readonly=False):
        self.calls.append(("select", folder, readonly))
        assert readonly is True
        return {b"UIDVALIDITY": 42, b"UIDNEXT": 8}

    def search(self, criteria):
        self.calls.append(("search", criteria))
        return [7]

    def fetch(self, uids, fields):
        self.calls.append(("fetch", uids, fields))
        if fields == ["RFC822.SIZE"]:
            return {7: {b"RFC822.SIZE": len(self.raw)}}
        if fields[0].startswith("BODY.PEEK[HEADER"):
            return {7: {b"BODY[HEADER.FIELDS (FROM REPLY-TO SUBJECT DATE MESSAGE-ID)]": self.raw.split(b"\r\n\r\n")[0]+b"\r\n\r\n", b"FLAGS": ()}}
        assert fields == ["BODY.PEEK[]", "FLAGS"]
        return {7: {b"BODY[]": self.raw, b"FLAGS": ()}}


@pytest.fixture
def agent(monkeypatch):
    value = SimpleNamespace(number=0, config=SimpleNamespace(profile="default"), context=SimpleNamespace(data={}))
    monkeypatch.setattr(mailbox.artifacts, "authorize", lambda agent: None)
    monkeypatch.setattr(mailbox.artifacts, "mask", lambda context, value: value)
    monkeypatch.setattr(mailbox, "ensure_tool_allowed", lambda *a: None)
    monkeypatch.setattr(mailbox.plugins, "get_enabled_plugins", lambda agent: ["openui", "_email_integration"])
    monkeypatch.setattr(mailbox.plugins, "get_plugin_config", lambda *a: {"handlers": [dict(CONFIG)]})
    return value


def test_accounts_never_expose_passwords_or_server_configuration(agent):
    result = mailbox.accounts(agent)
    assert result[0]["address"] == "owner@example.test"
    assert result[0]["supported"]
    assert "password" not in str(result) and "mail.example.test" not in str(result)


def test_disabled_integration_and_denied_tool_cannot_access_mail(agent, monkeypatch):
    monkeypatch.setattr(mailbox.plugins, "get_enabled_plugins", lambda agent: ["openui"])
    with pytest.raises(PermissionError):
        mailbox.accounts(agent)
    monkeypatch.setattr(mailbox.plugins, "get_enabled_plugins", lambda agent: ["openui", "_email_integration"])
    def deny(*args): raise PermissionError("denied")
    monkeypatch.setattr(mailbox, "ensure_tool_allowed", deny)
    with pytest.raises(PermissionError):
        mailbox.accounts(agent)


def test_list_fetches_headers_with_peek_in_readonly_inbox():
    client = Client()
    result = mailbox.read_sync(client, CONFIG, "list", query="synthetic", limit=10)
    assert len(result["messages"]) == 1
    assert result["messages"][0]["unread"]
    assert "body" not in result["messages"][0]
    assert ("search", ["UID", "1:*", "ALL", "TEXT", "synthetic"]) in client.calls
    assert all("PEEK" in c[2][0] for c in client.calls if c[0] == "fetch")


def test_read_retains_read_flag_and_actual_reply_metadata():
    client = Client()
    ref = f"{mailbox.account_id(CONFIG)}:42:7"
    result = mailbox.read_sync(client, CONFIG, "read", source=ref)
    assert result["body"] == "A synthetic message."
    assert result["unread"] and result["reply_to"] == "replies@example.test"
    assert result["from_address"] == "owner@example.test"
    assert ("fetch", [7], ["BODY.PEEK[]", "FLAGS"]) in client.calls


@pytest.mark.parametrize("source", ["other:42:7", "bad", "account:42:1 OR ALL"])
def test_foreign_or_malformed_message_reference_is_rejected(source):
    with pytest.raises(ValueError):
        mailbox.read_sync(Client(), CONFIG, "read", source=source)


def test_uidvalidity_change_refuses_stale_reference():
    with pytest.raises(ValueError, match="mailbox changed"):
        mailbox.read_sync(Client(), CONFIG, "read", source=f"{mailbox.account_id(CONFIG)}:41:7")


def test_oversized_message_is_rejected_before_body_download():
    client = Client(RAW + b"x" * mailbox.MAX_MESSAGE)
    with pytest.raises(ValueError, match="256 KiB"):
        mailbox.read_sync(client, CONFIG, "read", source=f"{mailbox.account_id(CONFIG)}:42:7")
    assert not any(c[0] == "fetch" and c[2][0] == "BODY.PEEK[]" for c in client.calls)


def test_sender_rules_remain_in_force():
    config = {**CONFIG, "sender_whitelist": ["allowed@example.test"]}
    assert mailbox.read_sync(Client(), config, "list")["messages"] == []
    with pytest.raises(PermissionError):
        mailbox.read_sync(Client(), config, "read", source=f"{mailbox.account_id(config)}:42:7")


def test_html_message_is_returned_as_bounded_text_without_active_content():
    from email.message import EmailMessage
    msg = EmailMessage()
    msg.set_content('<style>hidden</style><p>Hello</p><script>secret()</script><img src="https://tracker.test/x">' + 'x'*13000, subtype="html")
    body, truncated = mailbox.plain_body(msg)
    assert truncated and len(body.encode()) <= mailbox.BODY_LIMIT
    assert "<" not in body and "secret()" not in body and "tracker" not in body


def test_fetch_closes_connection_and_binds_metadata_to_reading_agent(agent, monkeypatch):
    from plugins._email_integration.helpers import imap_client
    client = Client()
    closed = []
    async def connect(**kwargs):
        assert kwargs["password"] == "synthetic-password"
        return client
    async def disconnect(value): closed.append(value)
    monkeypatch.setattr(imap_client, "connect_imap", connect)
    monkeypatch.setattr(imap_client, "disconnect_imap", disconnect)
    ref = f"{mailbox.account_id(CONFIG)}:42:7"
    result = asyncio.run(mailbox.fetch(agent, "read", source=ref))
    assert closed == [client] and result["body"]
    origin = mailbox.draft_context(agent, ref)
    assert origin["reply_to"] == "replies@example.test" and "body" not in origin
    agent.number = 1
    with pytest.raises(ValueError): mailbox.draft_context(agent, ref)


@pytest.mark.parametrize("exception", [RuntimeError, ValueError])
def test_provider_errors_do_not_expose_credentials(agent, monkeypatch, exception):
    from plugins._email_integration.helpers import imap_client
    async def fail(**kwargs): raise exception("server echoed synthetic-password")
    monkeypatch.setattr(imap_client, "connect_imap", fail)
    with pytest.raises(ValueError) as exc:
        asyncio.run(mailbox.fetch(agent, "list", account=mailbox.account_id(CONFIG)))
    assert "synthetic-password" not in str(exc.value)


@pytest.mark.parametrize("operation", ["send", "delete", "mark_read", "archive"])
def test_mail_operations_are_read_only(agent, operation):
    with pytest.raises(ValueError, match="Only listing and reading"):
        asyncio.run(mailbox.fetch(agent, operation))


def test_exchange_is_reported_as_unsupported_instead_of_claiming_connection(agent, monkeypatch):
    monkeypatch.setattr(mailbox.plugins, "get_plugin_config", lambda *a: {"handlers": [{**CONFIG, "account_type": "exchange"}]})
    result = mailbox.accounts(agent)
    assert result[0]["supported"] is False
    with pytest.raises(ValueError, match="separate reader"):
        mailbox.configuration(agent, result[0]["id"])


def test_rich_preview_is_opt_in_and_not_in_the_model_response_or_metadata(agent, monkeypatch):
    from plugins._email_integration.helpers import imap_client
    async def connect(**kwargs): return Client()
    async def disconnect(client): pass
    monkeypatch.setattr(imap_client, 'connect_imap', connect)
    monkeypatch.setattr(imap_client, 'disconnect_imap', disconnect)
    ref = f'{mailbox.account_id(CONFIG)}:42:7'
    assert 'html' not in asyncio.run(mailbox.fetch(agent, 'read', source=ref))
    rich = asyncio.run(mailbox.fetch(agent, 'read', source=ref, rich=True))
    assert 'A synthetic message.' in rich['html']
    assert 'html' not in mailbox.draft_context(agent, ref)
