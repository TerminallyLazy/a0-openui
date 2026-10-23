// @vitest-environment jsdom
import {test,expect} from 'vitest';
import {createParser} from '@openuidev/lang-core';
import {emailLibrary} from './library';
import {exportEmail,emailMetadata} from './email-export';
const source='root = EmailTemplate("Weekly sample", "Synthetic results", [EmailHeading("Weekly overview", 1), EmailText("All values are synthetic."), EmailStats([EmailStatItem("42", "Completed")]), EmailButton("Review", "https://example.com/review")])';
test('all 44 React Email definitions are available and parse a complete email',()=>{
  expect(Object.keys(emailLibrary.components)).toHaveLength(44);
  expect(createParser(emailLibrary.toJSONSchema(),emailLibrary.root).parse(source).meta.errors).toEqual([]);
});
test('preview metadata uses the actual email subject and preheader',()=>{
  expect(emailMetadata(source)).toEqual({subject:'Weekly sample',previewText:'Synthetic results'});
});
test('email export contains the rendered content, subject and plain text without an active form',async()=>{
  const result=await exportEmail(source);
  expect(result.subject).toBe('Weekly sample');expect(result.html).toContain('Weekly overview');
  expect(result.html).toContain('https://example.com/review');expect(result.text).toContain('Completed');
  expect(result.html).not.toMatch(/<script|<iframe|<form/i);
});
test('malformed email refuses export instead of producing a misleading blank document',async()=>{
  await expect(exportEmail('root = EmailTemplate()')).rejects.toThrow('Repair');
});
test('raw executable markup and unsafe links do not survive export',async()=>{
  const result=await exportEmail('root = EmailTemplate("Safety", "Sample", [EmailMarkdown("<script>alert(1)</script><img src=x onerror=alert(1)><a href=javascript:alert(1)>bad</a>")])');
  expect(result.html).not.toMatch(/<script|onerror=|href="javascript:/i);
});
