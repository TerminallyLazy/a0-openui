// @vitest-environment jsdom
import React,{act} from 'react';
import {createRoot} from 'react-dom/client';
import {renderToStaticMarkup} from 'react-dom/server';
import {test,expect,vi} from 'vitest';
import {createParser,createStreamingParser} from '@openuidev/lang-core';
import {Renderer} from '@openuidev/react-lang';
import {library,legacyLibrary,emailLibrary} from './library';
import {templateLibrary} from './templates';
import {SafeImage,publicURL,ImageCarouselView} from './media';
import {chartConfig,chartProps,ChartView} from './charts';
import {createHash} from 'node:crypto';
import {readFileSync} from 'node:fs';
vi.mock('chart.js/auto',()=>({default:class {destroy(){}}}));
const tile='root = Stack([MetricCard(@Prop("label", "Label"), @Prop("value", "0"))])';
const program='root = Stack([Dashboard("Project overview", "Synthetic sample", [MetricCard("Tasks", "42", "Across three days"), ChartJS("Daily tasks", "bar", ["Mon", "Tue", "Wed"], [{label:"Completed",data:[10,14,18]}]), form, ComponentTemplate("Reusable KPI", tile, {label:"Projects",value:"3"})], "two"), ImageCarousel("Image results", [{title:"Sourced image",imageUrl:"https://images.example.com/photo.jpg",alt:"Landscape",sourceUrl:"https://example.com/source",sourceName:"Source"}])])\ntile = '+JSON.stringify(tile)+'\nform = Form("brief", Buttons([Button("Submit brief", @ToAssistant("Use this brief"))]), [FormControl("Request", Input("request", "Describe it", "text", {required:true}))])';
const parse=(s:string,lib=library)=>createParser(lib.toJSONSchema(),lib.root).parse(s);
test('unfinished chart series never throw or remove the surrounding interface',()=>{
  for(const datasets of [null,[null],[{}],[{label:'Target',data:null}],[{label:'Target'}]]) {
    const markup=renderToStaticMarkup(<ChartView {...({title:'Weekly trend',type:'line',labels:['W1'],datasets} as any)}/>);
    expect(markup).toContain('Weekly trend');expect(markup).toContain('Chart data is incomplete.');
  }
});
test('the real renderer accepts chart arguments at every streaming boundary',async()=>{
  vi.stubGlobal('IS_REACT_ACT_ENVIRONMENT',true);
  const error=vi.spyOn(console,'error').mockImplementation(()=>{});
  const source='root = Stack([TextContent("Keep this visible"), ChartJS("Weekly trend", "line", ["W1", "W2"], [{label:"Completed",data:[12,18]}, {label:"Target",data:[30,30]}])])';
  const el=document.createElement('div');document.body.append(el);const root=createRoot(el);
  try {
    for(let end=1;end<=source.length;end++) {
      await act(async()=>root.render(<Renderer library={library} response={source.slice(0,end)} isStreaming={end<source.length} toolProvider={null}/>));
    }
    expect(el.textContent).toContain('Keep this visible');
    expect(el.querySelector('table')?.textContent).toContain('Target');
    expect(el.querySelectorAll('tbody tr')).toHaveLength(2);
    expect(error).not.toHaveBeenCalled();
  }finally{await act(async()=>root.unmount());el.remove();error.mockRestore();vi.unstubAllGlobals();}
});
test('new dashboard, image carousel, form and reusable template parse and stream together',()=>{
  const final=parse(program);expect(final.meta.errors).toEqual([]);expect(final.root).toBeTruthy();
  const stream=createStreamingParser(library.toJSONSchema(),library.root);
  for(let i=0;i<program.length;i+=13)stream.push(program.slice(i,i+13));
  expect(stream.getResult(true).root).toEqual(final.root);
});
test('ImageGrid has its own positional schema and preserves the same two result objects as the carousel',async()=>{
  vi.stubGlobal('IS_REACT_ACT_ENVIRONMENT',true);
  const source='root = Stack([ImageGrid("Photos", [{title:"One",imageUrl:"https://images.example.com/one.jpg",alt:"First photo",sourceUrl:"https://example.com/one"},{title:"Two",imageUrl:"https://images.example.com/two.jpg",alt:"Second photo",sourceUrl:"https://example.com/two"}])])';
  const result=parse(source);expect(result.meta.errors).toEqual([]);
  const el=document.createElement('div');document.body.append(el);const root=createRoot(el);
  try{
    await act(async()=>root.render(<Renderer library={library} response={source} isStreaming={false} toolProvider={null}/>));
    expect(el.querySelectorAll('article')).toHaveLength(2);
    expect(el.querySelectorAll('img')).toHaveLength(2);
    expect(el.querySelector('img')?.getAttribute('alt')).toBe('First photo');
    expect(el.querySelectorAll('a')).toHaveLength(2);
  }finally{await act(async()=>root.unmount());el.remove();vi.unstubAllGlobals();}
});
test('all nine Chart.js types have bounded data and accessible fallback-ready labels',()=>{
  for(const type of ['bar','line','area','pie','doughnut','radar','polarArea','scatter','bubble'] as const){
    const p=chartProps.parse({title:'Sample',type,labels:['A','B'],datasets:[{label:'Observed',data:type==='scatter'||type==='bubble'?[{x:1,y:2,r:4}]:[1,2]}]});
    const config=chartConfig(p);expect(config.options.animation).toBe(false);expect(config.type).toBe(type==='area'?'line':type);
  }
  expect(chartProps.safeParse({title:'Too large',type:'bar',labels:[],datasets:[{label:'x',data:Array(501).fill(1)}]}).success).toBe(false);
  expect(chartProps.safeParse({title:'Bad',type:'bar',labels:[],datasets:[{label:'x',data:[Infinity]}]}).success).toBe(false);
  const mixed=chartConfig(chartProps.parse({title:'Mixed',type:'bar',labels:['A'],datasets:[{label:'Bar',data:[3]},{label:'Line',data:[2],type:'line'}]}));
  expect(mixed.data.datasets[1].type).toBe('line');
});
test('image cards reject executable URLs, credentials, non-HTTPS and local literal addresses',()=>{
  for(const value of ['javascript:alert(1)','data:image/svg+xml,svg','http://example.com/a','https://127.0.0.1/a','https://[::1]/a','https://localhost/a','https://host.internal/a','https://user:secret@example.com/a','https://example.com:8443/a'])expect(publicURL(value)).toBeUndefined();
  expect(publicURL('https://images.example.com/photo.jpg')).toBeTruthy();
  const html=renderToStaticMarkup(<SafeImage src="https://images.example.com/photo.jpg" alt="Meaningful description"/>);
  expect(html).toContain('crossorigin="anonymous"');expect(html).toContain('referrerPolicy="no-referrer"');expect(html).toContain('Meaningful description');
});
test('legacy UI2 and email contracts are byte-identical and explicitly supported',()=>{
  const digest=(lib:any)=>createHash('sha256').update(JSON.stringify(lib.toSpec(),null,2)+'\n').digest('hex');
  expect(digest(legacyLibrary)).toBe('912831499155286ffb92432c31227d49fddd1dcaa0d56dd61f8e670e7bd47d32');
  expect(digest(emailLibrary)).toBe('6d9cfccbcdb02b6004db1f8dc4f511ff8221c71a17979218e53aea299c7b1f12');
  const manifest=JSON.parse(readFileSync('../generated/manifest.json','utf8'));
  expect(manifest.libraries.ui.compatible).toContain(digest(legacyLibrary));
});
test('template parameters render as text and cannot inject code or register interactive components',async()=>{
  vi.stubGlobal('IS_REACT_ACT_ENVIRONMENT',true);
  const el=document.createElement('div');document.body.append(el);const root=createRoot(el);
  const template=templateLibrary(library,{label:'<script>bad()</script>',value:'42'});
  const errors:any[]=[];
  try{
    await act(async()=>root.render(<Renderer library={template} response={tile} isStreaming={false} toolProvider={null} onError={e=>errors.push(...e)}/>));
    expect(el.textContent).toContain('<script>bad()</script>');expect(el.querySelector('script')).toBeNull();expect(el.textContent).toContain('42');expect(errors).toEqual([]);
    expect(template.components.Form).toBeUndefined();expect(template.components.ComponentTemplate).toBeUndefined();expect(template.components.Button).toBeUndefined();
    expect(parse('root = Stack([Form("bad")])',template).meta.errors.some(e=>e.code==='unknown-component')).toBe(true);
  }finally{await act(async()=>root.unmount());el.remove();vi.unstubAllGlobals();}
});
test('email keeps a network-isolated image policy while visual answers allow HTTPS images only',()=>{
  const email=readFileSync('../webui/renderer/index.html','utf8');const visual=readFileSync('../webui/renderer/visual.html','utf8');
  expect(email).toContain('img-src data:;');expect(visual).toContain('img-src data: https:;');
  for(const doc of [email,visual]){expect(doc).toContain("connect-src 'none'");expect(doc).toContain('name="referrer" content="no-referrer"');expect(doc).not.toContain('unsafe-eval');}
});

