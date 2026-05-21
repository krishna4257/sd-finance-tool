document.addEventListener("DOMContentLoaded", function () {
  const table = document.getElementById("customerTable");
  const tableBody = document.getElementById("customerTableBody");
  const rows = Array.from(tableBody.querySelectorAll("tr"));

  const headers = Array.from(table.querySelectorAll("thead th")).map(th => th.textContent.trim().toLowerCase().replace(/\s+/g, "_"));

  const amtIndex  = headers.indexOf("total_amount");
  const pamtIndex = headers.indexOf("paid_amount");
  const bamtIndex = headers.indexOf("balance_amount");
  const panoIndex = headers.indexOf("pano");

  const anoIdx = headers.indexOf("ano");
  const nameIdx = headers.indexOf("name");

  function formatDate(value) {
    if (!value) return "";

    const str = String(value).trim();

    // Match YYYY-MM-DD only
    const match = str.match(/^(\d{4})-(\d{2})-(\d{2})$/);

    if (!match) {
      return value;
    }

    const [, year, month, day] = match;
    return `${day}-${month}-${year}`;
  }
  
  const clean = v => v.replace(/[₹,]/g, "").trim();
  // 🔒 Immutable snapshot (single source of truth)
  const snapshot = rows.map(row => {
    const cells = row.children;
    return {
      row,
      ano: clean(cells[anoIdx]?.textContent || "").toLowerCase(),
      pano: clean(cells[panoIndex]?.textContent || "").toLowerCase(),
      name: (cells[nameIdx]?.textContent || "").trim().toLowerCase(),
      phone_number: (cells[headers.indexOf("phone_number")]?.textContent || "").trim(),
      total_amount: parseFloat(clean(cells[amtIndex]?.textContent || "0")) || 0,
      paid_amount: parseFloat(clean(cells[pamtIndex]?.textContent || "0")) || 0,
      balance_amount: parseFloat(clean(cells[bamtIndex]?.textContent || "0")) || 0,
    };
  });

  function updateSummary() {
    const visible = snapshot.filter(d => d.row.style.display !== "none");
    const total = visible.length;
    const sumAmt  = visible.reduce((s, d) => s + d.total_amount, 0);
    const sumPamt = visible.reduce((s, d) => s + d.paid_amount, 0);
    const sumBamt = visible.reduce((s, d) => s + d.balance_amount, 0);

    document.getElementById("totalCustomers").textContent = total;
    document.getElementById("sumAmt").textContent  = sumAmt.toFixed(2);
    document.getElementById("sumPamt").textContent = sumPamt.toFixed(2);
    document.getElementById("sumBamt").textContent = sumBamt.toFixed(2);

      // ✅ Apply ₹ formatting after updating values
    if (typeof applyGlobalMoneyFormatting === "function") {
      applyGlobalMoneyFormatting();
    }
    requestAnimationFrame(() => {
       table.style.width = "auto";  
    });
  }

  window.applySearch = function () {
    const rawTerm = document.getElementById("searchBox").value.trim();

    // Parent search multi-account support
    if (window.location.search.includes("parent_search=1") && rawTerm.includes(",")) {
      const accountList = rawTerm
        .split(",")
        .map(v => v.trim().toLowerCase())
        .filter(Boolean);

      snapshot.forEach(d => {
        d.row.style.display = accountList.includes(d.ano) ? "" : "none";
      });

      updateSummary();
      return;
    }

    const term = rawTerm.toLowerCase();

    // Empty search → show all
    if (!term) {
      snapshot.forEach(d => {
        d.row.style.display = "";
      });
      updateSummary();
      return;
    }

    // 📱 Mobile number search (10 digits)
    const isPhoneSearch = /^\d{10}$/.test(term);

    // 🔢 Account number search (only digits, but not 10-digit phone)
    const isAnoSearch = /^\d+$/.test(term) && !isPhoneSearch;

    // 🔤 Name search (contains letters)
    const isNameSearch = /[a-z]/i.test(rawTerm);

    snapshot.forEach(d => {
      const phone = (d.phone_number || "").toLowerCase();

      let show = false;

      if (isPhoneSearch) {
        show = phone === term;
      } else if (isAnoSearch) {
        // Exact ano match only
        show = d.ano === term;
      } else if (isNameSearch) {
        // Name contains only
        show = d.name.includes(term);
      }

      d.row.style.display = show ? "" : "none";
    });

    updateSummary();
  };

  window.resetSearch = function () {
    document.getElementById("searchBox").value = "";

    // Detect parent-search mode BEFORE removing params
    const wasParentSearch = window.location.search.includes("parent_search=1");

    // Remove parent search state from URL
    const url = new URL(window.location.href);
    url.searchParams.delete("parent_search");
    url.searchParams.delete("search");

    // Parent-search rebuild cannot be restored safely.
    // Reload original table state.
    if (wasParentSearch) {
      window.location.href = url.pathname;
      return;
    }

    window.history.replaceState({}, "", url);

    snapshot.forEach(d => (d.row.style.display = ""));
    table.querySelectorAll("input[type='checkbox']").forEach(cb => cb.checked = false);

    updateSummary();
  };

  window.toggleAll = function (source) {
    tableBody.querySelectorAll("input[type='checkbox']").forEach(cb => cb.checked = source.checked);
  };

  window.printSelected = function () {
    const selected = Array.from(tableBody.querySelectorAll("input[type='checkbox']:checked")).map(cb => cb.closest("tr"));
    const rowsToPrint = selected.length > 0 ? selected : snapshot.filter(d => d.row.style.display !== "none").map(d => d.row);


    let html = "<html><head><title>Print</title><style>table{border-collapse:collapse;width:100%}td,th{border:1px solid #ccc;padding:6px}</style></head><body><h2>Selected Customers</h2><table><thead><tr>";
    const headerCells = table.querySelectorAll("thead th");
    for (let i = 1; i < headerCells.length; i++) {
      html += "<th>" + headerCells[i].textContent + "</th>";
    }
    html += "</tr></thead><tbody>";

    rowsToPrint.forEach(row => {
      html += "<tr>";
      for (let i = 1; i < row.children.length; i++) {
        html += "<td>" + row.children[i].textContent + "</td>";
      }
      html += "</tr>";
    });

    html += "</tbody></table></body></html>";
    const w = window.open("", "", "width=900,height=600");
    w.document.write(html);
    w.document.close();
    w.print();
  };

  window.applyParentSearch = async function () {

  const rawTerm = document.getElementById("searchBox").value.trim();
  const term = rawTerm.toLowerCase();

  if (!term) {
    window.location.reload();
    return;
  }

  try {

    const response = await fetch(
      `/api/customer_family_full/${encodeURIComponent(term)}`
    );

    if (!response.ok) {
      throw new Error(`HTTP ${response.status}`);
    }

    const result = await response.json();

    console.log("Parent search result:", result);

    if (!result.success) {
      alert(result.error || "Unable to load parent accounts.");
      return;
    }

    const customers = result.customers || [];

    if (customers.length === 0) {
      alert("No related accounts found.");
      return;
    }

    // Normalize helper
    const normalizeAccount = (value) => {
      let normalized = String(value || "").trim().toLowerCase();

      if (normalized.endsWith('.0')) {
        normalized = normalized.slice(0, -2);
      }

      return normalized;
    };

    // Find searched customer
    const searchedCustomer = customers.find(customer => {
      return normalizeAccount(customer.ano) === term;
    });

    if (!searchedCustomer) {
      alert("Customer not found.");
      return;
    }

    const parentAno = normalizeAccount(searchedCustomer.pano);

    // ONLY keep:
    // 1. searched customer
    // 2. direct parent customer
    // 3. direct child customers
    const filteredCustomers = customers.filter(customer => {

      const ano = normalizeAccount(customer.ano);
      const pano = normalizeAccount(customer.pano);

      return (
        ano === term ||
        ano === parentAno ||
        pano === term
      );
    });

    // Completely destroy old DataTable before rebuilding rows
    if ($.fn.DataTable.isDataTable('#customerTable')) {
      $('#customerTable').DataTable().clear().destroy();
    }
    tableBody.innerHTML = "";

    filteredCustomers.forEach(customer => {

    // Force browser to fully commit rebuilt rows
    tableBody.offsetHeight;

      const tr = document.createElement("tr");
      tr.className = "table-row";

      const checkboxTd = document.createElement("td");
      checkboxTd.innerHTML = `<input type="checkbox" />`;

      tr.appendChild(checkboxTd);

      // Build ALL table columns exactly like original table
      headers.forEach((header, index) => {

        // Skip checkbox column because already added manually
        if (index === 0) {
          return;
        }

        const td = document.createElement("td");
        td.className = "table-cell";

        let value = customer[header];

        if (value === null || value === undefined) {
          value = "";
        }

        if (
          [
            "total_amount",
            "paid_amount",
            "balance_amount",
            "installment_amount"
          ].includes(header)
        ) {

          td.setAttribute("data-money", "");
          td.textContent = value;

        } else if (header === "status") {

          td.innerHTML = `
            <span class="status-badge status-${String(value)
              .toLowerCase()
              .replace(/\s+/g, "-")}">
              ${value}
            </span>
          `;

        } else if (["start_date", "end_date"].includes(header)) {

          td.textContent = formatDate(value);

        } else {

          td.textContent = value;
        }

        tr.appendChild(td);
      });

      // Ensure row has exact same column count as original table
      while (tr.children.length < table.querySelectorAll("thead th").length) {
        const emptyTd = document.createElement("td");
        emptyTd.className = "table-cell";
        emptyTd.textContent = "";
        tr.appendChild(emptyTd);
      }

      tableBody.appendChild(tr);
    });


    // Reinitialize DataTable properly after rebuilding rows
    const rebuiltTable = $('#customerTable').DataTable({
      destroy: true,
      paging: false,
      info: false,
      searching: false,
      ordering: false,
      autoWidth: true,
      scrollX: false,
      scrollCollapse: false,
      fixedHeader: false
    });

    // Restore default hidden columns
    const DEFAULT_HIDDEN_COLUMNS = [
      "cid",
      "vid",
      "created_at",
      "aadhaar_number",
      "latitude",
      "longitude",
      "eid",
      "status",
      "installment_amount",
      "phone_number",
      "notes"
    ];

    rebuiltTable.columns().every(function () {

      const headerText = this.header().innerText
        .trim()
        .toLowerCase()
        .replace(/\s+/g, "_");

      if (DEFAULT_HIDDEN_COLUMNS.includes(headerText)) {
        this.visible(false, false);
      }
    });

    setTimeout(() => {
      rebuiltTable.columns.adjust().draw(false);

      const wrapper = document.querySelector('#customerTable_wrapper');
      if (wrapper) {
        wrapper.style.width = '100%';
      }

      table.style.width = '100%';
      table.style.tableLayout = 'auto';
    }, 50);

    // Rebuild snapshot with new parent-search rows
    snapshot.length = 0;

    Array.from(tableBody.querySelectorAll("tr")).forEach(row => {
      const cells = row.children;
      snapshot.push({
        row,
        ano: clean(cells[anoIdx]?.textContent || "").toLowerCase(),
        pano:
          panoIndex >= 0
            ? clean(cells[panoIndex]?.textContent || "").toLowerCase()
            : "",
        name: (cells[nameIdx]?.textContent || "").trim().toLowerCase(),
        phone_number: (cells[headers.indexOf("phone_number")]?.textContent || "").trim(),
        total_amount: parseFloat(clean(cells[amtIndex]?.textContent || "0")) || 0,
        paid_amount: parseFloat(clean(cells[pamtIndex]?.textContent || "0")) || 0,
        balance_amount: parseFloat(clean(cells[bamtIndex]?.textContent || "0")) || 0,
      });
    });

    updateSummary();

    if (typeof applyGlobalMoneyFormatting === "function") {
      applyGlobalMoneyFormatting();
    }

    snapshot.forEach(d => {
      d.row.style.display = "";
    });

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

  // Sorting support
  function sortTable(colIndex) {
    const key = colIndex;
    if (!window.sortState) window.sortState = {};
    if (!window.sortState[key]) window.sortState[key] = 0;
    window.sortState[key]++;

    let visible = snapshot.filter(d => d.row.style.display !== "none");

    if (window.sortState[key] % 3 === 1) {
      visible.sort((a, b) =>
        clean(a.row.cells[colIndex].textContent)
          .localeCompare(clean(b.row.cells[colIndex].textContent), undefined, { numeric: true })
      );
    } else if (window.sortState[key] % 3 === 2) {
      visible.sort((a, b) =>
        clean(b.row.cells[colIndex].textContent)
          .localeCompare(clean(a.row.cells[colIndex].textContent), undefined, { numeric: true })
      );
    } else {
      visible = [...snapshot].filter(r => r.row.style.display !== "none");
    }

    tableBody.innerHTML = "";
    visible.forEach(d => tableBody.appendChild(d.row));
    updateSummary();
  }

  table.querySelectorAll("thead th").forEach((th, i) => {
    if (i === 0) return;

    th.classList.remove("sorting", "sorting_asc", "sorting_desc");
    th.style.backgroundImage = "none";
    th.style.cursor = "pointer";

    th.addEventListener("click", () => sortTable(i));
  });

  // Auto-run parent search from URL params
  const urlParams = new URLSearchParams(window.location.search);
  const initialSearch = urlParams.get("search") || "";
  const isParentSearch = urlParams.get("parent_search") === "1";

  if (initialSearch) {
    const searchBox = document.getElementById("searchBox");

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
    headers.forEach((header, index) => {
      if (["start_date", "end_date"].includes(header)) {
        // headers array already includes checkbox column,
        // so indexes already match row.children
        const cell = row.children[index];

        if (cell) {
          cell.textContent = formatDate(cell.textContent);
        }
      }
    });
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
  const DEFAULT_HIDDEN_COLUMNS = [
    "cid",
      "vid",
      "created_at",
      "aadhaar_number",
      "latitude",
      "longitude",
      "eid",
      "status",
      "installment_amount",
      "phone_number",
      "notes"
  ];

  const table = $.fn.DataTable.isDataTable('#customerTable')
    ? $('#customerTable').DataTable()
    : $('#customerTable').DataTable({
        paging: false,
        info: false,
        searching: false,
        ordering: false,
        autoWidth: false,
        scrollX: true,
        scrollCollapse: true,
        fixedHeader: false
      });

  // Always reset to default column visibility on page load
  table.columns().every(function () {
    const headerText = this.header().innerText
      .trim()
      .toLowerCase()
      .replace(/\s+/g, "_");

    if (DEFAULT_HIDDEN_COLUMNS.includes(headerText)) {
      this.visible(false, false);
    } else {
      this.visible(true, false);
    }
  });

  table.columns.adjust().draw(false);

  const modal = document.getElementById("columnModal");
  const list = document.getElementById("columnCheckboxList");
  const openBtn = document.getElementById("tableViewBtn");
  const closeBtn = document.getElementById("closeColumnModal");

  // Open modal
  if (openBtn) openBtn.addEventListener("click", () => {
    list.innerHTML = "";

    table.columns().every(function (index) {
      // Skip checkbox column (index 0)
      if (index === 0) return;

      const column = this;
      const headerText = column.header().innerText;

      const wrapper = document.createElement("label");
      wrapper.className = "column-item compact";

      const checkbox = document.createElement("input");
      checkbox.type = "checkbox";
      checkbox.checked = column.visible();

      checkbox.addEventListener("change", () => {
        column.visible(checkbox.checked, false);
        table.columns.adjust().draw(false);
      });

      wrapper.appendChild(checkbox);
      wrapper.appendChild(document.createTextNode(headerText));

      list.appendChild(wrapper);
    });

    modal.classList.remove("hidden");
  });

  // Close modal
  if (closeBtn) closeBtn.addEventListener("click", () => {
    modal.classList.add("hidden");
  });

  // Close on backdrop click
  modal.addEventListener("click", (e) => {
    if (e.target === modal) {
      modal.classList.add("hidden");
    }
  });
});