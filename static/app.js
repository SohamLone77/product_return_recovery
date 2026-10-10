// ReverseLogix AI — Interactive Dashboard Controller

let currentAllocations = [];
let currentFilter = 'all';

document.addEventListener('DOMContentLoaded', () => {
    initApp();
    setupEventListeners();
});

async function initApp() {
    try {
        await runOptimizer(4);
    } catch (err) {
        console.error("Initialization error:", err);
        showToast("Error connecting to backend server. Make sure port 8000 is running.");
    }
}

function setupEventListeners() {
    // Capacity Stepper
    const capInput = document.getElementById('capacity-input');
    document.getElementById('cap-dec').addEventListener('click', () => {
        let val = parseInt(capInput.value) || 0;
        if (val > 0) capInput.value = val - 1;
    });
    document.getElementById('cap-inc').addEventListener('click', () => {
        let val = parseInt(capInput.value) || 0;
        if (val < 20) capInput.value = val + 1;
    });

    // Run Optimizer Button
    document.getElementById('btn-run-optimizer').addEventListener('click', () => {
        const capacity = parseInt(capInput.value) || 4;
        runOptimizer(capacity);
    });

    // Seed Demo Devices Button
    document.getElementById('btn-seed-demo').addEventListener('click', async () => {
        showToast("Seeding 10 demonstration electronic devices...");
        try {
            const res = await fetch('/demo/seed', { method: 'POST' });
            const data = await res.json();
            showToast(`Seeded ${data.seeded_count} synthetic devices successfully!`);
            await runOptimizer(parseInt(capInput.value) || 4);
        } catch (err) {
            showToast("Failed to seed demo devices.");
        }
    });

    // Queue Filter Tabs
    document.querySelectorAll('.filter-tab').forEach(tab => {
        tab.addEventListener('click', (e) => {
            document.querySelectorAll('.filter-tab').forEach(t => t.classList.remove('active'));
            e.target.classList.add('active');
            currentFilter = e.target.dataset.filter;
            renderDevicesTable();
        });
    });

    // New Return Intake Modal
    const intakeModal = document.getElementById('intake-modal');
    document.getElementById('btn-open-intake').addEventListener('click', () => {
        intakeModal.classList.add('show');
    });
    document.getElementById('btn-close-intake').addEventListener('click', () => {
        intakeModal.classList.remove('show');
    });
    document.getElementById('btn-cancel-intake').addEventListener('click', () => {
        intakeModal.classList.remove('show');
    });

    // Device Details Modal Close
    const deviceModal = document.getElementById('device-modal');
    document.getElementById('btn-close-modal').addEventListener('click', () => {
        deviceModal.classList.remove('show');
    });
    window.addEventListener('click', (e) => {
        if (e.target === deviceModal) deviceModal.classList.remove('show');
        if (e.target === intakeModal) intakeModal.classList.remove('show');
    });

    // Intake Form Submission
    document.getElementById('intake-form').addEventListener('submit', handleIntakeSubmit);
}

async function runOptimizer(capacity) {
    showToast(`Solving reverse logistics knapsack for K=${capacity} bench slots...`);

    const res = await fetch('/optimize', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ repair_capacity_slots: capacity })
    });
    const data = await res.json();

    // If database was empty, auto-seed
    if (data.total_devices_evaluated === 0) {
        showToast("Database empty. Seeding 10 demonstration devices...");
        await fetch('/demo/seed', { method: 'POST' });
        return runOptimizer(capacity);
    }

    currentAllocations = data.allocations || [];

    // Update KPI Banner
    document.getElementById('kpi-net-recovery').innerText = data.optimized_total_net_recovery.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
    document.getElementById('kpi-slots-used').innerText = data.repair_slots_used;
    document.getElementById('kpi-slots-total').innerText = data.repair_capacity_slots;
    document.getElementById('kpi-cap-util').innerText = `${data.capacity_utilization_pct}% Utilized`;
    document.getElementById('kpi-progress-fill').style.width = `${Math.min(100, data.capacity_utilization_pct)}%`;
    document.getElementById('kpi-total-devices').innerText = data.total_devices_evaluated;

    const manualCount = currentAllocations.filter(a => a.manual_review_required).length;
    document.getElementById('kpi-manual-count').innerText = manualCount;
    document.getElementById('kpi-uplift-badge').innerText = `+${data.pct_uplift_vs_cheapest}% vs Cheapest`;

    // Update Comparison Grid
    document.getElementById('comp-opt-val').innerText = `$${data.optimized_total_net_recovery.toLocaleString('en-US', { minimumFractionDigits: 2 })}`;
    document.getElementById('comp-fifo-val').innerText = `$${data.baseline_fifo_net_recovery.toLocaleString('en-US', { minimumFractionDigits: 2 })}`;
    document.getElementById('comp-fifo-delta').innerText = `+$${data.dollar_uplift_vs_fifo.toLocaleString('en-US', { minimumFractionDigits: 2 })} (+${data.pct_uplift_vs_fifo}%)`;
    
    document.getElementById('comp-cheap-val').innerText = `$${data.baseline_cheapest_repair_net_recovery.toLocaleString('en-US', { minimumFractionDigits: 2 })}`;
    document.getElementById('comp-cheap-delta').innerText = `+$${data.dollar_uplift_vs_cheapest.toLocaleString('en-US', { minimumFractionDigits: 2 })} (+${data.pct_uplift_vs_cheapest}%)`;
    
    document.getElementById('comp-uncon-val').innerText = `$${data.baseline_unconstrained_net_recovery.toLocaleString('en-US', { minimumFractionDigits: 2 })}`;
    
    // Update Rationale
    document.getElementById('optimizer-rationale').innerText = data.batch_explanation;

    // Update tab counts
    const repairCount = currentAllocations.filter(a => a.was_repair_selected).length;
    const nonRepairCount = currentAllocations.filter(a => !a.was_repair_selected && !a.manual_review_required).length;
    document.getElementById('count-repair').innerText = repairCount;
    document.getElementById('count-nonrepair').innerText = nonRepairCount;
    document.getElementById('count-review').innerText = manualCount;

    renderDevicesTable();
    showToast("Optimization completed successfully!");
}

