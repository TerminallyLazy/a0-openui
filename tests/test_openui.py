import asyncio
import copy
import json
from functools import wraps
from types import SimpleNamespace

import pytest
from agent import AgentContext, AgentConfig
from helpers import extension, plugins, tool_policy, secrets
from usr.plugins.openui.helpers import artifacts, generation
from usr.plugins.openui.helpers.config import verify_assets
from usr.plugins.openui.tools.openui import OpenUI
from usr.plugins.openui.helpers import current_answer

PROGRAM = 'root = Stack([TextContent("Hello")])'


def run_async(function):
    @wraps(function)
    def run(*args, **kwargs):
        return asyncio.run(function(*args, **kwargs))
    return run


def preview_wire(program=PROGRAM, surface="ui"):
    return json.dumps({"tool_name":"openui", "tool_args":{"surface":surface, "title":"Stream test", "summary":"Synthetic example", "program":program}}, ensure_ascii=True)


@pytest.mark.parametrize("program", [PROGRAM, 'root = Stack([TextContent("A\\nB \\\"quote\\\" 🌲 café")])'])
def test_current_answer_decodes_only_complete_string_escapes(program):
    wire = preview_wire(program)
    seen = []
    for end in range(len(wire) + 1):
        args = current_answer.PrefixReader(wire[:end]).arguments()
        if args:
            value = args['program']
            value.encode('utf-8')
            assert program.startswith(value)
            if seen: assert value.startswith(seen[-1])
            seen.append(value)
    assert seen[-1] == program
    assert any(0 < len(value) < len(program) for value in seen)


@pytest.mark.parametrize('wire', [
    '{"tool_name":"openui","tool_args":{"surface":"ui","program":"x","program":"y"}}',
    '{"tool_name":"openui","tool_args":{"surface":"ui","program":"x"}} {}',
    '{"tool_name":"parallel_tool_calls","tool_args":{"calls":[]}}',
    '{"tool_name":"openui","tool_args":{"surface":"ui","program":"x","request":"no"}}',
    '{"tool_name":"openui","tool_args":{"surface":"ui","program":"\\q"}}',
])
def test_ambiguous_or_invalid_stream_is_rejected(wire):
    # Parallel envelopes are ignored; no nested program is extracted.
    try:
        assert current_answer.PrefixReader(wire).arguments() is None
    except ValueError:
        pass


@pytest.mark.parametrize('wire', [
    '{"tool_name":"response","tool_args":{"text":"openui program"}}',
    '{"tool_name":"openui","tool_args":{"program":"root = Stack([])"}}',
    '{"thoughts":["openui tool_args program"],"tool_name":"search_engine","tool_args":{}}',
])
def test_unrelated_calls_and_unspecified_surface_fall_back(wire):
    assert current_answer.PrefixReader(wire).arguments() is None


def prepare_preview(agent, monkeypatch):
    import itertools
    from agent import LoopData
    from usr.plugins.openui.tools import openui
    monkeypatch.setattr(current_answer, 'get_config', lambda a:{'generation_mode':'agent_program'})
    monkeypatch.setattr(openui, 'get_config', lambda a:{'generation_mode':'agent_program'})
    ticks = itertools.count()
    monkeypatch.setattr(current_answer, 'now', lambda:next(ticks))
    loop = LoopData()
    agent.loop_data = loop
    return loop


