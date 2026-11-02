document.addEventListener("DOMContentLoaded", function () {
  const vid = window.activeVillageId;
  
  // Initialize dashboard view toggle state
  const currentView = localStorage.getItem("dashboardView") || "active";
  const toggle = document.getElementById("dashboardViewToggle");
  if (toggle) {
    toggle.classList.remove("mode-active", "mode-complete");
    toggle.classList.add(`mode-${currentView}`);
  }

  if (vid) {
    loadDashboardData(vid);
  }
});


let activeVillageChart = null;
let historyChartInstance = null;

// ── Chart Theme Helper ──
function getChartThemeColors() {
  const isDark = document.documentElement.getAttribute('data-theme') === 'dark';
  return {
    legendColor: isDark ? '#9ca3af' : '#64748b',
    gridColor: isDark ? 'rgba(255,255,255,0.04)' : 'rgba(0,0,0,0.03)',
    tickColor: isDark ? '#9ca3af' : '#6b7280',
    tooltipBg: isDark ? 'rgba(15, 23, 42, 0.95)' : 'rgba(26, 26, 46, 0.95)',
    tooltipTitle: '#9ca3af',
    tooltipBody: '#f8fafc',
    tooltipBorder: isDark ? 'rgba(255,255,255,0.08)' : 'rgba(255,255,255,0.1)',
    totalLine: isDark ? '#10b981' : '#1a4d2e'
  };
}

let cachedDashboardHistory = null;
let cachedConsecutiveSkippers = [];
let cachedFirstTimeSkippers = [];
let postingTrendChartInstance = null;
let currentModalCategory = null;
let currentModalRange = "weekly";
let cachedTransitions = {};
let cachedRiskDistribution = null;
let cachedAttention = {};

async function loadDashboardData(vid, forceRecalc = false) {
  const loadingEl = document.getElementById("vpopLoading");
  const contentEl = document.getElementById("vpopContent");
  const emptyEl = document.getElementById("vpopEmpty");
  const refreshBtn = document.getElementById("vpopRecalcBtn");

  if (!loadingEl || !contentEl || !emptyEl) return;

  // Show loading state
  loadingEl.style.display = "flex";
  contentEl.style.display = "none";
  emptyEl.style.display = "none";
  if (refreshBtn) refreshBtn.classList.add("spinning");

  const currentView = localStorage.getItem("dashboardView") || "active";
  const localSubView = localStorage.getItem("villageCardSubView") || "active_only";

  try {
    const forceStr = forceRecalc ? "&force_recalc=true" : "";
    loadingEl.style.display = "none";
    contentEl.style.display = "flex";

    const safeJson = async (res) => {
      const ct = res.headers.get("content-type") || "";
      if (!ct.includes("application/json")) {
        return { success: false, error: `Server returned non-JSON response (HTTP ${res.status})` };
      }
      return res.json();
    };

    const dashboardPromise = fetch(
      `/api/dashboard/analytics/${vid}?view=${currentView}`
    ).then(safeJson);

    const postingPromise = fetch(
      `/api/dashboard/posting_analytics/${vid}`
    ).then(safeJson);

    const behavioralPromise = fetch(
      `/api/village/behavioral_analytics/${vid}?view=${currentView}&sub_view=${localSubView}${forceStr}`
    ).then(safeJson);

    const dashboardResult = await dashboardPromise;

    if (dashboardResult.success) {
      const dbData = dashboardResult.data;

      populateDashboardTiles(dbData);
      cachedDashboardHistory = dbData.history;
      bindTileDoubleClickListeners();
    }

    if (refreshBtn) refreshBtn.classList.remove("spinning");

    postingPromise.then((postingResult) => {
        if (!postingResult.success) {
          console.warn(
            "Posting analytics unavailable:",
            postingResult.error || "Unknown error"
          );

          const section = document.getElementById("vpopPostingAnalyticsSection");
          if (section) section.style.display = "none";
          return;
        }

        if (postingResult.data) {
          populatePostingAnalytics(postingResult.data);
        }
      })
      .catch((err) => {
        console.error("Posting analytics failed:", err);
      });

    const behavioralResult = await behavioralPromise;
    if (!behavioralResult.success) {
      console.error("Village behavioral analytics error:", behavioralResult.error || "Unknown error");
      // Don't block — the rest of the dashboard has already loaded
      return;
    }
    const data = behavioralResult.data;
    if (data.empty) {
      loadingEl.style.display = "none";
      emptyEl.style.display = "flex";
      return;
    }

    window.isMonthlyVillage = !!data.is_monthly;

    // Populate Headers
    const nameEl = document.getElementById("vpopNameTitle");
    const codeEl = document.getElementById("vpopCodeTitle");
    if (nameEl) nameEl.textContent = data.village_name;
    if (codeEl) codeEl.textContent = data.village_code;

    // 1. Render Health Score, SVG Circle & Status
    const score = data.health.score;
    const scoreEl = document.getElementById("vpopHealthScore");
    const riskEl = document.getElementById("vpopPredictedRisk");
    const trendEl = document.getElementById("vpopWeeklyTrend");
    const trendPeriodEl = document.getElementById("lblHealthTrendPeriod");
    if (trendPeriodEl) {
      trendPeriodEl.textContent = window.isMonthlyVillage ? "Monthly Trend" : "Weekly Trend";
    }
    if (scoreEl) scoreEl.textContent = score;

    const ring = document.getElementById("vpopHealthProgressRing");
    if (ring) {
      const circumference = 301.6;
      const offset = circumference - (score / 100) * circumference;
      ring.style.strokeDashoffset = offset;
      
      // Color transition based on score
      if (score >= 80) ring.setAttribute("stroke", "#10b981");
      else if (score >= 70) ring.setAttribute("stroke", "#38bdf8");
      else if (score >= 55) ring.setAttribute("stroke", "#fbbf24");
      else ring.setAttribute("stroke", "#ef4444");
    }

    const healthSubToggle = document.getElementById("healthSubToggleContainer");
    if (healthSubToggle) {
      if (currentView === "active") {
        healthSubToggle.style.display = "inline-flex";
        const mappedClass = localSubView === "active_defaulted" ? "mode-default" : "mode-active_only";
        healthSubToggle.className = `health-sub-toggle-container ${mappedClass}`;
      } else {
        healthSubToggle.style.display = "none";
      }
    }

    const statusBadge = document.getElementById("vpopHealthStatus");
    if (statusBadge) {
      statusBadge.textContent = data.health.status;
      statusBadge.className = "status-badge";
      if (data.health.status === "Excellent") statusBadge.classList.add("status-active");
      else if (data.health.status === "Stable") statusBadge.classList.add("status-frozen");
      else if (data.health.status === "Warning") statusBadge.classList.add("status-defaulted");
      else statusBadge.classList.add("status-closed");
    }

    if (riskEl) {
      riskEl.textContent = data.health.predicted_risk;
      if (data.health.predicted_risk === "Low") riskEl.style.color = "#10b981";
      else if (data.health.predicted_risk === "Medium") riskEl.style.color = "#fbbf24";
      else if (data.health.predicted_risk === "High") riskEl.style.color = "#f97316";
      else riskEl.style.color = "#ef4444";
    }

    if (trendEl) {
      trendEl.textContent = data.health.trend_text;
      if (data.health.trend_val > 0) trendEl.style.color = "#10b981";
      else if (data.health.trend_val < 0) trendEl.style.color = "#ef4444";
      else trendEl.style.color = "#94a3b8";
    }

    // 2. Render Individual Health Metrics Panel
    const metricsListEl = document.getElementById("vpopMetricsList");
    if (metricsListEl && data.metrics) {
      metricsListEl.innerHTML = "";
      
      const metricsDef = [
        { key: "avg_rating", label: "Average Rating", weight: "65% Weight", isPenalty: false },
        { key: "stability", label: "Stability Momentum", weight: "15% Weight", isPenalty: false },
        { key: "default_rate", label: "Portfolio Default Rate", weight: "20% Weight", isPenalty: false },
        { key: "overdue_penalty", label: "Overdue Concentration", weight: "-0.3x Penalty", isPenalty: true },
        { key: "severe_risk_penalty", label: "Severe Credit Risk", weight: "-0.3x Penalty", isPenalty: true },
        { key: "collection_drop", label: "Collection Drop Penalty", weight: "-10 pts Penalty", isPenalty: true },
        { key: "customer_count_scale", label: "Customer Count Scaling", weight: "150 Threshold", isPenalty: false },
        { key: "portfolio_size_factor", label: "Portfolio Size Factor", weight: "Reward / Penalty", isPenalty: false }
      ];
      
      metricsDef.forEach(m => {
        const mData = data.metrics[m.key];
        if (!mData) return;
        
        let valStr = "";
        let contribStr = "";
        let contribColor = "";
        
        if (m.key === "collection_drop") {
          valStr = `${mData.drop_pct}% drop`;
          contribStr = mData.contribution < 0 ? `${mData.contribution} pts` : "0 pts";
          contribColor = mData.contribution < 0 ? "#ef4444" : "#10b981";
        } else if (m.key === "customer_count_scale") {
          valStr = `${mData.count} active`;
          contribStr = mData.contribution >= 0 ? `+${mData.contribution} pts` : `${mData.contribution} pts`;
          contribColor = mData.contribution >= 0 ? "#10b981" : "#ef4444";
        } else if (m.key === "portfolio_size_factor") {
          valStr = `₹${Math.round(mData.loan_sum / 100000).toFixed(0)}L sum`;
          contribStr = mData.contribution >= 0 ? `+${mData.contribution} pts` : `${mData.contribution} pts`;
          contribColor = mData.contribution >= 0 ? "#10b981" : "#ef4444";
        } else {
          valStr = `${mData.value}%`;
          if (m.isPenalty) {
            contribStr = mData.contribution < 0 ? `${mData.contribution} pts` : "0 pts";
            contribColor = mData.contribution < 0 ? "#ef4444" : "#10b981";
          } else {
            contribStr = `+${mData.contribution} pts`;
            contribColor = "#10b981";
          }
        }
        
        const card = document.createElement("div");
        card.className = "metric-list-item";
        card.setAttribute("ondblclick", "event.stopPropagation(); openHealthModal('" + m.key + "')");
        card.setAttribute("title", "Double-click to view history");
        
        card.innerHTML = `
          <div style="display: flex; align-items: center; gap: 6px;">
            <span class="metric-item-label" style="font-size: 0.725rem; font-weight: 700;">${m.label}</span>
            <span class="metric-item-weight" style="font-size: 0.55rem; font-weight: 600; padding: 1px 6px; border-radius: 4px; text-transform: uppercase;">${m.weight}</span>
          </div>
          <div style="display: flex; align-items: center; gap: 8px;">
            <span class="metric-item-value" style="font-size: 0.8rem; font-weight: 800;">${valStr}</span>
            <span style="font-size: 0.725rem; font-weight: 800; color: ${contribColor};">${contribStr}</span>
          </div>
        `;
        metricsListEl.appendChild(card);
      });
    }

    // 3. Render Risk Distribution Panel
    data.risk_distribution.forEach(item => {
      const cat = item.category; // Excellent, Good, LowRisk, HighRisk
      const cntEl = document.getElementById(`vRiskCount_${cat}`);
      const pctEl = document.getElementById(`vRiskPct_${cat}`);
      const changeEl = document.getElementById(`vRiskChange_${cat}`);

      if (cntEl) cntEl.textContent = item.count;
      if (pctEl) pctEl.textContent = `${item.percentage}%`;
      if (changeEl) {
        changeEl.textContent = item.change;
        if (item.change.startsWith("+")) {
          // Excellent and Good increasing is green, High/Low increasing is red
          if (cat === "Excellent" || cat === "Good") {
            changeEl.style.color = "#10b981";
          } else {
            changeEl.style.color = "#ef4444";
          }
        } else if (item.change.startsWith("-")) {
          if (cat === "Excellent" || cat === "Good") {
            changeEl.style.color = "#ef4444";
          } else {
            changeEl.style.color = "#10b981";
          }
        } else {
          changeEl.style.color = "#64748b";
        }
      }
    });

    // Cache risk distribution and transitions data
    cachedRiskDistribution = data.risk_distribution;
    cachedTransitions = data.transitions;

    // Populate transition counts
    Object.keys(data.transitions).forEach(key => {
      const countEl = document.getElementById(`vMoveCount_${key}`);
      if (countEl) {
        countEl.textContent = data.transitions[key].length;
      }
    });

    // Reset/Close cohort inspector on load, preserving active view if set
    if (window.activeCohortKey) {
      const savedKey = window.activeCohortKey;
      window.activeCohortKey = null;
      closeCohortInspector();
      inspectCohortFlow(savedKey);
    } else {
      closeCohortInspector();
    }

    // 5. Populate Attention Cards
    cachedAttention = data.critical_attention;
    const attentionKeys = ["Missed4Plus", "RapidCollapse", "SevereOverdue", "RatingBelow40"];
    attentionKeys.forEach(key => {
      const group = data.critical_attention[key];
      const countEl = document.getElementById(`vAttentionCount_${key}`);
      const cardEl = document.getElementById(`vAttentionCard_${key}`);
      if (countEl) countEl.textContent = group.count;
      if (cardEl) {
        if (group.count > 0) {
          cardEl.classList.add("has-items");
        } else {
          cardEl.classList.remove("has-items");
        }
      }
    });

    // Show content
   

  } catch (err) {
    console.error("Dashboard render failed:", err);
    if (refreshBtn) refreshBtn.classList.remove("spinning");
    loadingEl.style.display = "none";
  }
}

