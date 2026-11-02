/**
 * Cluster Analytics Engine
 * ========================
 * Lazy-loaded module: zero overhead until the user clicks "Cluster Analytics".
 * Fetches data from the EXISTING /api/view_customers/data route.
 * All clustering is done client-side. READ-ONLY — no data mutations.
 */
(function () {
  'use strict';

  /* ─── State ─── */
  let rawCustomers = null;
  let currentClusters = [];
  let currentType = 'batches';       // 'batches' | 'loansize' | 'duration'
  let currentBatchMode = 'quarterly'; // 'weekly' | 'monthly' | 'quarterly' | 'halfyear' | 'yearly'
  let loanRangeMin = 0;
  let loanRangeMax = Infinity;
  let loanDataMax = 100000;          // actual max from data (for slider bounds)
  let particles = [];
  let clusterCenters = [];
  let canvas, ctx;
  let animFrameId = null;
  let modalOpen = false;
  let selectedClusterIds = new Set();
  let compareMode = false;
  let analyticsChart = null;

  const MAX_PARTICLES = 600;

  /* ═══════════════════════════════════════════════════════════════
     PUBLIC API
     ═══════════════════════════════════════════════════════════════ */

  window.openClusterAnalyticsModal = async function () {
    const modal = document.getElementById('clusterAnalyticsOverlay');
    if (!modal) return;
    modal.classList.add('ca-visible');
    modalOpen = true;

    showLoading(true);

    if (!rawCustomers) {
      try {
        const res = await fetch('/api/view_customers/data?mode=active');
        const json = await res.json();
        if (!json.success) throw new Error(json.error || 'Failed to load');
        rawCustomers = (json.all_customers_stats || []).map(normaliseCustomer);
        // compute data-driven slider bounds
        if (rawCustomers.length > 0) {
          loanDataMax = Math.ceil(Math.max(...rawCustomers.map(c => c.totalAmount)) / 1000) * 1000;
          loanRangeMax = loanDataMax;
          initRangeSlider();
        }
      } catch (e) {
        document.getElementById('caLoadingText').textContent = 'Error: ' + e.message;
        return;
      }
    }

    showLoading(false);
    initCanvas();
    updateSubControls();
    rebuildClusters();
    startAnimation();
  };

  window.closeClusterAnalyticsModal = function () {
    const modal = document.getElementById('clusterAnalyticsOverlay');
    if (modal) modal.classList.remove('ca-visible');
    modalOpen = false;
    stopAnimation();
    rawCustomers = null;
    selectedClusterIds.clear();
    particles = [];
    if (analyticsChart) { analyticsChart.destroy(); analyticsChart = null; }
  };

  window.caChangeClusterType = function (type) {
    currentType = type;
    document.querySelectorAll('.ca-type-btn').forEach(b => b.classList.remove('active'));
    const activeBtn = document.querySelector(`.ca-type-btn[data-type="${type}"]`);
    if (activeBtn) activeBtn.classList.add('active');
    selectedClusterIds.clear();
    compareMode = false;
    const cmp = document.getElementById('caCompareToggle');
    if (cmp) cmp.checked = false;
    hideAnalyticsPanel();
    updateSubControls();
    rebuildClusters();
  };

  window.caChangeBatchMode = function (mode) {
    currentBatchMode = mode;
    document.querySelectorAll('.ca-batch-btn').forEach(b => b.classList.remove('active'));
    const btn = document.querySelector(`.ca-batch-btn[data-mode="${mode}"]`);
    if (btn) btn.classList.add('active');
    selectedClusterIds.clear();
    hideAnalyticsPanel();
    rebuildClusters();
  };

  window.caUpdateLoanRange = function () {
    const minEl = document.getElementById('caRangeMin');
    const maxEl = document.getElementById('caRangeMax');
    if (!minEl || !maxEl) return;

    let minVal = parseFloat(minEl.value) || 0;
    let maxVal = parseFloat(maxEl.value) || loanDataMax;

    // ensure min <= max
    if (minVal > maxVal) {
      if (minEl === document.activeElement || minEl._lastChanged) { maxVal = minVal; maxEl.value = maxVal; }
      else { minVal = maxVal; minEl.value = minVal; }
    }

    loanRangeMin = minVal;
    loanRangeMax = maxVal;

    // update fill bar
    const fill = document.getElementById('caRangeFill');
    if (fill && loanDataMax > 0) {
      const leftPct = (minVal / loanDataMax) * 100;
      const rightPct = (maxVal / loanDataMax) * 100;
      fill.style.left = leftPct + '%';
      fill.style.width = (rightPct - leftPct) + '%';
    }
    // update labels
    const minLabel = document.getElementById('caRangeMinLabel');
    const maxLabel = document.getElementById('caRangeMaxLabel');
    if (minLabel) minLabel.textContent = '₹' + formatNum(Math.round(minVal));
    if (maxLabel) maxLabel.textContent = '₹' + formatNum(Math.round(maxVal));

    selectedClusterIds.clear();
    hideAnalyticsPanel();
    rebuildClusters();
  };

  window.caToggleCluster = function (id) {
    if (selectedClusterIds.has(id)) {
      selectedClusterIds.delete(id);
    } else {
      if (compareMode && selectedClusterIds.size >= 2) return;
      selectedClusterIds.add(id);
    }
    renderClusterList();
  };

  window.caToggleCompare = function (checked) {
    compareMode = checked;
    if (!compareMode && selectedClusterIds.size > 1) {
      const first = selectedClusterIds.values().next().value;
      selectedClusterIds.clear();
      selectedClusterIds.add(first);
    }
    renderClusterList();
  };

  window.caViewAnalytics = function () {
    if (selectedClusterIds.size === 0) return;
    showAnalyticsPanel();
  };

  /* ═══════════════════════════════════
     SUB-CONTROLS VISIBILITY
     ═══════════════════════════════════ */
  function updateSubControls() {
    const batchPanel = document.getElementById('caBatchModePanel');
    const rangePanel = document.getElementById('caRangePanel');
    if (batchPanel) batchPanel.style.display = currentType === 'batches' ? 'flex' : 'none';
    if (rangePanel) rangePanel.style.display = currentType === 'loansize' ? 'flex' : 'none';
  }

  function initRangeSlider() {
    const minEl = document.getElementById('caRangeMin');
    const maxEl = document.getElementById('caRangeMax');
    if (minEl) { minEl.max = loanDataMax; minEl.value = 0; }
    if (maxEl) { maxEl.max = loanDataMax; maxEl.value = loanDataMax; }
    loanRangeMin = 0;
    loanRangeMax = loanDataMax;

    const fill = document.getElementById('caRangeFill');
    if (fill) { fill.style.left = '0%'; fill.style.width = '100%'; }
    const minLabel = document.getElementById('caRangeMinLabel');
    const maxLabel = document.getElementById('caRangeMaxLabel');
    if (minLabel) minLabel.textContent = '₹0';
    if (maxLabel) maxLabel.textContent = '₹' + formatNum(loanDataMax);
  }

  /* ═══════════════════════════════════
     DATA NORMALISATION
     ═══════════════════════════════════ */
  function normaliseCustomer(c) {
    return {
      cid: c.cid,
      name: c.name || '',
      startDate: parseDate(c.start_date),
      endDate: parseDate(c.end_date),
      totalAmount: toNum(c.total_amount),
      paidAmount: toNum(c.paid_amount),
      balanceAmount: toNum(c.balance_amount),
      installment: toNum(c.installment_amount),
      period: toNum(c.period),
      baseAmount: toNum(c.base_amount),
      cuttingAmount: toNum(c.cutting_amount),
      interestAmount: toNum(c.interest_amount),
      source: c.source || 'active',
      get status() {
        if (this.source === 'active') return 'active';
        return this.balanceAmount > 0 ? 'defaulted' : 'closed';
      }
    };
  }

  function parseDate(v) {
    if (!v) return null;
    if (v instanceof Date) return v;
    const d = new Date(v);
    if (!isNaN(d)) return d;
    const parts = String(v).split('-');
    if (parts.length === 3) {
      const months = { Jan: 0, Feb: 1, Mar: 2, Apr: 3, May: 4, Jun: 5, Jul: 6, Aug: 7, Sep: 8, Oct: 9, Nov: 10, Dec: 11 };
      const m = months[parts[1]];
      if (m !== undefined) return new Date(+parts[2], m, +parts[0]);
    }
    return null;
  }

  function toNum(v) { return parseFloat(v) || 0; }

  /* ═══════════════════════════════════
     CLUSTERING ALGORITHMS
     ═══════════════════════════════════ */
  function rebuildClusters() {
    if (!rawCustomers || rawCustomers.length === 0) return;

    switch (currentType) {
      case 'batches':   currentClusters = clusterByBatches(rawCustomers); break;
      case 'loansize':  currentClusters = clusterByLoanSize(rawCustomers); break;
      case 'duration':  currentClusters = clusterByDuration(rawCustomers); break;
    }

    // sort DESCENDING by sortKey (newest dates first, largest amounts first)
    currentClusters.sort((a, b) => b.sortKey - a.sortKey);

    // assign IDs
    currentClusters.forEach((c, i) => { c.id = i; });

    // update cluster count badge
    const badge = document.getElementById('caClusterCount');
    if (badge) badge.textContent = currentClusters.length;

    computeClusterCenters();
    assignParticles();
    renderClusterList();
  }

  /* ── Batch Clustering (calendar-based periods) ── */
  const MONTH_SHORT = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];

  function clusterByBatches(customers) {
    const withDate = customers.filter(c => c.startDate);
    if (withDate.length === 0) return [];

    const groups = {};

    withDate.forEach(c => {
      const d = c.startDate;
      const y = d.getFullYear();
      const m = d.getMonth(); // 0-11
      let key, label, canvasLabel, sortVal;

      switch (currentBatchMode) {
        case 'weekly': {
          // ISO week-based grouping
          const jan1 = new Date(y, 0, 1);
          const weekNum = Math.ceil(((d - jan1) / 86400000 + jan1.getDay() + 1) / 7);
          key = y + '-W' + String(weekNum).padStart(2, '0');
          label = 'W' + weekNum + ' ' + MONTH_SHORT[m] + " '" + String(y).slice(2);
          canvasLabel = 'W' + weekNum + " '" + String(y).slice(2);
          sortVal = y * 100 + weekNum;
          break;
        }
        case 'monthly': {
          key = y + '-' + String(m + 1).padStart(2, '0');
          label = MONTH_SHORT[m] + ' ' + y;
          canvasLabel = MONTH_SHORT[m] + " '" + String(y).slice(2);
          sortVal = y * 100 + m;
          break;
        }
        case 'quarterly': {
          const q = Math.floor(m / 3) + 1;
          key = y + '-Q' + q;
          label = 'Q' + q + ' ' + y + ' (' + MONTH_SHORT[m - (m % 3)] + '–' + MONTH_SHORT[m - (m % 3) + 2] + ')';
          canvasLabel = 'Q' + q + " '" + String(y).slice(2);
          sortVal = y * 10 + q;
          break;
        }
        case 'halfyear': {
          const h = m < 6 ? 1 : 2;
          key = y + '-H' + h;
          label = 'H' + h + ' ' + y + (h === 1 ? ' (Jan–Jun)' : ' (Jul–Dec)');
          canvasLabel = 'H' + h + " '" + String(y).slice(2);
          sortVal = y * 10 + h;
          break;
        }
        case 'yearly': {
          key = String(y);
          label = String(y);
          canvasLabel = String(y);
          sortVal = y;
          break;
        }
        default: {
          // fallback to quarterly
          const qf = Math.floor(m / 3) + 1;
          key = y + '-Q' + qf;
          label = 'Q' + qf + ' ' + y;
          canvasLabel = 'Q' + qf + " '" + String(y).slice(2);
          sortVal = y * 10 + qf;
        }
      }

      if (!groups[key]) groups[key] = { label, canvasLabel, sortKey: sortVal, customers: [] };
      groups[key].customers.push(c);
    });

    return Object.values(groups).map(g => ({
      label: g.label,
      canvasLabel: g.canvasLabel,
      sortKey: g.sortKey,
      customers: g.customers,
      ...computeClusterStats(g.customers)
    }));
  }

  /* ── Loan Size Clustering (with range filter) ── */
  function clusterByLoanSize(customers) {
    // filter by current range
    const filtered = customers.filter(c => c.totalAmount >= loanRangeMin && c.totalAmount <= loanRangeMax);
    if (filtered.length === 0) return [];

    const buckets = {};
    filtered.forEach(c => {
      const amt = c.totalAmount;
      const key = Math.round(amt / 500) * 500;
      if (!buckets[key]) buckets[key] = [];
      buckets[key].push(c);
    });

    // merge tiny buckets (<5 members) into nearest larger bucket
    const sortedKeys = Object.keys(buckets).map(Number).sort((a, b) => a - b);
    const merged = [];
    let current = null;

    for (const key of sortedKeys) {
      if (!current) {
        current = { minAmt: key, maxAmt: key, customers: [...buckets[key]] };
      } else if (buckets[key].length < 5 && current.customers.length < 50) {
        current.customers.push(...buckets[key]);
        current.maxAmt = key;
      } else {
        merged.push(current);
        current = { minAmt: key, maxAmt: key, customers: [...buckets[key]] };
      }
    }
    if (current) merged.push(current);

    return merged.map(m => {
      const label = m.minAmt === m.maxAmt
        ? '₹' + formatNum(m.minAmt)
        : '₹' + formatNum(m.minAmt) + ' – ₹' + formatNum(m.maxAmt);
      const canvasLabel = m.minAmt === m.maxAmt
        ? '₹' + formatCompact(m.minAmt)
        : '₹' + formatCompact(m.minAmt) + '–' + formatCompact(m.maxAmt);
      return {
        label, canvasLabel,
        sortKey: m.maxAmt,
        customers: m.customers,
        ...computeClusterStats(m.customers)
      };
    });
  }

  /* ── Duration Clustering ── */
  function clusterByDuration(customers) {
    const groups = {};
    customers.forEach(c => {
      const p = c.period || 0;
      if (!groups[p]) groups[p] = [];
      groups[p].push(c);
    });

    return Object.keys(groups).sort((a, b) => +a - +b).map(p => ({
      label: p + ' Period' + (+p !== 1 ? 's' : ''),
      canvasLabel: p + 'P',
      sortKey: +p,
      customers: groups[p],
      ...computeClusterStats(groups[p])
    }));
  }

  /* ── Stats helper ── */
  function computeClusterStats(customers) {
    let totalLent = 0, totalPaid = 0, totalBalance = 0;
    let activeCount = 0, defaultedCount = 0, closedCount = 0;
    customers.forEach(c => {
      totalLent += c.totalAmount;
      totalPaid += c.paidAmount;
      totalBalance += c.balanceAmount;
      if (c.status === 'active') activeCount++;
      else if (c.status === 'defaulted') defaultedCount++;
      else closedCount++;
    });
    const total = customers.length;
    const defaultRate = total > 0 ? (defaultedCount / total * 100) : 0;
    const recoveryRate = totalLent > 0 ? (totalPaid / totalLent * 100) : 0;
    return { totalLent, totalPaid, totalBalance, activeCount, defaultedCount, closedCount, defaultRate, recoveryRate };
  }

  /* ═══════════════════════════════════
     CANVAS PARTICLE ENGINE
     ═══════════════════════════════════ */
  function initCanvas() {
    canvas = document.getElementById('caCanvas');
    if (!canvas) return;
    ctx = canvas.getContext('2d');
    resizeCanvas();
    window.addEventListener('resize', resizeCanvas);
  }

  function resizeCanvas() {
    if (!canvas) return;
    const container = canvas.parentElement;
    canvas.width = container.clientWidth;
    canvas.height = container.clientHeight;
    if (currentClusters.length > 0) {
      computeClusterCenters();
      particles.forEach(p => {
        const cc = clusterCenters[p.clusterId] || clusterCenters[0];
        if (cc) {
          p.targetX = cc.x + (Math.random() - 0.5) * cc.radius * 1.6;
          p.targetY = cc.y + (Math.random() - 0.5) * cc.radius * 1.6;
        }
      });
    }
  }

  function computeClusterCenters() {
    if (!canvas || currentClusters.length === 0) return;
    const W = canvas.width;
    const H = canvas.height;
    const n = currentClusters.length;
    const totalCustomers = currentClusters.reduce((s, c) => s + c.customers.length, 0);

    clusterCenters = [];

    if (n === 1) {
      clusterCenters.push({ x: W / 2, y: H / 2, radius: Math.min(W, H) * 0.3 });
      return;
    }

    const cols = Math.ceil(Math.sqrt(n * (W / H)));
    const rows = Math.ceil(n / cols);
    const cellW = W / cols;
    const cellH = H / rows;
    // reserve vertical space for labels above and count below
    const maxR = Math.min(cellW, cellH) * 0.32;

    for (let i = 0; i < n; i++) {
      const row = Math.floor(i / cols);
      const col = i % cols;
      const cx = cellW * (col + 0.5);
      const cy = cellH * (row + 0.5) + 8; // shift down a bit for label above
      const fraction = totalCustomers > 0 ? currentClusters[i].customers.length / totalCustomers : 1 / n;
      const radius = Math.max(16, maxR * Math.sqrt(fraction * n));
      clusterCenters.push({ x: cx, y: cy, radius: Math.min(radius, maxR) });
    }
  }

  function assignParticles() {
    if (!canvas || currentClusters.length === 0) return;

    const totalCustomers = currentClusters.reduce((s, c) => s + c.customers.length, 0);
    const sampleRate = totalCustomers > MAX_PARTICLES ? MAX_PARTICLES / totalCustomers : 1;

    const newAssignments = [];
    currentClusters.forEach((cluster, ci) => {
      const cc = clusterCenters[ci];
      if (!cc) return;
      const count = Math.max(1, Math.round(cluster.customers.length * sampleRate));
      for (let j = 0; j < count; j++) {
        const cust = cluster.customers[Math.min(j, cluster.customers.length - 1)];
        const angle = Math.random() * Math.PI * 2;
        const dist = Math.random() * cc.radius * 0.85;
        newAssignments.push({
          clusterId: ci,
          status: cust.status,
          targetX: cc.x + Math.cos(angle) * dist,
          targetY: cc.y + Math.sin(angle) * dist,
        });
      }
    });

    if (particles.length === 0) {
      const cx = canvas.width / 2;
      const cy = canvas.height / 2;
      particles = newAssignments.map(a => ({
        x: cx + (Math.random() - 0.5) * 40,
        y: cy + (Math.random() - 0.5) * 40,
        vx: 0, vy: 0,
        targetX: a.targetX, targetY: a.targetY,
        clusterId: a.clusterId, status: a.status,
        phase: Math.random() * Math.PI * 2,
      }));
    } else {
      const newP = [];
      for (let i = 0; i < newAssignments.length; i++) {
        const a = newAssignments[i];
        if (i < particles.length) {
          particles[i].targetX = a.targetX;
          particles[i].targetY = a.targetY;
          particles[i].clusterId = a.clusterId;
          particles[i].status = a.status;
          newP.push(particles[i]);
        } else {
          const src = particles[Math.floor(Math.random() * particles.length)];
          newP.push({
            x: src ? src.x : canvas.width / 2,
            y: src ? src.y : canvas.height / 2,
            vx: 0, vy: 0,
            targetX: a.targetX, targetY: a.targetY,
            clusterId: a.clusterId, status: a.status,
            phase: Math.random() * Math.PI * 2,
          });
        }
      }
      particles = newP;
    }
  }

  /* ── Animation Loop ── */
  const STATUS_COLORS = {
    active: { r: 34, g: 197, b: 94 },
    defaulted: { r: 239, g: 68, b: 68 },
    closed: { r: 148, g: 163, b: 184 },
  };

  function startAnimation() {
    if (animFrameId) return;
    animate();
  }

  function stopAnimation() {
    if (animFrameId) { cancelAnimationFrame(animFrameId); animFrameId = null; }
  }

  function animate() {
    if (!modalOpen || !canvas || !ctx) { animFrameId = null; return; }

    const W = canvas.width;
    const H = canvas.height;
    ctx.clearRect(0, 0, W, H);

    const isDark = document.documentElement.getAttribute('data-theme') === 'dark';
    const labelColor = isDark ? 'rgba(199, 210, 254, 0.9)' : 'rgba(67, 56, 202, 0.85)';
    const subLabelColor = isDark ? 'rgba(148, 163, 184, 0.7)' : 'rgba(100, 116, 139, 0.7)';

    // draw cluster boundaries + labels
    currentClusters.forEach((cluster, i) => {
      const cc = clusterCenters[i];
      if (!cc) return;

      const dr = cluster.defaultRate;
      let borderColor;
      if (dr < 3) borderColor = isDark ? 'rgba(34, 197, 94, 0.3)' : 'rgba(34, 197, 94, 0.25)';
      else if (dr < 10) borderColor = isDark ? 'rgba(234, 179, 8, 0.3)' : 'rgba(234, 179, 8, 0.25)';
      else borderColor = isDark ? 'rgba(239, 68, 68, 0.3)' : 'rgba(239, 68, 68, 0.25)';

      const isSelected = selectedClusterIds.has(i);

      // outer glow
      ctx.beginPath();
      ctx.arc(cc.x, cc.y, cc.radius + 4, 0, Math.PI * 2);
      ctx.fillStyle = isSelected ? 'rgba(99, 102, 241, 0.08)' : 'rgba(148, 163, 184, 0.03)';
      ctx.fill();

      // boundary ring
      ctx.beginPath();
      ctx.arc(cc.x, cc.y, cc.radius, 0, Math.PI * 2);
      ctx.strokeStyle = isSelected ? 'rgba(99, 102, 241, 0.5)' : borderColor;
      ctx.lineWidth = isSelected ? 2.5 : 1.2;
      ctx.setLineDash(isSelected ? [] : [4, 4]);
      ctx.stroke();
      ctx.setLineDash([]);

      // ── CLUSTER NAME LABEL (above circle) ──
      ctx.fillStyle = labelColor;
      ctx.font = '700 11px Inter, system-ui, sans-serif';
      ctx.textAlign = 'center';
      ctx.textBaseline = 'bottom';
      ctx.fillText(cluster.canvasLabel || cluster.label, cc.x, cc.y - cc.radius - 6);

      // ── Customer count label (below circle) ──
      ctx.fillStyle = subLabelColor;
      ctx.font = '600 9px Inter, system-ui, sans-serif';
      ctx.textBaseline = 'top';
      ctx.fillText(cluster.customers.length + ' cust.', cc.x, cc.y + cc.radius + 6);
    });

    // update & draw particles
    const now = performance.now() * 0.001;
    for (let i = 0; i < particles.length; i++) {
      const p = particles[i];

      const dx = p.targetX - p.x;
      const dy = p.targetY - p.y;
      p.vx += dx * 0.03;
      p.vy += dy * 0.03;

      p.phase += 0.02;
      p.vx += Math.sin(p.phase + i * 0.7) * 0.15;
      p.vy += Math.cos(p.phase + i * 1.1) * 0.15;

      p.vx *= 0.88;
      p.vy *= 0.88;
      p.x += p.vx;
      p.y += p.vy;

      const col = STATUS_COLORS[p.status] || STATUS_COLORS.active;
      const alpha = 0.75 + 0.2 * Math.sin(now * 2 + i);
      ctx.beginPath();
      ctx.arc(p.x, p.y, 3, 0, Math.PI * 2);
      ctx.fillStyle = `rgba(${col.r}, ${col.g}, ${col.b}, ${alpha})`;
      ctx.fill();
    }

    animFrameId = requestAnimationFrame(animate);
  }

  /* ═══════════════════════════════════
     SIDEBAR RENDERING
     ═══════════════════════════════════ */
  function renderClusterList() {
    const container = document.getElementById('caClusterList');
    if (!container) return;

    if (currentClusters.length === 0) {
      container.innerHTML = '<div class="ca-empty">No clusters found</div>';
      return;
    }

    let html = '';
    currentClusters.forEach((cluster, i) => {
      const isSelected = selectedClusterIds.has(i);
      const dr = cluster.defaultRate;
      let riskClass = 'ca-risk-low';
      if (dr >= 10) riskClass = 'ca-risk-high';
      else if (dr >= 3) riskClass = 'ca-risk-mid';

      html += `
        <div class="ca-cluster-row ${isSelected ? 'ca-selected' : ''}" onclick="caToggleCluster(${i})">
          <div class="ca-cluster-dot ${riskClass}"></div>
          <div class="ca-cluster-info">
            <div class="ca-cluster-label">${escHtml(cluster.label)}</div>
            <div class="ca-cluster-meta">
              <span>${cluster.customers.length} cust</span>
              <span class="ca-sep">·</span>
              <span>₹${formatNum(Math.round(cluster.totalLent))}</span>
              <span class="ca-sep">·</span>
              <span class="${riskClass}">${Math.round(dr)}% def</span>
            </div>
          </div>
          <div class="ca-cluster-counts">
            <span class="ca-cnt-active">${cluster.activeCount}</span>
            <span class="ca-cnt-def">${cluster.defaultedCount}</span>
            <span class="ca-cnt-cls">${cluster.closedCount}</span>
          </div>
        </div>`;
    });
    container.innerHTML = html;
  }

  /* ═══════════════════════════════════
     ANALYTICS PANEL
     ═══════════════════════════════════ */
  function showAnalyticsPanel() {
    const panel = document.getElementById('caAnalyticsPanel');
    if (!panel) return;
    panel.classList.add('ca-analytics-visible');

    const selected = [...selectedClusterIds].map(id => currentClusters[id]).filter(Boolean);
    if (selected.length === 0) return;

    if (compareMode && selected.length === 2) {
      renderCompareView(selected[0], selected[1]);
    } else {
      renderSingleView(selected[0]);
    }
  }

  function hideAnalyticsPanel() {
    const panel = document.getElementById('caAnalyticsPanel');
    if (panel) panel.classList.remove('ca-analytics-visible');
    if (analyticsChart) { analyticsChart.destroy(); analyticsChart = null; }
  }

  function renderSingleView(cluster) {
    const html = `
      <div class="ca-analytics-header">
        <h4>${escHtml(cluster.label)}</h4>
        <button class="ca-close-analytics" onclick="document.getElementById('caAnalyticsPanel').classList.remove('ca-analytics-visible')">✕</button>
      </div>
      <div class="ca-kpi-grid">
        ${kpiCard('Customers', cluster.customers.length, 'fas fa-users')}
        ${kpiCard('Total Lent', '₹' + formatNum(Math.round(cluster.totalLent)), 'fas fa-hand-holding-usd')}
        ${kpiCard('Total Paid', '₹' + formatNum(Math.round(cluster.totalPaid)), 'fas fa-coins')}
        ${kpiCard('Balance', '₹' + formatNum(Math.round(cluster.totalBalance)), 'fas fa-wallet')}
        ${kpiCard('Default Rate', Math.round(cluster.defaultRate) + '%', 'fas fa-exclamation-triangle', cluster.defaultRate >= 10 ? 'danger' : cluster.defaultRate >= 3 ? 'warning' : 'success')}
        ${kpiCard('Recovery', Math.round(cluster.recoveryRate) + '%', 'fas fa-chart-line', cluster.recoveryRate >= 80 ? 'success' : cluster.recoveryRate >= 50 ? 'warning' : 'danger')}
      </div>
      <div class="ca-chart-section">
        <h5>Status Distribution</h5>
        <canvas id="caDetailChart" height="200"></canvas>
      </div>`;
    document.getElementById('caAnalyticsContent').innerHTML = html;
    renderStatusChart(cluster);
  }

  function renderCompareView(a, b) {
    const html = `
      <div class="ca-analytics-header">
        <h4>Compare: ${escHtml(a.label)} vs ${escHtml(b.label)}</h4>
        <button class="ca-close-analytics" onclick="document.getElementById('caAnalyticsPanel').classList.remove('ca-analytics-visible')">✕</button>
      </div>
      <div class="ca-compare-grid">
        <div class="ca-compare-col">
          <div class="ca-compare-title">${escHtml(a.label)}</div>
          <div class="ca-kpi-grid ca-kpi-compact">
            ${kpiCard('Customers', a.customers.length, '')}
            ${kpiCard('Lent', '₹' + formatNum(Math.round(a.totalLent)), '')}
            ${kpiCard('Def Rate', Math.round(a.defaultRate) + '%', '', a.defaultRate >= 10 ? 'danger' : 'success')}
            ${kpiCard('Recovery', Math.round(a.recoveryRate) + '%', '', a.recoveryRate >= 80 ? 'success' : 'danger')}
          </div>
        </div>
        <div class="ca-compare-divider"></div>
        <div class="ca-compare-col">
          <div class="ca-compare-title">${escHtml(b.label)}</div>
          <div class="ca-kpi-grid ca-kpi-compact">
            ${kpiCard('Customers', b.customers.length, '')}
            ${kpiCard('Lent', '₹' + formatNum(Math.round(b.totalLent)), '')}
            ${kpiCard('Def Rate', Math.round(b.defaultRate) + '%', '', b.defaultRate >= 10 ? 'danger' : 'success')}
            ${kpiCard('Recovery', Math.round(b.recoveryRate) + '%', '', b.recoveryRate >= 80 ? 'success' : 'danger')}
          </div>
        </div>
      </div>
      <div class="ca-chart-section">
        <h5>Side-by-Side Composition</h5>
        <canvas id="caDetailChart" height="220"></canvas>
      </div>`;
    document.getElementById('caAnalyticsContent').innerHTML = html;
    renderCompareChart(a, b);
  }

  function kpiCard(title, value, icon, variant) {
    const cls = variant ? 'ca-kpi-' + variant : '';
    const iconHtml = icon ? `<i class="${icon}"></i>` : '';
    return `<div class="ca-kpi-card ${cls}">${iconHtml}<div class="ca-kpi-val">${value}</div><div class="ca-kpi-label">${title}</div></div>`;
  }

  function renderStatusChart(cluster) {
    const el = document.getElementById('caDetailChart');
    if (!el || typeof Chart === 'undefined') return;
    if (analyticsChart) analyticsChart.destroy();
    analyticsChart = new Chart(el, {
      type: 'doughnut',
      data: {
        labels: ['Active', 'Defaulted', 'Closed'],
        datasets: [{
          data: [cluster.activeCount, cluster.defaultedCount, cluster.closedCount],
          backgroundColor: ['rgba(34, 197, 94, 0.8)', 'rgba(239, 68, 68, 0.8)', 'rgba(148, 163, 184, 0.6)'],
          borderWidth: 0
        }]
      },
      options: {
        responsive: true, maintainAspectRatio: false, cutout: '60%',
        plugins: {
          legend: { position: 'bottom', labels: { color: getComputedStyle(document.documentElement).getPropertyValue('--text').trim() || '#333', font: { size: 11 } } }
        }
      }
    });
  }

  function renderCompareChart(a, b) {
    const el = document.getElementById('caDetailChart');
    if (!el || typeof Chart === 'undefined') return;
    if (analyticsChart) analyticsChart.destroy();
    analyticsChart = new Chart(el, {
      type: 'bar',
      data: {
        labels: ['Active', 'Defaulted', 'Closed', 'Recovery %', 'Default %'],
        datasets: [
          {
            label: a.label.substring(0, 20),
            data: [a.activeCount, a.defaultedCount, a.closedCount, Math.round(a.recoveryRate), Math.round(a.defaultRate)],
            backgroundColor: 'rgba(99, 102, 241, 0.7)', borderRadius: 4
          },
          {
            label: b.label.substring(0, 20),
            data: [b.activeCount, b.defaultedCount, b.closedCount, Math.round(b.recoveryRate), Math.round(b.defaultRate)],
            backgroundColor: 'rgba(236, 72, 153, 0.7)', borderRadius: 4
          }
        ]
      },
      options: {
        responsive: true, maintainAspectRatio: false,
        plugins: { legend: { position: 'top', labels: { color: getComputedStyle(document.documentElement).getPropertyValue('--text').trim() || '#333', font: { size: 11 } } } },
        scales: {
          x: { ticks: { color: '#94a3b8', font: { size: 10 } }, grid: { display: false } },
          y: { ticks: { color: '#94a3b8', font: { size: 10 } }, grid: { color: 'rgba(148, 163, 184, 0.1)' } }
        }
      }
    });
  }

  /* ═══════════════════════════════════
     UTILITIES
     ═══════════════════════════════════ */
  function showLoading(show) {
    const loader = document.getElementById('caLoading');
    const main = document.getElementById('caMainContent');
    if (loader) loader.style.display = show ? 'flex' : 'none';
    if (main) main.style.display = show ? 'none' : 'flex';
  }

  function formatNum(n) {
    return Number(n).toLocaleString('en-IN');
  }

  /** Compact format: 1000 → 1K, 100000 → 1L */
  function formatCompact(n) {
    if (n >= 100000) return Math.round(n / 100000) + 'L';
    if (n >= 1000) return Math.round(n / 1000) + 'K';
    return String(Math.round(n));
  }

  function escHtml(s) {
    const d = document.createElement('div');
    d.textContent = s;
    return d.innerHTML;
  }

})();
