"""Preview a single OpenUI tool call without executing it or calling a model.

Only strict JSON prefixes are accepted. The surface must precede the program so
an email draft can never be previewed under the UI image policy. Missing deltas,
reordered arguments and unsupported call envelopes fall back to normal dispatch.
"""
from __future__ import annotations

import asyncio
import hashlib
import json
import time

from usr.plugins.openui.helpers import artifacts
from usr.plugins.openui.helpers.config import get_config, verify_assets

KEY = "_openui_current_answer"
ACTIVE = {}
WIRE_LIMIT = artifacts.SOURCE_LIMIT * 6 + 32768
now = time.monotonic


class PrefixReader:
    """Decode JSON strings only through complete escapes, including surrogate pairs."""

    def __init__(self, source):
        if not isinstance(source, str) or len(source) > WIRE_LIMIT:
            raise ValueError("Unsupported stream size")
        self.source = source
        self.closed = set()

    def space(self, i):
        while i < len(self.source) and self.source[i] in " \n\r\t":
            i += 1
        return i

    def string(self, i):
        start = i + 1
        i = start
        safe = start
        s = self.source
        while i < len(s):
            if s[i] == '"':
                return json.loads(s[start - 1:i + 1]), i + 1, True
            if ord(s[i]) < 32:
                raise ValueError("Invalid string")
            if s[i] == "\\":
                if i + 1 == len(s):
                    break
                if s[i + 1] == "u":
                    if len(s) < i + 6:
                        break
                    code = int(s[i + 2:i + 6], 16)
                    if 0xD800 <= code <= 0xDBFF:
                        if len(s) < i + 12:
                            break
                        if s[i + 6:i + 8] != "\\u" or not 0xDC00 <= int(s[i + 8:i + 12], 16) <= 0xDFFF:
                            raise ValueError("Invalid surrogate pair")
                        i += 6
                    elif 0xDC00 <= code <= 0xDFFF:
                        raise ValueError("Invalid surrogate")
                    i += 6
                elif s[i + 1] in '"\\/bfnrt':
                    i += 2
                else:
                    raise ValueError("Invalid escape")
            else:
                if 0xD800 <= ord(s[i]) <= 0xDFFF:
                    raise ValueError("Invalid surrogate")
                i += 1
            safe = i
        return json.loads(s[start - 1:safe] + '"'), len(s), False

    def value(self, i=0, path=()):
        if len(path) > 12:
            raise ValueError("JSON too deep")
        i = self.space(i)
        s = self.source
        if i == len(s):
            return None, i, False
        ch = s[i]
        if ch == '"':
            value, i, done = self.string(i)
        elif ch in "{[":
            is_object = ch == "{"
            end = "}" if is_object else "]"
            value = {} if is_object else []
            i = self.space(i + 1)
            if i < len(s) and s[i] == end:
                i, done = i + 1, True
            else:
                while True:
                    i = self.space(i)
                    if i == len(s):
                        return value, i, False
                    key = len(value)
                    if is_object:
                        if s[i] != '"':
                            raise ValueError("Expected object key")
                        key, i, done = self.string(i)
                        if not done:
                            return value, i, False
                        if key in value:
                            raise ValueError("Duplicate key")
                        i = self.space(i)
                        if i == len(s):
                            return value, i, False
                        if s[i] != ":":
                            raise ValueError("Expected colon")
                        i += 1
                    item, i, done = self.value(i, (*path, key))
                    if is_object:
                        value[key] = item
                    else:
                        value.append(item)
                    if not done:
                        return value, i, False
                    i = self.space(i)
                    if i == len(s):
                        return value, i, False
                    if s[i] == end:
                        i, done = i + 1, True
                        break
                    if s[i] != ",":
                        raise ValueError("Expected comma")
                    i += 1
        else:
            end = i
            while end < len(s) and s[end] not in " \n\r\t,]}":
                end += 1
            token = s[i:end]
            if end == len(s):
                return None, end, False
            value = json.loads(token)
            if isinstance(value, (dict, list, str)) or token in {"NaN", "Infinity", "-Infinity"}:
                raise ValueError("Invalid primitive")
            i, done = end, True
        if done:
            self.closed.add(path)
        return value, i, done

    def arguments(self):
        value, i, done = self.value()
        if self.space(i) != len(self.source):
            raise ValueError("Multiple or trailing calls")
        if not isinstance(value, dict):
            return None
        if "parallel_tool_calls" in value or "tool_calls" in value:
            raise ValueError("Parallel calls are not previewed")
        if value.get("tool_name") != "openui" or ("tool_name",) not in self.closed:
            return None
        args = value.get("tool_args")
        if not isinstance(args, dict):
            return None
        if set(args) - {"title", "summary", "surface", "program", "mail_source"}:
            raise ValueError("Unsupported preview arguments")
        if ("tool_args", "surface") not in self.closed or args.get("surface") not in {"ui", "email"}:
            return None
        if not isinstance(args.get("program"), str):
            return None
        return args