function refreshDashboardData() {
  const vid = window.activeVillageId;
  if (vid) {
    loadDashboardData(vid, true);
  }
}

function toggleDashboardView() {
  const toggle = document.getElementById("dashboardViewToggle");
  if (!toggle) return;

  let currentView = "active";
  if (toggle.classList.contains("mode-active")) {
    toggle.classList.remove("mode-active");
    toggle.classList.add("mode-complete");
    currentView = "complete";
  } else {
    toggle.classList.remove("mode-complete");
    toggle.classList.add("mode-active");
    currentView = "active";
  }
  
  localStorage.setItem("dashboardView", currentView);
  
  // Reload dashboard data
  const vid = window.activeVillageId;
  if (vid) {
    loadDashboardData(vid);
  }
}
window.toggleDashboardView = toggleDashboardView;

function renderTrendGraph(trendData) {
  const ctx = document.getElementById("vHealthChart");
  if (!ctx) return;

  if (activeVillageChart) {
    activeVillageChart.destroy();
  }

  // Chronological weeks (oldest -> newest) are pre-ordered in backend trendData
  const labels = trendData.map(d => d.date);
  const healthScores = trendData.map(d => d.health_score);
  const avgRatings = trendData.map(d => d.avg_rating);
  const overduePcts = trendData.map(d => d.overdue_pct);

  activeVillageChart = new Chart(ctx, {
    type: "line",
    data: {
      labels: labels,
      datasets: [
        {
          label: "Health Score",
          data: healthScores,
          borderColor: "#00f2fe",
          backgroundColor: "rgba(0, 242, 254, 0.05)",
          borderWidth: 3,
          tension: 0.35,
          pointRadius: 4,
          pointBackgroundColor: "#00f2fe",
          fill: true
        },
        {
          label: "Avg Rating",
          data: avgRatings,
          borderColor: "#10b981",
          backgroundColor: "transparent",
          borderWidth: 2,
          tension: 0.35,
          pointRadius: 3,
          pointBackgroundColor: "#10b981"
        },
        {
          label: "Overdue %",
          data: overduePcts,
          borderColor: "#ef4444",
          backgroundColor: "transparent",
          borderWidth: 2,
          tension: 0.35,
          pointRadius: 3,
          pointBackgroundColor: "#ef4444"
        }
      ]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: {
          display: true,
          position: "top",
          labels: {
            color: getChartThemeColors().legendColor,
            boxWidth: 12,
            font: {
              size: 10,
              family: "Inter"
            }
          }
        },
        tooltip: {
          mode: "index",
          intersect: false,
          backgroundColor: getChartThemeColors().tooltipBg,
          titleColor: getChartThemeColors().tooltipTitle,
          bodyColor: getChartThemeColors().tooltipBody,
          borderColor: getChartThemeColors().tooltipBorder,
          borderWidth: 1,
          textDirection: "ltr"
        }
      },
      scales: {
        x: {
          grid: {
            color: getChartThemeColors().gridColor
          },
          ticks: {
            color: getChartThemeColors().tickColor,
            font: {
              size: 9
            }
          }
        },
        y: {
          min: 0,
          max: 100,
          grid: {
            color: getChartThemeColors().gridColor
          },
          ticks: {
            color: getChartThemeColors().tickColor,
            font: {
              size: 9
            },
            stepSize: 20
          }
        }
      }
    }
  });
}

