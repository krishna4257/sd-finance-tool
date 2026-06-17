// =====================================================
// GLOBAL SESSION EXPIRY HANDLER
// =====================================================
(function () {
  const originalFetch = window.fetch;

  window.fetch = async function (...args) {
    const response = await originalFetch(...args);

    try {
      const contentType = response.headers.get("content-type") || "";

      // Determine the original requested URL before any redirect
      const originalUrl =
        typeof args[0] === "string"
          ? args[0]
          : args[0] instanceof Request
          ? args[0].url
          : "";

      // TRUE only if this fetch was NOT already targeting /login and got redirected there
      const redirectedToLogin =
        response.redirected &&
        response.url.includes("/login") &&
        !originalUrl.includes("/login");

      let responseData = null;
      if (contentType.includes("application/json")) {
        try {
          responseData = await response.clone().json();
        } catch (_) {}
      }

      // Explicit 401 + session_expired flag from the backend (most reliable signal)
      const sessionExpired =
        response.status === 401 &&
        responseData &&
        responseData.session_expired === true;

      // HTML login page check: only fire if the original request was NOT to /login
      // AND it ended up serving the login page (i.e. a genuine auth redirect happened)
      const htmlLoginPage =
        !originalUrl.includes("/login") &&
        contentType.includes("text/html") &&
        response.url.includes("/login");

      if (redirectedToLogin || htmlLoginPage || sessionExpired) {

        // Prevent duplicate alerts
        if (!window.__sessionExpiredShown) {
          window.__sessionExpiredShown = true;

          alert("Session expired. Please login again.");

          window.location.href = "/login";
        }

        return Promise.reject(new Error("Session expired"));
      }

    } catch (err) {
      // Only log truly unexpected errors — not the "Session expired" rejection we throw above
      if (err.message !== "Session expired") {
        console.error("Session handling error:", err);
      }
    }

    return response;
  };
})();


// =====================================================
// CLIENT IDLE SESSION TIMER (Multi-Tab Safe via localStorage)
// =====================================================

const SESSION_TIMEOUT_MS = 30 * 60 * 1000; // 30 minutes
const WARNING_THRESHOLD_MS = 5 * 60 * 1000; // 5 minutes
const KEEPALIVE_THROTTLE_MS = 5 * 60 * 1000; // 5 minutes

let lastKeepAlivePing = Date.now();

async function pingKeepAlive() {
  try {
    const csrfTokenEl = document.querySelector('input[name="csrf_token"]') || document.querySelector('meta[name="csrf-token"]');
    const csrfToken = csrfTokenEl ? csrfTokenEl.value || csrfTokenEl.getAttribute('content') : '';
    
    const headers = {};
    if (csrfToken) {
      headers['X-CSRFToken'] = csrfToken;
    }
    
    await fetch('/api/session/keepalive', {
      method: 'POST',
      headers: headers
    });
    lastKeepAlivePing = Date.now();
  } catch (err) {
    console.error("Keep-alive ping failed:", err);
  }
}

function updateLastActivity() {
  const now = Date.now();
  localStorage.setItem("sd_last_activity", now.toString());
  
  const modal = document.getElementById("session-extension-modal");
  if (modal && modal.style.display === "flex") {
    modal.style.display = "none";
    modal.classList.remove("show");
  }
  
  if (now - lastKeepAlivePing > KEEPALIVE_THROTTLE_MS) {
    pingKeepAlive();
  }
}

// Initialize activity on load if not present
if (!localStorage.getItem("sd_last_activity")) {
  updateLastActivity();
}

[
  "click",
  "mousemove",
  "keydown",
  "scroll",
  "touchstart"
].forEach(event => {
  document.addEventListener(event, updateLastActivity, true);
});

setInterval(() => {
  const lastActivityStr = localStorage.getItem("sd_last_activity");
  const lastActivityTime = lastActivityStr ? parseInt(lastActivityStr, 10) : Date.now();
  const idleTime = Date.now() - lastActivityTime;
  const remainingTime = Math.max(0, SESSION_TIMEOUT_MS - idleTime);

  const clockElement = document.getElementById("session-timer-clock");
  const pillElement = document.getElementById("session-timer-pill");
  
  if (clockElement && pillElement) {
    pillElement.style.display = "flex";
    
    const hours = Math.floor(remainingTime / 3600000);
    const minutes = Math.floor((remainingTime % 3600000) / 60000);
    const seconds = Math.floor((remainingTime % 60000) / 1000);
    
    const formattedTime = 
      String(hours).padStart(2, '0') + ":" + 
      String(minutes).padStart(2, '0') + ":" + 
      String(seconds).padStart(2, '0');
      
    clockElement.textContent = formattedTime;
    
    if (remainingTime <= WARNING_THRESHOLD_MS) {
      clockElement.style.color = "#ef4444";
      pillElement.style.borderColor = "rgba(239, 68, 68, 0.35)";
    } else {
      clockElement.style.color = "";
      pillElement.style.borderColor = "";
    }
  }

  const modal = document.getElementById("session-extension-modal");
  const countdownText = document.getElementById("session-warning-countdown");
  
  if (remainingTime <= WARNING_THRESHOLD_MS && remainingTime > 0) {
    if (modal && modal.style.display !== "flex" && !window.__sessionExpiredShown) {
      modal.style.display = "flex";
      modal.classList.add("show");
    }
    
    if (countdownText) {
      const min = Math.floor(remainingTime / 60000);
      const sec = Math.floor((remainingTime % 60000) / 1000);
      countdownText.textContent = min + ":" + String(sec).padStart(2, '0');
    }
  } else if (remainingTime <= 0) {
    if (!window.__sessionExpiredShown) {
      window.__sessionExpiredShown = true;
      if (modal) {
        modal.style.display = "none";
        modal.classList.remove("show");
      }
      alert("Session expired. Please login again.");
      window.location.href = "/logout";
    }
  } else {
    if (modal && modal.style.display === "flex") {
      modal.style.display = "none";
      modal.classList.remove("show");
    }
  }
}, 1000);

