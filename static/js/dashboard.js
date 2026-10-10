/**
 * ReverseLogix AI - Dashboard Orchestrator
 * feature/returns-dashboard
 */

import * as API from '/static/js/api-service.js';

// Application State
export const State = {
  currency: 'INR',
  useConversionRate: false,
  optimizeResult: null,
  productionResult: null,
  scenarioResult: null,
  allDecisions: {},
  allAssessments: {},
  allInventoryRows: [],
  currentTab: 'overview',
  prevInventoryTab: 'inventory',
  currentCapacity: 4,
  chartInstances: {}
};

export const $ = id => document.getElementById(id);

export function fmt(n, compact = false) {
  if (n == null || isNaN(n)) return '-';
  const sym = State.currency === 'INR' ? '\u20b9' : '$';
  const rate = (State.currency === 'INR' && State.useConversionRate) ? 83 : 1;
  const v = n * rate;
  const abs = Math.abs(v);
  const prefix = v < 0 ? '-' : '';
  if (compact && abs >= 1000) {
    return prefix + sym + (abs / 1000).toFixed(1) + 'k';
  }
  return prefix + sym + abs.toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
}

export const fmtPct = p => (p == null || isNaN(p)) ? '-' : (p > 0 ? '+' : '') + p.toFixed(1) + '%';
export const fmtShort = s => s ? s.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase()) : '-';
export const shortId = id => id ? id.replace('ret_demo_', '').replace(/_/g, '-').toUpperCase() : '-';
export const now = () => new Date().toLocaleTimeString('en-IN', { hour: '2-digit', minute: '2-digit', second: '2-digit' });

export function toast(msg, type = 'info') {
  const c = $('toast-container');
  if (!c) return;
  const t = document.createElement('div');
  t.className = `toast toast-${type}`;
  const icons = { success: 'OK', error: 'ERR', warn: 'WARN', info: 'INFO' };
  t.innerHTML = `<span>[${icons[type] || 'INFO'}]</span><span>${msg}</span>`;
  c.appendChild(t);
  setTimeout(() => t.remove(), 4500);
}

export function showLoading(msg) {
  const el = $('loading-overlay');
  if (el) el.style.display = 'flex';
  const msgEl = $('loading-msg');
  if (msgEl) msgEl.textContent = msg || 'Working...';
}

export function hideLoading() {
  const el = $('loading-overlay');
  if (el) el.style.display = 'none';
}

export function routeBadgeClass(r) {
  const m = {
    repair: 'badge-repair',
    refurbish: 'badge-refurbish',
    resell_secondary: 'badge-resell',
    harvest_parts: 'badge-harvest',
    return_to_supplier: 'badge-supplier',
    recycle: 'badge-recycle',
    dispose: 'badge-dispose',
    manual_assessment: 'badge-manual'
  };
  return m[r] || 'badge-ok';
}

export function setCurrency(curr) {
  State.currency = curr;
  const inrBtn = $('btn-curr-inr');
  const usdBtn = $('btn-curr-usd');
  if (inrBtn && usdBtn) {
    inrBtn.classList.toggle('active', curr === 'INR');
    usdBtn.classList.toggle('active', curr === 'USD');
  }
  document.querySelectorAll('.curr-sym').forEach(el => {
    el.textContent = curr === 'INR' ? '\u20b9' : '$';
  });

  if (State.optimizeResult) {
    renderKPIs(State.optimizeResult, State.allInventoryRows);
    renderOverviewAllocSummary(State.allInventoryRows);
    filterInventory();
    renderComparison(State.optimizeResult);
    renderAllocationTab(State.optimizeResult, State.allInventoryRows);
    renderCharts(State.optimizeResult, State.allInventoryRows);
    if (State.scenarioResult) {
      renderScenarioResults(State.scenarioResult, State.productionResult);
    }
  }
  toast(`Currency switched to ${curr}`, 'info');
}

export function switchTab(tabId) {
  State.currentTab = tabId;
  document.querySelectorAll('.tab-pane').forEach(p => p.classList.remove('active'));
  document.querySelectorAll('.nav-item').forEach(i => i.classList.remove('active'));

  const pane = $(`tab-${tabId}`);
  if (pane) pane.classList.add('active');

  const nav = document.querySelector(`.nav-item[data-tab="${tabId}"]`);
  if (nav) nav.classList.add('active');

  window.scrollTo({ top: 0, behavior: 'smooth' });

  if (tabId === 'charts' && State.optimizeResult) {
    setTimeout(() => renderCharts(State.optimizeResult, State.allInventoryRows), 50);
  } else if (tabId === 'comparison' && State.optimizeResult) {
    setTimeout(() => renderStrategyComparisonChart(State.optimizeResult), 50);
  }
}

export function updateStatus(cls, label) {
  const badge = $('status-badge');
  if (badge) badge.className = `status-badge status-${cls}`;
  const lbl = $('status-label');
  if (lbl) lbl.textContent = label;
  const upd = $('last-updated');
  if (upd) upd.textContent = 'Updated ' + now();
}

export function setSourceLabels() {
  document.querySelectorAll('.chart-src').forEach(el => {
    el.textContent = API.isAdapterMode() ? 'synthetic' : 'live';
    el.className = `chart-src ${API.isAdapterMode() ? 'synthetic' : ''}`;
  });
}

export async function init() {
  updateStatus('loading', 'Connecting...');
  try {
    const health = await API.checkHealth();
    if (health.live) {
      updateStatus('live', 'Live API');
      $('data-source-label').style.display = 'none';
      toast('Connected to live ReverseLogix API on port 8000', 'success');
    } else {
      updateStatus('synthetic', 'Synthetic Demo');
      $('data-source-label').style.display = 'inline-flex';
      toast('Backend unreachable - running with synthetic adapter', 'warn');
    }
    $('btn-seed-run').disabled = false;
    $('btn-refresh').disabled = false;
    setSourceLabels();
    await seedAndRun();
  } catch (e) {
    updateStatus('error', 'Error');
    toast('Initialisation error: ' + e.message, 'error');
  }
}

export async function seedAndRun() {
  showLoading('Seeding 10 canonical demonstration devices...');
  try {
    await API.seedDemoDevices();
    $('loading-msg').textContent = 'Running Knapsack recovery optimizer (K=4 slots)...';
    const result = await API.runOptimizer({ repair_capacity_slots: 4 });
    State.previousResult = State.productionResult;
    State.productionResult = result;
    State.optimizeResult = result;
    State.currentCapacity = 4;

    $('loading-msg').textContent = 'Enriching devices with engineering assessments...';
    await enrichAllocations(result.allocations);

    applyOptimizeResult(result);
    toast('Evaluated 10 devices & optimized 4 repair bench slots', 'success');
  } catch (e) {
    toast('Seed & optimize failed: ' + e.message, 'error');
  } finally {
    hideLoading();
  }
}

