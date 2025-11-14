let originalData = JSON.parse(document.getElementById("payment-data").textContent);

document.addEventListener("DOMContentLoaded", () => {
  try {
    const raw = document.getElementById("payment-data").textContent;
    originalData = JSON.parse(raw);
  } catch (e) {
    console.error("❌ Failed to parse payments data:", e);
    return;
  }

  filteredData = [...originalData];
  renderTable(filteredData);

  // Add filter event listeners
  document.getElementById("filterAno").addEventListener("input", applyFilters);
  document.getElementById("filterFrom").addEventListener("change", applyFilters);
  document.getElementById("filterTo").addEventListener("change", applyFilters);
  document.getElementById("resetBtn").addEventListener("click", resetFilters);
});

function renderTable(data) {
  const tbody = document.getElementById("reportBody");
  tbody.innerHTML = "";

  let totalAmt = 0;
  const uniqueAno = new Set();

  data.forEach(([ano, pdt, amt]) => {
    uniqueAno.add(ano);
    totalAmt += parseFloat(amt);

    const tr = document.createElement("tr");
    tr.innerHTML = `
      <td>${ano}</td>
      <td>${pdt}</td>
      <td><span data-money>${amt}</span></td>
    `;
    tbody.appendChild(tr);
  });

  document.getElementById("totalAmt").textContent = totalAmt.toFixed(2);
  document.getElementById("totalAno").textContent = uniqueAno.size;
}

function applyFilters() {
  const ano = document.getElementById("filterAno").value.trim();
  const from = document.getElementById("filterFrom").value.trim();
  const to = document.getElementById("filterTo").value.trim();

  // Ensure the helper function from date_helpers.js is available
  if (typeof parseDDMMYYYY !== 'function') {
    console.error("Date helper function 'parseDDMMYYYY' not found. Make sure date_helpers.js is loaded.");
    return;
  }

  const fromDate = from ? parseDDMMYYYY(from) : null;
  const toDate = to ? parseDDMMYYYY(to) : null;

  filteredData = originalData.filter(([rowAno, rowPdt]) => {
    // Filter by Account Number (ANO)
    if (ano && rowAno.toString() !== ano) {
      return false;
    }

    // --- Corrected Date Filtering Logic ---

    // Case 1: Only "From Date" is entered, so we do an EXACT match.
    if (from && !to) {
      if (rowPdt !== from) {
        return false;
      }
    }
    // Case 2: Both "From" and "To" dates are entered, so we check if the row's date is within the RANGE.
    else if (from && to && fromDate && toDate) {
      const rowDate = parseDDMMYYYY(rowPdt);
      if (!rowDate || rowDate < fromDate || rowDate > toDate) {
        return false;
      }
    }

    // If the row passes all active filters, keep it.
    return true;
  });

  renderTable(filteredData);
}

function resetFilters() {
  document.getElementById("filterAno").value = "";
  document.getElementById("filterFrom").value = "";
  document.getElementById("filterTo").value = "";
  filteredData = [...originalData];
  renderTable(filteredData);
}

function sortReport(col) {
  const colIndex = { "ano": 0, "pdt": 1, "amt": 2 }[col];
  const isDate = col === "pdt";
  const isAmt = col === "amt";

  filteredData.sort((a, b) => {
    let valA = isDate ? new Date(a[colIndex]) : (isAmt ? parseFloat(a[colIndex]) : a[colIndex]);
    let valB = isDate ? new Date(b[colIndex]) : (isAmt ? parseFloat(b[colIndex]) : b[colIndex]);
    return valA > valB ? 1 : -1;
  });

  renderTable(filteredData);
}
