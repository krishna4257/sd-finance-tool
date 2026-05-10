/**
 * landing.js — Landing page: employee search + village selection
 *
 * Behaviour:
 * - Loads all employees on page load.
 * - Persists the selected employee across refreshes via localStorage.
 * - Filters the employee list in real-time as the user types.
 * - Clicking an employee populates the village panel without a page reload.
 * - Clicking a village calls /set_context then redirects to /dashboard.
 * - The Restart button clears the stored employee, resets both panels.
 */

const STORAGE_KEY = "landing_selected_eid";

let allEmployees = [];   // cache from /api/employees
let selectedEid  = null;

// ----------------------------------------------------------------
// Boot
// ----------------------------------------------------------------
document.addEventListener("DOMContentLoaded", () => {
  loadEmployees();

  document.getElementById("empSearchInput")
    .addEventListener("input", debounce(filterEmployees, 200));

  document.getElementById("empRestartBtn")
    .addEventListener("click", restartEmployee);
});

// ----------------------------------------------------------------
// 1. Load employees from API
// ----------------------------------------------------------------
function loadEmployees() {
  fetch("/api/employees")
    .then(r => r.json())
    .then(list => {
      allEmployees = list;
      renderEmployeeList(list);

      // Restore previously selected employee from localStorage
      const savedEid = localStorage.getItem(STORAGE_KEY);
      if (savedEid) {
        const match = list.find(e => String(e.eid) === String(savedEid));
        if (match) {
          selectEmployee(match.eid, match.name, /* skipPersist */ true);
        }
      }
    })
    .catch(() => {
      document.getElementById("empList").innerHTML =
        '<div class="landing-empty landing-error">Failed to load employees.</div>';
    });
}

// ----------------------------------------------------------------
// 2. Render employee cards
// ----------------------------------------------------------------
function renderEmployeeList(list) {
  const container = document.getElementById("empList");

  if (!list.length) {
    container.innerHTML = '<div class="landing-empty">No employees found.</div>';
    return;
  }

  container.innerHTML = list.map(e => `
    <div
      class="landing-item emp-item ${String(e.eid) === String(selectedEid) ? 'landing-item--active' : ''}"
      data-eid="${e.eid}"
      data-name="${e.name}"
      onclick="selectEmployee(${e.eid}, '${escHtml(e.name)}')"
    >
      <span class="landing-item-icon">👤</span>
      <span class="landing-item-label">${escHtml(e.name)}</span>
      ${String(e.eid) === String(selectedEid)
        ? '<span class="landing-item-badge">Selected</span>'
        : ''}
    </div>
  `).join("");
}

// ----------------------------------------------------------------
// 3. Real-time filter
// ----------------------------------------------------------------
function filterEmployees() {
  const q = document.getElementById("empSearchInput").value.trim().toLowerCase();
  const filtered = q
    ? allEmployees.filter(e => e.name.toLowerCase().includes(q))
    : allEmployees;
  renderEmployeeList(filtered);
}

// ----------------------------------------------------------------
// 4. Select an employee → load their villages
// ----------------------------------------------------------------
function selectEmployee(eid, name, skipPersist = false) {
  selectedEid = eid;

  if (!skipPersist) {
    localStorage.setItem(STORAGE_KEY, String(eid));
  }

  // Re-render employees so the active highlight refreshes
  renderEmployeeList(
    document.getElementById("empSearchInput").value.trim()
      ? allEmployees.filter(e =>
          e.name.toLowerCase().includes(
            document.getElementById("empSearchInput").value.trim().toLowerCase()
          ))
      : allEmployees
  );

  loadVillages(eid);
}

// ----------------------------------------------------------------
// 5. Load villages for selected employee
// ----------------------------------------------------------------
function loadVillages(eid) {
  const container = document.getElementById("villageList");
  container.innerHTML = '<div class="landing-empty">Loading villages…</div>';

  fetch(`/api/villages?eid=${eid}`)
    .then(r => r.json())
    .then(list => {
      if (!list.length) {
        container.innerHTML = '<div class="landing-empty">No villages assigned to this employee.</div>';
        return;
      }

      container.innerHTML = list.map(v => `
        <div
          class="landing-item village-item"
          data-vid="${v.vid}"
          onclick="enterVillage(${v.vid})"
        >
          <span class="landing-item-icon">🏘️</span>
          <span class="landing-item-label">${escHtml(v.name)}</span>
          <span class="landing-item-arrow">→</span>
        </div>
      `).join("");
    })
    .catch(() => {
      container.innerHTML =
        '<div class="landing-empty landing-error">Failed to load villages.</div>';
    });
}

// ----------------------------------------------------------------
// 6. Click village → set context → go to dashboard
// ----------------------------------------------------------------
function enterVillage(vid) {
  // Optimistic visual feedback
  document.querySelectorAll(".village-item").forEach(el => {
    if (Number(el.dataset.vid) === Number(vid)) {
      el.classList.add("landing-item--entering");
      el.innerHTML += ' <span class="landing-entering-label">Entering…</span>';
    }
  });

  csrfFetch("/set_context", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ vid })
  })
  .then(r => r.json())
  .then(data => {
    if (data.success) {
      window.location.href = "/dashboard";
    } else {
      alert("Could not enter village: " + (data.error || "Unknown error"));
      // Remove entering state
      document.querySelectorAll(".landing-item--entering").forEach(el => {
        el.classList.remove("landing-item--entering");
        const lbl = el.querySelector(".landing-entering-label");
        if (lbl) lbl.remove();
      });
    }
  })
  .catch(() => {
    alert("Network error. Please try again.");
  });
}

// ----------------------------------------------------------------
// 7. Restart — clear stored employee, reset both panels
// ----------------------------------------------------------------
function restartEmployee() {
  localStorage.removeItem(STORAGE_KEY);
  selectedEid = null;

  document.getElementById("empSearchInput").value = "";
  renderEmployeeList(allEmployees);

  document.getElementById("villageList").innerHTML = `
    <div class="landing-empty" id="villageEmptyMsg">
      ← Select an employee to see their villages
    </div>`;
}

// ----------------------------------------------------------------
// Utility
// ----------------------------------------------------------------
function escHtml(str) {
  return String(str)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#39;");
}

function debounce(fn, delay) {
  let t;
  return (...args) => {
    clearTimeout(t);
    t = setTimeout(() => fn(...args), delay);
  };
}
