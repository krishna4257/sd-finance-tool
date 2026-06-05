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
  // ROW HIGHLIGHTING (GLOBAL)
  // ===================================================
  document.body.addEventListener("click", e => {
    const row = e.target.closest("tr");
    if (!row) return;
    if (window.currentRow) {
      window.currentRow.classList.remove("highlighted-row");
    }
    window.currentRow = row;
    row.classList.add("highlighted-row");
  });


  // ===================================================
// KEYBOARD ROW NAVIGATION (GLOBAL)
// ===================================================
document.addEventListener("keydown", (e) => {

  // Don't interfere while typing
  const tag = document.activeElement?.tagName;

  if (
    tag === "INPUT" ||
    tag === "TEXTAREA" ||
    tag === "SELECT" ||
    document.activeElement?.isContentEditable
  ) {
    return;
  }

  if (!window.currentRow) return;

  if (e.key !== "ArrowDown" && e.key !== "ArrowUp") {
    return;
  }

  e.preventDefault();

  const tbody = window.currentRow.closest("tbody");
  if (!tbody) return;

  const visibleRows = Array.from(
    tbody.querySelectorAll("tr")
  ).filter(row =>
    row.offsetParent !== null &&
    row.style.display !== "none"
  );

  let index = visibleRows.indexOf(window.currentRow);

  if (index === -1) return;

  if (e.key === "ArrowDown" && index < visibleRows.length - 1) {
    index++;
  }

  if (e.key === "ArrowUp" && index > 0) {
    index--;
  }

  window.currentRow.classList.remove("highlighted-row");

  window.currentRow = visibleRows[index];

  window.currentRow.classList.add("highlighted-row");

  window.currentRow.scrollIntoView({
    block: "nearest",
    behavior: "smooth"
  });
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

document.addEventListener('DOMContentLoaded', () => {
      const themeToggle = document.getElementById('theme-toggle');
      
      // 1. Set the toggle switch to the correct state on page load
      const currentTheme = localStorage.getItem('theme') || 'dark';
      if (currentTheme === 'dark') {
        themeToggle.checked = true;
      }

      // 2. Add a listener to change the theme when the toggle is clicked
      themeToggle.addEventListener('change', () => {
        const selectedTheme = themeToggle.checked ? 'dark' : 'light';
        document.documentElement.setAttribute('data-theme', selectedTheme);
        localStorage.setItem('theme', selectedTheme);
      });
});

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
