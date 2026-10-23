import React from 'react';
import {Renderer} from '@openuidev/react-lang';
import {createParser} from '@openuidev/lang-core';
import {render,toPlainText} from '@react-email/render';
import DOMPurify from 'dompurify';
import {emailLibrary} from './library';

export function emailMetadata(source:string) {
  const result=createParser(emailLibrary.toJSONSchema(),emailLibrary.root).parse(source);
  if (!result.root || result.meta.errors.length) throw new Error('Repair the email before exporting it.');
  const subject=String(result.root.props.subject||'Email draft').slice(0,200);
  return {subject,previewText:String(result.root.props.previewText||'').slice(0,500)};
}

export async function exportEmail(source:string) {
  const {subject}=emailMetadata(source);
  const raw=await render(<Renderer response={source} library={emailLibrary} isStreaming={false} toolProvider={null}/>);
  // Exported documents are static; do not carry active content outside the preview sandbox.
  const body=DOMPurify.sanitize(raw,{USE_PROFILES:{html:true},FORBID_TAGS:['script','iframe','object','embed','form','input','button','meta','link','base'],
    FORBID_ATTR:['srcset','srcdoc'],ALLOW_UNKNOWN_PROTOCOLS:false});
  const escaped=subject.replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]!));
  const html='<!doctype html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>'+escaped+'</title></head><body>'+body+'</body></html>';
  if(new TextEncoder().encode(html).length>1048576)throw new Error('The exported email exceeds 1 MiB.');
  return {subject,html,text:toPlainText(html)};
}