def state(agent, loop_data=None):
    loop = loop_data or getattr(agent, "loop_data", None)
    return loop.params_temporary.get(KEY) if loop else None


def finish(agent, loop_data=None, status="interrupted"):
    pending = state(agent, loop_data)
    if not pending or pending.get("closed"):
        return
    pending["closed"] = True
    ACTIVE.pop(id(pending), None)
    if pending.get("task"):
        pending["task"].remove_done_callback(pending["cleanup"])
    if pending.get("id"):
        try:
            artifacts.update(agent, pending["log"], pending["id"], pending["safe"], status)
        except Exception:
            pass  # Deleted chats and revoked ownership cannot be written back.


def stop():
    for agent, loop in list(ACTIVE.values()):
        finish(agent, loop)


def preview(agent, loop_data, full):
    """Presentation side effect only; never change the main stream or dispatch."""
    if not agent or not loop_data:
        return
    pending = state(agent, loop_data)
    if pending and pending.get("closed"):
        return
    timestamp = now()
    if pending and timestamp - pending["last"] < 0.2:
        return
    try:
        args = PrefixReader(full).arguments()
        if args is None:
            if pending:
                finish(agent, loop_data)
            return
        if get_config(agent)["generation_mode"] != "agent_program":
            return
        artifacts.authorize(agent)
        program = artifacts.text(args["program"], artifacts.SOURCE_LIMIT, "program")
        if not program:
            return
        from helpers.secrets import StreamingSecretsFilter, get_secrets_manager
        # Re-filter the decoded snapshot: JSON escaping and later secret masking
        # can change previously seen characters. Never expose a secret prefix.
        filtered = StreamingSecretsFilter(get_secrets_manager(agent.context).load_secrets(), min_trigger=1)
        safe = filtered.process_chunk(program)
        if not pending:
            verify_assets()
            log = agent.context.log.log(type="tool", heading=f"icon://construction {agent.agent_name}: Creating interactive answer", content="", _tool_name="openui")
            record = artifacts.create(agent, log, "Interactive answer", "Creating your interactive answer…",
                                      safe, status="generating", surface=args["surface"])
            pending = {"id": record["id"], "log": log, "surface": args["surface"], "safe": safe, "last": timestamp}
            loop_data.params_temporary[KEY] = pending
            ACTIVE[id(pending)] = (agent, loop_data)
            task = asyncio.current_task()
            pending["task"] = task
            pending["cleanup"] = lambda _: finish(agent, loop_data)
            if task:
                task.add_done_callback(pending["cleanup"])
        elif pending["surface"] != args["surface"]:
            finish(agent, loop_data)
            return
        elif hashlib.sha256(program[:pending["length"]].encode()).hexdigest() != pending["digest"]:
            finish(agent, loop_data)
            return
        pending["length"] = len(program)
        pending["digest"] = hashlib.sha256(program.encode()).hexdigest()
        pending["safe"] = safe
        if timestamp - pending["last"] >= 0.2:
            artifacts.update(agent, pending["log"], pending["id"], safe, "generating")
            pending["last"] = timestamp
    except Exception:
        # Preview failure must not cancel the user's normal model/tool response.
        finish(agent, loop_data)
        loop_data.params_temporary[KEY] = {"closed": True}


def matching(agent, loop_data, args):
    pending = state(agent, loop_data)
    program = args.get("program")
    if (not pending or pending.get("closed") or pending.get("claimed") or not isinstance(program, str)
            or args.get("surface", "ui") != pending["surface"]):
        return None
    if hashlib.sha256(program[:pending["length"]].encode()).hexdigest() != pending["digest"]:
        return None
    return pending


def complete(tool, program):
    pending = matching(tool.agent, tool.loop_data, {"program": program, "surface": tool.surface})
    if not pending or pending["log"] is not tool.log:
        return None
    record = artifacts.complete_preview(tool.agent, tool.log, pending["id"], program,
                                        tool.title, tool.summary, tool.email_context)
    pending["claimed"] = True
    pending["closed"] = True
    ACTIVE.pop(id(pending), None)
    if pending.get("task"):
        pending["task"].remove_done_callback(pending["cleanup"])
    return record