export async function refresh() {
  showLoading('Refreshing return recovery data...');
  try {
    const result = await API.runOptimizer({ repair_capacity_slots: State.currentCapacity });
    State.optimizeResult = result;
    State.productionResult = result;
    await enrichAllocations(result.allocations);
    applyOptimizeResult(result);
    toast('Recovery data refreshed from engine', 'success');
  } catch (e) {
    toast('Refresh failed: ' + e.message, 'error');
  } finally {
    hideLoading();
  }
}

async function enrichAllocations(allocations) {
  const enriched = [];
  for (const a of allocations) {
    let asm = State.allAssessments[a.return_id];
    if (!asm) {
      try {
        asm = await API.getAssessment(a.return_id);
        State.allAssessments[a.return_id] = asm;
      } catch (err) {
        asm = null;
      }
    }
    enriched.push({
      ...a,
      assessment: asm,
      condition: asm?.product_condition || 'defective',
      repairability: asm?.repair_probability != null ? Math.round(asm.repair_probability * 100) : 70,
      confidence: asm?.authenticity_risk != null ? Math.round((1 - asm.authenticity_risk) * 100) : 90,
      warranty_status: asm?.verified_warranty_eligible ? 'verified_eligible' : (asm?.warranty_status || 'expired'),
      authenticity_risk: asm?.authenticity_risk != null ? asm.authenticity_risk : 0.02,
      estimated_resale_value: asm?.potential_resale_value || a.expected_proceeds,
      estimated_repair_cost: asm?.estimated_repair_cost || a.expected_cost
    });
  }
  State.allInventoryRows = enriched;
}

function applyOptimizeResult(result) {
  const allocs = State.allInventoryRows;
  renderKPIs(result, allocs);
  renderOverviewAllocSummary(allocs);
  renderInventoryTable(allocs);
  renderAllocationTab(result, allocs);
  renderComparison(result);
  renderReviewQueue(allocs);
  renderCharts(result, allocs);

  $('badge-inventory').textContent = allocs.length;
  $('badge-repair').textContent = `${result.repair_slots_used}/${result.repair_capacity_slots}`;
  const reviewCount = allocs.filter(a => a.manual_review_required).length;
  $('badge-review').textContent = reviewCount;
}

function renderKPIs(result, allocs) {
  setKV('kv-total-devices', allocs.length);
  $('ks-total-devices').textContent = `${allocs.filter(a => !a.manual_review_required).length} auto-routed, ${allocs.filter(a => a.manual_review_required).length} held`;

  const totalNet = allocs.reduce((sum, a) => sum + a.expected_net_recovery, 0);
  const totalProceeds = allocs.reduce((sum, a) => sum + a.expected_proceeds, 0);
  const totalCosts = allocs.reduce((sum, a) => sum + a.expected_cost, 0);

  setKV('kv-net-recovery', fmt(totalNet));
  setKV('kv-proceeds', fmt(totalProceeds));
  setKV('kv-costs', fmt(totalCosts));

  const slotsUsed = result.repair_slots_used ?? allocs.filter(a => a.was_repair_selected).length;
  const slotsCap = result.repair_capacity_slots ?? 4;
  setKV('kv-repair-slots', `${slotsUsed} / ${slotsCap}`);
  $('ks-repair-slots').textContent = `${result.capacity_utilization_pct ?? 100}% bench utilisation`;

  const uplift = result.dollar_uplift_vs_cheapest ?? result.dollar_uplift_vs_fifo ?? 0;
  const upliftPct = result.pct_uplift_vs_cheapest ?? result.pct_uplift_vs_fifo ?? 0;
  setKV('kv-uplift', fmt(uplift));
  $('ks-uplift').textContent = fmtPct(upliftPct) + ' vs Cheapest-Repair';

  const reviewCount = allocs.filter(a => a.manual_review_required).length;
  setKV('kv-review', `${reviewCount} cases`);

  const fraudCount = allocs.filter(a => (a.authenticity_risk > 0.5) || (a.manual_review_reasons || []).some(r => r.includes('authenticity') || r.includes('counterfeit'))).length;
  setKV('kv-fraud', `${fraudCount} flagged`);
}

function setKV(id, val) {
  const el = $(id);
  if (!el) return;
  el.classList.remove('skeleton');
  el.textContent = val;
}

// OVERVIEW ALLOCATION MINI-TABLE
export function renderOverviewAllocSummary(allocs) {
  const container = $('overview-alloc-table-container');
  const empty = $('overview-empty');
  if (!allocs.length) {
    if (empty) empty.style.display = 'flex';
    return;
  }
  if (empty) empty.style.display = 'none';

  const rows = allocs.slice().sort((a,b) => b.expected_net_recovery - a.expected_net_recovery).slice(0, 8);
  container.innerHTML = `
    <table class="alloc-mini-table">
      <thead><tr>
        <th>Device</th>
        <th>Category</th>
        <th>Disposition</th>
        <th style="text-align:right">Net Recovery</th>
        <th style="text-align:center">Repair Bench</th>
        <th style="text-align:center">Status</th>
      </tr></thead>
      <tbody>
        ${rows.map(a => `
          <tr>
            <td>
              <div style="font-weight:600;font-size:0.83rem">${a.product_name ? a.product_name.replace('[Synthetic Demo] ', '').substring(0,40) : shortId(a.return_id)}</div>
              <div style="font-size:0.7rem;color:var(--text-muted)">${a.return_id}</div>
            </td>
            <td>${a.category || '-'}</td>
            <td><span class="badge ${routeBadgeClass(a.assigned_route)}">${fmtShort(a.assigned_route)}</span></td>
            <td style="text-align:right;font-family:monospace;font-weight:700;color:${a.expected_net_recovery >= 0 ? 'var(--accent-success)' : 'var(--accent-danger)'}">${fmt(a.expected_net_recovery)}</td>
            <td style="text-align:center">${a.was_repair_selected ? '<span class="badge badge-yes">Slot Awarded</span>' : '<span class="badge badge-no">Non-Repair</span>'}</td>
            <td style="text-align:center">${a.manual_review_required ? '<span class="badge badge-review">Held for Review</span>' : '<span class="badge badge-ok">Auto-Decided</span>'}</td>
          </tr>
        `).join('')}
      </tbody>
    </table>
  `;
}

// INVENTORY TABLE & FILTERING
export function renderInventoryTable(allocs) {
  filterInventory();
}

