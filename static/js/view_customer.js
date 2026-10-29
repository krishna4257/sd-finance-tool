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

  function formatMoney(value) {
    const num = Math.round(parseFloat(value) || 0);
    return "₹" + num.toLocaleString('en-IN', { minimumFractionDigits: 0, maximumFractionDigits: 0 });
  }

  // Column keys in order of generation
  const COLUMN_KEYS = [
    "ano", "name", "start_date", "end_date", "total_amount", "paid_amount", 
    "balance_amount", "installment_amount", "type", "period", "pano", "notes",
    "base_amount", "cutting_amount", "interest_amount", "interest_discount",
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
    { key: "interest_discount", label: "Discount", isDefault: true },
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

    let activeBalP = 0;
    let activeBalI = 0;
    let activeBalR = 0;

    let defaultedBalP = 0;
    let defaultedBalI = 0;
    let defaultedBalR = 0;

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
      const tot = parseFloat(c.total_amount) || 0;
      const interestRate = window.VILLAGE_INTEREST_RATE || 0;
      const cuttingRate = window.VILLAGE_CUTTING_RATE || 0;

      // Calculate splits (Principal, Interest, Rusum)
      const i_orig = parseFloat(c.interest_amount) || (tot * (interestRate / 100.0));
      const r_orig = parseFloat(c.cutting_amount) || (tot * (cuttingRate / 100.0));
      const p_orig = parseFloat(c.base_amount) || (tot - i_orig - r_orig);

      const p_rem = Math.max(0, bal - i_orig - r_orig);
      const i_rem = Math.max(0, Math.min(i_orig, bal - r_orig));
      const r_rem = Math.max(0, Math.min(r_orig, bal));

      if (c.source === 'active') {
        activeCount++;
        activeBalSum += bal;
        activeBalP += p_rem;
        activeBalI += i_rem;
        activeBalR += r_rem;

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
          defaultedBalP += p_rem;
          defaultedBalI += i_rem;
          defaultedBalR += r_rem;

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

    const lblActiveBalSplitP = document.getElementById("lblActiveBalSplitP");
    const lblActiveBalSplitI = document.getElementById("lblActiveBalSplitI");
    const lblActiveBalSplitR = document.getElementById("lblActiveBalSplitR");
    const lblDefaultedBalSplitP = document.getElementById("lblDefaultedBalSplitP");
    const lblDefaultedBalSplitI = document.getElementById("lblDefaultedBalSplitI");
    const lblDefaultedBalSplitR = document.getElementById("lblDefaultedBalSplitR");

    if (activeCountEl) activeCountEl.textContent = activeCount;
    if (defaultedCountEl) defaultedCountEl.textContent = defaultedCount;
    if (closedCountEl) closedCountEl.textContent = closedCount;
    if (activeBalAmtEl) activeBalAmtEl.textContent = activeBalSum.toFixed(0);
    if (defaultedBalAmtEl) defaultedBalAmtEl.textContent = defaultedBalSum.toFixed(0);

    if (lblActiveBalSplitP) lblActiveBalSplitP.textContent = formatMoney(activeBalP);
    if (lblActiveBalSplitI) lblActiveBalSplitI.textContent = formatMoney(activeBalI);
    if (lblActiveBalSplitR) lblActiveBalSplitR.textContent = formatMoney(activeBalR);
    if (lblDefaultedBalSplitP) lblDefaultedBalSplitP.textContent = formatMoney(defaultedBalP);
    if (lblDefaultedBalSplitI) lblDefaultedBalSplitI.textContent = formatMoney(defaultedBalI);
    if (lblDefaultedBalSplitR) lblDefaultedBalSplitR.textContent = formatMoney(defaultedBalR);
    
    if (activeAvgScoreEl) activeAvgScoreEl.textContent = activeAvgScoreVal.toFixed(1);
    if (defaultedAvgScoreEl) defaultedAvgScoreEl.textContent = defaultedAvgScoreVal.toFixed(1);
    if (completeAvgScoreEl) completeAvgScoreEl.textContent = completeAvgScoreVal.toFixed(1);

    const activeAvgScoreTrendEl = document.getElementById("activeAvgScoreTrend");
    const defaultedAvgScoreTrendEl = document.getElementById("defaultedAvgScoreTrend");
    const completeAvgScoreTrendEl = document.getElementById("completeAvgScoreTrend");

    if (activeCountEl) activeCountEl.textContent = activeCount;
    if (defaultedCountEl) defaultedCountEl.textContent = defaultedCount;
    if (closedCountEl) closedCountEl.textContent = closedCount;
    if (activeBalAmtEl) activeBalAmtEl.textContent = activeBalSum.toFixed(0);
    if (defaultedBalAmtEl) defaultedBalAmtEl.textContent = defaultedBalSum.toFixed(0);
    
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

    const isPhoneSearch = /^\d{10}$/.test(term);
    
    // If it's a numeric account number search (digits, but not a 10-digit phone number)
    if (/^\d+$/.test(term) && !isPhoneSearch) {
      applyParentSearch(term);
      return;
    }

    if ($.fn.DataTable.isDataTable('#customerTable')) {
      $('#customerTable').DataTable().search(term).draw();
    } else {
      snapshot.forEach(d => {
        let show = false;
        if (isPhoneSearch) {
          show = d.phone_number === term;
        } else {
          show = d.name.includes(term) || d.ano.includes(term);
        }
        d.row.style.display = show ? "" : "none";
      });
      updateSummary();
    }
  };

  window.toggleAll = function (source) {
    const checkboxes = tableBody.querySelectorAll("input[type='checkbox']");
    checkboxes.forEach(cb => {
      cb.checked = source.checked;
      const row = cb.closest("tr");
      if (row) {
        if (source.checked) {
          row.classList.add("checked-row");
        } else {
          row.classList.remove("checked-row");
        }
      }
    });
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
    
    // Retrieve rows in current visual/display order (reflecting active sort and filter)
    let currentOrderedRows = [];
    if (window.jQuery && $.fn.DataTable && $.fn.DataTable.isDataTable('#customerTable')) {
      const dt = $('#customerTable').DataTable();
      currentOrderedRows = dt.rows({ search: 'applied', order: 'applied' }).nodes().toArray();
    } else {
      currentOrderedRows = Array.from(tableBody.querySelectorAll("tr")).filter(tr => 
        tr.style.display !== "none" && tr.id !== "tableLoaderRow"
      );
    }
    
    // Filter out loader or hidden rows
    currentOrderedRows = currentOrderedRows.filter(tr => tr && tr.id !== "tableLoaderRow" && tr.style.display !== "none");

    const selectedCheckboxes = Array.from(tableBody.querySelectorAll("input[type='checkbox']:checked"));
    let rowsToPrint = [];
    if (selectedCheckboxes.length > 0) {
      const selectedSet = new Set(selectedCheckboxes.map(cb => cb.closest("tr")).filter(Boolean));
      // Filter the ordered rows preserving the exact on-screen table ordering
      rowsToPrint = currentOrderedRows.filter(tr => selectedSet.has(tr));
    } else {
      // Print all currently displayed rows in exact on-screen table ordering
      rowsToPrint = currentOrderedRows;
    }
      
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
    <!DOCTYPE html>
    <html>
    <head>
      <title>Print Customers</title>
      <meta charset="utf-8">
      <style>
        * {
          box-sizing: border-box;
          font-weight: 700 !important;
          -webkit-print-color-adjust: exact !important;
          print-color-adjust: exact !important;
        }
        body {
          font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;
          padding: 20px;
          color: #000000 !important;
          background: #ffffff !important;
          font-weight: 700 !important;
        }
        h2 {
          color: #000000 !important;
          font-weight: 900 !important;
          border-bottom: 2px solid #000000;
          padding-bottom: 8px;
          margin-bottom: 16px;
          font-size: 18px;
        }
        table {
          width: 100%;
          border-collapse: collapse;
          margin-top: 10px;
          font-weight: 700 !important;
        }
        th, td {
          border: 1.5px solid #000000 !important;
          padding: 8px 6px;
          text-align: left;
          font-size: 11px;
          color: #000000 !important;
          font-weight: 700 !important;
          line-height: 1.3;
        }
        th {
          background-color: #f1f5f9 !important;
          font-weight: 900 !important;
        }
        tr:nth-child(even) td {
          background-color: #f8fafc;
        }
        @media print {
          @page {
            margin: 8mm;
          }
          body {
            padding: 0;
            color: #000000 !important;
          }
          * {
            font-weight: 700 !important;
            color: #000000 !important;
          }
          th, td {
            font-weight: 700 !important;
            border: 1.5px solid #000000 !important;
            color: #000000 !important;
          }
          th {
            background-color: #f1f5f9 !important;
            font-weight: 900 !important;
          }
        }
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
        const cell = row.querySelector(".col-" + col.key);
        const text = cell ? cell.textContent.trim() : "";
        html += "<td>" + text + "</td>";
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
    w.focus();
    setTimeout(() => {
      w.print();
    }, 250);
    
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
      
      if (["total_amount", "paid_amount", "balance_amount", "installment_amount", "interest_discount", "base_amount", "cutting_amount", "interest_amount"].includes(key)) {
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
      } else if (key === "ano") {
        td.setAttribute("data-order", value);
        if (customer.cycle_number && customer.cycle_number > 1) {
          td.innerHTML = `<span>${value}</span> <span class="badge-cycle-chip" title="Repeat Borrower (Cycle ${customer.cycle_number})" style="display: inline-block; font-size: 10px; font-weight: 800; padding: 1px 5px; border-radius: 10px; background: rgba(14, 165, 233, 0.15); color: #0284c7; border: 1px solid rgba(14, 165, 233, 0.3); vertical-align: middle; margin-left: 4px;">C${customer.cycle_number}</span>`;
        } else {
          td.textContent = value;
        }
      } else if (["pano", "period"].includes(key)) {
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

        let source = customer.status || "active";
        if (["closed", "defaulted", "written_off", "written off"].includes(source.toLowerCase())) {
          source = "closed";
        } else if (source.toLowerCase() === "historic") {
          source = "historic";
        } else {
          source = "active";
        }
        tr.setAttribute("data-source", source);

        appendCustomerCells(tr, customer, source);

        tableBody.appendChild(tr);
      });

      // Rebuild snapshot
      const newRows = Array.from(tableBody.querySelectorAll("tr"));
      snapshot = newRows.map(row => createSnapshotItem(row));

      const toggleContainer = document.getElementById("customerModeToggle");
      if (toggleContainer) {
        toggleContainer.className = `sliding-toggle-container three-way mode-both`;
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

  window.applyLinkSearch = async function (searchBoxValue) {
    const rawTerm = searchBoxValue || document.getElementById("searchBox").value.trim();
    const term = rawTerm.toLowerCase();

    if (!term) {
      alert("Please enter an account number.");
      return;
    }

    // Only allow numeric search for link account
    const isAnoSearch = /^\d+$/.test(term);
    if (!isAnoSearch) {
      alert("Please enter a numeric account number (ANO).");
      return;
    }

    try {
      const response = await fetch(`/api/customer_linked_accounts/${encodeURIComponent(term)}`);
      if (!response.ok) {
        throw new Error(`HTTP ${response.status}`);
      }

      const result = await response.json();
      if (!result.success) {
        alert(result.error || "Unable to load linked accounts.");
        return;
      }

      const customers = result.customers || [];
      if (customers.length === 0) {
        alert("No linked accounts found.");
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
        
        let source = customer.status || "active";
        if (source === "written_off") {
          source = "closed";
        }
        tr.setAttribute("data-source", source);

        appendCustomerCells(tr, customer, source);

        tableBody.appendChild(tr);
      });

      // Rebuild snapshot
      const newRows = Array.from(tableBody.querySelectorAll("tr"));
      snapshot = newRows.map(row => createSnapshotItem(row));

      const toggleContainer = document.getElementById("customerModeToggle");
      if (toggleContainer) {
        toggleContainer.className = `sliding-toggle-container three-way mode-both`;
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
      console.error("Link search failed:", err);
      alert(err?.message || "Link search failed.");
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
      window.VILLAGE_INTEREST_RATE = result.interest_rate || 0.0;
      window.VILLAGE_CUTTING_RATE = result.cutting_rate || 0.0;

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
    const num = Math.round(parseFloat(value) || 0);
    return "₹" + num.toLocaleString('en-IN', { minimumFractionDigits: 0, maximumFractionDigits: 0 });
  }

  // Handle checkbox clicks & state changes in the main table with zero lag
  if (tableBody) {
    // 1. Listen for checkbox state changes (add/remove checked-row highlight class)
    tableBody.addEventListener("change", function(e) {
      const cb = e.target.closest("input[type='checkbox']");
      if (!cb) return;
      
      // Stop event propagation to prevent any outer click/change handlers from intercepting
      e.stopPropagation();
      
      const row = cb.closest("tr");
      if (!row) return;
      
      if (cb.checked) {
        row.classList.add("checked-row");
      } else {
        row.classList.remove("checked-row");
      }
    });

    // 2. Stop click propagation from the checkbox to prevent any row selection/blurs
    tableBody.addEventListener("click", function(e) {
      if (e.target.tagName === "INPUT" && e.target.type === "checkbox") {
        e.stopPropagation();
        return;
      }
      
      // 3. Make clicking the cell td.checkbox-column toggle the checkbox inside it
      const cell = e.target.closest("td.checkbox-column");
      if (cell) {
        e.stopPropagation();
        e.preventDefault();
        const cb = cell.querySelector("input[type='checkbox']");
        if (cb) {
          cb.checked = !cb.checked;
          // Trigger change event programmatically so our listener runs
          cb.dispatchEvent(new Event("change", { bubbles: true }));
        }
      }
    });
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
      const discountInput = document.getElementById("popInputInterestDiscount");
      if (discountInput) {
        discountInput.value = "";
        discountInput.dataset.original = "";
      }
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
      const lifetimeScoreContainerReset = document.getElementById("popLifetimeScoreContainer");
      if (lifetimeScoreContainerReset) lifetimeScoreContainerReset.style.display = "none";
      
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
      
      // Cycle Lineage Badge & UCID Display
      const cycleBadge = document.getElementById("popCycleBadge");
      const cycleText = document.getElementById("popCycleText");
      const ucidContainer = document.getElementById("popUcidContainer");
      const ucidElem = document.getElementById("popUcid");

      if (cust.ucid) {
        if (ucidContainer && ucidElem) {
          ucidElem.textContent = `UCID-${String(cust.ucid).padStart(5, '0')}`;
          ucidContainer.style.display = "block";
        }
        if (cycleBadge && cycleText) {
          const totalCycles = (cust.borrower_summary && cust.borrower_summary.total_cycles) ? cust.borrower_summary.total_cycles : (cust.cycle_number || 1);
          if (totalCycles > 1) {
            cycleText.textContent = `Cycle ${cust.cycle_number || 1} of ${totalCycles} (Repeat Borrower)`;
            cycleBadge.style.display = "inline-flex";
          } else {
            cycleText.textContent = `Cycle 1`;
            cycleBadge.style.display = "inline-flex";
          }
        }
      } else {
        if (ucidContainer) ucidContainer.style.display = "none";
        if (cycleBadge) cycleBadge.style.display = "none";
      }
      
      // Load inputs (Auto-Edit defaults)
      document.getElementById("popInputName").value = cust.name || "";
      document.getElementById("popInputTotalAmount").value = cust.total_amount ? cust.total_amount.toFixed(0) : "0";
      document.getElementById("popInputInstallment").value = cust.installment_amount ? cust.installment_amount.toFixed(0) : "0";
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

      document.getElementById("popInputBaseAmount").value = baseAmtVal.toFixed(0);
      document.getElementById("popInputCuttingAmount").value = cuttingAmtVal.toFixed(0);
      document.getElementById("popInputInterestAmount").value = interestAmtVal.toFixed(0);

      // Save dataset original snapshots for delta checks
      document.getElementById("popInputName").dataset.original = cust.name || "";
      document.getElementById("popInputTotalAmount").dataset.original = cust.total_amount ? cust.total_amount.toFixed(0) : "0";
      document.getElementById("popInputInstallment").dataset.original = cust.installment_amount ? cust.installment_amount.toFixed(0) : "0";
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
      document.getElementById("popInputBaseAmount").dataset.original = baseAmtVal.toFixed(0);
      document.getElementById("popInputCuttingAmount").dataset.original = cuttingAmtVal.toFixed(0);
      document.getElementById("popInputInterestAmount").dataset.original = interestAmtVal.toFixed(0);

      document.getElementById("popSaveDetailsBtn").style.display = "none";

      // Read-only info fields
      document.getElementById("popPaidAmount").textContent = formatMoney(cust.paid_amount);
      document.getElementById("popBalanceAmount").textContent = formatMoney(cust.balance_amount);

      // Calculate remaining splits (clearing principal first)
      const balVal = cust.balance_amount || 0.0;
      const p_rem = Math.max(0, balVal - interestAmtVal - cuttingAmtVal);
      const i_rem = Math.max(0, Math.min(interestAmtVal, balVal - cuttingAmtVal));
      const r_rem = Math.max(0, Math.min(cuttingAmtVal, balVal));

      // Populate elements
      document.getElementById("popPopOriginalLoanVal").textContent = formatMoney(cust.total_amount);
      document.getElementById("popPopLoanSplitP").textContent = formatMoney(baseAmtVal);
      document.getElementById("popPopLoanSplitI").textContent = formatMoney(interestAmtVal);
      document.getElementById("popPopLoanSplitR").textContent = formatMoney(cuttingAmtVal);

      document.getElementById("popPopRemainingBalVal").textContent = formatMoney(balVal);
      document.getElementById("popPopBalanceSplitP").textContent = formatMoney(p_rem);
      document.getElementById("popPopBalanceSplitI").textContent = formatMoney(i_rem);
      document.getElementById("popPopBalanceSplitR").textContent = formatMoney(r_rem);

      const discountAmt = cust.interest_discount || 0.0;
      const discountInput = document.getElementById("popInputInterestDiscount");
      if (discountInput) {
        discountInput.value = discountAmt.toFixed(0);
        discountInput.dataset.original = discountAmt.toFixed(0);
      }

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

      // Render Lifetime Repayment Reliability (BRI)
      const lifetimeScoreContainer = document.getElementById("popLifetimeScoreContainer");
      const lifetimeScoreVal = document.getElementById("popLifetimeScoreVal");
      const lifetimeRatioVal = document.getElementById("popLifetimeRatioVal");
      if (lifetimeScoreContainer && cust.borrower_summary && cust.borrower_summary.lifetime_credit_score !== undefined) {
        const lScore = cust.borrower_summary.lifetime_credit_score;
        const lRatio = cust.borrower_summary.lifetime_on_time_ratio !== undefined ? cust.borrower_summary.lifetime_on_time_ratio : 100.0;
        if (lifetimeScoreVal) {
          lifetimeScoreVal.textContent = Math.round(lScore);
          if (lScore >= 85) {
            lifetimeScoreVal.style.color = "#0284c7";
          } else if (lScore >= 65) {
            lifetimeScoreVal.style.color = "#10b981";
          } else if (lScore >= 45) {
            lifetimeScoreVal.style.color = "#fbbf24";
          } else {
            lifetimeScoreVal.style.color = "#ef4444";
          }
        }
        if (lifetimeRatioVal) {
          lifetimeRatioVal.textContent = `${Math.round(lRatio)}% on-time`;
        }
        lifetimeScoreContainer.style.display = "flex";
      } else if (lifetimeScoreContainer) {
        lifetimeScoreContainer.style.display = "none";
      }

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
            tdPaid.textContent = "₹" + (wk.allocated || 0).toFixed(0);
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
      const discountInput = document.getElementById("popInputInterestDiscount");
      const interestDiscount = discountInput ? (parseFloat(discountInput.value) || 0) : 0;
      document.getElementById("popBalanceAmount").textContent = formatMoney(totalAmtInput - interestDiscount);
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
        <td data-field="amt" contenteditable="true" data-money="${p.amt}" data-order="${p.amt}">${p.amt.toFixed(0)}</td>
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
    const discountInput = document.getElementById("popInputInterestDiscount");
    const interestDiscount = discountInput ? (parseFloat(discountInput.value) || 0) : 0;
    document.getElementById("popBalanceAmount").textContent = formatMoney(totalAmtInput - totalAmt - interestDiscount);

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
      const duplicateIndex = localPayments.findIndex((p, idx) => idx !== index && p.payment_date === iso);
      if (duplicateIndex !== -1) {
        alert(`A payment for date ${formatDate(iso)} already exists (₹${localPayments[duplicateIndex].amt}). Only one payment per date is allowed.`);
        td.textContent = formatDate(localPayments[index].payment_date);
        return;
      }
      localPayments[index].payment_date = iso;
    } else if (field === "amt") {
      const amt = parseFloat(value.replace(/[^\d.-]/g, "")) || 0;
      if (amt < 0) {
        alert("Amount cannot be negative.");
        td.textContent = localPayments[index].amt.toFixed(0);
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
      "popInputLongitude", "popInputNotes", "popInputInterestDiscount"
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
    "popInputLongitude", "popInputNotes", "popInputInterestAmount", "popInputCuttingAmount", "popInputBaseAmount", "popInputInterestDiscount"
  ];

  function calculateInstallment() {
    const totalAmount = parseFloat(document.getElementById("popInputTotalAmount").value) || 0;
    const period = parseInt(document.getElementById("popInputPeriod").value) || 0;
    if (period > 0) {
      const installment = totalAmount / period;
      const roundedInstallment = Math.round(installment);
      const instEl = document.getElementById("popInputInstallment");
      instEl.value = roundedInstallment.toFixed(0);
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
        status: (document.getElementById("popStatusBadge")?.textContent || "active").trim().toLowerCase(),
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
        interest_amount: parseFloat(document.getElementById("popInputInterestAmount").value) || 0,
        interest_discount: parseFloat(document.getElementById("popInputInterestDiscount").value) || 0
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
          const discountInput = document.getElementById("popInputInterestDiscount");
          const interestDiscount = discountInput ? (parseFloat(discountInput.value) || 0) : 0;
          document.getElementById("popBalanceAmount").textContent = formatMoney(total - paid - interestDiscount);

          // Auto-calculate splits
          const interestRate = parseFloat(window.VILLAGE_INTEREST_RATE) || 0.0;
          const cuttingRate = parseFloat(window.VILLAGE_CUTTING_RATE) || 0.0;
          const interestAmt = Math.round(total * interestRate / 100.0);
          const cuttingAmt = Math.round(total * cuttingRate / 100.0);
          const baseAmt = total - interestAmt - cuttingAmt;
          document.getElementById("popInputInterestAmount").value = interestAmt.toFixed(0);
          document.getElementById("popInputCuttingAmount").value = cuttingAmt.toFixed(0);
          document.getElementById("popInputBaseAmount").value = baseAmt.toFixed(0);
        }
      } else if (id === "popInputPeriod" || id === "popInputEid") {
        this.value = this.value.replace(/[^0-9]/g, "");
      } else if (id === "popInputLatitude" || id === "popInputLongitude") {
        this.value = this.value.replace(/[^0-9.-]/g, "");
      } else if (id === "popInputInterestAmount" || id === "popInputCuttingAmount" || id === "popInputBaseAmount" || id === "popInputInterestDiscount") {
        this.value = this.value.replace(/[^0-9.]/g, "");
        if (id === "popInputInterestAmount" || id === "popInputCuttingAmount") {
          const total = parseFloat(document.getElementById("popInputTotalAmount").value) || 0;
          const interestAmt = parseFloat(document.getElementById("popInputInterestAmount").value) || 0;
          const cuttingAmt = parseFloat(document.getElementById("popInputCuttingAmount").value) || 0;
          document.getElementById("popInputBaseAmount").value = (total - interestAmt - cuttingAmt).toFixed(0);
        } else if (id === "popInputInterestDiscount") {
          const total = parseFloat(document.getElementById("popInputTotalAmount").value) || 0;
          const paid = localPayments.reduce((sum, p) => sum + p.amt, 0);
          const discount = parseFloat(this.value) || 0;
          document.getElementById("popBalanceAmount").textContent = formatMoney(total - paid - discount);
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
        "popInputLongitude", "popInputNotes", "popInputInterestAmount", "popInputCuttingAmount", "popInputBaseAmount", "popInputInterestDiscount"
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

        showToast("Account retrieved successfully!");
        closeCustomerPopup();
        setTimeout(() => {
          window.location.reload();
        }, 1000);
      } catch (err) {
        alert("Retrieve failed: " + err.message);
      }
    } else {
      // CLOSE FLOW
      const balance = parseFloat(document.getElementById("popBalanceAmount").textContent.replace(/[^\d.-]/g, "")) || 0;
      const interestAmount = parseFloat(document.getElementById("popInputInterestAmount").value) || 0;
      
      const modal = document.getElementById("popCloseAccountModal");
      const statusMsg = document.getElementById("popCloseAccountStatusMsg");
      const optionsContainer = document.getElementById("popCloseAccountOptions");
      const discountSection = document.getElementById("popDiscountSection");
      const discountInput = document.getElementById("popDiscountInput");
      
      if (!modal) {
        alert("Close options modal element not found.");
        return;
      }
      
      optionsContainer.innerHTML = "";
      discountSection.style.display = "none";
      discountInput.value = "";
      
      if (balance <= 0) {
        // Automatically close without popup
        const action = balance < 0 ? "written_off" : null;
        handleCloseSubmit(action);
        return;
      }
      
      // Balance > 0
      statusMsg.innerHTML = `Remaining Balance is <strong>₹${balance.toFixed(0)}</strong>.<br>This account will be closed and marked as <strong>Defaulted</strong>.`;
      
      // Option 1: Default
      const defaultBtn = document.createElement("button");
      defaultBtn.className = "neumorphic-btn small danger-btn";
      defaultBtn.style.width = "100%";
      defaultBtn.style.justifyContent = "center";
      defaultBtn.style.fontWeight = "bold";
      defaultBtn.textContent = "Close Account";
      defaultBtn.addEventListener("click", () => {
        modal.style.display = "none";
        handleCloseSubmit("defaulted");
      });
      optionsContainer.appendChild(defaultBtn);
      
      // Option 2: Discount Interest (only if balance <= interestAmount)
      if (balance <= interestAmount) {
        const discountBtn = document.createElement("button");
        discountBtn.className = "neumorphic-btn small primary-save-btn glow-cyan";
        discountBtn.style.width = "100%";
        discountBtn.style.justifyContent = "center";
        discountBtn.style.fontWeight = "bold";
        discountBtn.style.marginTop = "10px";
        discountBtn.textContent = "Discount Interest";
        discountBtn.addEventListener("click", () => {
          discountSection.style.display = "block";
          discountInput.value = balance.toFixed(0);
          discountInput.focus();
        });
        optionsContainer.appendChild(discountBtn);
      }
      
      modal.style.display = "flex";
    }
  });

  async function handleCloseSubmit(action, discountAmount = null) {
    const btn = document.getElementById("popCloseAccountBtn");
    const originalText = btn.textContent;
    btn.disabled = true;
    btn.textContent = "Processing...";
    
    try {
      const payload = { cid: activeCustomerCid, action: action };
      if (discountAmount !== null) {
        payload.discount_amount = discountAmount;
      }
      const res = await csrfFetch("/api/customer/close_account_pg", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload)
      });
      const data = await res.json();
      if (!data.success) throw new Error(data.error || "Failed to close");

      showToast("Account closed successfully!");
      closeCustomerPopup();
      setTimeout(() => {
        window.location.reload();
      }, 1000);
    } catch (err) {
      alert("Settlement failed: " + err.message);
      btn.disabled = false;
      btn.textContent = originalText;
    }
  }

  // Bind Confirm Discount button
  const popConfirmDiscountBtn = document.getElementById("popConfirmDiscountBtn");
  if (popConfirmDiscountBtn) {
    popConfirmDiscountBtn.addEventListener("click", function() {
      const discountInput = document.getElementById("popDiscountInput");
      const val = parseFloat(discountInput.value) || 0;
      const balance = parseFloat(document.getElementById("popBalanceAmount").textContent.replace(/[^\d.-]/g, "")) || 0;
      if (val <= 0) {
        alert("Discount must be greater than 0");
        return;
      }
      if (val > balance) {
        alert("Discount cannot exceed balance");
        return;
      }
      document.getElementById("popCloseAccountModal").style.display = "none";
      handleCloseSubmit("discount_interest", val);
    });
  }

  window.closePopCloseAccountModal = function() {
    document.getElementById("popCloseAccountModal").style.display = "none";
  };

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

    const existingIndex = localPayments.findIndex(p => p.payment_date === isoDate);
    if (existingIndex !== -1) {
      alert(`A payment for date ${formatDate(isoDate)} already exists (₹${localPayments[existingIndex].amt}). Only one payment per date is allowed.`);
      return;
    }

    const custStartDate = toISO(document.getElementById("popInputStartDate")?.value || "");
    if (custStartDate && isoDate < custStartDate) {
      alert(`Payment date (${formatDate(isoDate)}) cannot be earlier than customer start date (${formatDate(custStartDate)}).`);
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
    // Validate unique dates before sending request
    const dateSet = new Set();
    for (const p of localPayments) {
      if (dateSet.has(p.payment_date)) {
        alert(`Duplicate payment date detected: ${formatDate(p.payment_date)}. Each date can only have one payment.`);
        return;
      }
      dateSet.add(p.payment_date);
    }

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

  // 🍞 Transient Success Toast
  window.showToast = function(message, duration = 1500) {
    let toast = document.getElementById("transient-toast");
    if (!toast) {
      toast = document.createElement("div");
      toast.id = "transient-toast";
      toast.style.position = "fixed";
      toast.style.top = "24px";
      toast.style.right = "24px";
      toast.style.zIndex = "99999";
      toast.style.background = "rgba(16, 185, 129, 0.95)"; // nice emerald green
      toast.style.color = "#ffffff";
      toast.style.padding = "14px 24px";
      toast.style.borderRadius = "12px";
      toast.style.boxShadow = "0 10px 25px -5px rgba(0, 0, 0, 0.3), 0 8px 10px -6px rgba(0, 0, 0, 0.3)";
      toast.style.fontFamily = "'Space Grotesk', sans-serif";
      toast.style.fontWeight = "600";
      toast.style.fontSize = "14px";
      toast.style.pointerEvents = "none";
      toast.style.opacity = "0";
      toast.style.transform = "translateY(-20px)";
      toast.style.transition = "opacity 0.3s ease, transform 0.3s ease";
      document.body.appendChild(toast);
    }
    toast.textContent = message;
    
    // trigger animation
    requestAnimationFrame(() => {
      toast.style.opacity = "1";
      toast.style.transform = "translateY(0)";
    });
    
    setTimeout(() => {
      toast.style.opacity = "0";
      toast.style.transform = "translateY(-20px)";
    }, duration);
  };

  // 📦 Bulk Close Logic
  let isBulkCloseMode = false;
  let selectedCustomersForBulk = [];

  window.toggleBulkCloseMode = function() {
    const tableEl = document.getElementById("customerTable");
    const wrapper = document.querySelector(".customer-table-wrapper");
    const btn = document.getElementById("bulkCloseBtn");
    
    if (!tableEl) return;
    
    if (isBulkCloseMode) {
      // If it's already active, clicking the button again means we want to EXECUTE/Confirm!
      handleBulkCloseClick();
      return;
    }
    
    isBulkCloseMode = true;
    tableEl.classList.add("bulk-close-mode-active");
    if (wrapper) wrapper.classList.add("bulk-close-mode-active");
    btn.textContent = "Confirm Bulk Close";
    btn.className = "neumorphic-btn glow-red";
    
    // Add a cancel button if it doesn't exist
    if (!document.getElementById("cancelBulkCloseBtn")) {
      const cancelBtn = document.createElement("button");
      cancelBtn.id = "cancelBulkCloseBtn";
      cancelBtn.className = "neumorphic-btn";
      cancelBtn.style.margin = "0";
      cancelBtn.textContent = "Cancel";
      cancelBtn.onclick = deactivateBulkCloseMode;
      btn.parentNode.insertBefore(cancelBtn, btn.nextSibling);
    }
  };

  function deactivateBulkCloseMode() {
    const tableEl = document.getElementById("customerTable");
    const wrapper = document.querySelector(".customer-table-wrapper");
    const btn = document.getElementById("bulkCloseBtn");
    
    isBulkCloseMode = false;
    if (tableEl) tableEl.classList.remove("bulk-close-mode-active");
    if (wrapper) wrapper.classList.remove("bulk-close-mode-active");
    if (btn) {
      btn.textContent = "Close";
      btn.className = "neumorphic-btn";
    }
    
    const cancelBtn = document.getElementById("cancelBulkCloseBtn");
    if (cancelBtn) cancelBtn.remove();
    
    // Uncheck all and remove checked classes
    const checkboxes = document.querySelectorAll("#customerTable input[type='checkbox']");
    checkboxes.forEach(cb => {
      cb.checked = false;
      const row = cb.closest("tr");
      if (row) row.classList.remove("checked-row");
    });
  }

  window.closeBulkCloseModal = function() {
    const modal = document.getElementById("bulkCloseModal");
    if (modal) modal.style.display = "none";
  };

  window.handleBulkCloseClick = function() {
    const tableBody = document.getElementById("customerTableBody");
    if (!tableBody) return;
    
    const checkedBoxes = Array.from(tableBody.querySelectorAll("input[type='checkbox']:checked"));
    if (checkedBoxes.length === 0) {
      alert("Please select at least one customer to close.");
      return;
    }
    
    selectedCustomersForBulk = checkedBoxes.map(cb => {
      const row = cb.closest("tr");
      const cid = row.getAttribute("data-cid");
      const ano = row.querySelector(".col-ano")?.textContent.trim() || "";
      const name = row.querySelector(".col-name")?.textContent.trim() || "";
      const balText = row.querySelector(".col-balance_amount")?.textContent.replace(/[^\d.-]/g, "") || "0";
      const balance = parseFloat(balText) || 0;
      return { cid, ano, name, balance };
    });
    
    openBulkCloseStage1();
  };

  function openBulkCloseStage1() {
    const modal = document.getElementById("bulkCloseModal");
    const modalTitle = document.getElementById("bulkCloseModalTitle");
    const modalMsg = document.getElementById("bulkCloseModalMsg");
    const tableBody = document.getElementById("bulkCloseModalTableBody");
    const confirmBtn = document.getElementById("bulkCloseConfirmBtn");
    
    if (!modal || !tableBody || !confirmBtn) return;
    
    modalTitle.textContent = "Confirm Bulk Close (Stage 1)";
    modalMsg.textContent = "Review the selected customers to close. Accounts with balance <= 0 will be closed directly. Accounts with balance > 0 will be processed in the next stage.";
    
    tableBody.innerHTML = "";
    
    selectedCustomersForBulk.forEach(cust => {
      const tr = document.createElement("tr");
      tr.style.borderBottom = "1px solid var(--border)";
      
      let actionText = "";
      let actionColor = "";
      if (cust.balance === 0) {
        actionText = "Close Normally";
        actionColor = "var(--success)";
      } else if (cust.balance < 0) {
        actionText = "Write Off (Settle)";
        actionColor = "var(--warning)";
      } else {
        actionText = "Defer to Stage 2 (Default)";
        actionColor = "var(--text-secondary)";
      }
      
      tr.innerHTML = `
        <td style="padding: 10px; color: var(--text);">${cust.ano}</td>
        <td style="padding: 10px; color: var(--text); font-weight: 500;">${cust.name}</td>
        <td style="padding: 10px; color: ${cust.balance > 0 ? "var(--danger)" : "var(--text)"}; font-weight: 600;">₹${cust.balance.toFixed(0)}</td>
        <td style="padding: 10px; color: ${actionColor}; font-weight: 600;">${actionText}</td>
      `;
      tableBody.appendChild(tr);
    });
    
    confirmBtn.textContent = "Confirm Close";
    confirmBtn.onclick = processBulkCloseStage1;
    
    modal.style.display = "flex";
  }

  async function processBulkCloseStage1() {
    const listA = selectedCustomersForBulk.filter(c => c.balance <= 0);
    const listB = selectedCustomersForBulk.filter(c => c.balance > 0);
    
    if (listA.length > 0) {
      const confirmBtn = document.getElementById("bulkCloseConfirmBtn");
      confirmBtn.disabled = true;
      confirmBtn.textContent = "Processing...";
      
      try {
        const promises = listA.map(cust => {
          const action = cust.balance < 0 ? "written_off" : null;
          return csrfFetch("/api/customer/close_account_pg", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ cid: cust.cid, action: action })
          }).then(res => res.json());
        });
        
        const results = await Promise.all(promises);
        const errors = results.filter(r => !r.success).map(r => r.error);
        if (errors.length > 0) {
          alert("Some accounts failed to close: " + errors.join(", "));
        }
      } catch (err) {
        alert("Error closing accounts: " + err.message);
      } finally {
        confirmBtn.disabled = false;
      }
    }
    
    if (listB.length === 0) {
      closeBulkCloseModal();
      deactivateBulkCloseMode();
      showToast("Selected accounts closed successfully!");
      setTimeout(() => window.location.reload(), 1000);
    } else {
      selectedCustomersForBulk = listB;
      openBulkCloseStage2();
    }
  }

  function openBulkCloseStage2() {
    const modal = document.getElementById("bulkCloseModal");
    const modalTitle = document.getElementById("bulkCloseModalTitle");
    const modalMsg = document.getElementById("bulkCloseModalMsg");
    const tableBody = document.getElementById("bulkCloseModalTableBody");
    const confirmBtn = document.getElementById("bulkCloseConfirmBtn");
    
    if (!modal || !tableBody || !confirmBtn) return;
    
    modalTitle.textContent = "Confirm Default Close (Stage 2)";
    modalMsg.innerHTML = `<span style="color: var(--danger); font-weight: 700;">WARNING:</span> The following accounts have a remaining balance. Confirming will close these accounts and mark them as <strong>Defaulted</strong>.`;
    
    tableBody.innerHTML = "";
    
    selectedCustomersForBulk.forEach(cust => {
      const tr = document.createElement("tr");
      tr.style.borderBottom = "1px solid var(--border)";
      
      tr.innerHTML = `
        <td style="padding: 10px; color: var(--text);">${cust.ano}</td>
        <td style="padding: 10px; color: var(--text); font-weight: 500;">${cust.name}</td>
        <td style="padding: 10px; color: var(--danger); font-weight: 600;">₹${cust.balance.toFixed(0)}</td>
        <td style="padding: 10px; color: var(--danger); font-weight: bold;">Default Account</td>
      `;
      tableBody.appendChild(tr);
    });
    
    confirmBtn.textContent = "Confirm Default Close";
    confirmBtn.onclick = processBulkCloseStage2;
  }

  async function processBulkCloseStage2() {
    const confirmBtn = document.getElementById("bulkCloseConfirmBtn");
    confirmBtn.disabled = true;
    confirmBtn.textContent = "Processing...";
    
    try {
      const promises = selectedCustomersForBulk.map(cust => {
        return csrfFetch("/api/customer/close_account_pg", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ cid: cust.cid, action: "defaulted" })
        }).then(res => res.json());
      });
      
      const results = await Promise.all(promises);
      const errors = results.filter(r => !r.success).map(r => r.error);
      if (errors.length > 0) {
        alert("Some defaulted accounts failed to close: " + errors.join(", "));
      }
    } catch (err) {
      alert("Error closing accounts: " + err.message);
    } finally {
      confirmBtn.disabled = false;
    }
    
    closeBulkCloseModal();
    deactivateBulkCloseMode();
    showToast("Selected accounts defaulted and closed successfully!");
    setTimeout(() => window.location.reload(), 1000);
  }

  // ----------------------------------------------------
  // BORROWER 360° LOAN LINEAGE MODAL
  // ----------------------------------------------------
  window.openBorrowerLineageModal = async function () {
    const modal = document.getElementById("popBorrowerLineageModal");
    if (!modal) return;

    modal.style.display = "flex";
    modal.classList.add("active");

    const timelineContainer = document.getElementById("popLineageTimeline");
    if (timelineContainer) {
      timelineContainer.innerHTML = `<div style="text-align: center; padding: 25px; color: var(--text-secondary);"><i class="fas fa-spinner fa-spin" style="font-size: 1.5rem; margin-bottom: 8px; display: block;"></i>Loading 360° borrower history...</div>`;
    }

    try {
      const popCidElem = document.getElementById("popCid");
      const popUcidElem = document.getElementById("popUcid");
      const identifier = activeCustomerCid || 
                         (popCidElem && popCidElem.textContent.trim()) || 
                         (popUcidElem && popUcidElem.textContent.trim()) || 
                         activeCustomerAno;

      if (!identifier) {
        throw new Error("No customer identifier found.");
      }

      const res = await fetch(`/api/customer/${encodeURIComponent(identifier)}/borrower_360`);
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data = await res.json();
      if (!data.success) throw new Error(data.error || "Failed to load borrower profile");

      const b = data.borrower;
      const cycles = data.cycles || [];

      document.getElementById("popLineageBorrowerName").textContent = b.primary_name;
      document.getElementById("popLineageUcidBadge").textContent = b.ucid_display;
      document.getElementById("popLineageVillage").textContent = b.village_name ? `Village: ${b.village_name}` : "";
      document.getElementById("popLineagePhone").textContent = b.phone_number ? `Phone: ${b.phone_number}` : "";
      document.getElementById("popLineageCyclesPill").textContent = `Total Cycles: ${b.total_cycles}`;

      document.getElementById("popLineageTotalBorrowed").textContent = formatMoney(b.lifetime_borrowed);
      document.getElementById("popLineageTotalRepaid").textContent = formatMoney(b.lifetime_repaid);
      document.getElementById("popLineageActiveBalance").textContent = formatMoney(b.current_active_balance);
      
      const scoreElem = document.getElementById("popLineageLifetimeScore");
      if (scoreElem) {
        scoreElem.textContent = (b.lifetime_credit_score !== undefined ? b.lifetime_credit_score.toFixed(1) : "100.0");
        if (b.lifetime_credit_score < 65) {
          scoreElem.style.color = "var(--danger)";
        } else if (b.lifetime_credit_score < 85) {
          scoreElem.style.color = "var(--warning)";
        } else {
          scoreElem.style.color = "#0284c7";
        }
      }

      const ratioElem = document.getElementById("popLineageOnTimeRatio");
      if (ratioElem) {
        ratioElem.textContent = `${(b.lifetime_on_time_ratio !== undefined ? b.lifetime_on_time_ratio.toFixed(1) : "100.0")}%`;
      }

      const riskElem = document.getElementById("popLineageRiskTier");
      if (riskElem) {
        riskElem.textContent = (b.customer_risk_tier || "standard").toUpperCase();
        if (b.customer_risk_tier === "low") {
          riskElem.style.color = "var(--success)";
        } else if (b.customer_risk_tier === "high") {
          riskElem.style.color = "var(--danger)";
        } else {
          riskElem.style.color = "var(--primary)";
        }
      }

      // Render timeline cards
      timelineContainer.innerHTML = "";
      cycles.forEach((c) => {
        const isCurrent = String(c.cid) === String(activeCustomerCid) || String(c.ano) === String(activeCustomerAno);
        const card = document.createElement("div");
        card.className = "subcard-glass";
        card.style.cssText = `padding: 14px 16px; border-radius: 12px; border: 1.5px solid ${isCurrent ? 'var(--primary)' : 'var(--border)'}; background: ${isCurrent ? 'rgba(14, 165, 233, 0.08)' : 'var(--surface)'}; display: flex; flex-direction: column; gap: 8px; transition: all 0.2s ease;`;

        let tierColor = "#10b981"; // active
        let tierLabel = "Active";
        if (c.record_tier === "closed" || c.status === "closed") {
          tierColor = "#64748b";
          tierLabel = "Closed (Fully Paid)";
        } else if (c.record_tier === "historic") {
          tierColor = "#8b5cf6";
          tierLabel = "Historic Legacy";
        }
        if (c.status === "defaulted" || c.status === "written_off") {
          tierColor = "#ef4444";
          tierLabel = "Defaulted";
        }

        card.innerHTML = `
          <div style="display: flex; align-items: center; justify-content: space-between;">
            <div style="display: flex; align-items: center; gap: 10px;">
              <span style="display: inline-flex; align-items: center; justify-content: center; width: 32px; height: 32px; border-radius: 50%; background: ${isCurrent ? 'var(--primary)' : 'var(--border)'}; color: #fff; font-weight: 800; font-size: 0.85rem;">
                C${c.cycle_number}
              </span>
              <div>
                <strong style="font-size: 0.95rem; color: var(--text);">Account #${c.ano}</strong>
                ${isCurrent ? '<span class="status-badge" style="background: rgba(14, 165, 233, 0.2); color: var(--primary); padding: 1px 6px; font-size: 0.7rem; margin-left: 6px;">CURRENT VIEW</span>' : ''}
                <div style="font-size: 0.75rem; color: var(--text-secondary); margin-top: 2px;">
                  ${c.start_date || 'N/A'} ➔ ${c.end_date || 'N/A'} &bull; Period: ${c.period} (${c.type})
                </div>
              </div>
            </div>
            <div style="text-align: right;">
              <span class="status-badge" style="background: ${tierColor}20; color: ${tierColor}; border: 1px solid ${tierColor}40; font-weight: 700;">
                ${tierLabel}
              </span>
              <div style="font-size: 0.75rem; font-weight: 600; color: var(--text-secondary); margin-top: 4px;">
                Rating: <strong style="color: var(--text);">${c.customer_rating ? c.customer_rating.toFixed(1) : '100.0'}</strong>
              </div>
            </div>
          </div>
          <div style="display: grid; grid-template-columns: repeat(3, 1fr); gap: 8px; margin-top: 6px; padding-top: 8px; border-top: 1px dashed var(--border); font-size: 0.8rem;">
            <div>Loan: <strong>${formatMoney(c.total_amount)}</strong></div>
            <div>Repaid: <strong style="color: var(--success);">${formatMoney(c.paid_amount)}</strong></div>
            <div>Balance: <strong style="${c.balance_amount > 0 ? 'color: var(--danger);' : ''}">${formatMoney(c.balance_amount)}</strong></div>
          </div>
          ${!isCurrent ? `
            <div style="display: flex; justify-content: flex-end; margin-top: 6px;">
              <button class="neumorphic-btn small" onclick="closeBorrowerLineageModal(); openCustomerPopup('${c.cid || c.ano}');" style="font-size: 11px; padding: 4px 10px;">
                <i class="fas fa-folder-open"></i> Switch to Account #${c.ano}
              </button>
            </div>
          ` : ''}
        `;
        timelineContainer.appendChild(card);
      });

    } catch (err) {
      if (timelineContainer) {
        timelineContainer.innerHTML = `<div style="text-align: center; padding: 20px; color: var(--danger);">${err.message || "Failed to load borrower lineage."}</div>`;
      }
    }
  };

  window.closeBorrowerLineageModal = function () {
    const modal = document.getElementById("popBorrowerLineageModal");
    if (modal) {
      modal.style.display = "none";
      modal.classList.remove("active");
    }
  };

  // Close lineage modal on backdrop click
  const lineageModal = document.getElementById("popBorrowerLineageModal");
  if (lineageModal) {
    lineageModal.addEventListener("click", function(e) {
      if (e.target === lineageModal) {
        closeBorrowerLineageModal();
      }
    });
  }

});