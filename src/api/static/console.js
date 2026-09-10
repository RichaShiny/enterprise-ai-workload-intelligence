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
