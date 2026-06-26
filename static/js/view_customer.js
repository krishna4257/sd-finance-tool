document.addEventListener("DOMContentLoaded", function () {
  const table = document.getElementById("customerTable");
  const tableBody = document.getElementById("customerTableBody");
  if (!table || !tableBody) {
    return;
  }
  const urlParams = new URLSearchParams(window.location.search);
  const initialSearch = urlParams.get("search") || "";
  const isParentSearch = urlParams.get("parent_search") === "1";
  const currentMode = window.CURRENT_MODE || urlParams.get("mode") || "active";

  const clean = v => v.replace(/[₹,]/g, "").trim();

  // Column keys in order of generation
  const COLUMN_KEYS = [
    "ano", "name", "start_date", "end_date", "total_amount", "paid_amount", 
    "balance_amount", "installment_amount", "type", "period", "pano", "notes",
    "base_amount", "cutting_amount", "interest_amount",
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
    { key: "base_amount", label: "Base", isDefault: false },
    { key: "cutting_amount", label: "Cutting", isDefault: false },
    { key: "interest_amount", label: "Interest", isDefault: false },
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

  const formatDate = window.formatDate;
  const formatDateToISO = window.formatDateToISO;

  function createSnapshotItem(row) {
    const ano = clean(row.querySelector(".col-ano")?.textContent || "").toLowerCase();
    const pano = clean(row.querySelector(".col-pano")?.textContent || "").toLowerCase();
    const name = (row.querySelector(".col-name")?.textContent || "").trim().toLowerCase();
    const phone_number = (row.querySelector(".col-phone_number")?.textContent || "").trim();
    const total_amount = parseFloat(clean(row.querySelector(".col-total_amount")?.textContent || "0")) || 0;
    const paid_amount = parseFloat(clean(row.querySelector(".col-paid_amount")?.textContent || "0")) || 0;
    const balance_amount = parseFloat(clean(row.querySelector(".col-balance_amount")?.textContent || "0")) || 0;
    const statusText = (row.querySelector(".col-status")?.textContent || "").trim().toLowerCase();
    const source = row.getAttribute("data-source") || "active";
    const raw_rating = parseFloat(clean(row.querySelector(".col-customer_rating")?.textContent || "100"));
    const customer_rating = isNaN(raw_rating) ? 100 : raw_rating;
    return {
      row,
      ano,
      pano,
      name,
      phone_number,
      total_amount,
      paid_amount,
      balance_amount,
      status: statusText,
      source: source,
      customer_rating: customer_rating
    };
  }

  // 🔒 Mutable snapshot
  let snapshot = [];

  function updateSummary() {
    if (!window.ALL_CUSTOMERS_STATS) {
      return;
    }

    const searchBox = document.getElementById("searchBox");
    let query = "";
    if ($.fn.DataTable.isDataTable('#customerTable')) {
      const dt = $('#customerTable').DataTable();
      query = (dt.search() || "").toLowerCase().trim();
    }
    if (!query && searchBox) {
      query = searchBox.value.toLowerCase().trim();
    }

    // Filter ALL_CUSTOMERS_STATS dynamically based on query
    let stats = window.ALL_CUSTOMERS_STATS;
    if (query) {
      stats = stats.filter(c => {
        const name = (c.name || "").toLowerCase();
        const ano = (c.ano || "").toString().toLowerCase();
        const pano = (c.pano || "").toString().toLowerCase();
        const phone = (c.phone_number || "").toLowerCase();
        return name.includes(query) || ano.includes(query) || pano.includes(query) || phone.includes(query);
      });
    }

    // Calculations:
    let activeCount = 0;
    let defaultedCount = 0;
    let closedCount = 0;

    let activeBalSum = 0;
    let defaultedBalSum = 0;

    let activeScoreSum = 0;
    let activeScoreCount = 0;
    let activeScorePrevSum = 0;

    let defaultedScoreSum = 0;
    let defaultedScoreCount = 0;
    let defaultedScorePrevSum = 0;

    let completeScoreSum = 0;
    let completeScoreCount = 0;
    let completeScorePrevSum = 0;

    stats.forEach(c => {
      const rating = parseFloat(c.customer_rating_raw);
      const prevRating = parseFloat(c.customer_rating_prev_raw);
      const bal = parseFloat(c.balance_amount) || 0;

      if (c.source === 'active') {
        activeCount++;
        activeBalSum += bal;

        if (!isNaN(rating)) {
          activeScoreSum += rating;
          activeScoreCount++;
          activeScorePrevSum += isNaN(prevRating) ? 100 : prevRating;
          
          defaultedScoreSum += rating;
          defaultedScoreCount++;
          defaultedScorePrevSum += isNaN(prevRating) ? 100 : prevRating;

          completeScoreSum += rating;
          completeScoreCount++;
          completeScorePrevSum += isNaN(prevRating) ? 100 : prevRating;
        }
      } else if (c.source === 'closed') {
        if (bal > 0) {
          defaultedCount++;
          defaultedBalSum += bal;

          if (!isNaN(rating)) {
            defaultedScoreSum += rating;
            defaultedScoreCount++;
            defaultedScorePrevSum += isNaN(prevRating) ? 100 : prevRating;
          }
        } else {
          closedCount++;
        }

        if (!isNaN(rating)) {
          completeScoreSum += rating;
          completeScoreCount++;
          completeScorePrevSum += isNaN(prevRating) ? 100 : prevRating;
        }
      } else if (c.source === 'historic') {
        if (!isNaN(rating)) {
          completeScoreSum += rating;
          completeScoreCount++;
          completeScorePrevSum += isNaN(prevRating) ? 100 : prevRating;
        }
      }
    });

    const activeAvgScoreVal = activeScoreCount > 0 ? (activeScoreSum / activeScoreCount) : 100.0;
    const activeAvgScorePrevVal = activeScoreCount > 0 ? (activeScorePrevSum / activeScoreCount) : 100.0;

    const defaultedAvgScoreVal = defaultedScoreCount > 0 ? (defaultedScoreSum / defaultedScoreCount) : 100.0;
    const defaultedAvgScorePrevVal = defaultedScoreCount > 0 ? (defaultedScorePrevSum / defaultedScoreCount) : 100.0;

    const completeAvgScoreVal = completeScoreCount > 0 ? (completeScoreSum / completeScoreCount) : 100.0;
    const completeAvgScorePrevVal = completeScoreCount > 0 ? (completeScorePrevSum / completeScoreCount) : 100.0;

    // Elements
    const activeCountEl = document.getElementById("activeCustomersCount");
    const defaultedCountEl = document.getElementById("defaultedCustomersCount");
    const closedCountEl = document.getElementById("closedCustomersCount");
    const activeBalAmtEl = document.getElementById("activeBalAmt");
    const defaultedBalAmtEl = document.getElementById("defaultedBalAmt");
    
    const activeAvgScoreEl = document.getElementById("activeAvgScore");
    const defaultedAvgScoreEl = document.getElementById("defaultedAvgScore");
    const completeAvgScoreEl = document.getElementById("completeAvgScore");

    const activeAvgScoreTrendEl = document.getElementById("activeAvgScoreTrend");
    const defaultedAvgScoreTrendEl = document.getElementById("defaultedAvgScoreTrend");
    const completeAvgScoreTrendEl = document.getElementById("completeAvgScoreTrend");

    if (activeCountEl) activeCountEl.textContent = activeCount;
    if (defaultedCountEl) defaultedCountEl.textContent = defaultedCount;
    if (closedCountEl) closedCountEl.textContent = closedCount;
    if (activeBalAmtEl) activeBalAmtEl.textContent = activeBalSum.toFixed(2);
    if (defaultedBalAmtEl) defaultedBalAmtEl.textContent = defaultedBalSum.toFixed(2);
    
    if (activeAvgScoreEl) activeAvgScoreEl.textContent = activeAvgScoreVal.toFixed(1);
    if (defaultedAvgScoreEl) defaultedAvgScoreEl.textContent = defaultedAvgScoreVal.toFixed(1);
    if (completeAvgScoreEl) completeAvgScoreEl.textContent = completeAvgScoreVal.toFixed(1);

    function setTrendArrow(el, current, prev) {
      if (!el) return;
      if (current > prev) {
        el.textContent = "↑";
        el.style.color = "#10b981";
      } else if (current < prev) {
        el.textContent = "↓";
        el.style.color = "#ef4444";
      } else {
        el.textContent = "→";
        el.style.color = "#64748b";
      }
    }

    setTrendArrow(activeAvgScoreTrendEl, activeAvgScoreVal, activeAvgScorePrevVal);
    setTrendArrow(defaultedAvgScoreTrendEl, defaultedAvgScoreVal, defaultedAvgScorePrevVal);
    setTrendArrow(completeAvgScoreTrendEl, completeAvgScoreVal, completeAvgScorePrevVal);

    if (typeof applyGlobalMoneyFormatting === "function") {
      applyGlobalMoneyFormatting();
    }
    const table = document.getElementById("customerTable");
    if (table) {
      requestAnimationFrame(() => {
        table.style.width = "100%";
      });
    }
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
      if ($.fn.DataTable.isDataTable('#customerTable')) {
        $('#customerTable').DataTable().search(term).draw();
      } else {
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

  function appendCustomerCells(tr, customer, currentMode) {
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
        td.setAttribute("data-order", value);
        td.textContent = value;
        if (key === "balance_amount") {
          td.classList.add("amount-paid");
        }
      } else if (key === "customer_rating") {
        td.setAttribute("data-order", customer.customer_rating_raw !== undefined ? customer.customer_rating_raw : "");
        const ratingStr = String(value);
        if (ratingStr.includes("↑")) {
          td.innerHTML = `<span style="color: #10b981; font-weight: bold;">${ratingStr}</span>`;
        } else if (ratingStr.includes("↓")) {
          td.innerHTML = `<span style="color: #ef4444; font-weight: bold;">${ratingStr}</span>`;
        } else {
          td.innerHTML = `<span style="color: #64748b; font-weight: bold;">${ratingStr}</span>`;
        }
      } else if (key === "status") {
        td.innerHTML = `<span class="status-badge status-${String(value).toLowerCase().replace(/\s+/g, '-')}">${value}</span>`;
      } else if (["start_date", "end_date", "freeze_date", "created_at"].includes(key)) {
        td.setAttribute("data-order", formatDateToISO(value));
        td.textContent = formatDate(value);
      } else if (["ano", "pano", "period"].includes(key)) {
        td.setAttribute("data-order", value);
        td.textContent = value;
      } else {
        td.textContent = value;
      }
      
      tr.appendChild(td);
    });
  }

  window.applyParentSearch = async function (searchBoxValue) {
    const rawTerm = searchBoxValue || document.getElementById("searchBox").value.trim();
    const term = rawTerm.toLowerCase();

    if (!term) {
      window.location.reload();
      return;
    }

    try {
      const urlParams = new URLSearchParams(window.location.search);
      const currentMode = urlParams.get("mode") || "active";
      const response = await fetch(`/api/customer_family_full/${encodeURIComponent(term)}?mode=${currentMode}`);
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
        tr.setAttribute("data-source", currentMode);

        appendCustomerCells(tr, customer, currentMode);

        tableBody.appendChild(tr);
      });

      // Rebuild snapshot
      const newRows = Array.from(tableBody.querySelectorAll("tr"));
      snapshot = newRows.map(row => createSnapshotItem(row));

      const toggleContainer = document.getElementById("customerModeToggle");
      if (toggleContainer) {
        toggleContainer.className = `sliding-toggle-container three-way mode-${currentMode}`;
      }

      // Reinitialize DataTable matching standard views
      const rebuiltTable = $('#customerTable').DataTable({
        destroy: true,
        paging: false,
        info: false,
        searching: true,
        ordering: true,
        order: [[1, 'desc']],
        autoWidth: false,
        scrollX: false
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

        // Determine source based on status
        let source = "active";
        if (customer.status && customer.status.toLowerCase() === "closed") {
          source = "closed";
        } else if (customer.status && customer.status.toLowerCase() === "historic") {
          source = "historic";
        } else if (customer.status && customer.status.toLowerCase() === "written_off") {
          source = "closed";
        }
        tr.setAttribute("data-source", source);

        appendCustomerCells(tr, customer, source);

        tableBody.appendChild(tr);
      });

      // Rebuild snapshot
      const newRows = Array.from(tableBody.querySelectorAll("tr"));
      snapshot = newRows.map(row => createSnapshotItem(row));

      // Update toggle switch container highlight
      const toggleContainer = document.getElementById("customerModeToggle");
      if (toggleContainer) {
        toggleContainer.className = "sliding-toggle-container three-way mode-both";
      }

      // Reinitialize DataTable
      const rebuiltTable = $('#customerTable').DataTable({
        destroy: true,
        paging: false,
        info: false,
        searching: true,
        ordering: true,
        order: [[1, 'desc']],
        autoWidth: false,
        scrollX: false
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
      const term = this.value.trim();
      if ($.fn.DataTable.isDataTable('#customerTable')) {
        $('#customerTable').DataTable().search(term).draw();
      } else {
        const lowerTerm = term.toLowerCase();
        const dateTerm = lowerTerm.replace(/\//g, "-");
        snapshot.forEach(d => {
          const anoText = d.ano.toLowerCase();
          const nameText = d.name.toLowerCase();
          
          const startCell = d.row.querySelector(".col-start_date");
          const endCell = d.row.querySelector(".col-end_date");
          const startDateText = startCell ? startCell.textContent.toLowerCase() : "";
          const endDateText = endCell ? endCell.textContent.toLowerCase() : "";
          
          const match = anoText.includes(lowerTerm) ||
                        nameText.includes(lowerTerm) ||
                        startDateText.includes(dateTerm) ||
                        endDateText.includes(dateTerm);
                         
          d.row.style.display = match || !term ? "" : "none";
        });
        updateSummary();
      }
    });

    // Parent family search on Enter key
    searchBox.addEventListener("keydown", function(e) {
      if (e.key === "Enter") {
        e.preventDefault();
        window.applySearch();
      }
    });
  }

  async function loadInitialData() {
    try {
      const response = await fetch(`/api/view_customers/data?mode=${currentMode}`);
      if (!response.ok) {
        throw new Error(`HTTP ${response.status}`);
      }
      const result = await response.json();
      if (!result.success) {
        console.error("Failed to load customer data:", result.error);
        return;
      }

      // 1. Update ALL_CUSTOMERS_STATS
      window.ALL_CUSTOMERS_STATS = result.all_customers_stats;

      // 2. Clear table and populate rows
      if ($.fn.DataTable.isDataTable('#customerTable')) {
        $('#customerTable').DataTable().clear().destroy();
      }
      tableBody.innerHTML = "";

      const customers = result.data || [];
      customers.forEach(customer => {
        const tr = document.createElement("tr");
        tr.className = "table-row";
        tr.setAttribute("data-ano", customer.ano);
        tr.setAttribute("data-cid", customer.cid);
        tr.setAttribute("data-source", customer.source || currentMode);

        appendCustomerCells(tr, customer, currentMode);
        tableBody.appendChild(tr);
      });

      // 3. Rebuild snapshot
      const newRows = Array.from(tableBody.querySelectorAll("tr"));
      snapshot = newRows.map(row => createSnapshotItem(row));

      // 4. Update Summary Cards
      updateSummary();

      // 5. Initialize DataTable
      const tableObj = $('#customerTable').DataTable({
        paging: false,
        info: false,
        searching: true,
        ordering: true,
        order: [[1, 'desc']],
        autoWidth: false,
        scrollX: false
      });

      tableObj.on('draw', () => {
        if (typeof window.updateSummary === 'function') {
          window.updateSummary();
        }
      });

      // Initialize columns configurator dropdown checkboxes if applicable
      if (typeof window.initColumnConfigurator === 'function') {
        window.initColumnConfigurator();
      }

      setTimeout(() => {
        tableObj.columns.adjust().draw(false);
      }, 50);

      // 6. Handle initialSearch if present
      if (initialSearch) {
        const searchBox = document.getElementById("searchBox");
        if (searchBox) {
          searchBox.value = initialSearch;
          if (isParentSearch) {
            window.applyParentSearch(initialSearch);
          } else {
            window.applySearch();
          }
        }
      }

    } catch (err) {
      console.error("Error loading initial view_customers data:", err);
      tableBody.innerHTML = `<tr><td colspan="30" style="text-align: center; padding: 20px; color: #ef4444;">Failed to load customers data: ${err.message || err}. Please refresh the page.</td></tr>`;
    }
  }

  loadInitialData();
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
  // ========================================================
  // 👤 CUSTOMER DASHBOARD POPUP ENGINE & EVENTS
  // ========================================================
  const tableBody = document.getElementById("customerTableBody");
  const popModal = document.getElementById("customerDetailPopup");
  let activeCustomerCid = null;
  let activeCustomerAno = null;
  let localPayments = [];
  let originalPayments = [];

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
      document.getElementById("popInputType").value = cust.type || "W";
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

      // Amount Splits
      const baseAmtVal = cust.base_amount !== null && cust.base_amount !== undefined ? cust.base_amount : 0.0;
      const cuttingAmtVal = cust.cutting_amount !== null && cust.cutting_amount !== undefined ? cust.cutting_amount : 0.0;
      const interestAmtVal = cust.interest_amount !== null && cust.interest_amount !== undefined ? cust.interest_amount : 0.0;

      document.getElementById("popInputBaseAmount").value = baseAmtVal.toFixed(2);
      document.getElementById("popInputCuttingAmount").value = cuttingAmtVal.toFixed(2);
      document.getElementById("popInputInterestAmount").value = interestAmtVal.toFixed(2);

      // Save dataset original snapshots for delta checks
      document.getElementById("popInputName").dataset.original = cust.name || "";
      document.getElementById("popInputTotalAmount").dataset.original = cust.total_amount ? cust.total_amount.toFixed(2) : "0.00";
      document.getElementById("popInputInstallment").dataset.original = cust.installment_amount ? cust.installment_amount.toFixed(2) : "0.00";
      document.getElementById("popInputType").dataset.original = cust.type || "W";
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
      document.getElementById("popInputBaseAmount").dataset.original = baseAmtVal.toFixed(2);
      document.getElementById("popInputCuttingAmount").dataset.original = cuttingAmtVal.toFixed(2);
      document.getElementById("popInputInterestAmount").dataset.original = interestAmtVal.toFixed(2);

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
        
        // Dynamically update title based on type
        const weeklyLogTitle = document.getElementById("popWeeklyLogTitle");
        if (weeklyLogTitle) {
          const typeLabel = (data.customer && data.customer.type === "M") ? "Monthly" : 
                            (data.customer && data.customer.type === "D") ? "Daily" : "Weekly";
          weeklyLogTitle.textContent = typeLabel + " Repayment Log";
        }

        if (data.week_details && data.week_details.length > 0) {
          const typePrefix = (data.customer && data.customer.type) ? data.customer.type : "W";
          data.week_details.forEach(wk => {
            const tr = document.createElement("tr");
            
            // Format Week
            const tdWk = document.createElement("td");
            tdWk.textContent = typePrefix + wk.week;
            tdWk.style.fontWeight = "bold";
            tr.appendChild(tdWk);
            
            // Format Due Date (Normal text color)
            const tdDate = document.createElement("td");
            tdDate.textContent = formatDate(wk.due_date);
            tdDate.setAttribute("data-order", wk.due_date);
            tr.appendChild(tdDate);
            
            // Format Paid Date
            const tdPaidDate = document.createElement("td");
            if (wk.paid_date) {
              const dates = wk.paid_date.split(", ").map(d => formatDate(d));
              tdPaidDate.textContent = dates.join(", ");
              tdPaidDate.setAttribute("data-order", wk.paid_date.split(", ")[0]);
            } else {
              tdPaidDate.textContent = "-";
              tdPaidDate.setAttribute("data-order", "");
            }
            tr.appendChild(tdPaidDate);
            
            // Format Allocated Paid Amt (Normal text color)
            const tdPaid = document.createElement("td");
            tdPaid.textContent = "₹" + (wk.allocated || 0).toFixed(2);
            tdPaid.setAttribute("data-order", wk.allocated || 0);
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
            tdScore.setAttribute("data-order", wk.score_after);
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
      const custStatus = (cust.status || "unknown").trim();
      statusBadge.className = `status-badge status-${custStatus.toLowerCase().replace(/\s+/g, "-")}`;
      statusBadge.textContent = custStatus;

      const closeBtn = document.getElementById("popCloseAccountBtn");
      if (["closed", "defaulted", "written_off", "written off"].includes(custStatus.toLowerCase())) {
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
    if (window.popupChangesMade) {
      window.popupChangesMade = false; // reset
      if (document.getElementById("customerTable")) {
        window.location.reload();
      } else if (typeof loadDashboardData === "function" && window.activeVillageId) {
        loadDashboardData(window.activeVillageId);
      } else {
        window.location.reload();
      }
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
        <td data-field="payment_date" contenteditable="true" data-order="${p.payment_date}">${formatDate(p.payment_date)}</td>
        <td data-field="amt" contenteditable="true" data-money="${p.amt}" data-order="${p.amt}">${p.amt.toFixed(2)}</td>
        <td class="cumulative-amt" data-money="${cumulative}" data-order="${cumulative}">${formatMoney(cumulative)}</td>
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

  // Real-time input detection for payment cells — show save button on first keystroke
  document.getElementById("popPaymentTable").addEventListener("input", function(e) {
    const td = e.target.closest("td[contenteditable='true']");
    if (!td) return;
    // Show save button immediately on any typing
    const saveBtn = document.getElementById("popSavePaymentsBtn");
    if (saveBtn) saveBtn.style.display = "inline-block";
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

  // Bind change monitoring and auto-calculation to all details inputs
  const inputIds = [
    "popInputName", "popInputTotalAmount", "popInputInstallment", "popInputType",
    "popInputPeriod", "popInputPhone", "popInputPano", "popInputStartDate",
    "popInputEndDate", "popInputAadhaar", "popInputEid", "popInputLatitude",
    "popInputLongitude", "popInputNotes", "popInputInterestAmount", "popInputCuttingAmount", "popInputBaseAmount"
  ];

  function calculateInstallment() {
    const totalAmount = parseFloat(document.getElementById("popInputTotalAmount").value) || 0;
    const period = parseInt(document.getElementById("popInputPeriod").value) || 0;
    if (period > 0) {
      const installment = totalAmount / period;
      const roundedInstallment = Math.round(installment * 100) / 100;
      const instEl = document.getElementById("popInputInstallment");
      instEl.value = roundedInstallment.toFixed(2);
    }
  }

  function calculateEndDate() {
    const startStr = document.getElementById("popInputStartDate").value.trim();
    const period = parseInt(document.getElementById("popInputPeriod").value) || 0;
    const type = document.getElementById("popInputType").value;
    const endEl = document.getElementById("popInputEndDate");
    if (startStr && period > 0 && type && endEl) {
      const startDate = parseDDMMYYYY(startStr);
      if (startDate) {
        let endDate = new Date(startDate);
        if (type === 'W') {
          endDate.setDate(endDate.getDate() + (period * 7));
        } else if (type === 'D') {
          endDate.setDate(endDate.getDate() + period);
        } else {
          endDate.setMonth(endDate.getMonth() + period);
        }
        endEl.value = formatDate(endDate);
      }
    }
  }

  async function autoSaveCustomerDetails() {
    const name = document.getElementById("popInputName").value.trim();
    const lettersOnly = name.replace(/\s/g, "");

    if (!name || lettersOnly.length < 3) {
      alert("Name must be at least 3 letters long.");
      return false;
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
        notes: document.getElementById("popInputNotes").value.trim(),
        base_amount: parseFloat(document.getElementById("popInputBaseAmount").value) || 0,
        cutting_amount: parseFloat(document.getElementById("popInputCuttingAmount").value) || 0,
        interest_amount: parseFloat(document.getElementById("popInputInterestAmount").value) || 0
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

      document.getElementById("popProfileName").textContent = name;
      document.getElementById("popAvatarInitial").textContent = name.trim().charAt(0).toUpperCase();

      window.popupChangesMade = true;
      return true;

    } catch (err) {
      console.error("Save failed:", err);
      alert("Failed to save details: " + err.message);
      return false;
    }
  }

  // Bind keyup/input listeners for live calculations and sanitization
  inputIds.forEach(id => {
    const el = document.getElementById(id);
    if (!el) return;
    const eventName = el.tagName === "SELECT" ? "change" : "input";
    el.addEventListener(eventName, function() {
      if (id === "popInputName") {
        this.value = this.value.replace(/[^a-zA-Z\s]/g, "").replace(/\s{2,}/g, " ").replace(/^\s+/g, "");
      } else if (id === "popInputTotalAmount" || id === "popInputInstallment") {
        this.value = this.value.replace(/[^0-9.]/g, "");
        if (id === "popInputTotalAmount") {
          const total = parseFloat(this.value) || 0;
          const paid = localPayments.reduce((sum, p) => sum + p.amt, 0);
          document.getElementById("popBalanceAmount").textContent = formatMoney(total - paid);

          // Auto-calculate splits
          const interestRate = parseFloat(window.VILLAGE_INTEREST_RATE) || 0.0;
          const cuttingRate = parseFloat(window.VILLAGE_CUTTING_RATE) || 0.0;
          const interestAmt = total * interestRate / 100.0;
          const cuttingAmt = total * cuttingRate / 100.0;
          const baseAmt = total - interestAmt - cuttingAmt;
          document.getElementById("popInputInterestAmount").value = interestAmt.toFixed(2);
          document.getElementById("popInputCuttingAmount").value = cuttingAmt.toFixed(2);
          document.getElementById("popInputBaseAmount").value = baseAmt.toFixed(2);
        }
      } else if (id === "popInputPeriod" || id === "popInputEid") {
        this.value = this.value.replace(/[^0-9]/g, "");
      } else if (id === "popInputLatitude" || id === "popInputLongitude") {
        this.value = this.value.replace(/[^0-9.-]/g, "");
      } else if (id === "popInputInterestAmount" || id === "popInputCuttingAmount" || id === "popInputBaseAmount") {
        this.value = this.value.replace(/[^0-9.]/g, "");
        if (id === "popInputInterestAmount" || id === "popInputCuttingAmount") {
          const total = parseFloat(document.getElementById("popInputTotalAmount").value) || 0;
          const interestAmt = parseFloat(document.getElementById("popInputInterestAmount").value) || 0;
          const cuttingAmt = parseFloat(document.getElementById("popInputCuttingAmount").value) || 0;
          document.getElementById("popInputBaseAmount").value = (total - interestAmt - cuttingAmt).toFixed(2);
        }
      }

      if (id === "popInputTotalAmount" || id === "popInputPeriod") {
        calculateInstallment();
      }
      if (id === "popInputStartDate" || id === "popInputPeriod" || id === "popInputType") {
        calculateEndDate();
      }
      checkInputsChanged();
    });
  });

  const saveDetailsBtn = document.getElementById("popSaveDetailsBtn");
  if (saveDetailsBtn) {
    saveDetailsBtn.style.display = "none";
    saveDetailsBtn.addEventListener("click", async function() {
      const fields = [
        "popInputName", "popInputTotalAmount", "popInputInstallment", "popInputType",
        "popInputPeriod", "popInputPhone", "popInputPano", "popInputStartDate",
        "popInputEndDate", "popInputAadhaar", "popInputEid", "popInputLatitude",
        "popInputLongitude", "popInputNotes", "popInputInterestAmount", "popInputCuttingAmount", "popInputBaseAmount"
      ];
      
      let changedElements = [];
      fields.forEach(fid => {
        const el = document.getElementById(fid);
        if (el && el.value.trim() !== (el.dataset.original || "").trim()) {
          changedElements.push(el);
        }
      });

      if (changedElements.length === 0) {
        saveDetailsBtn.style.display = "none";
        return;
      }

      // Synchronously warm up the shared AudioContext within the user gesture event handler
      const audioCtx = window.getSharedAudioContext ? window.getSharedAudioContext() : null;
      if (audioCtx && audioCtx.state === 'suspended') {
        audioCtx.resume().catch(err => console.warn("AudioContext warm up failed:", err));
      }

      const success = await autoSaveCustomerDetails();
      if (success) {
        changedElements.forEach(el => {
          el.dataset.original = el.value.trim();
        });

        if (typeof triggerSuccessFeedback === "function") {
          triggerSuccessFeedback({
            sectionElement: document.getElementById("popColDetails"),
            highlightElements: changedElements,
            message: "Details saved successfully",
            highlightDuration: 5000
          });
        }

        saveDetailsBtn.style.display = "none";
      }
    });
  }

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

  // Recalculate Split Button click/double-click logic
  let recalClickCount = 0;
  let recalClickTimeout = null;
  const recalBtn = document.getElementById("recalBtn");
  if (recalBtn) {
    recalBtn.addEventListener("click", async function () {
      recalClickCount++;
      if (recalClickCount === 1) {
        recalBtn.innerText = "Confirm Recal?";
        recalBtn.style.borderColor = "var(--danger)";
        recalClickTimeout = setTimeout(() => {
          recalClickCount = 0;
          recalBtn.innerText = "Recal";
          recalBtn.style.borderColor = "rgba(220, 38, 38, 0.35)";
        }, 3000); // Reset after 3 seconds
      } else if (recalClickCount === 2) {
        clearTimeout(recalClickTimeout);
        recalClickCount = 0;
        recalBtn.innerText = "Recal";
        recalBtn.style.borderColor = "rgba(220, 38, 38, 0.35)";

        if (!confirm("Are you sure you want to recalculate the split of total amounts (Base, Interest, Cutting) for all active and defaulted customers of this village?")) {
          return;
        }

        recalBtn.disabled = true;
        recalBtn.innerText = "Recalculating...";

        try {
          const response = await csrfFetch("/api/customers/recalculate_split", {
            method: "POST",
            headers: { "Content-Type": "application/json" }
          });
          const result = await response.json();
          if (result.success) {
            alert("Recalculation completed successfully!");
            window.location.reload();
          } else {
            alert("Error: " + (result.error || "Unknown error occurred"));
          }
        } catch (err) {
          alert("A network error occurred: " + err.message);
        } finally {
          recalBtn.disabled = false;
          recalBtn.innerText = "Recal";
        }
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