test('carousel navigation follows real overflow and stops at each end',async()=>{
  vi.stubGlobal('IS_REACT_ACT_ENVIRONMENT',true);vi.stubGlobal('ResizeObserver',class{observe(){}disconnect(){}});
  const el=document.createElement('div');document.body.append(el);const root=createRoot(el);
  try{
    await act(async()=>root.render(<ImageCarouselView title="Results" items={[{title:'One',imageUrl:'',alt:'One'},{title:'Two',imageUrl:'',alt:'Two'}]}/>));
    expect(el.querySelectorAll('button')).toHaveLength(0);
    const track=el.querySelector('.a0-image-track') as HTMLDivElement;
    Object.defineProperties(track,{scrollWidth:{value:636,configurable:true},clientWidth:{value:350,configurable:true}});
    track.scrollBy=vi.fn();
    await act(async()=>track.dispatchEvent(new Event('scroll',{bubbles:true})));
    const buttons=el.querySelectorAll('button');expect(buttons[0].disabled).toBe(true);expect(buttons[1].disabled).toBe(false);
    await act(async()=>buttons[1].click());expect(track.scrollBy).toHaveBeenCalledTimes(1);
    track.scrollLeft=286;await act(async()=>track.dispatchEvent(new Event('scroll',{bubbles:true})));
    expect(buttons[0].disabled).toBe(false);expect(buttons[1].disabled).toBe(true);
  }finally{await act(async()=>root.unmount());el.remove();vi.unstubAllGlobals();}
});
