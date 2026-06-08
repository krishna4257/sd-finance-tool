// =====================================================
// GLOBAL SESSION EXPIRY HANDLER
// =====================================================
(function () {
  const originalFetch = window.fetch;

  window.fetch = async function (...args) {
    const response = await originalFetch(...args);

    try {
      const contentType = response.headers.get("content-type") || "";
      const redirectedToLogin = response.redirected &&
        response.url.includes("/login");

      const unauthorized = response.status === 401;

      const htmlLoginPage =
        contentType.includes("text/html") &&
        response.url.includes("/login");

      if (redirectedToLogin || unauthorized || htmlLoginPage) {

        // Prevent duplicate alerts
        if (!window.__sessionExpiredShown) {
          window.__sessionExpiredShown = true;

          alert("Session expired. Please login again.");

          window.location.href = "/login";
        }

        return Promise.reject(new Error("Session expired"));
      }

    } catch (err) {
      console.error("Session handling error:", err);
    }

    return response;
  };
})();

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

  // ===================================================
  // SAFE TABLE INIT (does NOT touch business features)
  // ===================================================
  document.querySelectorAll("table").forEach(t => {
    if (t.id === "popPaymentTable" || t.classList.contains("no-datatable") || t.classList.contains("popup-mini-table")) return;
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
  window.openCreateVillageModal = () => {
    document.getElementById("createVillageModal").style.display = "block";
    loadEmployeesForVillageModal();
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
  window.loadEmployeesForVillageModal = () => {
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
      });
  };
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

        flatpickr('#newPDT', {
          dateFormat: 'd/m/Y',
          allowInput: true,
          clickOpens: true,
          wrap: false
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