// =====================================================
// GLOBAL STATE (DO NOT REMOVE – used across features)
// =====================================================
window.currentRow = null;
window.currentEmployeeTarget = null;
let isSyncingContext = false;
let lastSelectedEmployee = null;
let lastSelectedVillage = null;
let contextLocked = false; // NEW: prevents dropdown reset after Set
let isDashboardRefreshing = false;
let isContextReady = false;   
// =====================================================
// DOM READY
// =====================================================
document.addEventListener("DOMContentLoaded", () => {
  // Session extension modal button listeners
  const btnExtend = document.getElementById("btn-extend-session");
  const btnLogout = document.getElementById("btn-logout-session");
  const extModal = document.getElementById("session-extension-modal");

  if (btnExtend) {
    btnExtend.addEventListener("click", () => {
      pingKeepAlive();
      updateLastActivity();
      if (extModal) {
        extModal.style.display = "none";
        extModal.classList.remove("show");
      }
    });
  }

  if (btnLogout) {
    btnLogout.addEventListener("click", () => {
      window.location.href = "/logout";
    });
  }

  // ===================================================
  // SAFE TABLE INIT (does NOT touch business features)
  // ===================================================
  document.querySelectorAll("table").forEach(t => {
    if (t.id === "customerTable" || t.id === "userTable" || t.id === "popPaymentTable" || t.id === "feedPaymentTable" || t.classList.contains("no-datatable") || t.classList.contains("popup-mini-table")) return;
    if (!t.querySelector("thead")) return;
    if ($.fn.DataTable.isDataTable(t)) return;

    $(t).DataTable({
      paging: false,
      info: false,
      searching: false,
      ordering: true,
      responsive: true
    });
  });

  // ===================================================
  // ROW HIGHLIGHTING (GLOBAL) & KEYBOARD NAVIGATION
  // ===================================================
  document.body.addEventListener("click", e => {
    const row = e.target.closest("tbody tr");
    if (!row) return;

    // Ignore rows inside the Weekly Repayment Log only
    if (row.closest("#popWeeklyLogTable") || row.closest("#popWeeklyLogModal")) {
      return;
    }

    // Ignore if clicking on interactive form elements inside rows
    if (e.target.closest("input") || e.target.closest("button") || e.target.closest("a") || e.target.closest("span.delete-btn")) {
      return;
    }

    // Blur active inputs so keyboard navigation takes effect immediately on row click
    if (document.activeElement && (document.activeElement.tagName === "INPUT" || document.activeElement.tagName === "TEXTAREA")) {
      document.activeElement.blur();
    }

    if (window.currentRow) {
      window.currentRow.classList.remove("highlighted-row");
    }
    window.currentRow = row;
    row.classList.add("highlighted-row");
  });
  function scrollRowIntoView(row) {
    if (!row) return;
    const container = row.closest(".customer-table-wrapper, .scroll-table-container, .app-table-wrapper");
    if (container) {
      const containerRect = container.getBoundingClientRect();
      const rowRect = row.getBoundingClientRect();
      
      const rowTop = rowRect.top - containerRect.top + container.scrollTop;
      const rowBottom = rowTop + rowRect.height;
      
      const containerTop = container.scrollTop;
      const containerBottom = containerTop + container.clientHeight;
      
      const headerHeight = container.querySelector("thead")?.offsetHeight || 0;
      
      if (rowTop < containerTop + headerHeight) {
        container.scrollTop = rowTop - headerHeight;
      } else if (rowBottom > containerBottom) {
        container.scrollTop = rowBottom - container.clientHeight;
      }
    } else {
      row.scrollIntoView({ block: "nearest", behavior: "auto" });
    }
  }

  document.addEventListener("keydown", e => {
    if (e.key === "ArrowUp" || e.key === "ArrowDown") {
      const activeInput = document.activeElement;
      const isSearchBox = activeInput && activeInput.id === "searchBox";

      // Premium Shortcut: Pressing ArrowDown in the searchbox focuses the first table row
      if (isSearchBox && e.key === "ArrowDown") {
        const firstTable = document.querySelector("table");
        if (firstTable) {
          const visibleRows = Array.from(firstTable.querySelectorAll("tbody tr"))
            .filter(r => r.style.display !== "none" && !r.classList.contains("dataTables_empty"));
          
          if (visibleRows.length > 0) {
            e.preventDefault();
            activeInput.blur(); // blur search box
            
            if (window.currentRow) {
              window.currentRow.classList.remove("highlighted-row");
              window.currentRow.classList.remove("highlighted");
            }
            
            window.currentRow = visibleRows[0];
            window.currentRow.classList.add("highlighted-row");
            scrollRowIntoView(window.currentRow);
            return;
          }
        }
      }

      // Ignore normal inputs (except searchbox ArrowDown shortcut handled above)
      if (activeInput && !isSearchBox && (
          activeInput.tagName === "INPUT" || 
          activeInput.tagName === "TEXTAREA" || 
          activeInput.tagName === "SELECT" || 
          activeInput.getAttribute("contenteditable") === "true"
      )) {
          return;
      }

      // Ignore if user is currently focused on the search box but pressed other keys
      if (isSearchBox) {
          return;
      }

      if (!window.currentRow) return;

      // Prevent standard browser scrolling immediately to avoid competing scroll conflicts
      e.preventDefault();

      const currentTable = window.currentRow.closest("table");
      if (!currentTable) return;

      const rows = Array.from(currentTable.querySelectorAll("tbody tr"));
      // filter out hidden rows or empty rows
      const visibleRows = rows.filter(r => r.style.display !== "none" && !r.classList.contains("dataTables_empty"));
      if (visibleRows.length === 0) return;

      let currentIndex = visibleRows.indexOf(window.currentRow);
      let nextIndex = currentIndex;

      if (e.key === "ArrowUp") {
        nextIndex = currentIndex - 1;
      } else if (e.key === "ArrowDown") {
        nextIndex = currentIndex + 1;
      }

      if (nextIndex >= 0 && nextIndex < visibleRows.length) {
        window.currentRow.classList.remove("highlighted-row");
        window.currentRow.classList.remove("highlighted"); // safety rollback
        
        window.currentRow = visibleRows[nextIndex];
        window.currentRow.classList.add("highlighted-row");

        // Scroll the highlighted row into view instantly and snappily
        scrollRowIntoView(window.currentRow);
      }
    }
    
    // Trigger dblclick event when Enter key is pressed on a highlighted row
    if (e.key === "Enter") {
      if (window.currentRow) {
        const activeInput = document.activeElement;
        // Ignore if user is currently editing a field
        if (activeInput && (activeInput.tagName === "INPUT" || activeInput.tagName === "TEXTAREA" || activeInput.getAttribute("contenteditable") === "true")) {
          return;
        }
        
        e.preventDefault();
        
        // Trigger a double click mouse event on the second cell (index 1) of the highlighted row
        const target = window.currentRow.children[1] || window.currentRow;
        const dblClickEvent = new MouseEvent("dblclick", {
          bubbles: true,
          cancelable: true,
          view: window
        });
        target.dispatchEvent(dblClickEvent);
      }
    }
  });


  // Keyboard row navigation is handled by the primary keydown handler above
  // ===================================================
  // DASHBOARD CONTEXT DROPDOWNS (FIXED BI-DIRECTIONAL)
  // ===================================================
  const empSelect = document.getElementById("employeeSelect");
  const villageSelect = document.getElementById("villageSelect");
  const setBtn = document.getElementById("setContextBtn");

  if (empSelect && villageSelect && setBtn) {

    // -------- Load all employees on page load --------
    if (!contextLocked) {
     fetch("/api/employees")
      .then(r => r.json())
      .then(list => {
        empSelect.innerHTML = `<option value="">-- Employee --</option>`;
        list.forEach(e => {
          const o = document.createElement("option");
          o.value = e.eid;
          o.textContent = e.name;
          empSelect.appendChild(o);
        });
      });
     // Load ALL villages initially
     fetch("/api/villages")
      .then(r => r.json())
      .then(villages => {
        villageSelect.innerHTML = `<option value="">-- Village --</option>`;
        villages.forEach(v => {
          const o = document.createElement("option");
          o.value = v.vid;
          o.textContent = v.name;
          villageSelect.appendChild(o);
        });

        // Ensure dropdowns are NOT auto-cleared unless reset
        if (contextLocked && lastSelectedEmployee) {
          empSelect.value = lastSelectedEmployee;
        }
        if (contextLocked && lastSelectedVillage) {
          villageSelect.value = lastSelectedVillage;
        }
      });
    }

    // -------- Restore context from session --------
    fetch("/get_context")
      .then(r => r.json())
      .then(ctx => {
        if (!ctx.vid){
          isContextReady = false;
          return;
        } 

        isSyncingContext = true;
        contextLocked = true;
        isContextReady = false;
        empSelect.disabled = true;
        villageSelect.disabled = true;  
        lastSelectedVillage = ctx.vid;

        fetch(`/api/villages?eid=${ctx.eid}`)
          .then(r => r.json())
          .then(villages => {
            villageSelect.innerHTML = `<option value="">-- Village --</option>`;
            villages.forEach(v => {
              const o = new Option(v.name, v.vid);
              villageSelect.add(o);
            });

            villageSelect.value = ctx.vid;
            lastSelectedVillage = ctx.vid;
          })
          .finally(() => {
            setBtn.textContent = "Reset";
            setBtn.dataset.mode = "reset";
            isSyncingContext = false;
            isContextReady = true; 
          });
      });
    // -------- Employee → Villages --------
    empSelect.addEventListener("change", () => {
      if (isSyncingContext || contextLocked || isDashboardRefreshing) return;

      const eid = empSelect.value || null;
      lastSelectedEmployee = eid;
      if (!eid) return;

      isSyncingContext = true;

      fetch(`/api/villages?eid=${eid}`)
        .then(r => r.json())
        .then(villages => {
          const prevVillage = villageSelect.value;

          villageSelect.innerHTML = `<option value="">-- Village --</option>`;
          villages.forEach(v => {
            const o = document.createElement("option");
            o.value = v.vid;
            o.textContent = v.name;
            villageSelect.appendChild(o);
         });

      // 🔥 restore village if still valid
         if (villages.some(v => String(v.vid) === String(prevVillage))) {
           villageSelect.value = prevVillage;
         }
       })
       .finally(() => isSyncingContext = false);
    });

    // -------- Village → Employees --------
    villageSelect.addEventListener("change", () => {
      if (isSyncingContext || contextLocked || isDashboardRefreshing) return;

      const vid = villageSelect.value;
      lastSelectedVillage = vid;
      if (!vid) return;

      isSyncingContext = true;

      fetch(`/api/village/employees?vid=${vid}`)
        .then(r => r.json())
        .then(emps => {
          const prevEmployee = empSelect.value;

          empSelect.innerHTML = `<option value="">-- Employee --</option>`;
          emps.forEach(e => {
            const o = document.createElement("option");
            o.value = e.eid;
            o.textContent = e.name;
            empSelect.appendChild(o);
          });

          // 🔥 restore employee if still valid
          if (emps.some(e => String(e.eid) === String(prevEmployee))) {
            empSelect.value = prevEmployee;
          }
        })
        .finally(() => isSyncingContext = false);
    });

    // -------- Set/Reset Context --------
    setBtn.dataset.mode = "set";
    setBtn.addEventListener("click", async () => {

      // RESET MODE
      if (setBtn.dataset.mode === "reset") {
        await csrfFetch("/reset_context", { method: "POST" });

        contextLocked = false;
        lastSelectedEmployee = null;
        lastSelectedVillage = null;

        empSelect.disabled = false;
        villageSelect.disabled = false;

        empSelect.value = "";
        villageSelect.value = "";

        setBtn.textContent = "Set";
        setBtn.dataset.mode = "set";
        window.location.reload();
        return;
      }

      // SET MODE
      const eid = empSelect.value || null;
      const vid = villageSelect.value;

      if (!eid || !vid) {
        alert("Please select Village");
        return;
      }

      csrfFetch("/set_context", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({vid })
      })
      .then(() => {
        contextLocked = true;
        isContextReady = true; 
        lastSelectedEmployee = eid;
        lastSelectedVillage = vid;
        empSelect.disabled = true;
        villageSelect.disabled = true;
        setBtn.textContent = "Reset";
        setBtn.dataset.mode = "reset";

        window.location.reload();

      });
    });
  }

  // ===================================================
  // CREATE VILLAGE MODAL
  // ===================================================
  window.openCreateVillageModal = (preSelectEmp1, preSelectEmp2) => {
    document.getElementById("createVillageModal").style.display = "block";
    loadEmployeesForVillageModal(preSelectEmp1, preSelectEmp2);
  };

  window.closeCreateVillageModal = () => {
    document.getElementById("createVillageModal").style.display = "none";
  };

  // ===================================================
  // ADD EMPLOYEE MODAL
  // ===================================================
  window.openAddEmployeeModal = async target => {
    window.currentEmployeeTarget = target;

    document.getElementById("addEmployeeModal").style.display = "block";

    // Reset form fields
    empName.value = "";
    empPhone.value = "";
    empCity.value = "";
    empJoiningDate.value = "";
    empLevel.value = "";
    empState.value = "";

    // Load next employee ID
    try {
      const response = await fetch("/api/employee/next_eid");
      const data = await response.json();

      if (data.next_eid) {
        empId.value = data.next_eid;
      } else {
        empId.value = "AUTO";
      }
    } catch (err) {
      console.error("Failed to fetch next employee ID:", err);
      empId.value = "AUTO";
    }
  };

  window.closeAddEmployeeModal = () => {
    document.getElementById("addEmployeeModal").style.display = "none";

    // Clear modal fields
    empId.value = "";
    empName.value = "";
    empPhone.value = "";
    empCity.value = "";
    empJoiningDate.value = "";
    empLevel.value = "";
    empState.value = "";
  };

  window.submitAddEmployee = () => {
    const payload = {
      name: empName.value.trim().toUpperCase(),
      phone_number: empPhone.value.trim(),
      city: empCity.value.trim().toUpperCase(),
      joining_date: empJoiningDate.value,
      level: empLevel.value,
      state: empState.value.trim().toUpperCase()
    };

    if (!payload.name) return alert("Employee name required");

    csrfFetch("/api/create_employee", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload)
    })
    .then(r => r.json())
    .then(data => {
      if (!data.success) return alert(data.error);
      closeAddEmployeeModal();
      if (window.location.pathname.includes("/employee")) {
        window.location.reload();
        return;
      }
      loadEmployeesForVillageModal();

      const target =
        window.currentEmployeeTarget === "emp2"
          ? emp2Select
          : emp1Select;

      if (target) target.value = data.eid;
    });
  };

  // ===================================================
  // CREATE VILLAGE
  // ===================================================
  window.submitCreateVillage = () => {
    const payload = {
      village_code: villageCode.value.trim().toUpperCase(),
      village_name: villageName.value.trim().toUpperCase(),
      district: district.value.trim().toUpperCase(),
      pincode: pincode.value.trim(),
      state: state.value,
      emp1_eid: emp1Select.value,
      emp2_eid: emp2Select.value || null
    };

    if (!payload.village_code || !payload.village_name || !payload.emp1_eid) {
      alert("Missing required fields");
      return;
    }

        // ⚠️ Warn if only one employee selected
        // ⚠️ Confirm if only one employee selected
    if (payload.emp1_eid && !payload.emp2_eid) {

      const proceed = confirm(
        "Only one employee selected for this village.\n\n" +
        "Click OK to continue creating the village.\n" +
        "Click Cancel to select a second employee."
      );

      if (!proceed) {
        return;
      }
    }

    csrfFetch("/api/create_village", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload)
    })
    .then(r => r.json())
    .then(data => {
      if (!data.success) return alert(data.error);
      closeCreateVillageModal();
      refreshDashboard();
    });
  };

  // ===================================================
  // LOAD EMPLOYEES FOR MODAL
  // ===================================================
  window.loadEmployeesForVillageModal = (preSelectEmp1, preSelectEmp2) => {
    fetch("/api/employees")
      .then(r => r.json())
      .then(list => {
        emp1Select.innerHTML = `<option value="">-- Select Employee --</option>`;
        emp2Select.innerHTML = `<option value="">-- Optional --</option>`;
        list.forEach(e => {
          const o1 = new Option(e.name, e.eid);
          const o2 = new Option(e.name, e.eid);
          emp1Select.add(o1);
          emp2Select.add(o2);
        });
        if (preSelectEmp1) {
          emp1Select.value = preSelectEmp1;
        }
        if (preSelectEmp2) {
          emp2Select.value = preSelectEmp2 === "None" ? "" : preSelectEmp2;
        }
      });
  };

  // Pre-fetch notifications count on DOM ready if village is active
  if (window.activeVillageId) {
    fetchNotificationCounts(window.activeVillageId);
  }
});

