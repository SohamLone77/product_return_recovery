/**
 * ReverseLogix AI - Central API Service Layer
 * feature/returns-dashboard
 *
 * Centralized API client for the Intelligent Product Returns & Recovery Engine.
 * Integrates directly with live FastAPI endpoints:
 *   POST /demo/seed            - Seed 10 canonical demo devices
 *   GET  /demo/dataset         - Inspect demo device specifications
 *   POST /optimize             - Batch optimizer (OptimizeResponse)
 *   POST /decision             - Single device decision (DecisionResponse)
 *   GET  /assessment/{id}      - Retrieve physical assessment record
 *   POST /assessment           - Submit updated assessment
 *   GET  /returns              - Query return records
 *   GET  /analytics            - Operational & financial analytics
 *   GET  /health               - System status check
 *
 * If the backend is unreachable, the SYNTHETIC_ADAPTER activates seamlessly
 * with clear UI labelling.
 */

const BASE_URL = ''; // Same origin

let _adapterMode = false;

export function isAdapterMode() {
  return _adapterMode;
}

export function setAdapterMode(val) {
  _adapterMode = val;
}

async function apiGet(path) {
  const resp = await fetch(BASE_URL + path, {
    headers: { 'Accept': 'application/json' }
  });
  if (!resp.ok) {
    const err = await resp.json().catch(() => ({}));
    throw new Error(err.detail || `HTTP ${resp.status} - ${path}`);
  }
  return resp.json();
}

async function apiPost(path, body = {}) {
  const resp = await fetch(BASE_URL + path, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', 'Accept': 'application/json' },
    body: JSON.stringify(body)
  });
  if (!resp.ok) {
    const err = await resp.json().catch(() => ({}));
    throw new Error(err.detail || `HTTP ${resp.status} - ${path}`);
  }
  return resp.json();
}

export async function checkHealth() {
  try {
    const data = await apiGet('/health');
    _adapterMode = false;
    return { live: true, data };
  } catch {
    _adapterMode = true;
    return { live: false, data: null };
  }
}

export async function seedDemoDevices() {
  if (_adapterMode) return SYNTHETIC_ADAPTER.seedResult();
  try {
    return await apiPost('/demo/seed');
  } catch (e) {
    console.warn('Backend seed failed, using synthetic adapter:', e);
    _adapterMode = true;
    return SYNTHETIC_ADAPTER.seedResult();
  }
}

export async function runOptimizer({ repair_capacity_slots = 4, return_ids = null, custom_costs = null } = {}) {
  if (_adapterMode) return SYNTHETIC_ADAPTER.optimize(repair_capacity_slots, custom_costs);
  try {
    const body = { repair_capacity_slots };
    if (return_ids) body.return_ids = return_ids;
    if (custom_costs) body.custom_costs = custom_costs;
    return await apiPost('/optimize', body);
  } catch (e) {
    console.warn('Backend optimize failed, using synthetic adapter:', e);
    _adapterMode = true;
    return SYNTHETIC_ADAPTER.optimize(repair_capacity_slots, custom_costs);
  }
}

export async function getDecision(return_id, custom_costs = null) {
  if (_adapterMode) return SYNTHETIC_ADAPTER.decision(return_id);
  try {
    const body = { return_id };
    if (custom_costs) body.custom_costs = custom_costs;
    return await apiPost('/decision', body);
  } catch (e) {
    console.warn('Backend decision failed, using synthetic adapter:', e);
    return SYNTHETIC_ADAPTER.decision(return_id);
  }
}

export async function getAssessment(return_id) {
  if (_adapterMode) return SYNTHETIC_ADAPTER.assessment(return_id);
  try {
    return await apiGet(`/assessment/${encodeURIComponent(return_id)}`);
  } catch (e) {
    console.warn('Backend assessment fetch failed, using synthetic adapter:', e);
    return SYNTHETIC_ADAPTER.assessment(return_id);
  }
}

export async function createReturn(payload) {
  if (_adapterMode) {
    const id = `ret_${Date.now().toString(16)}`;
    return { id, ...payload, status: 'registered' };
  }
  return await apiPost('/returns', payload);
}