@pytest.mark.parametrize('surface', ['ui','email'])
@run_async
async def test_current_answer_stream_adopts_one_artifact_and_log_without_inference(agent, monkeypatch, surface):
    loop = prepare_preview(agent, monkeypatch)
    calls = []
    async def forbidden(*a, **k): raise AssertionError('No extra model call')
    monkeypatch.setattr(generation, 'generate', forbidden)
    monkeypatch.setattr(agent, 'get_chat_model', lambda:pytest.fail('No extra model call'))
    monkeypatch.setattr(agent, 'hist_add_tool_result', lambda *a,**k:calls.append(k))
    wire = preview_wire(surface=surface)
    for end in range(1, len(wire) + 1):
        current_answer.preview(agent, loop, wire[:end])
    pending = current_answer.state(agent, loop)
    record = artifacts.snapshot(agent.context.id, pending['id'])
    assert record['status'] == 'generating' and record['surface'] == surface
    with pytest.raises(ValueError):
        artifacts.save_state(agent.context.id, record['id'], record['revision'], 0, {'x':'no'})
    args = json.loads(wire)['tool_args']
    tool = OpenUI(agent=agent, name='openui', method=None, args=args, message='', loop_data=loop)
    await tool.before_execution()
    assert tool.log is pending['log']
    result = await tool.execute(**args)
    await tool.after_execution(result)
    current_answer.finish(agent, loop)
    final = artifacts.snapshot(agent.context.id, record['id'])
    assert final['status'] == 'complete' and final['source'] == PROGRAM and final['title'] == args['title']
    assert len(agent.context.data[artifacts.KEY]) == 1
    assert len([log for log in agent.context.log.logs if (log.kvps or {}).get('_tool_name') == 'openui']) == 1
    assert len(calls) == 1 and calls[0]['openui_artifact'] == record['id']
    assert not current_answer.ACTIVE


@run_async
async def test_current_answer_masks_decoded_secret_at_every_prefix(agent, monkeypatch):
    loop = prepare_preview(agent, monkeypatch)
    class FakeSecrets:
        def load_secrets(self): return {'demo':'sensitive-secret'}
        def mask_values(self, value): return value.replace('sensitive-secret', 'MASKED')
    monkeypatch.setattr(secrets, 'get_secrets_manager', lambda *a:FakeSecrets())
    wire = preview_wire('root = Stack([TextContent("sensitive-secret")])')
    # Also exercise the escaped wire spelling of a secret's first character.
    wire = wire.replace('sensitive', '\\u0073ensitive')
    for end in range(len(wire) + 1):
        current_answer.preview(agent, loop, wire[:end])
        pending = current_answer.state(agent, loop)
        if pending and pending.get('id'):
            safe = pending['safe']
            assert 'sensitive' not in safe
            assert not safe.endswith('"s')
    current_answer.finish(agent, loop)
    assert artifacts.snapshot(agent.context.id, pending['id'])['status'] == 'interrupted'


@pytest.mark.parametrize('failure', ['malformed','multi','limit','revoked','cancel','tool_validation'])
@run_async
async def test_current_answer_failed_or_cancelled_previews_stay_inert(agent, monkeypatch, failure):
    loop = prepare_preview(agent, monkeypatch)
    wire = preview_wire()
    if failure == 'cancel':
        ready = asyncio.Event()
        async def stream_task():
            current_answer.preview(agent, loop, wire[:-8])
            ready.set()
            await asyncio.Event().wait()
        task = asyncio.create_task(stream_task())
        await ready.wait()
        task.cancel()
        with pytest.raises(asyncio.CancelledError): await task
        await asyncio.sleep(0)
    else:
        current_answer.preview(agent, loop, wire[:-8])
        if failure == 'malformed': current_answer.preview(agent, loop, wire + ' bad')
        if failure == 'multi': current_answer.preview(agent, loop, '{"tool_name":"parallel_tool_calls","tool_args":{"calls":[]}}')
        if failure == 'limit': current_answer.preview(agent, loop, preview_wire('x' * 65537))
        if failure == 'revoked':
            monkeypatch.setattr(plugins, 'get_enabled_plugins', lambda a:[])
            current_answer.preview(agent, loop, wire)
        if failure == 'tool_validation':
            args = json.loads(wire)['tool_args']
            args['unknown'] = True
            tool = OpenUI(agent=agent, name='openui', method=None, args=args, message='', loop_data=loop)
            tool.log = tool.get_log_object()
            with pytest.raises(ValueError): await tool.execute(**args)
            current_answer.finish(agent, loop)
    record = next(iter(agent.context.data[artifacts.KEY].values()))
    assert record['status'] == 'interrupted'
    assert not current_answer.ACTIVE


