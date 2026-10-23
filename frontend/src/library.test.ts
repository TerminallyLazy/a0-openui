import {describe, test, expect} from 'vitest';
import {createParser, createStreamingParser, generateSystemPrompt} from '@openuidev/lang-core';
import {readFileSync} from 'node:fs';
import {library} from './library';
import {promptOptions} from './prompt-options';
import {fixtures} from './fixtures';
import {compositionExamples} from './composition';

const parse = (s: string) => createParser(library.toJSONSchema(), library.root).parse(s);
describe('the released library contract', () => {
  for (const {name,source} of compositionExamples) test(`teaching example: ${name} parses and streams`,()=>{
    const result=parse(source);
    expect(result.root).toBeTruthy();expect(result.meta.errors).toEqual([]);
    const stream=createStreamingParser(library.toJSONSchema(),library.root);
    for(let i=0;i<source.length;i+=7)stream.push(source.slice(i,i+7));
    expect(stream.getResult(true).root).toEqual(result.root);
    for(const file of ['tool-reference.txt','prompt-direct.txt','prompt-gateway.txt']){
      const prompt=readFileSync('../generated/'+file,'utf8');
      // Gateway encodes its managed configuration as JSON.
      expect(prompt.includes(source)||prompt.includes(JSON.stringify(source).slice(1,-1))).toBe(true);
    }
  });
  for (const [name, source] of Object.entries(fixtures)) {
    test(`${name} uses valid actual component signatures`, () => {
      const result = parse(source);
      expect(result.root).toBeTruthy();
      expect(result.meta.errors).toEqual([]);
    });
    for (const size of [1, 7, 29]) test(`${name}: ${size}-character chunks equal a final parse`, () => {
      const stream = createStreamingParser(library.toJSONSchema(), library.root);
      for (let i = 0; i < source.length; i += size) stream.push(source.slice(i, i + size));
      expect(stream.getResult(true).root).toEqual(parse(source).root);
    });
  }
  test('unknown nodes do not discard a valid sibling', () => {
    const result = parse('root = Stack([TextContent("Keep me"), Invented("bad")])');
    expect(JSON.stringify(result.root)).toContain('Keep me');
    expect(result.meta.errors.some(e => e.code === 'unknown-component')).toBe(true);
  });
  test('missing arguments produce structured diagnostics', () => {
    expect(parse('root = Stack([TextContent()])').meta.errors.length).toBeGreaterThan(0);
  });
  test('published files match the source library and direct prompt', () => {
    const spec = JSON.parse(readFileSync('../generated/library.spec.json', 'utf8'));
    expect(spec).toEqual(library.toSpec());
    expect(readFileSync('../generated/prompt-direct.txt', 'utf8')).toBe(generateSystemPrompt({library:library.toSpec(), promptOptions}));
  });
  test('full UI component families are exposed while password fields remain excluded', () => {
    const spec = library.toSpec();
    expect(spec.components.Input.signature).not.toContain('password');
    for (const name of ['Image','ImageGallery','Modal','MarkDownRenderer','CodeBlock','PieChart','DatePicker','EditableTable','Accordion']) expect(library.components[name]).toBeDefined();
    expect(Object.keys(spec.components).length).toBeGreaterThan(70);
  });
  test('direct and opt-in Gateway prompts use different wire formats', () => {
    expect(readFileSync('../generated/prompt-direct.txt', 'utf8')).not.toContain(']]>openui:config');
    expect(readFileSync('../generated/prompt-gateway.txt', 'utf8')).toContain(']]>openui:config');
  });
});