export function filterInventory() {
  const search = ($('inv-search')?.value || '').toLowerCase();
  const routeFilter = $('inv-filter-route')?.value || '';
  const reviewFilter = $('inv-filter-review')?.value || '';
  const repairFilter = $('inv-filter-repair')?.value || '';
  const sort = $('inv-sort')?.value || 'net_recovery_desc';

  let rows = (State.allInventoryRows || []).slice();
  if (search) {
    rows = rows.filter(a =>
      (a.return_id || '').toLowerCase().includes(search) ||
      (a.product_name || '').toLowerCase().includes(search) ||
      (a.category || '').toLowerCase().includes(search) ||
      (a.assessment?.defect_description || '').toLowerCase().includes(search)
    );
  }
  if (routeFilter) rows = rows.filter(a => a.assigned_route === routeFilter);
  if (reviewFilter !== '') rows = rows.filter(a => String(a.manual_review_required) === reviewFilter);
  if (repairFilter !== '') rows = rows.filter(a => String(a.was_repair_selected) === repairFilter);

  rows.sort((a, b) => {
    if (sort === 'net_recovery_desc') return b.expected_net_recovery - a.expected_net_recovery;
    if (sort === 'net_recovery_asc') return a.expected_net_recovery - b.expected_net_recovery;
    if (sort === 'incremental_benefit_desc') return b.repair_incremental_benefit - a.repair_incremental_benefit;
    if (sort === 'repair_cost_asc') return (a.estimated_repair_cost || a.expected_cost) - (b.estimated_repair_cost || b.expected_cost);
    if (sort === 'repairability_desc') return (b.repairability || 0) - (a.repairability || 0);
    if (sort === 'confidence_desc') return (b.confidence || 0) - (a.confidence || 0);
    return 0;
  });

  const empty = $('inv-empty');
  const table = $('inv-table');
  const tbody = $('inv-tbody');
  const countEl = $('inv-count');

  if (!rows.length) {
    if (empty) empty.style.display = 'flex';
    if (table) table.style.display = 'none';
    if (countEl) countEl.textContent = 'No matching devices';
    return;
  }
  if (empty) empty.style.display = 'none';
  if (table) table.style.display = 'table';
  if (countEl) countEl.textContent = `Showing ${rows.length} of ${State.allInventoryRows.length} returned devices`;

  const repairCandidates = State.allInventoryRows
    .filter(a => a.repair_feasible && a.repair_incremental_benefit > 0 && !a.manual_review_required)
    .sort((a, b) => b.repair_incremental_benefit - a.repair_incremental_benefit);

  const kSlots = State.optimizeResult?.repair_capacity_slots ?? 4;
  const slotMap = {};
  repairCandidates.slice(0, kSlots).forEach((a, idx) => {
    slotMap[a.return_id] = `Slot #${idx + 1}`;
  });

  tbody.innerHTML = rows.map(a => {
    const repFeasible = a.repair_feasible;
    const repSelected = a.was_repair_selected;
    const netColor = a.expected_net_recovery >= 0 ? 'var(--accent-success)' : 'var(--accent-danger)';
    const slotBadge = slotMap[a.return_id]
      ? `<span class="badge badge-yes">${slotMap[a.return_id]}</span>`
      : `<span class="badge badge-no">Unassigned</span>`;

    const condBadgeClass = {
      unopened: 'badge-ok',
      like_new: 'badge-ok',
      minor_damage: 'badge-refurbish',
      defective: 'badge-repair',
      major_damage: 'badge-danger'
    }[a.condition] || 'badge-ok';

    const authBadge = a.authenticity_risk > 0.5
      ? `<span class="badge badge-danger">High Risk (${Math.round(a.authenticity_risk * 100)}%)</span>`
      : `<span class="badge badge-ok">Normal (${Math.round(a.authenticity_risk * 100)}%)</span>`;

    const warrantyBadge = a.warranty_status === 'verified_eligible'
      ? `<span class="badge badge-yes">Verified Eligible</span>`
      : a.warranty_status === 'active'
        ? `<span class="badge badge-refurbish">Active (Reported)</span>`
        : `<span class="badge badge-no">Expired / None</span>`;

    return `
      <tr>
        <td><code style="font-size:0.75rem">${a.return_id}</code></td>
        <td>
          <div style="font-weight:600;font-size:0.83rem">${a.product_name ? a.product_name.replace('[Synthetic Demo] ', '').substring(0, 36) : shortId(a.return_id)}</div>
          <div style="font-size:0.7rem;color:var(--text-muted)">${a.category || ''}</div>
        </td>
        <td class="text-center"><span class="badge ${condBadgeClass}">${fmtShort(a.condition)}</span></td>
        <td class="text-center font-mono font-semibold">${a.repairability}%</td>
        <td class="text-center font-mono">${a.confidence}%</td>
        <td class="text-center">${warrantyBadge}</td>
        <td class="text-center">${authBadge}</td>
        <td class="text-right font-mono">${fmt(a.estimated_repair_cost || a.expected_cost)}</td>
        <td class="text-right font-mono">${fmt(a.estimated_resale_value || a.expected_proceeds)}</td>
        <td class="text-center"><span class="badge ${routeBadgeClass(a.assigned_route)}">${fmtShort(a.assigned_route)}</span></td>
        <td class="text-right font-mono font-bold" style="color:${netColor}">${fmt(a.expected_net_recovery)}</td>
        <td class="text-center">${slotBadge}</td>
        <td class="text-center">${a.manual_review_required ? '<span class="badge badge-review">Held for Review</span>' : '<span class="badge badge-ok">Auto-Decided</span>'}</td>
        <td class="text-center">
          <button class="btn btn-sm btn-secondary" onclick="App.openDeviceDetail('${a.return_id}')">Inspect</button>
        </td>
      </tr>
    `;
  }).join('');
}

export function exportInventoryCSV() {
  if (!State.allInventoryRows.length) { toast('No data to export', 'warn'); return; }
  const headers = ['return_id','product_name','category','condition','repairability_pct','confidence_pct','warranty_status','authenticity_risk','repair_cost','resale_value','assigned_route','expected_net_recovery','was_repair_selected','manual_review_required'];
  const rows = State.allInventoryRows.map(a => [
    a.return_id,
    `"${(a.product_name||'').replace(/"/g, '""')}"`,
    a.category,
    a.condition,
    a.repairability,
    a.confidence,
    a.warranty_status,
    a.authenticity_risk,
    a.estimated_repair_cost,
    a.estimated_resale_value,
    a.assigned_route,
    a.expected_net_recovery,
    a.was_repair_selected,
    a.manual_review_required
  ].join(','));
  const csv = [headers.join(','), ...rows].join('\n');
  const blob = new Blob([csv], { type: 'text/csv' });
  const url = URL.createObjectURL(blob);
  const link = document.createElement('a'); link.href = url; link.download = 'ReverseLogix_Inventory_Allocation.csv'; link.click();
  URL.revokeObjectURL(url);
  toast('Inventory CSV exported', 'success');
}

// DEVICE DETAIL & DECISION EXPLANATION (Feature B)
export async function openDeviceDetail(return_id) {
  showLoading('Retrieving physical assessment & route economics...');
  try {
    let dec = State.allDecisions[return_id];
    if (!dec) {
      dec = await API.getDecision(return_id);
      State.allDecisions[return_id] = dec;
    }
    let asm = State.allAssessments[return_id];
    if (!asm) {
      try {
        asm = await API.getAssessment(return_id);
        State.allAssessments[return_id] = asm;
      } catch (err) {
        asm = null;
      }
    }
    const alloc = State.allInventoryRows.find(a => a.return_id === return_id) || {};
    renderDeviceDetail(alloc, dec, asm);
    State.prevInventoryTab = State.currentTab;
    switchTab('device-detail');
  } catch (e) {
    toast('Could not open device detail: ' + e.message, 'error');
  } finally {
    hideLoading();
  }
}

