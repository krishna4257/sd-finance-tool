document.addEventListener("DOMContentLoaded", function () {

  const table = document.getElementById("employeeTable");
  const body = document.getElementById("employeeTableBody");
  let rows = Array.from(body.querySelectorAll("tr"));

  let snapshot = rows.map(row => ({
    row,
    text: row.innerText.toLowerCase()
  }));

  const formatDate = window.formatDate;

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
    let visibleCount = 0;
    if ($.fn.DataTable.isDataTable('#employeeTable')) {
      visibleCount = $('#employeeTable').DataTable().rows({ search: 'applied' }).count();
    } else {
      visibleCount = snapshot.filter(d => d.row.style.display !== "none").length;
    }
    const headerCount = document.getElementById("headerTotalEmployees");
    if (headerCount) {
      headerCount.textContent = visibleCount;
    }
  }

  /* ===== VIEW TOGGLER ===== */
  function switchEmployeeView(view) {
    const tileBtn = document.getElementById("tileViewBtn");
    const tableBtn = document.getElementById("tableViewBtn");
    const tileContainer = document.getElementById("tileViewContainer");
    const tableContainer = document.getElementById("tableViewContainer");

    if (view === "tile") {
      tileBtn.classList.add("active");
      tableBtn.classList.remove("active");
      if (tileContainer) tileContainer.style.display = "";
      if (tableContainer) tableContainer.style.display = "none";
    } else {
      tableBtn.classList.add("active");
      tileBtn.classList.remove("active");
      if (tableContainer) tableContainer.style.display = "";
      if (tileContainer) tileContainer.style.display = "none";
    }
    updateSegmentedHighlight();
  }

  function updateSegmentedHighlight() {
    const container = document.getElementById("viewToggleContainer");
    if (!container) return;
    const pill = container.querySelector("#viewTabPill");
    const activeBtn = container.querySelector(".segmented-btn.active");
    if (pill && activeBtn) {
      pill.style.width = activeBtn.offsetWidth + "px";
      pill.style.left = activeBtn.offsetLeft + "px";
    }
  }

  const tileBtn = document.getElementById("tileViewBtn");
  const tableBtn = document.getElementById("tableViewBtn");
  if (tileBtn) tileBtn.addEventListener("click", () => switchEmployeeView("tile"));
  if (tableBtn) tableBtn.addEventListener("click", () => switchEmployeeView("table"));

  window.addEventListener("resize", updateSegmentedHighlight);
  // Initial position calculation after rendering settles
  setTimeout(updateSegmentedHighlight, 100);

  /* ===== SEARCH FILTERING ===== */
  window.applySearch = function () {
    const rawTerm = document.getElementById("searchBox").value.trim();
    const term = rawTerm.toLowerCase();

    if ($.fn.DataTable.isDataTable('#employeeTable')) {
      const dtInstance = $('#employeeTable').DataTable();
      dtInstance.search(term).draw();

      // Synchronize card visibility based on Datatable active rows
      const visibleEids = new Set();
      dtInstance.rows({ search: 'applied' }).every(function() {
        const rowNode = this.node();
        const eid = rowNode.dataset.eid;
        if (eid) {
          visibleEids.add(eid);
        }
      });

      document.querySelectorAll(".employee-card").forEach(card => {
        const eid = card.dataset.eid;
        if (visibleEids.has(eid)) {
          card.style.display = "";
        } else {
          card.style.display = "none";
        }
      });
    } else {
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

        const card = document.querySelector(`.employee-card[data-eid="${eid}"]`);
        if (card) {
          card.style.display = match ? "" : "none";
        }
      });
    }
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

  // Format joining dates on initial page load (both table and card)
  document.querySelectorAll('[data-field="joining_date"]').forEach(el => {
    el.textContent = formatDate(el.textContent);
  });

  /* ===== DOUBLE-CLICK INLINE EDITING FOR ROWS ===== */
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
    if (currentlyEditingCard) {
      cancelCardInline(currentlyEditingCard);
    }

    currentlyEditingRow = row;
    row.dataset.originalHtml = row.innerHTML;
    row.classList.add("row-editing");

    const cells = row.querySelectorAll("td[data-field]");

    cells.forEach(cell => {
      const field = cell.dataset.field;
      const currentText = cell.innerText.trim();

      if (field === "eid" || field === "is_active") {
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

      // Sync Card View
      const card = document.querySelector(`.employee-card[data-eid="${eid}"]`);
      if (card) {
        const avatarEl = card.querySelector(".employee-avatar");
        const nameEl = card.querySelector(".employee-name");
        const levelEl = card.querySelector(".employee-level");

        if (avatarEl) avatarEl.innerText = name.charAt(0).toUpperCase();
        if (nameEl) nameEl.innerText = name;
        if (levelEl) levelEl.innerText = level;

        const cardPhone = card.querySelector('[data-field="phone_number"]');
        const cardCity = card.querySelector('[data-field="city"]');
        const cardState = card.querySelector('[data-field="state"]');
        const cardJoining = card.querySelector('[data-field="joining_date"]');

        if (cardPhone) cardPhone.innerText = phone_number;
        if (cardCity) cardCity.innerText = city;
        if (cardState) cardState.innerText = state;
        if (cardJoining) cardJoining.innerText = display_date;
      }

      // Update Datatable
      if (dt) {
        dt.row(row).invalidate().draw(false);
      }

      // Success chime and overlay
      if (typeof triggerSuccessFeedback === "function") {
        triggerSuccessFeedback({
          sectionElement: document.getElementById("tableViewContainer"),
          highlightElements: [row],
          message: "Employee Saved Successfully",
          highlightDuration: 3000
        });
      } else {
        row.classList.add("row-updated-glow");
        setTimeout(() => row.classList.remove("row-updated-glow"), 3000);
      }

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

  /* ===== DOUBLE-CLICK INLINE EDITING FOR CARDS ===== */
  let currentlyEditingCard = null;

  const cardGrid = document.getElementById("employeeCardsGrid");
  if (cardGrid) {
    cardGrid.addEventListener("dblclick", function(e) {
      const card = e.target.closest(".employee-card");
      if (!card) return;

      if (card.classList.contains("card-editing")) return;
      if (e.target.closest(".employee-card-footer") || e.target.closest("button")) return;

      makeCardEditable(card);
    });
  }

  function makeCardEditable(card) {
    if (currentlyEditingCard) {
      cancelCardInline(currentlyEditingCard);
    }
    if (currentlyEditingRow) {
      cancelRowInline(currentlyEditingRow);
    }

    currentlyEditingCard = card;
    card.dataset.originalHtml = card.innerHTML;
    card.classList.add("card-editing");

    const nameEl = card.querySelector(".employee-name");
    const levelEl = card.querySelector(".employee-level");

    if (nameEl) {
      const currentName = nameEl.innerText.trim();
      nameEl.innerHTML = `<input type="text" class="inline-edit-input" name="name" value="${currentName.replace(/"/g, '&quot;')}">`;
    }
    if (levelEl) {
      const currentLevel = levelEl.innerText.trim();
      levelEl.innerHTML = `<input type="text" class="inline-edit-input" name="level" value="${currentLevel.replace(/"/g, '&quot;')}">`;
    }

    const fields = ['phone_number', 'city', 'state', 'joining_date'];
    fields.forEach(field => {
      const cell = card.querySelector(`[data-field="${field}"]`);
      if (cell) {
        const currentText = cell.innerText.trim();
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
      }
    });

    const footer = card.querySelector(".employee-card-footer");
    if (footer) {
      footer.innerHTML = `
        <div style="width: 100%; display: flex; justify-content: flex-end; gap: 8px; align-items: center;">
          <button class="neumorphic-btn ultrasmall" style="color: #10b981; border-color: rgba(16, 185, 129, 0.35);" onclick="event.stopPropagation(); saveCardInline(this)">
            Save
          </button>
          <button class="neumorphic-btn ultrasmall" style="color: var(--text-muted); border-color: rgba(255,255,255,0.2);" onclick="event.stopPropagation(); cancelCardInline(this)">
            Cancel
          </button>
        </div>
      `;
    }
  }

  window.cancelCardInline = function (btnOrCard) {
    const card = btnOrCard.classList.contains("employee-card") ? btnOrCard : btnOrCard.closest(".employee-card");
    if (!card) return;

    card.innerHTML = card.dataset.originalHtml;
    card.classList.remove("card-editing");
    delete card.dataset.originalHtml;
    currentlyEditingCard = null;
  };

  window.saveCardInline = async function (btn) {
    const card = btn.closest(".employee-card");
    if (!card) return;

    const eid = card.dataset.eid;
    const name_input = card.querySelector('[name="name"]');
    const phone_input = card.querySelector('[name="phone_number"]');
    const city_input = card.querySelector('[name="city"]');
    const date_input = card.querySelector('[name="joining_date"]');
    const level_input = card.querySelector('[name="level"]');
    const state_input = card.querySelector('[name="state"]');

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

      // Restore card layout
      card.innerHTML = card.dataset.originalHtml;
      card.classList.remove("card-editing");
      delete card.dataset.originalHtml;
      currentlyEditingCard = null;

      // Update card values
      card.querySelector(".employee-avatar").innerText = name.charAt(0).toUpperCase();
      card.querySelector(".employee-name").innerText = name;
      card.querySelector(".employee-level").innerText = level;
      if (card.querySelector('[data-field="phone_number"]')) card.querySelector('[data-field="phone_number"]').innerText = phone_number;
      if (card.querySelector('[data-field="city"]')) card.querySelector('[data-field="city"]').innerText = city;
      if (card.querySelector('[data-field="state"]')) card.querySelector('[data-field="state"]').innerText = state;
      if (card.querySelector('[data-field="joining_date"]')) card.querySelector('[data-field="joining_date"]').innerText = display_date;

      // Update corresponding table row
      const row = document.querySelector(`tr[data-eid="${eid}"]`);
      if (row) {
        row.querySelector('[data-field="name"]').innerText = name;
        if (row.querySelector('[data-field="phone_number"]')) row.querySelector('[data-field="phone_number"]').innerText = phone_number;
        if (row.querySelector('[data-field="city"]')) row.querySelector('[data-field="city"]').innerText = city;
        if (row.querySelector('[data-field="joining_date"]')) row.querySelector('[data-field="joining_date"]').innerText = display_date;
        if (row.querySelector('[data-field="level"]')) row.querySelector('[data-field="level"]').innerText = level;
        if (row.querySelector('[data-field="state"]')) row.querySelector('[data-field="state"]').innerText = state;

        if (dt) {
          dt.row(row).invalidate().draw(false);
        }

        // Update search snapshot index
        const snapRow = snapshot.find(s => s.row === row);
        if (snapRow) {
          snapRow.text = row.innerText.toLowerCase();
        }
      }

      // Success chime and overlay
      if (typeof triggerSuccessFeedback === "function") {
        triggerSuccessFeedback({
          sectionElement: document.getElementById("tileViewContainer"),
          highlightElements: [card],
          message: "Employee Saved Successfully",
          highlightDuration: 3000
        });
      } else {
        card.classList.add("row-updated-glow");
        setTimeout(() => card.classList.remove("row-updated-glow"), 3000);
      }

    } catch (err) {
      alert("Error saving: " + err.message);
    }
  };

  /* ===== TOGGLE EMPLOYEE STATUS ===== */
  window.toggleEmployeeStatus = function(eid, btn) {
    if (!confirm("Are you sure you want to change employee status?")) return;

    const row = document.querySelector(`tr[data-eid="${eid}"]`);
    const card = document.querySelector(`.employee-card[data-eid="${eid}"]`);

    const rowBtn = row ? row.querySelector('td[data-field="actions"] button, td:last-child button') : null;
    const cardBtn = card ? card.querySelector('.employee-card-footer button') : null;

    const originalRowText = rowBtn ? rowBtn.innerText : "";
    const originalCardText = cardBtn ? cardBtn.innerText : "";

    if (rowBtn) {
      rowBtn.disabled = true;
      rowBtn.innerText = "Processing...";
    }
    if (cardBtn) {
      cardBtn.disabled = true;
      cardBtn.innerText = "Processing...";
    }

    csrfFetch("/api/employee/toggle_status", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ eid })
    })
    .then(res => res.json())
    .then(data => {
      if (data.success) {
        const isActive = data.status === "active";
        const statusText = data.status.charAt(0).toUpperCase() + data.status.slice(1);

        if (row) {
          if (!isActive) {
            row.classList.add("inactive-row");
          } else {
            row.classList.remove("inactive-row");
          }
          const rowStatusCell = row.querySelector(".status-cell");
          if (rowStatusCell) {
            rowStatusCell.innerHTML = `<span class="status-badge status-${data.status}">${statusText}</span>`;
          }
          if (rowBtn) {
            rowBtn.innerText = isActive ? "Deactivate" : "Activate";
            if (isActive) {
              rowBtn.classList.add("danger-btn");
            } else {
              rowBtn.classList.remove("danger-btn");
            }
          }
        }

        if (card) {
          if (!isActive) {
            card.classList.add("inactive-card");
          } else {
            card.classList.remove("inactive-card");
          }
          const cardStatusCell = card.querySelector(".status-cell");
          if (cardStatusCell) {
            cardStatusCell.innerHTML = `<span class="status-badge status-${data.status}">${statusText}</span>`;
          }
          if (cardBtn) {
            cardBtn.innerText = isActive ? "Deactivate" : "Activate";
            if (isActive) {
              cardBtn.classList.add("danger-btn");
            } else {
              cardBtn.classList.remove("danger-btn");
            }
          }
        }

        // Update search snapshot index
        if (row) {
          const snapshotItem = snapshot.find(d => d.row === row);
          if (snapshotItem) {
            snapshotItem.text = row.innerText.toLowerCase();
          }
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
        if (rowBtn) rowBtn.innerText = originalRowText;
        if (cardBtn) cardBtn.innerText = originalCardText;
      }
    })
    .catch(err => {
      alert("Request failed: " + err.message);
      if (rowBtn) rowBtn.innerText = originalRowText;
      if (cardBtn) cardBtn.innerText = originalCardText;
    })
    .finally(() => {
      if (rowBtn) rowBtn.disabled = false;
      if (cardBtn) cardBtn.disabled = false;
    });
  };

  /* ===== INITIALIZE DATA AND TABLES ===== */
  updateSummary();

  const dt = $.fn.DataTable.isDataTable('#employeeTable')
    ? $('#employeeTable').DataTable()
    : $('#employeeTable').DataTable({
        paging: false,
        info: false,
        searching: true,
        ordering: true
      });

  dt.on('draw', () => {
    updateSummary();
  });
});

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