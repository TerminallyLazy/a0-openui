import { createLibrary, defineComponent } from '@openuidev/react-lang';
import { openuiLibrary } from '@openuidev/react-ui/genui-lib';
import { emailLibrary as upstreamEmail, emailPromptOptions } from '@openuidev/react-email';
import { z } from 'zod';
import {ChartJS} from './charts';
import {ImageCard,ImageCarousel,ImageGrid,SourceLink} from './media';
import {extraComponents} from './components';
import {makeTemplate} from './templates';

// Keep the full upstream component set; execution/network authority stays in the host.
// Do not accept model-supplied regex validators or credential collection fields.
const rules = z.object({required:z.boolean().optional(),email:z.boolean().optional(),
  numeric:z.boolean().optional(),min:z.number().optional(),max:z.number().optional(),
  minLength:z.number().optional(),maxLength:z.number().optional()}).optional();
const overrides = Object.entries(openuiLibrary.components).flatMap(([name,c]) => {
  if (!('rules' in c.props.shape)) return [];
  return [defineComponent({name,description:c.description,
    props:c.props.extend({...{rules},...(name === 'Input' ? {type:z.enum(['text','email','number','url']).optional()} : {})}),
    component:c.component})];
});
const extended = openuiLibrary.extend({components:{override:overrides}});
export const legacyLibrary = createLibrary({id:'a0-openui@2',root:'Stack',components:Object.values(extended.components)});
const ComponentTemplate=makeTemplate(()=>library);
const additions=[ChartJS,ImageCard,ImageCarousel,ImageGrid,SourceLink,...extraComponents,ComponentTemplate];
const expanded=extended.extend({components:{add:additions.map(component=>({component,slots:['Card.children','Carousel.children','TabItem.content']}))}});
export const library = createLibrary({id:'a0-openui@3',root:'Stack',components:Object.values(expanded.components)});
export const emailLibrary = createLibrary({id:'a0-openui-email@1',root:upstreamEmail.root,components:Object.values(upstreamEmail.components)});
export const libraries = {ui:library,email:emailLibrary};
// Preserve useful upstream design guidance, replacing invented data/URLs with source fidelity.
export const emailOptions = {...emailPromptOptions,
  examples:emailPromptOptions.examples?.slice(0,1),
  additionalRules:[...(emailPromptOptions.additionalRules || []).filter(rule=>
    !/realistic|plausible|publicly accessible|picsum|realistic href/i.test(rule)),
    'Use only facts, brands, links and image URLs supplied by the user. Never invent credentials, addresses or live links.',
    'Use clearly labelled sample text when the user explicitly asks for a sample.',
    'Remote images remain blocked in the local preview; their supplied URLs can be included in exported email HTML.',
    'This library creates drafts only. Native Email studio controls separately offer user-reviewed sending. Generated programs must not emulate, trigger or claim sending.'],
};