function renderDevicesTable() {
    const tbody = document.getElementById('devices-table-body');
    tbody.innerHTML = '';

    let filtered = currentAllocations;
    if (currentFilter === 'repair') {
        filtered = currentAllocations.filter(a => a.was_repair_selected);
    } else if (currentFilter === 'non-repair') {
        filtered = currentAllocations.filter(a => !a.was_repair_selected && !a.manual_review_required);
    } else if (currentFilter === 'review') {
        filtered = currentAllocations.filter(a => a.manual_review_required);
    }

    if (filtered.length === 0) {
        tbody.innerHTML = `<tr><td colspan="9" class="loading-cell">No devices match current filter.</td></tr>`;
        return;
    }

    filtered.forEach(item => {
        const tr = document.createElement('tr');
        
        const cleanName = item.product_name.replace('[Synthetic Demo] ', '');
        const routeClass = `route-${item.assigned_route}`;
        const routeDisplay = item.assigned_route.replace(/_/g, ' ');
        const incr = item.repair_incremental_benefit;
        const incrDisplay = incr > 0 ? `+${formatCurrency(incr)}` : formatCurrency(incr);
        const incrClass = incr > 0 ? 'text-success' : (incr < -500 ? 'text-muted' : 'text-muted');

        tr.innerHTML = `
            <td>
                <div class="device-cell">
                    <span class="device-name">${escapeHtml(cleanName)}</span>
                    <span class="device-sub">${escapeHtml(item.return_id)}</span>
                </div>
            </td>
            <td><span class="badge-neutral kpi-badge">${escapeHtml(item.category)}</span></td>
            <td class="num-cell">$${item.expected_proceeds ? (item.expected_proceeds + item.expected_cost).toFixed(2) : '—'}</td>
            <td><span class="badge-route ${routeClass}">${routeDisplay}</span></td>
            <td class="num-cell text-info">${formatCurrency(item.expected_proceeds)}</td>
            <td class="num-cell text-muted">${formatCurrency(item.expected_cost)}</td>
            <td class="num-cell text-success"><strong>${formatCurrency(item.expected_net_recovery)}</strong></td>
            <td class="num-cell ${incrClass}">${incr < -500 ? 'Infeasible' : incrDisplay}</td>
            <td>
                <button class="btn-detail" onclick="viewDeviceDetails('${item.return_id}')">
                    Analysis
                </button>
            </td>
        `;
        tbody.appendChild(tr);
    });
}

