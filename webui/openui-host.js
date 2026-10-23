import { callJsonApi } from '/js/api.js';
import { toastFrontendWarning } from '/components/notifications/notification-store.js';
import {copyToClipboard} from '/components/messages/action-buttons/simple-action-buttons.js';

import {EmailWorkspace} from './email-workspace.js';

const LIMIT = 8192;
function bounded(value) {
  const data = JSON.stringify(value);
  if (new TextEncoder().encode(data).length > LIMIT) throw new Error('The form is too large to send.');
  return JSON.parse(data);
}

export class OpenUIHost extends HTMLElement {
  configure(context, artifact, revision) {
    if (this.context && (context !== this.context || artifact !== this.artifact)) this.dispose();
    this.context = context;
    this.artifact = artifact;
    this.wanted = Number(revision) || 1;
    if (this.isConnected) this.start();
  }
  connectedCallback() { if (this.context) this.start(); }
  disconnectedCallback() { this.flushState().catch(() => {}); this.dispose(); }
  start() {
    if (!this.frame) {
      this.frame = document.createElement('iframe');
      this.frame.title = 'Interactive answer';
      this.frame.setAttribute('sandbox', 'allow-scripts');
      this.frame.referrerPolicy = 'no-referrer';
      this.frame.setAttribute('credentialless','');
      this.frame.style.cssText = 'display:block;width:100%;height:180px;border:0;border-radius:10px;';
      this.frame.src = '/plugins/openui/webui/renderer/index.html';
      this.connection = (event) => {
        if (event.source !== this.frame?.contentWindow || event.origin !== 'null' || event.data?.kind !== 'openui-ready' || this.port) return;
        const channel = new MessageChannel();
        this.port = channel.port1;
        this.port.onmessage = ({data}) => this.receive(data);
        this.port.start();
        this.frame.contentWindow.postMessage({kind: 'openui-connect', version: 1}, '*', [channel.port2]);
      };
      window.addEventListener('message', this.connection);
      this.appendChild(this.frame);
      this.themeObserver = new MutationObserver(() => this.render());
      this.themeObserver.observe(document.documentElement, {attributes: true, attributeFilter: ['class', 'data-theme']});
      this.themeObserver.observe(document.body, {attributes: true, attributeFilter: ['class', 'data-theme']});
      const step=this.closest('.process-step');
      if (step) {
        const syncVisibility=()=>{this.hidden=!step.classList.contains('expanded');};
        this.visibilityObserver=new MutationObserver(syncVisibility);
        this.visibilityObserver.observe(step,{attributes:true,attributeFilter:['class']});
        syncVisibility();
      }
    }
    if (!this.snapshot || this.snapshot.revision < this.wanted) this.load();
  }
  valid() { return this.isConnected && globalThis.getContext?.() === this.context; }
  async load() {
    if (this.loading || !this.valid()) return;
    this.loading = true;
    const frame = this.frame;
    try {
      const result = await callJsonApi('/api/plugins/openui/artifact', {context: this.context, artifact: this.artifact});
      if (!this.valid() || this.frame !== frame || result.artifact?.id !== this.artifact) return;
      if (this.snapshot && result.artifact.revision < this.snapshot.revision) return;
      this.snapshot = result.artifact;
      const renderer=this.snapshot.surface==='email'?'index.html':'visual.html';
      const target='/plugins/openui/webui/renderer/'+renderer;
      if(this.frame.getAttribute('src')!==target){
        this.port?.close();this.port=null;this.ready=false;this.frame.src=target;
      }
      this.render();
    } catch (error) { if(this.frame===frame)this.report('The interactive answer is unavailable. Its text summary is still available.'); }
    finally { if(this.frame===frame)this.loading = false; }
    if (this.frame===frame && this.valid() && this.snapshot && this.snapshot.revision < this.wanted)
      this.retry = setTimeout(() => this.load(), 250);
  }
  render() {
    if (!this.port || !this.ready || !this.snapshot || !this.valid()) return;
    const contract=this.contracts?.[this.snapshot.surface || 'ui'];
    if (![contract?.spec_digest,...(contract?.compatible||[])].includes(this.snapshot.spec_digest)) {
      this.report('This answer uses a different OpenUI library. Use its summary or ask the agent to regenerate it.');
      return;
    }
    this.renderEmailToolbar();
    if(!this.port || !this.ready)return;
    const dark = document.body.classList.contains('dark-mode') || document.documentElement.classList.contains('dark') ||
      document.documentElement.dataset.theme === 'dark' || document.body.dataset.theme === 'dark';
    this.port.postMessage({kind:'snapshot', payload:{...this.snapshot, dark}});
  }
  renderEmailToolbar() {
    if (this.snapshot?.surface !== 'email') { this.emailWorkspace?.dispose(); this.emailWorkspace=null; return; }
    if (!this.emailWorkspace) this.emailWorkspace=new EmailWorkspace(this);
    this.emailWorkspace.review.disabled=this.snapshot.status!=='complete'||!!this.emailWorkspace.received;
  }
  async mailRequest(operation,params={}) {
    if(!this.valid())throw new Error('Reopen this email draft first.');
    return callJsonApi('/api/plugins/openui/mail',{context:this.context,artifact:this.artifact,operation,...params});
  }
  receive(data) {
    if (!this.valid() || !data || typeof data !== 'object') return;
    if (data.kind === 'ready') { this.ready = true; this.contracts = data.payload?.contracts; this.render(); return; }
    if (data.kind === 'resize' && Number.isFinite(data.payload)) {
      this.frame.style.height = Math.max(100, Math.min(1200, data.payload)) + 'px'; return;
    }
    if (!this.snapshot || data.revision !== this.snapshot.revision) return;
    if (data.kind === 'error') {
      if(this.exportRequest){this.exportRequest.reject(new Error('Email export failed.'));this.exportRequest=null;clearTimeout(this.exportTimer);}
      this.errors = Array.isArray(data.payload) ? data.payload.slice(0,8) : [];
      this.report('Part of this interactive answer could not render. Use Repair to ask the agent to correct it.');
    }
    if (this.snapshot.status !== 'complete') return;
    if (data.kind === 'email-metadata' && this.snapshot.surface === 'email') {
      this.emailWorkspace?.metadata(data.payload);
      return;
    }
    if (data.kind === 'open-link') {
      try {
        if (typeof data.payload !== 'string' || data.payload.length > 2048) throw new Error();
        const url=new URL(data.payload);
        if (!['https:','http:'].includes(url.protocol) || url.username || url.password) throw new Error();
        window.open(url.href, '_blank', 'noopener,noreferrer');
      } catch { this.report('Only complete HTTP or HTTPS links can be opened from this preview.'); }
      return;
    }
    if (data.kind === 'email-export' && this.exportRequest?.revision === data.revision) {
      const request=this.exportRequest;this.exportRequest=null;clearTimeout(this.exportTimer);
      const payload=this.emailWorkspace?.received?.html ? this.emailWorkspace.received : data.payload;
      if (!payload || typeof payload.html !== 'string' || new TextEncoder().encode(payload.html).length>1048576) {request.reject(new Error('Invalid email export.'));return;}
      let copied;
      if (request.mode === 'copy') copied=copyToClipboard(payload.html);
      if (request.mode === 'subject') copied=copyToClipboard(String(this.emailWorkspace?.subject.value||payload.subject||'').slice(0,500));
      if (request.mode === 'text') copied=copyToClipboard(String(payload.text||'').slice(0,1048576));
      if (request.mode === 'download') {
        const url=URL.createObjectURL(new Blob([payload.html],{type:'text/html'}));
        const link=document.createElement('a');link.href=url;
        link.download=(this.snapshot.title.replace(/[^a-z0-9 _-]/gi,'').slice(0,70)||'email-draft')+'.html';
        link.click();setTimeout(()=>URL.revokeObjectURL(url),1000);
      }
      Promise.resolve(copied).then(()=>request.resolve(request.mode==='payload'?payload:undefined),request.reject);
      return;
    }
    if (data.kind === 'state') {
      try { this.pendingState = bounded({...data.payload, ...(this.snapshot.surface==='email'?{__mailEnvelope:(this.pendingState||this.snapshot.state).__mailEnvelope||{}}:{})}); } catch (error) { this.report(error.message); return; }
      clearTimeout(this.stateTimer);
      this.stateTimer = setTimeout(() => this.flushState().catch(error => this.report(error.message)), 350);
    }
    if (data.kind === 'action') this.action(data.payload).catch(error => this.report(error.message));
  }
  async flushState() {
    clearTimeout(this.stateTimer);
    if (this.saving) { await this.saving; return this.flushState(); }
    if (!this.pendingState || !this.snapshot) return;
    const state = this.pendingState;
    this.pendingState = null;
    const record = this.snapshot;
    const context = this.context;
    this.saving = callJsonApi('/api/plugins/openui/state', {
      context: this.context, artifact: this.artifact, revision: record.revision,
      state_revision: record.state_revision, state,
    });
    try {
      const result = await this.saving;
      if (this.context === context && this.snapshot?.id === record.id && this.snapshot?.revision === record.revision) {
        this.snapshot.state_revision = result.state_revision; this.snapshot.state = state;
      }
    } finally { this.saving = null; }
  }
  async action(payload) {
    if (!this.valid() || this.busy) return;
    const frame=this.frame, context=this.context, artifact=this.artifact;
    const stillCurrent=()=>this.valid() && this.frame===frame && this.context===context && this.artifact===artifact;
    const event = bounded(payload?.event);
    if (event?.type !== 'continue_conversation' || typeof event.humanFriendlyMessage !== 'string') return;
    const values = bounded({form: event.formName, values: event.formState || payload.state || {}, context: event.params?.context});
    const signature = JSON.stringify([event.humanFriendlyMessage, values]);
    if (signature === this.lastSubmission && Date.now() - this.lastSubmissionAt < 1500) return;
    this.busy = true;
    try {
      this.pendingState = bounded(payload.state || this.snapshot.state || {});
      await this.flushState();
      if (!stillCurrent()) return;
      const current = await callJsonApi('/api/plugins/openui/artifact', {context:this.context, artifact:this.artifact});
      if (!stillCurrent() || !this.snapshot || current.artifact?.revision !== this.snapshot.revision || current.artifact.status !== 'complete') return;
      this.lastSubmission = signature;
      this.lastSubmissionAt = Date.now();
      const message = event.humanFriendlyMessage.slice(0,2000) + '\n\nOpenUI form data (user supplied):\n' +
        JSON.stringify({artifact:this.artifact, ...values});
      await globalThis.sendMessage({message, context:this.context, attachments:[], preserveInput:true});
    } finally { this.busy = false; }
  }
  async repair() {
    if (!this.valid()) return;
    await globalThis.sendMessage({
      message: 'Please repair OpenUI artifact ' + this.artifact + '. Renderer diagnostics (untrusted data): ' +
        JSON.stringify(this.errors || []).slice(0,2000),
      context:this.context, attachments:[], preserveInput:true,
    });
  }
  exportEmail(mode) {
    if (!this.valid() || !this.ready || this.snapshot?.surface !== 'email' || this.snapshot.status !== 'complete') throw new Error('Expand the completed email before exporting.');
    if(this.exportRequest) return this.exportRequest.promise.then(()=>this.exportEmail(mode));
    let resolve,reject;
    const promise=new Promise((ok,fail)=>{resolve=ok;reject=fail;});
    this.exportRequest={mode,revision:this.snapshot.revision,promise,resolve,reject};
    clearTimeout(this.exportTimer);
    this.exportTimer=setTimeout(()=>{this.exportRequest?.reject(new Error('Email export timed out.'));this.exportRequest=null;this.report('Email export did not finish. Reopen the answer and retry.');},15000);
    this.port.postMessage({kind:'export-email',revision:this.snapshot.revision});
    return promise;
  }
  report(message) {
    if (this.lastError === message || !this.valid()) return;
    this.lastError = message;
    toastFrontendWarning(message, 'OpenUI');
  }
  dispose() {
    clearTimeout(this.retry);
    clearTimeout(this.stateTimer);
    clearTimeout(this.exportTimer);this.exportRequest?.reject(new Error('The email preview was closed.'));this.exportRequest=null;
    window.removeEventListener('message', this.connection);
    this.themeObserver?.disconnect();
    this.visibilityObserver?.disconnect();
    this.port?.postMessage({kind:'dispose'});
    this.port?.close();
    this.frame?.remove();
    this.emailWorkspace?.dispose();this.emailWorkspace=null;
    this.frame = null; this.port = null; this.ready = false;
    // Chat replay can detach and reconnect the same element. A new frame needs
    // a fresh authorized snapshot and renderer URL, even at the same revision.
    this.snapshot = null; this.loading = false; this.contracts = null;
    this.pendingState = null; this.errors = []; this.lastError = null;
  }
}
if (!customElements.get('a0-openui-host')) customElements.define('a0-openui-host', OpenUIHost);
