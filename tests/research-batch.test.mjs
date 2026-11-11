import assert from 'node:assert/strict';
import { test } from 'node:test';
import { mkdtempSync, readFileSync, rmSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { researchBatch, registerResearch } from '../extensions/research.ts';

test('trusted batch accepts data only and pins three foreground leaves', () => {
  for (const args of [{}, { tasks: [] }, { tasks: [''] }, { tasks: [null] },
      { tasks: ['a', 'b', 'c', 'd'] }, { tasks: ['a'], model: 'other' },
      { tasks: [{ agent: 'worker', task: 'x' }] }, { tasks: ['x'.repeat(12001)] }])
    assert.ok(researchBatch(args).error);
  const task = '"}); throw new Error("injection"); //';
  const result = researchBatch({ tasks: [task, 'second', 'third'] });
  const encoded = result.script.slice('return await runs.all('.length, -2);
  const children = JSON.parse(encoded);
  assert.equal(children.length, 3);
  assert.equal(children[0].task, task);
  assert.ok(children.every(c => c.agent === 'tejun-researcher' && c.async === false &&
    c.context === 'fresh' && c.timeoutMs === 600000));
});

test('batch settlement requires every expected child and rejects detached or failed rows', () => {
  const directory = mkdtempSync(join(tmpdir(), 'tejun-batch-'));
  const previous = process.env.TEJUN_CHILDREN_FILE;
  process.env.TEJUN_CHILDREN_FILE = join(directory, 'children.json');
  try {
    const handlers = new Map();
    let resource;
    const pi = {
      on: (event, callback) => handlers.set(event, callback),
      getAllTools: () => ['subagent', 'web_search'].map(name => ({ name })),
      events: { emit: (_name, request) => {
        request.result = { ok: true, registration: { dispose() {} } };
      } },
    };
    registerResearch(pi, input => { resource = input; return { dispose() {} }; });
    handlers.get('session_start')({}, { sessionManager: { getSessionId: () => 'session' } });
    assert.equal(resource.sessionId, 'session');
    assert.equal(resource.definition.name, 'tejun-research');
    for (const [index, rows] of [
      [0, 1, 2].map(i => ({ agent: 'tejun-researcher', workflowKey: `research-${i}`, success: true })),
      [{ agent: 'tejun-researcher', workflowKey: 'research-0', success: true }],
      [0, 1, 2].map(i => ({ agent: 'tejun-researcher', workflowKey: `research-${i}`, success: i !== 1 })),
      [0, 1, 2].map(i => ({ agent: 'tejun-researcher', workflowKey: `research-${i}`, success: true, detached: true })),
    ].entries()) {
      const toolCallId = `batch-${index}`;
      assert.equal(handlers.get('tool_call')({ toolName: 'subagent', toolCallId,
        input: { workflow: 'tejun-research', args: { tasks: ['a', 'b', 'c'] }, async: false } }), undefined);
      handlers.get('tool_execution_end')({ toolName: 'subagent', toolCallId,
        result: { details: { results: rows } } });
      const receipt = JSON.parse(readFileSync(process.env.TEJUN_CHILDREN_FILE));
      assert.equal(receipt.children[toolCallId], index === 0 ? 'completed' : 'failed-or-unknown');
    }
    for (const input of [
      { workflow: 'parallel', args: { tasks: ['a'] }, async: false },
      { workflow: 'tejun-research', args: { tasks: ['a'], script: 'x' }, async: false },
      { workflow: 'tejun-research', args: { tasks: ['a'] }, async: true },
      { workflow: 'tejun-research', args: { tasks: ['a'] }, async: false, cwd: '/other' },
    ]) assert.equal(handlers.get('tool_call')({ toolName: 'subagent', toolCallId: 'bad', input }).block, true);
  } finally {
    if (previous === undefined) delete process.env.TEJUN_CHILDREN_FILE;
    else process.env.TEJUN_CHILDREN_FILE = previous;
    rmSync(directory, { recursive: true, force: true });
  }
});
