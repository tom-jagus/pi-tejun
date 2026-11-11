import assert from 'node:assert/strict';
import { test } from 'node:test';
import { mkdtempSync, readFileSync, rmSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { registerResearch, researchBatch } from '../extensions/research.ts';
const register = pi => registerResearch(pi, () => ({ dispose() {} }));
const session = { sessionManager: { getSessionId: () => 'fixture' } };
import child from '../extensions/research-child.ts';

function harness(owner = true, tools = ['read', 'web_search', 'subagent']) {
  const handlers = new Map();
  let definition;
  let disposed = false;
  let active = ['read', 'subagents_enable', 'bg_wait'];
  const pi = {
    on: (event, callback) => handlers.set(event, callback),
    getAllTools: () => tools.map(name => ({ name })),
    getActiveTools: () => active,
    setActiveTools: names => { active = names; },
    events: { emit: (_event, request) => {
      definition = request.definition;
      if (owner) request.result = { ok: true, registration: { dispose: () => { disposed = true; } } };
    } },
  };
  return { pi, handlers, definition: () => definition, active: () => active, disposed: () => disposed };
}

test('fixed foreground profile, activation, rejection, settlement, cleanup', () => {
  const directory = mkdtempSync(join(tmpdir(), 'tejun-research-'));
  const old = { ...process.env };
  try {
    process.env.TEJUN_CHILDREN_FILE = join(directory, 'children.json');
    process.env.TEJUN_ERROR_FILE = join(directory, 'error.txt');
    process.env.TEJUN_SEARCH_EXTENSION = '/fixture/search.ts';
    const read = () => JSON.parse(readFileSync(process.env.TEJUN_CHILDREN_FILE));
    const h = harness();
    register(h.pi);
    h.handlers.get('session_start')({}, session);
    assert.equal(read().ready, true);
    assert.deepEqual(h.definition().tools, ['read', 'web_search']);
    assert.equal(h.definition().defaultAsync, false);
    assert.equal(h.definition().allowNestedSubagents, false);
    assert.equal(h.definition().inheritGlobalContext, false);
    assert.equal(h.definition().extensions.length, 2);
    h.handlers.get('before_agent_start')();
    assert.deepEqual(h.active(), ['read', 'subagent']);
    const call = (id, input) => h.handlers.get('tool_call')({ toolName: 'subagent', toolCallId: id, input });
    const valid = { agent: 'tejun-researcher', task: 'Research', async: false };
    for (const [i, args] of [
      { ...valid, async: true }, { ...valid, agent: 'worker' },
      { ...valid, tools: ['bash'] }, { ...valid, script: 'anything' },
      { ...valid, model: 'other' }, { ...valid, task: '' },
    ].entries()) assert.equal(call(`bad-${i}`, args).block, true);
    for (const [i, row] of [
      { agent: 'tejun-researcher', exitCode: 0 },
      { agent: 'tejun-researcher', exitCode: 1 },
      { agent: 'tejun-researcher', exitCode: 0, detached: true },
      { agent: 'tejun-researcher', exitCode: 0, timedOut: true },
      { agent: 'tejun-researcher', exitCode: 0, stopped: true },
      { agent: 'tejun-researcher', exitCode: 0, interrupted: true },
      undefined,
    ].entries()) {
      const id = `child-${i}`;
      assert.equal(call(id, valid), undefined);
      assert.equal(read().children[id], 'running');
      h.handlers.get('tool_execution_end')({ toolName: 'subagent', toolCallId: id,
        result: { details: { results: row ? [row] : [] } } });
      assert.equal(read().children[id], i === 0 ? 'completed' : 'failed-or-unknown');
    }
    call('unfinished', valid);
    h.handlers.get('session_shutdown')();
    assert.equal(read().children.unfinished, 'running');
    assert.equal(h.disposed(), true);
    for (const missing of [harness(false), harness(true, ['subagent'])]) {
      register(missing.pi);
      missing.handlers.get('session_start')({}, session);
      assert.equal(read().ready, false);
      assert.equal(missing.handlers.get('input')().action, 'handled');
      assert.match(readFileSync(process.env.TEJUN_ERROR_FILE, 'utf8'), /unavailable/);
    }
  } finally {
    process.env = old;
    rmSync(directory, { recursive: true, force: true });
  }
});

test('child tools remain read-only, missing search fails closed', () => {
  const directory = mkdtempSync(join(tmpdir(), 'tejun-child-'));
  const previous = process.env.TEJUN_CHILDREN_FILE;
  process.env.TEJUN_CHILDREN_FILE = join(directory, 'children');
  try {
  for (const tools of [['read', 'web_search', 'bash', 'write', 'subagent'], ['read']]) {
    const h = harness(false, tools);
    child(h.pi);
    if (tools.includes('web_search')) {
      h.handlers.get('before_agent_start')();
      assert.deepEqual(h.active(), ['read', 'web_search']);
      assert.equal(h.handlers.get('tool_call')({ toolName: 'web_search' }), undefined);
      h.handlers.get('tool_result')({ toolName: 'web_search', isError: true });
      h.handlers.get('tool_result')({ toolName: 'web_search', isError: false,
        details: { error: 'unsupported_model' } });
      h.handlers.get('tool_result')({ toolName: 'web_search', isError: false });
      const evidence = readFileSync(process.env.TEJUN_CHILDREN_FILE + '.search.jsonl', 'utf8');
      assert.match(evidence, /failed/);
      assert.match(evidence, /succeeded/);
      assert.equal(evidence.split('\n').filter(line => line.includes('"failed"')).length, 2);
    } else assert.throws(() => h.handlers.get('before_agent_start')(), /requires/);
    for (const toolName of ['bash', 'write', 'edit', 'subagent', 'codemode'])
      assert.equal(h.handlers.get('tool_call')({ toolName }).block, true);
  }
  } finally {
    if (previous === undefined) delete process.env.TEJUN_CHILDREN_FILE;
    else process.env.TEJUN_CHILDREN_FILE = previous;
    rmSync(directory, { recursive: true, force: true });
  }
});