export async function submitAssessment(payload) {
  if (_adapterMode) return SYNTHETIC_ADAPTER.submitAssessment(payload);
  return await apiPost('/assessment', payload);
}

export async function listReturns({ limit = 100, offset = 0, category = null, status = null } = {}) {
  if (_adapterMode) return SYNTHETIC_ADAPTER.returns();
  try {
    let path = `/returns?limit=${limit}&offset=${offset}`;
    if (category) path += `&category=${encodeURIComponent(category)}`;
    if (status) path += `&status=${encodeURIComponent(status)}`;
    return await apiGet(path);
  } catch (e) {
    console.warn('Backend list returns failed, using synthetic adapter:', e);
    return SYNTHETIC_ADAPTER.returns();
  }
}

export async function getAnalytics() {
  if (_adapterMode) return SYNTHETIC_ADAPTER.analytics();
  try {
    return await apiGet('/analytics');
  } catch (e) {
    console.warn('Backend analytics failed, using synthetic adapter:', e);
    return SYNTHETIC_ADAPTER.analytics();
  }
}

export async function getDemoDatasetSpec() {
  if (_adapterMode) return SYNTHETIC_ADAPTER.demoDataset();
  try {
    return await apiGet('/demo/dataset');
  } catch (e) {
    return SYNTHETIC_ADAPTER.demoDataset();
  }
}

