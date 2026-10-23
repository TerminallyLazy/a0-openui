"""Bounded chat-owned OpenUI documents; logs contain descriptors, never source."""
from __future__ import annotations

import copy
import json
import math
import threading
import time
import uuid

from usr.plugins.openui.helpers.config import library_contract

KEY = "openui_artifacts_v1"
SOURCE_LIMIT = 65536
STATE_LIMIT = 8192
DATA_LIMIT = 16384
TOTAL_LIMIT = 1048576
COUNT_LIMIT = 32
EPOCH = str(uuid.uuid4())
LOCK = threading.RLock()
TERMINAL = {"complete", "interrupted", "failed"}


def bounded_json(value, limit, *, depth=0, max_depth=8):
    def check(item, level):
        if level > max_depth:
            raise ValueError("OpenUI data is nested too deeply.")
        if isinstance(item, dict):
            if len(item) > 256:
                raise ValueError("OpenUI object has too many fields.")
            for key, val in item.items():
                if not isinstance(key, str) or len(key) > 128 or key in {"__proto__", "prototype", "constructor"}:
                    raise ValueError("OpenUI data contains an invalid field name.")
                check(val, level + 1)
        elif isinstance(item, list):
            if len(item) > 2000:
                raise ValueError("OpenUI list has too many items.")
            for val in item:
                check(val, level + 1)
        elif item is None or isinstance(item, (str, bool, int)):
            pass
        elif isinstance(item, float) and math.isfinite(item):
            pass
        else:
            raise ValueError("OpenUI requires finite JSON data.")
    check(value, depth)
    encoded = json.dumps(value, ensure_ascii=False, allow_nan=False)
    if len(encoded.encode("utf-8")) > limit:
        raise ValueError("OpenUI data exceeds this artifact's size limit.")
    return copy.deepcopy(value)


def text(value, limit, label):
    if not isinstance(value, str) or len(value.encode("utf-8")) > limit:
        raise ValueError(f"OpenUI {label} must be text within {limit} bytes.")
    return value


def mask(context, value):
    from helpers.secrets import get_secrets_manager
    manager = get_secrets_manager(context)
    def visit(item):
        if isinstance(item, str):
            return manager.mask_values(item)
        if isinstance(item, list):
            return [visit(v) for v in item]
        if isinstance(item, dict):
            return {k: visit(v) for k, v in item.items()}
        return item
    return visit(value)


def persist(context):
    from helpers.persist_chat import save_tmp_chat
    save_tmp_chat(context)


def authorize(agent):
    from agent import AgentContext
    from helpers.plugins import get_enabled_plugins
    from helpers.tool_policy import ensure_tool_allowed
    if AgentContext.get(agent.context.id) is not agent.context:
        raise PermissionError("This OpenUI chat is no longer active.")
    if "openui" not in get_enabled_plugins(agent):
        raise PermissionError("OpenUI is disabled for this agent.")
    ensure_tool_allowed(agent, "openui")


def _commit(context, record):
    current = context.data.get(KEY, {})
    if not isinstance(current, dict):
        raise ValueError("OpenUI artifact storage is not valid.")
    updated = {**current, record["id"]: record}
    if len(updated) > COUNT_LIMIT:
        raise ValueError("This chat has reached its OpenUI artifact limit.")
    # The store adds two wrapper levels around a previously validated state.
    bounded_json(updated, TOTAL_LIMIT, max_depth=10)
    context.data[KEY] = updated


def create(agent, log, title, summary, source="", status="complete", surface="ui", email_context=None):
    authorize(agent)
    info = library_contract(surface)
    record = mask(agent.context, {
        "id": str(uuid.uuid4()), "log_id": log.id, "agent_number": agent.number,
        "profile": agent.config.profile, "format_version": 1, "surface": surface,
        "library_id": info["library_id"], "spec_digest": info["spec_digest"],
        "source": text(source, SOURCE_LIMIT, "program"), "revision": 1,
        "title": text(title, 200, "title"), "summary": text(summary, 1200, "summary"),
        "state": {}, "state_revision": 0, "status": status,
        "created_at": time.time(), "updated_at": time.time(), "epoch": EPOCH,
    })
    if email_context is not None:
        record["email_context"] = mask(agent.context, bounded_json(email_context, 4096))
    text(record["source"], SOURCE_LIMIT, "masked program")
    with LOCK:
        _commit(agent.context, record)
    publish(log, record)
    if status in TERMINAL:
        persist(agent.context)
    return copy.deepcopy(record)


def publish(log, record):
    log.update(content=record["summary"], _tool_name="openui",
               openui_artifact=record["id"], openui_revision=record["revision"],
               openui_status=record["status"], openui_surface=record.get("surface", "ui"))