function closeCohortInspector() {
  const inspector = document.getElementById("vpopCohortInspector");
  if (inspector) {
    inspector.style.display = "none";
    document.getElementById("vCohortInspectorTableBody").innerHTML = "";
    
    // Clear search input
    const searchInput = document.getElementById("vCohortInspectorSearch");
    if (searchInput) searchInput.value = "";
  }
  // Remove active classes
  document.querySelectorAll(".premium-cohort-card").forEach(el => el.classList.remove("active"));
  document.querySelectorAll(".premium-flow-connector").forEach(el => el.classList.remove("active"));
  document.querySelectorAll(".aux-flow-btn").forEach(el => el.classList.remove("active"));
  document.querySelectorAll(".attention-capsule").forEach(el => el.classList.remove("active"));
  window.activeCohortKey = null;
}
window.closeCohortInspector = closeCohortInspector;

function inspectCohortFlow(key) {
  const inspector = document.getElementById("vpopCohortInspector");
  if (!inspector) return;
  
  window.activeCohortKey = key;

  let clickedElement = null;
  if (["Excellent", "Good", "LowRisk", "HighRisk"].includes(key)) {
    clickedElement = document.getElementById(`vRiskCard_${key}`);
  } else if (["Excellent_Good", "Good_LowRisk", "LowRisk_HighRisk"].includes(key)) {
    clickedElement = document.getElementById(`vFlowConnector_${key}`);
  } else if (key === "Recovered") {
    clickedElement = document.getElementById("vAuxRecovered");
  } else if (key === "Newly_Overdue") {
    clickedElement = document.getElementById("vAuxOverdue");
  } else if (["Missed4Plus", "RapidCollapse", "SevereOverdue", "RatingBelow40"].includes(key)) {
    clickedElement = document.getElementById(`vAttentionCard_${key}`);
  } else if (key === "ConsecutiveSkippers") {
    clickedElement = document.getElementById("vAuxConsecutiveSkippers");
  } else if (key === "FirstTimeSkippers") {
    clickedElement = document.getElementById("vAuxFirstTimeSkippers");
  }

  // Toggle behaviour: if clicked active element, close it
  if (clickedElement && clickedElement.classList.contains("active")) {
    closeCohortInspector();
    return;
  }

  // Remove active highlights
  document.querySelectorAll(".premium-cohort-card").forEach(el => el.classList.remove("active"));
  document.querySelectorAll(".premium-flow-connector").forEach(el => el.classList.remove("active"));
  document.querySelectorAll(".aux-flow-btn").forEach(el => el.classList.remove("active"));
  document.querySelectorAll(".attention-capsule").forEach(el => el.classList.remove("active"));

  if (clickedElement) clickedElement.classList.add("active");

  const periodUnit = window.isMonthlyVillage ? "month" : "week";
  const periodUnitPlural = window.isMonthlyVillage ? "months" : "weeks";
  const periodUnitCap = window.isMonthlyVillage ? "Month" : "Week";

  let list = [];
  let title = "";
  let subtitle = "";

  if (["Excellent", "Good", "LowRisk", "HighRisk"].includes(key)) {
    const cohort = cachedRiskDistribution ? cachedRiskDistribution.find(item => item.category === key) : null;
    list = cohort ? cohort.list : [];
    const displayLabel = key === "LowRisk" ? "Low Risk" : (key === "HighRisk" ? "High Risk" : key);
    title = `${displayLabel} Cohort`;
    subtitle = `${list.length} customers currently in ${displayLabel} category`;
  } else if (["Excellent_Good", "Good_LowRisk", "LowRisk_HighRisk"].includes(key)) {
    list = cachedTransitions ? cachedTransitions[key] : [];
    const labelMap = {
      "Excellent_Good": "Excellent → Good",
      "Good_LowRisk": "Good → Low Risk",
      "LowRisk_HighRisk": "Low Risk → High Risk"
    };
    title = `${labelMap[key]} Transitions`;
    subtitle = `${list.length} customers downgraded this ${periodUnit}`;
  } else if (key === "Recovered") {
    list = cachedTransitions ? cachedTransitions.Recovered : [];
    title = "Recovered Customers";
    subtitle = `${list.length} customers moved from overdue/delay back to On-Track status`;
  } else if (key === "Newly_Overdue") {
    list = cachedTransitions ? cachedTransitions.Newly_Overdue : [];
    title = `Newly Overdue (This ${periodUnitCap})`;
    subtitle = `${list.length} customers entered overdue status this ${periodUnit}`;
  } else if (["Missed4Plus", "RapidCollapse", "SevereOverdue", "RatingBelow40"].includes(key)) {
    const group = cachedAttention ? cachedAttention[key] : null;
    list = group ? group.list : [];
    title = group ? group.label : "Attention Group";
    subtitle = `${list.length} customers in this category`;
  } else if (key === "ConsecutiveSkippers") {
    list = cachedConsecutiveSkippers || [];
    title = "Consecutive Skippers";
    subtitle = `${list.length} active customers skipped both of the last 2 posting dates`;
  } else if (key === "FirstTimeSkippers") {
    list = cachedFirstTimeSkippers || [];
    title = "First-Time Skippers (Streak of 2+ paid prior)";
    subtitle = `${list.length} active customers skipped this ${periodUnit} but paid the previous 2+ ${periodUnitPlural} consecutive`;
  }

  document.getElementById("vCohortInspectorTitle").textContent = title;
  document.getElementById("vCohortInspectorSubtitle").textContent = subtitle;

  const searchInput = document.getElementById("vCohortInspectorSearch");
  if (searchInput) searchInput.value = "";

  if (list && list.length > 0) {
    list.sort((a, b) => parseInt(b.ano, 10) - parseInt(a.ano, 10));
  }

  const tbody = document.getElementById("vCohortInspectorTableBody");
  tbody.innerHTML = "";

  if (list.length === 0) {
    tbody.innerHTML = `
      <tr>
        <td colspan="9" style="padding: 24px; text-align: center; color: #64748b; font-size: 0.85rem;">
          No customer records found in this category.
        </td>
      </tr>
    `;
    inspector.style.display = "flex";
    return;
  }

  list.forEach(c => {
    let badgeClass = "risk-badge-excellent";
    if (c.rating < 40) badgeClass = "risk-badge-critical";
    else if (c.rating < 60) badgeClass = "risk-badge-risky";
    else if (c.rating < 80) badgeClass = "risk-badge-good";

    const loanVal = formatRupee(c.total_amount);
    const paidVal = formatRupee(c.paid_amount);
    const balVal = formatRupee(c.balance_amount);

    const row = document.createElement("tr");
    row.className = "clickable-row";
    row.setAttribute("onclick", `window.openCustomerPopup('${c.ano}')`);
    const lastPmtDate = c.last_payment_date ? formatDate(c.last_payment_date) : "N/A";
    const missedCycles = c.missed_cycles !== undefined ? c.missed_cycles : "-";
    row.innerHTML = `
      <td style="font-weight: 700; color: #1a4d2e;">${c.ano}</td>
      <td style="text-align: left; font-weight: 600; color: #334155;">${c.name}</td>
      <td>${loanVal}</td>
      <td>${paidVal}</td>
      <td style="color: #ef4444; font-weight: 600;">${balVal}</td>
      <td><span class="status-badge ${badgeClass}" style="font-size: 0.65rem; font-weight:800; padding: 1px 6px;">${Math.round(c.rating)}</span></td>
      <td>${lastPmtDate}</td>
      <td style="color: ${missedCycles > 0 ? '#ef4444' : '#64748b'}; font-weight: 700;">${missedCycles}</td>
      <td><span class="status-badge status-${c.status === 'OnTrack' ? 'active' : (c.status === 'Overdue' ? 'defaulted' : 'closed')}" style="font-size: 0.65rem; font-weight:700; padding: 1px 6px;">${c.status}</span></td>
    `;
    tbody.appendChild(row);
  });

  inspector.style.display = "flex";
}
window.inspectCohortFlow = inspectCohortFlow;