export function openFirstDeviceDetail() {
  if (State.allInventoryRows.length) {
    openDeviceDetail(State.allInventoryRows[0].return_id);
  }
}

export function closeDeviceDetail() {
  switchTab(State.prevInventoryTab || 'inventory');
}

function renderDeviceDetail(alloc, dec, asm) {
  const title = alloc.product_name ? alloc.product_name.replace('[Synthetic Demo] ', '') : alloc.return_id;
  $('detail-title').textContent = title;
  $('detail-subtitle').textContent = `${alloc.return_id} • ${alloc.category || ''} • Disposition: ${fmtShort(alloc.assigned_route)}`;

  const routes = (dec.alternative_routes && dec.alternative_routes.length) ? dec.alternative_routes : [];

  const routeRows = routes.map(r => {
    const isSelected = r.route === dec.recommended_route || r.route === alloc.assigned_route;
    const netColor = r.expected_net_recovery >= 0 ? 'net-positive' : 'net-negative';
    return `
      <tr class="${isSelected ? 'route-selected' : ''} ${r.feasible === false ? 'route-infeasible' : ''}">
        <td>
          <span class="badge ${routeBadgeClass(r.route)}">${fmtShort(r.route)}</span>
          ${isSelected ? ' <strong style="color:var(--accent-primary)">[SELECTED]</strong>' : ''}
        </td>
        <td class="text-right">${r.feasible === false ? '<span class="badge badge-no">Infeasible</span>' : fmt(r.expected_recovered_value)}</td>
        <td class="text-right">${fmt(r.route_costs)}</td>
        <td class="text-right ${netColor}">${fmt(r.expected_net_recovery)}</td>
        <td style="font-size:0.75rem;color:var(--text-muted)">${r.feasibility_note || (r.feasible === false ? 'Policy / Technical Rejection' : 'Feasible')}</td>
      </tr>
    `;
  }).join('');

  // Evidence-based explanation
  let explanationText = '';
  if (dec.manual_review_required) {
    explanationText = `<strong>AUTOMATED DECISION SUSPENDED (MANUAL TRIAGE REQUIRED):</strong> This device was halted by system policy guardrails due to: <em>${dec.manual_review_reasons.join(', ')}</em>. Automated repair and resale are strictly blocked until verified by technical or legal review.`;
  } else if (alloc.assigned_route === 'repair') {
    const repairNet = fmt(alloc.expected_net_recovery);
    const bestFallbackNet = fmt(alloc.best_non_repair_net_recovery);
    const diff = fmt(alloc.repair_incremental_benefit);
    explanationText = `<strong>Repair was selected</strong> because its expected net recovery is <strong>${repairNet}</strong>, compared with <strong>${bestFallbackNet}</strong> from the best feasible alternative (<em>${fmtShort(alloc.best_non_repair_route)}</em>). The incremental financial difference is <strong>+${diff}</strong>. This option consumes 1 technician bench slot. The recommendation assumes the estimated repair success probability (${alloc.repairability}%) and resale secondary value (${fmt(alloc.estimated_resale_value)}) are accurate.`;
  } else {
    explanationText = `<strong>${fmtShort(alloc.assigned_route)} was selected</strong> because its expected net recovery of <strong>${fmt(alloc.expected_net_recovery)}</strong> strictly outperforms all alternatives. Repair was not assigned because its incremental benefit over this fallback is non-positive (${fmt(alloc.repair_incremental_benefit)}), successfully conserving technician bench capacity for high-margin repairs.`;
  }

  $('device-detail-content').innerHTML = `
    <div class="detail-layout">
      <!-- LEFT: Assessment & Engineering Intake -->
      <div>
        <div class="card mb-3">
          <div class="card-header">
            <h3 class="card-title">Engineering Assessment &amp; Intake</h3>
            <span class="badge ${routeBadgeClass(alloc.assigned_route)}">${fmtShort(alloc.assigned_route)}</span>
          </div>
          <div class="card-body">
            <div class="detail-field mb-2">
              <label>Observed Condition Grade</label>
              <div><span class="badge badge-ok">${fmtShort(alloc.condition)}</span> ${asm?.visible_damage ? '<span class="badge badge-danger">Visible Physical Damage</span>' : '<span class="badge badge-yes">No Visible Damage</span>'}</div>
            </div>

            <div class="detail-field mb-2">
              <label>Defect Category &amp; Observed Failure</label>
              <div><strong>${fmtShort(asm?.defect_category || 'Functional')}:</strong> ${asm?.defect_description || alloc.allocation_rationale}</div>
            </div>

            <div class="detail-field mb-2">
              <label>Repairability Score &amp; Bench Time</label>
              <div class="font-mono"><strong>${alloc.repairability}%</strong> probability of success • <strong>${asm?.estimated_repair_hours || alloc.repair_hours || 1.5} hrs</strong> bench time</div>
            </div>

            <div class="detail-field mb-2">
              <label>Warranty Verification Evidence</label>
              <div>
                ${alloc.warranty_status === 'verified_eligible'
                  ? '<span class="badge badge-yes">Verified Eligible (Manufacturer Direct Credit)</span>'
                  : alloc.warranty_status === 'active'
                    ? '<span class="badge badge-refurbish">Active (Self-reported)</span>'
                    : '<span class="badge badge-no">Expired / Out of Warranty</span>'}
              </div>
            </div>

            <div class="detail-field mb-2">
              <label>Authenticity &amp; Fraud Risk Score</label>
              <div>
                ${alloc.authenticity_risk > 0.5
                  ? `<span class="badge badge-danger">HIGH RISK (${Math.round(alloc.authenticity_risk * 100)}%) - Counterfeit / Serial Mismatch</span>`
                  : `<span class="badge badge-ok">Normal OEM Verified (${Math.round(alloc.authenticity_risk * 100)}% risk)</span>`}
              </div>
            </div>

            ${asm?.safety_hazard ? `
              <div class="alert-box alert-warning mt-2">
                <strong>SAFETY HAZARD DETECTED:</strong> Swollen lithium battery. Hazardous materials protocol engaged.
              </div>
            ` : ''}

            <div class="detail-field mt-3">
              <label>Technician Notes</label>
              <div style="font-size:0.85rem;color:var(--text-secondary);font-style:italic">"${asm?.assessor_notes || 'Standard reverse logistics inspection completed.'}"</div>
            </div>
          </div>
        </div>
      </div>

      <!-- RIGHT: Financial Route Comparison -->
      <div>
        <div class="card mb-3">
          <div class="card-header">
            <h3 class="card-title">Financial Route Comparison (7 Routes)</h3>
            <span class="card-subtitle">Expected proceeds vs route processing costs</span>
          </div>
          <div class="table-responsive">
            <table class="data-table">
              <thead>
                <tr>
                  <th>Disposition Route</th>
                  <th class="text-right">Expected Proceeds</th>
                  <th class="text-right">Route Costs</th>
                  <th class="text-right">Expected Net</th>
                  <th>Feasibility / Rejection Reason</th>
                </tr>
              </thead>
              <tbody>${routeRows}</tbody>
            </table>
          </div>
        </div>

        <!-- Evidence-Based Explanation Card -->
        <div class="card">
          <div class="card-header">
            <h3 class="card-title">Evidence-Based Decision Explanation</h3>
          </div>
          <div class="card-body">
            <div class="info-callout" style="background:rgba(79,142,255,0.08);border-left:3px solid var(--accent-primary)">
              <p style="font-size:0.9rem;line-height:1.6">${explanationText}</p>
            </div>
          </div>
        </div>
      </div>
    </div>
  `;
}