document.addEventListener("DOMContentLoaded", function () {

    /* ---------------------------------------------------
        PREMIUM PROFILE DROPDOWN TOGGLE
    --------------------------------------------------- */
    const triggerBtn  = document.getElementById("userTriggerBtn");
    const profileMenu = document.getElementById("userDropdown");
    const wrapper     = document.getElementById("userProfileWrapper");

    if (!triggerBtn || !profileMenu) return;

    profileMenu.style.display = "none";

    triggerBtn.addEventListener("click", function (e) {
        e.stopPropagation();
        const isOpen = profileMenu.style.display === "block";
        profileMenu.style.display = isOpen ? "none" : "block";
        triggerBtn.setAttribute("aria-expanded", String(!isOpen));
    });

    document.addEventListener("click", function (e) {
        if (wrapper && !wrapper.contains(e.target)) {
            profileMenu.style.display = "none";
            triggerBtn.setAttribute("aria-expanded", "false");
        }
    });
});

// Theme toggle removed - light mode only

document.addEventListener('DOMContentLoaded', function () {
      const newPDT = document.getElementById('newPDT');

      if (newPDT) {
        newPDT.addEventListener('input', function(e) {
          let input = e.target.value.replace(/\D/g, '');

          if (input.length >= 3 && input.length <= 4) {
            input = input.slice(0,2) + '/' + input.slice(2);
          } else if (input.length > 4) {
            input = input.slice(0,2) + '/' + input.slice(2,4) + '/' + input.slice(4,8);
          }

          e.target.value = input;
        });

        window.initCustomCalendar(newPDT, {
          clickOpens: true
        });
      }
});
// =====================================================
// HELPERS
// =====================================================
function debounce(fn, delay) {
  let t;
  return (...args) => {
    clearTimeout(t);
    t = setTimeout(() => fn(...args), delay);
  };
}