function filterCohortInspectorTable() {
  const input = document.getElementById("vCohortInspectorSearch");
  const filter = input.value.toLowerCase().trim();
  const tbody = document.getElementById("vCohortInspectorTableBody");
  const rows = tbody.getElementsByTagName("tr");

  for (let i = 0; i < rows.length; i++) {
    const row = rows[i];
    if (row.cells.length === 1) continue; // skip no-records row
    
    const acNo = row.cells[0].textContent.toLowerCase();
    const name = row.cells[1].textContent.toLowerCase();
    
    if (acNo.includes(filter) || name.includes(filter)) {
      row.style.display = "";
    } else {
      row.style.display = "none";
    }
  }
}
window.filterCohortInspectorTable = filterCohortInspectorTable;

function updateTrendEl(el, trend, isRisk = false) {
  if (!el) return;
  el.className = ''; // reset classes
  if (trend === 'up') {
    el.textContent = '↑';
    el.className = isRisk ? 'trend-arrow risk-trend-up' : 'trend-arrow trend-up';
  } else if (trend === 'down') {
    el.textContent = '↓';
    el.className = isRisk ? 'trend-arrow risk-trend-down' : 'trend-arrow trend-down';
  } else {
    el.textContent = '→';
    el.className = 'trend-arrow trend-stable';
  }
}

function updateLargeTrendEl(el, trend, isRisk = false) {
  if (!el) return;
  el.className = '';
  if (trend === 'up') {
    el.textContent = '↑';
    el.className = isRisk ? 'trend-indicator-large risk-trend-up' : 'trend-indicator-large trend-up';
  } else if (trend === 'down') {
    el.textContent = '↓';
    el.className = isRisk ? 'trend-indicator-large risk-trend-down' : 'trend-indicator-large trend-down';
  } else {
    el.textContent = '→';
    el.className = 'trend-indicator-large trend-stable';
  }
}

function populateDashboardTiles(dbData) {
  const current = dbData.current;
  const trends = dbData.trends;

  // 1. Customers
  const totalCust = current.customers.total;
  document.getElementById("lblTotalCustomers").textContent = totalCust;
  updateLargeTrendEl(document.getElementById("trendTotalCustomers"), trends.customers.total);

  document.getElementById("lblActiveCustomers").textContent = totalCust ? current.customers.active : 0;
  const pctActiveCustVal = totalCust ? Math.round(current.customers.active / totalCust * 100) : 0;
  document.getElementById("pctActiveCustomers").textContent = `(${pctActiveCustVal}%)`;
  document.getElementById("barActiveCustomers").style.width = pctActiveCustVal + "%";

  document.getElementById("lblDefaultedCustomers").textContent = totalCust ? current.customers.defaulted : 0;
  const pctDefaultedCustVal = totalCust ? Math.round(current.customers.defaulted / totalCust * 100) : 0;
  document.getElementById("pctDefaultedCustomers").textContent = `(${pctDefaultedCustVal}%)`;
  document.getElementById("barDefaultedCustomers").style.width = pctDefaultedCustVal + "%";

  document.getElementById("lblClosedCustomers").textContent = totalCust ? current.customers.closed : 0;
  const pctClosedCustVal = totalCust ? Math.round(current.customers.closed / totalCust * 100) : 0;
  document.getElementById("pctClosedCustomers").textContent = `(${pctClosedCustVal}%)`;
  document.getElementById("barClosedCustomers").style.width = pctClosedCustVal + "%";

  // 2. Loan Amount
  const totalLoan = current.loan_amount.total;
  document.getElementById("lblTotalLoanAmount").textContent = formatRupee(totalLoan);
  updateLargeTrendEl(document.getElementById("trendTotalLoanAmount"), trends.loan_amount.total);

  document.getElementById("lblActiveLoanAmount").textContent = formatRupee(current.loan_amount.active);
  const pctActiveLoanVal = totalLoan ? Math.round(current.loan_amount.active / totalLoan * 100) : 0;
  document.getElementById("pctActiveLoanAmount").textContent = `(${pctActiveLoanVal}%)`;
  document.getElementById("barActiveLoanAmount").style.width = pctActiveLoanVal + "%";

  document.getElementById("lblDefaultedLoanAmount").textContent = formatRupee(current.loan_amount.defaulted);
  const pctDefaultedLoanVal = totalLoan ? Math.round(current.loan_amount.defaulted / totalLoan * 100) : 0;
  document.getElementById("pctDefaultedLoanAmount").textContent = `(${pctDefaultedLoanVal}%)`;
  document.getElementById("barDefaultedLoanAmount").style.width = pctDefaultedLoanVal + "%";

  document.getElementById("lblClosedLoanAmount").textContent = formatRupee(current.loan_amount.closed);
  const pctClosedLoanVal = totalLoan ? Math.round(current.loan_amount.closed / totalLoan * 100) : 0;
  document.getElementById("pctClosedLoanAmount").textContent = `(${pctClosedLoanVal}%)`;
  document.getElementById("barClosedLoanAmount").style.width = pctClosedLoanVal + "%";

  // 3. Balance
  const totalBal = current.balance.total;
  document.getElementById("lblTotalBalance").textContent = formatRupee(totalBal);
  updateLargeTrendEl(document.getElementById("trendTotalBalance"), trends.balance.total, true);

  document.getElementById("lblActiveBalance").textContent = formatRupee(current.balance.active);
  const pctActiveBalVal = totalBal ? Math.round(current.balance.active / totalBal * 100) : 0;
  document.getElementById("pctActiveBalance").textContent = `(${pctActiveBalVal}%)`;
  document.getElementById("barActiveBalance").style.width = pctActiveBalVal + "%";

  document.getElementById("lblDefaultedBalance").textContent = formatRupee(current.balance.defaulted);
  const pctDefaultedBalVal = totalBal ? Math.round(current.balance.defaulted / totalBal * 100) : 0;
  document.getElementById("pctDefaultedBalance").textContent = `(${pctDefaultedBalVal}%)`;
  document.getElementById("barDefaultedBalance").style.width = pctDefaultedBalVal + "%";

  // Render splits
  const loanSplit = current.loan_amount.split || { total: { p: 0, i: 0, r: 0 } };
  const balSplit = current.balance.split || { total: { p: 0, i: 0, r: 0 } };

  document.getElementById("lblLoanSplitPrincipal").textContent = formatRupee(loanSplit.total.p);
  document.getElementById("lblLoanSplitInterest").textContent = formatRupee(loanSplit.total.i);
  document.getElementById("lblLoanSplitRusum").textContent = formatRupee(loanSplit.total.r);

  document.getElementById("lblBalanceSplitPrincipal").textContent = formatRupee(balSplit.total.p);
  document.getElementById("lblBalanceSplitInterest").textContent = formatRupee(balSplit.total.i);
  document.getElementById("lblBalanceSplitRusum").textContent = formatRupee(balSplit.total.r);

  // Show Closed legends whenever closed accounts exist so tile breakdowns reconcile 100%
  const legendClosedCust = document.getElementById("legendClosedCustomers");
  const legendClosedLoan = document.getElementById("legendClosedLoanAmount");

  if (legendClosedCust) legendClosedCust.style.display = (current.customers && current.customers.closed > 0) ? "" : "none";
  if (legendClosedLoan) legendClosedLoan.style.display = (current.loan_amount && current.loan_amount.closed > 0) ? "" : "none";

  // 4. Interest Discount
  const discData = current.interest_discount || { total: 0, accounts: 0, avg: 0, pct_of_interest: 0 };
  const totalDisc = discData.total || 0;
  const discAccts = discData.accounts || 0;
  const avgDisc = discData.avg || 0;
  const pctDisc = discData.pct_of_interest || 0;

  const lblTotalDisc = document.getElementById("lblTotalInterestDiscount");
  if (lblTotalDisc) lblTotalDisc.textContent = formatRupee(totalDisc);

  const lblDiscWaived = document.getElementById("lblInterestDiscountWaived");
  if (lblDiscWaived) lblDiscWaived.textContent = formatRupee(totalDisc);

  const lblDiscAccts = document.getElementById("lblInterestDiscountAccounts");
  if (lblDiscAccts) lblDiscAccts.textContent = discAccts;

  const lblAvgD = document.getElementById("lblAvgInterestDiscount");
  if (lblAvgD) lblAvgD.textContent = formatRupee(avgDisc);

  const lblPctD = document.getElementById("lblInterestDiscountPct");
  if (lblPctD) lblPctD.textContent = `${Math.round(pctDisc)}%`;

  const trendDisc = document.getElementById("trendTotalInterestDiscount");
  if (trendDisc && trends && trends.interest_discount) {
    updateLargeTrendEl(trendDisc, trends.interest_discount.total);
  }
}

