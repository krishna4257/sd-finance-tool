document.addEventListener("DOMContentLoaded", async function () {

  const table = document.getElementById("villageTable");
  const body = document.getElementById("villageTableBody");
  let rows = Array.from(body.querySelectorAll("tr"));

  let snapshot = rows.map(row => ({
    row,
    text: row.innerText.toLowerCase()
  }));

  let dt;
  let mapLayers = [];

  /* ===== TILE & VIEW STATE ===== */
  const tableViewContainer = document.getElementById("tableViewContainer");
  const tileViewContainer = document.getElementById("tileViewContainer");
  const employeeTilesContainer = document.getElementById("employeeTilesContainer");
  const mapViewContainer = document.getElementById("mapViewContainer");
  let currentView = "tile"; // default view is tile

  // Global employee list cache
  let allEmployees = [];

  async function fetchEmployees() {
    try {
      const res = await fetch("/api/employees");
      allEmployees = await res.json();
    } catch (e) {
      console.error("Failed to fetch employees:", e);
    }
  }

  await fetchEmployees();

  // ── Village Context Selection ──
  window.selectVillageContext = async function (vid) {
    try {
      const response = await csrfFetch("/set_context", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ vid })
      });
      const data = await response.json();
      if (data.success) {
        localStorage.setItem("landing_selected_vid", String(vid));
        window.location.href = "/dashboard";
      } else {
        alert("Failed to set village context: " + (data.error || "Unknown error"));
      }
    } catch (err) {
      console.error("Error setting context:", err);
      alert("Network error. Please try again.");
    }
  };

  if (employeeTilesContainer) {
    employeeTilesContainer.addEventListener("click", (e) => {
      const chip = e.target.closest(".village-chip");
      if (chip) {
        e.stopPropagation();
        const vid = chip.dataset.vid;
        window.selectVillageContext(vid);
      }
    });
  }

  // ── Restart Context Button Logic ──
  const restartBtn = document.getElementById("restartContextBtn");
  if (restartBtn) {
    if (window.selectedVid) {
      restartBtn.style.display = "inline-flex";
    }

    restartBtn.addEventListener("click", async () => {
      try {
        const response = await csrfFetch("/reset_context", {
          method: "POST"
        });
        const data = await response.json();
        if (data.success) {
          localStorage.removeItem("landing_selected_vid");
          window.location.reload();
        } else {
          alert("Failed to reset context");
        }
      } catch (err) {
        console.error("Error resetting context:", err);
      }
    });
  }

  // Update real-time search row counts
  function updateSummary() {
    const visible = snapshot.filter(d => d.row.style.display !== "none");
    const headerCount = document.getElementById("headerTotalVillages");
    if (headerCount) {
      headerCount.textContent = visible.length;
    }
  }

  window.applySearch = function () {
    const term = document.getElementById("searchBox").value.toLowerCase();

    // Filter table rows
    snapshot.forEach(d => {
      d.row.style.display = term === "" || d.text.includes(term) ? "" : "none";
    });
    updateSummary();

    // Filter employee tiles
    document.querySelectorAll(".employee-tile").forEach(tile => {
      const txt = tile.innerText.toLowerCase();
      tile.style.display = term === "" || txt.includes(term) ? "" : "none";
    });

    // Filter map markers & circles
    if (leafletMap && mapLayers.length > 0) {
      let visibleMarkers = [];
      mapLayers.forEach(item => {
        const matches = term === "" || 
                        item.name.includes(term) || 
                        item.code.includes(term) ||
                        item.emp1.includes(term) ||
                        item.emp2.includes(term);
        if (matches) {
          if (!leafletMap.hasLayer(item.marker)) leafletMap.addLayer(item.marker);
          if (!leafletMap.hasLayer(item.circle)) leafletMap.addLayer(item.circle);
          visibleMarkers.push(item.marker);
        } else {
          if (leafletMap.hasLayer(item.marker)) leafletMap.removeLayer(item.marker);
          if (leafletMap.hasLayer(item.circle)) leafletMap.removeLayer(item.circle);
        }
      });
      // Dynamically fit map bounds to matching markers
      if (visibleMarkers.length > 0) {
        const group = L.featureGroup(visibleMarkers);
        leafletMap.fitBounds(group.getBounds().pad(0.1));
      }
    }
  };

  window.printSelected = function () {
    window.print();
  };

  /* ===== COLUMN SELECTOR ===== */
  const modal = document.getElementById("columnModal");
  const list = document.getElementById("columnCheckboxList");
  const openBtn = document.getElementById("columnSelectorBtn");
  const closeBtn = document.getElementById("closeColumnModal");

  if (openBtn) {
    openBtn.addEventListener("click", () => {
      list.innerHTML = "";

      table.querySelectorAll("thead th").forEach((th, index) => {
        if (th.innerText.trim().toLowerCase() === "actions") return;

        const wrapper = document.createElement("label");
        wrapper.className = "column-item";

        const checkbox = document.createElement("input");
        checkbox.type = "checkbox";
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
  }

  if (closeBtn) {
    closeBtn.addEventListener("click", () => {
      modal.classList.add("hidden");
    });
  }

  function toggleColumn(index, show) {
    table.querySelectorAll("tr").forEach(row => {
      if (row.children[index])
        row.children[index].style.display = show ? "" : "none";
    });
  }

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

  /* ===== PRO-DESIGNER TILES VIEW ===== */
  function buildTileView() {
    if (!window.villageData || !employeeTilesContainer) return;

    const grouped = {};
    const selectedVid = window.selectedVid || localStorage.getItem("landing_selected_vid") || "";

    window.villageData.forEach(v => {
      const key = `${v.emp1 || "None"}-${v.emp2 || "None"}`;

      if (!grouped[key]) {
        grouped[key] = {
          emp1: v.emp1 || "None",
          emp2: v.emp2 || "None",
          emp1_name: v.emp1_name || `Employee ${v.emp1 || "None"}`,
          emp2_name: v.emp2_name || (v.emp2_name ? v.emp2_name : (v.emp2 ? `Employee ${v.emp2}` : "Unassigned")),
          villages: [],
          selected: false
        };
      }

      grouped[key].villages.push(v);
      if (selectedVid && String(v.vid) === String(selectedVid)) {
        grouped[key].selected = true;
      }
    });

    employeeTilesContainer.innerHTML = "";

    // Sort: selected group goes first
    const groups = Object.values(grouped).sort((a, b) => {
      if (a.selected && !b.selected) return -1;
      if (!a.selected && b.selected) return 1;
      return 0;
    });

    const showCreateBtn = window.userLevel === 'admin' || window.userLevel === 'mgmt';

    groups.forEach(group => {
      const tile = document.createElement("div");
      tile.dataset.emp1 = group.emp1;
      tile.dataset.emp2 = group.emp2;
      tile.className = "employee-tile" + (group.selected ? " selected-tile" : "");

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
              <i class="fas fa-user-tie"></i> ${group.emp1_name}
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
                <i class="fas fa-user-tie"></i> ${group.emp2_name}
              </span>
              `
              : `
              <span
                class="employee-empty-slot"
                data-slot="emp2"
                data-emp1="${group.emp1}"
                data-emp2="${group.emp2}">
                <i class="fas fa-plus-circle"></i> Add Employee
              </span>
              `
            }
          </div>
          <div class="employee-pair-subtitle">
            <i class="fas fa-fingerprint"></i> ID Ref: ${group.emp1} ${group.emp2 !== "None" ? '+ ' + group.emp2 : ''}
          </div>
          <div class="employee-pair-count" style="display: flex; justify-content: space-between; align-items: center; width: 100%;">
            <div>
              <i class="fas fa-home"></i> <span>${group.villages.length} Villages</span>
            </div>
            ${
              showCreateBtn
              ? `
              <button class="neumorphic-btn small create-village-tile-btn" style="margin: 0; padding: 4px 8px; font-size: 0.725rem; font-weight: 600; color: var(--primary); border-color: var(--primary); display: flex; align-items: center; gap: 4px;" onclick="event.stopPropagation(); window.openCreateVillageModal('${group.emp1}', '${group.emp2}')">
                <i class="fas fa-plus-circle"></i> Create Village
              </button>
              `
              : ''
            }
          </div>
        </div>
        <div class="employee-tile-body">
          ${group.villages.map(v => {
            const isChipSelected = selectedVid && String(v.vid) === String(selectedVid);
            return `
              <span
                class="village-chip draggable-village ${isChipSelected ? 'selected-village-chip' : ''}"
                draggable="true"
                data-vid="${v.vid}"
                data-village-code="${v.village_code}"
                data-village-name="${v.village_name}"
                data-emp1="${group.emp1}"
                data-emp2="${group.emp2}">
                <i class="fas fa-map-pin"></i> ${v.village_name}
              </span>
            `;
          }).join("")}
        </div>
      `;

      employeeTilesContainer.appendChild(tile);
      enableTileDrop(tile);
    });

    // Update Top bar stats
    const headerPairs = document.getElementById("headerEmployeePairs");
    if (headerPairs) {
      headerPairs.textContent = Object.keys(grouped).length;
    }

    initializeEmptySlotAssignment();
    initializeVillageDragging();
    initializeEmployeeDragging();
    initializeEmployeeEditing();
  }

  function enableTileDrop(tile) {
    const bodyContainer = tile.querySelector('.employee-tile-body');

    tile.addEventListener("dragover", (e) => {
      e.preventDefault();
      tile.classList.add("drag-target");
      if (bodyContainer) bodyContainer.classList.add("drag-over-body");
    });

    tile.addEventListener("dragleave", () => {
      tile.classList.remove("drag-target");
      if (bodyContainer) bodyContainer.classList.remove("drag-over-body");
    });

    tile.addEventListener("drop", async (e) => {
      e.preventDefault();
      tile.classList.remove("drag-target");
      if (bodyContainer) bodyContainer.classList.remove("drag-over-body");

      const employeeRaw = e.dataTransfer.getData("employee");

      if (employeeRaw) {
        const employee = JSON.parse(employeeRaw);
        const targetEmp1 = tile.dataset.emp1;
        const targetEmp2 = tile.dataset.emp2;
        const normalizedTargetEmp2 = (!targetEmp2 || targetEmp2 === "None") ? null : targetEmp2;

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
          const old_emp1 = employee.pair_emp1;
          const old_emp2 = employee.pair_emp2 === "None" ? null : employee.pair_emp2;

          const response = await csrfFetch("/api/village/update_employee_pair", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
              old_emp1: old_emp1,
              old_emp2: old_emp2,
              new_emp1: old_emp1,
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

          // Update local window.villageData cache
          window.villageData.forEach(v => {
            if (
              (String(v.emp1) === String(old_emp1) || (!v.emp1 && !old_emp1)) &&
              (String(v.emp2) === String(old_emp2) || (!v.emp2 && !old_emp2))
            ) {
              v.emp1 = old_emp1;
              v.emp2 = null;
              v.emp1_name = allEmployees.find(e => String(e.eid) === String(old_emp1))?.name || '';
              v.emp2_name = 'Unassigned';
            }
          });

          window.villageData.forEach(v => {
            if (
              (String(v.emp1) === String(targetEmp1) || (!v.emp1 && !targetEmp1)) &&
              (String(v.emp2) === String(normalizedTargetEmp2) || (!v.emp2 && !normalizedTargetEmp2))
            ) {
              v.emp1 = targetEmp1;
              v.emp2 = employee.eid;
              v.emp1_name = allEmployees.find(e => String(e.eid) === String(targetEmp1))?.name || '';
              v.emp2_name = employee.employee_name;
            }
          });

          // Sync table rows
          updateTableRowsForCluster(old_emp1, old_emp2, old_emp1, null);
          updateTableRowsForCluster(targetEmp1, normalizedTargetEmp2, targetEmp1, employee.eid);

          buildTileView();

          // Highlight target tile
          const newTile = Array.from(document.querySelectorAll('.employee-tile')).find(t => 
            String(t.dataset.emp1) === String(targetEmp1) && String(t.dataset.emp2) === String(employee.eid)
          );
          if (newTile) {
            newTile.classList.add("tile-success-flash");
            playSuccessSound();
            setTimeout(() => newTile.classList.remove("tile-success-flash"), 1800);
          }

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

      const normNewEmp2 = newEmp2 === "None" ? null : newEmp2;

      if (
        String(village.emp1) === String(newEmp1) &&
        String(village.emp2) === String(newEmp2)
      ) {
        return;
      }

      if (!confirm(`Move ${village.village_name} to employee pair ${newEmp1} + ${newEmp2}?`)) {
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
            emp1: newEmp1 === "None" ? null : newEmp1,
            emp2: normNewEmp2,
            new_name: village.village_name
          })
        });

        const result = await response.json();
        if (!result.success) {
          alert(result.error || "Failed to move village");
          return;
        }

        const record = window.villageData.find(x => String(x.vid) === String(village.vid));

        if (record) {
          record.emp1 = newEmp1 === "None" ? null : newEmp1;
          record.emp2 = normNewEmp2;
          record.emp1_name = allEmployees.find(e => String(e.eid) === String(newEmp1))?.name || `Employee ${newEmp1}`;
          record.emp2_name = normNewEmp2 ? (allEmployees.find(e => String(e.eid) === String(normNewEmp2))?.name || `Employee ${normNewEmp2}`) : 'Unassigned';
        }

        // Sync table row
        const row = document.querySelector(`#villageTableBody tr[data-vid="${village.vid}"]`);
        if (row) {
          row.querySelector('[data-field="emp1"]').innerText = newEmp1 === 'None' ? '' : newEmp1;
          row.querySelector('[data-field="emp2"]').innerText = normNewEmp2 || '';
          row.querySelector('[data-field="emp1_name"]').innerText = allEmployees.find(e => String(e.eid) === String(newEmp1))?.name || '';
          row.querySelector('[data-field="emp2_name"]').innerText = normNewEmp2 ? (allEmployees.find(e => String(e.eid) === String(normNewEmp2))?.name || '') : 'Unassigned';
          if (dt) dt.row(row).invalidate().draw(false);
        }

        buildTileView();

        // Highlight card
        tile.classList.add("tile-success-flash");
        playSuccessSound();
        setTimeout(() => {
          tile.classList.remove("tile-success-flash");
        }, 1800);

      } catch (err) {
        alert("Move failed: " + err.message);
      }
    });
  }

  function updateTableRowsForCluster(old_emp1, old_emp2, new_emp1, new_emp2) {
    document.querySelectorAll('#villageTableBody tr').forEach(row => {
      const rowEmp1 = row.querySelector('[data-field="emp1"]').innerText.trim();
      const rowEmp2 = row.querySelector('[data-field="emp2"]').innerText.trim();
      const normEmp2 = rowEmp2 === 'None' || rowEmp2 === '' ? null : rowEmp2;

      if (
        (String(rowEmp1) === String(old_emp1) || (!rowEmp1 && !old_emp1)) &&
        (String(normEmp2) === String(old_emp2) || (!normEmp2 && !old_emp2))
      ) {
        row.querySelector('[data-field="emp1"]').innerText = new_emp1 || '';
        row.querySelector('[data-field="emp2"]').innerText = new_emp2 || '';

        const emp1Name = allEmployees.find(e => String(e.eid) === String(new_emp1))?.name || '';
        const emp2Name = new_emp2 ? (allEmployees.find(e => String(e.eid) === String(new_emp2))?.name || '') : 'Unassigned';
        row.querySelector('[data-field="emp1_name"]').innerText = emp1Name;
        row.querySelector('[data-field="emp2_name"]').innerText = emp2Name;

        if (dt) dt.row(row).invalidate().draw(false);
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

  function initializeEmptySlotAssignment() {
    document.querySelectorAll('.employee-empty-slot').forEach(slot => {
      slot.addEventListener('click', async () => {
        try {
          const options = allEmployees
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
              justify-content:center;
              backdrop-filter: blur(8px);">

              <div style="
                width:520px;
                max-width:90vw;
                background:var(--surface-elevated, var(--surface));
                border:1px solid var(--border);
                border-radius:14px;
                padding:22px;
                box-shadow:var(--shadow-lg);">

                <h3 style="margin:0 0 16px 0;color:var(--primary);font-family:'Space Grotesk',sans-serif;">Assign Employee</h3>

                <select id="employeeAssignSelect" style="width:100%;padding:12px;background:var(--input-bg);color:var(--text);border:1px solid var(--border);border-radius:6px;outline:none;">
                  <option value="">Select Employee</option>
                  ${options}
                </select>

                <div style="display:flex;justify-content:flex-end;gap:12px;margin-top:20px;">
                  <button id="employeeAssignCancel" class="neumorphic-btn small">Cancel</button>
                  <button id="employeeAssignSave" class="neumorphic-btn small" style="color:var(--primary);border-color:var(--primary);">Assign</button>
                </div>
              </div>
            </div>
          `;

          document.body.insertAdjacentHTML('beforeend', selectedHtml);
          const overlay = document.getElementById('employeeAssignOverlay');

          document.getElementById('employeeAssignCancel').onclick = () => overlay.remove();

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

              // Update local state
              window.villageData.forEach(v => {
                if (String(v.emp1) === String(emp1) && (!v.emp2 || v.emp2 === 'None')) {
                  v.emp2 = employeeId;
                  v.emp2_name = allEmployees.find(e => String(e.eid) === String(employeeId))?.name || '';
                }
              });

              updateTableRowsForCluster(emp1, null, emp1, employeeId);
              overlay.remove();
              buildTileView();

              // Highlight card
              const t = Array.from(document.querySelectorAll('.employee-tile')).find(tile => 
                String(tile.dataset.emp1) === String(emp1) && String(tile.dataset.emp2) === String(employeeId)
              );
              if (t) {
                t.classList.add("tile-success-flash");
                playSuccessSound();
                setTimeout(() => t.classList.remove("tile-success-flash"), 1800);
              }

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

  function initializeDeactivateZone() {
    const deactivateZone = document.getElementById("deactivateZone");
    if (!deactivateZone) return;

    deactivateZone.addEventListener("dragover", (e) => {
      e.preventDefault();
      deactivateZone.classList.add("drag-over-deactivate");
    });

    deactivateZone.addEventListener("dragleave", () => {
      deactivateZone.classList.remove("drag-over-deactivate");
    });

    deactivateZone.addEventListener("drop", async (e) => {
      e.preventDefault();
      deactivateZone.classList.remove("drag-over-deactivate");

      const employeeRaw = e.dataTransfer.getData("employee");
      const villageRaw = e.dataTransfer.getData("application/json");

      if (employeeRaw) {
        const employee = JSON.parse(employeeRaw);
        showDeactivateOrDeleteModal({
          type: "employee",
          id: employee.eid,
          name: employee.employee_name,
          employeeData: employee
        });
      } else if (villageRaw) {
        const village = JSON.parse(villageRaw);
        showDeactivateOrDeleteModal({
          type: "village",
          id: village.vid,
          name: village.village_name,
          villageData: village
        });
      }
    });
  }

  function showDeactivateOrDeleteModal(item) {
    let existingModal = document.getElementById("deactivateActionOverlay");
    if (existingModal) existingModal.remove();

    const labelType = item.type === "employee" ? "employee" : "village";
    const displayName = item.name;

    const overlay = document.createElement("div");
    overlay.id = "deactivateActionOverlay";
    overlay.style.cssText = `
      position: fixed;
      inset: 0;
      background: rgba(0,0,0,.6);
      z-index: 10000;
      display: flex;
      align-items: center;
      justify-content: center;
      backdrop-filter: blur(8px);
    `;

    const isVillage = item.type === "village";

    overlay.innerHTML = `
      <div style="
        width: 520px;
        max-width: 90vw;
        background: var(--surface, #ffffff);
        border: 1px solid var(--border, #e5e7eb);
        border-radius: var(--radius-lg, 16px);
        padding: 24px;
        box-shadow: var(--shadow-lg);
        font-family: 'Inter', sans-serif;
        color: var(--text, #1a1a2e);">

        <h3 id="deactivateModalTitle" style="margin: 0 0 16px 0; color: var(--danger, #dc2626); font-family: var(--font-headline, 'Space Grotesk', sans-serif); font-weight: 700; font-size: 1.3rem;">
          ${isVillage ? 'Deactivate Village?' : 'Deactivate or Delete?'}
        </h3>
        <p id="deactivateModalDesc" style="margin: 0 0 24px 0; font-size: 0.95rem; color: var(--text-secondary, #6b7280); line-height: 1.5;">
          ${isVillage 
            ? `Are you sure you want to deactivate the village <strong>${displayName}</strong>?` 
            : `Would you like to <strong>Deactivate</strong> or <strong>Delete</strong> the employee <strong>${displayName}</strong>?`}
        </p>

        <!-- Choice Screen Buttons (hidden for village) -->
        <div id="deactivateActionChoice" style="display: ${isVillage ? 'none' : 'flex'}; gap: 12px; margin-bottom: 24px;">
          <button id="choiceDeactivateBtn" class="neumorphic-btn danger-btn" style="flex: 1; padding: 12px 18px; font-weight: 600; display: flex; align-items: center; justify-content: center; border-radius: 8px;">Deactivate</button>
          <button id="choiceDeleteBtn" class="neumorphic-btn danger-btn" style="flex: 1; padding: 12px 18px; font-weight: 600; display: flex; align-items: center; justify-content: center; border-radius: 8px; border-color: rgba(220, 38, 38, 0.4); color: var(--danger, #dc2626); background: transparent;">Delete</button>
        </div>

        <!-- Confirm Input Screen (shown immediately for village) -->
        <div id="deactivateConfirmSection" style="display: ${isVillage ? 'flex' : 'none'}; flex-direction: column; gap: 14px;">
          <p style="margin: 0; font-size: 0.9rem; color: var(--text-secondary, #6b7280); line-height: 1.4;">
            Please type the following phrase exactly to confirm: <br>
            <strong style="color: var(--text, #1a1a2e); font-family: monospace; font-size: 0.95rem; background: var(--border-light, #f3f4f6); padding: 4px 8px; border-radius: 4px; display: inline-block; margin-top: 6px;" id="confirmPhrase"></strong>
          </p>
          <input type="text" id="deactivateConfirmInput" placeholder="Type the confirmation phrase..." style="width: 100%; padding: 12px; border: 1px solid var(--border, #e5e7eb); border-radius: 6px; outline: none; font-size: 0.9rem; background: var(--input-bg, #f9fafb); color: var(--text, #1a1a2e); box-sizing: border-box;">
          
          <div style="display: flex; justify-content: flex-end; gap: 12px; margin-top: 10px;">
            <button id="deactivateConfirmCancel" class="neumorphic-btn small">Cancel</button>
            <button id="deactivateConfirmProceed" class="neumorphic-btn small danger-btn" style="padding: 8px 16px; border-radius: 6px;" disabled>Confirm Action</button>
          </div>
        </div>

        <!-- Cancel button on choice screen (hidden for village) -->
        <div id="deactivateChoiceCancelRow" style="display: ${isVillage ? 'none' : 'flex'}; justify-content: flex-end;">
          <button id="deactivateChoiceCancel" class="neumorphic-btn small">Cancel</button>
        </div>
      </div>
    `;

    document.body.appendChild(overlay);

    const actionChoiceDiv = overlay.querySelector("#deactivateActionChoice");
    const confirmSection = overlay.querySelector("#deactivateConfirmSection");
    const choiceCancelRow = overlay.querySelector("#deactivateChoiceCancelRow");
    const choiceDeactivateBtn = overlay.querySelector("#choiceDeactivateBtn");
    const choiceDeleteBtn = overlay.querySelector("#choiceDeleteBtn");
    const confirmPhraseStrong = overlay.querySelector("#confirmPhrase");
    const confirmInput = overlay.querySelector("#deactivateConfirmInput");
    const confirmCancelBtn = overlay.querySelector("#deactivateConfirmCancel");
    const choiceCancelBtn = overlay.querySelector("#deactivateChoiceCancel");
    const proceedBtn = overlay.querySelector("#deactivateConfirmProceed");

    const closeModal = () => overlay.remove();
    confirmCancelBtn.onclick = closeModal;
    choiceCancelBtn.onclick = closeModal;

    let chosenAction = isVillage ? "deactivate" : "";
    const expectedPhrase = `Deactivate the ${displayName} ${labelType}`;
    confirmPhraseStrong.textContent = expectedPhrase;

    if (isVillage) {
      setTimeout(() => confirmInput.focus(), 50);
    }

    const setupConfirmation = (action) => {
      chosenAction = action;
      actionChoiceDiv.style.display = "none";
      choiceCancelRow.style.display = "none";
      confirmSection.style.display = "flex";
      confirmInput.focus();
    };

    choiceDeactivateBtn.onclick = () => setupConfirmation("deactivate");
    choiceDeleteBtn.onclick = () => setupConfirmation("delete");

    confirmInput.oninput = () => {
      const isMatch = confirmInput.value === expectedPhrase;
      proceedBtn.disabled = !isMatch;
    };

    proceedBtn.onclick = async () => {
      proceedBtn.disabled = true;
      proceedBtn.textContent = "Processing...";

      try {
        let success = false;
        let errorMsg = "";
        let newStatus = "";

        if (item.type === "village") {
          if (chosenAction === "deactivate") {
            const response = await csrfFetch("/api/village/toggle_status", {
              method: "POST",
              headers: { "Content-Type": "application/json" },
              body: JSON.stringify({ vid: item.id })
            });
            const data = await response.json();
            success = data.success;
            errorMsg = data.error;
            newStatus = data.status;
          }
        } else if (item.type === "employee") {
          if (chosenAction === "deactivate") {
            const response = await csrfFetch("/api/employee/toggle_status", {
              method: "POST",
              headers: { "Content-Type": "application/json" },
              body: JSON.stringify({ eid: item.id })
            });
            const data = await response.json();
            success = data.success;
            errorMsg = data.error;
            newStatus = data.status;
          } else {
            const response = await csrfFetch("/api/delete_employee", {
              method: "POST",
              headers: { "Content-Type": "application/json" },
              body: JSON.stringify({ eid: item.id })
            });
            const data = await response.json();
            success = data.success;
            errorMsg = data.error;
          }
        }

        if (success) {
          closeModal();
          playSuccessSound();

          if (item.type === "village") {
            if (chosenAction === "deactivate") {
              const record = window.villageData.find(x => String(x.vid) === String(item.id));
              if (record) {
                record.status = newStatus;
              }

              const row = document.querySelector(`#villageTableBody tr[data-vid="${item.id}"]`);
              if (row) {
                const statusCell = row.querySelector(".status-badge");
                if (statusCell) {
                  statusCell.innerText = newStatus.charAt(0).toUpperCase() + newStatus.slice(1);
                  statusCell.className = `status-badge status-${newStatus}`;
                }
                if (newStatus === "inactive") {
                  row.classList.add("inactive-row");
                } else {
                  row.classList.remove("inactive-row");
                }
                if (dt) dt.row(row).invalidate().draw(false);
              }

              triggerSuccessFeedback({
                sectionElement: document.getElementById("tableViewContainer"),
                message: `Village ${displayName} deactivated successfully.`,
                highlightDuration: 2000
              });
            } else {
              window.villageData = window.villageData.filter(x => String(x.vid) !== String(item.id));

              const row = document.querySelector(`#villageTableBody tr[data-vid="${item.id}"]`);
              if (row) {
                if (dt) dt.row(row).remove().draw(false);
              }

              triggerSuccessFeedback({
                sectionElement: document.getElementById("tableViewContainer"),
                message: `Village ${displayName} deleted successfully.`,
                highlightDuration: 2000
              });
            }

            buildTileView();
            if (leafletMap) {
              mapInitialized = false;
              document.getElementById("indiaVillageMap").innerHTML = "";
              initMap();
            }
          } else if (item.type === "employee") {
            await fetchEmployees();

            if (chosenAction === "deactivate") {
              triggerSuccessFeedback({
                sectionElement: document.getElementById("tileViewContainer"),
                message: `Employee ${displayName} deactivated successfully.`,
                highlightDuration: 2000
              });
            } else {
              triggerSuccessFeedback({
                sectionElement: document.getElementById("tileViewContainer"),
                message: `Employee ${displayName} deleted successfully.`,
                highlightDuration: 2000
              });
            }

            buildTileView();
          }

        } else {
          alert(`Error: ${errorMsg || "Failed to perform action."}`);
          proceedBtn.disabled = false;
          proceedBtn.textContent = "Confirm Action";
        }
      } catch (err) {
        alert(`Request failed: ${err.message}`);
        proceedBtn.disabled = false;
        proceedBtn.textContent = "Confirm Action";
      }
    };
  }
  window.showDeactivateOrDeleteModal = showDeactivateOrDeleteModal;

  function initializeEmployeeEditing() {
    document.querySelectorAll(".editable-employee").forEach(chip => {
      chip.addEventListener("dblclick", async (e) => {
        e.stopPropagation();
        try {
          const options = allEmployees
            .map(emp => `<option value="${emp.eid}">${emp.eid} - ${emp.name}</option>`)
            .join("");

          const currentSlot = chip.dataset.slot;
          const overlay = document.createElement("div");
          overlay.id = "employeeReplaceOverlay";
          overlay.style.position = 'fixed';
          overlay.style.inset = '0';
          overlay.style.background = 'rgba(0,0,0,.6)';
          overlay.style.zIndex = '10000';
          overlay.style.display = 'flex';
          overlay.style.alignItems = 'center';
          overlay.style.justifyContent = 'center';
          overlay.style.backdropFilter = 'blur(8px)';

          overlay.innerHTML = `
            <div style="width:520px;max-width:90vw;background:var(--surface-elevated, var(--surface));border:1px solid var(--border);border-radius:14px;padding:22px;box-shadow:var(--shadow-lg);">
              <h3 style="margin:0 0 16px 0;color:var(--primary);font-family:'Space Grotesk',sans-serif;">Replace Employee</h3>
              <select id="employeeReplaceSelect" style="width:100%;padding:12px;background:var(--input-bg);color:var(--text);border:1px solid var(--border);border-radius:6px;outline:none;">
                <option value="">Select Employee</option>
                ${options}
              </select>
              <div style="margin-top:20px;display:flex;justify-content:flex-end;gap:12px;">
                <button id="employeeReplaceCancel" class="neumorphic-btn small">Cancel</button>
                <button id="employeeReplaceSave" class="neumorphic-btn small" style="color:var(--primary);border-color:var(--primary);">Save</button>
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

            const old_emp1 = chip.dataset.pairEmp1;
            const old_emp2 = chip.dataset.pairEmp2 === "None" ? null : chip.dataset.pairEmp2;
            const new_emp1 = currentSlot === "emp1" ? selectedEmployee : old_emp1;
            const new_emp2 = currentSlot === "emp2" ? selectedEmployee : old_emp2;

            const saveResponse = await csrfFetch("/api/village/update_employee_pair", {
              method: "POST",
              headers: { "Content-Type": "application/json" },
              body: JSON.stringify({
                old_emp1,
                old_emp2,
                new_emp1,
                new_emp2
              })
            });

            const result = await saveResponse.json();

            if (!result.success) {
              alert(result.error || "Update failed");
              return;
            }

            // Update local state cache
            window.villageData.forEach(v => {
              if (
                (String(v.emp1) === String(old_emp1) || (!v.emp1 && !old_emp1)) &&
                (String(v.emp2) === String(old_emp2) || (!v.emp2 && !old_emp2))
              ) {
                v.emp1 = new_emp1;
                v.emp2 = new_emp2;
                v.emp1_name = allEmployees.find(e => String(e.eid) === String(new_emp1))?.name || '';
                v.emp2_name = new_emp2 ? (allEmployees.find(e => String(e.eid) === String(new_emp2))?.name || '') : 'Unassigned';
              }
            });

            updateTableRowsForCluster(old_emp1, old_emp2, new_emp1, new_emp2);
            overlay.remove();
            buildTileView();

            const t = Array.from(document.querySelectorAll('.employee-tile')).find(tile => 
              String(tile.dataset.emp1) === String(new_emp1) && String(tile.dataset.emp2) === String(new_emp2)
            );
            if (t) {
              t.classList.add("tile-success-flash");
              playSuccessSound();
              setTimeout(() => t.classList.remove("tile-success-flash"), 1800);
            }
          };

        } catch (err) {
          alert(err.message);
        }
      });
    });
  }

  /* ===== SLIDING SEGMENTED SWITCHER ===== */
  function switchVillageView(mode) {
    currentView = mode;

    if (tableViewContainer) {
      tableViewContainer.style.display = mode === "table" ? "" : "none";
      if (mode === "table" && dt) {
        dt.columns.adjust().draw(false);
      }
    }
    if (tileViewContainer) {
      tileViewContainer.style.display = mode === "tile" ? "" : "none";
    }
    if (mapViewContainer) {
      mapViewContainer.style.display = mode === "map" ? "" : "none";
    }

    // No trash zone display toggling

    document.querySelectorAll(".segmented-btn").forEach(btn => {
      btn.classList.toggle("active", btn.id === `${mode}ViewBtn`);
    });

    if (mode === "map") {
      initMap();
      if (leafletMap) {
        setTimeout(() => {
          leafletMap.invalidateSize();
        }, 50);
      }
    }

    setTimeout(updateSegmentedHighlight, 50);
  }

  function updateSegmentedHighlight() {
    const pill = document.getElementById("viewTabPill");
    const activeBtn = document.querySelector(".segmented-btn.active");
    if (pill && activeBtn) {
      pill.style.width = activeBtn.offsetWidth + "px";
      pill.style.left = activeBtn.offsetLeft + "px";
    }
  }

  window.addEventListener("resize", updateSegmentedHighlight);

  // Bind clicks
  const tableBtn = document.getElementById("tableViewBtn");
  const tileBtn = document.getElementById("tileViewBtn");
  const mapBtn = document.getElementById("mapViewBtn");

  if (tableBtn) tableBtn.onclick = () => switchVillageView("table");
  if (tileBtn) tileBtn.onclick = () => switchVillageView("tile");
  if (mapBtn) mapBtn.onclick = () => switchVillageView("map");

  /* ===== DOUBLE-CLICK INLINE EDITING ===== */
  let currentlyEditingRow = null;

  body.addEventListener("dblclick", function(e) {
    const row = e.target.closest("tr");
    if (!row) return;

    if (row.classList.contains("row-editing")) return;
    if (e.target.closest("[data-field='actions']")) return;

    makeRowEditable(row);
  });

  function makeRowEditable(row) {
    if (currentlyEditingRow) {
      cancelRowInline(currentlyEditingRow);
    }

    currentlyEditingRow = row;
    row.dataset.originalHtml = row.innerHTML;
    row.classList.add("row-editing");

    const cells = row.querySelectorAll("td[data-field]");
    const emp1Val = row.querySelector('[data-field="emp1"]')?.innerText.trim() || "";
    const emp2Val = row.querySelector('[data-field="emp2"]')?.innerText.trim() || "";

    cells.forEach(cell => {
      const field = cell.dataset.field;
      const currentText = cell.innerText.trim();

      if (field === "village_code" || field === "village_name" || field === "district" || field === "pincode" || field === "state") {
        cell.innerHTML = `<input type="text" class="inline-edit-input" name="${field}" value="${currentText.replace(/"/g, '&quot;')}">`;
      } else if (field === "emp1_name") {
        let options = allEmployees.map(emp => `
          <option value="${emp.eid}" ${String(emp.eid) === String(emp1Val) ? 'selected' : ''}>
            ${emp.name}
          </option>
        `).join('');
        cell.innerHTML = `<select class="inline-edit-select" name="emp1">${options}</select>`;
      } else if (field === "emp2_name") {
        let options = `<option value="">Unassigned</option>` + allEmployees.map(emp => `
          <option value="${emp.eid}" ${String(emp.eid) === String(emp2Val) ? 'selected' : ''}>
            ${emp.name}
          </option>
        `).join('');
        cell.innerHTML = `<select class="inline-edit-select" name="emp2">${options}</select>`;
      }
    });

    const actionsCell = row.querySelector("td[data-field='actions']") || row.querySelector("td:last-child");
    if (actionsCell) {
      actionsCell.innerHTML = `
        <div class="action-buttons" style="display: flex; gap: 6px; align-items: center;">
          <button class="neumorphic-btn ultrasmall" style="color: #10b981; border-color: rgba(16, 185, 129, 0.35);" onclick="event.stopPropagation(); saveRowInline(this)">
            Save
          </button>
          <button class="neumorphic-btn ultrasmall" style="color: var(--text-muted); border-color: rgba(255,255,255,0.2);" onclick="event.stopPropagation(); cancelRowInline(this)">
            Cancel
          </button>
        </div>
      `;
    }
  }

  window.saveRowInline = async function (btn) {
    const row = btn.closest("tr");
    if (!row) return;

    const vid = row.dataset.vid;
    const village_code_input = row.querySelector('[name="village_code"]');
    const village_name_input = row.querySelector('[name="village_name"]');
    const district_input = row.querySelector('[name="district"]');
    const pincode_input = row.querySelector('[name="pincode"]');
    const state_input = row.querySelector('[name="state"]');
    const emp1_select = row.querySelector('[name="emp1"]');
    const emp2_select = row.querySelector('[name="emp2"]');

    if (!village_code_input || !village_name_input) return;

    const village_code = village_code_input.value.trim().toUpperCase();
    const village_name = village_name_input.value.trim().toUpperCase();
    const district = district_input ? district_input.value.trim().toUpperCase() : "";
    const pincode = pincode_input ? pincode_input.value.trim().toUpperCase() : "";
    const state = state_input ? state_input.value.trim().toUpperCase() : "";
    const emp1 = emp1_select ? emp1_select.value : "";
    const emp2 = emp2_select ? (emp2_select.value || null) : null;

    if (!village_code || !village_name) {
      alert("Village code and name are required.");
      return;
    }

    try {
      const response = await csrfFetch("/api/update_village", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          vid,
          village_code,
          village_name,
          district,
          pincode,
          state,
          emp1,
          emp2
        })
      });

      const result = await response.json();
      if (!result.success) {
        alert(result.error || "Failed to update village");
        return;
      }

      // Update local cache
      const record = window.villageData.find(x => String(x.vid) === String(vid));
      if (record) {
        record.village_code = village_code;
        record.village_name = village_name;
        record.district = district;
        record.pincode = pincode;
        record.state = state;
        record.emp1 = emp1;
        record.emp2 = emp2;
        record.emp1_name = allEmployees.find(e => String(e.eid) === String(emp1))?.name || `Employee ${emp1}`;
        record.emp2_name = emp2 ? (allEmployees.find(e => String(e.eid) === String(emp2))?.name || `Employee ${emp2}`) : 'Unassigned';
      }

      // Update table cells
      row.querySelector('[data-field="village_code"]').innerText = village_code;
      row.querySelector('[data-field="village_name"]').innerText = village_name;
      row.querySelector('[data-field="district"]').innerText = district;
      row.querySelector('[data-field="pincode"]').innerText = pincode;
      row.querySelector('[data-field="state"]').innerText = state;
      row.querySelector('[data-field="emp1"]').innerText = emp1;
      row.querySelector('[data-field="emp2"]').innerText = emp2 || 'None';

      const emp1Name = allEmployees.find(e => String(e.eid) === String(emp1))?.name || `Employee ${emp1}`;
      const emp2Name = emp2 ? (allEmployees.find(e => String(e.eid) === String(emp2))?.name || `Employee ${emp2}`) : 'Unassigned';
      row.querySelector('[data-field="emp1_name"]').innerText = emp1Name;
      row.querySelector('[data-field="emp2_name"]').innerText = emp2Name;

      // Restore action buttons
      const status = record ? record.status : 'active';
      const actionHtml = `
        <div class="action-buttons" style="display: flex; gap: 6px; align-items: center;">
          <button class="neumorphic-btn ultrasmall" style="color: #00f2fe; border-color: rgba(0, 242, 254, 0.35);"
                  onclick="event.stopPropagation(); openVillageDashboard('${vid}')">
            Dashboard
          </button>
          <button class="neumorphic-btn ultrasmall ${status === 'active' ? 'danger-btn' : ''}"
                  onclick="event.stopPropagation(); toggleVillageStatus('${vid}', this)">
            ${status === 'active' ? 'Inactivate' : 'Activate'}
          </button>
        </div>
      `;
      const actionsCell = row.querySelector("td[data-field='actions']") || row.querySelector("td:last-child");
      if (actionsCell) {
        actionsCell.innerHTML = actionHtml;
      }

      row.classList.remove("row-editing");
      delete row.dataset.originalHtml;
      currentlyEditingRow = null;

      // Invalidate DataTable cache
      if (dt) {
        dt.row(row).invalidate().draw(false);
      }

      // Trigger success overlay & sounds
      triggerSuccessFeedback({
        sectionElement: document.getElementById("tableViewContainer"),
        highlightElements: [row],
        message: "Village Saved Successfully",
        highlightDuration: 3000
      });

      // Update Search Index
      const snapRow = snapshot.find(s => s.row === row);
      if (snapRow) {
        snapRow.text = row.innerText.toLowerCase();
      }

      // Rebuild views
      buildTileView();
      if (leafletMap) {
        mapInitialized = false;
        initMap();
      }

    } catch (err) {
      alert("Error saving: " + err.message);
    }
  };

  window.cancelRowInline = function (btn) {
    const row = btn.closest("tr");
    if (!row) return;

    row.innerHTML = row.dataset.originalHtml;
    row.classList.remove("row-editing");
    delete row.dataset.originalHtml;
    currentlyEditingRow = null;
  };

  /* ===== MAP VIEW ===== */
  let mapInitialized = false;
  let leafletMap = null;
  let mapTileLayer = null;

  function updateMapTileLayer() {
    if (!leafletMap) return;
    
    if (mapTileLayer) {
      leafletMap.removeLayer(mapTileLayer);
    }
    
    const isDark = document.documentElement.getAttribute('data-theme') === 'dark';
    const tileUrl = isDark 
      ? 'https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png'
      : 'https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png';
      
    mapTileLayer = L.tileLayer(tileUrl, {
      attribution: '© OpenStreetMap contributors, © CARTO',
      maxZoom: 19
    }).addTo(leafletMap);
  }

  function initMap() {
    if (mapInitialized) return;
    mapInitialized = true;

    // Destroy existing map instance to prevent "Map container is already initialized" error
    if (leafletMap) {
      try {
        leafletMap.off();
        leafletMap.remove();
      } catch (e) {
        console.error("Error destroying map:", e);
      }
      leafletMap = null;
    }
    mapLayers = [];

    // Calculate map center based on average coordinates of villages that have coordinates
    let latSum = 0;
    let lngSum = 0;
    let validCoordsCount = 0;

    window.villageData.forEach(v => {
      if (v.latitude && v.longitude) {
        latSum += parseFloat(v.latitude);
        lngSum += parseFloat(v.longitude);
        validCoordsCount++;
      }
    });

    let centerLat = 15.9129; // fallback center (Andhra Pradesh/Telangana area)
    let centerLng = 79.7400;
    if (validCoordsCount > 0) {
      centerLat = latSum / validCoordsCount;
      centerLng = lngSum / validCoordsCount;
    }

    // Initialize Leaflet map
    leafletMap = L.map('indiaVillageMap', {
      doubleClickZoom: false // disable default double-click zoom so dblclick event handler works cleanly
    }).setView([centerLat, centerLng], validCoordsCount > 0 ? 8 : 7);

    // Load initial tile layer based on current theme
    updateMapTileLayer();

    // Loop through villages and render markers and circles
    window.villageData.forEach(v => {
      let lat = v.latitude;
      let lng = v.longitude;
      
      // Fallback coordinate generation if not geocoded
      if (!lat || !lng) {
        let seed = (v.vid * 1337) % 1000 / 1000;
        let seed2 = (v.vid * 7331) % 1000 / 1000;
        lat = 15.9129 + (seed - 0.5) * 2.2;
        lng = 79.7400 + (seed2 - 0.5) * 2.2;
      }

      // Determine size (customer count) and circle radius
      const customerCount = v.customer_count || 0;
      // Clamped radius: 25 meters per customer, min 400m, max 10000m
      const radius = Math.max(400, Math.min(10000, customerCount * 25));

      // Theme-aware color choices for glass circles
      const isDark = document.documentElement.getAttribute('data-theme') === 'dark';
      const circleOptions = {
        color: isDark ? 'rgba(16, 185, 129, 0.45)' : 'rgba(26, 77, 46, 0.45)',
        fillColor: isDark ? 'rgba(16, 185, 129, 0.08)' : 'rgba(26, 77, 46, 0.08)',
        fillOpacity: 0.2,
        weight: 1,
        radius: radius
      };

      // Create marker and glass circle
      const marker = L.marker([lat, lng]).addTo(leafletMap);
      const circle = L.circle([lat, lng], circleOptions).addTo(leafletMap);

      // Custom tooltips (show on hover)
      const tooltipContent = `
        <div class="map-tooltip-content">
          <h4>${v.village_name}</h4>
          <div class="tooltip-row"><strong>Code:</strong> <span>${v.village_code}</span></div>
          <div class="tooltip-row"><strong>Pincode:</strong> <span>${v.pincode || 'N/A'}</span></div>
          <div class="tooltip-row"><strong>Location:</strong> <span>${v.district}, ${v.state}</span></div>
          <div class="tooltip-row"><strong>Customers:</strong> <span class="status-badge status-active" style="padding: 1px 6px; font-size:0.75rem;">${customerCount} open</span></div>
          <div class="tooltip-row"><strong>Assigned:</strong> <span>${v.emp1_name || 'None'} ${v.emp2_name && v.emp2_name !== 'Unassigned' ? '+ ' + v.emp2_name : ''}</span></div>
          <div class="tooltip-footer">Double-click marker/circle to enter dashboard</div>
        </div>
      `;

      marker.bindTooltip(tooltipContent, { sticky: true, className: 'custom-map-tooltip' });
      circle.bindTooltip(tooltipContent, { sticky: true, className: 'custom-map-tooltip' });

      // Detailed popups (show on click)
      const popupContent = `
        <div class="map-popup-content" style="font-family:'Inter', sans-serif; padding: 4px; color: var(--text);">
          <h4 style="margin: 0 0 8px 0; font-family:'Space Grotesk', sans-serif; font-size: 1.1rem; color: var(--primary); font-weight:600;">${v.village_name}</h4>
          <p style="margin: 0 0 6px 0; font-size: 0.85rem;"><strong>Code:</strong> ${v.village_code} &nbsp;|&nbsp; <strong>Pincode:</strong> ${v.pincode || 'N/A'}</p>
          <p style="margin: 0 0 6px 0; font-size: 0.85rem;"><strong>District:</strong> ${v.district} &nbsp;|&nbsp; <strong>State:</strong> ${v.state}</p>
          <p style="margin: 0 0 12px 0; font-size: 0.85rem;"><strong>Size:</strong> ${customerCount} open customer accounts</p>
          <button class="neumorphic-btn small" style="width: 100%; margin: 0; padding: 8px; font-weight: 600; display: flex; align-items: center; justify-content: center; gap: 6px;" onclick="window.openVillageDashboard(${v.vid})">
            <i class="fas fa-chart-line"></i> Enter Dashboard
          </button>
        </div>
      `;

      marker.bindPopup(popupContent);
      circle.bindPopup(popupContent);

      // Double-click navigation
      marker.on('dblclick', () => {
        window.openVillageDashboard(v.vid);
      });
      circle.on('dblclick', () => {
        window.openVillageDashboard(v.vid);
      });

      // Save layers for search filtering
      mapLayers.push({
        vid: v.vid,
        name: v.village_name.toLowerCase(),
        code: v.village_code.toLowerCase(),
        emp1: (v.emp1_name || "").toLowerCase(),
        emp2: (v.emp2_name || "").toLowerCase(),
        marker: marker,
        circle: circle
      });
    });

    // Invalidate map size so it fits container perfectly
    setTimeout(() => {
      leafletMap.invalidateSize();
    }, 150);
  }

  // Hook into the global theme switcher checkbox to update the map tile layer on-the-fly
  const themeToggleCb = document.getElementById('themeToggleCheckbox');
  if (themeToggleCb) {
    themeToggleCb.addEventListener('change', () => {
      if (leafletMap) {
        updateMapTileLayer();
        // Redraw circles with theme-specific colors
        window.villageData.forEach(v => {
          const item = mapLayers.find(layer => layer.vid === v.vid);
          if (item && item.circle) {
            const isDark = document.documentElement.getAttribute('data-theme') === 'dark';
            item.circle.setStyle({
              color: isDark ? 'rgba(16, 185, 129, 0.45)' : 'rgba(26, 77, 46, 0.45)',
              fillColor: isDark ? 'rgba(16, 185, 129, 0.08)' : 'rgba(26, 77, 46, 0.08)'
            });
          }
        });
      }
    });
  }

  /* ===== INITIALIZE DATA AND TABLES ===== */
  updateSummary();

  dt = $.fn.DataTable.isDataTable('#villageTable')
    ? $('#villageTable').DataTable()
    : $('#villageTable').DataTable({
        paging: false,
        info: false,
        searching: false,
        ordering: true
      });

  applyDefaultColumnVisibility();
  buildTileView();
  initializeDeactivateZone();

  // Set default view to tiles
  switchVillageView("tile");

  const searchBox = document.getElementById("searchBox");
  if (searchBox) {
    searchBox.addEventListener("input", window.applySearch);
  }

  dt.on('draw', () => {
    updateSummary();
  });
});

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
      if (data.status === "inactive") {
        btn.innerText = "Activate";
        btn.classList.remove("danger-btn");
      } else {
        btn.innerText = "Inactivate";
        btn.classList.add("danger-btn");
      }

      const row = btn.closest("tr");
      const statusCell = row.querySelector(".status-badge");

      if (statusCell) {
        statusCell.innerText = data.status.charAt(0).toUpperCase() + data.status.slice(1);
        statusCell.classList.remove("status-active", "status-inactive");
        statusCell.classList.add("status-" + data.status);
      }

      if (data.status === "inactive") {
        row.classList.add("inactive-row");
      } else {
        row.classList.remove("inactive-row");
      }

      // Update local cache
      const record = window.villageData.find(x => String(x.vid) === String(vid));
      if (record) {
        record.status = data.status;
      }

      if (typeof refreshVillageDropdown === "function") {
        refreshVillageDropdown();
      }

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