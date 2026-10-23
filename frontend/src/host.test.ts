// @vitest-environment jsdom
import {beforeEach,afterEach,test,expect,vi} from 'vitest';
import {callJsonApi} from './test-api';
import {toastFrontendWarning,copyToClipboard} from './test-notifications';
// The shipped JavaScript module is exercised directly with only network/toast seams replaced.
// @ts-expect-error JavaScript host has no generated declarations.
import {OpenUIHost} from '../../webui/openui-host.js';
const record = () => ({id:'artifact',revision:1,state_revision:0,state:{},status:'complete',spec_digest:'test',source:'root = Stack([])'});
let context:string;
let send:any;
let host:any;
beforeEach(() => {
  context='chat';send=vi.fn().mockResolvedValue(undefined);
  vi.stubGlobal('getContext',()=>context);vi.stubGlobal('sendMessage',send);
  callJsonApi.mockReset();toastFrontendWarning.mockReset();
  copyToClipboard.mockReset();
  callJsonApi.mockImplementation(async (url:string) => url.endsWith('/state') ? {state_revision:1} : {artifact:record()});
  host=new OpenUIHost();document.body.append(host);
  host.context='chat';host.artifact='artifact';host.snapshot=record();
});
afterEach(() => {host.pendingState=null;host.remove();vi.unstubAllGlobals();vi.useRealTimers();});
const payload = {event:{type:'continue_conversation',humanFriendlyMessage:'Review this',formName:'request',formState:{request:'Synthetic'}},state:{request:'Synthetic'}};
test('form actions use the normal send path with correct context and no composer attachments',async()=>{
  await host.action(payload);
  expect(send).toHaveBeenCalledTimes(1);
  expect(send.mock.calls[0][0]).toMatchObject({context:'chat',attachments:[],preserveInput:true});
  expect(send.mock.calls[0][0].message).toContain('Synthetic');
  expect(send.mock.calls[0][0].message).toContain('artifact');
});
test('rapid duplicate submissions are coalesced, then an intentional retry is possible',async()=>{
  vi.useFakeTimers();await host.action(payload);await host.action(payload);
  expect(send).toHaveBeenCalledTimes(1);
  vi.advanceTimersByTime(1600);await host.action(payload);
  expect(send).toHaveBeenCalledTimes(2);
});
test('switching chats while an artifact is fetched never sends a message',async()=>{
  let release:any;
  callJsonApi.mockImplementation(async(url:string)=>url.endsWith('/state')?{state_revision:1}:await new Promise(resolve=>release=resolve));
  const action=host.action(payload);
  await vi.waitFor(()=>expect(release).toBeTypeOf('function'));
  context='other';release({artifact:record()});await action;
  expect(send).not.toHaveBeenCalled();
});
test('reconnecting a host during an action invalidates that old frame action',async()=>{
  let release:any;
  callJsonApi.mockImplementation(async(url:string)=>url.endsWith('/state')?{state_revision:1}:await new Promise(resolve=>release=resolve));
  const action=host.action(payload);
  await vi.waitFor(()=>expect(release).toBeTypeOf('function'));
  // Replaying the same chat creates a new iframe even if the artifact id is unchanged.
  host.frame=document.createElement('iframe');
  release({artifact:record()});await action;
  expect(send).not.toHaveBeenCalled();
});
test('a changed source revision invalidates an old button action',async()=>{
  callJsonApi.mockImplementation(async(url:string)=>url.endsWith('/state')?{state_revision:1}:{artifact:{...record(),revision:2}});
  await host.action(payload);expect(send).not.toHaveBeenCalled();
});
test('state save rejection prevents action dispatch',async()=>{
  callJsonApi.mockRejectedValueOnce(new Error('Stale state'));
  await expect(host.action(payload)).rejects.toThrow('Stale state');expect(send).not.toHaveBeenCalled();
});
test('wrong revision and non-conversation actions are ignored',async()=>{
  host.receive({kind:'action',revision:99,payload});
  await host.action({...payload,event:{type:'tool',humanFriendlyMessage:'Run shell'}});
  expect(send).not.toHaveBeenCalled();expect(callJsonApi).not.toHaveBeenCalled();
});
test('detached hosts ignore late snapshots and close their communication channel',async()=>{
  const frame=document.createElement('iframe');host.frame=frame;host.append(frame);
  const port={postMessage:vi.fn(),close:vi.fn()};host.port=port;
  host.remove();expect(port.close).toHaveBeenCalledTimes(1);expect(frame.isConnected).toBe(false);
  host.receive({kind:'action',revision:1,payload});expect(send).not.toHaveBeenCalled();
});
test('chat replay reconnects a saved artifact with the correct visual renderer',async()=>{
  host.wanted=1;
  host.remove();document.body.append(host);
  await vi.waitFor(()=>expect(host.frame.getAttribute('src')).toContain('/visual.html'));
  expect(callJsonApi).toHaveBeenCalledWith('/api/plugins/openui/artifact',{context:'chat',artifact:'artifact'});
  expect(host.snapshot.id).toBe('artifact');
});
test('late responses from a detached frame cannot block or overwrite its replacement',async()=>{
  const pending:any[]=[];
  callJsonApi.mockImplementation(()=>new Promise(resolve=>pending.push(resolve)));
  host.snapshot=null;host.wanted=1;host.start();
  const oldFrame=host.frame;
  host.remove();document.body.append(host);
  expect(pending).toHaveLength(2);expect(host.frame).not.toBe(oldFrame);
  pending[0]({artifact:record()});await Promise.resolve();await Promise.resolve();
  expect(host.loading).toBe(true);expect(host.snapshot).toBeNull();
  pending[1]({artifact:record()});
  await vi.waitFor(()=>expect(host.frame.getAttribute('src')).toContain('/visual.html'));
  expect(host.snapshot.id).toBe('artifact');expect(host.loading).toBe(false);
});
test('reusing a host for another artifact discards its previous snapshot and state',async()=>{
  host.pendingState={private:'old values'};
  callJsonApi.mockResolvedValue({artifact:{...record(),id:'other'}});
  host.configure('chat','other',1);
  await vi.waitFor(()=>expect(host.snapshot?.id).toBe('other'));
  expect(host.pendingState).toBeNull();
  expect(host.frame.getAttribute('src')).toContain('/visual.html');
});
test('an in-flight save advances the revision even when polling replaces the snapshot',async()=>{
  let release:any;callJsonApi.mockImplementation(()=>new Promise(resolve=>release=resolve));
  host.pendingState={request:'kept'};const saving=host.flushState();
  host.snapshot=record();release({state_revision:1});await saving;
  expect(host.snapshot.state_revision).toBe(1);expect(host.snapshot.state).toEqual({request:'kept'});
});
test('a completed save cannot copy state into a different artifact at the same revision',async()=>{
  let release:any;callJsonApi.mockImplementation(()=>new Promise(resolve=>release=resolve));
  host.pendingState={request:'old'};const saving=host.flushState();
  host.snapshot={...record(),id:'other'};release({state_revision:1});await saving;
  expect(host.snapshot.state_revision).toBe(0);expect(host.snapshot.state).toEqual({});
});
test('library mismatch yields a fallback notification',()=>{
  host.port={postMessage:vi.fn(),close:vi.fn()};host.ready=true;host.contracts={ui:{spec_digest:'different'}};host.render();
  expect(toastFrontendWarning).toHaveBeenCalledTimes(1);expect(host.port.postMessage).not.toHaveBeenCalled();
});
test('email export resolves only after the matching frame result is copied',async()=>{
  host.snapshot={...record(),surface:'email'};host.ready=true;
  host.port={postMessage:vi.fn(),close:vi.fn()};
  const pending=host.exportEmail('copy');
  host.receive({kind:'email-export',revision:99,payload:{html:'wrong'}});
  expect(copyToClipboard).not.toHaveBeenCalled();
  host.receive({kind:'email-export',revision:1,payload:{html:'<!doctype html><p>draft</p>',subject:'Draft',text:'draft'}});
  await pending;expect(copyToClipboard).toHaveBeenCalledWith('<!doctype html><p>draft</p>');
});
test('user-clicked web links open separately without an opener or referrer',()=>{
  const open=vi.spyOn(window,'open').mockReturnValue(null);
  host.receive({kind:'open-link',revision:1,payload:'https://example.com/dashboard'});
  expect(open).toHaveBeenCalledWith('https://example.com/dashboard','_blank','noopener,noreferrer');
  open.mockRestore();
});
test('links cannot execute scripts, expose URL credentials or use stale artifacts',()=>{
  const open=vi.spyOn(window,'open').mockReturnValue(null);
  for (const payload of ['javascript:alert(1)','data:text/html,test','file:///tmp/private','/relative','https://user:secret@example.com/'])
    host.receive({kind:'open-link',revision:1,payload});
  host.receive({kind:'open-link',revision:99,payload:'https://example.com/'});
  host.snapshot.status='generating';
  host.receive({kind:'open-link',revision:1,payload:'https://example.com/'});
  expect(open).not.toHaveBeenCalled();open.mockRestore();
});
test('an explicitly compatible saved library contract still renders',()=>{
  host.port={postMessage:vi.fn(),close:vi.fn()};host.ready=true;
  host.contracts={ui:{spec_digest:'new',compatible:['test']}};host.render();
  expect(host.port.postMessage).toHaveBeenCalledWith(expect.objectContaining({kind:'snapshot'}));
  expect(toastFrontendWarning).not.toHaveBeenCalled();
});