let doubleClickListenersBound = false;
function bindTileDoubleClickListeners() {
  if (doubleClickListenersBound) return;
  const tileCustomers = document.getElementById("tileCustomers");
  const tileLoanAmount = document.getElementById("tileLoanAmount");
  const tileBalance = document.getElementById("tileBalance");
  const villageHealthCard = document.getElementById("villageHealthCard");

  if (tileCustomers) {
    tileCustomers.addEventListener("dblclick", () => openHistoryModal("customers"));
  }
  if (tileLoanAmount) {
    tileLoanAmount.addEventListener("dblclick", () => openHistoryModal("loan_amount"));
  }
  if (tileBalance) {
    tileBalance.addEventListener("dblclick", () => openHistoryModal("balance"));
  }
  const tileInterestDiscount = document.getElementById("tileInterestDiscount");
  if (tileInterestDiscount) {
    tileInterestDiscount.addEventListener("dblclick", () => openHistoryModal("interest_discount"));
  }
  if (villageHealthCard) {
    villageHealthCard.addEventListener("dblclick", (e) => {
      if (e.target.closest("button") || e.target.closest(".health-sub-toggle-container") || e.target.closest(".metric-list-item")) {
        return;
      }
      if (typeof window.openHealthModal === "function") {
        window.openHealthModal("overall");
      }
    });
  }
  
  const modal = document.getElementById("historyModal");
  if (modal) {
    modal.addEventListener("click", function(e) {
      if (e.target === modal) {
        closeHistoryModal();
      }
    });
  }
  doubleClickListenersBound = true;
}

function openHistoryModal(category) {
  const modal = document.getElementById("historyModal");
  if (!modal || !cachedDashboardHistory) return;

  currentModalCategory = category;
  currentModalRange = window.isMonthlyVillage ? "monthly" : "weekly";

  // Reset toggle buttons active state
  document.querySelectorAll(".modal-time-toggle .time-btn").forEach(btn => {
    btn.classList.remove("active");
  });
  const activeBtnId = currentModalRange === "weekly" ? "btnTimeWeekly" : "btnTimeMonthly";
  const defaultBtn = document.getElementById(activeBtnId);
  if (defaultBtn) defaultBtn.classList.add("active");

  const titleEl = document.getElementById("modalChartTitle");
  if (titleEl) {
    const rangeText = currentModalRange === "weekly" ? "Last 12 Weeks" : "Last 12 Months";
    if (category === "customers") titleEl.textContent = `Historical Customers Trend (${rangeText})`;
    else if (category === "loan_amount") titleEl.textContent = `Historical Loan Amount Trend (${rangeText})`;
    else if (category === "balance") titleEl.textContent = `Historical Outstanding Balance Trend (${rangeText})`;
    else if (category === "interest_discount") titleEl.textContent = `Historical Interest Discount Trend (${rangeText})`;
  }

  modal.classList.add("show");
  
  setTimeout(() => {
    renderHistoryChart(category, currentModalRange);
  }, 100);
}

function closeHistoryModal() {
  const modal = document.getElementById("historyModal");
  if (modal) {
    modal.classList.remove("show");
  }
  if (historyChartInstance) {
    historyChartInstance.destroy();
    historyChartInstance = null;
  }
}

function switchModalTimeRange(range) {
  if (!currentModalCategory || !cachedDashboardHistory) return;
  currentModalRange = range;

  // Update button active state
  document.querySelectorAll(".modal-time-toggle .time-btn").forEach(btn => {
    btn.classList.remove("active");
  });

  const activeBtnId = range === "weekly" ? "btnTimeWeekly" : (range === "monthly" ? "btnTimeMonthly" : "btnTimeYearly");
  const activeBtn = document.getElementById(activeBtnId);
  if (activeBtn) {
    activeBtn.classList.add("active");
  }

  // Update title
  const titleEl = document.getElementById("modalChartTitle");
  if (titleEl) {
    const rangeText = range === "weekly" ? "Last 12 Weeks" : (range === "monthly" ? "Last 12 Months" : "Last 5 Years");
    if (currentModalCategory === "customers") titleEl.textContent = `Historical Customers Trend (${rangeText})`;
    else if (currentModalCategory === "loan_amount") titleEl.textContent = `Historical Loan Amount Trend (${rangeText})`;
    else if (currentModalCategory === "balance") titleEl.textContent = `Historical Outstanding Balance Trend (${rangeText})`;
    else if (currentModalCategory === "interest_discount") titleEl.textContent = `Historical Interest Discount Trend (${rangeText})`;
  }

  // Redraw chart
  renderHistoryChart(currentModalCategory, range);
}

window.switchModalTimeRange = switchModalTimeRange; // Expose globally for onclick handlers

