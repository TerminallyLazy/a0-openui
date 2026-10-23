import {drawProcessStep, cleanStepTitle, buildDetailPayload} from '/js/messages.js';
import {store as details} from '/components/modals/process-step-detail/step-detail-store.js';
import {copyToClipboard, createActionButton} from '/components/messages/action-buttons/simple-action-buttons.js';
import {ttsService} from '/js/tts-service.js';
import '/plugins/openui/webui/openui-host.js';

export default function (context) {
  if (context.tool_name !== 'openui') return;
  context.handler = function (log) {
    const text = String(log.content || 'Interactive answer');
    let result;
    const getHost = () => result?.detail.querySelector(':scope > a0-openui-host');
    result = drawProcessStep({id:log.id, title:cleanStepTitle(log.heading), code:'UI', log,
      content:text, kvps:{}, actionButtons:[
        createActionButton('detail', '', () => details.showStepDetail(buildDetailPayload(log, {
          content: getHost()?.snapshot?.source || text, headerLabels:[],
        }))),
        createActionButton('copy', '', () => copyToClipboard(getHost()?.snapshot?.source || text)),
        createActionButton('speak', '', () => ttsService.speak(text)),
        createActionButton('build', 'Repair', () => getHost()?.repair()),
        ...(log.kvps?.openui_surface === 'email' ? [
          createActionButton('copy', 'HTML', () => getHost()?.exportEmail('copy')),
          createActionButton('download', 'Download HTML', () => getHost()?.exportEmail('download')),
          createActionButton('copy', 'subject', () => getHost()?.exportEmail('subject')),
          createActionButton('copy', 'text', () => getHost()?.exportEmail('text')),
        ] : []),
      ]});
    if (log.kvps?.openui_artifact && !result.detailPending) {
      let host = getHost();
      if (!host) { host = document.createElement('a0-openui-host'); result.detail.appendChild(host); }
      host.configure(globalThis.getContext?.(), log.kvps.openui_artifact, log.kvps.openui_revision);
    }
    return result;
  };
}
