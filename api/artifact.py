from helpers.api import ApiHandler, Request, Response
from usr.plugins.openui.helpers.artifacts import snapshot


class Artifact(ApiHandler):
    async def process(self, input: dict, request: Request):
        try:
            return {"artifact": snapshot(input.get("context"), input.get("artifact"))}
        except (ValueError, LookupError, PermissionError) as exc:
            return Response(str(exc), status=400, mimetype="text/plain")