function renderHistoryChart(category, range) {
  const ctx = document.getElementById("historyChart");
  if (!ctx || !cachedDashboardHistory) return;

  const historyData = cachedDashboardHistory[range] || [];

  if (historyChartInstance) {
    historyChartInstance.destroy();
  }

  const labels = historyData.map(h => h.date);
  let datasets = [];

  if (category === "customers") {
    datasets = [
      {
        label: "Active Customers",
        data: historyData.map(h => h.customers.active),
        borderColor: "#16a34a",
        backgroundColor: "rgba(22, 163, 74, 0.05)",
        borderWidth: 2,
        tension: 0.35,
        pointRadius: 4,
        pointBackgroundColor: "#16a34a",
        fill: true
      },
      {
        label: "Defaulted Customers",
        data: historyData.map(h => h.customers.defaulted),
        borderColor: "#dc2626",
        backgroundColor: "rgba(220, 38, 38, 0.05)",
        borderWidth: 2,
        tension: 0.35,
        pointRadius: 4,
        pointBackgroundColor: "#dc2626",
        fill: true
      },
      {
        label: "Closed Customers",
        data: historyData.map(h => h.customers.closed),
        borderColor: "#2563eb",
        backgroundColor: "rgba(37, 99, 235, 0.05)",
        borderWidth: 2,
        tension: 0.35,
        pointRadius: 4,
        pointBackgroundColor: "#2563eb",
        fill: true
      },
      {
        label: "Total Customers",
        data: historyData.map(h => h.customers.total),
        borderColor: getChartThemeColors().totalLine,
        backgroundColor: "transparent",
        borderWidth: 3,
        tension: 0.35,
        pointRadius: 5,
        pointBackgroundColor: getChartThemeColors().totalLine
      }
    ];
  } else if (category === "loan_amount") {
    datasets = [
      {
        label: "Active Loan Amount",
        data: historyData.map(h => h.loan_amount.active),
        borderColor: "#16a34a",
        backgroundColor: "rgba(22, 163, 74, 0.05)",
        borderWidth: 2,
        tension: 0.35,
        pointRadius: 4,
        pointBackgroundColor: "#16a34a",
        fill: true
      },
      {
        label: "Defaulted Loan Amount",
        data: historyData.map(h => h.loan_amount.defaulted),
        borderColor: "#dc2626",
        backgroundColor: "rgba(220, 38, 38, 0.05)",
        borderWidth: 2,
        tension: 0.35,
        pointRadius: 4,
        pointBackgroundColor: "#dc2626",
        fill: true
      },
      {
        label: "Closed Loan Amount",
        data: historyData.map(h => h.loan_amount.closed),
        borderColor: "#2563eb",
        backgroundColor: "rgba(37, 99, 235, 0.05)",
        borderWidth: 2,
        tension: 0.35,
        pointRadius: 4,
        pointBackgroundColor: "#2563eb",
        fill: true
      },
      {
        label: "Total Loan Amount",
        data: historyData.map(h => h.loan_amount.total),
        borderColor: getChartThemeColors().totalLine,
        backgroundColor: "transparent",
        borderWidth: 3,
        tension: 0.35,
        pointRadius: 5,
        pointBackgroundColor: getChartThemeColors().totalLine
      }
    ];
  } else if (category === "balance") {
    datasets = [
      {
        label: "Active Balance",
        data: historyData.map(h => h.balance.active),
        borderColor: "#16a34a",
        backgroundColor: "rgba(22, 163, 74, 0.05)",
        borderWidth: 2,
        tension: 0.35,
        pointRadius: 4,
        pointBackgroundColor: "#16a34a",
        fill: true
      },
      {
        label: "Defaulted Balance",
        data: historyData.map(h => h.balance.defaulted),
        borderColor: "#dc2626",
        backgroundColor: "rgba(220, 38, 38, 0.05)",
        borderWidth: 2,
        tension: 0.35,
        pointRadius: 4,
        pointBackgroundColor: "#dc2626",
        fill: true
      },
      {
        label: "Total Outstanding Balance",
        data: historyData.map(h => h.balance.total),
        borderColor: getChartThemeColors().totalLine,
        backgroundColor: "transparent",
        borderWidth: 3,
        tension: 0.35,
        pointRadius: 5,
        pointBackgroundColor: getChartThemeColors().totalLine
      }
    ];
  } else if (category === "interest_discount") {
    datasets = [
      {
        label: "Interest Discount Waived",
        data: historyData.map(h => (h.interest_discount && h.interest_discount.total) || 0),
        borderColor: "#8b5cf6",
        backgroundColor: "rgba(139, 92, 246, 0.08)",
        borderWidth: 2.5,
        tension: 0.35,
        pointRadius: 4,
        pointBackgroundColor: "#8b5cf6",
        fill: true
      }
    ];
  }

  const chartColors = getChartThemeColors();
  historyChartInstance = new Chart(ctx, {
    type: "line",
    data: {
      labels: labels,
      datasets: datasets
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: {
          display: true,
          position: "top",
          labels: {
            color: chartColors.legendColor,
            boxWidth: 12,
            font: {
              size: 11,
              family: "Inter",
              weight: 500
            }
          }
        },
        tooltip: {
          mode: "index",
          intersect: false,
          backgroundColor: chartColors.tooltipBg,
          titleColor: chartColors.tooltipTitle,
          bodyColor: chartColors.tooltipBody,
          borderColor: chartColors.tooltipBorder,
          borderWidth: 1,
          padding: 12,
          bodySpacing: 6,
          titleFont: {
            family: "Space Grotesk",
            size: 12,
            weight: 700
          },
          bodyFont: {
            family: "Inter",
            size: 11
          },
          callbacks: {
            label: function(context) {
              let label = context.dataset.label || '';
              if (label) {
                label += ': ';
              }
              if (context.parsed.y !== null) {
                if (category === 'customers') {
                  label += context.parsed.y;
                } else {
                  label += formatRupee(context.parsed.y);
                }
              }
              return label;
            }
          }
        }
      },
      scales: {
        x: {
          grid: {
            color: chartColors.gridColor
          },
          ticks: {
            color: chartColors.tickColor,
            font: {
              size: 10,
              family: "Inter"
            }
          }
        },
        y: {
          grid: {
            color: chartColors.gridColor
          },
          ticks: {
            color: chartColors.tickColor,
            font: {
              size: 10,
              family: "Inter"
            },
            callback: function(value) {
              if (category === "customers") {
                return value;
              } else {
                if (value >= 100000) {
                  return '₹' + Math.round(value / 100000).toFixed(0) + 'L';
                } else if (value >= 1000) {
                  return '₹' + Math.round(value / 1000).toFixed(0) + 'K';
                }
                return '₹' + Math.round(value).toFixed(0);
              }
            }
          }
        }
      }
    }
  });
}

function formatRupee(num) {
  if (num === null || num === undefined) return "₹0";
  const val = Math.round(parseFloat(num));
  return "₹" + val.toLocaleString('en-IN', { minimumFractionDigits: 0, maximumFractionDigits: 0 });
}

// ------------------ NEW: Village Health Sub-View & Modal Controllers ------------------

function toggleHealthSubView(event) {
  event.stopPropagation();
  const healthSubToggle = document.getElementById("healthSubToggleContainer");
  if (!healthSubToggle) return;
  
  let currentSubView = "active_only";
  if (healthSubToggle.classList.contains("mode-active_only")) {
    healthSubToggle.classList.remove("mode-active_only");
    healthSubToggle.classList.add("mode-default");
    currentSubView = "active_defaulted";
  } else {
    healthSubToggle.classList.remove("mode-default");
    healthSubToggle.classList.add("mode-active_only");
    currentSubView = "active_only";
  }
  
  localStorage.setItem("villageCardSubView", currentSubView);
  
  // Reload dashboard data
  const vid = window.activeVillageId;
  if (vid) {
    loadDashboardData(vid);
  }
}
window.toggleHealthSubView = toggleHealthSubView;

function flipVillageHealthCard(event) {
  if (event) event.stopPropagation();
  const container = document.querySelector(".flip-card-container");
  if (container) {
    container.classList.toggle("flipped");
  }
}
window.flipVillageHealthCard = flipVillageHealthCard;

let vHealthHistoryChartInstance = null;
let activeHealthModalCategory = "overall";
let activeHealthModalRange = "weekly";

function openHealthModal(category) {
  const modal = document.getElementById("villageHealthModal");
  if (!modal) return;
  
  activeHealthModalCategory = category;
  activeHealthModalRange = window.isMonthlyVillage ? "monthly" : "weekly";
  
  // Reset toggle buttons active state
  document.querySelectorAll("#vHealthModalTimeToggle .time-btn").forEach(btn => {
    btn.classList.remove("active");
  });
  const defaultBtn = document.querySelector(`#vHealthModalTimeToggle .time-btn[data-range="${activeHealthModalRange}"]`);
  if (defaultBtn) defaultBtn.classList.add("active");
  
  // Set subtitle/title
  const nameEl = document.getElementById("vpopNameTitle");
  const subEl = document.getElementById("vHealthModalSubtitle");
  if (subEl && nameEl) subEl.textContent = nameEl.textContent;
  
  const titleEl = document.getElementById("vHealthModalTitle");
  if (titleEl) {
    if (category === "overall") titleEl.textContent = "Village Health Score History";
    else if (category === "avg_rating") titleEl.textContent = "Average Repayment Rating History";
    else if (category === "stability") titleEl.textContent = "Stability Momentum History";
    else if (category === "default_rate") titleEl.textContent = "Portfolio Default Rate History";
    else if (category === "overdue_penalty") titleEl.textContent = "Overdue Concentration History";
    else if (category === "severe_risk_penalty") titleEl.textContent = "Severe Credit Risk History";
    else if (category === "collection_drop") titleEl.textContent = "Collection Drop History";
    else if (category === "customer_count_scale") titleEl.textContent = "Customer Count Scale History";
    else if (category === "portfolio_size_factor") titleEl.textContent = "Portfolio Size Factor History";
  }
  
  modal.classList.add("show");
  
  loadHealthHistoryAndRender();
}
window.openHealthModal = openHealthModal;

function closeHealthModal() {
  const modal = document.getElementById("villageHealthModal");
  if (modal) modal.classList.remove("show");
  if (vHealthHistoryChartInstance) {
    vHealthHistoryChartInstance.destroy();
    vHealthHistoryChartInstance = null;
  }
}
window.closeHealthModal = closeHealthModal;

function switchHealthModalRange(range) {
  activeHealthModalRange = range;
  
  document.querySelectorAll("#vHealthModalTimeToggle .time-btn").forEach(btn => {
    btn.classList.remove("active");
    if (btn.getAttribute("data-range") === range) {
      btn.classList.add("active");
    }
  });
  
  loadHealthHistoryAndRender();
}
window.switchHealthModalRange = switchHealthModalRange;

async function loadHealthHistoryAndRender() {
  const vid = window.activeVillageId;
  if (!vid) return;
  
  const currentView = localStorage.getItem("dashboardView") || "active";
  const localSubView = localStorage.getItem("villageCardSubView") || "active_only";
  
  try {
    const res = await fetch(`/api/village/health_history/${vid}?view=${currentView}&sub_view=${localSubView}&range=${activeHealthModalRange}&event_days=30`);
    const result = await res.json();
    if (!result.success) {
      console.error("Failed to load health history:", result.error);
      return;
    }
    
    renderHealthHistoryChart(result.history);
    renderHealthEventsTimeline(result.events);
  } catch (err) {
    console.error("Error loading health history:", err);
  }
}