// =====================================================
// GLOBAL PAGE LOADER & MOUSE GLOW TRACKING
// =====================================================
document.addEventListener("DOMContentLoaded", () => {
  // Hide page loader with a smooth transition once page is loaded
  const loader = document.getElementById("global-page-loader");
  if (loader) {
    setTimeout(() => {
      loader.classList.add("fade-out");
      setTimeout(() => {
        loader.style.display = "none";
      }, 450);
    }, 150);
  }

  // Intercept normal links to display loader before leaving page
  document.addEventListener("click", e => {
    const link = e.target.closest("a");
    if (link) {
      const href = link.getAttribute("href");
      const target = link.getAttribute("target");
      if (href && !href.startsWith("#") && !href.startsWith("javascript:") && !target && !e.ctrlKey && !e.metaKey) {
        if (loader) {
          loader.style.display = "flex";
          loader.offsetHeight; // Force reflow
          loader.classList.remove("fade-out");
        }
      }
    }
  });

  // Intercept form submissions to display loader
  document.addEventListener("submit", e => {
    if (e.defaultPrevented) return;
    const form = e.target.closest("form");
    if (form && !form.classList.contains("no-loader")) {
      if (loader) {
        loader.classList.remove("fade-out");
      }
    }
  });
});

// Mouse glow tracking removed for light mode design

