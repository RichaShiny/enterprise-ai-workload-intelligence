const byId = (id) => document.getElementById(id);
const formatPercent = (value) => value === null || value === undefined ? "Not yet measured" : `${Math.round(value * 100)}%`;
const formatNumber = (value, suffix = "") => value === null || value === undefined ? "—" : `${Number(value).toLocaleString()}${suffix}`;

async function loadInsights() {
  try {
    const response = await fetch('/insights');
    const data = await response.json();
    byId('events').textContent = formatNumber(data.events_recorded);
    byId('success').textContent = formatPercent(data.observed_success_rate);
    byId('latency').textContent = formatNumber(data.average_latency_ms, ' ms');
    byId('disagreements').textContent = formatNumber(data.shadow_recommendation_disagreements);
  } catch (_) {
    byId('events').textContent = 'Offline';
  }
}

function renderCandidates(candidates) {
  byId('candidates').innerHTML = candidates.map((candidate) => {
    const reason = candidate.eligible ? 'Meets the current policy limits.' : candidate.reasons.join(' ');
    const evidence = candidate.sample_count ? `${candidate.sample_count} matching executions · ${formatPercent(candidate.conservative_success_probability)} conservative success` : 'No qualifying observed history';
    return `<article class="candidate"><div class="candidate-top"><span class="candidate-name">${candidate.strategy.replaceAll('_', ' ')}</span><span class="badge ${candidate.eligible ? 'eligible' : 'excluded'}">${candidate.eligible ? 'Eligible' : 'Excluded'}</span></div><p>${reason}</p><div class="candidate-meta">${evidence}</div></article>`;
  }).join('');
}

byId('route-form').addEventListener('submit', async (event) => {
  event.preventDefault();
  const button = byId('evaluate');
  button.disabled = true;
  button.firstChild.textContent = 'Evaluating… ';
  const value = (id) => byId(id).value;
  const payload = {
    task_type: value('task_type'), complexity: value('complexity'), sensitivity: value('sensitivity'), risk_level: value('risk_level'),
    min_success_probability: Number(value('min_success_probability')), max_latency_ms: Number(value('max_latency_ms')),
  };
  try {
    const response = await fetch('/route', {method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify(payload)});
    if (!response.ok) throw new Error('The workload could not be evaluated.');
    const data = await response.json();
    byId('empty-state').hidden = true;
    byId('decision').hidden = false;
    byId('source').textContent = data.routing_source.replaceAll('_', ' ');
    byId('strategy').textContent = data.recommended_strategy.replaceAll('_', ' ');
    byId('note').textContent = data.note;
    byId('samples').textContent = formatNumber(data.sample_count);
    byId('match').textContent = data.match_level?.replaceAll('_', ' ') || 'Cold start';
    byId('confidence').textContent = formatPercent(data.conservative_success_probability);
    renderCandidates(data.candidates);
  } catch (error) {
    byId('source').textContent = error.message;
  } finally {
    button.disabled = false;
    button.firstChild.textContent = 'Evaluate routing strategy ';
  }
});

loadInsights();

async function loadProviderStatus() {
  const badge = byId('provider-status');
  try {
    const response = await fetch('/policy-assistant/provider-status');
    if (!response.ok) throw new Error('Provider status unavailable');
    const data = await response.json();
    if (data.status === 'ready') {
      badge.textContent = `Model summaries ready · ${data.model}`;
      badge.classList.add('provider-ready');
    } else {
      badge.textContent = 'Cited evidence only';
      badge.classList.remove('provider-ready');
    }
  } catch (_) {
    badge.textContent = 'Cited evidence only';
    badge.classList.remove('provider-ready');
  }
}

