// @vitest-environment jsdom
import {beforeEach,afterEach,test,expect,vi} from 'vitest';
import {callJsonApi} from './test-api';
// @ts-expect-error shipped JavaScript
import {OpenUIHost} from '../../webui/openui-host.js';
// @ts-expect-error shipped JavaScript
import {richFrame} from '../../webui/email-workspace.js';
let host:any, workspace:any, send:any;
const prepared={token:'opaque-review',from:'owner@example.test',to:['reply@example.test'],cc:[],bcc:['private@example.test'],subject:'Reviewed subject',html:'<h1>Exact reviewed content</h1>',text:'Exact reviewed content'};
beforeEach(async()=>{
  vi.stubGlobal('getContext',()=> 'chat');send=vi.fn().mockResolvedValue(undefined);vi.stubGlobal('sendMessage',send);
  HTMLDialogElement.prototype.showModal=function(){this.open=true;};
  HTMLDialogElement.prototype.close=function(){this.open=false;this.dispatchEvent(new Event('close'));};
  callJsonApi.mockReset();callJsonApi.mockImplementation(async(_url:string, input:any)=>{
    if(input.operation==='accounts')return {accounts:[{id:'account',address:'owner@example.test',supported:true}]};
    if(input.operation==='delivery_status')return {status:'draft'};
    if(input.operation==='prepare_send')return prepared;
    if(input.operation==='send')return {...prepared,status:'sent',accepted:prepared.to,refused:[]};
    return {state_revision:1};
  });
  host=new OpenUIHost();document.body.append(host);host.context='chat';host.artifact='artifact';
  host.snapshot={id:'artifact',revision:1,state_revision:0,state:{},surface:'email',status:'complete',title:'Fallback',email_context:{account:'account',reply_to:'reply@example.test'}};
  host.frame=document.createElement('iframe');host.append(host.frame);host.renderEmailToolbar();workspace=host.emailWorkspace;
  await vi.waitFor(()=>expect(workspace.account.value).toBe('account'));
  vi.spyOn(host,'exportEmail').mockResolvedValue({html:'<h1>Original draft</h1>',text:'Original draft',subject:'Original'});
});
afterEach(()=>{host.pendingState=null;host.remove();vi.unstubAllGlobals();vi.useRealTimers();});
test('draft shows visible review, sender, recipients and real subject',()=>{
  host.receive({kind:'email-metadata',revision:1,payload:{subject:'Newsletter',previewText:'A useful preview'}});
  expect(workspace.subject.value).toBe('Newsletter');expect(workspace.preheader.textContent).toBe('A useful preview');
  expect(workspace.inputs.to.value).toBe('reply@example.test');expect(workspace.review.textContent).toBe('Review & send');
  expect(workspace.canvas.contains(host.frame)).toBe(true);
  workspace.subject.value='Edited';workspace.subject.dispatchEvent(new Event('input'));
  host.receive({kind:'email-metadata',revision:1,payload:{subject:'Newsletter'}});
  expect(workspace.subject.value).toBe('Edited');expect(host.pendingState.__mailEnvelope.subject).toBe('Edited');
});
test('review shows server prepared recipients and HTML and does not send until final click',async()=>{
  await workspace.reviewSend();
  expect(callJsonApi.mock.calls.filter(([,v]:any)=>v.operation==='send')).toHaveLength(0);
  expect(workspace.dialog.textContent).toContain('private@example.test');
  expect(workspace.dialog.textContent).toContain('Reviewed subject');
  expect(workspace.dialog.querySelector('iframe').srcdoc).toContain('Exact reviewed content');
  const final=[...workspace.dialog.querySelectorAll('button')].find((b:any)=>b.textContent==='Send email') as HTMLButtonElement;
  final.click();final.click();
  await vi.waitFor(()=>expect(workspace.badge.textContent).toBe('Sent'));
  const calls=callJsonApi.mock.calls.filter(([,v]:any)=>v.operation==='send');
  expect(calls).toHaveLength(1);expect(calls[0][1]).toEqual({context:'chat',artifact:'artifact',operation:'send',token:'opaque-review'});
  expect(workspace.review.disabled).toBe(true);expect(workspace.sentFrame.srcdoc).toContain('Exact reviewed content');
});
test('closing review leaves the email unsent',async()=>{
  await workspace.reviewSend();workspace.dialog.close();
  expect(callJsonApi.mock.calls.filter(([,v]:any)=>v.operation==='send')).toHaveLength(0);
  expect(workspace.dialog).toBeNull();
});
test('changed chat cannot present a late review or send it',async()=>{
  let resolve:any;callJsonApi.mockImplementation(()=>new Promise(r=>resolve=r));
  const pending=workspace.reviewSend();await vi.waitFor(()=>expect(resolve).toBeTypeOf('function'));
  vi.stubGlobal('getContext',()=> 'other');resolve(prepared);await pending;
  expect(workspace.dialog).toBeUndefined();
});
test('rich mailbox selection and reply use one source reference, not body text',async()=>{
  await workspace.openMailbox();
  callJsonApi.mockResolvedValue({subject:'Synthetic',sender:'sender@example.test',reply_to:'reply@example.test',body:'Private synthetic mail',html:'<b>Rich content</b>'});
  await workspace.readMail('account:42:7');
  expect(workspace.detail.querySelector('iframe').srcdoc).toContain('<b>Rich content</b>');
  const reply=[...workspace.detail.querySelectorAll('button')].find((b:any)=>b.textContent==='Draft a reply') as HTMLButtonElement;reply.click();
  await vi.waitFor(()=>expect(send).toHaveBeenCalledTimes(1));
  expect(send.mock.calls[0][0]).toMatchObject({context:'chat',attachments:[],preserveInput:true});
  expect(send.mock.calls[0][0].message).toContain('account:42:7');expect(send.mock.calls[0][0].message).not.toContain('Private synthetic mail');
});
test('a late previous mailbox read cannot replace the latest rich message',async()=>{
  await workspace.openMailbox();let earlier:any;
  callJsonApi.mockImplementation(async(_url:any,input:any)=>input.source==='first'?await new Promise(r=>earlier=r):{subject:'Latest',sender:'sender@example.test',body:'Latest body',html:'<p>Latest HTML</p>'});
  const first=workspace.readMail('first');await workspace.readMail('second');earlier({subject:'Old',body:'Old body'});await first;
  expect(workspace.detail.textContent).toContain('Latest');expect(workspace.detail.textContent).not.toContain('Old body');
});
test('rich frames block scripts, forms, remote images and parent access',()=>{
  const frame=richFrame('<h1>Message</h1>');
  expect(frame.getAttribute('sandbox')).toBe('allow-popups allow-popups-to-escape-sandbox');
  expect(frame.srcdoc).toContain("default-src 'none'");expect(frame.srcdoc).toContain("img-src data:");expect(frame.srcdoc).toContain("form-action 'none'");
});
test('unknown outcome stays locked and never automatically retries send',async()=>{
  await workspace.reviewSend();
  callJsonApi.mockImplementation(async(_url:any,input:any)=>{
    if(input.operation==='send')throw new Error('Lost connection');
    return {status:'unknown',detail:'Check your provider'};
  });
  const final=[...workspace.dialog.querySelectorAll('button')].find((b:any)=>b.textContent==='Send email') as HTMLButtonElement;final.click();
  await vi.waitFor(()=>expect(workspace.badge.textContent).toBe('Send unconfirmed'));
  expect(workspace.review.disabled).toBe(true);
  expect(callJsonApi.mock.calls.filter(([,v]:any)=>v.operation==='send')).toHaveLength(1);
});
test('sent rich and plain views never expose the earlier generated preview again',async()=>{
  workspace.receipt({...prepared,status:'sent'});
  await workspace.preview('text');expect(host.frame.hidden).toBe(true);expect(workspace.text.textContent).toBe(prepared.text);
  await workspace.preview('rich');expect(host.frame.hidden).toBe(true);expect(workspace.sentFrame.hidden).toBe(false);
  workspace.metadata({subject:'Old subject'});expect(workspace.subject.value).toBe('Reviewed subject');
});
test('moving the generated preview closes its old channel so the new document can reconnect',()=>{
  workspace.dispose();host.emailWorkspace=null;host.append(host.frame);
  const port={close:vi.fn()};host.port=port;host.ready=true;
  host.renderEmailToolbar();
  expect(port.close).toHaveBeenCalledTimes(1);expect(host.port).toBeNull();expect(host.ready).toBe(false);
});