// =====================================================
// NOTIFICATIONS DROPDOWN SYSTEM
// =====================================================
let cachedNotifications = {
  stress_alerts: [],
  events: []
};
let currentActiveNotifTab = 'intelligence';

function getNotificationId(item, type) {
  const vid = window.activeVillageId || 'global';
  if (type === 'intelligence') {
    const textKey = (item.type + "-" + item.message).replace(/[^a-zA-Z0-9]/g, '-');
    return `stress-${vid}-${textKey}`;
  } else {
    const timeKey = (item.action + "-" + (item.created_at || 'unknown')).replace(/[^a-zA-Z0-9]/g, '-');
    return `event-${vid}-${timeKey}`;
  }
}

async function fetchNotificationCounts(vid) {
  try {
    const [resAnalytics, resPosting] = await Promise.all([
      fetch(`/api/village/behavioral_analytics/${vid}`),
      fetch(`/api/dashboard/posting_analytics/${vid}`)
    ]);
    const dataAnalytics = await resAnalytics.json();
    const dataPosting = await resPosting.json();
    
    let alerts = [];
    if (dataAnalytics.success && dataAnalytics.stress_alerts) {
      alerts = [...dataAnalytics.stress_alerts];
    }
    const postingData = dataPosting.success ? (dataPosting.data || {}) : {};
    if (postingData.employee_breakdown) {
      postingData.employee_breakdown.forEach(emp => {
        const avgLag = parseFloat(emp.avg_lag_days || 0);
        if (avgLag > 0) {
          alerts.push({
            type: "Employee Performance Lag",
            message: `Employee ${emp.name || 'Unknown'} (EID: ${emp.eid}) has an average collection posting lag of ${avgLag.toFixed(1)} days.`,
            severity: avgLag > 14 ? "Critical" : (avgLag > 7 ? "High" : "Normal")
          });
        }
      });
    }
    cachedNotifications.stress_alerts = alerts;
    updateNotificationBadge();
  } catch (e) {
    console.error("Failed to pre-fetch notification counts:", e);
  }
}