byId('policy-form').addEventListener('submit', async (event) => {
  event.preventDefault();
  const button = byId('ask-policy');
  button.disabled = true;
  button.firstChild.textContent = 'Retrieving… ';
  try {
    const value = (id) => byId(id).value;
    const response = await fetch('/decision-assistant', {
      method: 'POST', headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({
        question: value('policy-question'), department: value('policy-department') || null,
        task_type: value('task_type'), complexity: value('complexity'), sensitivity: value('sensitivity'), risk_level: value('risk_level'),
        min_success_probability: Number(value('min_success_probability')), max_latency_ms: Number(value('max_latency_ms')),
      }),
    });
    if (!response.ok) throw new Error('The decision question could not be answered.');
    const data = await response.json();
    const execution = data.execution;
    byId('policy-empty').hidden = true;
    byId('policy-result').hidden = false;
    const result = data.policy_result;
    byId('grounding').textContent = data.kind === 'policy' ? (result.grounded ? 'Grounded in approved evidence' : 'Abstained — insufficient evidence') : data.kind === 'routing' ? 'Current workload recommendation' : 'Scope limit reached';
    byId('policy-answer').textContent = result?.answer || data.answer;
    byId('policy-reason').textContent = result ? `${result.reason} Ranked with ${result.retrieval.ranking_method} retrieval.` : data.reason;
    byId('execution-status').textContent = execution.status.replaceAll('_', ' ');
    byId('execution-action').textContent = execution.next_action;
    byId('execution-reason').textContent = execution.route ? `${execution.reason} Route: ${execution.route.recommended_strategy.replaceAll('_', ' ')}.` : execution.reason;
    const summary = data.model_summary || {};
    const summaryPanel = byId('model-summary');
    if (summary.status === 'generated') {
      summaryPanel.hidden = false;
      byId('model-summary-answer').textContent = summary.answer;
      byId('model-summary-note').textContent = `Generated from the selected evidence with ${summary.provider} · ${summary.model}. Review the citations below before acting.`;
    } else {
      summaryPanel.hidden = true;
      byId('model-summary-answer').textContent = '';
      byId('model-summary-note').textContent = '';
    }
    if (result?.evidence?.length) {
      byId('policy-evidence').innerHTML = result.evidence.map((item) => `<article><strong>${item.title}</strong><span>${item.department} · version ${item.version} · relevance ${Math.round(item.relevance_score * 100)}%</span><p>${item.excerpt}</p></article>`).join('');
    } else if (data.kind === 'routing') {
      const routing = data.routing;
      byId('policy-evidence').innerHTML = `<article><strong>Current operating limits</strong><span>${routing.routing_source.replaceAll('_', ' ')}</span><p>Minimum success ${formatPercent(routing.policy?.min_success_probability)} · maximum latency ${formatNumber(routing.policy?.max_latency_ms, ' ms')} · ${routing.sample_count || 0} matching executions.</p></article>`;
    } else {
      byId('policy-evidence').innerHTML = '';
    }
  } catch (error) {
    byId('policy-empty').hidden = false;
    byId('policy-empty').textContent = error.message;
  } finally {
    button.disabled = false;
    button.firstChild.textContent = 'Ask the decision layer ';
  }
});

byId('run-evaluation').addEventListener('click', async () => {
  const button = byId('run-evaluation');
  button.disabled = true;
  button.firstChild.textContent = 'Running… ';
  try {
    const response = await fetch('/policy-assistant/evaluation');
    if (!response.ok) throw new Error('The demo evaluation could not be run.');
    const data = await response.json();
    byId('evaluation-summary').textContent = `${Math.round(data.retrieval_accuracy * 100)}% retrieval accuracy · ${Math.round(data.safe_abstention_rate * 100)}% safe abstention · ${data.cases} fixed demo cases.`;
  } catch (error) {
    byId('evaluation-summary').textContent = error.message;
  } finally {
    button.disabled = false;
    button.firstChild.textContent = 'Run demo evaluation ';
  }
});


function formatAuditTime(value) {
  if (!value) return 'Unknown time';
  const date = new Date(value);
  return Number.isNaN(date.valueOf()) ? value : date.toLocaleString();
}

function renderAuditHistory(records) {
  const container = byId('audit-records');
  container.replaceChildren();
  if (!records.length) {
    byId('audit-summary').textContent = 'No policy revisions have been evaluated yet.';
    return;
  }
  byId('audit-summary').textContent = `${records.length} recent release decision${records.length === 1 ? '' : 's'} · policy content is not retained here.`;
  records.forEach((record) => {
    const article = document.createElement('article');
    article.className = `audit-record ${record.passed ? 'passed' : 'blocked'}`;
    const heading = document.createElement('div');
    const status = document.createElement('strong');
    status.textContent = record.passed ? 'Passed release gate' : 'Blocked by release gate';
    const timestamp = document.createElement('span');
    timestamp.textContent = formatAuditTime(record.created_at);
    heading.append(status, timestamp);
    const details = document.createElement('p');
    const changed = [...(record.improvements || []), ...(record.regressions || [])];
    details.textContent = record.note || (changed.length ? `Metrics reviewed: ${changed.join(', ').replaceAll('_', ' ')}.` : 'No metric change recorded.');
    const fingerprint = document.createElement('span');
    fingerprint.className = 'audit-fingerprint';
    fingerprint.textContent = record.candidate_fingerprint ? `Release fingerprint ${record.candidate_fingerprint.slice(0, 20)}…` : 'Release fingerprint unavailable';
    article.append(heading, details, fingerprint);
    container.append(article);
  });
}

async function loadPolicyChangeHistory() {
  const button = byId('refresh-history');
  button.disabled = true;
  button.firstChild.textContent = 'Refreshing… ';
  try {
    const response = await fetch('/policy-assistant/change-history');
    if (!response.ok) throw new Error('Policy change history could not be loaded.');
    const data = await response.json();
    renderAuditHistory(data.records || []);
  } catch (error) {
    byId('audit-summary').textContent = error.message;
  } finally {
    button.disabled = false;
    button.firstChild.textContent = 'Refresh history ';
  }
}

byId('refresh-history').addEventListener('click', loadPolicyChangeHistory);
loadPolicyChangeHistory();
loadProviderStatus();
