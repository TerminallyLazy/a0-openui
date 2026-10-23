from helpers.api import ApiHandler, Request, Response
from usr.plugins.openui.helpers.artifacts import save_state


class State(ApiHandler):
    async def process(self, input: dict, request: Request):
        try:
            return save_state(input.get("context"), input.get("artifact"),
                              input.get("revision"), input.get("state_revision"), input.get("state"))
        except (ValueError, LookupError, PermissionError) as exc:
            return Response(str(exc), status=409, mimetype="text/plain")