@pytest.mark.parametrize('commentary', [False, True])
@run_async
async def test_native_argument_deltas_reach_preview_with_commentary(agent, monkeypatch, commentary):
    from helpers.litellm_transport import ResponsesEventParser
    loop = prepare_preview(agent, monkeypatch)
    parser = ResponsesEventParser()
    args = json.loads(preview_wire())['tool_args']
    if commentary:
        parser.parse({'type':'response.output_item.added','output_index':0,'item':{'id':'comment','type':'message','phase':'commentary'}})
        parser.parse({'type':'response.output_text.delta','item_id':'comment','output_index':0,'delta':'Preparing the dashboard.'})
    parser.parse({'type':'response.output_item.added','output_index':1,'item':{'id':'call-1','type':'function_call','call_id':'call-1','name':'openui','arguments':''}})
    full = ''
    for delta in json.dumps(args):
        parsed = parser.parse({'type':'response.function_call_arguments.delta','item_id':'call-1','output_index':1,'delta':delta})
        full += parsed.get('response_delta','')
        current_answer.preview(agent, loop, parsed.get('response_preview', full))
    pending = current_answer.state(agent, loop)
    assert pending['safe'] == PROGRAM
    assert artifacts.snapshot(agent.context.id, pending['id'])['status'] == 'generating'
    current_answer.finish(agent, loop)




@pytest.fixture
def agent(monkeypatch):
    monkeypatch.setattr(extension, "call_extensions_sync", lambda *a, **k: None)
    monkeypatch.setattr(plugins, "get_enabled_plugins", lambda agent: ["openui"])
    monkeypatch.setattr(tool_policy, "ensure_tool_allowed", lambda *a: None)
    context = AgentContext(AgentConfig(mcp_servers="", profile="default"), id="openui-test-context")
    monkeypatch.setattr(artifacts, "persist", lambda context: None)
    yield context.agent0
    AgentContext._contexts.pop(context.id, None)


def make(agent, source=PROGRAM):
    log = agent.context.log.log(type="tool", content="", _tool_name="openui")
    record = artifacts.create(agent, log, "Sample", "Synthetic example", source)
    return log, record


def test_release_assets_are_complete():
    info = verify_assets()
    assert info["library_id"] == "a0-openui@3"
    assert info["libraries"]["ui"]["compatible"] == ["912831499155286ffb92432c31227d49fddd1dcaa0d56dd61f8e670e7bd47d32", "d47d2f0867c161496ad9a049f16cc19b638ff41448b8e38ebe09cd3e2f906ae5"]


def test_install_validation_is_idempotent_through_installer():
    from plugins._plugin_installer.helpers.install import run_install_hook
    run_install_hook('openui')
    run_install_hook('openui')


def test_email_records_use_the_separate_contract(agent):
    log=agent.context.log.log(type='tool',content='',_tool_name='openui')
    record=artifacts.create(agent,log,'Email','Draft','root = EmailTemplate("Sample", "Preview", [EmailText("Sample")])',surface='email')
    assert record['library_id']=='a0-openui-email@1'
    assert log.kvps['openui_surface']=='email'


def test_malformed_import_is_rejected_before_rendering(agent):
    _, record=make(agent)
    del agent.context.data[artifacts.KEY][record['id']]['source']
    with pytest.raises(ValueError): artifacts.snapshot(agent.context.id,record['id'])


def test_program_survives_both_log_limits_and_completion(agent):
    program = 'root = Stack([TextContent("' + 'x' * 20000 + '")])'
    log, record = make(agent, program)
    log.update(content="Rendered UI.")
    snapshot = artifacts.snapshot(agent.context.id, record["id"])
    assert snapshot["source"] == program
    assert "x" * 100 not in json.dumps(log.output())
    assert len(json.dumps(log.output())) < 5000


def test_unknown_context_does_not_create_a_chat(agent):
    before = set(AgentContext._contexts)
    with pytest.raises(LookupError):
        artifacts.snapshot("unknown", "absent")
    assert set(AgentContext._contexts) == before


def test_cross_context_artifact_is_rejected(agent):
    _, record = make(agent)
    with pytest.raises(LookupError):
        artifacts.snapshot("another-chat", record["id"])


def test_unlinked_artifact_cannot_be_read(agent):
    log, record = make(agent)
    log.update(openui_artifact="different")
    with pytest.raises(LookupError):
        artifacts.snapshot(agent.context.id, record["id"])


