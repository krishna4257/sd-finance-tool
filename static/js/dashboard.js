document.addEventListener("DOMContentLoaded", function () {
  const vid = window.activeVillageId;
  if (vid) {
    loadDashboardData(vid);
  }
});

let activeVillageChart = null;
let cachedTransitions = {};
let cachedAttention = {};

async function loadDashboardData(vid) {
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

  try {
    const res = await fetch(`/api/village/behavioral_analytics/${vid}`);
    const result = await res.json();

    if (refreshBtn) refreshBtn.classList.remove("spinning");

    if (!result.success) {
      alert("Failed to load village behavioral analytics: " + (result.error || "Unknown error"));
      return;
    }

    const data = result.data;
    if (data.empty) {
      loadingEl.style.display = "none";
      emptyEl.style.display = "flex";
      return;
    }

    // Populate Headers
    const nameEl = document.getElementById("vpopNameTitle");
    const codeEl = document.getElementById("vpopCodeTitle");
    if (nameEl) nameEl.textContent = data.village_name;
    if (codeEl) codeEl.textContent = data.village_code;

    // 1. Render Health Score & Status
    const scoreEl = document.getElementById("vpopHealthScore");
    const statusBadge = document.getElementById("vpopHealthStatus");
    const riskEl = document.getElementById("vpopPredictedRisk");
    const trendEl = document.getElementById("vpopWeeklyTrend");

    if (scoreEl) {
      scoreEl.textContent = data.health.score;
      // Change color based on score
      if (data.health.score >= 80) scoreEl.style.color = "#10b981";
      else if (data.health.score >= 70) scoreEl.style.color = "#38bdf8";
      else if (data.health.score >= 55) scoreEl.style.color = "#fbbf24";
      else scoreEl.style.color = "#ef4444";
    }

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

    // 2. Render Chart.js Trend Graph
    renderTrendGraph(data.health_trend);

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

    // Cache transitions data for lazy rendering
    cachedTransitions = data.transitions;

    // Populate transition counts
    Object.keys(data.transitions).forEach(key => {
      const countEl = document.getElementById(`vMoveCount_${key}`);
      if (countEl) {
        countEl.textContent = data.transitions[key].length;
      }
      // Reset expanded list
      const wrapper = document.getElementById(`vMoveListContainer_${key}`);
      if (wrapper) {
        wrapper.style.display = "none";
        wrapper.innerHTML = "";
      }
    });

    // 4. Render Stress & Trend Alerts
    const stressContainer = document.getElementById("vpopStressContainer");
    if (stressContainer) {
      stressContainer.innerHTML = "";
      if (data.stress_alerts.length === 0) {
        stressContainer.innerHTML = `
          <div style="padding: 24px; text-align: center; color: #64748b; font-size: 0.85rem;">
            🌱 No portfolio stress markers detected currently.
          </div>
        `;
      } else {
        data.stress_alerts.forEach(alertItem => {
          const sevClass = `stress-${alertItem.severity.toLowerCase()}`;
          const alertCard = document.createElement("div");
          alertCard.className = `v-stress-card ${sevClass}`;
          
          let icon = "⚠️";
          if (alertItem.severity === "Critical") icon = "🚨";
          else if (alertItem.severity === "High") icon = "⚡";
          
          alertCard.innerHTML = `
            <span style="font-size: 1.25rem;">${icon}</span>
            <div style="display: flex; flex-direction: column; gap: 3px;">
              <span style="font-size: 0.825rem; font-weight: 700; color: #fff;">${alertItem.type}</span>
              <span style="font-size: 0.775rem; color: #cbd5e1; line-height: 1.3;">${alertItem.message}</span>
            </div>
          `;
          stressContainer.appendChild(alertCard);
        });
      }
    }

    // 5. Render Critical Attention Engine
    cachedAttention = data.critical_attention;
    const attentionContainer = document.getElementById("vpopAttentionContainer");
    if (attentionContainer) {
      attentionContainer.innerHTML = "";
      
      const attentionKeys = ["Missed4Plus", "RapidCollapse", "SevereOverdue", "RatingBelow40"];
      attentionKeys.forEach(key => {
        const group = data.critical_attention[key];
        const groupCard = document.createElement("div");
        groupCard.style.display = "flex";
        groupCard.style.flexDirection = "column";
        groupCard.style.gap = "8px";

        const urgencyClass = group.urgency.toLowerCase();
        
        groupCard.innerHTML = `
          <div class="v-attention-header ${urgencyClass}" onclick="toggleAttentionList('${key}')">
            <div style="display: flex; align-items: center; gap: 12px;">
              <span style="font-size: 1.1rem;">${urgencyClass === 'critical' ? '🔴' : '🟠'}</span>
              <span style="font-size: 0.85rem; font-weight: 700; color: #cbd5e1;">${group.label}</span>
            </div>
            <div style="display: flex; align-items: center; gap: 10px;">
              <span style="font-size: 0.7rem; font-weight: 700; text-transform: uppercase; padding: 2px 8px; border-radius: 6px; background: rgba(255,255,255,0.05); color: #94a3b8;">${group.urgency}</span>
              <span class="badge-count" style="font-weight: 800; background: ${urgencyClass === 'critical' ? 'rgba(239, 68, 68, 0.2)' : 'rgba(249, 115, 22, 0.2)'}; color: ${urgencyClass === 'critical' ? '#ef4444' : '#f97316'};">${group.count}</span>
            </div>
          </div>
          <div id="vAttentionListContainer_${key}" class="v-drilldown-wrapper" style="display: none;"></div>
        `;
        attentionContainer.appendChild(groupCard);
      });
    }

    // Show content
    loadingEl.style.display = "none";
    contentEl.style.display = "flex";

  } catch (err) {
    console.error("Dashboard render failed:", err);
    if (refreshBtn) refreshBtn.classList.remove("spinning");
    loadingEl.style.display = "none";
    alert("Connection error occurred while retrieving intelligence. Please try again.");
  }
}

