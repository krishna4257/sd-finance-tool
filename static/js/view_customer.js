document.addEventListener("DOMContentLoaded", function () {
  const table = document.getElementById("customerTable");
  const tableBody = document.getElementById("customerTableBody");
  if (!table || !tableBody) {
    window.formatDate = function(value) {
      if (!value) return "";
      const str = String(value).trim();
      const match = str.match(/^(\d{4})-(\d{2})-(\d{2})$/);
      if (!match) return value;
      const [, year, month, day] = match;
      return `${day}/${month}/${year}`;
    };
    return;
  }
  const rows = Array.from(tableBody.querySelectorAll("tr"));
  const clean = v => v.replace(/[₹,]/g, "").trim();

  // Column keys in order of generation
  const COLUMN_KEYS = [
    "ano", "name", "start_date", "end_date", "total_amount", "paid_amount", 
    "balance_amount", "installment_amount", "type", "period", "pano", "notes",
    "phone_number", "aadhaar_number", "customer_rating", "final_frozen_rating",
    "final_risk_level", "freeze_date", "latitude", "longitude", "eid", "created_at", "status"
  ];

  const ALL_COLUMNS = [
    { key: "ano", label: "ANO", isDefault: true },
    { key: "name", label: "Name", isDefault: true },
    { key: "start_date", label: "Start DT", isDefault: true },
    { key: "end_date", label: "End DT", isDefault: true },
    { key: "total_amount", label: "Total", isDefault: true },
    { key: "paid_amount", label: "Paid", isDefault: true },
    { key: "balance_amount", label: "Balance", isDefault: true },
    { key: "installment_amount", label: "Inst", isDefault: true },
    { key: "type", label: "Type", isDefault: true },
    { key: "period", label: "PRD", isDefault: true },
    { key: "pano", label: "P.NO", isDefault: true },
    { key: "notes", label: "Notes", isDefault: true },
    { key: "phone_number", label: "Phone", isDefault: false },
    { key: "aadhaar_number", label: "Aadhaar", isDefault: false },
    { key: "customer_rating", label: "Rating", isDefault: true },
    { key: "final_frozen_rating", label: "Frozen Rating", isDefault: false },
    { key: "final_risk_level", label: "Risk Level", isDefault: false },
    { key: "freeze_date", label: "Freeze Date", isDefault: false },
    { key: "latitude", label: "Latitude", isDefault: false },
    { key: "longitude", label: "Longitude", isDefault: false },
    { key: "eid", label: "Collector EID", isDefault: false },
    { key: "created_at", label: "Created At", isDefault: false },
    { key: "status", label: "Status", isDefault: false }
  ];

  function formatDate(value) {
    if (!value) return "";
    const str = String(value).trim();
    const match = str.match(/^(\d{4})-(\d{2})-(\d{2})$/);
    if (!match) return value;
    const [, year, month, day] = match;
    return `${day}/${month}/${year}`;
  }

  function createSnapshotItem(row) {
    const ano = clean(row.querySelector(".col-ano")?.textContent || "").toLowerCase();
    const pano = clean(row.querySelector(".col-pano")?.textContent || "").toLowerCase();
    const name = (row.querySelector(".col-name")?.textContent || "").trim().toLowerCase();
    const phone_number = (row.querySelector(".col-phone_number")?.textContent || "").trim();
    const total_amount = parseFloat(clean(row.querySelector(".col-total_amount")?.textContent || "0")) || 0;
    const paid_amount = parseFloat(clean(row.querySelector(".col-paid_amount")?.textContent || "0")) || 0;
    const balance_amount = parseFloat(clean(row.querySelector(".col-balance_amount")?.textContent || "0")) || 0;
    const statusText = (row.querySelector(".col-status")?.textContent || "").trim().toLowerCase();
    return {
      row,
      ano,
      pano,
      name,
      phone_number,
      total_amount,
      paid_amount,
      balance_amount,
      status: statusText
    };
  }

  // 🔒 Immutable snapshot
  const snapshot = rows.map(row => createSnapshotItem(row));

  function updateSummary() {
    const searchBox = document.getElementById("searchBox");
    const isSearchActive = searchBox && searchBox.value.trim() !== "";
    const isReportActive = snapshot.some(d => d.row.style.display === "none") && !isSearchActive;
    
    // Check if we have any active search or filter active
    const isFiltered = isSearchActive || isReportActive;

    if (!isFiltered) {
      // Restore initial server-side totals (incorporating all active & closed village data)
      const grid = document.querySelector(".customer-analytics-grid");
      if (grid) {
        const activeCount = grid.dataset.initActiveCount || "0";
        const closedCount = grid.dataset.initClosedCount || "0";
        const defaultedCount = grid.dataset.initDefaultedCount || "0";
        const activeLoan = parseFloat(grid.dataset.initActiveLoan || "0") || 0;
        const closedLoan = parseFloat(grid.dataset.initClosedLoan || "0") || 0;
        const activeBal = parseFloat(grid.dataset.initActiveBal || "0") || 0;
        const defaultedBal = parseFloat(grid.dataset.initDefaultedBal || "0") || 0;

        const activeCountEl = document.getElementById("activeCustomersCount");
        const defaultedCountEl = document.getElementById("defaultedCustomersCount");
        const closedCountEl = document.getElementById("closedCustomersCount");
        const totalLoanAmtEl = document.getElementById("totalLoanAmt");
        const closedLoanAmtEl = document.getElementById("closedLoanAmt");
        const activeBalAmtEl = document.getElementById("activeBalAmt");
        const defaultedBalAmtEl = document.getElementById("defaultedBalAmt");

        if (activeCountEl) activeCountEl.textContent = activeCount;
        if (defaultedCountEl) defaultedCountEl.textContent = defaultedCount;
        if (closedCountEl) closedCountEl.textContent = closedCount;
        if (totalLoanAmtEl) totalLoanAmtEl.textContent = activeLoan.toFixed(2);
        if (closedLoanAmtEl) closedLoanAmtEl.textContent = closedLoan.toFixed(2);
        if (activeBalAmtEl) activeBalAmtEl.textContent = activeBal.toFixed(2);
        if (defaultedBalAmtEl) defaultedBalAmtEl.textContent = defaultedBal.toFixed(2);
      }
    } else {
      // Filtered/searched state: calculate from visible rows in the table
      const visible = snapshot.filter(d => d.row.style.display !== "none");
      
      let activeCount = 0;
      let defaultedCount = 0;
      let closedCount = 0;
      let totalLoanSum = 0;
      let closedLoanSum = 0;
      let activeBalSum = 0;
      let defaultedBalSum = 0;
      
      visible.forEach(d => {
        if (d.status === 'active') {
          activeCount++;
          totalLoanSum += d.total_amount;
          activeBalSum += d.balance_amount;
        } else {
          closedCount++;
          closedLoanSum += d.total_amount; // Sum of total_amount of all closed customers
          if (d.balance_amount > 0) {
            defaultedCount++;
            defaultedBalSum += d.balance_amount;
          }
        }
      });

      const activeCountEl = document.getElementById("activeCustomersCount");
      const defaultedCountEl = document.getElementById("defaultedCustomersCount");
      const closedCountEl = document.getElementById("closedCustomersCount");
      const totalLoanAmtEl = document.getElementById("totalLoanAmt");
      const closedLoanAmtEl = document.getElementById("closedLoanAmt");
      const activeBalAmtEl = document.getElementById("activeBalAmt");
      const defaultedBalAmtEl = document.getElementById("defaultedBalAmt");

      if (activeCountEl) activeCountEl.textContent = activeCount;
      if (defaultedCountEl) defaultedCountEl.textContent = defaultedCount;
      if (closedCountEl) closedCountEl.textContent = closedCount;
      if (totalLoanAmtEl) totalLoanAmtEl.textContent = totalLoanSum.toFixed(2);
      if (closedLoanAmtEl) closedLoanAmtEl.textContent = closedLoanSum.toFixed(2);
      if (activeBalAmtEl) activeBalAmtEl.textContent = activeBalSum.toFixed(2);
      if (defaultedBalAmtEl) defaultedBalAmtEl.textContent = defaultedBalSum.toFixed(2);
    }

    // Apply ₹ formatting after updating values
    if (typeof applyGlobalMoneyFormatting === "function") {
      applyGlobalMoneyFormatting();
    }
    requestAnimationFrame(() => {
       table.style.width = "100%";  
    });
  }

  window.applySearch = function () {
    const rawTerm = document.getElementById("searchBox").value.trim();
    const term = rawTerm.toLowerCase();

    // Empty search → reset view by loading default path
    if (!term) {
      window.location.href = window.location.pathname + (window.location.search.includes("mode=closed") ? "?mode=closed" : "");
      return;
    }

    // If it's a number (but not a 10-digit phone number)
    const isAnoSearch = /^\d+$/.test(term) && !/^\d{10}$/.test(term);

    if (isAnoSearch) {
      applyParentSearch(term);
    } else {
      const isPhoneSearch = /^\d{10}$/.test(term);
      snapshot.forEach(d => {
        let show = false;
        if (isPhoneSearch) {
          show = d.phone_number === term;
        } else {
          show = d.name.includes(term);
        }
        d.row.style.display = show ? "" : "none";
      });
      updateSummary();
    }
  };

  window.toggleAll = function (source) {
    tableBody.querySelectorAll("input[type='checkbox']").forEach(cb => cb.checked = source.checked);
  };

  window.toggleColumnDropdown = function() {
    const dropdown = document.getElementById("columnDropdownMenu");
    if (dropdown) {
      dropdown.classList.toggle("hidden");
    }
  };

  window.initColumnConfigurator = function() {
    const container = document.getElementById("columnCheckboxesList");
    if (!container) return;
    container.innerHTML = "";
    
    ALL_COLUMNS.forEach(col => {
      const label = document.createElement("label");
      const checkbox = document.createElement("input");
      checkbox.type = "checkbox";
      checkbox.checked = col.isDefault;
      checkbox.addEventListener("change", function() {
        toggleColumnVisibility(col.key, this.checked);
      });
      label.appendChild(checkbox);
      label.appendChild(document.createTextNode(" " + col.label));
      container.appendChild(label);
    });
  };

  function toggleColumnVisibility(key, visible) {
    const tableEl = document.getElementById("customerTable");
    const wrapper = document.querySelector(".customer-table-wrapper");
    if (!tableEl) return;
    
    const className = `hide-col-${key}`;
    [tableEl, wrapper].forEach(el => {
      if (!el) return;
      if (visible) {
        el.classList.remove(className);
      } else {
        el.classList.add(className);
      }
    });
  }

  // Close columns config dropdown if clicking outside
  document.addEventListener("click", function(e) {
    const dropdown = document.getElementById("columnDropdownMenu");
    const btn = document.getElementById("colConfigBtn");
    if (dropdown && btn && !dropdown.contains(e.target) && !btn.contains(e.target)) {
      dropdown.classList.add("hidden");
    }
  });

  // Printing Layout Actions
  window.activatePrintLayout = function() {
    const bar = document.getElementById("printSetupBar");
    const tableEl = document.getElementById("customerTable");
    const wrapper = document.querySelector(".customer-table-wrapper");
    if (!bar || !tableEl) return;
    
    bar.classList.remove("hidden");
    tableEl.classList.add("print-mode-active");
    if (wrapper) wrapper.classList.add("print-mode-active");
    
    const selector = document.getElementById("printColumnsSelector");
    if (selector) {
      selector.innerHTML = "";
      
      ALL_COLUMNS.forEach(col => {
        const isVisible = !tableEl.classList.contains(`hide-col-${col.key}`);
        if (isVisible) {
          const label = document.createElement("label");
          label.style.display = "inline-flex";
          label.style.alignItems = "center";
          label.style.gap = "6px";
          label.style.cursor = "pointer";
          
          const checkbox = document.createElement("input");
          checkbox.type = "checkbox";
          checkbox.checked = true;
          checkbox.dataset.colKey = col.key;
          checkbox.dataset.colLabel = col.label;
          
          label.appendChild(checkbox);
          label.appendChild(document.createTextNode(col.label));
          selector.appendChild(label);
        }
      });
    }
  };

  window.confirmPrintLayout = function() {
    const tableEl = document.getElementById("customerTable");
    if (!tableEl || !tableBody) return;
    
    const selectedCheckboxes = Array.from(tableBody.querySelectorAll("input[type='checkbox']:checked"));
    const rowsToPrint = selectedCheckboxes.length > 0 
      ? selectedCheckboxes.map(cb => cb.closest("tr")) 
      : snapshot.filter(d => d.row.style.display !== "none").map(d => d.row);
      
    const printCheckboxes = Array.from(document.querySelectorAll("#printColumnsSelector input[type='checkbox']:checked"));
    const colsToPrint = printCheckboxes.map(cb => ({
      key: cb.dataset.colKey,
      label: cb.dataset.colLabel
    }));
    
    if (colsToPrint.length === 0) {
      alert("Please select at least one column to print.");
      return;
    }
    
    let html = `
    <html>
    <head>
      <title>Print Customers</title>
      <style>
        body { font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; padding: 20px; color: #1e293b; }
        h2 { color: #1e3a8a; border-bottom: 2px solid #3b82f6; padding-bottom: 8px; margin-bottom: 20px; }
        table { width: 100%; border-collapse: collapse; margin-top: 10px; }
        th, td { border: 1px solid #e2e8f0; padding: 10px 8px; text-align: left; font-size: 11px; }
        th { background-color: #f8fafc; font-weight: bold; color: #475569; }
        tr:nth-child(even) { background-color: #f8fafc; }
      </style>
    </head>
    <body>
      <h2>Customers List</h2>
      <table>
        <thead>
          <tr>
    `;
    
    colsToPrint.forEach(col => {
      html += `<th>${col.label}</th>`;
    });
    
    html += `
          </tr>
        </thead>
        <tbody>
    `;
    
    rowsToPrint.forEach(row => {
      html += "<tr>";
      colsToPrint.forEach(col => {
        const cell = row.querySelector(`.col-${col.key}`);
        const text = cell ? cell.textContent.trim() : "";
        html += `<td>${text}</td>`;
      });
      html += "</tr>";
    });
    
    html += `
        </tbody>
      </table>
    </body>
    </html>
    `;
    
    const w = window.open("", "", "width=1000,height=700");
    w.document.write(html);
    w.document.close();
    w.print();
    
    cancelPrintLayout();
  };

  window.cancelPrintLayout = function() {
    const bar = document.getElementById("printSetupBar");
    const tableEl = document.getElementById("customerTable");
    const wrapper = document.querySelector(".customer-table-wrapper");
    if (bar) bar.classList.add("hidden");
    if (tableEl) tableEl.classList.remove("print-mode-active");
    if (wrapper) wrapper.classList.remove("print-mode-active");
    
    const checkboxes = document.querySelectorAll("#customerTable input[type='checkbox']");
    checkboxes.forEach(cb => cb.checked = false);
  };

  window.applyParentSearch = async function (searchBoxValue) {
    const rawTerm = searchBoxValue || document.getElementById("searchBox").value.trim();
    const term = rawTerm.toLowerCase();

    if (!term) {
      window.location.reload();
      return;
    }

    try {
      const response = await fetch(`/api/customer_family_full/${encodeURIComponent(term)}`);
      if (!response.ok) {
        throw new Error(`HTTP ${response.status}`);
      }

      const result = await response.json();
      if (!result.success) {
        alert(result.error || "Unable to load parent accounts.");
        return;
      }

      const customers = result.customers || [];
      if (customers.length === 0) {
        alert("No related accounts found.");
        return;
      }

      // Rebuild Table rows dynamically using COLUMN_KEYS
      if ($.fn.DataTable.isDataTable('#customerTable')) {
        $('#customerTable').DataTable().clear().destroy();
      }
      tableBody.innerHTML = "";

      customers.forEach(customer => {
        tableBody.offsetHeight; // force repaint

        const tr = document.createElement("tr");
        tr.className = "table-row";
        tr.setAttribute("data-ano", customer.ano);
        tr.setAttribute("data-cid", customer.cid);

        // Checkbox column
        const checkboxTd = document.createElement("td");
        checkboxTd.className = "checkbox-column";
        checkboxTd.style.textAlign = "center";
        checkboxTd.innerHTML = `<input type="checkbox" />`;
        tr.appendChild(checkboxTd);

        // Values columns
        COLUMN_KEYS.forEach(key => {
          const td = document.createElement("td");
          td.className = `col-${key}`;
          
          let value = customer[key];
          if (value === null || value === undefined) {
            value = "";
          }
          
          if (["total_amount", "paid_amount", "balance_amount", "installment_amount"].includes(key)) {
            td.setAttribute("data-money", "");
            td.textContent = value;
            if (key === "balance_amount") {
              td.classList.add("amount-paid");
            }
          } else if (key === "status") {
            td.innerHTML = `<span class="status-badge status-${String(value).toLowerCase().replace(/\s+/g, '-')}">${value}</span>`;
          } else if (key === "start_date" || key === "end_date") {
            td.textContent = formatDate(value);
          } else {
            td.textContent = value;
          }
          
          tr.appendChild(td);
        });

        tableBody.appendChild(tr);
      });

      // Update toggle switch container highlight based on returned customer statuses
      let hasActive = false;
      let hasClosed = false;
      customers.forEach(customer => {
        if (String(customer.status).toLowerCase() === 'active') {
          hasActive = true;
        } else {
          hasClosed = true;
        }
      });
      const toggleContainer = document.getElementById("customerModeToggle");
      if (toggleContainer) {
        if (hasActive && hasClosed) {
          toggleContainer.className = "sliding-toggle-container mode-both";
        } else if (hasClosed) {
          toggleContainer.className = "sliding-toggle-container mode-closed";
        } else {
          toggleContainer.className = "sliding-toggle-container mode-active";
        }
      }

      // Reinitialize DataTable matching standard views
      const rebuiltTable = $('#customerTable').DataTable({
        destroy: true,
        paging: false,
        info: false,
        searching: false,
        ordering: true,
        order: [[1, 'desc']],
        autoWidth: false,
        scrollX: true,
        scrollCollapse: true,
        fixedHeader: false
      });

      rebuiltTable.on('draw', () => {
        if (typeof window.updateSummary === 'function') {
          window.updateSummary();
        }
      });

      setTimeout(() => {
        rebuiltTable.columns.adjust().draw(false);
      }, 50);

      // Rebuild snapshot
      snapshot.length = 0;
      Array.from(tableBody.querySelectorAll("tr")).forEach(row => {
        snapshot.push(createSnapshotItem(row));
      });

      updateSummary();

      const url = new URL(window.location.href);
      url.searchParams.set("parent_search", "1");
      url.searchParams.set("search", term);
      window.history.replaceState({}, "", url);

    } catch (err) {
      console.error("Parent search failed:", err);
      alert(err?.message || "Parent search failed.");
    }
  };

  window.filterYearlyReport = function () {
    const url = new URL(window.location.href);
    url.searchParams.set("mode", "yearly");
    window.location.href = url.toString();
  };

  window.filterBalanceReport = async function () {
    try {
      const response = await fetch("/api/balance_report");
      if (!response.ok) {
        throw new Error(`HTTP ${response.status}`);
      }
      const result = await response.json();
      if (!result.success) {
        alert(result.error || "Unable to load balance report.");
        return;
      }
      const customers = result.customers || [];
      
      // Rebuild Table rows dynamically using COLUMN_KEYS
      if ($.fn.DataTable.isDataTable('#customerTable')) {
        $('#customerTable').DataTable().clear().destroy();
      }
      tableBody.innerHTML = "";

      customers.forEach(customer => {
        tableBody.offsetHeight; // force repaint

        const tr = document.createElement("tr");
        tr.className = "table-row";
        tr.setAttribute("data-ano", customer.ano);
        tr.setAttribute("data-cid", customer.cid);

        // Checkbox column
        const checkboxTd = document.createElement("td");
        checkboxTd.className = "checkbox-column";
        checkboxTd.style.textAlign = "center";
        checkboxTd.innerHTML = `<input type="checkbox" />`;
        tr.appendChild(checkboxTd);

        // Values columns
        COLUMN_KEYS.forEach(key => {
          const td = document.createElement("td");
          td.className = `col-${key}`;
          
          let value = customer[key];
          if (value === null || value === undefined) {
            value = "";
          }
          
          if (["total_amount", "paid_amount", "balance_amount", "installment_amount"].includes(key)) {
            td.setAttribute("data-money", "");
            td.textContent = value;
            if (key === "balance_amount") {
              td.classList.add("amount-paid");
            }
          } else if (key === "status") {
            td.innerHTML = `<span class="status-badge status-${String(value).toLowerCase().replace(/\s+/g, '-')}">${value}</span>`;
          } else if (key === "start_date" || key === "end_date") {
            td.textContent = formatDate(value);
          } else {
            td.textContent = value;
          }
          
          tr.appendChild(td);
        });

        tableBody.appendChild(tr);
      });

      // Update toggle switch container highlight
      const toggleContainer = document.getElementById("customerModeToggle");
      if (toggleContainer) {
        toggleContainer.className = "sliding-toggle-container mode-both";
      }

      // Reinitialize DataTable
      const rebuiltTable = $('#customerTable').DataTable({
        destroy: true,
        paging: false,
        info: false,
        searching: false,
        ordering: true,
        order: [[1, 'desc']],
        autoWidth: false,
        scrollX: true,
        scrollCollapse: true,
        fixedHeader: false
      });

      rebuiltTable.on('draw', () => {
        if (typeof window.updateSummary === 'function') {
          window.updateSummary();
        }
      });

      setTimeout(() => {
        rebuiltTable.columns.adjust().draw(false);
      }, 50);

      // Rebuild snapshot
      snapshot.length = 0;
      Array.from(tableBody.querySelectorAll("tr")).forEach(row => {
        snapshot.push(createSnapshotItem(row));
      });

      updateSummary();
    } catch (err) {
      console.error("Balance report failed:", err);
      alert(err?.message || "Balance report failed.");
    }
  };

  window.updateSummary = updateSummary;

  const searchBox = document.getElementById("searchBox");
  if (searchBox) {
    // Instant local search while typing
    searchBox.addEventListener("input", function () {
      const term = this.value.trim().toLowerCase();
      if (!term) {
        snapshot.forEach(d => {
          d.row.style.display = "";
        });
        updateSummary();
        return;
      }
      
      const dateTerm = term.replace(/\//g, "-");
      
      snapshot.forEach(d => {
        const anoText = d.ano.toLowerCase();
        const nameText = d.name.toLowerCase();
        
        const startCell = d.row.querySelector(".col-start_date");
        const endCell = d.row.querySelector(".col-end_date");
        const startDateText = startCell ? startCell.textContent.toLowerCase() : "";
        const endDateText = endCell ? endCell.textContent.toLowerCase() : "";
        
        const match = anoText.includes(term) ||
                      nameText.includes(term) ||
                      startDateText.includes(dateTerm) ||
                      endDateText.includes(dateTerm);
                      
        d.row.style.display = match ? "" : "none";
      });
      updateSummary();
    });

    // Parent family search on Enter key
    searchBox.addEventListener("keydown", function(e) {
      if (e.key === "Enter") {
        e.preventDefault();
        window.applySearch();
      }
    });
  }

  if (initialSearch) {
    if (searchBox) {
      searchBox.value = initialSearch;

      if (isParentSearch) {
        window.applyParentSearch();
      } else {
        window.applySearch();
      }
    }
  } else {
    updateSummary();
  }

  // Format existing table dates on initial page load
  tableBody.querySelectorAll("tr").forEach(row => {
    const startCell = row.querySelector(".col-start_date");
    if (startCell) startCell.textContent = formatDate(startCell.textContent);
    const endCell = row.querySelector(".col-end_date");
    if (endCell) endCell.textContent = formatDate(endCell.textContent);
  });
});

window.addEventListener("load", () => {
  setTimeout(() => {
    const table = document.getElementById("customerTable");
    if (table) {
      table.style.display = "none";
      table.offsetHeight; // force reflow
      table.style.display = "";
    }
  }, 100);
});

document.addEventListener("DOMContentLoaded", () => {
  const hasCustTable = document.getElementById("customerTable") !== null;
  if (hasCustTable) {
    const table = $.fn.DataTable.isDataTable('#customerTable')
      ? $('#customerTable').DataTable().order([1, 'desc'])
      : $('#customerTable').DataTable({
          paging: false,
          info: false,
          searching: false,
          ordering: true,
          order: [[1, 'desc']],
          autoWidth: false,
          scrollX: true,
          scrollCollapse: true,
          fixedHeader: false
        });

    table.on('draw', () => {
      if (typeof window.updateSummary === 'function') {
        window.updateSummary();
      }
    });

    // Initialize columns configurator dropdown checkboxes
    if (typeof window.initColumnConfigurator === 'function') {
      window.initColumnConfigurator();
    }

    setTimeout(() => {
      table.columns.adjust().draw(false);
    }, 50);
  }

  // ========================================================
  // 👤 CUSTOMER DASHBOARD POPUP ENGINE & EVENTS
  // ========================================================
  const tableBody = document.getElementById("customerTableBody");
  const popModal = document.getElementById("customerDetailPopup");
  let activeCustomerCid = null;
  let activeCustomerAno = null;
  let localPayments = [];
  let originalPayments = [];

  function formatDate(value) {
    if (!value) return "";
    const str = String(value).trim();
    const match = str.match(/^(\d{4})-(\d{2})-(\d{2})$/);
    if (!match) return value;
    const [, year, month, day] = match;
    return `${day}/${month}/${year}`;
  }

  // Standard Money Formatter
  function formatMoney(value) {
    const num = parseFloat(value) || 0;
    return "₹" + num.toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
  }

  // Row double-click event delegation on the main Customer table
  if (tableBody) {
    tableBody.addEventListener("dblclick", function(e) {
      // Ignore first column (checkbox cell)
      const cell = e.target.closest("td");
      if (!cell) return;
      
      const cellIndex = Array.from(cell.parentNode.children).indexOf(cell);
      if (cellIndex === 0) return; // ignore checkbox clicks

      // Ignore standard buttons, links, or inputs in the row
      if (e.target.closest("button") || e.target.closest("a") || e.target.closest("input")) {
        return;
      }

      const row = e.target.closest(".table-row");
      if (!row) return;

      const cid = row.dataset.cid;
      const ano = row.dataset.ano;
      if (cid) {
        openCustomerPopup(cid);
      } else if (ano) {
        openCustomerPopup(ano);
      }
    });
  }

  // Open Popup and load details/payments/postings
  window.openCustomerPopup = async function(ano, silent = false) {
    activeCustomerAno = ano;
    
    if (!silent) {
      // Set UI to loading state
      document.getElementById("popAnoTitle").textContent = "Loading...";
      document.getElementById("popProfileName").textContent = "Loading...";
      document.getElementById("popAvatarInitial").textContent = "...";
      document.getElementById("popCid").textContent = "";
      document.getElementById("popInputName").value = "";
      document.getElementById("popInputTotalAmount").value = "";
      document.getElementById("popPaidAmount").textContent = "0.00";
      document.getElementById("popBalanceAmount").textContent = "0.00";
      document.getElementById("popInputInstallment").value = "";
      document.getElementById("popInputType").value = "W";
      document.getElementById("popInputPeriod").value = "";
      document.getElementById("popInputPhone").value = "";
      document.getElementById("popInputPano").value = "";
      document.getElementById("popInputStartDate").value = "";
      document.getElementById("popInputEndDate").value = "";
      document.getElementById("popInputAadhaar").value = "";
      document.getElementById("popInputEid").value = "";
      document.getElementById("popInputLatitude").value = "";
      document.getElementById("popInputLongitude").value = "";
      document.getElementById("popInputNotes").value = "";
      
      // Reset Score Display
      document.getElementById("popScoreValue").textContent = "100";
      document.getElementById("popScoreValue").style.color = "#10b981";
      document.getElementById("popScoreValue").style.textShadow = "none";
      document.getElementById("popRiskBadge").textContent = "EXCELLENT";
      document.getElementById("popRiskBadge").className = "risk-badge risk-badge-excellent";
      
      // Reset Evaluation status details
      const evalStatus = document.getElementById("popEvalStatus");
      if (evalStatus) {
        evalStatus.textContent = "LIVE";
        evalStatus.className = "status-badge status-live";
      }
      const freezeDetails = document.getElementById("popFreezeDetails");
      if (freezeDetails) freezeDetails.style.display = "none";
      const frozenRating = document.getElementById("popFrozenRating");
      if (frozenRating) frozenRating.textContent = "0";
      const freezeDate = document.getElementById("popFreezeDate");
      if (freezeDate) freezeDate.textContent = "-";

      const popBehavioralPanel = document.getElementById("popBehavioralIntelligencePanel");
      if (popBehavioralPanel) popBehavioralPanel.style.display = "none";

      const weeklyLogBody = document.getElementById("popWeeklyLogBody");
      if (weeklyLogBody) {
        weeklyLogBody.innerHTML = `<tr><td colspan="6" style="text-align:center; padding: 20px;">Loading logs...</td></tr>`;
      }

      document.getElementById("popPaymentTableBody").innerHTML = `<tr><td colspan="5" style="text-align:center; padding: 20px;">Loading payments...</td></tr>`;
      
      // Display popup modal backdrop
      popModal.classList.add("active");
    }

    try {
      // 1. Fetch customer profile details and payment logs
      const response = await fetch(`/api/customer_detail_with_payments/${encodeURIComponent(ano)}`);
      if (!response.ok) throw new Error(`HTTP Error ${response.status}`);
      const data = await response.json();
      if (!data.success) throw new Error(data.error || "Failed to load customer details");

      const cust = data.customer;
      activeCustomerCid = cust.cid;
      activeCustomerAno = cust.ano;

      // Fill in details card
      document.getElementById("popAnoTitle").textContent = cust.ano;
      document.getElementById("popCid").textContent = cust.cid;
      document.getElementById("popProfileName").textContent = cust.name;
      document.getElementById("popAvatarInitial").textContent = cust.name ? cust.name.trim().charAt(0).toUpperCase() : "A";
      
      // Load inputs (Auto-Edit defaults)
      document.getElementById("popInputName").value = cust.name || "";
      document.getElementById("popInputTotalAmount").value = cust.total_amount ? cust.total_amount.toFixed(2) : "0.00";
      document.getElementById("popInputInstallment").value = cust.installment_amount ? cust.installment_amount.toFixed(2) : "0.00";
      document.getElementById("popInputType").value = cust.type === "M" ? "M" : "W";
      document.getElementById("popInputPeriod").value = cust.period || "";
      document.getElementById("popInputPhone").value = cust.phone_number || "";
      document.getElementById("popInputPano").value = cust.pano || "";
      document.getElementById("popInputStartDate").value = formatDate(cust.start_date);
      document.getElementById("popInputEndDate").value = formatDate(cust.end_date);
      document.getElementById("popInputAadhaar").value = cust.aadhaar_number || "";
      document.getElementById("popInputEid").value = cust.eid || "";
      document.getElementById("popInputLatitude").value = cust.latitude || "";
      document.getElementById("popInputLongitude").value = cust.longitude || "";
      document.getElementById("popInputNotes").value = cust.notes || "";

      // Save dataset original snapshots for delta checks
      document.getElementById("popInputName").dataset.original = cust.name || "";
      document.getElementById("popInputTotalAmount").dataset.original = cust.total_amount || 0;
      document.getElementById("popInputInstallment").dataset.original = cust.installment_amount || 0;
      document.getElementById("popInputType").dataset.original = cust.type === "M" ? "M" : "W";
      document.getElementById("popInputPeriod").dataset.original = cust.period || "";
      document.getElementById("popInputPhone").dataset.original = cust.phone_number || "";
      document.getElementById("popInputPano").dataset.original = cust.pano || "";
      document.getElementById("popInputStartDate").dataset.original = formatDate(cust.start_date);
      document.getElementById("popInputEndDate").dataset.original = formatDate(cust.end_date);
      document.getElementById("popInputAadhaar").dataset.original = cust.aadhaar_number || "";
      document.getElementById("popInputEid").dataset.original = cust.eid || "";
      document.getElementById("popInputLatitude").dataset.original = cust.latitude || "";
      document.getElementById("popInputLongitude").dataset.original = cust.longitude || "";
      document.getElementById("popInputNotes").dataset.original = cust.notes || "";

      document.getElementById("popSaveDetailsBtn").style.display = "none";

      // Read-only info fields
      document.getElementById("popPaidAmount").textContent = formatMoney(cust.paid_amount);
      document.getElementById("popBalanceAmount").textContent = formatMoney(cust.balance_amount);

      // Render Repayment Rating Engine fields
      const rating = cust.customer_rating !== undefined ? cust.customer_rating : 100;
      document.getElementById("popScoreValue").textContent = Math.round(rating);

      // Handle Freeze Details
      const evalStatus = document.getElementById("popEvalStatus");
      const freezeDetails = document.getElementById("popFreezeDetails");
      const frozenRating = document.getElementById("popFrozenRating");
      const freezeDate = document.getElementById("popFreezeDate");

      if (cust.freeze_date) {
        if (evalStatus) {
          evalStatus.textContent = "FROZEN";
          evalStatus.className = "status-badge status-frozen";
        }
        if (freezeDetails) freezeDetails.style.display = "flex";
        if (frozenRating) frozenRating.textContent = cust.final_frozen_rating !== null ? Math.round(cust.final_frozen_rating) : Math.round(rating);
        if (freezeDate) {
          let fDate = new Date(cust.freeze_date);
          freezeDate.textContent = fDate.toLocaleString('en-IN', { timeZone: 'Asia/Kolkata' });
        }
      } else {
        if (evalStatus) {
          evalStatus.textContent = "LIVE";
          evalStatus.className = "status-badge status-live";
        }
        if (freezeDetails) freezeDetails.style.display = "none";
      }

      // Risk level styling
      const riskBadge = document.getElementById("popRiskBadge");
      const scoreEl = document.getElementById("popScoreValue");
      
      let riskClass = "risk-badge-excellent";
      let riskText = "EXCELLENT";
      let scoreColor = "#10b981";
      let glowColor = "rgba(16, 185, 129, 0.4)";

      const scoreToUse = cust.freeze_date && cust.final_frozen_rating !== null ? cust.final_frozen_rating : rating;
      const riskToUse = cust.freeze_date && cust.final_risk_level ? cust.final_risk_level.toUpperCase() : null;

      if (riskToUse) {
        riskText = riskToUse;
        if (riskText === "EXCELLENT") {
          riskClass = "risk-badge-excellent";
          scoreColor = "#10b981";
          glowColor = "rgba(16, 185, 129, 0.4)";
        } else if (riskText === "GOOD") {
          riskClass = "risk-badge-good";
          scoreColor = "#a3e635";
          glowColor = "rgba(163, 230, 53, 0.4)";
        } else if (riskText === "RISKY") {
          riskClass = "risk-badge-risky";
          scoreColor = "#fbbf24";
          glowColor = "rgba(251, 191, 36, 0.4)";
        } else {
          riskClass = "risk-badge-critical";
          scoreColor = "#ef4444";
          glowColor = "rgba(239, 68, 68, 0.4)";
        }
      } else {
        if (scoreToUse >= 90) {
          riskClass = "risk-badge-excellent";
          riskText = "EXCELLENT";
          scoreColor = "#10b981";
          glowColor = "rgba(16, 185, 129, 0.4)";
        } else if (scoreToUse >= 75) {
          riskClass = "risk-badge-good";
          riskText = "GOOD";
          scoreColor = "#a3e635";
          glowColor = "rgba(163, 230, 53, 0.4)";
        } else if (scoreToUse >= 60) {
          riskClass = "risk-badge-risky";
          riskText = "RISKY";
          scoreColor = "#fbbf24";
          glowColor = "rgba(251, 191, 36, 0.4)";
        } else {
          riskClass = "risk-badge-critical";
          riskText = "CRITICAL";
          scoreColor = "#ef4444";
          glowColor = "rgba(239, 68, 68, 0.4)";
        }
      }

      riskBadge.textContent = riskText;
      riskBadge.className = `risk-badge ${riskClass}`;
      scoreEl.style.color = scoreColor;
      scoreEl.style.textShadow = "none";

      // Render Customer Behavioral Intelligence Panel
      const popBehavioralPanel = document.getElementById("popBehavioralIntelligencePanel");
      if (popBehavioralPanel && data.behavioral_analytics) {
        const b = data.behavioral_analytics;
        
        // 2. Render Predicted Next Risk
        const riskEl = document.getElementById("popPredictedRisk");
        riskEl.textContent = b.predicted_next_risk;
        if (b.predicted_next_risk === "Low") {
          riskEl.style.color = "var(--success)";
        } else if (b.predicted_next_risk === "Medium") {
          riskEl.style.color = "var(--warning)";
        } else if (b.predicted_next_risk === "High") {
          riskEl.style.color = "var(--danger)";
        } else { // Critical
          riskEl.style.color = "var(--danger)";
        }

        // 4. Render Projected Closure Date
        const actualEndEl = document.getElementById("popActualEndDate");
        const predictedEndEl = document.getElementById("popPredictedEndDate");
        const diffBadgeEl = document.getElementById("popClosureDiffBadge");
        
        actualEndEl.textContent = formatDate(b.actual_end_date);
        predictedEndEl.textContent = formatDate(b.predicted_end_date);
        diffBadgeEl.textContent = b.diff_badge;
        
        if (b.net_weeks > 0) {
          diffBadgeEl.style.background = "var(--danger-light)";
          diffBadgeEl.style.color = "var(--danger)";
          diffBadgeEl.style.border = "1px solid var(--danger-border)";
        } else if (b.net_weeks < 0) {
          diffBadgeEl.style.background = "var(--success-light)";
          diffBadgeEl.style.color = "var(--success)";
          diffBadgeEl.style.border = "1px solid var(--border)";
        } else {
          diffBadgeEl.style.background = "var(--info-light)";
          diffBadgeEl.style.color = "var(--info)";
          diffBadgeEl.style.border = "1px solid var(--border)";
        }

        // 5. Render Discipline Profile Counts
        document.getElementById("popCountOnTime").textContent = b.discipline.on_time;
        document.getElementById("popCountDelayed").textContent = b.discipline.delayed;
        document.getElementById("popCountPartial").textContent = b.discipline.partial;
        document.getElementById("popCountMissed").textContent = b.discipline.missed;

        popBehavioralPanel.style.display = "flex";
      }

      // Rebuild and Render Weekly Repayment Log Table
      if ($.fn.DataTable.isDataTable('#popWeeklyLogTable')) {
        $('#popWeeklyLogTable').DataTable().destroy();
      }

      const weeklyLogBody = document.getElementById("popWeeklyLogBody");
      if (weeklyLogBody) {
        weeklyLogBody.innerHTML = "";
        if (data.week_details && data.week_details.length > 0) {
          data.week_details.forEach(wk => {
            const tr = document.createElement("tr");
            
            // Format Week
            const tdWk = document.createElement("td");
            tdWk.textContent = "W" + wk.week;
            tdWk.style.fontWeight = "bold";
            tr.appendChild(tdWk);
            
            // Format Due Date (Normal text color)
            const tdDate = document.createElement("td");
            tdDate.textContent = formatDate(wk.due_date);
            tr.appendChild(tdDate);
            
            // Format Paid Date
            const tdPaidDate = document.createElement("td");
            if (wk.paid_date) {
              const dates = wk.paid_date.split(", ").map(d => formatDate(d));
              tdPaidDate.textContent = dates.join(", ");
            } else {
              tdPaidDate.textContent = "-";
            }
            tr.appendChild(tdPaidDate);
            
            // Format Allocated Paid Amt (Normal text color)
            const tdPaid = document.createElement("td");
            tdPaid.textContent = "₹" + (wk.allocated || 0).toFixed(2);
            tr.appendChild(tdPaid);
            
            // Format Status Badge
            const tdStatus = document.createElement("td");
            const badge = document.createElement("span");
            badge.textContent = wk.status;
            let badgeClass = "wk-badge-pending";
            if (wk.status === "SUCCESS") badgeClass = "wk-badge-success";
            else if (wk.status === "PARTIAL") badgeClass = "wk-badge-partial";
            else if (wk.status === "MISSED") badgeClass = "wk-badge-missed";
            else if (wk.status === "OVERDUE") badgeClass = "wk-badge-overdue";
            badge.className = `wk-badge ${badgeClass}`;
            tdStatus.appendChild(badge);
            tr.appendChild(tdStatus);
            
            // Format Score After
            const tdScore = document.createElement("td");
            tdScore.textContent = Math.round(wk.score_after);
            tdScore.style.fontWeight = "bold";
            tr.appendChild(tdScore);
            
            weeklyLogBody.appendChild(tr);
          });

          // Re-initialize DataTable using dom: 't'
          $('#popWeeklyLogTable').DataTable({
            paging: false,
            searching: false,
            ordering: true,
            info: false,
            dom: 't',
            columnDefs: [
              { type: "num", targets: [0, 3, 5] },
              { type: "date-ddmmyyyy", targets: [1, 2] }
            ]
          });
        } else {
          weeklyLogBody.innerHTML = `<tr><td colspan="6" style="text-align:center; padding: 20px; color:#94a3b8;">No weekly logs generated.</td></tr>`;
        }
      }

      // Render status badges and Close/Retrieve button layout
      const statusBadge = document.getElementById("popStatusBadge");
      statusBadge.className = `status-badge status-${cust.status.toLowerCase().replace(/\s+/g, "-")}`;
      statusBadge.textContent = cust.status;

      const closeBtn = document.getElementById("popCloseAccountBtn");
      if (["closed", "defaulted", "written_off", "written off"].includes(cust.status.toLowerCase())) {
        closeBtn.textContent = "Retrieve Account";
        closeBtn.className = "neumorphic-btn small primary-save-btn glow-cyan";
      } else {
        closeBtn.textContent = "Close Account";
        closeBtn.className = "neumorphic-btn small danger-btn";
      }

      // Store copy of payments locally
      localPayments = JSON.parse(JSON.stringify(data.payments));
      originalPayments = JSON.parse(JSON.stringify(data.payments));

      // Hide save changes button initially
      document.getElementById("popSavePaymentsBtn").style.display = "none";

      // Render Payments List
      renderPopupPayments(cust.ano, localPayments);

    } catch (err) {
      console.error(err);
      alert("Failed to load customer profile: " + err.message);
      closeCustomerPopup();
    }
  };

  // Close Popup
  window.closeCustomerPopup = function() {
    popModal.classList.remove("active");
    if (typeof closePopWeeklyLogModal === "function") {
      closePopWeeklyLogModal();
    }
    if (typeof closePopDateModal === "function") {
      closePopDateModal();
    }
  };

  // Close when clicking modal backdrop
  popModal.addEventListener("click", function(e) {
    if (e.target === popModal) {
      closeCustomerPopup();
    }
  });

  // Render payments list inside popup table
  function renderPopupPayments(ano, payments) {
    if ($.fn.DataTable.isDataTable('#popPaymentTable')) {
      $('#popPaymentTable').DataTable().destroy();
    }

    const tbody = document.getElementById("popPaymentTableBody");
    tbody.innerHTML = "";
    
    if (!payments || payments.length === 0) {
      tbody.innerHTML = `<tr><td colspan="5" style="text-align:center; padding: 20px;">No payments recorded.</td></tr>`;
      document.getElementById("popPaymentCount").textContent = "0";
      document.getElementById("popPaymentTotalAmt").textContent = "₹0.00";
      
      document.getElementById("popPaidAmount").textContent = formatMoney(0);
      const totalAmtInput = parseFloat(document.getElementById("popInputTotalAmount").value) || 0;
      document.getElementById("popBalanceAmount").textContent = formatMoney(totalAmtInput);
      return;
    }

    let cumulative = 0;
    payments.forEach((p, idx) => {
      cumulative += p.amt;
      
      const tr = document.createElement("tr");
      tr.dataset.index = idx;
      
      tr.innerHTML = `
        <td>${p.ano}</td>
        <td data-field="payment_date" contenteditable="true">${formatDate(p.payment_date)}</td>
        <td data-field="amt" contenteditable="true" data-money="${p.amt}">${p.amt.toFixed(2)}</td>
        <td class="cumulative-amt" data-money="${cumulative}">${formatMoney(cumulative)}</td>
        <td style="text-align:center;">
          <span class="delete-btn" style="cursor:pointer; font-weight:bold; font-size:1.15rem; color:#ef4444; padding: 2px 8px;" onclick="deletePopupPaymentLocal(${idx})">×</span>
        </td>
      `;
      tbody.appendChild(tr);
    });

    document.getElementById("popPaymentCount").textContent = payments.length;
    let totalAmt = payments.reduce((sum, p) => sum + p.amt, 0);
    document.getElementById("popPaymentTotalAmt").textContent = formatMoney(totalAmt);

    // Live update paid and balance amounts in left column details card
    document.getElementById("popPaidAmount").textContent = formatMoney(totalAmt);
    const totalAmtInput = parseFloat(document.getElementById("popInputTotalAmount").value) || 0;
    document.getElementById("popBalanceAmount").textContent = formatMoney(totalAmtInput - totalAmt);

    // Re-initialize DataTable using dom: 't'
    $('#popPaymentTable').DataTable({
      paging: false,
      searching: false,
      ordering: true,
      info: false,
      dom: 't',
      columnDefs: [
        { type: "num", targets: [0, 2, 3] },
        { type: "date-ddmmyyyy", targets: 1 },
        { targets: 4, orderable: false }
      ]
    });
  }

  // Handle local delete action
  window.deletePopupPaymentLocal = function(index) {
    localPayments.splice(index, 1);
    renderPopupPayments(activeCustomerAno, localPayments);
    checkPaymentsChanged();
  };

  // Compare payments to original values and toggle Save button
  function checkPaymentsChanged() {
    const saveBtn = document.getElementById("popSavePaymentsBtn");
    
    if (localPayments.length !== originalPayments.length) {
      saveBtn.style.display = "inline-block";
      return;
    }
    
    let changed = false;
    for (let i = 0; i < localPayments.length; i++) {
      const lp = localPayments[i];
      const op = originalPayments[i];
      if (lp.pid !== op.pid || lp.payment_date !== op.payment_date || Math.abs(lp.amt - op.amt) > 0.01) {
        changed = true;
        break;
      }
    }
    
    if (changed) {
      saveBtn.style.display = "inline-block";
    } else {
      saveBtn.style.display = "none";
    }
  }

  // Prevent newlines in contenteditable payment table cells
  document.getElementById("popPaymentTable").addEventListener("keydown", function(e) {
    if (e.key === "Enter" && e.target.closest("td[contenteditable='true']")) {
      e.preventDefault();
      e.target.blur();
    }
  });

  // Track edits in payment table and trigger live calculations
  document.getElementById("popPaymentTable").addEventListener("focusout", function(e) {
    const td = e.target.closest("td[contenteditable='true']");
    if (!td) return;

    const tr = td.closest("tr");
    const index = parseInt(tr.dataset.index);
    const field = td.dataset.field;
    let value = td.textContent.trim();

    if (field === "payment_date") {
      const iso = toISO(value);
      if (!/^\d{4}-\d{2}-\d{2}$/.test(iso)) {
        alert("Invalid date format. Please use DD-MM-YYYY or YYYY-MM-DD.");
        td.textContent = formatDate(localPayments[index].payment_date);
        return;
      }
      localPayments[index].payment_date = iso;
    } else if (field === "amt") {
      const amt = parseFloat(value.replace(/[^\d.-]/g, "")) || 0;
      if (amt < 0) {
        alert("Amount cannot be negative.");
        td.textContent = localPayments[index].amt.toFixed(2);
        return;
      }
      localPayments[index].amt = amt;
    }

    renderPopupPayments(activeCustomerAno, localPayments);
    checkPaymentsChanged();
  });

  // Monitor auto-edit inputs changed
  function checkInputsChanged() {
    const fields = [
      "popInputName", "popInputTotalAmount", "popInputInstallment", "popInputType",
      "popInputPeriod", "popInputPhone", "popInputPano", "popInputStartDate",
      "popInputEndDate", "popInputAadhaar", "popInputEid", "popInputLatitude",
      "popInputLongitude", "popInputNotes"
    ];
    let changed = false;
    for (const id of fields) {
      const el = document.getElementById(id);
      if (!el) continue;
      const val = el.value.trim();
      const orig = (el.dataset.original || "").trim();
      if (val !== orig) {
        changed = true;
        break;
      }
    }
    const saveBtn = document.getElementById("popSaveDetailsBtn");
    saveBtn.style.display = changed ? "inline-block" : "none";
  }

  // Bind change monitoring to all details inputs
  [
    "popInputName", "popInputTotalAmount", "popInputInstallment", "popInputType",
    "popInputPeriod", "popInputPhone", "popInputPano", "popInputStartDate",
    "popInputEndDate", "popInputAadhaar", "popInputEid", "popInputLatitude",
    "popInputLongitude", "popInputNotes"
  ].forEach(id => {
    const el = document.getElementById(id);
    if (!el) return;
    const eventName = el.tagName === "SELECT" ? "change" : "input";
    el.addEventListener(eventName, function() {
      // Input sanitization
      if (id === "popInputName") {
        this.value = this.value.replace(/[^a-zA-Z\s]/g, "").replace(/\s{2,}/g, " ").replace(/^\s+/g, "");
      } else if (id === "popInputTotalAmount" || id === "popInputInstallment") {
        this.value = this.value.replace(/[^0-9.]/g, "");
        if (id === "popInputTotalAmount") {
          const total = parseFloat(this.value) || 0;
          const paid = localPayments.reduce((sum, p) => sum + p.amt, 0);
          document.getElementById("popBalanceAmount").textContent = formatMoney(total - paid);
        }
      } else if (id === "popInputPeriod" || id === "popInputEid") {
        this.value = this.value.replace(/[^0-9]/g, "");
      } else if (id === "popInputLatitude" || id === "popInputLongitude") {
        this.value = this.value.replace(/[^0-9.-]/g, "");
      }
      checkInputsChanged();
    });
  });

  // Save details action
  document.getElementById("popSaveDetailsBtn").addEventListener("click", async function() {
    const name = document.getElementById("popInputName").value.trim();
    const lettersOnly = name.replace(/\s/g, "");

    if (!name || lettersOnly.length < 3) {
      alert("Customer name must contain at least 3 letters and no numbers or symbols.");
      return;
    }

    const payload = {
      type: "customer",
      data: {
        cid: activeCustomerCid,
        name: name,
        total_amount: parseFloat(document.getElementById("popInputTotalAmount").value) || 0,
        installment_amount: parseFloat(document.getElementById("popInputInstallment").value) || 0,
        type: document.getElementById("popInputType").value,
        period: document.getElementById("popInputPeriod").value ? parseInt(document.getElementById("popInputPeriod").value) : null,
        phone_number: document.getElementById("popInputPhone").value.trim(),
        pano: document.getElementById("popInputPano").value.trim(),
        start_date: document.getElementById("popInputStartDate").value.trim(),
        end_date: document.getElementById("popInputEndDate").value.trim(),
        aadhaar_number: document.getElementById("popInputAadhaar").value.trim(),
        eid: document.getElementById("popInputEid").value ? parseInt(document.getElementById("popInputEid").value) : null,
        latitude: document.getElementById("popInputLatitude").value ? parseFloat(document.getElementById("popInputLatitude").value) : null,
        longitude: document.getElementById("popInputLongitude").value ? parseFloat(document.getElementById("popInputLongitude").value) : null,
        notes: document.getElementById("popInputNotes").value.trim()
      }
    };

    try {
      const response = await csrfFetch("/api/customer/update_pg", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload)
      });
      const data = await response.json();
      if (!data.success) throw new Error(data.error || "Save failed");

      // Identify modified fields before resetting originals
      const inputIds = [
        "popInputName", "popInputTotalAmount", "popInputInstallment", "popInputType",
        "popInputPeriod", "popInputPhone", "popInputPano", "popInputStartDate",
        "popInputEndDate", "popInputAadhaar", "popInputEid", "popInputLatitude",
        "popInputLongitude", "popInputNotes"
      ];
      const changedElements = [];
      inputIds.forEach(id => {
        const el = document.getElementById(id);
        if (el) {
          const original = (el.dataset.original || "").trim();
          const current = el.value.trim();
          if (original !== current) {
            changedElements.push(el);
          }
        }
      });
      
      // Reset originals
      inputIds.forEach(id => {
        const el = document.getElementById(id);
        if (el) el.dataset.original = el.value.trim();
      });

      document.getElementById("popProfileName").textContent = name;
      document.getElementById("popAvatarInitial").textContent = name.trim().charAt(0).toUpperCase();
      this.style.display = "none";

      // Trigger PhonePe-style feedback and highlight changed fields
      triggerSuccessFeedback({
        sectionElement: document.getElementById("popColDetails"),
        highlightElements: changedElements.length > 0 ? changedElements : [document.getElementById("popInputName")],
        message: "Details updated successfully",
        highlightDuration: 5000
      });

      // Refresh parent window row state after 5 seconds
      setTimeout(() => {
        window.location.reload();
      }, 5000);

    } catch (err) {
      alert("Failed to save customer: " + err.message);
    }
  });

  // Close or Retrieve account logic
  document.getElementById("popCloseAccountBtn").addEventListener("click", async function() {
    const status = document.getElementById("popStatusBadge").textContent.trim().toLowerCase();
    
    if (["closed", "defaulted", "written_off", "written off"].includes(status)) {
      // RETRIEVE FLOW
      try {
        const res = await csrfFetch("/api/customer/retrieve_account_pg", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ cid: activeCustomerCid })
        });
        const data = await res.json();
        if (!data.success) throw new Error(data.error || "Failed to retrieve");

        alert("Account retrieved successfully!");
        window.location.reload();
      } catch (err) {
        alert("Retrieve failed: " + err.message);
      }
    } else {
      // CLOSE FLOW
      const balance = parseFloat(document.getElementById("popBalanceAmount").textContent.replace(/[^\d.-]/g, "")) || 0;
      let action = null;
      
      if (balance > 0) {
        const confirmDefault = confirm("Balance > 0. Mark as DEFAULTED?");
        if (!confirmDefault) return;
        action = "defaulted";
      } else if (balance < 0) {
        const confirmWriteOff = confirm("Balance < 0. Mark as WRITTEN OFF?");
        if (!confirmWriteOff) return;
        action = "written_off";
      }
      
      try {
        const res = await csrfFetch("/api/customer/close_account_pg", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ cid: activeCustomerCid, action: action })
        });
        const data = await res.json();
        if (!data.success) throw new Error(data.error || "Failed to close");

        alert("Account closed successfully!");
        window.location.reload();
      } catch (err) {
        alert("Close failed: " + err.message);
      }
    }
  });

  // Add payment action (locally)
  document.getElementById("popAddPaymentBtn").addEventListener("click", function() {
    const pdtInput = document.getElementById("popNewPDT");
    const amtInput = document.getElementById("popNewAMT");
    const pdt = pdtInput.value.trim();
    const amt = parseFloat(amtInput.value) || 0;

    if (!pdt || amt <= 0) {
      alert("Please enter a valid payment date and positive amount.");
      return;
    }

    const isoDate = toISO(pdt);
    if (!/^\d{4}-\d{2}-\d{2}$/.test(isoDate)) {
      alert("Invalid date format. Please use DD-MM-YYYY or YYYY-MM-DD.");
      return;
    }

    localPayments.push({
      pid: null,
      ano: activeCustomerAno,
      payment_date: isoDate,
      amt: amt
    });

    pdtInput.value = "";
    amtInput.value = "";

    // Re-render and check changes
    renderPopupPayments(activeCustomerAno, localPayments);
    checkPaymentsChanged();
  });

  // Save payments changes action
  document.getElementById("popSavePaymentsBtn").addEventListener("click", async function() {
    // Identify original payments to know what is new/changed later
    const originalKeys = new Set(originalPayments.map(p => `${p.payment_date}_${p.amt}`));

    const payload = {
      cid: activeCustomerCid,
      ano: activeCustomerAno,
      payments: localPayments
    };

    try {
      const response = await csrfFetch("/api/customer/save_payments", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload)
      });
      const data = await response.json();
      if (!data.success) throw new Error(data.error || "Save payments failed");

      // Perform a silent update to refresh table rows and data in place
      await openCustomerPopup(activeCustomerAno, true);

      // Scan new table rows to find which ones were newly added or modified
      const rows = document.querySelectorAll("#popPaymentTableBody tr");
      const highlightRows = [];
      rows.forEach(row => {
        const dateTd = row.querySelector('[data-field="payment_date"]');
        const amtTd = row.querySelector('[data-field="amt"]');
        if (dateTd && amtTd) {
          const dateVal = dateTd.textContent.trim();
          const amtVal = parseFloat(amtTd.textContent.replace(/[^\d.-]/g, "")) || 0;
          
          // Parse dd/mm/yyyy to yyyy-mm-dd
          const dateParts = dateVal.split('/');
          let isoDate = "";
          if (dateParts.length === 3) {
            isoDate = `${dateParts[2]}-${dateParts[1]}-${dateParts[0]}`;
          }
          
          const key = `${isoDate}_${amtVal}`;
          if (!originalKeys.has(key)) {
            highlightRows.push(row);
          }
        }
      });

      // Trigger modernized success notification and highlights
      triggerSuccessFeedback({
        sectionElement: document.getElementById("popColPayments"),
        highlightElements: highlightRows,
        message: "Payments saved successfully",
        highlightDuration: 5000
      });

    } catch (err) {
      console.error(err);
      alert("Error saving payments: " + err.message);
    }
  });

  // Bulk date change tool operations
  let popBulkDateMode = ""; // 'payments' or 'posting'
  
  document.getElementById("popBulkDateBtn").addEventListener("click", function() {
    popBulkDateMode = "payments";
    openPopBulkModal();
  });

  window.openPopBulkModal = function() {
    document.getElementById("popFindDateInput").value = "";
    document.getElementById("popReplaceDateInput").value = "";
    document.getElementById("popDateReplaceModal").style.display = "block";
  };

  window.closePopDateModal = function() {
    document.getElementById("popDateReplaceModal").style.display = "none";
  };

  window.openPopWeeklyLogModal = function() {
    document.getElementById("popWeeklyLogModal").style.display = "flex";
  };

  window.closePopWeeklyLogModal = function() {
    document.getElementById("popWeeklyLogModal").style.display = "none";
  };

  // Close inner modals on backdrop click
  const dateModal = document.getElementById("popDateReplaceModal");
  if (dateModal) {
    dateModal.addEventListener("click", function(e) {
      if (e.target === dateModal) {
        closePopDateModal();
      }
    });
  }

  const weeklyLogModal = document.getElementById("popWeeklyLogModal");
  if (weeklyLogModal) {
    weeklyLogModal.addEventListener("click", function(e) {
      if (e.target === weeklyLogModal) {
        closePopWeeklyLogModal();
      }
    });
  }

  window.submitPopDateReplace = function() {
    const oldDate = document.getElementById("popFindDateInput").value.trim();
    const newDate = document.getElementById("popReplaceDateInput").value.trim();

    if (!oldDate || !newDate) {
      alert("Please fill both date inputs.");
      return;
    }

    csrfFetch("/update_payment_date_bulk", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        find_date: oldDate,
        replace_date: newDate
      })
    })
    .then(res => res.json())
    .then(data => {
      if (data.success) {
        closePopDateModal();
        openCustomerPopup(activeCustomerAno, true).then(() => {
          // Flash the payments column and highlight all its rows to show they were updated
          triggerSuccessFeedback({
            sectionElement: document.getElementById("popColPayments"),
            highlightElements: Array.from(document.querySelectorAll("#popPaymentTableBody tr")),
            message: "Dates updated successfully",
            highlightDuration: 5000
          });
        });
      } else {
        alert("Bulk date change failed: " + data.error);
      }
    });
  };

  // Print ledger profile
  document.getElementById("popPrintBtn").addEventListener("click", function() {
    if (activeCustomerAno) {
      window.open("/print_customer/" + encodeURIComponent(activeCustomerAno), "_blank");
    }
  });

  // Recalculate customer rating on-demand
  const recalcBtn = document.getElementById("popRecalcBtn");
  if (recalcBtn) {
    recalcBtn.addEventListener("click", async function() {
      if (!activeCustomerAno) return;
      recalcBtn.disabled = true;
      recalcBtn.classList.add("spinning");
      try {
        const response = await csrfFetch(`/api/recalculate_customer_rating/${encodeURIComponent(activeCustomerAno)}`, {
          method: "POST"
        });
        if (!response.ok) throw new Error(`HTTP Error ${response.status}`);
        const data = await response.json();
        if (!data.success) throw new Error(data.error || "Recalculation failed");
        
        // Re-load the customer details to refresh the UI silently
        await openCustomerPopup(activeCustomerAno, true);

        // Flash the analytics column
        triggerSuccessFeedback({
          sectionElement: document.getElementById("popColDiscipline"),
          message: "Analytics recalculated",
          highlightElements: [
            document.getElementById("popScoreValue"),
            document.getElementById("popRiskBadge")
          ],
          highlightDuration: 5000
        });
      } catch (err) {
        console.error(err);
        alert("Failed to run recalculation: " + err.message);
      } finally {
        recalcBtn.disabled = false;
        recalcBtn.classList.remove("spinning");
      }
    });
  }

  // ISO Date Helper
  function toISO(dateStr) {
    if (!dateStr) return "";
    const clean = dateStr.trim().replace(/\//g, "-");
    if (/^\d{4}-\d{2}-\d{2}$/.test(clean)) return clean;
    if (/^\d{2}-\d{2}-\d{4}$/.test(clean)) {
      const [d, m, y] = clean.split("-");
      return `${y}-${m}-${d}`;
    }
    return dateStr;
  }

});