const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const { test } = require('node:test');
const vm = require('node:vm');

const script = fs.readFileSync(
  path.join(__dirname, '../../backend/static/gestao-hoje.js'),
  'utf8',
);

function makeHarness(fetchImpl) {
  const elements = new Map();
  const intervals = [];

  function element(id) {
    if (!elements.has(id)) {
      const classes = new Set();
      const listeners = new Map();
      elements.set(id, {
        id,
        textContent: '',
        innerHTML: '',
        disabled: false,
        classList: {
          add: (name) => classes.add(name),
          remove: (name) => classes.delete(name),
          contains: (name) => classes.has(name),
        },
        addEventListener: (name, callback) => listeners.set(name, callback),
        dispatch: (name) => listeners.get(name)?.(),
        querySelectorAll: () => [],
        querySelector: () => null,
      });
    }
    return elements.get(id);
  }

  const context = {
    document: { getElementById: element },
    sessionStorage: { getItem: (key) => key === 'sim_session' ? 'qa-test-token' : null },
    fetch: fetchImpl,
    Headers,
    TypeError,
    setInterval: (callback, delay) => {
      intervals.push({ callback, delay });
      return intervals.length;
    },
    clearInterval: () => {},
    window: { confirm: () => true, addEventListener: () => {} },
  };

  vm.runInNewContext(script, context, { filename: 'gestao-hoje.js' });
  return { element, intervals };
}

function jsonResponse(body, status = 200) {
  return { ok: status >= 200 && status < 300, status, json: async () => body };
}

function successfulGet(url) {
  if (url.includes('/company')) return { tasks: [], agents: [] };
  if (url.includes('/inbox') || url.includes('/releases') || url.includes('/decisions') || url.includes('/daily')) return [];
  if (url.includes('/qa/pipeline/status')) return { status: 'NOT_RUN' };
  return { status: 'ok' };
}

const tick = () => new Promise((resolve) => setImmediate(resolve));

test('falha de conexão remove o estado RUNNING antigo e bloqueia novo disparo', async () => {
  const h = makeHarness(async (url) => {
    if (url.endsWith('/qa/pipeline/status')) throw new TypeError('Failed to fetch');
    return jsonResponse(successfulGet(url));
  });
  h.element('pipeline-state').textContent = 'Executando no clone QA';
  h.element('run-pipeline').textContent = 'Executando…';
  h.element('run-pipeline').disabled = true;

  await tick();

  assert.equal(h.element('pipeline-state').textContent, 'Conexão indisponível');
  assert.equal(h.element('run-pipeline').textContent, 'Aguardando conexão');
  assert.equal(h.element('run-pipeline').disabled, true);
  assert.match(h.element('error').textContent, /conexão com a API/i);
});

test('resposta perdida após aceitar o QA não libera um segundo disparo', async () => {
  let accepted = false;
  let postCount = 0;
  const h = makeHarness(async (url, options = {}) => {
    if (options.method === 'POST') {
      postCount += 1;
      accepted = true;
      return jsonResponse({ status: 'RUNNING' }, 202);
    }
    if (accepted && url.endsWith('/qa/pipeline/status')) throw new TypeError('Failed to fetch');
    return jsonResponse(successfulGet(url));
  });

  await tick();
  await h.element('run-pipeline').dispatch('click');

  assert.equal(postCount, 1);
  assert.equal(h.element('pipeline-state').textContent, 'Confirmação pendente');
  assert.equal(h.element('run-pipeline').textContent, 'Verificando execução…');
  assert.equal(h.element('run-pipeline').disabled, true);
  assert.ok(h.intervals.some((item) => item.delay === 5000));
});