function updateNotificationBadge() {
  const badge = document.getElementById("notificationBadge");
  if (!badge) return;
  
  let unreadStates = JSON.parse(localStorage.getItem('sd-notifications-unread') || '{}');
  let count = 0;
  
  cachedNotifications.stress_alerts.forEach(item => {
    const id = getNotificationId(item, 'intelligence');
    if (unreadStates[id] !== false) {
      count++;
    }
  });
  
  cachedNotifications.events.forEach(item => {
    const id = getNotificationId(item, 'event');
    if (unreadStates[id] !== false) {
      count++;
    }
  });

  if (count > 0) {
    badge.textContent = count;
    badge.style.display = "flex";
  } else {
    badge.style.display = "none";
  }
}

function toggleNotificationsDropdown(event) {
  if (event) {
    event.stopPropagation();
    event.preventDefault();
  }
  const dropdown = document.getElementById("notificationDropdown");
  if (!dropdown) return;
  
  const isShown = dropdown.classList.contains("show");
  
  // Close user profile dropdown if open
  const userDropdown = document.getElementById("userDropdown");
  if (userDropdown) userDropdown.classList.remove("show");
  
  if (!isShown) {
    dropdown.classList.add("show");
    document.addEventListener("click", closeNotificationsOnOutsideClick);
    
    // Load fresh data
    loadNotificationsContent();
  } else {
    dropdown.classList.remove("show");
    document.removeEventListener("click", closeNotificationsOnOutsideClick);
  }
}

