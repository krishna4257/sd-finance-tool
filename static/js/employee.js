document.addEventListener("DOMContentLoaded", function () {

  const table = document.getElementById("employeeTable");
  const body = document.getElementById("employeeTableBody");
  const rows = Array.from(body.querySelectorAll("tr"));

  const snapshot = rows.map(row => ({
    row,
    text: row.innerText.toLowerCase()
  }));

  function updateSummary() {
    const visible = snapshot.filter(d => d.row.style.display !== "none");
    document.getElementById("totalCount").textContent = visible.length;
  }

  window.applySearch = function () {
    const term = document.getElementById("searchBox").value.toLowerCase();
    snapshot.forEach(d => {
      d.row.style.display = term === "" || d.text.includes(term) ? "" : "none";
    });
    updateSummary();
  };

  window.resetSearch = function () {
    document.getElementById("searchBox").value = "";
    snapshot.forEach(d => d.row.style.display = "");
    updateSummary();
  };

  window.toggleAll = function (source) {
    body.querySelectorAll("input[type='checkbox']")
        .forEach(cb => cb.checked = source.checked);
  };

  window.printSelected = function () {
    window.print();
  };

  /* COLUMN SELECTOR */

  const modal = document.getElementById("columnModal");
  const list = document.getElementById("columnCheckboxList");
  const openBtn = document.getElementById("tableViewBtn");
  const closeBtn = document.getElementById("closeColumnModal");

  openBtn.addEventListener("click", () => {

    list.innerHTML = "";

    table.querySelectorAll("thead th").forEach((th, index) => {
      if (index === 0) return;

      const wrapper = document.createElement("label");
      wrapper.className = "column-item";

      const checkbox = document.createElement("input");
      checkbox.type = "checkbox";
      checkbox.checked = true;

      checkbox.addEventListener("change", () => {
        toggleColumn(index, checkbox.checked);
      });

      wrapper.appendChild(checkbox);
      wrapper.appendChild(document.createTextNode(th.innerText));
      list.appendChild(wrapper);
    });

    modal.classList.remove("hidden");
  });

  closeBtn.addEventListener("click", () => {
    modal.classList.add("hidden");
  });

  function toggleColumn(index, show) {
    table.querySelectorAll("tr").forEach(row => {
      if (row.children[index])
        row.children[index].style.display = show ? "" : "none";
    });
  }

  updateSummary();

});

/* ===== EDIT + SAVE ===== */

function enableEdit(btn) {
  const row = btn.closest("tr");

  if (btn.innerText === "Edit") {

    row.querySelectorAll("td[data-field]").forEach(td => {
      if (td.dataset.field !== "eid") {
        td.contentEditable = true;
        td.classList.add("highlighted");
      }
    });

    btn.innerText = "Save";

  } else {

    const updatedData = {};
    row.querySelectorAll("td[data-field]").forEach(td => {
      updatedData[td.dataset.field] = td.innerText.trim();
      td.contentEditable = false;
      td.classList.remove("highlighted");
    });

    fetch("/api/update_employee", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(updatedData)
    })
    .then(res => res.json())
    .then(data => {
      if (data.success) {
        btn.innerText = "Edit";
      } else {
        alert("Update failed: " + data.error);
      }
    });
  }
}

/* ===== TOGGLE EMPLOYEE STATUS ===== */

function toggleEmployeeStatus(eid, btn) {

  fetch("/api/employee/toggle_status", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ eid })
  })
  .then(res => res.json())
  .then(data => {

    if (!data.success) {
      alert(data.error || "Failed");
      return;
    }

    const row = btn.closest("tr");

    const statusCell = row.querySelector(".status-cell");

    const isActive = data.status === "active";

    if (isActive) {
      statusCell.innerHTML = '<span class="status-badge active">Active</span>';
      btn.innerText = "Deactivate";
      btn.classList.remove("activate-btn");
      btn.classList.add("deactivate-btn");
    } else {
      statusCell.innerHTML = '<span class="status-badge inactive">Inactive</span>';
      btn.innerText = "Activate";
      btn.classList.remove("deactivate-btn");
      btn.classList.add("activate-btn");
    }

    // ✅ Ensure row becomes visible immediately after status change
    row.style.display = "";

    // ✅ Update snapshot text so search/filter works correctly after activation
    const snapshotItem = Array.from(document.querySelectorAll("#employeeTableBody tr"))
      .map(r => ({ row: r, text: r.innerText.toLowerCase() }))
      .find(d => d.row === row);

    if (snapshotItem) {
      snapshotItem.text = row.innerText.toLowerCase();
    }

    // 🔥 Refresh employee dropdown (hide inactive)
    if (typeof refreshEmployeeDropdown === "function") {
      refreshEmployeeDropdown();
    }

    // 🔥 If currently selected employee becomes inactive → reset context
    const employeeSelect = document.getElementById("employeeSelect");
    if (employeeSelect && employeeSelect.value == eid && !isActive) {
      fetch("/reset_context", { method: "POST" })
        .then(() => {
          employeeSelect.value = "";
        });
    }
  })
  .catch(err => {
    alert("Request failed: " + err.message);
  });
}

/* ===== REFRESH EMPLOYEE DROPDOWN ===== */

function refreshEmployeeDropdown() {
  const employeeSelect = document.getElementById("employeeSelect");

  if (!employeeSelect) return;

  fetch("/api/employees")  // backend must return ONLY active employees
    .then(res => res.json())
    .then(data => {
      employeeSelect.innerHTML = '<option value="">-- Select Employee --</option>';

      data.forEach(emp => {
        const opt = document.createElement("option");
        opt.value = emp.eid;
        opt.textContent = emp.name;
        employeeSelect.appendChild(opt);
      });
    })
    .catch(err => {
      console.error("Employee dropdown refresh failed:", err);
    });
}