// REPAIR CAPACITY ALLOCATION (Feature C)
export function renderAllocationTab(result, allocs) {
  const k = result.repair_capacity_slots ?? 4;
  const used = result.repair_slots_used ?? allocs.filter(a => a.was_repair_selected).length;
  const rem = Math.max(0, k - used);

  $('alloc-stat-total').textContent = allocs.length;
  $('alloc-stat-cap').textContent = `${k} slots`;
  $('alloc-stat-used').textContent = `${used} slots`;
  $('alloc-stat-rem').textContent = `${rem} slots`;
  $('alloc-stat-pct').textContent = `${result.capacity_utilization_pct ?? 100}%`;

  const repairCandidates = allocs
    .filter(a => a.repair_feasible && a.repair_incremental_benefit > 0 && !a.manual_review_required)
    .sort((a, b) => b.repair_incremental_benefit - a.repair_incremental_benefit);

  const selectedRepairs = repairCandidates.slice(0, k);

  // Render Visual Bench Cards
  const benchContainer = $('bench-slots-visual');
  if (benchContainer) {
    let benchHTML = '';
    for (let i = 0; i < k; i++) {
      const dev = selectedRepairs[i];
      if (dev) {
        benchHTML += `
          <div class="bench-slot-card bench-slot-occupied">
            <div class="bench-slot-badge">Bench Slot #${i + 1}</div>
            <h4 class="bench-slot-title">${dev.product_name ? dev.product_name.replace('[Synthetic Demo] ', '') : dev.return_id}</h4>
            <div class="bench-slot-id font-mono">${dev.return_id} • ${dev.category}</div>
            <div class="bench-slot-metric-row mt-2">
              <div>
                <span class="text-muted" style="font-size:0.75rem">Net Recovery</span>
                <div class="font-bold text-success">${fmt(dev.expected_net_recovery)}</div>
              </div>
              <div>
                <span class="text-muted" style="font-size:0.75rem">Incremental Lift</span>
                <div class="font-bold text-primary">+${fmt(dev.repair_incremental_benefit)}</div>
              </div>
            </div>
          </div>
        `;
      } else {
        benchHTML += `
          <div class="bench-slot-card bench-slot-empty">
            <div class="bench-slot-badge" style="background:rgba(255,255,255,0.1)">Bench Slot #${i + 1}</div>
            <h4 class="bench-slot-title" style="color:var(--text-muted)">Unused Capacity</h4>
            <div style="font-size:0.8rem;color:var(--text-muted);margin-top:8px">No additional devices provide positive incremental repair benefit.</div>
          </div>
        `;
      }
    }
    benchContainer.innerHTML = benchHTML;
  }

  // Render Candidate Ranking Table
  const tbody = $('alloc-table-tbody');
  if (tbody) {
    const sortedAll = allocs.slice().sort((a, b) => (b.repair_incremental_benefit || 0) - (a.repair_incremental_benefit || 0));
    tbody.innerHTML = sortedAll.map((a, idx) => {
      const slotAssigned = a.was_repair_selected;
      return `
        <tr style="${slotAssigned ? 'background:rgba(79,142,255,0.06)' : ''}">
          <td class="font-mono">#${idx + 1}</td>
          <td>
            <div style="font-weight:600">${a.product_name ? a.product_name.replace('[Synthetic Demo] ', '') : a.return_id}</div>
            <div style="font-size:0.7rem;color:var(--text-muted)">${a.return_id}</div>
          </td>
          <td>${a.category}</td>
          <td class="text-right font-mono">${a.repair_feasible ? fmt(a.expected_net_recovery) : '<span class="text-muted">-</span>'}</td>
          <td><span class="badge ${routeBadgeClass(a.best_non_repair_route)}">${fmtShort(a.best_non_repair_route)}</span></td>
          <td class="text-right font-mono">${fmt(a.best_non_repair_net_recovery)}</td>
          <td class="text-right font-mono font-bold" style="color:${a.repair_incremental_benefit > 0 ? 'var(--accent-success)' : 'var(--accent-danger)'}">
            ${a.repair_feasible ? '+' + fmt(a.repair_incremental_benefit) : '<span class="text-muted">-</span>'}
          </td>
          <td class="text-center">${slotAssigned ? '<span class="badge badge-yes">Awarded Slot</span>' : '<span class="badge badge-no">Non-Repair</span>'}</td>
          <td style="font-size:0.8rem;color:var(--text-secondary)">${a.allocation_rationale}</td>
        </tr>
      `;
    }).join('');
  }
}

// BASELINE VS OPTIMIZED COMPARISON (Feature E)
export function renderComparison(result) {
  const optNet = result.optimized_total_net_recovery;
  const fifoNet = result.baseline_fifo_net_recovery;
  const cheapNet = result.baseline_cheapest_repair_net_recovery;
  const upperNet = result.baseline_unconstrained_net_recovery;

  $('cmp-opt-net').textContent = fmt(optNet);
  $('cmp-fifo-net').textContent = fmt(fifoNet);
  $('cmp-cheapest-net').textContent = fmt(cheapNet);
  $('cmp-upper-net').textContent = fmt(upperNet);

  const fifoDiff = optNet - fifoNet;
  const fifoPct = fifoNet > 0 ? (fifoDiff / fifoNet) * 100 : 0;
  $('cmp-fifo-diff').textContent = `+${fmt(fifoDiff)} uplift`;
  $('cmp-fifo-pct').textContent = `+${fifoPct.toFixed(1)}% improvement`;

  const cheapDiff = optNet - cheapNet;
  const cheapPct = cheapNet > 0 ? (cheapDiff / cheapNet) * 100 : 0;
  $('cmp-cheapest-diff').textContent = `+${fmt(cheapDiff)} uplift`;
  $('cmp-cheapest-pct').textContent = `+${cheapPct.toFixed(1)}% improvement`;

  renderStrategyComparisonChart(result);
}

