from helpers.api import ApiHandler, Request, Response
from usr.plugins.openui.helpers import artifacts, mailbox, delivery


class Mail(ApiHandler):
    async def process(self, input: dict, request: Request):
        try:
            context, record = artifacts.resolve(input.get("context"), input.get("artifact"))
            if record.get("surface") != "email" or record["status"] != "complete":
                raise ValueError("Open a completed email draft first.")
            agent = context.agent0
            while agent is not None and agent.number != record["agent_number"]:
                agent = agent.data.get(agent.DATA_NAME_SUBORDINATE)
            if agent is None:
                raise PermissionError("This draft's agent is no longer available.")
            operation = input.get("operation", "accounts")
            mailbox.authorize(agent)
            if operation == "accounts":
                return {"accounts": mailbox.accounts(agent)}
            if operation == "delivery_status":
                return delivery.status(context, record)
            if operation == "prepare_send":
                return delivery.prepare(agent, record, input)
            if operation == "send":
                return await delivery.send(agent, record, input.get('token'))
            return await mailbox.fetch(agent, operation, account=input.get("account", ""),
                                       source=input.get("source", ""), query=input.get("query", ""), limit=input.get("limit", 10), rich=True)
        except (ValueError, LookupError, PermissionError) as exc:
            return Response(str(exc), status=400, mimetype="text/plain")
        except OSError:
            return Response('The send receipt could not be saved. Check the mail provider before retrying.', status=500, mimetype='text/plain')
