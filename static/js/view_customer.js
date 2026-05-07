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

  window.applyParentSearch = function () {
    const term = document.getElementById("searchBox").value.trim().toLowerCase();

    if (!term) {
      snapshot.forEach(d => (d.row.style.display = ""));
      updateSummary();
      return;
    }

    snapshot.forEach(d => {
      // Show:
      // 1) the searched customer (ano === term)
      // 2) the parent record (ano === pano of searched)
      // 3) the child record (pano === term)
      const show =
        d.ano === term ||
        d.pano === term ||
        snapshot.some(x => x.ano === term && d.ano === x.pano);

      d.row.style.display = show ? "" : "none";
    });

    updateSummary();
  };

  window.filterYearlyReport = function () {
    snapshot.forEach(d => {d.row.style.display = d.balance_amount > 0 ? "" : "none";});
    updateSummary();
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
    th.style.cursor = "pointer";
    th.addEventListener("click", () => sortTable(i));
  });

  updateSummary();
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
    "eid"
  ];

  const table = $.fn.DataTable.isDataTable('#customerTable')
    ? $('#customerTable').DataTable()
    : $('#customerTable').DataTable({ paging: false, info: false });

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

  table.columns.adjust();

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
        table.columns.adjust();
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