function renderHealthHistoryChart(history) {
  const ctx = document.getElementById("vHealthHistoryChart");
  if (!ctx) return;
  
  if (vHealthHistoryChartInstance) {
    vHealthHistoryChartInstance.destroy();
  }
  
  const labels = history.map(pt => pt.date_label);
  
  // Set up colors and datasets
  const colorMap = {
    overall: { label: "Health Score", color: "#10b981", data: history.map(pt => pt.health_score), thickness: 3 },
    avg_rating: { label: "Avg Rating", color: "#3b82f6", data: history.map(pt => pt.metrics.avg_rating.value), thickness: 2 },
    stability: { label: "Stability Momentum", color: "#06b6d4", data: history.map(pt => pt.metrics.stability.value), thickness: 2 },
    default_rate: { label: "Portfolio Default Rate", color: "#ef4444", data: history.map(pt => pt.metrics.default_rate.value), thickness: 2 },
    overdue_penalty: { label: "Overdue %", color: "#f97316", data: history.map(pt => pt.metrics.overdue_penalty.value), thickness: 2 },
    severe_risk_penalty: { label: "High Risk %", color: "#8b5cf6", data: history.map(pt => pt.metrics.severe_risk_penalty.value), thickness: 2 },
    collection_drop: { label: "Collection Drop %", color: "#eab308", data: history.map(pt => pt.metrics.collection_drop.drop_pct), thickness: 2 },
    customer_count_scale: { label: "Active Customers", color: "#14b8a6", data: history.map(pt => pt.metrics.customer_count_scale.count), thickness: 2 },
    portfolio_size_factor: { label: "Active Loan Sum (Lakhs)", color: "#ec4899", data: history.map(pt => pt.metrics.portfolio_size_factor.loan_sum / 100000), thickness: 2 }
  };
  
  let datasets = [];
  
  if (activeHealthModalCategory === "overall") {
    // Show Health Score highlighted, and other core components by default
    datasets.push({
      label: "Health Score",
      data: colorMap.overall.data,
      borderColor: colorMap.overall.color,
      backgroundColor: "rgba(16, 185, 129, 0.05)",
      borderWidth: 4,
      tension: 0.3,
      pointRadius: 4,
      fill: true
    });
    
    // Add other metrics as thinner lines
    Object.keys(colorMap).forEach(k => {
      if (k !== "overall") {
        datasets.push({
          label: colorMap[k].label,
          data: colorMap[k].data,
          borderColor: colorMap[k].color,
          borderWidth: 1.5,
          tension: 0.3,
          pointRadius: 2,
          fill: false
        });
      }
    });
  } else {
    // Show Health Score muted, and selected metric highlighted
    datasets.push({
      label: "Health Score",
      data: colorMap.overall.data,
      borderColor: "rgba(16, 185, 129, 0.2)",
      borderWidth: 2,
      tension: 0.3,
      pointRadius: 2,
      fill: false
    });
    
    const sel = colorMap[activeHealthModalCategory];
    if (sel) {
      datasets.push({
        label: sel.label,
        data: sel.data,
        borderColor: sel.color,
        backgroundColor: "rgba(59, 130, 246, 0.05)",
        borderWidth: 4,
        tension: 0.3,
        pointRadius: 4,
        fill: true
      });
    }
  }
  
  const themeC = getChartThemeColors();
  vHealthHistoryChartInstance = new Chart(ctx, {
    type: "line",
    data: {
      labels: labels,
      datasets: datasets
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: {
          display: true,
          position: "top",
          labels: {
            color: themeC.legendColor,
            font: { size: 10, family: "Inter", weight: 600 }
          }
        },
        tooltip: {
          mode: "index",
          intersect: false,
          backgroundColor: themeC.tooltipBg,
          borderColor: themeC.tooltipBorder,
          borderWidth: 1,
          titleFont: { family: "Space Grotesk", size: 11, weight: 700 },
          bodyFont: { family: "Inter", size: 10 }
        }
      },
      scales: {
        x: {
          grid: { color: themeC.gridColor },
          ticks: { color: themeC.tickColor, font: { size: 10, family: "Inter" } }
        },
        y: {
          grid: { color: themeC.gridColor },
          ticks: { color: themeC.tickColor, font: { size: 10, family: "Inter" } }
        }
      }
    }
  });
}

function renderHealthEventsTimeline(events) {
  const timelineEl = document.getElementById("vHealthEventsTimeline");
  if (!timelineEl) return;
  
  timelineEl.innerHTML = "";
  if (!events || events.length === 0) {
    timelineEl.innerHTML = `
      <div style="padding: 15px; text-align: center; color: #94a3b8; font-size: 0.8rem;">
        🌱 No system events recorded in this time range.
      </div>
    `;
    return;
  }
  
  events.forEach(evt => {
    let icon = "🔧";
    let color = "#f1f5f9";
    let iconColor = "#64748b";
    
    if (evt.action === "submit_post_payment") {
      icon = "💰";
      color = "rgba(16, 185, 129, 0.1)";
      iconColor = "#10b981";
    } else if (evt.action === "close_customer_account") {
      icon = "🔒";
      color = "rgba(239, 68, 68, 0.1)";
      iconColor = "#ef4444";
    } else if (evt.action.includes("village")) {
      icon = "⚙️";
      color = "rgba(59, 130, 246, 0.1)";
      iconColor = "#3b82f6";
    }
    
    let desc = "";
    if (evt.action === "submit_post_payment" && evt.details) {
      desc = `Posted <strong>${evt.details.submitted_count}</strong> payment(s) successfully for this village.`;
    } else if (evt.action === "close_customer_account" && evt.details) {
      desc = `Closed account with status <strong>${evt.details.status}</strong>, paid amount ₹${parseFloat(evt.details.paid_amount || 0).toLocaleString()}.`;
    } else {
      desc = `${evt.action.replace(/_/g, " ")}: ${JSON.stringify(evt.details)}`;
    }
    
    const row = document.createElement("div");
    row.className = "timeline-event-item";
    
    row.innerHTML = `
      <div class="timeline-icon" style="background: ${color}; color: ${iconColor};">
        ${icon}
      </div>
      <div class="timeline-details">
        <span style="font-size: 0.775rem; color: #334155; line-height: 1.3;">${desc}</span>
        <span style="font-size: 0.675rem; color: #94a3b8; margin-top: 2px;">
          By <strong>${evt.username}</strong> &bull; ${evt.created_at}
        </span>
      </div>
    `;
    timelineEl.appendChild(row);
  });
}