window.viewDeviceDetails = async function(returnId) {
    const alloc = currentAllocations.find(a => a.return_id === returnId);
    if (!alloc) return;

    const modal = document.getElementById('device-modal');
    document.getElementById('modal-device-title').innerText = alloc.product_name.replace('[Synthetic Demo] ', '');
    document.getElementById('modal-device-id').innerText = `${alloc.return_id} • ${alloc.category}`;

    const content = document.getElementById('modal-body-content');
    content.innerHTML = `
        <div style="display: flex; gap: 1rem; margin-bottom: 1.25rem;">
            <div style="flex: 1; background: rgba(11, 19, 34, 0.6); padding: 1rem; border-radius: 8px; border: 1px solid rgba(255,255,255,0.06);">
                <div style="font-size: 0.75rem; color: #94a3b8; text-transform: uppercase;">Assigned Disposition</div>
                <div style="font-size: 1.2rem; font-weight: 700; margin-top: 4px;" class="route-${alloc.assigned_route}">${alloc.assigned_route.replace(/_/g, ' ')}</div>
            </div>
            <div style="flex: 1; background: rgba(11, 19, 34, 0.6); padding: 1rem; border-radius: 8px; border: 1px solid rgba(255,255,255,0.06);">
                <div style="font-size: 0.75rem; color: #94a3b8; text-transform: uppercase;">Expected Net Recovery</div>
                <div style="font-size: 1.2rem; font-weight: 700; color: #34d399; margin-top: 4px;">$${alloc.expected_net_recovery.toFixed(2)}</div>
            </div>
            <div style="flex: 1; background: rgba(11, 19, 34, 0.6); padding: 1rem; border-radius: 8px; border: 1px solid rgba(255,255,255,0.06);">
                <div style="font-size: 0.75rem; color: #94a3b8; text-transform: uppercase;">Bench Incr Benefit</div>
                <div style="font-size: 1.2rem; font-weight: 700; color: #38bdf8; margin-top: 4px;">$${alloc.repair_incremental_benefit.toFixed(2)}</div>
            </div>
        </div>

        <div style="background: rgba(11, 19, 34, 0.75); border: 1px solid rgba(99, 102, 241, 0.3); border-radius: 8px; padding: 1rem; margin-bottom: 1.25rem;">
            <div style="font-size: 0.8rem; font-weight: 700; color: #cbd5e1; margin-bottom: 0.35rem; text-transform: uppercase;">Allocation Rationale</div>
            <div style="font-size: 0.875rem; color: #94a3b8; line-height: 1.5;">${escapeHtml(alloc.allocation_rationale)}</div>
        </div>

        <div style="display: flex; justify-content: space-between; font-size: 0.85rem; color: #94a3b8; margin-top: 1rem;">
            <span>Best Non-Repair Fallback: <strong style="color: #cbd5e1;">${alloc.best_non_repair_route}</strong> ($${alloc.best_non_repair_net_recovery.toFixed(2)})</span>
            <span>Technician Bench Hours: <strong style="color: #cbd5e1;">${alloc.repair_hours}h</strong></span>
        </div>
    `;

    modal.classList.add('show');
};

async function handleIntakeSubmit(e) {
    e.preventDefault();

    const productId = document.getElementById('intake-product-id').value.trim();
    const productName = document.getElementById('intake-product-name').value.trim();
    const category = document.getElementById('intake-category').value;
    const price = parseFloat(document.getElementById('intake-price').value) || 0;
    const reason = document.getElementById('intake-reason').value.trim();
    const condition = document.getElementById('intake-condition').value;
    const defectCat = document.getElementById('intake-defect-cat').value;
    const prob = parseFloat(document.getElementById('intake-prob').value) || 0.85;
    const repairCost = parseFloat(document.getElementById('intake-repair-cost').value) || 50;
    const resale = parseFloat(document.getElementById('intake-resale').value) || (price * 0.8);
    const partsVal = parseFloat(document.getElementById('intake-parts').value) || (price * 0.3);
    const warranty = document.getElementById('intake-warranty').value;
    const hazard = document.getElementById('intake-hazard').checked;

    showToast("Submitting return intake...");

    try {
        // 1. Create Return
        const retRes = await fetch('/returns', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                product_id: productId,
                product_name: productName,
                category: category,
                purchase_price: price,
                customer_id: "PORTAL-USER",
                return_reason: reason
            })
        });
        const returnRecord = await retRes.json();

        // 2. Submit Assessment
        await fetch('/assessment', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                return_id: returnRecord.id,
                product_condition: condition,
                defect_category: defectCat,
                defect_description: reason,
                warranty_status: warranty,
                repair_probability: prob,
                estimated_repair_cost: repairCost,
                potential_resale_value: resale,
                parts_recovery_value: partsVal,
                safety_hazard: hazard
            })
        });

        // 3. Trigger Decision
        await fetch('/decision', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ return_id: returnRecord.id })
        });

        document.getElementById('intake-modal').classList.remove('show');
        document.getElementById('intake-form').reset();
        showToast("Device ingested! Re-evaluating batch optimization...");
        await runOptimizer(parseInt(document.getElementById('capacity-input').value) || 4);

    } catch (err) {
        showToast("Error ingesting return.");
    }
}

function formatCurrency(num) {
    if (num === null || num === undefined) return '$0.00';
    return '$' + parseFloat(num).toFixed(2);
}

function escapeHtml(text) {
    if (!text) return '';
    return text
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;")
        .replace(/'/g, "&#039;");
}

function showToast(msg) {
    const toast = document.getElementById('toast-notification');
    toast.innerText = msg;
    toast.classList.add('show');
    setTimeout(() => {
        toast.classList.remove('show');
    }, 3200);
}