function renderStrategyComparisonChart(result) {
  destroyChart('chart-strategy-comparison');
  const canvas = $('chart-strategy-comparison');
  if (!canvas) return;

  const labels = [
    'Optimized (K=4 Knapsack)',
    'FIFO Arrival Baseline',
    'Cheapest-Repair First',
    'Unconstrained Upper Bound'
  ];
  const data = [
    result.optimized_total_net_recovery,
    result.baseline_fifo_net_recovery,
    result.baseline_cheapest_repair_net_recovery,
    result.baseline_unconstrained_net_recovery
  ];
  const colors = ['#4f8eff', '#7c5ffc', '#f5a623', '#22d3a044'];

  State.chartInstances['chart-strategy-comparison'] = new Chart(canvas, {
    type: 'bar',
    data: {
      labels,
      datasets: [{
        label: 'Total Expected Net Recovery',
        data,
        backgroundColor: colors,
        borderRadius: 6
      }]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: { display: false },
        tooltip: { callbacks: { label: ctx => ' Net Recovery: ' + fmt(ctx.raw) } }
      },
      scales: {
        x: { grid: { color: 'rgba(255,255,255,0.05)' } },
        y: { grid: { color: 'rgba(255,255,255,0.05)' }, ticks: { callback: v => fmt(v, true) } }
      }
    }
  });
}

// CHARTS (Feature D: Charts A-F)
function destroyChart(id) {
  if (State.chartInstances[id]) {
    State.chartInstances[id].destroy();
    delete State.chartInstances[id];
  }
}

export function renderCharts(result, allocs) {
  if (!allocs || !allocs.length) return;
  renderDispositionDonut(allocs, 'chart-disposition');
  renderDispositionDonut(allocs, 'chart-overview-donut');
  renderNetRecoveryBar(allocs, 'chart-net-recovery');
  renderNetRecoveryBar(allocs, 'chart-overview-recovery');
  renderRouteComparison(allocs, 'chart-route-comparison');
  renderCostProceeds(allocs, 'chart-cost-proceeds');
  renderRepairSlotChart(allocs, result, 'chart-repair-slots');
  renderRiskOverview(allocs, result, 'chart-risk-overview');
}

// Chart A: Disposition Distribution
function renderDispositionDonut(allocs, canvasId) {
  destroyChart(canvasId);
  const canvas = $(canvasId);
  if (!canvas) return;

  const counts = {};
  allocs.forEach(a => { counts[a.assigned_route] = (counts[a.assigned_route] || 0) + 1; });
  const labels = Object.keys(counts).map(fmtShort);
  const data = Object.values(counts);
  const colorMap = {
    repair: '#4f8eff',
    refurbish: '#7c5ffc',
    harvest_parts: '#f5a623',
    return_to_supplier: '#38bdf8',
    resell_secondary: '#22d3a0',
    recycle: '#8899cc',
    dispose: '#4a5880',
    manual_assessment: '#ff5c72'
  };
  const bg = Object.keys(counts).map(r => colorMap[r] || '#8899cc');

  State.chartInstances[canvasId] = new Chart(canvas, {
    type: 'doughnut',
    data: { labels, datasets: [{ data, backgroundColor: bg, borderColor: 'transparent', hoverOffset: 6 }] },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      cutout: '60%',
      plugins: {
        legend: { position: 'right', labels: { boxWidth: 12, padding: 12, font: { size: 11 } } },
        tooltip: { callbacks: { label: ctx => ` ${ctx.label}: ${ctx.raw} devices` } }
      }
    }
  });
}

// Chart B: Net Recovery by Device
function renderNetRecoveryBar(allocs, canvasId) {
  destroyChart(canvasId);
  const canvas = $(canvasId);
  if (!canvas) return;

  const sorted = allocs.slice().sort((a,b) => b.expected_net_recovery - a.expected_net_recovery);
  const labels = sorted.map(a => a.product_name ? a.product_name.replace('[Synthetic Demo] ', '').substring(0, 20) : shortId(a.return_id));
  const data = sorted.map(a => a.expected_net_recovery);
  const colors = data.map(v => v >= 0 ? '#22d3a0' : '#ff5c72');

  State.chartInstances[canvasId] = new Chart(canvas, {
    type: 'bar',
    data: { labels, datasets: [{ label: 'Expected Net Recovery', data, backgroundColor: colors, borderRadius: 4 }] },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      indexAxis: 'y',
      plugins: {
        legend: { display: false },
        tooltip: { callbacks: { label: ctx => ' Net Recovery: ' + fmt(ctx.raw) } }
      },
      scales: {
        x: { grid: { color: 'rgba(255,255,255,0.05)' }, ticks: { callback: v => fmt(v, true) } },
        y: { grid: { display: false }, ticks: { font: { size: 10 } } }
      }
    }
  });
}

// Chart C: Route Comparison
function renderRouteComparison(allocs, canvasId) {
  destroyChart(canvasId);
  const canvas = $(canvasId);
  if (!canvas) return;

  const candidates = allocs.filter(a => a.repair_feasible && !a.manual_review_required);
  if (!candidates.length) return;

  const labels = candidates.map(a => a.product_name ? a.product_name.replace('[Synthetic Demo] ', '').substring(0, 18) : shortId(a.return_id));
  State.chartInstances[canvasId] = new Chart(canvas, {
    type: 'bar',
    data: {
      labels,
      datasets: [
        { label: 'Selected Route Net Recovery', data: candidates.map(a => a.expected_net_recovery), backgroundColor: '#4f8eff', borderRadius: 4 },
        { label: 'Best Non-Repair Alternative', data: candidates.map(a => a.best_non_repair_net_recovery), backgroundColor: 'rgba(34,211,160,0.35)', borderColor: '#22d3a0', borderWidth: 1.5, borderRadius: 4 }
      ]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: { position: 'top', labels: { boxWidth: 12 } },
        tooltip: { callbacks: { label: ctx => ` ${ctx.dataset.label}: ${fmt(ctx.raw)}` } }
      },
      scales: {
        x: { grid: { color: 'rgba(255,255,255,0.05)' } },
        y: { grid: { color: 'rgba(255,255,255,0.05)' }, ticks: { callback: v => fmt(v, true) } }
      }
    }
  });
}

// Chart D: Cost vs Proceeds
function renderCostProceeds(allocs, canvasId) {
  destroyChart(canvasId);
  const canvas = $(canvasId);
  if (!canvas) return;

  const sorted = allocs.slice().sort((a,b) => b.expected_proceeds - a.expected_proceeds);
  const labels = sorted.map(a => a.product_name ? a.product_name.replace('[Synthetic Demo] ', '').substring(0, 16) : shortId(a.return_id));

  State.chartInstances[canvasId] = new Chart(canvas, {
    type: 'bar',
    data: {
      labels,
      datasets: [
        { label: 'Expected Gross Proceeds', data: sorted.map(a => a.expected_proceeds), backgroundColor: '#22d3a0cc', borderRadius: 4 },
        { label: 'Processing & Route Costs', data: sorted.map(a => a.expected_cost), backgroundColor: '#ff5c72cc', borderRadius: 4 }
      ]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: { position: 'top', labels: { boxWidth: 12 } },
        tooltip: { callbacks: { label: ctx => ` ${ctx.dataset.label}: ${fmt(ctx.raw)}` } }
      },
      scales: {
        x: { grid: { color: 'rgba(255,255,255,0.05)' } },
        y: { grid: { color: 'rgba(255,255,255,0.05)' }, ticks: { callback: v => fmt(v, true) } }
      }
    }
  });
}

