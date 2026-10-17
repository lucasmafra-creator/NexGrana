(() => {
  const apiRoot = '/api/v1';
  const $ = (id) => document.getElementById(id);
  const esc = (value) => String(value ?? '').replace(/[&<>"']/g, (char) => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[char]));
  const sectors = [
    ['executive','CEO · Decisões','mesa'],['operations','Operações','fila'],['product','Produto','spec'],['ux','Feedback & UX','ux'],
    ['qa','QA','qa'],['build','Build & Release','build'],['performance','Performance','perf'],['offers','Ofertas & Parcerias','oferta'],
    ['red_team','Red Team','red'],['chaos_test','Chaos Test','chaos'],['analytics','Dados & Auditoria','dados'],['engineering','Engenharia','eng'],
    ['marketing','Marketing','growth'],['security','Segurança','sec']
  ];
  let snapshot = null;
  let timer = null;

  function schedulePolling(intervalMs = 30000) {
    if (timer) clearInterval(timer);
    timer = setInterval(() => load().catch(showError), intervalMs);
  }

  async function get(path, options = {}) {
    const headers = new Headers(options.headers || {});
    const token = sessionStorage.getItem('sim_session');
    if (token) headers.set('Authorization', `Bearer ${token}`);
    if (options.body) headers.set('Content-Type', 'application/json');
    const response = await fetch(`${apiRoot}${path}`, {...options, headers});
    const body = await response.json().catch(() => ({}));
    if (!response.ok) throw new Error(body.detail?.message || body.detail || `HTTP ${response.status}`);
    return body;
  }

  function showError(error) {
    const raw = String(error?.message || error);
    const networkFailure = error instanceof TypeError || /failed to fetch|networkerror|load failed/i.test(raw);
    $('error').textContent = networkFailure
      ? 'Conexão com a API perdida. O estado do QA não está confirmado; reconectando automaticamente.'
      : raw;
    $('error').classList.remove('hidden');
    if (networkFailure) {
      setText('pipeline-state','Conexão indisponível');
      $('run-pipeline').disabled = true;
      $('run-pipeline').textContent = 'Aguardando conexão';
      schedulePolling(5000);
    }
  }

  function setText(id, value) { $(id).textContent = String(value); }
  function asList(value) { return Array.isArray(value) ? value : []; }
  function isOpen(item) { return !['done','resolved','cancelled'].includes(String(item.status || '').toLowerCase()); }

  async function load() {
    $('error').classList.add('hidden');
    const token = sessionStorage.getItem('sim_session');
    if (!token) {
      $('auth-message').classList.remove('hidden');
      setText('pipeline-state','Entre na central');
      return;
    }
    $('auth-message').classList.add('hidden');
    const suffix = '?product_slug=nexgrana';
    const [company, inbox, releases, decisions, live, pipeline, daily] = await Promise.all([
      get(`/company${suffix}`),get(`/inbox${suffix}`),get(`/releases${suffix}`),get(`/decisions${suffix}`),
      get('/live/status'),get('/qa/pipeline/status'),get(`/daily${suffix}`)
    ]);
    snapshot = {company,inbox:asList(inbox),releases:asList(releases),decisions:asList(decisions),live,pipeline,daily:asList(daily)};
    render();
  }

  function render() {
    const {company,inbox,releases,decisions,pipeline} = snapshot;
    const tasks = asList(company.tasks);
    const criticalTasks = tasks.filter((item) => isOpen(item) && String(item.priority || '').toUpperCase() === 'P0');
    const blockedReleases = releases.filter((item) => item.status === 'blocked' || item.gate?.ready === false);
    const pendingDecisions = decisions.filter((item) => ['pending','defer','changes'].includes(item.status));
    const importantFeedback = inbox.filter((item) => isOpen(item) && ['P0','P1'].includes(String(item.priority || '').toUpperCase()));

    setText('critical-count',criticalTasks.length);
    setText('release-count',blockedReleases.length);
    setText('decision-count',pendingDecisions.length);
    setText('feedback-count',importantFeedback.length);
    setText('step-critical',criticalTasks.length ? `${criticalTasks.length} missão(ões) P0 em aberto; confira os títulos abaixo.` : 'Nenhuma missão P0 em aberto nos registros carregados.');
    setText('step-release',blockedReleases.length ? `${blockedReleases.length} release(s) com bloqueio de gate registrado.` : 'Nenhuma release bloqueada nos registros carregados.');
    setText('step-decision',pendingDecisions.length ? `${pendingDecisions.length} decisão(ões) aguardam sua análise.` : 'Nenhuma decisão pendente registrada.');
    setText('step-feedback',importantFeedback.length ? `${importantFeedback.length} feedback(s) P0/P1 ainda aberto(s).` : 'Nenhum feedback P0/P1 aberto nos registros carregados.');

    const openTasks = tasks.filter((item) => isOpen(item));
    const grouped = new Map();
    for (const task of openTasks) grouped.set(task.owner_sector || 'sem setor', (grouped.get(task.owner_sector || 'sem setor') || 0) + 1);
    const highest = [...grouped.entries()].sort((a,b) => b[1]-a[1])[0];
    setText('step-bottleneck',highest ? `Maior fila registrada: ${highest[0]} (${highest[1]} missão(ões) aberta(s)).` : 'Sem missões abertas para comparar gargalos.');
    setText('step-summary',`${criticalTasks.length} críticos P0 · ${blockedReleases.length} releases bloqueadas · ${pendingDecisions.length} aprovações pendentes · ${importantFeedback.length} feedbacks importantes.`);
    setText('updated-at',`Atualizado ${new Date().toLocaleTimeString('pt-BR',{hour:'2-digit',minute:'2-digit'})}`);

    $('approved-list').innerHTML = decisions.filter((item) => item.status === 'approve').slice(0,4).map((item) => `<div class="row"><b>${esc(item.title || item.release_version || 'Decisão')}</b> · ${esc(item.reason || 'sem motivo registrado')}</div>`).join('') || '<p>Nenhuma decisão aprovada registrada.</p>';
    const blockerNotes = [
      ...criticalTasks.slice(0,3).map((item) => `P0 · ${item.title}`),
      ...blockedReleases.slice(0,3).map((item) => `Release ${item.version || ''} · ${asList(item.gate?.blockers).join('; ') || item.status}`),
      ...importantFeedback.slice(0,3).map((item) => `Feedback ${item.human_id || ''} · ${item.title}`),
      ...asList(pipeline.blockers).slice(0,3).map((item) => `Pipeline · ${item}`)
    ];
    $('blocker-list').innerHTML = blockerNotes.map((item) => `<div class="row">${esc(item)}</div>`).join('') || '<p>Nenhum bloqueio nos dados carregados.</p>';

    const state = pipeline.status || 'NOT_RUN';
    setText('pipeline-state',state === 'RUNNING' ? 'Executando no clone QA' : state === 'NOT_RUN' ? 'Ainda não executado' : state);
    const testCounts = pipeline.summary ? `${pipeline.summary.tests_passed || 0} testes passaram · ${pipeline.summary.tests_blocked_or_failed || 0} bloqueados/falharam · ${pipeline.summary.native_builds_generated || 0} builds gerados` : 'Windows e Android só serão compilados se o host e os gates locais permitirem.';
    setText('pipeline-detail',testCounts);
    $('run-pipeline').disabled = state === 'RUNNING';
    $('run-pipeline').textContent = state === 'RUNNING' ? 'Executando…' : 'Executar QA';
    schedulePolling(state === 'RUNNING' ? 5000 : 30000);
    renderDepartments(company,tasks);
  }

  function renderDepartments(company,tasks) {
    const agents = new Map(asList(company.agents).map((item) => [item.department,item]));
    $('departments').innerHTML = sectors.map(([id,label,icon]) => {
      const agent = agents.get(id);
      const count = tasks.filter((task) => task.owner_sector === id && isOpen(task)).length;
      const mode = agent?.mode === 'automatic' ? 'Automação limitada' : agent?.mode === 'planned' ? 'Planejado / inativo' : 'Revisão / regras';
      return `<button class="department" data-sector="${esc(id)}" aria-label="Abrir setor ${esc(label)}"><span class="icon">${esc(icon)}</span><strong>${esc(label)}</strong><small>${count} tarefa(s) em aberto · ${esc(mode)}</small></button>`;
    }).join('');
    $('departments').querySelectorAll('[data-sector]').forEach((button) => button.addEventListener('click',() => selectDepartment(button.dataset.sector,button)));
    const first = $('departments').querySelector('[data-sector="executive"]');
    if (first) selectDepartment('executive',first);
  }

  function selectDepartment(id,button) {
    $('departments').querySelectorAll('.department').forEach((item) => item.classList.toggle('selected',item === button));
    const [,label] = sectors.find((item) => item[0] === id) || [id,id];
    const tasks = asList(snapshot.company.tasks).filter((task) => task.owner_sector === id && isOpen(task));
    let warning = '';
    if (id === 'red_team') warning = '<p class="warning">Segurança ofensiva automática está desativada. Não houve varredura nem ataque nesta execução.</p>';
    if (id === 'chaos_test') warning = '<p class="warning">Injeção de falhas está desativada. Este setor mantém plano QA e evidências quando autorizadas.</p>';
    if (id === 'executive') warning = '<p>Use a central principal para revisar decisões e liberar releases dentro dos gates.</p>';
    const list = tasks.length ? tasks.map((task) => `<article class="task"><b>${esc(task.title)}</b><small>${esc(task.human_id || task.priority || 'Sem prioridade registrada')} · ${esc(task.status)}</small><p>${esc(task.description || 'Sem descrição registrada.')}</p></article>`).join('') : '<p class="empty">Nenhuma tarefa aberta registrada para este setor.</p>';
    $('department-detail').innerHTML = `<h3>${esc(label)} · ${tasks.length} tarefa(s) aberta(s)</h3>${warning}${list}`;
  }

  async function startPipeline() {
    if (!sessionStorage.getItem('sim_session')) { $('auth-message').classList.remove('hidden'); return; }
    const ok = window.confirm('Iniciar o pipeline no clone SIM Labs QA? Ele pode criar ambientes virtuais e instalar dependências dentro do clone. Não altera SIM Labs oficial, não instala EXE/APK e não publica nada.');
    if (!ok) return;
    $('error').classList.add('hidden');
    $('run-pipeline').disabled = true;
    let accepted = false;
    try {
      await get('/qa/pipeline',{method:'POST'});
      accepted = true;
      await load();
    } catch (error) {
      showError(error);
      const networkFailure = error instanceof TypeError || /failed to fetch|networkerror|load failed/i.test(String(error?.message || error));
      if (accepted || networkFailure) {
        setText('pipeline-state','Confirmação pendente');
        $('run-pipeline').disabled = true;
        $('run-pipeline').textContent = 'Verificando execução…';
        schedulePolling(5000);
      } else {
        $('run-pipeline').disabled = false;
      }
    }
  }

  $('refresh').addEventListener('click',() => load().catch(showError));
  $('run-pipeline').addEventListener('click',startPipeline);
  window.addEventListener('storage',(event) => { if (event.key === 'sim_session') load().catch(showError); });
  load().catch(showError);
  schedulePolling(30000);
})();
