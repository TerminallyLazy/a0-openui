import React,{createContext,useContext,useMemo} from 'react';
import {createLibrary,defineComponent,defineFunction,Renderer,type Library} from '@openuidev/react-lang';
import {z} from 'zod';
const scalar=z.union([z.string().max(2000),z.number().finite(),z.boolean()]);
const fields=z.record(z.string().max(80),scalar).refine(v=>Object.keys(v).length<=40&&!Object.keys(v).some(k=>['__proto__','constructor','prototype'].includes(k)),'Invalid template values');
export const TemplateErrors=createContext<(errors:any[])=>void>(()=>{});
// Templates reuse the same reviewed renderers. They never compile/evaluate JavaScript or register global code.
const presentation=new Set(['Stack','Card','CardHeader','TextContent','Text','BoldText','Callout','TextCallout','Separator','Tag','TagBlock','Icon','Image','SourceLink','ImageCard','ImageCarousel','ImageGrid','ChartJS','Dashboard','DashboardSection','MetricCard','ProgressMeter','KeyValueList','Timeline','KanbanBoard','ComparisonTable','Agenda','FileList','StatusBadge','EmptyState','QuoteBlock','Checklist','Rating']);
export function templateLibrary(base:Library,values:Record<string,string|number|boolean>) {
  const Prop=defineFunction({name:'Prop',description:'Read a supplied template parameter, or its fallback.',params:z.object({name:z.string(),fallback:scalar}),returns:scalar,
    fn:({name,fallback})=>Object.hasOwn(values,name)?values[name]:fallback});
  return createLibrary({id:'a0-openui-template@1',root:'Stack',components:Object.values(base.components).filter(c=>presentation.has(c.name)),functions:[Prop]});
}
export function makeTemplate(getLibrary:()=>Library){
  return defineComponent({name:'ComponentTemplate',description:'Create a reusable PRESENTATION component on the fly. name identifies the layout; program is a quoted OpenUI program rooted at Stack, with @Prop("key", fallback) for scalar values. values is a JSON object. Reuse the same program variable with different values. Cards/charts/images/metrics work; templates cannot nest templates, contain forms, run code or execute actions. Use normal Form outside the template.',
    props:z.object({name:z.string().max(100),program:z.string().max(8192),values:fields}),component:({props})=>{
      const report=useContext(TemplateErrors);
      const lib=useMemo(()=>templateLibrary(getLibrary(),props.values),[JSON.stringify(props.values)]);
      return <section aria-label={props.name}><Renderer library={lib} response={props.program} isStreaming={false} toolProvider={null} onError={errors=>{if(errors.length)report(errors);}}/></section>;
    }});
}