def test_profile_changes_revoke_interaction(agent):
    _, record = make(agent)
    agent.config.profile = "different"
    with pytest.raises(PermissionError):
        artifacts.snapshot(agent.context.id, record["id"])


def test_disabled_plugin_rejects_read_and_write(agent, monkeypatch):
    _, record = make(agent)
    monkeypatch.setattr(plugins, "get_enabled_plugins", lambda agent: [])
    with pytest.raises(PermissionError):
        artifacts.snapshot(agent.context.id, record["id"])
    with pytest.raises(PermissionError):
        artifacts.save_state(agent.context.id, record["id"], 1, 0, {})


def test_tool_policy_is_checked(agent, monkeypatch):
    def reject(*args): raise PermissionError("blocked")
    monkeypatch.setattr(tool_policy, "ensure_tool_allowed", reject)
    with pytest.raises(PermissionError): make(agent)


def test_state_revisions_prevent_lost_updates(agent):
    _, record = make(agent)
    assert artifacts.save_state(agent.context.id, record["id"], 1, 0, {"name":"One"}) == {"state_revision":1}
    with pytest.raises(ValueError):
        artifacts.save_state(agent.context.id, record["id"], 1, 0, {"name":"Two"})
    assert artifacts.snapshot(agent.context.id, record["id"])["state"] == {"name":"One"}


@pytest.mark.parametrize("value", [float('nan'), {"__proto__":{}}, {'x':'a' * 9000}, [[[[]]]] * 2001])
def test_invalid_state_is_rejected_without_overwriting(agent, value):
    _, record = make(agent)
    with pytest.raises(ValueError):
        artifacts.save_state(agent.context.id, record["id"], 1, 0, value)
    assert artifacts.snapshot(agent.context.id, record["id"])["state"] == {}


def test_source_over_limit_is_not_truncated(agent):
    with pytest.raises(ValueError): make(agent, "x" * 65537)
    assert not agent.context.data.get(artifacts.KEY)


def test_chat_owned_artifact_serialization_and_restore(agent):
    _, record = make(agent)
    encoded = json.dumps({k:v for k,v in agent.context.data.items() if not k.startswith('_')})
    agent.context.data = json.loads(encoded)
    assert artifacts.snapshot(agent.context.id, record["id"])["source"] == PROGRAM


def test_real_chat_export_import_retains_program_and_form_state(agent, monkeypatch):
    from helpers import persist_chat
    monkeypatch.setattr(persist_chat, "initialize_agent", lambda **kwargs: agent.config)
    _, record = make(agent)
    artifacts.save_state(agent.context.id, record['id'], 1, 0, {'request':'kept'})
    imported = persist_chat.load_json_chats([persist_chat.export_json_chat(agent.context)])
    try:
        restored = artifacts.snapshot(imported[0], record['id'])
        assert restored['source'] == PROGRAM and restored['state'] == {'request':'kept'}
        assert imported[0] != agent.context.id
    finally:
        for identity in imported: AgentContext._contexts.pop(identity, None)


def test_deleted_context_revokes_artifact_access(agent):
    _, record = make(agent)
    AgentContext._contexts.pop(agent.context.id)
    with pytest.raises(LookupError): artifacts.snapshot(agent.context.id, record['id'])


def test_api_handlers_retain_framework_auth_and_csrf():
    from usr.plugins.openui.api.artifact import Artifact
    from usr.plugins.openui.api.state import State
    for handler in (Artifact, State):
        assert handler.requires_auth() and handler.requires_csrf()
        assert handler.get_methods() == ['POST']


