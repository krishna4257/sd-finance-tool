document.addEventListener("DOMContentLoaded", function () {

  const table = document.getElementById("employeeTable");
  const body = document.getElementById("employeeTableBody");
  let rows = Array.from(body.querySelectorAll("tr"));

  let snapshot = rows.map(row => ({
    row,
    text: row.innerText.toLowerCase()
  }));

  function formatDate(value) {
    if (!value) return "";
    const str = String(value).trim();
    // Match YYYY-MM-DD
    const match = str.match(/^(\d{4})-(\d{2})-(\d{2})$/);
    if (!match) return value;
    const [, year, month, day] = match;
    return `${day}-${month}-${year}`;
  }

  function ddmmyyyyToIso(dateStr) {
    if (!dateStr) return "";
    const parts = dateStr.split('-');
    if (parts.length === 3) {
      const [dd, mm, yyyy] = parts;
      return `${yyyy}-${mm}-${dd}`;
    }
    return dateStr;
  }

  function updateSummary() {
    const visible = snapshot.filter(d => d.row.style.display !== "none");
    const headerCount = document.getElementById("headerTotalEmployees");
    if (headerCount) {
      headerCount.textContent = visible.length;
    }
  }

  window.applySearch = function () {
    const rawTerm = document.getElementById("searchBox").value.trim();
    const term = rawTerm.toLowerCase();

    snapshot.forEach(d => {
      const row = d.row;
      const eidCell = row.querySelector('td[data-field="eid"]');
      const nameCell = row.querySelector('td[data-field="name"]');
      const phoneCell = row.querySelector('td[data-field="phone_number"]');

      const eid = eidCell ? eidCell.innerText.trim() : "";
      const name = nameCell ? nameCell.innerText.toLowerCase().trim() : "";
      const phone = phoneCell ? phoneCell.innerText.trim() : "";

      let match = false;

      if (term === "") {
        match = true;
      } else if (/^\d{10}$/.test(term)) {
        match = phone.includes(term);
      } else if (/^\d{1,3}$/.test(term)) {
        match = eid === term;
      } else {
        match = name.includes(term);
      }

      row.style.display = match ? "" : "none";
    });

    updateSummary();
  };

  const searchBox = document.getElementById("searchBox");
  if (searchBox) {
    searchBox.addEventListener("input", window.applySearch);
  }

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

  const DEFAULT_HIDDEN_COLUMNS = [];

  // Format joining dates on initial page load
  body.querySelectorAll('td[data-field="joining_date"]').forEach(td => {
    td.textContent = formatDate(td.textContent);
  });

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

    cells.forEach(cell => {
      const field = cell.dataset.field;
      const currentText = cell.innerText.trim();

      if (field === "eid" || field === "is_active") {
        // Read-only columns
        return;
      }

      cell.innerHTML = `<input type="text" class="inline-edit-input" name="${field}" value="${currentText.replace(/"/g, '&quot;')}">`;

      if (field === "joining_date") {
        const inputEl = cell.querySelector('input');
        if (typeof window.initCustomCalendar === "function") {
          window.initCustomCalendar(inputEl, {
            dateFormat: 'd-m-Y',
            clickOpens: true,
            noWrapper: true
          });
          setTimeout(() => {
            if (document.activeElement === inputEl) {
              inputEl.click();
            }
          }, 50);
        }
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

    const eid = row.dataset.eid;
    const name_input = row.querySelector('[name="name"]');
    const phone_input = row.querySelector('[name="phone_number"]');
    const city_input = row.querySelector('[name="city"]');
    const date_input = row.querySelector('[name="joining_date"]');
    const level_input = row.querySelector('[name="level"]');
    const state_input = row.querySelector('[name="state"]');

    if (!name_input) return;

    const name = name_input.value.trim();
    const phone_number = phone_input ? phone_input.value.trim() : "";
    const city = city_input ? city_input.value.trim() : "";
    const display_date = date_input ? date_input.value.trim() : "";
    const level = level_input ? level_input.value.trim() : "";
    const state = state_input ? state_input.value.trim() : "";

    const joining_date = ddmmyyyyToIso(display_date);

    if (!name) {
      alert("Employee name is required.");
      return;
    }

    try {
      const response = await csrfFetch("/api/update_employee", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          eid,
          name,
          phone_number,
          city,
          joining_date,
          level,
          state
        })
      });

      const result = await response.json();
      if (!result.success) {
        alert(result.error || "Failed to update employee");
        return;
      }

      // Update table cells in DOM
      row.querySelector('[data-field="name"]').innerText = name;
      if (row.querySelector('[data-field="phone_number"]')) row.querySelector('[data-field="phone_number"]').innerText = phone_number;
      if (row.querySelector('[data-field="city"]')) row.querySelector('[data-field="city"]').innerText = city;
      if (row.querySelector('[data-field="joining_date"]')) row.querySelector('[data-field="joining_date"]').innerText = display_date;
      if (row.querySelector('[data-field="level"]')) row.querySelector('[data-field="level"]').innerText = level;
      if (row.querySelector('[data-field="state"]')) row.querySelector('[data-field="state"]').innerText = state;

      // Restore Actions
      const statusCell = row.querySelector('[data-field="is_active"]');
      const is_active = statusCell ? statusCell.innerText.trim().toLowerCase() === "active" : true;
      const actionHtml = `
        <div class="action-buttons" style="display: flex; gap: 6px; align-items: center;">
          <button class="neumorphic-btn ultrasmall ${is_active ? 'danger-btn' : ''}"
                  onclick="event.stopPropagation(); toggleEmployeeStatus('${eid}', this)">
            ${is_active ? 'Deactivate' : 'Activate'}
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

      // Update Datatable
      if (dt) {
        dt.row(row).invalidate().draw(false);
      }

      // Success chime and overlay
      triggerSuccessFeedback({
        sectionElement: document.getElementById("tableViewContainer"),
        highlightElements: [row],
        message: "Employee Saved Successfully",
        highlightDuration: 3000
      });

      // Update search snapshot index
      const snapRow = snapshot.find(s => s.row === row);
      if (snapRow) {
        snapRow.text = row.innerText.toLowerCase();
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

  /* ===== INITIALIZE DATA AND TABLES ===== */
  updateSummary();

  const dt = $.fn.DataTable.isDataTable('#employeeTable')
    ? $('#employeeTable').DataTable()
    : $('#employeeTable').DataTable({
        paging: false,
        info: false,
        searching: false,
        ordering: true
      });

  dt.on('draw', () => {
    updateSummary();
  });
});

/* ===== TOGGLE EMPLOYEE STATUS ===== */
function toggleEmployeeStatus(eid, btn) {
  if (!confirm("Are you sure you want to change employee status?")) return;

  const originalText = btn.innerText;
  btn.disabled = true;
  btn.innerText = "Processing...";

  csrfFetch("/api/employee/toggle_status", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ eid })
  })
  .then(res => res.json())
  .then(data => {
    if (data.success) {
      const isActive = data.status === "active";
      if (isActive) {
        btn.innerText = "Deactivate";
        btn.classList.add("danger-btn");
      } else {
        btn.innerText = "Activate";
        btn.classList.remove("danger-btn");
      }

      const row = btn.closest("tr");
      const statusCell = row.querySelector(".status-cell");

      if (statusCell) {
        statusCell.innerHTML = `<span class="status-badge status-${data.status}">${data.status.charAt(0).toUpperCase() + data.status.slice(1)}</span>`;
      }

      if (!isActive) {
        row.classList.add("inactive-row");
      } else {
        row.classList.remove("inactive-row");
      }

      // Update snapshot
      const employeeTableBody = document.getElementById("employeeTableBody");
      const rows = Array.from(employeeTableBody.querySelectorAll("tr"));
      const snapshotItem = rows
        .map(r => ({ row: r, text: r.innerText.toLowerCase() }))
        .find(d => d.row === row);

      if (snapshotItem) {
        snapshotItem.text = row.innerText.toLowerCase();
      }

      if (typeof refreshEmployeeDropdown === "function") {
        refreshEmployeeDropdown();
      }

      const employeeSelect = document.getElementById("employeeSelect");
      if (employeeSelect && employeeSelect.value == eid && !isActive) {
        csrfFetch("/reset_context", { method: "POST" })
          .then(() => {
            employeeSelect.value = "";
          });
      }

    } else {
      alert("Failed: " + (data.error || "Unknown error"));
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

function refreshEmployeeDropdown() {
  const employeeSelect = document.getElementById("employeeSelect");
  if (!employeeSelect) return;

  fetch("/api/employees")
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