import React,{useEffect,useRef,useState} from 'react';
import {defineComponent} from '@openuidev/react-lang';
import {z} from 'zod';

export function publicURL(value:unknown):string|undefined {
  if(typeof value!=='string'||value.length>2048)return;
  try {const u=new URL(value);const host=u.hostname.toLowerCase();
    if(u.protocol!=='https:'||u.username||u.password||u.port&&u.port!=='443'||
      !host.includes('.')||host.endsWith('.local')||host.endsWith('.localhost')||host.endsWith('.internal')||
      /^\d/.test(host)||host.includes(':')||host.startsWith('['))return;
    return u.href;
  }catch{return;}
}
export function SafeImage({src,alt}:{src?:string;alt:string}) {
  const [failed,setFailed]=useState(false);
  useEffect(()=>setFailed(false),[src]);
  const url=publicURL(src);
  return url&&!failed?<img className="a0-result-image" src={url} alt={alt} crossOrigin="anonymous" referrerPolicy="no-referrer" loading="lazy" decoding="async" onError={()=>setFailed(true)}/>:
    <div className="a0-image-fallback" role="img" aria-label={alt}><span>{alt}</span><small>{src?'Image unavailable • use source link':'No image supplied'}</small></div>;
}
export const imageCardProps=z.object({title:z.string().max(200),imageUrl:z.string().max(2048),alt:z.string().max(400),
  description:z.string().max(1000).optional(),sourceUrl:z.string().max(2048).optional(),sourceName:z.string().max(120).optional(),badge:z.string().max(80).optional()});
type ImageProps=z.infer<typeof imageCardProps>;
export function ImageCardView(p:ImageProps){return <article className="a0-image-card"><SafeImage src={p.imageUrl} alt={p.alt}/><div className="a0-image-copy">
  {p.badge&&<span className="a0-badge">{p.badge}</span>}<h3>{p.title}</h3>{p.description&&<p>{p.description}</p>}
  {publicURL(p.sourceUrl)&&<a href={publicURL(p.sourceUrl)}>{p.sourceName||'View source'} ↗</a>}</div></article>;}
export const ImageCard=defineComponent({name:'ImageCard',props:imageCardProps,description:'Image search result or recommendation with image, alt text, description, source-page link and optional badge. Use actual HTTPS URLs returned by search or supplied by the user; never invent URLs or provenance. Broken/CORS-blocked images have an accessible fallback.',component:({props})=><ImageCardView {...props}/>});
const collection=z.object({title:z.string().max(200),items:z.array(z.object({...imageCardProps.shape})).max(24)});
export function ImageCarouselView({title,items}:z.infer<typeof collection>){
  const track=useRef<HTMLDivElement>(null);
  const [navigation,setNavigation]=useState({previous:false,next:false,overflow:false});
  const measure=()=>{const el=track.current;if(!el)return;const max=el.scrollWidth-el.clientWidth;
    const next={previous:el.scrollLeft>1,next:el.scrollLeft<max-1,overflow:max>1};
    setNavigation(old=>old.previous===next.previous&&old.next===next.next&&old.overflow===next.overflow?old:next);
  };
  useEffect(()=>{measure();const observer=new ResizeObserver(measure);if(track.current)observer.observe(track.current);return ()=>observer.disconnect();},[items.length]);
  const move=(direction:number)=>{const el=track.current;if(el)el.scrollBy({left:direction*((el.firstElementChild?.getBoundingClientRect().width||el.clientWidth)+16),behavior:'instant'});};
  return <section className="a0-image-collection" aria-label={title} aria-roledescription="carousel"><div className="a0-section-heading"><h3>{title}</h3><div className="a0-carousel-controls">
    {navigation.overflow&&<button aria-label={`Previous image in ${title}`} disabled={!navigation.previous} onClick={()=>move(-1)}>←</button>}<span>{items.length} images</span>
    {navigation.overflow&&<button aria-label={`Next image in ${title}`} disabled={!navigation.next} onClick={()=>move(1)}>→</button>}</div></div>
    <div ref={track} className="a0-image-track" onScroll={measure}>
      {items.map((item,i)=><div key={i} role="group" aria-label={`${i+1} of ${items.length}`}><ImageCardView {...item}/></div>)}</div></section>;
}
export const ImageCarousel=defineComponent({name:'ImageCarousel',props:collection,description:'Responsive, keyboard-operable horizontal image cards. items are objects in ImageCard prop shape; maximum 24. No auto-play. Include sourceUrl/sourceName for search provenance.',component:({props})=><ImageCarouselView {...props}/>});
// A clone retains Zod's schema parent and serializes as a $ref to ImageCarousel.
// The OpenUI positional parser needs this component's own object definition.
export const ImageGrid=defineComponent({name:'ImageGrid',props:z.object({...collection.shape}),description:'Responsive grid of up to 24 image search results or recommendations. items are objects with title,imageUrl,alt,description?,sourceUrl?,sourceName?,badge?.',component:({props})=><section className="a0-image-collection"><h3>{props.title}</h3><div className="a0-image-grid">{props.items.map((p,i)=><ImageCardView key={i} {...p}/>)}</div></section>});
export const SourceLink=defineComponent({name:'SourceLink',props:z.object({label:z.string(),url:z.string(),note:z.string().optional()}),description:'Named source/citation link for facts or image attribution. HTTPS only.',component:({props})=><p className="a0-source">{publicURL(props.url)?<a href={publicURL(props.url)}>{props.label} ↗</a>:<span>{props.label}</span>}{props.note&&<small>{props.note}</small>}</p>});
