document.addEventListener("DOMContentLoaded", function () {
  const table = document.getElementById("customerTable");
  const tableBody = document.getElementById("customerTableBody");
  const originalRows = [...tableBody.querySelectorAll("tr")];

  const headers = [...table.querySelectorAll("thead th")].map(th => th.textContent.trim());
  const amtIndex = headers.indexOf("AMT");
  const pamtIndex = headers.indexOf("PAMT");
  const bamtIndex = headers.indexOf("BAMT");
  const panoIndex = headers.indexOf("PANO");

  function clean(val) {
    return val.replace(/[₹,]/g, "").trim();
  }

  function updateSummary() {
    const visibleRows = [...tableBody.querySelectorAll("tr")].filter(row => row.style.display !== "none");
    let total = visibleRows.length, sumAmt = 0, sumPamt = 0, sumBamt = 0;

    visibleRows.forEach(row => {
      const cells = row.children;
      if (amtIndex !== -1) sumAmt += parseFloat(clean(cells[amtIndex]?.textContent || "0")) || 0;
      if (pamtIndex !== -1) sumPamt += parseFloat(clean(cells[pamtIndex]?.textContent || "0")) || 0;
      if (bamtIndex !== -1) sumBamt += parseFloat(clean(cells[bamtIndex]?.textContent || "0")) || 0;
    });

    document.getElementById("totalCustomers").textContent = total;
    document.getElementById("sumAmt").textContent = sumAmt.toFixed(2);
    document.getElementById("sumPamt").textContent = sumPamt.toFixed(2);
    document.getElementById("sumBamt").textContent = sumBamt.toFixed(2);

      // ✅ Apply ₹ formatting after updating values
    if (typeof applyGlobalMoneyFormatting === "function") {
      applyGlobalMoneyFormatting();
    }
  }

  window.applySearch = function () {
    const term = document.getElementById("searchBox").value.trim().toLowerCase();
    originalRows.forEach(row => {
      const ano = clean(row.children[1]?.textContent || "").toLowerCase();
      const name = clean(row.children[2]?.textContent || "").toLowerCase();
      row.style.display = (term === "" || ano === term || name.includes(term)) ? "" : "none";
    });
    updateSummary();
  };

  window.resetSearch = function () {
    document.getElementById("searchBox").value = "";
    originalRows.forEach(row => row.style.display = "");
    table.querySelectorAll("input[type='checkbox']").forEach(cb => cb.checked = false);
    updateSummary();
  };

  window.toggleAll = function (source) {
    const checkboxes = tableBody.querySelectorAll("input[type='checkbox']");
    checkboxes.forEach(cb => cb.checked = source.checked);
  };

  window.printSelected = function () {
    const selected = [...tableBody.querySelectorAll("input[type='checkbox']:checked")];
    const rows = selected.length > 0
      ? selected.map(cb => cb.closest("tr"))
      : [...tableBody.querySelectorAll("tr")].filter(r => r.style.display !== "none");

    let html = "<html><head><title>Print</title><style>table{border-collapse:collapse;width:100%}td,th{border:1px solid #ccc;padding:6px}</style></head><body><h2>Selected Customers</h2><table><thead><tr>";
    const headerCells = table.querySelectorAll("thead th");
    for (let i = 1; i < headerCells.length; i++) {
      html += "<th>" + headerCells[i].textContent + "</th>";
    }
    html += "</tr></thead><tbody>";

    rows.forEach(row => {
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

  function getFamilyChain(ano, rows) {
    const familySet = new Set();
    const parentMap = new Map();
    const childMap = new Map();

    rows.forEach(row => {
      const a = clean(row.children[1]?.textContent || "");
      const p = clean(row.children[panoIndex]?.textContent || "");
      if (a) parentMap.set(a, p);
      if (p) {
        if (!childMap.has(p)) childMap.set(p, []);
        childMap.get(p).push(a);
      }
    });

    const stack = [ano];
    while (stack.length) {
      const current = stack.pop();
      if (!familySet.has(current)) {
        familySet.add(current);
        const parent = parentMap.get(current);
        if (parent && !familySet.has(parent)) stack.push(parent);
        const children = childMap.get(current) || [];
        children.forEach(child => {
          if (!familySet.has(child)) stack.push(child);
        });
      }
    }

    return familySet;
  }

  window.applyParentSearch = function () {
    const term = document.getElementById("searchBox").value.trim().toLowerCase();
    const rows = [...tableBody.querySelectorAll("tr")];
    const matched = getFamilyChain(term, rows);

    rows.forEach(row => {
      const ano = clean(row.children[1]?.textContent || "").toLowerCase();
      row.style.display = matched.has(ano) || term === "" ? "" : "none";
    });

    updateSummary();
  };

  window.filterYearlyReport = function () {
    originalRows.forEach(row => {
      const bamtCell = row.children[bamtIndex];
      const bamt = parseFloat(clean(bamtCell?.textContent || "0")) || 0;
      row.style.display = bamt > 0 ? "" : "none";
    });
    updateSummary();
  };

  // Sorting support
  let sortState = {};
  function sortTable(columnIndex) {
    const colKey = `col-${columnIndex}`;
    sortState[colKey] = (sortState[colKey] || 0) + 1;

    let rows = [...tableBody.querySelectorAll("tr")].filter(row => row.style.display !== "none");
    const getValue = row => clean(row.cells[columnIndex].textContent);

    if (sortState[colKey] % 3 === 1) {
      rows.sort((a, b) => getValue(a).localeCompare(getValue(b), undefined, { numeric: true }));
    } else if (sortState[colKey] % 3 === 2) {
      rows.sort((a, b) => getValue(b).localeCompare(getValue(a), undefined, { numeric: true }));
    } else {
      rows = originalRows;
    }

    tableBody.innerHTML = "";
    rows.forEach(row => tableBody.appendChild(row));
    updateSummary();
  }

  const ths = table.querySelectorAll("thead th");
  ths.forEach((th, i) => {
    if (i === 0) return;
    th.style.cursor = "pointer";
    th.addEventListener("click", () => sortTable(i));
  });

  updateSummary();
});
