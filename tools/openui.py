from helpers.tool import Tool, Response
from usr.plugins.openui.helpers import artifacts, generation, mailbox, current_answer
from usr.plugins.openui.helpers.config import get_config, verify_assets, library_contract


class OpenUI(Tool):
    def get_log_object(self):
        pending = current_answer.matching(self.agent, self.loop_data, self.args) if get_config(self.agent)["generation_mode"] == "agent_program" else None
        if pending:
            pending["log"].update(heading=f"icon://construction {self.agent.agent_name}: Using tool 'openui'")
            return pending["log"]
        current_answer.finish(self.agent, self.loop_data)
        # Source belongs in the bounded artifact store, not in truncated log kvps.
        return self.agent.context.log.log(type="tool", heading=f"icon://construction {self.agent.agent_name}: Using tool 'openui'",
                                          content="", _tool_name="openui")

    async def execute(self, title="Interactive answer", summary="Interactive answer is available in the WebUI.",
                      program=None, request=None, data=None, prior_artifact=None, surface="ui", mail_source=None, **kwargs):
        artifacts.authorize(self.agent)
        verify_assets()
        config = get_config(self.agent)
        library_contract(surface)
        self.surface = surface
        if mail_source is not None and surface != "email":
            raise ValueError("mail_source applies only to an email draft.")
        self.email_context = mailbox.draft_context(self.agent, mail_source)
        self.title = artifacts.text(title, 200, "title")
        self.summary = artifacts.text(summary, 1200, "summary")
        if kwargs:
            raise ValueError("Unknown OpenUI arguments.")
        if config["generation_mode"] == "agent_program":
            if request is not None or data is not None or prior_artifact is not None:
                raise ValueError("Use the program argument in current-answer mode.")
            if not isinstance(program, str) or not program.strip():
                raise ValueError("OpenUI requires a nonempty program.")
            record = current_answer.complete(self, program)
            if record is None:
                record = artifacts.create(self.agent, self.log, self.title, self.summary, program, surface=surface,
                                          email_context=self.email_context)
        else:
            if program is not None:
                raise ValueError("Use request and data in the selected streaming mode.")
            record = await generation.generate(self, config, request, data if data is not None else {}, prior_artifact)
        return Response(message=f"{self.summary}\nOpenUI artifact: {record['id']}", break_loop=False,
                        additional={"openui_artifact": record["id"], "openui_revision": record["revision"]})