@pytest.mark.parametrize('failure', ['timeout','cancel','limit'])
@run_async
async def test_stream_failure_preserves_bounded_partial_source(agent, monkeypatch, failure):
    async def hooks(*a,**k): pass
    async def intervene(*a,**k): pass
    async def unified_call(**kwargs):
        await kwargs['response_callback'](PROGRAM)
        if failure == 'timeout': raise TimeoutError('Synthetic timeout')
        if failure == 'cancel': raise asyncio.CancelledError()
        await kwargs['response_callback']('x' * 65537)
    monkeypatch.setattr(extension,'call_extensions_async',hooks)
    monkeypatch.setattr(agent,'handle_intervention',intervene)
    monkeypatch.setattr(agent,'get_chat_model',lambda:SimpleNamespace(unified_call=unified_call))
    log=agent.context.log.log(type='tool',content='',_tool_name='openui')
    tool=SimpleNamespace(agent=agent,log=log,title='Interrupted',summary='Synthetic')
    config={'generation_mode':'agent_stream','stream_model':'main','max_output_tokens':256,'timeout_seconds':10}
    with pytest.raises((TimeoutError, asyncio.CancelledError, ValueError)):
        await generation.generate(tool,config,'Test',{})
    record=artifacts.snapshot(agent.context.id,log.kvps['openui_artifact'])
    assert record['source'] == PROGRAM
    assert record['status'] == ('interrupted' if failure == 'cancel' else 'failed')
    assert not generation.ACTIVE


def test_restored_generation_is_interrupted(agent):
    log = agent.context.log.log(type="tool", content="", _tool_name="openui")
    record = artifacts.create(agent, log, "Sample", "Pending", PROGRAM, status="generating")
    agent.context.data[artifacts.KEY][record["id"]]["epoch"] = "previous-process"
    assert artifacts.snapshot(agent.context.id, record["id"])["status"] == "interrupted"
    with pytest.raises(ValueError):
        artifacts.save_state(agent.context.id, record["id"], 2, 0, {})


@run_async
async def test_normal_tool_completion_inserts_history_once(agent, monkeypatch):
    from usr.plugins.openui.tools import openui
    monkeypatch.setattr(openui, "get_config", lambda agent:{"generation_mode":"agent_program"})
    calls=[]
    monkeypatch.setattr(agent, "hist_add_tool_result", lambda *a, **k: calls.append((a,k)))
    tool=OpenUI(agent=agent, name="openui", method=None, args={}, message="", loop_data=None)
    await tool.before_execution()
    result=await tool.execute(title="Demo", summary="A demo.", program=PROGRAM)
    await tool.after_execution(result)
    assert len(calls)==1 and result.break_loop is False
    assert artifacts.snapshot(agent.context.id, result.additional["openui_artifact"])["source"]==PROGRAM
    assert "A demo." in tool.log.content


@run_async
async def test_streaming_masks_split_secrets_and_preserves_main_state(agent, monkeypatch):
    class FakeSecrets:
        def load_secrets(self): return {"synthetic":"split-test-secret"}
        def mask_values(self, s): return s.replace("split-test-secret", "MASKED")
    monkeypatch.setattr(secrets, "get_secrets_manager", lambda context=None:FakeSecrets())
    async def hooks(*a,**k): pass
    monkeypatch.setattr(extension, "call_extensions_async", hooks)
    async def unified_call(**kwargs):
        for c in 'root = Stack([TextContent("split-test-secret")])':
            await kwargs["response_callback"](c, "")
        return "ignored", ""
    async def intervene(*a,**k): pass
    monkeypatch.setattr(agent,"handle_intervention",intervene)
    monkeypatch.setattr(agent,"get_chat_model",lambda:SimpleNamespace(unified_call=unified_call))
    agent.data['responses_state']={'id':'main-response'}
    before=copy.deepcopy(agent.data)
    log=agent.context.log.log(type="tool",content="",_tool_name="openui")
    tool=SimpleNamespace(agent=agent,log=log,title="Demo",summary="Test")
    config={"generation_mode":"agent_stream","stream_model":"main","max_output_tokens":256,"timeout_seconds":10}
    result=await generation.generate(tool,config,"Make a card",{})
    assert 'split-test-secret' not in result['source']
    assert result['status']=='complete'
    assert agent.data==before
    assert not generation.ACTIVE


