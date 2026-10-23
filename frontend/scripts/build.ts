import {mkdir,readFile,writeFile,copyFile,readdir} from 'node:fs/promises';
import path from 'node:path';
import {createHash} from 'node:crypto';
import {build} from 'esbuild';
import {generateSystemPrompt} from '@openuidev/lang-core';
import {libraries,emailOptions,legacyLibrary} from '../src/library';
import {promptOptions} from '../src/prompt-options';
import {compositionRules,compositionExamples} from '../src/composition';
const root=path.resolve(import.meta.dirname,'../..');
const hash=(value:string|Buffer)=>createHash('sha256').update(value).digest('hex');
await mkdir(path.join(root,'generated'),{recursive:true});
await mkdir(path.join(root,'webui/renderer/assets'),{recursive:true});
const files:Record<string,string>={};
const contracts:Record<string,any>={};
let catalog='# OpenUI component catalog\n\nGenerated from the exact libraries shipped in this release. UI uses `Stack` as root; email uses `EmailTemplate`. Arguments are positional. Gateway is optional.\n\n';
for (const [surface,library] of Object.entries(libraries)) {
  const spec=library.toSpec();
  const source=JSON.stringify(spec,null,2)+'\n';
  catalog+=`## ${surface==='ui'?'Interactive UI':'React Email'} (${Object.keys(spec.components).length})\n\n`+Object.entries(spec.components).map(([name,c]:[string,any])=>`### ${name}\n\n\`\`\`text\n${c.signature}\n\`\`\`\n${c.description||''}\n`).join('\n')+'\n';
  const options=surface==='email'?emailOptions:promptOptions;
  const signatures=Object.values(spec.components).map((c:any)=>`${c.signature}\n${c.description||''}`).join('\n\n');
  const reference=`The following grammar applies only inside the program string argument.\n`+
    `Write one name = expression statement per line. root = ${library.root}(...) comes first.\n`+
    `Arguments are positional in signature order; arrays contain children; null skips optional middle arguments.\n`+
    `References may precede definitions. Strings are quoted.\n`+
    (surface==='ui'?'Local $variables, @Set and @Reset control state. @ToAssistant(message, context) sends a follow-up.\n':'EmailTemplate supplies the subject and previewText. This is a draft; export never sends email.\n')+
    `Query, Mutation, @Run and @OpenUrl are unavailable. For UI image search results use ImageCard/ImageCarousel/ImageGrid with actual public HTTPS URLs and source links. Email preview remote images remain blocked.\n\n`+
    (surface==='ui'?'Composition guidance:\n'+compositionRules.join('\n')+'\n\n':'')+
    signatures+(surface==='ui'?'\n\nWorked compositions (illustrative syntax only; replace all sample facts and URLs):\n'+compositionExamples.map(({name,source})=>`${name}\n${source}`).join('\n\n'):'');
  const prefix=surface==='ui'?'':surface+'-';
  for(const [name,contents] of Object.entries({
    'library.spec.json':source,'prompt-direct.txt':generateSystemPrompt({library:spec,promptOptions:options}),
    'prompt-gateway.txt':generateSystemPrompt({library:spec,promptOptions:options,cloud:true}),
    'tool-reference.txt':reference,
  })) {
    const file=`generated/${prefix}${name}`;
    await writeFile(path.join(root,file),contents);files[file]=hash(contents);
  }
  contracts[surface]={library_id:library.id,spec_digest:hash(source),components:Object.keys(spec.components).length,
    ...(surface==='ui'?{
      legacy_spec_digest:hash(JSON.stringify(legacyLibrary.toSpec(),null,2)+'\n'),
      compatible:[hash(JSON.stringify(legacyLibrary.toSpec(),null,2)+'\n'),
        'd47d2f0867c161496ad9a049f16cc19b638ff41448b8e38ebe09cd3e2f906ae5'],
    }:{})};
}
catalog+='## Reusable template example\n\nForms and actions stay in the main program. Template values are strings, finite numbers or booleans; templates cannot nest.\n\n```text\nroot = Stack([ComponentTemplate("Tasks", tile, {label:"Tasks",value:"42"}), ComponentTemplate("Projects", tile, {label:"Projects",value:"3"})])\ntile = '+JSON.stringify('root = Stack([MetricCard(@Prop("label", "Label"), @Prop("value", "0"))])')+'\n```\n';
catalog+='## Worked compositions\n\nSyntax examples only; replace all sample facts and URLs.\n\n'+compositionExamples.map(({name,source})=>`### ${name}\n\n\`\`\`text\n${source}\n\`\`\`\n`).join('\n');
await writeFile(path.join(root,'generated/components.md'),catalog);
files['generated/components.md']=hash(catalog);
const chartLicense=await readFile(path.join(root,'frontend/node_modules/chart.js/LICENSE.md'));
await writeFile(path.join(root,'generated/chartjs-license.txt'),chartLicense);
files['generated/chartjs-license.txt']=hash(chartLicense);
// Preserve complete notices from the pinned production dependency tree in releases.
const lock=JSON.parse(await readFile(path.join(root,'frontend/package-lock.json'),'utf8'));
const extraLicenses:Record<string,string>={
  'react-remove-scroll-bar':'react-remove-scroll-bar.txt',
  'rehype-katex':'remark-math.txt','remark-math':'remark-math.txt',
  'format':'format.txt','highlightjs-vue':'highlightjs-vue.txt',
};
let notices='Third-party dependency notices\n\nCollected from the pinned production dependency tree, including transitive packages.\nThe renderer also retains its linked esbuild legal notices.\n';
for(const [location,metadata] of Object.entries(lock.packages).sort(([a],[b])=>a.localeCompare(b)) as [string,any][]) {
  if(!location||metadata.dev) continue;
  const directory=path.join(root,'frontend',location);
  const names=await readdir(directory);
  const licenses=names.filter(name=>/^(license|licence|notice|copying)/i.test(name));
  notices+=`\n\n=== ${location} @ ${metadata.version} (${metadata.license||'see notice'}) ===\n`;
  if(!licenses.length) {
    const fallback=extraLicenses[location.replace(/^.*node_modules\//,'')];
    if(!fallback) throw new Error(`Missing dependency license: ${location}`);
    notices+=await readFile(path.join(root,'frontend/licenses',fallback),'utf8');
  }
  for(const name of licenses.sort()) notices+=`\n--- ${name} ---\n${await readFile(path.join(directory,name),'utf8')}\n`;
}
await writeFile(path.join(root,'generated/third-party-notices.txt'),notices);
files['generated/third-party-notices.txt']=hash(notices);
await build({entryPoints:[path.join(root,'frontend/src/frame.tsx')],bundle:true,minify:true,
  outfile:path.join(root,'webui/renderer/assets/frame.js'),format:'iife',target:'es2020',
  define:{'process.env.NODE_ENV':'"production"',__OPENUI_CONTRACTS__:JSON.stringify(contracts)},legalComments:'linked'});
await copyFile(path.join(root,'frontend/node_modules/@openuidev/react-ui/dist/styles/index.css'),path.join(root,'webui/renderer/assets/openui.css'));
for(const name of ['frame.js','frame.js.LEGAL.txt','openui.css']) {
  const file=`webui/renderer/assets/${name}`;files[file]=hash(await readFile(path.join(root,file)));
}
const visual=(await readFile(path.join(root,'webui/renderer/index.html'),'utf8')).replace('img-src data:', 'img-src data: https:');
await writeFile(path.join(root,'webui/renderer/visual.html'),visual);
files['webui/renderer/visual.html']=hash(visual);
files['webui/renderer/components.css']=hash(await readFile(path.join(root,'webui/renderer/components.css')));
files['webui/renderer/index.html']=hash(await readFile(path.join(root,'webui/renderer/index.html')));
for (const file of [
  'plugin.yaml','default_config.yaml','hooks.py','helpers/config.py','helpers/artifacts.py','helpers/generation.py','helpers/current_answer.py',
  'tools/openui.py','tools/openui_mail.py','api/artifact.py','api/state.py','api/mail.py','helpers/mailbox.py','helpers/mail_html.py','helpers/delivery.py',
  'prompts/agent.system.tool.openui.md','prompts/agent.system.tool.openui_mail.md',
  'extensions/python/system_prompt/_09_openui_config.py',
  'extensions/python/response_stream_chunk/_05_openui_preview.py','extensions/python/message_loop_end/_90_openui_preview.py',
  'extensions/webui/get_tool_message_handler/openui-handler.js','webui/config.html','webui/openui-host.js','webui/email-workspace.js','webui/email-workspace.css','thumbnail.png','webui/thumbnail.png',
]) files[file]=hash(await readFile(path.join(root,file)));
const pkg=JSON.parse(await readFile(path.join(root,'frontend/package.json'),'utf8'));
await writeFile(path.join(root,'generated/manifest.json'),JSON.stringify({format_version:1,...contracts.ui,
  libraries:contracts,dependencies:pkg.dependencies,overrides:pkg.overrides,files},null,2)+'\n');
console.log('Built contracts:',contracts);
