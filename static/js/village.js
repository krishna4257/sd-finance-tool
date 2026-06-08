document.addEventListener("DOMContentLoaded", function () {

  const table = document.getElementById("villageTable");
  const body = document.getElementById("villageTableBody");
  const rows = Array.from(body.querySelectorAll("tr"));

  const snapshot = rows.map(row => ({
    row,
    text: row.innerText.toLowerCase()
  }));

  /* ===== TILE VIEW ===== */
  const tableViewContainer = document.getElementById("tableViewContainer");
  const tileViewContainer = document.getElementById("tileViewContainer");
  const employeeTilesContainer = document.getElementById("employeeTilesContainer");
  const mapViewContainer = document.getElementById("mapViewContainer");
  const tileEmployeePairCount = document.getElementById("tileEmployeePairCount");
  let currentView = "table";

  function updateSummary() {
    const visible = snapshot.filter(d => d.row.style.display !== "none");
    document.getElementById("totalCount").textContent = visible.length;
  }

  window.applySearch = function () {
    const term = document.getElementById("searchBox").value.toLowerCase();

    if (currentView === "table") {
      snapshot.forEach(d => {
        d.row.style.display = term === "" || d.text.includes(term) ? "" : "none";
      });
      updateSummary();
    } else {
      document.querySelectorAll(".employee-tile").forEach(tile => {
        const txt = tile.innerText.toLowerCase();
        tile.style.display = term === "" || txt.includes(term) ? "" : "none";
      });
    }
  };

  window.resetSearch = function () {
    document.getElementById("searchBox").value = "";
    snapshot.forEach(d => d.row.style.display = "");

    document.querySelectorAll(".employee-tile").forEach(tile => {
      tile.style.display = "";
    });

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
  const openBtn = document.getElementById("columnSelectorBtn");
  const closeBtn = document.getElementById("closeColumnModal");

  openBtn.addEventListener("click", () => {

    list.innerHTML = "";

    table.querySelectorAll("thead th").forEach((th, index) => {
      if (index === 0) return; // skip checkbox

      const wrapper = document.createElement("label");
      wrapper.className = "column-item";

      const checkbox = document.createElement("input");
      checkbox.type = "checkbox";
      // Determine column name for default visibility
      const columnName = th.innerText
        .trim()
        .toLowerCase()
        .replace(/\s+/g, "_");

      checkbox.checked = !DEFAULT_HIDDEN_COLUMNS.includes(columnName);

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

  // ===== DEFAULT HIDDEN COLUMNS =====
  const DEFAULT_HIDDEN_COLUMNS = [
    "vid",
    "emp1",
    "emp2",
    "created_at",
    "status"
  ];

  function applyDefaultColumnVisibility() {
    const headers = Array.from(table.querySelectorAll("thead th"));

    headers.forEach((th, index) => {
      const columnName = th.innerText
        .trim()
        .toLowerCase()
        .replace(/\s+/g, "_");

      if (DEFAULT_HIDDEN_COLUMNS.includes(columnName)) {
        toggleColumn(index, false);
      }
    });
  }

  function buildTileView() {
    if (!window.villageData || !employeeTilesContainer) return;

    const grouped = {};

    window.villageData.forEach(v => {
      const key = `${v.emp1 || "None"}-${v.emp2 || "None"}`;

      if (!grouped[key]) {
        grouped[key] = {
          emp1: v.emp1 || "None",
          emp2: v.emp2 || "None",
          emp1_name: v.emp1_name || `Employee ${v.emp1 || "None"}`,
          emp2_name: v.emp2_name || (v.emp2_name ? v.emp2_name : (v.emp2 ? `Employee ${v.emp2}` : "Unassigned")),
          villages: []
        };
      }

      grouped[key].villages.push(v);
    });

    employeeTilesContainer.innerHTML = "";

    Object.values(grouped).forEach(group => {
      const tile = document.createElement("div");
      tile.dataset.emp1 = group.emp1;
      tile.dataset.emp2 = group.emp2;
      tile.className = "employee-tile";

    tile.innerHTML = `
      <div class="employee-tile-header">
        <div class="employee-name-row">

  <span
      class="employee-chip draggable-employee editable-employee"
      draggable="true"
      data-slot="emp1"
      data-eid="${group.emp1}"
      data-name="${group.emp1_name}"
      data-pair-emp1="${group.emp1}"
      data-pair-emp2="${group.emp2}">
      ${group.emp1_name}
  </span>

  <span class="employee-separator">+</span>

  ${
    group.emp2 && group.emp2 !== "None"
    ? `
    <span
        class="employee-chip draggable-employee editable-employee"
        draggable="true"
        data-slot="emp2"
        data-eid="${group.emp2}"
        data-name="${group.emp2_name}"
        data-pair-emp1="${group.emp1}"
        data-pair-emp2="${group.emp2}">
        ${group.emp2_name}
    </span>
    `
    : `
    <span
        class="employee-empty-slot"
        data-slot="emp2"
        data-emp1="${group.emp1}"
        data-emp2="${group.emp2}">
        + Add Employee
    </span>
    `
  }

</div>
        <div class="employee-pair-subtitle">
            IDs: ${group.emp1} + ${group.emp2}
        </div>
        <div class="employee-pair-count">
            🏘️ ${group.villages.length} Villages
        </div>
      </div>
      <div class="employee-tile-body">
        ${group.villages.map(v => `
<span
  class="village-chip draggable-village"
  draggable="true"
  data-vid="${v.vid}"
  data-village-code="${v.village_code}"
  data-village-name="${v.village_name}"
  data-emp1="${group.emp1}"
  data-emp2="${group.emp2}">
  ${v.village_name}
</span>
`).join("")}
      </div>
    `;

      employeeTilesContainer.appendChild(tile);
      enableTileDrop(tile);
    });

    if (tileEmployeePairCount) {
      tileEmployeePairCount.textContent = Object.keys(grouped).length;
    }

    initializeEmptySlotAssignment();
    initializeEmployeeTrashZone();
    initializeVillageDragging();
    initializeEmployeeDragging();
    initializeEmployeeEditing();
  }

  function enableTileDrop(tile) {

    tile.addEventListener("dragover", (e) => {
      e.preventDefault();
      tile.classList.add("drag-target");
    });

    tile.addEventListener("dragleave", () => {
      tile.classList.remove("drag-target");
    });

    tile.addEventListener("drop", async (e) => {
      e.preventDefault();
      tile.classList.remove("drag-target");

      const employeeRaw = e.dataTransfer.getData("employee");

      if (employeeRaw) {

        const employee = JSON.parse(employeeRaw);

        const targetEmp1 = tile.dataset.emp1;
        const targetEmp2 = tile.dataset.emp2;
        const normalizedTargetEmp2 = (
          !targetEmp2 || targetEmp2 === "None"
        ) ? null : targetEmp2;

        if (targetEmp2 && targetEmp2 !== "None") {
          alert("Target tile already has 2 employees.");
          return;
        }

        const newEmp1 = targetEmp1;
        const newEmp2 = employee.eid;

        if (!confirm(`Assign ${employee.employee_name} to employee pair ${newEmp1} + ${newEmp2}?`)) {
          return;
        }

        try {

          const response = await csrfFetch("/api/village/update_employee_pair", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
              old_emp1: employee.pair_emp1,
              old_emp2: employee.pair_emp2 === "None" ? null : employee.pair_emp2,
              new_emp1: employee.pair_emp1,
              new_emp2: null
            })
          });

          const result = await response.json();

          if (!result.success) {
            alert(result.error);
            return;
          }

          const response2 = await csrfFetch("/api/village/update_employee_pair", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
              old_emp1: targetEmp1,
              old_emp2: normalizedTargetEmp2,
              new_emp1: targetEmp1,
              new_emp2: employee.eid
            })
          });

          const result2 = await response2.json();

          if (!result2.success) {
            alert(result2.error);
            return;
          }

          location.reload();

        } catch (err) {
          alert(err.message);
        }

        return;
      }

      const raw = e.dataTransfer.getData("application/json");
      if (!raw) return;

      const village = JSON.parse(raw);

      const newEmp1 = tile.dataset.emp1;
      const newEmp2 = tile.dataset.emp2;

      if (
        String(village.emp1) === String(newEmp1) &&
        String(village.emp2) === String(newEmp2)
      ) {
        return;
      }

      if (!confirm(
        `Move ${village.village_name} to employee pair ${newEmp1} + ${newEmp2}?`
      )) {
        return;
      }

      try {

        const response = await csrfFetch("/api/update_village", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            vid: village.vid,
            village_code: village.village_code,
            village_name: village.village_name,
            emp1: newEmp1,
            emp2: newEmp2,
            new_name: village.village_name
          })
        });

        const result = await response.json();

        if (!result.success) {
          alert(result.error || "Failed to move village");
          return;
        }

        const record = window.villageData.find(
          x => String(x.vid) === String(village.vid)
        );

        if (record) {
          record.emp1 = newEmp1;
          record.emp2 = newEmp2;
        }

        buildTileView();

      } catch (err) {
        alert("Move failed: " + err.message);
      }
    });
  }

  function initializeVillageDragging() {

    document.querySelectorAll(".draggable-village").forEach(chip => {

      chip.addEventListener("dragstart", (e) => {
        e.dataTransfer.setData(
          "application/json",
          JSON.stringify({
            vid: chip.dataset.vid,
            village_code: chip.dataset.villageCode,
            village_name: chip.dataset.villageName,
            emp1: chip.dataset.emp1,
            emp2: chip.dataset.emp2
          })
        );
      });

    });
  }

  function initializeEmployeeDragging() {

    document.querySelectorAll(".draggable-employee").forEach(chip => {

      chip.addEventListener("dragstart", (e) => {

        e.stopPropagation();

        e.dataTransfer.setData(
          "employee",
          JSON.stringify({
            eid: chip.dataset.eid,
            slot: chip.dataset.slot,
            pair_emp1: chip.dataset.pairEmp1,
            pair_emp2: chip.dataset.pairEmp2,
            employee_name: chip.dataset.name
          })
        );

      });

    });
  }

  function initializeEmployeeEditing() {
    document.querySelectorAll(".editable-employee").forEach(chip => {
      chip.addEventListener("dblclick", async () => {
        try {
          const response = await fetch("/api/employees");
          const employees = await response.json();

          const options = employees
            .map(emp => `
              <option value="${emp.eid}">
                ${emp.eid} - ${emp.name}
              </option>
            `)
            .join("");

          const currentSlot = chip.dataset.slot;

          const overlay = document.createElement("div");
          overlay.id = "employeeReplaceOverlay";

          overlay.innerHTML = `
            <div style="position:fixed;inset:0;background:rgba(0,0,0,.6);z-index:10000;display:flex;align-items:center;justify-content:center;">
              <div style="width:520px;max-width:90vw;background:#1f1f1f;border:1px solid rgba(212,175,55,.35);border-radius:14px;padding:18px;">
                <h3 style="margin-bottom:12px;color:#d4af37;">Replace Employee</h3>
                <select id="employeeReplaceSelect" style="width:100%;padding:10px;">
                  <option value="">Select Employee</option>
                  ${options}
                </select>
                <div style="margin-top:14px;display:flex;justify-content:flex-end;gap:10px;">
                  <button id="employeeReplaceCancel">Cancel</button>
                  <button id="employeeReplaceSave">Save</button>
                </div>
              </div>
            </div>
          `;

          document.body.appendChild(overlay);

          document.getElementById("employeeReplaceCancel").onclick = () => overlay.remove();

          document.getElementById("employeeReplaceSave").onclick = async () => {

            const selectedEmployee = document.getElementById("employeeReplaceSelect").value;

            if (!selectedEmployee) {
              alert("Please select employee");
              return;
            }

            const payload = {
              old_emp1: chip.dataset.pairEmp1,
              old_emp2: chip.dataset.pairEmp2 === "None" ? null : chip.dataset.pairEmp2,
              new_emp1: currentSlot === "emp1" ? selectedEmployee : chip.dataset.pairEmp1,
              new_emp2: currentSlot === "emp2"
                ? selectedEmployee
                : (chip.dataset.pairEmp2 === "None" ? null : chip.dataset.pairEmp2)
            };

            const saveResponse = await csrfFetch("/api/village/update_employee_pair", {
              method: "POST",
              headers: { "Content-Type": "application/json" },
              body: JSON.stringify(payload)
            });

            const result = await saveResponse.json();

            if (!result.success) {
              alert(result.error || "Update failed");
              return;
            }

            location.reload();
          };

        } catch (err) {
          alert(err.message);
        }

      });
    });
  }

  function initializeEmptySlotAssignment() {

    document.querySelectorAll('.employee-empty-slot').forEach(slot => {

      slot.addEventListener('click', async () => {

        try {

          const empResponse = await fetch('/api/employees');
          const employees = await empResponse.json();

          const options = employees
            .map(emp => `<option value="${emp.eid}">${emp.eid} - ${emp.name}</option>`)
            .join('');

          const selectedHtml = `
            <div id="employeeAssignOverlay" style="
              position:fixed;
              inset:0;
              background:rgba(0,0,0,.6);
              z-index:10000;
              display:flex;
              align-items:center;
              justify-content:center;">

              <div style="
                width:520px;
                max-width:90vw;
                background:#1f1f1f;
                border:1px solid rgba(212,175,55,.35);
                border-radius:14px;
                padding:18px;">

                <h3 style="margin:0 0 12px 0;color:#d4af37;">Assign Employee</h3>

                <select id="employeeAssignSelect" style="width:100%;padding:10px;">
                  <option value="">Select Employee</option>
                  ${options}
                </select>

                <div style="display:flex;justify-content:flex-end;gap:10px;margin-top:14px;">
                  <button id="employeeAssignCancel">Cancel</button>
                  <button id="employeeAssignSave">Assign</button>
                </div>
              </div>
            </div>
          `;

          document.body.insertAdjacentHTML('beforeend', selectedHtml);

          const overlay = document.getElementById('employeeAssignOverlay');

          document.getElementById('employeeAssignCancel').onclick = () => {
            overlay.remove();
          };

          document.getElementById('employeeAssignSave').onclick = async () => {

            const employeeId = document.getElementById('employeeAssignSelect').value;

            if (!employeeId) {
              alert('Please select employee');
              return;
            }

            const emp1 = slot.dataset.emp1;

            try {

              const response = await csrfFetch('/api/village/update_employee_pair', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                  old_emp1: emp1,
                  old_emp2: null,
                  new_emp1: emp1,
                  new_emp2: employeeId
                })
              });

              const result = await response.json();

              if (!result.success) {
                alert(result.error || 'Assignment failed');
                return;
              }

              location.reload();

            } catch (err) {
              alert(err.message);
            }
          };

        } catch (err) {
          alert(err.message);
        }

      });

    });
  }

  function initializeEmployeeTrashZone() {

    let trash = document.getElementById('employeeTrashZone');

    if (!trash) {
      trash = document.createElement('div');
      trash.id = 'employeeTrashZone';
      trash.innerHTML = '🗑 Remove Employee';

      trash.style.position = 'fixed';
      trash.style.right = '25px';
      trash.style.bottom = '25px';
      trash.style.zIndex = '9999';
      trash.style.padding = '14px 18px';
      trash.style.borderRadius = '12px';
      trash.style.border = '1px dashed #d4af37';
      trash.style.background = 'rgba(0,0,0,.75)';
      trash.style.color = '#d4af37';
      trash.style.display = 'none';

      document.body.appendChild(trash);
    }

    // Always sync visibility with current view
    trash.style.display = (currentView === 'tile') ? 'block' : 'none';

    trash.addEventListener('dragover', e => {
      e.preventDefault();
    });

    trash.addEventListener('drop', async e => {

      e.preventDefault();

      const raw = e.dataTransfer.getData('employee');
      if (!raw) return;

      const employee = JSON.parse(raw);

      if (employee.slot !== 'emp2') {
        alert('Only secondary employee can be removed');
        return;
      }

      try {

        const response = await csrfFetch('/api/village/update_employee_pair', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            old_emp1: employee.pair_emp1,
            old_emp2: employee.pair_emp2 === 'None' ? null : employee.pair_emp2,
            new_emp1: employee.pair_emp1,
            new_emp2: null
          })
        });

        const result = await response.json();

        if (!result.success) {
          alert(result.error || 'Remove failed');
          return;
        }

        location.reload();

      } catch (err) {
        alert(err.message);
      }
    });
  }

  function switchVillageView(mode) {

    currentView = mode;

    if (tableViewContainer) {
      tableViewContainer.style.display = mode === "table" ? "" : "none";
    }

    if (tileViewContainer) {
      tileViewContainer.style.display = mode === "tile" ? "" : "none";
    }

    if (mapViewContainer) {
      mapViewContainer.style.display = mode === "map" ? "" : "none";
    }

    const trashZone = document.getElementById('employeeTrashZone');
    if (trashZone) {
      trashZone.style.display = mode === 'tile' ? 'block' : 'none';
    }

    const tableBtn = document.getElementById("tableViewBtn");
    const tileBtn = document.getElementById("tileViewBtn");
    const mapBtn = document.getElementById("mapViewBtn");

    if (tableBtn) tableBtn.classList.toggle("active", mode === "table");
    if (tileBtn) tileBtn.classList.toggle("active", mode === "tile");
    if (mapBtn) mapBtn.classList.toggle("active", mode === "map");
  }

  updateSummary();

  const dt = $.fn.DataTable.isDataTable('#villageTable')
    ? $('#villageTable').DataTable()
    : $('#villageTable').DataTable({
        paging: false,
        info: false,
        searching: false,
        ordering: true
      });

  applyDefaultColumnVisibility();

  buildTileView();
  switchVillageView("table");

  const trashZoneInit = document.getElementById('employeeTrashZone');
  if (trashZoneInit) {
      trashZoneInit.style.display = 'none';
  }

  const tableBtn = document.getElementById("tableViewBtn");
  const tileBtn = document.getElementById("tileViewBtn");

  if (tableBtn) {
    tableBtn.addEventListener("click", () => {
      switchVillageView("table");
      tableBtn.classList.add("active");
      tileBtn.classList.remove("active");
      window.applySearch();
    });
  }

  if (tileBtn) {
    tileBtn.addEventListener("click", () => {
      switchVillageView("tile");
      tileBtn.classList.add("active");
      tableBtn.classList.remove("active");
      window.applySearch();
    });
  }

  const mapBtn = document.getElementById("mapViewBtn");

  if (mapBtn) {
    mapBtn.addEventListener("click", () => {
      switchVillageView("map");
      window.applySearch();
    });
  }

  dt.on('draw', () => {
    updateSummary();
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

  // ⚠️ Warn if only one employee is assigned
  if (emp1 && !emp2) {
    alert("Only one employee selected for this village.");
  }

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

window.openVillageDashboard = function (vid) {
  csrfFetch("/set_context", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ vid })
  })
  .then(res => res.json())
  .then(data => {
    if (data.success) {
      window.location.href = "/dashboard";
    } else {
      alert("Failed to set village context: " + (data.error || "Unknown error"));
    }
  })
  .catch(err => {
    alert("Connection error: " + err.message);
  });
};