// Chart E: Repair Allocation & Knapsack Cutoff
function renderRepairSlotChart(allocs, result, canvasId) {
  destroyChart(canvasId);
  const canvas = $(canvasId);
  if (!canvas) return;

  const eligible = allocs
    .filter(a => a.repair_feasible && !a.manual_review_required)
    .sort((a, b) => b.repair_incremental_benefit - a.repair_incremental_benefit);

  const k = result.repair_capacity_slots ?? 4;
  const labels = eligible.map(a => a.product_name ? a.product_name.replace('[Synthetic Demo] ', '').substring(0, 16) : shortId(a.return_id));
  const data = eligible.map(a => a.repair_incremental_benefit);
  const colors = eligible.map((a, i) => i < k && a.repair_incremental_benefit > 0 ? '#4f8eff' : a.repair_incremental_benefit > 0 ? 'rgba(79,142,255,0.3)' : '#ff5c72');

  State.chartInstances[canvasId] = new Chart(canvas, {
    type: 'bar',
    data: { labels, datasets: [{ label: 'Incremental Repair Benefit', data, backgroundColor: colors, borderRadius: 4 }] },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: { display: false },
        tooltip: { callbacks: { label: ctx => ` Incremental Lift: +${fmt(ctx.raw)}` } }
      },
      scales: {
        x: { grid: { color: 'rgba(255,255,255,0.05)' } },
        y: { grid: { color: 'rgba(255,255,255,0.05)' }, ticks: { callback: v => fmt(v, true) } }
      }
    }
  });
}

// Chart F: Risk & Review Overview
function renderRiskOverview(allocs, result, canvasId) {
  destroyChart(canvasId);
  const canvas = $(canvasId);
  if (!canvas) return;

  const reviewTotal = allocs.filter(a => a.manual_review_required).length;
  const autoOk = allocs.length - reviewTotal;
  const counterfeit = allocs.filter(a => a.authenticity_risk > 0.5).length;
  const safety = allocs.filter(a => (a.manual_review_reasons || []).some(r => r.includes('Safety') || r.includes('swollen'))).length;

  State.chartInstances[canvasId] = new Chart(canvas, {
    type: 'doughnut',
    data: {
      labels: ['Auto-Decided (Normal)', 'Counterfeit Suspected', 'Battery Thermal Hazard'],
      datasets: [{
        data: [autoOk, counterfeit, safety],
        backgroundColor: ['#22d3a0', '#ff5c72', '#f5a623'],
        borderColor: 'transparent',
        hoverOffset: 6
      }]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      cutout: '55%',
      plugins: { legend: { position: 'bottom', labels: { boxWidth: 12, padding: 10 } } }
    }
  });

  const legend = $('risk-legend');
  if (legend) {
    legend.innerHTML = `
      <div class="risk-legend-item"><div class="risk-legend-dot" style="background:#22d3a0"></div> Auto-Decided: ${autoOk}</div>
      <div class="risk-legend-item"><div class="risk-legend-dot" style="background:#ff5c72"></div> Counterfeit Flagged: ${counterfeit}</div>
      <div class="risk-legend-item"><div class="risk-legend-dot" style="background:#f5a623"></div> Hazmat Hazard: ${safety}</div>
      <div class="risk-legend-item"><div class="risk-legend-dot" style="background:#4f8eff"></div> Total In Review: ${reviewTotal}</div>
    `;
  }
}

// WHAT-IF SIMULATOR (Feature F)
export function updateSimCapacityDisplay() {
  const val = $('sim-capacity-slider')?.value || 4;
  $('sim-cap-display').textContent = `${val} slots`;
}

export function updateSimCostDisplay() {
  const val = $('sim-cost-slider')?.value || 1.0;
  $('sim-cost-display').textContent = `${val}x (${val == 1.0 ? 'Baseline' : val > 1.0 ? '+' + Math.round((val - 1.0) * 100) + '%' : Math.round((val - 1.0) * 100) + '%'})`;
}

export function updateSimResaleDisplay() {
  const val = $('sim-resale-slider')?.value || 1.0;
  $('sim-resale-display').textContent = `${val}x (${val == 1.0 ? 'Baseline' : val > 1.0 ? '+' + Math.round((val - 1.0) * 100) + '%' : Math.round((val - 1.0) * 100) + '%'})`;
}

export function setScenarioCapacity(k) {
  const slider = $('sim-capacity-slider');
  if (slider) slider.value = k;
  updateSimCapacityDisplay();
  runScenario();
}

export async function runScenario() {
  const k = parseInt($('sim-capacity-slider')?.value || '4', 10);
  const costMult = parseFloat($('sim-cost-slider')?.value || '1.0');
  const resaleMult = parseFloat($('sim-resale-slider')?.value || '1.0');

  showLoading(`Simulating scenario (Capacity K=${k}, Costs ${costMult}x, Resale ${resaleMult}x)...`);
  try {
    const customCosts = { cost_multiplier: costMult, resale_multiplier: resaleMult };
    const scenarioRes = await API.runOptimizer({ repair_capacity_slots: k, custom_costs: customCosts });
    State.scenarioResult = scenarioRes;
    renderScenarioResults(scenarioRes, State.productionResult || State.optimizeResult);
    toast(`Scenario K=${k} calculated successfully`, 'success');
  } catch (e) {
    toast('Scenario simulation failed: ' + e.message, 'error');
  } finally {
    hideLoading();
  }
}

export function resetSimulator() {
  const cap = $('sim-capacity-slider');
  const cost = $('sim-cost-slider');
  const resale = $('sim-resale-slider');
  if (cap) cap.value = 4;
  if (cost) cost.value = 1.0;
  if (resale) resale.value = 1.0;
  updateSimCapacityDisplay();
  updateSimCostDisplay();
  updateSimResaleDisplay();
  $('sim-outcome-panel').style.display = 'none';
  $('sim-diff-card').style.display = 'none';
  State.scenarioResult = null;
  toast('Simulator reset to baseline production parameters', 'info');
}

export function runPresetK2() {
  switchTab('simulator');
  setScenarioCapacity(2);
}

