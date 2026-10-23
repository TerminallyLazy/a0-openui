"""Isolated UI generation. No main-loop response IDs or history mutations."""
import asyncio
import copy
import json
import time

from usr.plugins.openui.helpers import artifacts
from usr.plugins.openui.helpers.config import ROOT

ACTIVE = {}


def stop():
    for loop, task in list(ACTIVE.values()):
        if not task.done():
            loop.call_soon_threadsafe(task.cancel)


async def generate(tool, config, request, data, prior=None):
    from helpers.secrets import get_secrets_manager
    artifacts.text(request, 8192, "request")
    artifacts.bounded_json(data, artifacts.DATA_LIMIT)
    agent = tool.agent
    prompt_name = "prompt-gateway.txt" if config["generation_mode"] == "gateway" else "prompt-direct.txt"
    surface = getattr(tool, "surface", "ui")
    if surface == "email": prompt_name = "email-" + prompt_name
    prompt = (ROOT / "generated" / prompt_name).read_text()
    user_data = {"request": request, "data": data}
    if prior:
        _, previous = artifacts.resolve(agent.context.id, prior)
        user_data["previous_program"] = previous["source"]
    message = json.dumps(artifacts.mask(agent.context, user_data), ensure_ascii=False)
    record = artifacts.create(agent, tool.log, tool.title, tool.summary, status="generating", surface=surface,
                              email_context=getattr(tool, "email_context", None))
    source = ""
    last_publish = 0.0
    # min_trigger=1 is required for arbitrary one-character stream boundaries.
    from helpers.secrets import StreamingSecretsFilter
    filter_ = StreamingSecretsFilter(get_secrets_manager(agent.context).load_secrets(), min_trigger=1)
    task = asyncio.current_task()
    ACTIVE[record["id"]] = (asyncio.get_running_loop(), task)

    async def chunk(delta, _total=None):
        nonlocal source, last_publish
        await agent.handle_intervention()
        artifacts.authorize(agent)
        candidate = source + filter_.process_chunk(delta)
        artifacts.text(candidate, artifacts.SOURCE_LIMIT, "program")
        source = candidate
        if time.monotonic() - last_publish >= 0.25:
            artifacts.update(agent, tool.log, record["id"], source, "generating")
            last_publish = time.monotonic()

    try:
        async with asyncio.timeout(config["timeout_seconds"]):
            if config["generation_mode"] == "gateway":
                await gateway(config, prompt, message, chunk)
            else:
                from helpers.extension import call_extensions_async
                utility = config["stream_model"] == "utility"
                original = agent.get_utility_model() if utility else agent.get_chat_model()
                model = copy.copy(original)
                model.kwargs = copy.deepcopy(getattr(original, "kwargs", {}))
                # Retain normal model-call hooks without borrowing main-turn state.
                from langchain_core.messages import HumanMessage, SystemMessage
                limits = dict(max_tokens=config["max_output_tokens"], a0_responses_function_tools=[],
                              responses_builtin_tools=[], responses_state="local", previous_response_id=None)
                if utility:
                    call = {"model":model,"system":prompt,"message":message,"callback":chunk,"background":False}
                    await call_extensions_async("util_model_call_before", agent, call_data=call)
                    output, reasoning = await call["model"].unified_call(
                        system_message=call["system"], user_message=call["message"],
                        response_callback=call["callback"],
                        rate_limiter_callback=None if call["background"] else agent.rate_limiter_callback, **limits)
                    await call_extensions_async("util_model_call_after", agent, call_data=call, response=output)
                else:
                    call = {"model": model, "messages": [SystemMessage(content=prompt), HumanMessage(content=message)],
                            "response_callback": chunk, "reasoning_callback": None, "background": False,
                            "explicit_caching": True}
                    await call_extensions_async("chat_model_call_before", agent, call_data=call)
                    output, reasoning = await call["model"].unified_call(
                        messages=call["messages"], response_callback=call["response_callback"],
                        reasoning_callback=call["reasoning_callback"],
                        rate_limiter_callback=None if call["background"] else agent.rate_limiter_callback,
                        explicit_caching=call["explicit_caching"], **limits)
                    await call_extensions_async("chat_model_call_after", agent, call_data=call,
                                                response=output, reasoning=reasoning)
            candidate = source + filter_.finalize()
            artifacts.text(candidate, artifacts.SOURCE_LIMIT, "program")
            source = candidate
            if not source.strip():
                raise ValueError("The model returned no OpenUI program.")
            record = artifacts.update(agent, tool.log, record["id"], source, "complete")
            return record
    except BaseException as exc:
        status = "interrupted" if isinstance(exc, asyncio.CancelledError) else "failed"
        artifacts.update(agent, tool.log, record["id"], source, status)
        raise
    finally:
        ACTIVE.pop(record["id"], None)


async def gateway(config, prompt, message, callback):
    # The user configures this environment variable. Its value never reaches config/UI/logs.
    import os
    from openai import AsyncOpenAI
    if not os.environ.get("THESYS_API_KEY"):
        raise ValueError("Gateway is selected but its server-side key is not configured.")
    if not config["gateway_model"] or "/" not in config["gateway_model"]:
        raise ValueError("Choose an OpenUI Gateway provider/model in plugin settings.")
    async with AsyncOpenAI(base_url="https://api.thesys.dev/v1/embed", api_key=os.environ["THESYS_API_KEY"],
                           timeout=config["timeout_seconds"], max_retries=0) as client:
        stream = await client.chat.completions.create(
            model=config["gateway_model"], messages=[{"role": "system", "content": prompt},
                                                   {"role": "user", "content": message}],
            max_tokens=config["max_output_tokens"], stream=True,
        )
        async with stream:
            async for event in stream:
                if event.choices and event.choices[0].delta.content:
                    await callback(event.choices[0].delta.content)