def update(agent, log, artifact_id, source, status):
    from agent import AgentContext
    if AgentContext.get(agent.context.id) is not agent.context:
        raise PermissionError("This OpenUI chat is no longer active.")
    source = text(source, SOURCE_LIMIT, "program")
    with LOCK:
        old = agent.context.data[KEY][artifact_id]
        record = {**old, "source": text(mask(agent.context, source), SOURCE_LIMIT, "masked program"), "status": status,
                  "revision": old["revision"] + 1, "updated_at": time.time()}
        _commit(agent.context, record)
    publish(log, record)
    if status in TERMINAL:
        persist(agent.context)
    return copy.deepcopy(record)


def complete_preview(agent, log, artifact_id, source, title, summary, email_context=None):
    """Promote the same inert preview only after ordinary tool validation."""
    authorize(agent)
    with LOCK:
        old = agent.context.data[KEY][artifact_id]
        if old["status"] != "generating" or old["log_id"] != log.id or old["epoch"] != EPOCH:
            raise ValueError("The OpenUI preview is no longer current.")
        record = {**old, "source": text(source, SOURCE_LIMIT, "program"),
                  "title": text(title, 200, "title"), "summary": text(summary, 1200, "summary"),
                  "status": "complete", "revision": old["revision"] + 1, "updated_at": time.time()}
        if email_context is not None:
            record["email_context"] = bounded_json(email_context, 4096)
        record = mask(agent.context, record)
        text(record["source"], SOURCE_LIMIT, "masked program")
        _commit(agent.context, record)
    publish(log, record)
    persist(agent.context)
    return copy.deepcopy(record)


def resolve(context_id, artifact_id):
    from agent import AgentContext
    if not isinstance(context_id, str) or not context_id or not isinstance(artifact_id, str):
        raise ValueError("An existing chat and artifact are required.")
    context = AgentContext.get(context_id)
    if context is None:
        raise LookupError("The OpenUI chat no longer exists.")
    with LOCK:
        record = context.data.get(KEY, {}).get(artifact_id)
        if not isinstance(record, dict):
            raise LookupError("The OpenUI artifact is unavailable in this chat snapshot.")
        # Chat imports and older snapshots are data, not trusted plugin-created records.
        required = {"id", "log_id", "agent_number", "profile", "source", "revision", "state", "state_revision", "status", "spec_digest"}
        if not required.issubset(record) or record["id"] != artifact_id:
            raise ValueError("The imported OpenUI artifact is incomplete.")
        bounded_json(record, SOURCE_LIMIT + STATE_LIMIT + 8192, max_depth=9)
        text(record["source"], SOURCE_LIMIT, "program")
        bounded_json(record["state"], STATE_LIMIT)
        if (not isinstance(record["state"], dict) or type(record["revision"]) is not int or
                type(record["state_revision"]) is not int or type(record["agent_number"]) is not int or
                record["status"] not in TERMINAL | {"generating"}):
            raise ValueError("The imported OpenUI artifact is invalid.")
        agent = context.agent0
        while agent is not None and agent.number != record["agent_number"]:
            agent = agent.data.get(agent.DATA_NAME_SUBORDINATE)
        if agent is None or agent.config.profile != record["profile"]:
            raise PermissionError("This artifact's agent profile is no longer active.")
        authorize(agent)
        if not any(log.id == record["log_id"] and (log.kvps or {}).get("openui_artifact") == artifact_id for log in context.log.logs):
            raise LookupError("The OpenUI artifact is not linked to this chat history.")
        if record["status"] == "generating" and record.get("epoch") != EPOCH:
            record = {**record, "status": "interrupted", "revision": record["revision"] + 1}
            _commit(context, record)
            persist(context)
        return context, copy.deepcopy(record)


def snapshot(context_id, artifact_id):
    context, record = resolve(context_id, artifact_id)
    record.pop("epoch", None)
    return mask(context, record)


def save_state(context_id, artifact_id, revision, state_revision, state):
    if type(revision) is not int or type(state_revision) is not int:
        raise ValueError("OpenUI revisions must be integers.")
    if not isinstance(state, dict):
        raise ValueError("OpenUI form state must be an object.")
    bounded_json(state, STATE_LIMIT)
    with LOCK:
        context, record = resolve(context_id, artifact_id)
        if record["status"] != "complete" or record["revision"] != revision:
            raise ValueError("The OpenUI program changed. Reopen the artifact before editing.")
        if record["state_revision"] != state_revision:
            raise ValueError("The form was updated elsewhere. Reopen it before editing.")
        record = {**record, "state": mask(context, state), "state_revision": state_revision + 1,
                  "updated_at": time.time()}
        _commit(context, record)
        persist(context)
    return {"state_revision": record["state_revision"]}