function renderScenarioResults(scenarioRes, baseRes) {
  $('sim-outcome-panel').style.display = 'grid';
  $('sim-diff-card').style.display = 'block';

  const sNet = scenarioRes.optimized_total_net_recovery;
  const bNet = baseRes.optimized_total_net_recovery;
  const delta = sNet - bNet;

  $('sim-res-net').textContent = fmt(sNet);
  $('sim-res-diff').textContent = `${delta >= 0 ? '+' : ''}${fmt(delta)} vs baseline (${delta >= 0 ? '+' : ''}${fmtPct((delta / bNet) * 100)})`;
  $('sim-res-slots').textContent = `${scenarioRes.repair_slots_used} / ${scenarioRes.repair_capacity_slots} slots`;
  $('sim-res-util').textContent = `${scenarioRes.capacity_utilization_pct}% capacity utilization`;

  const sAllocs = scenarioRes.allocations;
  const bAllocs = baseRes.allocations;
  let changedCount = 0;

  const tbody = $('sim-diff-tbody');
  tbody.innerHTML = sAllocs.map(sa => {
    const ba = bAllocs.find(b => b.return_id === sa.return_id) || {};
    const changed = sa.assigned_route !== ba.assigned_route;
    if (changed) changedCount++;
    const devDelta = sa.expected_net_recovery - ba.expected_net_recovery;

    return `
      <tr style="${changed ? 'background:rgba(245,166,35,0.08)' : ''}">
        <td>
          <div style="font-weight:600">${sa.product_name ? sa.product_name.replace('[Synthetic Demo] ', '') : sa.return_id}</div>
          <div style="font-size:0.7rem;color:var(--text-muted)">${sa.return_id}</div>
        </td>
        <td><span class="badge ${routeBadgeClass(ba.assigned_route)}">${fmtShort(ba.assigned_route)}</span></td>
        <td><span class="badge ${routeBadgeClass(sa.assigned_route)}">${fmtShort(sa.assigned_route)}</span></td>
        <td>
          ${changed
            ? '<span class="badge badge-warning">Disposition Changed</span>'
            : '<span class="badge badge-ok">Unchanged</span>'}
        </td>
        <td class="text-right font-mono">${fmt(ba.expected_net_recovery)}</td>
        <td class="text-right font-mono">${fmt(sa.expected_net_recovery)}</td>
        <td class="text-right font-mono font-bold" style="color:${devDelta >= 0 ? 'var(--accent-success)' : 'var(--accent-danger)'}">
          ${devDelta >= 0 ? '+' : ''}${fmt(devDelta)}
        </td>
        <td style="font-size:0.8rem;color:var(--text-secondary)">${sa.allocation_rationale}</td>
      </tr>
    `;
  }).join('');

  $('sim-res-changed').textContent = `${changedCount} devices`;
}

// MANUAL REVIEW QUEUE (Feature G)
export function renderReviewQueue(allocs) {
  const container = $('review-cards-container');
  if (!container) return;

  const reviewCases = allocs.filter(a => a.manual_review_required);
  if (!reviewCases.length) {
    container.innerHTML = '<div class="empty-state"><p>No returns currently require manual review.</p></div>';
    return;
  }

  container.innerHTML = reviewCases.map(c => {
    const isCounterfeit = c.authenticity_risk > 0.5 || (c.manual_review_reasons||[]).some(r => r.includes('authenticity') || r.includes('counterfeit'));
    const isBattery = (c.manual_review_reasons||[]).some(r => r.includes('Safety') || r.includes('swollen') || r.includes('battery'));

    return `
      <div class="review-card">
        <div class="review-card-header">
          <div>
            <h4 class="review-card-title">${c.product_name ? c.product_name.replace('[Synthetic Demo] ', '') : c.return_id}</h4>
            <div class="font-mono text-muted" style="font-size:0.75rem">${c.return_id} • Category: ${c.category}</div>
          </div>
          <span class="badge badge-danger">Policy Guardrail Hold</span>
        </div>
        <div class="review-card-body">
          <div class="review-detail-grid">
            <div>
              <span class="text-muted" style="font-size:0.75rem">Triggered Reason</span>
              <div class="font-semibold text-danger">${c.manual_review_reasons.join('; ')}</div>
            </div>
            <div>
              <span class="text-muted" style="font-size:0.75rem">Risk &amp; Confidence</span>
              <div class="font-mono">Authenticity Risk: <strong>${Math.round((c.authenticity_risk||0.94)*100)}%</strong> • Confidence: <strong>10%</strong></div>
            </div>
            <div>
              <span class="text-muted" style="font-size:0.75rem">Missing Verification</span>
              <div>${isCounterfeit ? 'OEM factory serial database reconciliation; package seal inspection.' : 'Battery swelling expansion gauge & thermal imaging verification.'}</div>
            </div>
            <div>
              <span class="text-muted" style="font-size:0.75rem">Provisional Recommendation</span>
              <div><span class="badge badge-manual">Quarantine pending verification</span></div>
            </div>
          </div>
          <div class="review-actions mt-3">
            <button class="btn btn-sm btn-primary" onclick="App.simulateReviewAction('${c.return_id}', '${isCounterfeit ? 'counterfeit_verified' : 'safety_quarantine'}')">
              ${isCounterfeit ? 'Verify Counterfeit & Legal Hold' : 'Approve Hazmat Battery Disposal'}
            </button>
            <button class="btn btn-sm btn-secondary" onclick="App.openDeviceDetail('${c.return_id}')">
              Inspect Full Assessment &rarr;
            </button>
          </div>
        </div>
      </div>
    `;
  }).join('');
}

export async function simulateReviewAction(return_id, actionType) {
  showLoading('Recording review verification & updating disposition...');
  try {
    const isCounterfeit = actionType === 'counterfeit_verified';
    const payload = {
      return_id,
      product_condition: isCounterfeit ? 'like_new' : 'major_damage',
      defect_category: isCounterfeit ? 'none' : 'functional',
      defect_description: isCounterfeit
        ? 'OEM authentication failed: confirmed clone unit. Confiscated for legal custody.'
        : 'Swollen lithium cell verified. Certified hazmat battery disposal protocol executed.',
      visible_damage: !isCounterfeit,
      warranty_status: 'none',
      verified_warranty_eligible: false,
      authenticity_risk: isCounterfeit ? 1.0 : 0.02,
      safety_hazard: !isCounterfeit,
      fraud_risk_score: isCounterfeit ? 1.0 : 0.05,
      fraud_flags: isCounterfeit ? ['COUNTERFEIT_CONFIRMED'] : ['HAZMAT_DISPOSAL_APPROVED'],
      assessor_notes: `Manual review verified by senior inspector: ${actionType}.`
    };

    await API.submitAssessment(payload);
    await API.getDecision(return_id);
    toast(`Review record persisted for ${return_id}`, 'success');
    await refresh();
  } catch (e) {
    toast('Review action failed: ' + e.message, 'error');
  } finally {
    hideLoading();
  }
}

// WINDOW API ATTACHMENT
window.App = {
  setCurrency,
  switchTab,
  seedAndRun,
  refresh,
  filterInventory,
  exportInventoryCSV,
  openDeviceDetail,
  openFirstDeviceDetail,
  closeDeviceDetail,
  updateSimCapacityDisplay,
  updateSimCostDisplay,
  updateSimResaleDisplay,
  setScenarioCapacity,
  runScenario,
  resetSimulator,
  runPresetK2,
  simulateReviewAction
};

// AUTO-BOOT
document.addEventListener('DOMContentLoaded', () => {
  updateSimCapacityDisplay();
  updateSimCostDisplay();
  updateSimResaleDisplay();
  init();
});
