document.addEventListener("DOMContentLoaded", function () {

  const table = document.getElementById("villageTable");
  const body = document.getElementById("villageTableBody");
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

  /* ===== COLUMN SELECTOR (same logic as customers page) ===== */

  const modal = document.getElementById("columnModal");
  const list = document.getElementById("columnCheckboxList");
  const openBtn = document.getElementById("tableViewBtn");
  const closeBtn = document.getElementById("closeColumnModal");

  openBtn.addEventListener("click", () => {

    list.innerHTML = "";

    table.querySelectorAll("thead th").forEach((th, index) => {
      if (index === 0) return; // skip checkbox

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

  // === Sorting support (match customers page behavior) ===
  function sortTable(colIndex) {
    if (!window.sortState) window.sortState = {};
    if (!window.sortState[colIndex]) window.sortState[colIndex] = 0;
    window.sortState[colIndex]++;

    let visible = snapshot.filter(d => d.row.style.display !== "none");

    const getCell = (row, i) => (row.children[i]?.textContent || "").trim();

    if (window.sortState[colIndex] % 3 === 1) {
      visible.sort((a, b) =>
        getCell(a.row, colIndex).localeCompare(getCell(b.row, colIndex), undefined, { numeric: true })
      );
    } else if (window.sortState[colIndex] % 3 === 2) {
      visible.sort((a, b) =>
        getCell(b.row, colIndex).localeCompare(getCell(a.row, colIndex), undefined, { numeric: true })
      );
    } else {
      visible = [...snapshot].filter(d => d.row.style.display !== "none");
    }

    body.innerHTML = "";
    visible.forEach(d => body.appendChild(d.row));
    updateSummary();
  }

  table.querySelectorAll("thead th").forEach((th, i) => {
    if (i === 0) return; // skip checkbox
    th.style.cursor = "pointer";
    th.addEventListener("click", () => sortTable(i));
  });
});

/* ===== ENABLE EDIT ===== */

function openEditModal(btn) {
  const row = btn.closest("tr");
  window.currentEditRow = row;
  const cells = row.querySelectorAll("td[data-field]");

  let data = {};

  cells.forEach(cell => {
    data[cell.dataset.field] = cell.innerText.trim();
  });

  document.getElementById("edit_vid").value = data.vid || "";
  document.getElementById("edit_village_code").value = data.village_code || "";
  document.getElementById("edit_village_name").value = data.village_name || "";

  loadEmployees(data.emp1, data.emp2);

  document.getElementById("editVillageModal").classList.remove("hidden");
}

function closeEditModal() {
  document.getElementById("editVillageModal").classList.add("hidden");
}

function loadEmployees(selectedEmp1, selectedEmp2) {
  fetch("/api/employees")
    .then(res => res.json())
    .then(data => {
      const emp1 = document.getElementById("edit_emp1");
      const emp2 = document.getElementById("edit_emp2");

      emp1.innerHTML = "";
      emp2.innerHTML = "";

      data.forEach(emp => {
        const opt1 = new Option(`${emp.eid} - ${emp.name}`, emp.eid);
        const opt2 = new Option(`${emp.eid} - ${emp.name}`, emp.eid);

        if (emp.eid == selectedEmp1) opt1.selected = true;
        if (emp.eid == selectedEmp2) opt2.selected = true;

        emp1.add(opt1);
        emp2.add(opt2);
      });
    });
}

function saveVillageEdit() {
  const vid = document.getElementById("edit_vid").value;
  const village_code = document.getElementById("edit_village_code").value;
  const village_name = document.getElementById("edit_village_name").value;
  const emp1 = document.getElementById("edit_emp1").value;
  const emp2 = document.getElementById("edit_emp2").value;

  fetch(`/api/village/check?code=${village_code}&name=${village_name}&vid=${vid}`)
  .then(res => res.json())
  .then(check => {
    if (check.exists) {
      alert("Village already exists!");
      return;
    }

    csrfFetch("/api/update_village", {
      method: "POST",
      headers: {"Content-Type": "application/json"},
      body: JSON.stringify({
        vid,
        village_code,
        village_name,
        emp1,
        emp2,
        new_name: village_name
      })
    })
    .then(res => res.json())
    .then(resp => {
      if (resp.success) {
        const row = window.currentEditRow;

        if (row) {
            // update table cells live
            row.querySelector("td[data-field='village_code']").innerText = village_code;
            row.querySelector("td[data-field='village_name']").innerText = village_name;
            row.querySelector("td[data-field='emp1']").innerText = emp1;
            row.querySelector("td[data-field='emp2']").innerText = emp2;
        }

        closeEditModal();
      } else {
        alert(resp.error);
      }
    });
  });
}


/* ===== TOGGLE VILLAGE STATUS ===== */

function toggleVillageStatus(vid, btn) {

  if (!confirm("Are you sure you want to change village status?")) return;

  const originalText = btn.innerText;
  btn.disabled = true;
  btn.innerText = "Processing...";

  csrfFetch("/api/village/toggle_status", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ vid })
  })
  .then(res => res.json())
  .then(data => {
    if (data.success) {

      // Update button text + style
      if (data.status === "inactive") {
        btn.innerText = "Activate";
        btn.classList.remove("danger-btn");
      } else {
        btn.innerText = "Inactivate";
        btn.classList.add("danger-btn");
      }

      const row = btn.closest("tr");

      // 🔹 Update status badge text + class
      const statusCell = row.querySelector(".status-badge");

      if (statusCell) {
        statusCell.innerText =
          data.status.charAt(0).toUpperCase() + data.status.slice(1);

        statusCell.classList.remove("status-active", "status-inactive");
        statusCell.classList.add("status-" + data.status);
      }

      // 🔹 Update row styling
      if (data.status === "inactive") {
        row.classList.add("inactive-row");
      } else {
        row.classList.remove("inactive-row");
      }

      // 🔥 Refresh village dropdown after status change
      if (typeof refreshVillageDropdown === "function") {
        refreshVillageDropdown();
      }

      // 🔥 If current selected village becomes inactive → reset context
      const villageSelect = document.getElementById("villageSelect");
      if (villageSelect && villageSelect.value == vid && data.status === "inactive") {
        csrfFetch("/reset_context", { method: "POST" })
          .then(() => {
            villageSelect.value = "";
          });
      }

    } else {
      alert("Failed: " + data.error);
      btn.innerText = originalText;
    }
  })
  .catch(err => {
    alert("Request failed: " + err.message);
    btn.innerText = originalText;
  })
  .finally(() => {
    btn.disabled = false;
  });
}

/* ===== REFRESH VILLAGE DROPDOWN ===== */

function refreshVillageDropdown() {
  const employeeSelect = document.getElementById("employeeSelect");
  const villageSelect = document.getElementById("villageSelect");

  if (!villageSelect) return;

  const eid = employeeSelect ? employeeSelect.value : "";

  fetch(`/api/villages?eid=${eid || ""}`)
    .then(res => res.json())
    .then(data => {
      villageSelect.innerHTML = '<option value="">-- Select Village --</option>';

      data.forEach(v => {
        const opt = document.createElement("option");
        opt.value = v.vid;
        opt.textContent = v.name;
        villageSelect.appendChild(opt);
      });
    })
    .catch(err => {
      console.error("Dropdown refresh failed:", err);
    });
}