function closeNotificationsOnOutsideClick(event) {
  const dropdown = document.getElementById("notificationDropdown");
  const wrapper = document.getElementById("notificationsWrapper");
  if (dropdown && !wrapper.contains(event.target)) {
    dropdown.classList.remove("show");
    document.removeEventListener("click", closeNotificationsOnOutsideClick);
  }
}

async function loadNotificationsContent() {
  const contentEl = document.getElementById("notificationsContent");
  if (!contentEl) return;
  
  const vid = window.activeVillageId;
  if (!vid) {
    contentEl.innerHTML = `
      <div class="notification-empty">
        <i class="fas fa-info-circle" style="font-size:1.5rem; color:#94a3b8; margin-bottom:8px; display:block;"></i>
        Please select a village to view behavioral intelligence and system events.
      </div>
    `;
    return;
  }
  
  // Show loading spinner
  contentEl.innerHTML = `
    <div class="notification-loading">
      <i class="fas fa-sync-alt" style="font-size:1.2rem; color:#1a4d2e;"></i>
      <span>Loading intelligence & system events...</span>
    </div>
  `;
  
  try {
    // Fetch behavioral analytics, health history, and posting analytics concurrently
    const [resAnalytics, resHistory, resPosting] = await Promise.all([
      fetch(`/api/village/behavioral_analytics/${vid}`),
      fetch(`/api/village/health_history/${vid}?view=active&sub_view=active_only&range=weekly&event_days=30`),
      fetch(`/api/dashboard/posting_analytics/${vid}`)
    ]);
    
    const dataAnalytics = await resAnalytics.json();
    const dataHistory = await resHistory.json();
    const dataPosting = await resPosting.json();
    
    let alerts = [];
    if (dataAnalytics.success && dataAnalytics.stress_alerts) {
      alerts = [...dataAnalytics.stress_alerts];
    }
    const postingData2 = dataPosting.success ? (dataPosting.data || {}) : {};
    if (postingData2.employee_breakdown) {
      postingData2.employee_breakdown.forEach(emp => {
        const avgLag = parseFloat(emp.avg_lag_days || 0);
        if (avgLag > 0) {
          alerts.push({
            type: "Employee Performance Lag",
            message: `Employee ${emp.name || 'Unknown'} (EID: ${emp.eid}) has an average collection posting lag of ${avgLag.toFixed(1)} days.`,
            severity: avgLag > 14 ? "Critical" : (avgLag > 7 ? "High" : "Normal")
          });
        }
      });
    }
    cachedNotifications.stress_alerts = alerts;

    if (dataHistory.success) {
      cachedNotifications.events = dataHistory.events || [];
    }
    
    // Mark all currently loaded alerts as read upon opening the dropdown
    let unreadStates = JSON.parse(localStorage.getItem('sd-notifications-unread') || '{}');
    cachedNotifications.stress_alerts.forEach(item => {
      const id = getNotificationId(item, 'intelligence');
      unreadStates[id] = false;
    });
    cachedNotifications.events.forEach(item => {
      const id = getNotificationId(item, 'event');
      unreadStates[id] = false;
    });
    localStorage.setItem('sd-notifications-unread', JSON.stringify(unreadStates));

    // Update badge count (will clear since all are set to read)
    updateNotificationBadge();
    
    // Render current active tab
    renderNotificationTabContent(currentActiveNotifTab);
    
  } catch (err) {
    console.error("Error loading notification details:", err);
    contentEl.innerHTML = `
      <div class="notification-empty" style="color: #ef4444;">
        <i class="fas fa-exclamation-triangle" style="font-size:1.5rem; margin-bottom:8px; display:block;"></i>
        Failed to load notifications. Please check connection.
      </div>
    `;
  }
}

function switchNotificationTab(tab) {
  currentActiveNotifTab = tab;
  
  // Update active tab button classes
  const btnIntel = document.getElementById("btnTabIntelligence");
  const btnEvt = document.getElementById("btnTabEvents");
  
  if (tab === 'intelligence') {
    if (btnIntel) btnIntel.classList.add("active");
    if (btnEvt) btnEvt.classList.remove("active");
  } else {
    if (btnIntel) btnIntel.classList.remove("active");
    if (btnEvt) btnEvt.classList.add("active");
  }
  
  renderNotificationTabContent(tab);
}

function toggleReadStatus(id, event) {
  if (event) {
    event.stopPropagation();
    event.preventDefault();
  }
  let unreadStates = JSON.parse(localStorage.getItem('sd-notifications-unread') || '{}');
  const currentVal = unreadStates[id] !== false; // Default is unread (true)
  unreadStates[id] = !currentVal;
  localStorage.setItem('sd-notifications-unread', JSON.stringify(unreadStates));
  
  updateNotificationBadge();
  renderNotificationTabContent(currentActiveNotifTab);
}