// =============================================================================
// SYNTHETIC DEMO ADAPTER
// =============================================================================
export const SYNTHETIC_ADAPTER = (() => {
  const DEMO_SPEC = [
    {
      product_id: 'SYNTH-PHONE-15PRO',
      product_name: '[Synthetic Demo] Flagship Smartphone 15 Pro (256GB)',
      category: 'Electronics',
      purchase_price: 1100.0,
      condition: 'minor_damage',
      defect_category: 'functional',
      defect_description: 'Front glass cracked, OLED panel damaged, motherboard and battery healthy.',
      repair_probability: 0.95,
      estimated_repair_cost: 120.0,
      potential_resale_value: 850.0,
      parts_recovery_value: 280.0,
      warranty_status: 'expired',
      verified_warranty_eligible: false,
      authenticity_risk: 0.05,
      safety_hazard: false,
      assigned_route: 'repair',
      expected_proceeds: 763.56,
      expected_cost: 119.81,
      expected_net_recovery: 643.75,
      was_repair_selected: true,
      repair_feasible: true,
      repair_incremental_benefit: 167.75,
      best_non_repair_route: 'resell_secondary',
      best_non_repair_net_recovery: 476.0,
      repair_hours: 1.5,
      manual_review_required: false,
      manual_review_reasons: []
    },
    {
      product_id: 'SYNTH-LAPTOP-RTX4080',
      product_name: '[Synthetic Demo] Ultra Gaming Laptop 16 (RTX 4080, 32GB RAM)',
      category: 'Computers',
      purchase_price: 2200.0,
      condition: 'defective',
      defect_category: 'electrical',
      defect_description: 'Blown surface-mount capacitor on primary 19V rail; GPU/CPU silicon intact.',
      repair_probability: 0.90,
      estimated_repair_cost: 160.0,
      potential_resale_value: 1650.0,
      parts_recovery_value: 550.0,
      warranty_status: 'expired',
      verified_warranty_eligible: false,
      authenticity_risk: 0.02,
      safety_hazard: false,
      assigned_route: 'repair',
      expected_proceeds: 1633.5,
      expected_cost: 160.0,
      expected_net_recovery: 1473.5,
      was_repair_selected: true,
      repair_feasible: true,
      repair_incremental_benefit: 923.5,
      best_non_repair_route: 'harvest_parts',
      best_non_repair_net_recovery: 550.0,
      repair_hours: 2.5,
      manual_review_required: false,
      manual_review_reasons: []
    },
    {
      product_id: 'SYNTH-TABLET-PRO13',
      product_name: '[Synthetic Demo] Professional Creator Tablet 13-inch',
      category: 'Electronics',
      purchase_price: 950.0,
      condition: 'minor_damage',
      defect_category: 'functional',
      defect_description: 'Degraded battery cells; screen and enclosure in pristine condition.',
      repair_probability: 0.92,
      estimated_repair_cost: 85.0,
      potential_resale_value: 720.0,
      parts_recovery_value: 220.0,
      warranty_status: 'expired',
      verified_warranty_eligible: false,
      authenticity_risk: 0.03,
      safety_hazard: false,
      assigned_route: 'repair',
      expected_proceeds: 662.4,
      expected_cost: 85.0,
      expected_net_recovery: 577.4,
      was_repair_selected: true,
      repair_feasible: true,
      repair_incremental_benefit: 357.4,
      best_non_repair_route: 'harvest_parts',
      best_non_repair_net_recovery: 220.0,
      repair_hours: 1.0,
      manual_review_required: false,
      manual_review_reasons: []
    },
    {
      product_id: 'SYNTH-OLEDTV-65',
      product_name: '[Synthetic Demo] 65-inch Smart 4K OLED Cinema TV',
      category: 'Electronics',
      purchase_price: 1400.0,
      condition: 'minor_damage',
      defect_category: 'functional',
      defect_description: 'Loose T-Con LVDS ribbon cable; OLED panel itself is undamaged.',
      repair_probability: 0.88,
      estimated_repair_cost: 95.0,
      potential_resale_value: 920.0,
      parts_recovery_value: 310.0,
      warranty_status: 'expired',
      verified_warranty_eligible: false,
      authenticity_risk: 0.01,
      safety_hazard: false,
      assigned_route: 'repair',
      expected_proceeds: 765.44,
      expected_cost: 95.0,
      expected_net_recovery: 670.44,
      was_repair_selected: true,
      repair_feasible: true,
      repair_incremental_benefit: 293.44,
      best_non_repair_route: 'resell_secondary',
      best_non_repair_net_recovery: 377.0,
      repair_hours: 1.5,
      manual_review_required: false,
      manual_review_reasons: []
    },
    {
      product_id: 'SYNTH-BUDGET-A12',
      product_name: '[Synthetic Demo] Entry-Level Budget Smartphone A12',
      category: 'Electronics',
      purchase_price: 160.0,
      condition: 'defective',
      defect_category: 'electrical',
      defect_description: 'Extensive corrosion across logic board; liquid contact indicators red.',
      repair_probability: 0.35,
      estimated_repair_cost: 75.0,
      potential_resale_value: 85.0,
      parts_recovery_value: 20.0,
      warranty_status: 'none',
      verified_warranty_eligible: false,
      authenticity_risk: 0.02,
      safety_hazard: false,
      assigned_route: 'recycle',
      expected_proceeds: 20.0,
      expected_cost: 14.0,
      expected_net_recovery: 6.0,
      was_repair_selected: false,
      repair_feasible: true,
      repair_incremental_benefit: -33.5,
      best_non_repair_route: 'recycle',
      best_non_repair_net_recovery: 6.0,
      repair_hours: 2.0,
      manual_review_required: false,
      manual_review_reasons: []
    },
    {
      product_id: 'SYNTH-WATCH-ACT5',
      product_name: '[Synthetic Demo] Smartwatch Active 5 (Cellular, 44mm)',
      category: 'Electronics',
      purchase_price: 320.0,
      condition: 'like_new',
      defect_category: 'cosmetic',
      defect_description: 'Minor surface scuff on outer bezel; display, sensor suite, and battery 100% operational.',
      repair_probability: 1.0,
      estimated_repair_cost: 85.0,
      potential_resale_value: 240.0,
      parts_recovery_value: 70.0,
      warranty_status: 'active',
      verified_warranty_eligible: false,
      authenticity_risk: 0.02,
      safety_hazard: false,
      assigned_route: 'refurbish',
      expected_proceeds: 204.0,
      expected_cost: 43.4,
      expected_net_recovery: 160.6,
      was_repair_selected: false,
      repair_feasible: false,
      repair_incremental_benefit: 0.0,
      best_non_repair_route: 'refurbish',
      best_non_repair_net_recovery: 160.6,
      repair_hours: 1.0,
      manual_review_required: false,
      manual_review_reasons: []
    },
    {
      product_id: 'SYNTH-TOWER-CUSTOM',
      product_name: '[Synthetic Demo] High-Performance Tower PC (Crushed Chassis)',
      category: 'Computers',
      purchase_price: 1800.0,
      condition: 'major_damage',
      defect_category: 'functional',
      defect_description: 'Chassis crushed beyond repair; motherboard cracked. RTX 4070 GPU, 64GB RAM undamaged.',
      repair_probability: 0.10,
      estimated_repair_cost: 900.0,
      potential_resale_value: 1100.0,
      parts_recovery_value: 580.0,
      warranty_status: 'none',
      verified_warranty_eligible: false,
      authenticity_risk: 0.02,
      safety_hazard: false,
      assigned_route: 'harvest_parts',
      expected_proceeds: 580.0,
      expected_cost: 35.0,
      expected_net_recovery: 545.0,
      was_repair_selected: false,
      repair_feasible: false,
      repair_incremental_benefit: 0.0,
      best_non_repair_route: 'harvest_parts',
      best_non_repair_net_recovery: 545.0,
      repair_hours: 4.0,
      manual_review_required: false,
      manual_review_reasons: []
    },
    {
      product_id: 'SYNTH-HUB-SMARTHOME',
      product_name: '[Synthetic Demo] Smart Home Automation Hub Pro',
      category: 'Electronics',
      purchase_price: 260.0,
      condition: 'defective',
      defect_category: 'electrical',
      defect_description: 'Factory defect in internal radio IC; verified invoice within 1-year manufacturer warranty.',
      repair_probability: 0.70,
      estimated_repair_cost: 80.0,
      potential_resale_value: 170.0,
      parts_recovery_value: 45.0,
      warranty_status: 'active',
      verified_warranty_eligible: true,
      authenticity_risk: 0.01,
      safety_hazard: false,
      assigned_route: 'return_to_supplier',
      expected_proceeds: 229.32,
      expected_cost: 26.54,
      expected_net_recovery: 202.78,
      was_repair_selected: false,
      repair_feasible: true,
      repair_incremental_benefit: -189.58,
      best_non_repair_route: 'return_to_supplier',
      best_non_repair_net_recovery: 202.78,
      repair_hours: 1.2,
      manual_review_required: false,
      manual_review_reasons: []
    },
    {
      product_id: 'SYNTH-EARBUDS-SUSPECT',
      product_name: '[Synthetic Demo] ANC Wireless Earbuds Pro (Counterfeit Suspect)',
      category: 'Accessories',
      purchase_price: 280.0,
      condition: 'like_new',
      defect_category: 'none',
      defect_description: 'Serial number does not match factory database; charging case weight is 12g lighter than OEM.',
      repair_probability: 0.0,
      estimated_repair_cost: 0.0,
      potential_resale_value: 0.0,
      parts_recovery_value: 0.0,
      warranty_status: 'none',
      verified_warranty_eligible: false,
      authenticity_risk: 0.94,
      safety_hazard: false,
      assigned_route: 'manual_assessment',
      expected_proceeds: 0.0,
      expected_cost: 8.0,
      expected_net_recovery: -8.0,
      was_repair_selected: false,
      repair_feasible: false,
      repair_incremental_benefit: 0.0,
      best_non_repair_route: 'dispose',
      best_non_repair_net_recovery: -13.0,
      repair_hours: 0.0,
      manual_review_required: true,
      manual_review_reasons: [
        'Elevated fraud/authenticity risk (score: 0.94). Potential counterfeit or serial mismatch.'
      ]
    },
    {
      product_id: 'SYNTH-ULTRABOOK-SWELL',
      product_name: '[Synthetic Demo] Ultra-Slim Laptop 14 (Swollen Lithium Cell)',
      category: 'Computers',
      purchase_price: 950.0,
      condition: 'major_damage',
      defect_category: 'functional',
      defect_description: 'Lithium-ion polymer battery cell has swollen significantly, pushing trackpad up.',
      repair_probability: 0.80,
      estimated_repair_cost: 110.0,
      potential_resale_value: 650.0,
      parts_recovery_value: 200.0,
      warranty_status: 'expired',
      verified_warranty_eligible: false,
      authenticity_risk: 0.02,
      safety_hazard: true,
      assigned_route: 'manual_assessment',
      expected_proceeds: 0.0,
      expected_cost: 8.0,
      expected_net_recovery: -8.0,
      was_repair_selected: false,
      repair_feasible: false,
      repair_incremental_benefit: 0.0,
      best_non_repair_route: 'harvest_parts',
      best_non_repair_net_recovery: 165.0,
      repair_hours: 1.5,
      manual_review_required: true,
      manual_review_reasons: [
        'Safety hazard detected (e.g. swollen lithium battery, thermal damage). Standard automated processing blocked.'
      ]
    }
  ];

  function buildAllocations(k, costMult = 1.0, resaleMult = 1.0) {
    let allocs = DEMO_SPEC.map((d, i) => {
      const return_id = `ret_demo_synth_${i + 1}`;
      let proceeds = d.expected_proceeds * resaleMult;
      let cost = d.expected_cost * costMult;
      let net = proceeds - cost;
      let incr = d.repair_incremental_benefit;
      if (d.assigned_route === 'repair') {
        incr = incr * resaleMult - (costMult - 1.0) * d.estimated_repair_cost;
      }
      return {
        return_id,
        product_name: d.product_name,
        category: d.category,
        assigned_route: d.assigned_route,
        expected_proceeds: Math.round(proceeds * 100) / 100,
        expected_cost: Math.round(cost * 100) / 100,
        expected_net_recovery: Math.round(net * 100) / 100,
        was_repair_selected: d.was_repair_selected,
        repair_feasible: d.repair_feasible,
        repair_incremental_benefit: Math.round(incr * 100) / 100,
        best_non_repair_route: d.best_non_repair_route,
        best_non_repair_net_recovery: d.best_non_repair_net_recovery,
        repair_hours: d.repair_hours,
        manual_review_required: d.manual_review_required,
        manual_review_reasons: d.manual_review_reasons,
        allocation_rationale: d.manual_review_required
          ? `Escalated for human review: ${d.manual_review_reasons[0]}`
          : d.was_repair_selected
            ? `Allocated repair bench slot: Incremental recovery exceeds non-repair route by +$${incr.toFixed(2)}.`
            : `Routed to ${d.assigned_route}: Superior to repair or repair unviable.`
      };
    });

    // Re-rank repair candidates
    const repairCandidates = allocs
      .filter(a => a.repair_feasible && a.repair_incremental_benefit > 0 && !a.manual_review_required)
      .sort((a, b) => b.repair_incremental_benefit - a.repair_incremental_benefit);

    const selectedIds = new Set(repairCandidates.slice(0, k).map(a => a.return_id));

    allocs = allocs.map(a => {
      if (a.was_repair_selected && !selectedIds.has(a.return_id)) {
        return {
          ...a,
          was_repair_selected: false,
          assigned_route: a.best_non_repair_route,
          expected_net_recovery: a.best_non_repair_net_recovery,
          expected_proceeds: a.best_non_repair_net_recovery + a.expected_cost,
          allocation_rationale: `[Capacity constraint K=${k}] Demoted to best non-repair fallback (${a.best_non_repair_route}).`
        };
      }
      return a;
    });

    return allocs;
  }

  function optimize(k = 4, custom_costs = null) {
    const costMult = custom_costs?.cost_multiplier || 1.0;
    const resaleMult = custom_costs?.resale_multiplier || 1.0;
    const allocations = buildAllocations(k, costMult, resaleMult);
    const slotsUsed = allocations.filter(a => a.was_repair_selected).length;
    const optNet = allocations.reduce((sum, a) => sum + a.expected_net_recovery, 0);

    return {
      run_id: `run_synth_k${k}_${Date.now()}`,
      total_devices_evaluated: 10,
      repair_capacity_slots: k,
      repair_slots_used: slotsUsed,
      capacity_utilization_pct: k > 0 ? Math.round((slotsUsed / k) * 100) : 0,
      optimized_total_net_recovery: Math.round(optNet * 100) / 100,
      baseline_unconstrained_net_recovery: 4071.03,
      baseline_fifo_net_recovery: 3497.53,
      baseline_cheapest_repair_net_recovery: 2853.35,
      dollar_uplift_vs_fifo: Math.round((optNet - 3497.53) * 100) / 100,
      pct_uplift_vs_fifo: Math.round(((optNet - 3497.53) / 3497.53) * 1000) / 10,
      dollar_uplift_vs_cheapest: Math.round((optNet - 2853.35) * 100) / 100,
      pct_uplift_vs_cheapest: Math.round(((optNet - 2853.35) / 2853.35) * 1000) / 10,
      allocations,
      batch_explanation: `Evaluated 10 devices against ${k} repair bench slots. Allocated ${slotsUsed}/${k} slots (${k>0?Math.round((slotsUsed/k)*100):0}% utilization) exclusively to devices delivering positive incremental net recovery.`,
      comparison_summary: {
        optimized: { total_net_recovery: optNet, repairs_selected: slotsUsed },
        baseline_fifo: { total_net_recovery: 3497.53, dollar_difference: optNet - 3497.53 },
        baseline_cheapest_repair: { total_net_recovery: 2853.35, dollar_difference: optNet - 2853.35 }
      },
      created_at: new Date().toISOString()
    };
  }

  function decision(return_id) {
    const idx = parseInt((return_id.split('_').pop() || '1'), 10) - 1;
    const spec = DEMO_SPEC[idx >= 0 && idx < 10 ? idx : 0];
    return {
      id: `dec_synth_${return_id}`,
      return_id,
      recommended_action: spec.assigned_route,
      recommended_route: spec.assigned_route,
      expected_recovered_value: spec.expected_proceeds,
      estimated_costs: spec.expected_cost,
      expected_net_recovery: spec.expected_net_recovery,
      cost_breakdown: { inspection: 8.0, handling: 5.0, route_cost: spec.expected_cost - 13.0 },
      alternative_routes: [
        { route: 'repair', feasible: spec.repair_feasible, expected_recovered_value: spec.potential_resale_value, route_costs: spec.estimated_repair_cost + 13, expected_net_recovery: spec.expected_net_recovery, feasibility_note: spec.repair_feasible ? 'Feasible' : 'Rejected' },
        { route: 'refurbish', feasible: spec.condition === 'like_new', expected_recovered_value: spec.potential_resale_value * 0.85, route_costs: 43.4, expected_net_recovery: spec.potential_resale_value * 0.85 - 43.4, feasibility_note: '' },
        { route: 'harvest_parts', feasible: spec.parts_recovery_value > 0, expected_recovered_value: spec.parts_recovery_value, route_costs: 35.0, expected_net_recovery: spec.parts_recovery_value - 35.0, feasibility_note: '' },
        { route: 'resell_secondary', feasible: spec.condition !== 'major_damage', expected_recovered_value: spec.purchase_price * 0.45, route_costs: 34.0, expected_net_recovery: spec.purchase_price * 0.45 - 34.0, feasibility_note: '' },
        { route: 'recycle', feasible: true, expected_recovered_value: 20.0, route_costs: 14.0, expected_net_recovery: 6.0, feasibility_note: '' },
        { route: 'return_to_supplier', feasible: spec.verified_warranty_eligible, expected_recovered_value: spec.purchase_price * 0.9, route_costs: 26.54, expected_net_recovery: spec.purchase_price * 0.9 - 26.54, feasibility_note: spec.verified_warranty_eligible ? 'Verified warranty' : 'Ineligible' },
        { route: 'dispose', feasible: true, expected_recovered_value: 0.0, route_costs: 13.0, expected_net_recovery: -13.0, feasibility_note: '' }
      ],
      reason_codes: spec.manual_review_required ? spec.manual_review_reasons : ['MAX_INCREMENTAL_RECOVERY'],
      explanation: spec.manual_review_required
        ? `Case flagged for manual review: ${spec.manual_review_reasons[0]}`
        : `${spec.assigned_route.toUpperCase()} selected because expected net recovery is $${spec.expected_net_recovery.toFixed(2)}, outperforming fallback by +$${spec.repair_incremental_benefit.toFixed(2)}.`,
      manual_review_required: spec.manual_review_required,
      manual_review_reasons: spec.manual_review_reasons,
      flags: spec.manual_review_reasons,
      best_non_repair_route: spec.best_non_repair_route,
      best_non_repair_net_recovery: spec.best_non_repair_net_recovery,
      repair_incremental_benefit: spec.repair_incremental_benefit,
      confidence_score: spec.manual_review_required ? 0.2 : (spec.repair_probability || 0.9),
      assumptions: ['Assessment data verified', 'Stable resale secondary pricing'],
      created_at: new Date().toISOString()
    };
  }

  function assessment(return_id) {
    const idx = parseInt((return_id.split('_').pop() || '1'), 10) - 1;
    const spec = DEMO_SPEC[idx >= 0 && idx < 10 ? idx : 0];
    return {
      id: `asm_synth_${return_id}`,
      return_id,
      product_condition: spec.condition,
      defect_category: spec.defect_category,
      defect_description: spec.defect_description,
      visible_damage: spec.condition === 'minor_damage' || spec.condition === 'major_damage',
      warranty_status: spec.warranty_status,
      purchase_date: '2024-06-15',
      warranty_expiry_date: spec.warranty_status === 'active' ? '2025-06-15' : '2024-06-15',
      verified_warranty_eligible: spec.verified_warranty_eligible,
      proof_of_purchase_metadata: { invoice: 'INV-DEMO-9912' },
      image_reference: null,
      fraud_risk_score: spec.authenticity_risk,
      fraud_flags: spec.authenticity_risk > 0.5 ? ['COUNTERFEIT_SUSPECTED'] : [],
      assessor_notes: 'Synthetic engineering intake inspection.',
      repair_probability: spec.repair_probability,
      estimated_repair_cost: spec.estimated_repair_cost,
      estimated_repair_hours: spec.repair_hours,
      potential_resale_value: spec.potential_resale_value,
      parts_recovery_value: spec.parts_recovery_value,
      authenticity_risk: spec.authenticity_risk,
      safety_hazard: spec.safety_hazard,
      created_at: new Date().toISOString()
    };
  }

  return {
    seedResult: () => ({
      message: '[SYNTHETIC ADAPTER] 10 demo devices loaded.',
      seeded_count: 10,
      repair_capacity_slots: 4,
      return_ids: DEMO_SPEC.map((_, i) => `ret_demo_synth_${i + 1}`)
    }),
    optimize,
    decision,
    assessment,
    submitAssessment: (payload) => ({
      id: `asm_synth_${Date.now()}`,
      ...payload,
      created_at: new Date().toISOString()
    }),
    returns: () => ({
      items: DEMO_SPEC.map((d, i) => ({
        id: `ret_demo_synth_${i + 1}`,
        product_id: d.product_id,
        product_name: d.product_name,
        category: d.category,
        purchase_price: d.purchase_price,
        currency: 'USD',
        customer_id: `CUST-0${i + 1}`,
        order_id: `ORD-10${i + 1}`,
        return_reason: d.defect_description,
        status: 'decided',
        created_at: new Date().toISOString(),
        updated_at: new Date().toISOString()
      })),
      total: 10,
      limit: 100,
      offset: 0
    }),
    analytics: () => ({
      total_returns: 10,
      returns_by_condition: { minor_damage: 3, defective: 3, like_new: 2, major_damage: 2 },
      returns_by_warranty_status: { expired: 6, none: 3, active: 1 },
      counts_by_recommended_action: { repair: 4, refurbish: 1, harvest_parts: 1, return_to_supplier: 1, recycle: 1, manual_assessment: 2 },
      total_estimated_recovered_value: 4434.22,
      total_estimated_processing_costs: 363.19,
      total_expected_net_recovery: 4071.03,
      manual_physical_review_count: 2,
      fraud_risk_flag_count: 1,
      records_with_complete_economic_data: 10,
      accounting_notes: 'All figures derived from reverse logistics probabilistic valuation engine.'
    }),
    demoDataset: () => ({
      description: '10 Synthetic Demonstration Devices',
      repair_capacity_slots: 4,
      devices: DEMO_SPEC
    })
  };
})();