function populatePostingAnalytics(data) {
  const section = document.getElementById("vpopPostingAnalyticsSection");
  if (!section) return;

  if (!data || data.empty) {
    section.style.display = "none";
    return;
  }
  section.style.display = "flex";

  // Cache skippers lists
  cachedConsecutiveSkippers = data.risk_alerts.consecutive_skippers_list || [];
  cachedFirstTimeSkippers = data.risk_alerts.first_time_skippers_list || [];

  // Card 1: Posting Lag
  const elapsedDays = data.recent_posting.elapsed_days;
  const elapsedDaysEl = document.getElementById("lblPostingElapsedDays");
  if (elapsedDaysEl) {
    elapsedDaysEl.textContent = elapsedDays;
  }
  const lastDateEl = document.getElementById("lblPostingLastDate");
  if (lastDateEl) {
    lastDateEl.textContent = `Last Posting: ${data.recent_posting.last_date || "N/A"}`;
  }
  const avgLagEl = document.getElementById("lblPostingAvgLag");
  if (avgLagEl) {
    avgLagEl.textContent = `${Math.round(data.recent_posting.avg_entry_lag_days)} days`;
  }
  
  const statusBadge = document.getElementById("badgePostingLagStatus");
  if (statusBadge) {
    const status = data.recent_posting.status || "active";
    statusBadge.textContent = status.toUpperCase();
    statusBadge.className = "status-badge";
    if (status === "active") {
      statusBadge.classList.add("status-active");
    } else if (status === "delayed") {
      statusBadge.classList.add("status-frozen"); // orange/yellow
    } else {
      statusBadge.classList.add("status-defaulted"); // red
    }
  }

  const isMonthly = !!data.is_monthly;

  // Card 2: Recent Collection
  const card2TitleEl = document.getElementById("lblPostingCard2Title");
  if (card2TitleEl) {
    card2TitleEl.textContent = isMonthly ? "Latest Month Collection" : "Latest Week Collection";
  }
  const stats = data.recent_week_stats;
  const amtCollectedEl = document.getElementById("lblPostingAmtCollected");
  if (amtCollectedEl) {
    amtCollectedEl.textContent = formatRupee(stats.collected_amount);
  }
  const amtExpectedEl = document.getElementById("lblPostingAmtExpected");
  if (amtExpectedEl) {
    amtExpectedEl.textContent = formatRupee(stats.expected_amount);
  }
  
  const collectionRate = stats.expected_amount > 0 ? (stats.collected_amount / stats.expected_amount * 100) : 0;
  const rateBar = document.getElementById("barPostingCollectionRate");
  if (rateBar) {
    rateBar.style.width = `${Math.min(100, collectionRate)}%`;
  }
  const ratePctEl = document.getElementById("lblPostingCollectionRatePct");
  if (ratePctEl) {
    ratePctEl.textContent = `${Math.round(collectionRate)}%`;
  }

  const compHistEl = document.getElementById("lblPostingAmountvsHist");
  if (compHistEl) {
    const val = data.comparisons.historical.amount_vs_avg_pct || 0;
    compHistEl.textContent = `${val >= 0 ? "+" : ""}${Math.round(val)}% vs hist`;
    compHistEl.style.color = val >= 0 ? "#10b981" : "#ef4444";
  }

  // Card 3: Skipping
  const skippingPctEl = document.getElementById("lblPostingSkippingPct");
  if (skippingPctEl) {
    skippingPctEl.textContent = `${Math.round(stats.skipping_pct)}%`;
  }
  const skippedCustEl = document.getElementById("lblPostingSkippedCustomers");
  if (skippedCustEl) {
    skippedCustEl.textContent = stats.skipped_count;
  }
  const unpaidAmtEl = document.getElementById("lblPostingAmtUnpaid");
  if (unpaidAmtEl) {
    unpaidAmtEl.textContent = formatRupee(stats.unpaid_amount);
  }
  const missedPeriodEl = document.getElementById("lblPostingMissedPeriod");
  if (missedPeriodEl) {
    missedPeriodEl.textContent = isMonthly ? "monthly" : "weekly";
  }

  const compPrevEl = document.getElementById("lblPostingSkippingvsPrev");
  if (compPrevEl) {
    const val = data.comparisons.previous_week.skipping_change_pct || 0;
    compPrevEl.textContent = `${val >= 0 ? "+" : ""}${Math.round(val)}% vs prev ${isMonthly ? "month" : "week"}`;
    compPrevEl.style.color = val <= 0 ? "#10b981" : "#ef4444";
  }

  const chartPeriodEl = document.getElementById("lblPostingChartPeriod");
  if (chartPeriodEl) {
    chartPeriodEl.textContent = isMonthly ? "Months" : "Weeks";
  }

  const consSkippersEl = document.getElementById("lblPostingConsecutiveSkippers");
  if (consSkippersEl) {
    consSkippersEl.textContent = data.risk_alerts.consecutive_skippers_count;
  }
  const firstTimeSkippersEl = document.getElementById("lblPostingFirstTimeSkippers");
  if (firstTimeSkippersEl) {
    firstTimeSkippersEl.textContent = data.risk_alerts.first_time_skippers_count;
  }

  // Render Chart
  renderPostingTrendChart(data.historical_trend);
}

function renderPostingTrendChart(trendData) {
  const ctx = document.getElementById("vpopPostingTrendChart");
  if (!ctx) return;

  if (postingTrendChartInstance) {
    postingTrendChartInstance.destroy();
  }

  const labels = trendData.map(d => d.date);
  const collectedAmounts = trendData.map(d => d.collected_amount);
  const expectedAmounts = trendData.map(d => d.expected_amount);
  const coveragePcts = trendData.map(d => d.coverage_pct);

  const themeColors = getChartThemeColors();

  postingTrendChartInstance = new Chart(ctx, {
    plugins: [{
      id: "postingTrendDatalabels",
      afterDatasetsDraw(chart) {
        const { ctx } = chart;
        ctx.save();
        chart.data.datasets.forEach((dataset, datasetIndex) => {
          if (dataset.label === "Collection Rate (%)") {
            const meta = chart.getDatasetMeta(datasetIndex);
            meta.data.forEach((bar, index) => {
              const value = dataset.data[index];
              if (value === null || value === undefined) return;
              const valString = Math.round(value) + "%";
              ctx.fillStyle = themeColors.tickColor;
              ctx.font = "bold 9px 'Inter', sans-serif";
              ctx.textAlign = "center";
              ctx.textBaseline = "bottom";
              const x = bar.x;
              const y = bar.y - 4;
              ctx.fillText(valString, x, y);
            });
          }
        });
        ctx.restore();
      }
    }],
    data: {
      labels: labels,
      datasets: [
        {
          type: "line",
          label: "Collected Amount",
          data: collectedAmounts,
          backgroundColor: "rgba(56, 189, 248, 0.05)",
          borderColor: "#38bdf8",
          borderWidth: 2.5,
          tension: 0.15,
          pointRadius: 3,
          pointBackgroundColor: "#38bdf8",
          yAxisID: "yAmount",
          order: 2
        },
        {
          type: "line",
          label: "Expected Installments",
          data: expectedAmounts,
          backgroundColor: "transparent",
          borderColor: "#94a3b8",
          borderWidth: 2,
          borderDash: [5, 5],
          tension: 0.1,
          pointRadius: 0,
          yAxisID: "yAmount",
          order: 3
        },
        {
          type: "bar",
          label: "Collection Rate (%)",
          data: coveragePcts,
          backgroundColor: "rgba(16, 185, 129, 0.25)",
          borderColor: "#10b981",
          borderWidth: 1.5,
          yAxisID: "yRate",
          order: 1
        }
      ]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: {
          display: true,
          position: "top",
          labels: {
            color: themeColors.legendColor,
            boxWidth: 10,
            font: { size: 9, family: "Inter" }
          }
        },
        tooltip: {
          mode: "index",
          intersect: false,
          backgroundColor: themeColors.tooltipBg,
          titleColor: themeColors.tooltipTitle,
          bodyColor: themeColors.tooltipBody,
          borderColor: themeColors.tooltipBorder,
          borderWidth: 1
        }
      },
      scales: {
        x: {
          grid: { color: themeColors.gridColor },
          ticks: { color: themeColors.tickColor, font: { size: 8 } }
        },
        yAmount: {
          type: "linear",
          position: "left",
          grid: { color: themeColors.gridColor },
          ticks: {
            color: themeColors.tickColor,
            font: { size: 8 },
            callback: function(value) {
              return "₹" + (value >= 1000 ? (value / 1000) + "k" : value);
            }
          },
          title: {
            display: true,
            text: "Collections (INR)",
            color: themeColors.tickColor,
            font: { size: 9, weight: "bold" }
          }
        },
        yRate: {
          type: "linear",
          position: "right",
          min: 0,
          max: 110,
          display: false,
          grid: { drawOnChartArea: false }
        }
      }
    }
  });
}

window.openPostingChartModal = function() {
  const modal = document.getElementById("postingChartModal");
  if (modal) {
    modal.classList.add("active");
    modal.style.display = "flex";
    if (postingTrendChartInstance) {
      setTimeout(() => {
        postingTrendChartInstance.resize();
        postingTrendChartInstance.update();
      }, 50);
    }
  }
};

window.closePostingChartModal = function() {
  const modal = document.getElementById("postingChartModal");
  if (modal) {
    modal.classList.remove("active");
    setTimeout(() => {
      modal.style.display = "none";
    }, 300);
  }
};

// Close chart modal if clicked outside
document.addEventListener("click", (e) => {
  const modal = document.getElementById("postingChartModal");
  if (modal && modal.classList.contains("active") && e.target === modal) {
    closePostingChartModal();
  }
});