@run_async
async def test_gateway_is_never_called_in_default_mode(agent, monkeypatch):
    from usr.plugins.openui.tools import openui
    monkeypatch.setattr(openui,"get_config",lambda agent:{"generation_mode":"agent_program"})
    async def forbidden(*a,**k): raise AssertionError("Unexpected inference")
    monkeypatch.setattr(generation,"generate",forbidden)
    tool=OpenUI(agent=agent,name="openui",method=None,args={},message="",loop_data=None)
    tool.log=agent.context.log.log(type="tool",content="",_tool_name="openui")
    assert not (await tool.execute(program=PROGRAM)).break_loop


@pytest.mark.parametrize('choice',['main','utility'])
@run_async
async def test_stream_uses_matching_hooks_without_mutating_shared_wrapper(agent,monkeypatch,choice):
    events=[]
    async def hook(name,agent,call_data,**kwargs):
        events.append(name)
        call_data['model'].kwargs['hook_marker']=True
    async def intervene(*a,**k):pass
    async def unified_call(**kwargs):
        assert kwargs['previous_response_id'] is None
        assert kwargs['responses_state']=='local'
        await kwargs['response_callback'](PROGRAM,'')
        return PROGRAM,''
    wrapper=SimpleNamespace(unified_call=unified_call,kwargs={'nested':{'kept':True}})
    monkeypatch.setattr(extension,'call_extensions_async',hook)
    monkeypatch.setattr(agent,'handle_intervention',intervene)
    monkeypatch.setattr(agent,'get_chat_model',lambda:wrapper)
    monkeypatch.setattr(agent,'get_utility_model',lambda:wrapper)
    log=agent.context.log.log(type='tool',content='',_tool_name='openui')
    tool=SimpleNamespace(agent=agent,log=log,title='Test',summary='Test')
    await generation.generate(tool,{'generation_mode':'agent_stream','stream_model':choice,'max_output_tokens':256,'timeout_seconds':10},'Test',{})
    prefix='util' if choice=='utility' else 'chat'
    assert events==[prefix+'_model_call_before',prefix+'_model_call_after']
    assert wrapper.kwargs=={'nested':{'kept':True}}


@pytest.mark.parametrize('mode', ['agent_program', 'agent_stream', 'gateway'])
@run_async
async def test_automatic_guidance_reaches_text_and_native_tools_and_respects_policy(agent, monkeypatch, mode):
    from extensions.python.system_prompt import _11_tools_prompt
    from helpers import responses_tools, subagents, files
    from usr.plugins.openui.extensions.python.system_prompt import _09_openui_config
    from usr.plugins.openui.helpers.config import ROOT

    original_paths = subagents.get_paths
    monkeypatch.setattr(subagents, 'get_paths', lambda a, *parts, **kw:
        [str(ROOT / 'prompts'), files.get_abs_path('prompts')] if parts == ('prompts',) else original_paths(a, *parts, **kw))
    monkeypatch.setattr(_09_openui_config, 'get_config', lambda a: {'generation_mode': mode})
    monkeypatch.setattr('plugins._model_config.helpers.model_config.get_chat_model_config', lambda a: {'vision':False})
    monkeypatch.setattr('plugins._model_config.helpers.model_config.get_vision_model_config', lambda a: None)
    monkeypatch.setattr(responses_tools, '_mcp_tools', lambda a: [])
    policy = {'mode':'custom', 'default':'allow', 'mcp_default':'allow', 'allowed':[], 'blocked':[]}
    monkeypatch.setattr(tool_policy, 'get_policy', lambda a: policy)
    await _09_openui_config.OpenUIConfig(agent).execute()
    prompt = await _11_tools_prompt.build_prompt(agent)
    native, _ = responses_tools.build_responses_function_tools(agent)
    description = next(item['description'] for item in native if item['name'] == 'openui')
    for rendered in [prompt, description]:
        assert 'Automatically use this tool' in rendered
        assert 'Keep greetings, acknowledgments, single facts' in rendered
        assert '{{openui_' not in rendered
        assert ('Worked compositions' in rendered) == (mode == 'agent_program')
    policy['blocked'] = ['plugin:openui:openui']
    assert 'Automatically use this tool' not in await _11_tools_prompt.build_prompt(agent)
    blocked, _ = responses_tools.build_responses_function_tools(agent)
    assert not any(item['name'] == 'openui' for item in blocked)
