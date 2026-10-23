import React, {useEffect, useRef, useState} from 'react';
import Chart from 'chart.js/auto';
import {defineComponent} from '@openuidev/react-lang';
import {z} from 'zod';

const number = z.number().finite();
const point = z.object({x:number,y:number,r:number.min(1).max(40).optional()});
const types = z.enum(['bar','line','area','pie','doughnut','radar','polarArea','scatter','bubble']);
const series = z.object({label:z.string().max(100),data:z.array(z.union([number,point,z.null()])).max(500),
  type:z.enum(['bar','line']).optional()});
export const chartProps = z.object({title:z.string().max(200),type:types,
  labels:z.array(z.string().max(100)).max(500),datasets:z.array(series).min(1).max(12),
  stacked:z.boolean().optional(),horizontal:z.boolean().optional(),description:z.string().max(1000).optional()});
type Props = z.infer<typeof chartProps>;
const colors=['#218b83','#d38a38','#5d83bc','#ad6485','#85a34b','#8a72ba','#c86c57','#658b9c'];
export function chartConfig(p:Props, dark=false):any {
  const circular=['pie','doughnut','polarArea'].includes(p.type);
  const radial=circular||p.type==='radar';
  const foreground=dark?'#d7dadd':'#414b53';
  return {type:p.type==='area'?'line':p.type,data:{labels:p.labels,datasets:p.datasets.map((s,i)=>({
    label:s.label,data:s.data,type:s.type,fill:p.type==='area',borderWidth:2,
    borderColor:circular?undefined:colors[i%colors.length],
    backgroundColor:circular?p.labels.map((_,j)=>colors[j%colors.length]):colors[i%colors.length]+(p.type==='area'?'40':'cc'),
    pointRadius:3,tension:0.2,
  }))},options:{responsive:true,maintainAspectRatio:false,animation:false,
    indexAxis:p.horizontal&&p.type==='bar'?'y':'x',
    plugins:{legend:{position:'bottom',labels:{color:foreground,usePointStyle:true,boxWidth:8}},tooltip:{enabled:true}},
    scales:radial?(p.type==='radar'||p.type==='polarArea'?{r:{ticks:{color:foreground,backdropColor:'transparent'},pointLabels:{color:foreground},grid:{color:dark?'#444a50':'#dce1e5'}}}:undefined):
      {x:{stacked:!!p.stacked,ticks:{color:foreground},grid:{display:false}},y:{stacked:!!p.stacked,beginAtZero:p.type!=='scatter'&&p.type!=='bubble',ticks:{color:foreground},grid:{color:dark?'#343a40':'#e5e9ec'}}}}};
}
export function ChartView(p:Props) {
  // Streaming can expose an unfinished series as {data: null} before the
  // parser has enough tokens to validate it. Keep that local to this chart.
  const parsed=chartProps.safeParse(p);
  if(!parsed.success)return <figure className="a0-chart"><figcaption><h3>{typeof p.title==='string'?p.title:'Chart'}</h3></figcaption><p>Chart data is incomplete.</p></figure>;
  return <ReadyChartView {...parsed.data}/>;
}
function ReadyChartView(p:Props) {
  const canvas=useRef<HTMLCanvasElement>(null);
  const [failed,setFailed]=useState(false);
  const dark=typeof document!=='undefined'&&document.documentElement.dataset.mode==='dark';
  const fingerprint=JSON.stringify(p);
  useEffect(()=>{
    let chart:Chart|undefined;
    try {setFailed(false);chart=new Chart(canvas.current!,chartConfig(p,dark));}
    catch {setFailed(true);}
    return ()=>chart?.destroy();
  },[fingerprint,dark]);
  const rows=Math.max(p.labels.length,...p.datasets.map(s=>s.data.length));
  const display=(value:unknown)=>value===null||value===undefined?'—':typeof value==='object'?Object.entries(value).map(([k,v])=>`${k}: ${v}`).join(', '):String(value);
  return <figure className="a0-chart"><figcaption><h3>{p.title}</h3>{p.description&&<p>{p.description}</p>}</figcaption>
    {!failed&&<div className="a0-chart-canvas"><canvas ref={canvas} role="img" aria-label={`${p.title}. Values are available in the data table below.`}/></div>}
    <details open={failed||undefined}><summary>{failed?'Chart unavailable — view data':'View chart data'}</summary><div className="a0-table-scroll"><table><thead><tr><th scope="col">Label</th>{p.datasets.map((s,i)=><th scope="col" key={i}>{s.label}</th>)}</tr></thead>
      <tbody>{Array.from({length:rows},(_,i)=><tr key={i}><th scope="row">{p.labels[i]??i+1}</th>{p.datasets.map((s,j)=><td key={j}>{display(s.data[i])}</td>)}</tr>)}</tbody></table></div></details>
  </figure>;
}
export const ChartJS=defineComponent({name:'ChartJS',props:chartProps,description:'Chart.js canvas chart with accessible data table. Types: bar, line, area, pie, doughnut, radar, polarArea, scatter, bubble. datasets are objects {label,data,type?}; scatter/bubble data are {x,y,r?}. Per-series bar/line type makes mixed charts. Maximum 12 series and 500 points each. No executable options.',component:({props})=><ChartView {...props}/>});
