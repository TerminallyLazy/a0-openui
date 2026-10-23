from pathlib import Path
import hashlib
import json

ROOT = Path(__file__).resolve().parents[1]
PLUGIN = "openui"


def get_config(agent):
    from helpers.plugins import get_plugin_config
    raw = get_plugin_config(PLUGIN, agent=agent) or {}
    mode = raw.get("generation_mode", "agent_program")
    if mode not in {"agent_program", "agent_stream", "gateway"}:
        raise ValueError("Unknown OpenUI generation mode. Review plugin settings.")
    return {
        "generation_mode": mode,
        "stream_model": "utility" if raw.get("stream_model") == "utility" else "main",
        "gateway_model": str(raw.get("gateway_model", ""))[:160],
        "max_output_tokens": max(256, min(int(raw.get("max_output_tokens", 4096)), 8192)),
        "timeout_seconds": max(10, min(int(raw.get("timeout_seconds", 120)), 300)),
    }


def manifest():
    return json.loads((ROOT / "generated/manifest.json").read_text())


def library_contract(surface):
    if surface not in {"ui", "email"}:
        raise ValueError("OpenUI surface must be ui or email.")
    return manifest()["libraries"][surface]


def verify_assets():
    info = manifest()
    for name, digest in info["files"].items():
        path = (ROOT / name).resolve()
        if not path.is_relative_to(ROOT) or not path.is_file():
            raise ValueError("OpenUI release assets are incomplete. Reinstall the plugin release.")
        if hashlib.sha256(path.read_bytes()).hexdigest() != digest:
            raise ValueError("OpenUI release assets do not match. Rebuild or reinstall the release.")
    return info
