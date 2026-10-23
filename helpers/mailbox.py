"""On-demand, read-only access to existing Agent Zero IMAP connections."""
import asyncio
import hashlib
import json
from email import policy
from email.parser import BytesParser
from email.utils import getaddresses

from helpers import plugins
from helpers.tool_policy import ensure_tool_allowed
from usr.plugins.openui.helpers import artifacts

SOURCES = "_openui_mail_sources"
MAX_MESSAGE = 262144
BODY_LIMIT = 12000


class MailboxReadError(ValueError):
    """A safe, user-facing validation error owned by this adapter."""


def authorize(agent):
    artifacts.authorize(agent)
    ensure_tool_allowed(agent, "openui_mail")
    if "_email_integration" not in plugins.get_enabled_plugins(agent):
        raise PermissionError("Enable the existing Agent Zero Email Integration to use this mailbox.")


def account_id(config):
    identity = [config.get(k, "") for k in ("name", "account_type", "imap_server", "username")]
    return hashlib.sha256(json.dumps(identity).encode()).hexdigest()[:24]


def configurations(agent):
    authorize(agent)
    config = plugins.get_plugin_config("_email_integration") or {}
    return [h for h in config.get("handlers", []) if isinstance(h, dict) and h.get("enabled") and
            all(h.get(key) for key in ("imap_server", "username", "password"))]


def accounts(agent):
    return [{"id": account_id(h), "label": str(h.get("name") or "Mailbox")[:100],
             "address": str(h.get("username", ""))[:254], "type": h.get("account_type", "imap"),
             "supported": h.get("account_type", "imap") == "imap"}
            for h in configurations(agent)]


def configuration(agent, account):
    for config in configurations(agent):
        if account_id(config) == account:
            if config.get("account_type", "imap") != "imap":
                raise ValueError("This release supports read-only IMAP mailboxes. Exchange requires a separate reader adapter.")
            return config
    raise PermissionError("This mailbox is no longer available to the current agent.")


def single_address(value):
    found = getaddresses([str(value or "")])
    if len(found) != 1 or "@" not in found[0][1] or any(c in found[0][1] for c in "\r\n"):
        return ""
    return found[0][1][:254]


def metadata(raw, reference, config):
    from plugins._email_integration.helpers.imap_client import _extract_single_sender, _matches_whitelist
    msg = BytesParser(policy=policy.default).parsebytes(raw)
    sender = _extract_single_sender(msg)
    whitelist = config.get("sender_whitelist") or []
    if not sender or (whitelist and not _matches_whitelist(sender, whitelist)):
        return None, msg
    return {"source": reference, "account": account_id(config),
            "account_label": str(config.get("name") or "Mailbox")[:100],
            "from_address": single_address(config.get("username")),
            "reply_to": single_address(msg.get("Reply-To")) or sender,
            "sender": sender, "subject": str(msg.get("Subject", "(no subject)"))[:500],
            "date": str(msg.get("Date", ""))[:100],
            "message_id": str(msg.get("Message-ID", ""))[:500]}, msg


def plain_body(msg):
    part = msg.get_body(preferencelist=("plain", "html"))
    if part is None:
        return "", False
    content = part.get_content()
    if not isinstance(content, str):
        content = ""
    if part.get_content_type() == "text/html":
        from bs4 import BeautifulSoup
        document = BeautifulSoup(content, "html.parser")
        for tag in document(["script", "style", "iframe", "object"]):
            tag.decompose()
        content = document.get_text("\n", strip=True)
    content = content.replace("\x00", "")
    encoded = content.encode("utf-8")
    return encoded[:BODY_LIMIT].decode("utf-8", errors="ignore"), len(encoded) > BODY_LIMIT