function renderNotificationTabContent(tab) {
  const contentEl = document.getElementById("notificationsContent");
  if (!contentEl) return;
  
  contentEl.innerHTML = "";
  let unreadStates = JSON.parse(localStorage.getItem('sd-notifications-unread') || '{}');
  
  if (tab === 'intelligence') {
    const alerts = cachedNotifications.stress_alerts;
    if (alerts.length === 0) {
      contentEl.innerHTML = `
        <div class="notification-empty">
          <i class="fas fa-check-circle" style="font-size:1.8rem; color:#10b981; margin-bottom:8px; display:block;"></i>
          <strong>All clear!</strong><br/>No intelligence anomalies or portfolio stress alerts detected.
        </div>
      `;
      return;
    }
    
    alerts.forEach(alertItem => {
      const severity = (alertItem.severity || 'normal').toLowerCase();
      let icon = "⚠️";
      if (alertItem.severity === "Critical") icon = "🚨";
      else if (alertItem.severity === "High") icon = "⚡";
      
      const id = getNotificationId(alertItem, 'intelligence');
      const isUnread = unreadStates[id] !== false;
      const dotClass = isUnread ? 'unread' : 'read';
      const dotTitle = isUnread ? 'Mark as Read' : 'Mark as Unread';
      
      const item = document.createElement("div");
      item.className = `intel-alert-item severity-${severity}`;
      item.style.display = "flex";
      item.style.alignItems = "center";
      item.style.width = "100%";
      item.style.boxSizing = "border-box";
      
      item.innerHTML = `
        <div class="intel-icon-wrapper" style="flex-shrink:0;">${icon}</div>
        <div class="intel-body" style="flex:1; margin-right:8px;">
          <span class="intel-title" style="font-weight: 700; display:block;">${alertItem.type}</span>
          <span class="intel-desc" style="font-size: 0.725rem; color: #475569; line-height: 1.3; display:block;">${alertItem.message}</span>
        </div>
        <span class="notif-status-dot ${dotClass}" onclick="toggleReadStatus('${id}', event)" title="${dotTitle}"></span>
      `;
      contentEl.appendChild(item);
    });
    
  } else {
    // Events Timeline Tab
    const events = cachedNotifications.events;
    if (events.length === 0) {
      contentEl.innerHTML = `
        <div class="notification-empty">
          <i class="fas fa-calendar-alt" style="font-size:1.8rem; color:#94a3b8; margin-bottom:8px; display:block;"></i>
          No system events recorded in this range.
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
      
      const id = getNotificationId(evt, 'event');
      const isUnread = unreadStates[id] !== false;
      const dotClass = isUnread ? 'unread' : 'read';
      const dotTitle = isUnread ? 'Mark as Read' : 'Mark as Unread';
      
      const row = document.createElement("div");
      row.className = "timeline-event-item";
      row.style.margin = "0";
      row.style.display = "flex";
      row.style.alignItems = "center";
      row.style.width = "100%";
      row.style.boxSizing = "border-box";
      
      row.innerHTML = `
        <div class="timeline-icon" style="background: ${color}; color: ${iconColor}; flex-shrink: 0;">
          ${icon}
        </div>
        <div class="timeline-details" style="flex: 1; margin-right: 8px;">
          <span style="font-size: 0.775rem; color: var(--text, #334155); line-height: 1.3;">${desc}</span>
          <span style="font-size: 0.675rem; color: #94a3b8; margin-top: 2px; display: block;">
            By <strong>${evt.username}</strong> &bull; ${evt.created_at}
          </span>
        </div>
        <span class="notif-status-dot ${dotClass}" onclick="toggleReadStatus('${id}', event)" title="${dotTitle}"></span>
      `;
      contentEl.appendChild(row);
    });
  }
}

// Bind functions to window context
window.fetchNotificationCounts = fetchNotificationCounts;
window.toggleNotificationsDropdown = toggleNotificationsDropdown;
window.switchNotificationTab = switchNotificationTab;
window.toggleReadStatus = toggleReadStatus;

// =====================================================
// THEME MANAGER — Dark / Light Mode Toggle
// =====================================================
window.ThemeManager = {
  toggle() {
    const current = document.documentElement.getAttribute('data-theme');
    const next = current === 'dark' ? 'light' : 'dark';
    document.documentElement.setAttribute('data-theme', next);
    localStorage.setItem('sd-theme', next);
    this.syncCheckbox(next);
  },
  syncCheckbox(theme) {
    const cb = document.getElementById('themeToggleCheckbox');
    if (cb) cb.checked = (theme === 'dark');
  },
  init() {
    const current = document.documentElement.getAttribute('data-theme') || 'light';
    this.syncCheckbox(current);

    const cb = document.getElementById('themeToggleCheckbox');
    if (cb) {
      cb.addEventListener('change', () => this.toggle());
    }
  }
};

document.addEventListener('DOMContentLoaded', () => {
  ThemeManager.init();
});