function refreshDashboardData() {
  const vid = window.activeVillageId;
  if (vid) {
    loadDashboardData(vid);
  }
}

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
            color: "#94a3b8",
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
          backgroundColor: "rgba(15, 23, 42, 0.95)",
          titleColor: "#94a3b8",
          bodyColor: "#f8fafc",
          borderColor: "rgba(255,255,255,0.08)",
          borderWidth: 1,
          textDirection: "ltr"
        }
      },
      scales: {
        x: {
          grid: {
            color: "rgba(255,255,255,0.03)",
            borderColor: "rgba(255,255,255,0.05)"
          },
          ticks: {
            color: "#94a3b8",
            font: {
              size: 9
            }
          }
        },
        y: {
          min: 0,
          max: 100,
          grid: {
            color: "rgba(255,255,255,0.03)",
            borderColor: "rgba(255,255,255,0.05)"
          },
          ticks: {
            color: "#94a3b8",
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

function toggleMovementList(key) {
  const container = document.getElementById(`vMoveListContainer_${key}`);
  if (!container) return;

  if (container.style.display === "block") {
    container.style.display = "none";
    container.innerHTML = "";
    return;
  }

  // Close all other movement lists first
  Object.keys(cachedTransitions).forEach(k => {
    if (k !== key) {
      const other = document.getElementById(`vMoveListContainer_${k}`);
      if (other) {
        other.style.display = "none";
        other.innerHTML = "";
      }
    }
  });

  const list = cachedTransitions[key] || [];
  if (list.length === 0) {
    container.innerHTML = `<div style="padding: 12px; text-align: center; color: #64748b; font-size: 0.8rem;">No transitions in this category.</div>`;
    container.style.display = "block";
    return;
  }

  // Build Table
  let html = `
    <table class="v-drilldown-table">
      <thead>
        <tr>
          <th>A.No</th>
          <th>Name</th>
          <th>Loan</th>
          <th>Paid</th>
          <th>Bal</th>
          <th>Rating</th>
          <th>Last Paid</th>
          <th>Missed</th>
          <th>Status</th>
        </tr>
      </thead>
      <tbody>
  `;

  list.forEach(c => {
    let badgeClass = "risk-badge-excellent";
    if (c.rating < 40) badgeClass = "risk-badge-critical";
    else if (c.rating < 60) badgeClass = "risk-badge-risky";
    else if (c.rating < 80) badgeClass = "risk-badge-good";

    const loanVal = formatRupee(c.total_amount);
    const paidVal = formatRupee(c.paid_amount);
    const balVal = formatRupee(c.balance_amount);

    html += `
      <tr class="clickable-row" onclick="window.openCustomerPopup('${c.ano}')">
        <td style="font-weight: 700; color: #00f2fe;">${c.ano}</td>
        <td style="text-align: left; font-weight: 600;">${c.name}</td>
        <td>${loanVal}</td>
        <td>${paidVal}</td>
        <td style="color: #ef4444; font-weight: 600;">${balVal}</td>
        <td><span class="status-badge ${badgeClass}" style="font-size: 0.65rem; font-weight:800; padding: 1px 6px;">${c.rating}</span></td>
        <td>${c.last_payment_date}</td>
        <td style="color: ${c.missed_cycles > 0 ? '#ef4444' : '#64748b'}; font-weight: 700;">${c.missed_cycles}</td>
        <td><span class="status-badge status-${c.status === 'OnTrack' ? 'active' : (c.status === 'Overdue' ? 'defaulted' : 'closed')}" style="font-size: 0.65rem; font-weight:700; padding: 1px 6px;">${c.status}</span></td>
      </tr>
    `;
  });

  html += `</tbody></table>`;
  container.innerHTML = html;
  container.style.display = "block";
}

function toggleAttentionList(key) {
  const container = document.getElementById(`vAttentionListContainer_${key}`);
  if (!container) return;

  if (container.style.display === "block") {
    container.style.display = "none";
    container.innerHTML = "";
    return;
  }

  // Close all other attention lists first
  Object.keys(cachedAttention).forEach(k => {
    if (k !== key) {
      const other = document.getElementById(`vAttentionListContainer_${k}`);
      if (other) {
        other.style.display = "none";
        other.innerHTML = "";
      }
    }
  });

  const group = cachedAttention[key] || { list: [] };
  const list = group.list;
  if (list.length === 0) {
    container.innerHTML = `<div style="padding: 12px; text-align: center; color: #64748b; font-size: 0.8rem;">No cases requiring attention in this category.</div>`;
    container.style.display = "block";
    return;
  }

  // Build Table
  let html = `
    <table class="v-drilldown-table">
      <thead>
        <tr>
          <th>A.No</th>
          <th>Name</th>
          <th>Bal</th>
          <th>Rating</th>
          <th>Missed Cycles</th>
          <th>Status</th>
        </tr>
      </thead>
      <tbody>
  `;

  list.forEach(c => {
    let badgeClass = "risk-badge-excellent";
    if (c.rating < 40) badgeClass = "risk-badge-critical";
    else if (c.rating < 60) badgeClass = "risk-badge-risky";
    else if (c.rating < 80) badgeClass = "risk-badge-good";

    const balVal = formatRupee(c.balance_amount);

    html += `
      <tr class="clickable-row" onclick="window.openCustomerPopup('${c.ano}')">
        <td style="font-weight: 700; color: #00f2fe;">${c.ano}</td>
        <td style="text-align: left; font-weight: 600;">${c.name}</td>
        <td style="color: #ef4444; font-weight: 600;">${balVal}</td>
        <td><span class="status-badge ${badgeClass}" style="font-size: 0.65rem; font-weight:800; padding: 1px 6px;">${c.rating}</span></td>
        <td style="color: ${c.missed_cycles > 0 ? '#ef4444' : '#64748b'}; font-weight: 700;">${c.missed_cycles}</td>
        <td><span class="status-badge status-${c.status === 'OnTrack' ? 'active' : (c.status === 'Overdue' ? 'defaulted' : 'closed')}" style="font-size: 0.65rem; font-weight:700; padding: 1px 6px;">${c.status}</span></td>
      </tr>
    `;
  });

  html += `</tbody></table>`;
  container.innerHTML = html;
  container.style.display = "block";
}

function formatRupee(num) {
  if (num === null || num === undefined) return "₹0";
  const val = parseFloat(num);
  return "₹" + val.toLocaleString('en-IN', { maximumFractionDigits: 0 });
}