def read_sync(client, config, operation, *, source="", query="", limit=10, rich=False):
    # EXAMINE + BODY.PEEK leaves flags and the integration's polling cursor unchanged.
    selected = client.select_folder("INBOX", readonly=True)
    validity = int(selected[b"UIDVALIDITY"])
    account = account_id(config)
    if operation == "list":
        next_uid = int(selected.get(b"UIDNEXT", 1))
        criteria = ["UID", f"{max(1, next_uid - 5000)}:*", "ALL"]
        if query:
            criteria += ["TEXT", query]
        uids = sorted(client.search(criteria), reverse=True)[:limit]
        if not uids:
            return {"messages": [], "window": "Most recent 5,000 message UIDs in Inbox"}
        fields = "BODY.PEEK[HEADER.FIELDS (FROM REPLY-TO SUBJECT DATE MESSAGE-ID)]"
        fetched = client.fetch(uids, [fields, "FLAGS"])
        messages = []
        for uid in uids:
            row = fetched.get(uid, {})
            raw = next((v for k, v in row.items() if isinstance(k, bytes) and k.startswith(b"BODY[")), b"")
            if not isinstance(raw, bytes) or len(raw) > 16384:
                continue
            item, _ = metadata(raw, f"{account}:{validity}:{uid}", config)
            if item:
                item["unread"] = b"\\Seen" not in row.get(b"FLAGS", ())
                messages.append(item)
        return {"messages": messages, "window": "Most recent 5,000 message UIDs in Inbox"}
    parts = source.split(":")
    if len(parts) != 3 or parts[0] != account or not all(p.isdigit() for p in parts[1:]):
        raise MailboxReadError("Choose a message from this mailbox first.")
    if int(parts[1]) != validity:
        raise MailboxReadError("The mailbox changed. Refresh its messages before opening this item.")
    uid = int(parts[2])
    sizes = client.fetch([uid], ["RFC822.SIZE"])
    if uid not in sizes:
        raise MailboxReadError("This message is no longer in the Inbox.")
    if int(sizes[uid].get(b"RFC822.SIZE", MAX_MESSAGE + 1)) > MAX_MESSAGE:
        raise MailboxReadError("This message exceeds the 256 KiB preview limit. Open it in your email app.")
    fetched = client.fetch([uid], ["BODY.PEEK[]", "FLAGS"])
    row = fetched.get(uid, {})
    raw = row.get(b"BODY[]", b"")
    if not isinstance(raw, bytes) or not raw or len(raw) > MAX_MESSAGE:
        raise MailboxReadError("This message could not be safely previewed.")
    item, msg = metadata(raw, source, config)
    if not item:
        raise PermissionError("This message does not match the email integration's sender rules.")
    body, truncated = plain_body(msg)
    result = {**item, "body": body, "truncated": truncated, "unread": b"\\Seen" not in row.get(b"FLAGS", ())}
    if rich:
        from usr.plugins.openui.helpers.mail_html import from_message
        result['html'] = from_message(msg, body)
    return result


async def fetch(agent, operation, *, account="", source="", query="", limit=10, rich=False):
    if operation not in {"list", "read"}:
        raise ValueError("Only listing and reading messages are supported.")
    if not isinstance(source, str) or len(source) > 100:
        raise ValueError("Invalid message reference.")
    artifacts.text(query, 200, "mail search")
    if any(c in query for c in "\r\n\x00") or type(limit) is not int or not 1 <= limit <= 20:
        raise ValueError("Use a short search and a limit from 1 to 20.")
    config = configuration(agent, account or source.split(":")[0])
    from plugins._email_integration.helpers.imap_client import connect_imap, disconnect_imap
    client = None
    try:
        client = await connect_imap(server=config["imap_server"], port=int(config.get("imap_port", 993)),
                                    username=config["username"], password=config["password"], timeout=20)
        result = await asyncio.to_thread(read_sync, client, config, operation, source=source, query=query, limit=limit, rich=rich)
        configuration(agent, account_id(config))  # Re-check activation and scope after I/O.
        result = artifacts.mask(agent.context, result)
        if operation == "read":
            cached = agent.context.data.setdefault(SOURCES, {})
            cached[source] = {k: v for k, v in result.items() if k not in {"body", "html", "truncated", "unread"}}
            cached[source]["agent_number"] = agent.number
            cached[source]["profile"] = agent.config.profile
            while len(cached) > 20:
                cached.pop(next(iter(cached)))
        return result
    except (MailboxReadError, PermissionError):
        raise
    except Exception:
        # Provider exceptions can include connection or authentication details.
        raise ValueError("The mailbox could not be read. Check its existing Agent Zero Email Integration connection.") from None
    finally:
        if client is not None:
            await disconnect_imap(client)


def draft_context(agent, source):
    if source is None:
        return None
    if not isinstance(source, str):
        raise ValueError("mail_source must identify a message read in this chat.")
    saved = agent.context.data.get(SOURCES, {}).get(source)
    if not saved or saved.get("agent_number") != agent.number or saved.get("profile") != agent.config.profile:
        raise ValueError("Read the selected message with openui_mail before drafting its reply.")
    configuration(agent, saved["account"])
    return {k: v for k, v in saved.items() if k not in {"agent_number", "profile"}}
