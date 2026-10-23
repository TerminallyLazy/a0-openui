import React, { Component } from 'react';
import { createRoot } from 'react-dom/client';
import { Renderer } from '@openuidev/react-lang';
import { ThemeProvider } from '@openuidev/react-ui';
import {libraries,legacyLibrary} from './library';
import {TemplateErrors} from './templates';
import {exportEmail,emailMetadata} from './email-export';

declare const __OPENUI_CONTRACTS__: Record<string,{spec_digest:string,compatible?:string[],legacy_spec_digest?:string}>;
let port: MessagePort | undefined;
let current: any;
let revision = -1;
let state: Record<string, unknown> = {};
const root = createRoot(document.getElementById('root')!);
const send = (kind: string, payload: unknown) => port?.postMessage({kind, revision, payload});

class Boundary extends Component<React.PropsWithChildren<{revision:number}>, {failed: boolean}> {
  state = {failed: false};
  static getDerivedStateFromError() { return {failed: true}; }
  componentDidCatch() { send('error', [{code: 'render-error', message: 'This interface could not be rendered.'}]); }
  componentDidUpdate(previous: Readonly<{revision:number}>) {
    if (previous.revision !== this.props.revision && this.state.failed) this.setState({failed:false});
  }
  render() { return this.state.failed ? <p>See the answer summary or ask the agent to repair this interface.</p> : this.props.children; }
}

function draw(snapshot: any) {
  const surface=snapshot?.surface === 'email' ? 'email' : 'ui';
  const contract=__OPENUI_CONTRACTS__[surface];
  if (!snapshot || ![contract.spec_digest,...(contract.compatible||[])].includes(snapshot.spec_digest) || typeof snapshot.source !== 'string' ||
      new TextEncoder().encode(snapshot.source).length > 65536 || snapshot.revision < revision) return;
  if (!current) state = snapshot.state || {};
  document.documentElement.dataset.mode=snapshot.dark?'dark':'light';
  current = snapshot;
  revision = snapshot.revision;
  if (surface === 'email' && snapshot.status === 'complete') {
    try { send('email-metadata',emailMetadata(snapshot.source)); } catch { /* Renderer reports diagnostics. */ }
  }
  root.render(<Boundary key={snapshot.id} revision={snapshot.revision}>
    <TemplateErrors.Provider value={errors=>send('error',errors.slice(0,8).map(e=>({code:e.code,message:String(e.message).slice(0,200)})))}>
    <ThemeProvider mode={snapshot.dark ? 'dark' : 'light'}>
      <div inert={snapshot.status !== 'complete' ? true : undefined}>
        <Renderer library={surface==='ui'&&snapshot.spec_digest===contract.legacy_spec_digest?legacyLibrary:libraries[surface]} response={snapshot.source} isStreaming={snapshot.status === 'generating'}
          toolProvider={null} initialState={snapshot.state || {}}
          onStateUpdate={(value) => {
            if (current.status !== 'complete') return;
            state = value;
            send('state', value);
          }}
          onAction={(event) => {
            if (current.status !== 'complete' || event.type !== 'continue_conversation') return;
            send('action', {event, state});
          }}
          onError={(errors) => {
            if (current.status === 'generating' || !errors.length) return;
            send('error', errors.slice(0, 8).map(e => ({code: e.code, statement: e.statementId, message: e.message.slice(0,200)})));
          }} />
      </div>
    </ThemeProvider></TemplateErrors.Provider>
  </Boundary>);
}

window.addEventListener('message', function connect(event) {
  if (event.source !== window.parent || event.data?.kind !== 'openui-connect' || event.data.version !== 1 || !event.ports[0] || port) return;
  port = event.ports[0];
  port.onmessage = ({data}) => {
    if (data?.kind === 'snapshot') draw(data.payload);
    if (data?.kind === 'export-email' && data.revision === revision && current?.surface === 'email' && current.status === 'complete') {
      const requested=revision;
      exportEmail(current.source).then(result=>{
        if(requested===revision) send('email-export',result);
      }).catch(()=>send('error',[{code:'email-export',message:'The email could not be exported. Repair it and retry.'}]));
    }
    if (data?.kind === 'dispose') { root.unmount(); observer.disconnect(); port?.close(); window.removeEventListener('message', connect); }
  };
  port.start();
  send('ready', {contracts: __OPENUI_CONTRACTS__});
});
let previousHeight = 0;
const observer = new ResizeObserver(() => {
  const height = Math.min(1200, Math.max(100, document.documentElement.scrollHeight));
  if (height !== previousHeight) { previousHeight = height; send('resize', height); }
});
observer.observe(document.getElementById('root')!);
// User-clicked links go through the host; the sandbox itself stays network-isolated.
document.addEventListener('click', event => {
  const link=(event.target as Element)?.closest?.('a');
  if (!link) return;
  event.preventDefault();
  if (event.isTrusted && current?.status === 'complete') send('open-link',link.getAttribute('href'));
}, true);
window.parent.postMessage({kind: 'openui-ready'}, '*');
