from helpers.extension import Extension
from usr.plugins.openui.helpers.config import ROOT, get_config


class OpenUIConfig(Extension):
    async def execute(self, **kwargs):
        if not self.agent:
            return
        config = get_config(self.agent)
        if config["generation_mode"] == "agent_program":
            contract = (ROOT / "generated/tool-reference.txt").read_text()
            contract += "\n\nFor surface=email use this separate library:\n" + (ROOT / "generated/email-tool-reference.txt").read_text()
            mode = "Write the OpenUI program in tool_args.program. Always emit surface, title and summary before program, so the UI can appear while you generate it in this same response. Use surface=ui or surface=email explicitly. Do not use request/data."
        else:
            contract = "The plugin generates the program using the configured UI-generation mode."
            mode = "Supply request (what to show), data (bounded JSON), title and summary. Do not supply program."
        self.agent.data.setdefault("_tool_prompt_kwargs", {})["agent.system.tool.openui.md"] = {
            "openui_mode": mode, "openui_contract": contract,
        }
