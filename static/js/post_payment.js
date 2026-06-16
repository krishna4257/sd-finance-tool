// --- Initialize sound effect ---
// Make sure you have a file at static/sounds/error.mp3
const errorSound = new Audio('static/sounds/error.mp3');

// Use sessionStorage instead of localStorage so unsaved payment rows
// do not leak across different employees using the same browser/device.
const POST_PAYMENT_STORAGE_KEY = 'postPayments';

function loadTempPayments() {
    try {
        return JSON.parse(sessionStorage.getItem(POST_PAYMENT_STORAGE_KEY) || '[]');
    } catch (e) {
        console.error('Failed to load temporary payments:', e);
        return [];
    }
}

function persistTempPayments() {
    sessionStorage.setItem(
        POST_PAYMENT_STORAGE_KEY,
        JSON.stringify(tempTable)
    );
}


let tempTable = loadTempPayments();
let selectedDate = null;
let lastWeekPaidCount = 0;
let lastWeekCollection = 0;
let isSubmittingPayments = false;
let expectedPayments = 0;
let alreadyPaidPayments = 0;
window.expandedDateTiles = window.expandedDateTiles || new Set();
window.tileSortStates = window.tileSortStates || {};


// --- Instant lookup mapping ---
const CUSTOMER_MAP = {};
let expectedAccCount = 0;
let expectedTotalAmount = 0;

function initCustomerMapAndStats() {
    (window.CUSTOMERS || []).forEach(c => {
        try {
            if (!c || c.ano === null || c.ano === undefined) {
                console.warn("Skipping invalid customer:", c);
                return;
            }

            // Normalize backend keys to the frontend expected shape
            const normalized = {
                ano: String(c.ano).trim(),
                name: c.name || "",
                amt: Number(c.total_amount) || 0,
                pamt: Number(c.paid_amount) || 0,
                bamt: Number(c.balance_amount) || 0,
                da: Number(c.installment_amount) || 0,
                start_date: c.start_date || ""
            };

            if (normalized.ano) {
                CUSTOMER_MAP[normalized.ano] = normalized;
            }
        } catch (err) {
            console.error("Failed loading customer:", c, err);
        }
    });

    // --- Expected Stats Calculations ---
    const activeCustomers = window.CUSTOMERS.filter(c => (Number(c.balance_amount) || 0) > 0);
    expectedAccCount = activeCustomers.length;
    expectedTotalAmount = activeCustomers.reduce((sum, c) => sum + (Number(c.installment_amount) || 0), 0);
}

// --- Helper function to show errors and play sound ---
function showError(message) {
    const errorMsg = document.getElementById("errorMsg");
    errorMsg.innerText = message;
    errorMsg.style.display = "block";
    // Play the sound, catching potential browser errors
    errorSound.play().catch(e => console.warn("Could not play error sound:", e));
}


function normalizeDateForComparison(dateStr) {
  if (!dateStr) return "";

  const parsed = parseISOorDDMMYYYY(dateStr);
  if (!parsed || isNaN(parsed.getTime())) {
    return "";
  }

  return formatDateToYYYYMMDD(parsed);
}

function isPostingDateValidForCustomer(ano, postingDate) {
  const customer = CUSTOMER_MAP[String(ano).trim()];
  if (!customer) {
    return { valid: false, error: "❌ A.no not found in database!" };
  }

  const postingIso = normalizeDateForComparison(postingDate);
  const startIso = normalizeDateForComparison(customer.start_date);
  const startDisplay = formatDateDDMMYYYY(customer.start_date);

  if (!postingIso) {
    return {
      valid: false,
      customer,
      error: "❌ Invalid posting date."
    };
  }

  if (!startIso) {
    console.error(
      "Unable to validate customer start_date:",
      ano,
      customer.start_date
    );

    return {
      valid: false,
      customer,
      error: `❌ Customer ANO - ${ano} has an invalid start date. Contact administrator.`
    };
  }

  if (postingIso < startIso) {
    return {
      valid: false,
      customer,
      error: `❌ Customer ANO - ${ano} start_date is ${startDisplay}. Posting date must be greater than or equal to start_date.`
    };
  }

  return { valid: true, customer };
}

function sanitizeTempPayments(rows) {
  const cleaned = [];
  const rejected = [];

  (rows || []).forEach((row, index) => {
    const ano = String(row?.ano ?? "").trim();
    const pdt = String(row?.pdt ?? "").trim();
    const amt = Number(row?.amt);

    if (!ano || !pdt || !Number.isFinite(amt) || amt <= 0) {
      rejected.push({ index, reason: "invalid_basic_fields", row });
      return;
    }

    const validation = isPostingDateValidForCustomer(ano, pdt);
    if (!validation.valid) {
      rejected.push({ index, reason: validation.error, row });
      return;
    }

    cleaned.push({ ano, pdt, amt });
  });

  return { cleaned, rejected };
}


async function loadPaymentDayStats() {

    const pdt = document.getElementById("pdt")?.value?.trim();

    if (!pdt) {
        expectedPayments = 0;
        alreadyPaidPayments = 0;
        updateCollectionStats();
        return;
    }

    try {


        const response = await fetch(
            `/api/payment_day_stats?date=${encodeURIComponent(pdt)}`
        );


        if (!response.ok) {
            throw new Error(`HTTP ${response.status}`);
        }

        const data = await response.json();


        if (data.error) {
            console.error("PAYMENT DAY STATS API ERROR =>", data.error);

            expectedPayments = 0;
            alreadyPaidPayments = 0;
            updateCollectionStats();

            return;
        }

        expectedPayments = Number(
            data.expected_accounts ||
            data.expectedPayments ||
            data.eligible_accounts ||
            0
        );

        alreadyPaidPayments = Number(
            data.already_paid ||
            data.paid_accounts ||
            data.alreadyPaid ||
            0
        );


        updateCollectionStats();

    } catch (err) {
        console.error("Failed loading collection stats:", err);

        expectedPayments = 0;
        alreadyPaidPayments = 0;
        updateCollectionStats();
    }
}

function updateCollectionStats() {

    const enteredToday = tempTable.length;

    const expected = expectedPayments;

    const missed = Math.max(
        expected - (alreadyPaidPayments + enteredToday),
        0
    );

    const expectedEl = document.getElementById("expectedPayments");
    const missedEl = document.getElementById("missedPayments");

    if (expectedEl) {
        expectedEl.textContent = expected;
    }

    if (missedEl) {
        missedEl.textContent = missed;
    }
}

let isEditingCell = false; // Prevent multiple cell editing sessions simultaneously
const pendingReportChanges = new Map(); // key=pid, value={field: newValue, ...}

function makeCellEditable(cell, index, field, currentValue) {
    if (isEditingCell) return;
    isEditingCell = true;

    // Clear highlights temporarily to avoid visual clash
    document.querySelectorAll('#tempTable tbody tr').forEach(r => {
        r.classList.remove('highlighted');
        r.classList.remove('highlighted-row');
    });
    window.currentRow = null;

    const input = document.createElement("input");
    input.className = "inline-edit-input";

    if (field === 'amt') {
        input.type = "number";
        input.step = "0.01";
        input.value = Number(currentValue).toFixed(2);
    } else {
        input.type = "text";
        input.value = currentValue;
    }

    cell.innerHTML = "";
    cell.appendChild(input);
    input.focus();

    let isFinished = false;

    function finishEdit(save) {
        if (isFinished) return;
        isFinished = true;
        isEditingCell = false;

        const errorMsg = document.getElementById("errorMsg");
        errorMsg.style.display = "none";

        if (!save) {
            updateTable();
            return;
        }

        const rawVal = input.value.trim();
        let parsedValue = rawVal;

        if (field === 'ano') {
            if (!parsedValue) {
                showError("❌ Account Number cannot be empty.");
                updateTable();
                return;
            }
            if (!/^\d+$/.test(parsedValue)) {
                showError("❌ Account Number must contain numbers only.");
                updateTable();
                return;
            }
            const customer = CUSTOMER_MAP[parsedValue];
            if (!customer) {
                showError("❌ Account Number not found in database!");
                updateTable();
                return;
            }
            // Check duplicates
            const duplicate = tempTable.some((row, i) => i !== index && row.ano === parsedValue && row.pdt === tempTable[index].pdt);
            if (duplicate) {
                showError("❌ Duplicate Account Number + Date combination in table.");
                updateTable();
                return;
            }
        } else if (field === 'pdt') {
            if (!parsedValue) {
                showError("❌ Payment Date cannot be empty.");
                updateTable();
                return;
            }
            // Check duplicate
            const duplicate = tempTable.some((row, i) => i !== index && row.ano === tempTable[index].ano && row.pdt === parsedValue);
            if (duplicate) {
                showError("❌ Duplicate Account Number + Date combination in table.");
                updateTable();
                return;
            }
        } else if (field === 'amt') {
            parsedValue = parseFloat(rawVal);
            if (isNaN(parsedValue) || parsedValue <= 0) {
                showError("❌ Please enter a valid positive amount.");
                updateTable();
                return;
            }
        }

        tempTable[index][field] = parsedValue;
        saveAndUpdate();
    }

    input.addEventListener("keydown", function(e) {
        if (e.key === "Enter") {
            e.preventDefault();
            finishEdit(true);
        } else if (e.key === "Escape") {
            e.preventDefault();
            finishEdit(false);
        }
    });

    if (field === 'pdt') {
        window.initCustomCalendar(input, {
            clickOpens: true,
            noWrapper: true,
            onClose: function() {
                setTimeout(() => finishEdit(true), 150);
            }
        });
        setTimeout(() => {
            if (document.activeElement === input) {
                input.click();
            }
        }, 50);
    } else {
        input.addEventListener("blur", function() {
            setTimeout(() => finishEdit(true), 150);
        });
    }
}

function updateTable() {
  const tbody = document.querySelector("#tempTable tbody");
  
  // Try to preserve row highlight index
  let highlightedIndex = -1;
  if (window.currentRow && window.currentRow.closest("#tempTable")) {
      const oldRows = Array.from(document.querySelectorAll("#tempTable tbody tr"));
      highlightedIndex = oldRows.indexOf(window.currentRow);
  }

  tbody.innerHTML = "";
  const uniqueAno = new Set();
  let totalAmt = 0;

  tempTable.forEach((row, index) => {
    const tr = document.createElement("tr");

    const anoCell = document.createElement("td");
    anoCell.textContent = row.ano;
    anoCell.style.cursor = "pointer";
    anoCell.title = "Double-click to edit";
    anoCell.addEventListener("dblclick", (e) => {
        e.stopPropagation();
        makeCellEditable(anoCell, index, 'ano', row.ano);
    });

    const pdtCell = document.createElement("td");
    pdtCell.textContent = row.pdt;
    pdtCell.style.cursor = "pointer";
    pdtCell.title = "Double-click to edit";
    pdtCell.addEventListener("dblclick", (e) => {
        e.stopPropagation();
        makeCellEditable(pdtCell, index, 'pdt', row.pdt);
    });

    const amtCell = document.createElement("td");
    amtCell.classList.add("amount-paid");
    amtCell.style.cursor = "pointer";
    amtCell.title = "Double-click to edit";

    const amtText = document.createElement("span");
    amtText.textContent = row.amt?.toFixed(2) || "0.00";
    amtText.setAttribute('data-money', '');
    amtCell.appendChild(amtText);

    amtCell.addEventListener("dblclick", (e) => {
        e.stopPropagation();
        makeCellEditable(amtCell, index, 'amt', row.amt);
    });

    const cumulativeCell = document.createElement("td");
    cumulativeCell.classList.add("cumulative-amt");
    cumulativeCell.textContent = "";

    const deleteCell = document.createElement("td");
    deleteCell.style.textAlign = "center";

    const deleteBtn = document.createElement("button");
    deleteBtn.innerHTML = "&times;";
    deleteBtn.className = "delete-row-btn";
    deleteBtn.title = "Delete Row";
    deleteBtn.addEventListener("click", (e) => {
        e.stopPropagation();
        tempTable.splice(index, 1);
        saveAndUpdate();
    });
    deleteCell.appendChild(deleteBtn);

    tr.appendChild(anoCell);
    tr.appendChild(pdtCell);
    tr.appendChild(amtCell);
    tr.appendChild(cumulativeCell);
    tr.appendChild(deleteCell);

    tbody.appendChild(tr);
    uniqueAno.add(row.ano);
    totalAmt += row.amt;
  });

  document.getElementById("totalAnotop").textContent = uniqueAno.size;
  document.getElementById("totalAmttop").textContent = totalAmt.toFixed(2);
  document.getElementById("totalAno").textContent = uniqueAno.size;
  document.getElementById("totalAmt").textContent = totalAmt.toFixed(2);

  // Update expected and short-by stats in summary card widgets
  document.getElementById("expectedAccs").textContent = expectedAccCount;
  document.getElementById("shortAccs").textContent = Math.max(0, expectedAccCount - uniqueAno.size);

  document.getElementById("expectedAmt").textContent = expectedTotalAmount.toFixed(2);
  document.getElementById("expectedAmt").setAttribute("data-money", "");
  
  const shortAmtVal = Math.max(0, expectedTotalAmount - totalAmt);
  document.getElementById("shortAmt").textContent = shortAmtVal.toFixed(2);
  document.getElementById("shortAmt").setAttribute("data-money", "");

  persistTempPayments();

  // Cumulative Sum Logic
  let runningTotal = 0;
  const rows = Array.from(document.querySelectorAll("#tempTable tbody tr")).reverse();

  rows.forEach(row => {
    const amtSpan = row.querySelector("td.amount-paid span");
    const cumulativeCell = row.querySelector("td.cumulative-amt");
    
    if (amtSpan) {
        const amt = parseFloat(amtSpan.textContent.trim().replace(/[^\d.-]/g, '')) || 0;
        runningTotal += amt;
        cumulativeCell.textContent = runningTotal.toFixed(2);
        cumulativeCell.setAttribute('data-money', '');
    } else {
        const input = row.querySelector("td.amount-paid input");
        const amt = parseFloat(input?.value) || 0;
        runningTotal += amt;
        cumulativeCell.textContent = runningTotal.toFixed(2);
        cumulativeCell.setAttribute('data-money', '');
    }
  });

  updateComparativeStats();
  applyGlobalMoneyFormatting();
  updateCollectionStats();

  // Restore row highlight index if applicable
  if (highlightedIndex !== -1) {
      const newRows = document.querySelectorAll("#tempTable tbody tr");
      if (newRows.length > 0) {
          const indexToHighlight = Math.min(highlightedIndex, newRows.length - 1);
          window.currentRow = newRows[indexToHighlight];
          window.currentRow.classList.add("highlighted-row");
      } else {
          window.currentRow = null;
      }
  }
}



let sortState = { ano: 0, pdt: 0, amt: 0 };

function sortTemp(column) {
  for (let key in sortState) {
    if (key !== column) sortState[key] = 0;
  }
  sortState[column] = (sortState[column] + 1) % 3;

  if (sortState[column] === 0) {
    tempTable = loadTempPayments();
  } else {
    tempTable.sort((a, b) => {
      let valA = a[column];
      let valB = b[column];

      if (column === 'pdt') {
        valA = parseDDMMYYYY(valA);
        valB = parseDDMMYYYY(valB);
      } else if (column === 'amt') {
        valA = parseFloat(valA);
        valB = parseFloat(valB);
      } else if (column === 'ano') {
        valA = parseInt(valA, 10);
        valB = parseInt(valB, 10);
      }

      if (valA < valB) return sortState[column] === 1 ? -1 : 1;
      if (valA > valB) return sortState[column] === 1 ? 1 : -1;
      return 0;
    });
  }
  saveAndUpdate();
}

function saveAndUpdate() {
  const sanitized = sanitizeTempPayments(tempTable);
  tempTable = sanitized.cleaned;
  persistTempPayments();
  updateTable();

  if (sanitized.rejected.length > 0) {
    const firstError = sanitized.rejected[0]?.reason;
    if (typeof firstError === 'string' && firstError.startsWith('❌')) {
      showError(firstError);
    } else {
      showError("❌ Invalid rows were removed from the temporary table.");
    }
  }
}

function resetTempTable() {
  if (confirm("Are you sure you want to reset the entire table?")) {
    tempTable = [];
    saveAndUpdate();
  }
}

function printTemp() {
  tempTable.sort((a, b) => String(a.ano).localeCompare(String(b.ano)));

  let printHTML = '<html><head><title>Print Table</title>';
  printHTML += '<style>body { font-family: Arial; padding: 20px; } table { width: 100%; border-collapse: collapse; } th, td { border: 1px solid #ccc; padding: 8px; text-align: left; }</style>';
  printHTML += '</head><body><h2>📋 Temporary Payment Table</h2><table>';
  printHTML += '<thead><tr><th>ANO</th><th>PDT</th><th>AMT</th></tr></thead><tbody>';

  tempTable.forEach(row => {
    printHTML += `<tr><td>${row.ano}</td><td>${row.pdt}</td><td>${row.amt.toFixed(2)}</td></tr>`;
  });

  printHTML += '</tbody></table></body></html>';

  const printWindow = window.open('', '', 'height=600,width=800');
  printWindow.document.write(printHTML);
  printWindow.document.close();
  printWindow.print();
}

function submitAllPayments() {

  if (isSubmittingPayments) {
    console.log("Payment submission already in progress.");
    return;
  }

  if (tempTable.length === 0) {
    alert("There are no payments to submit.");
    return;
  }

  isSubmittingPayments = true;

  const submitBtn = document.querySelector(
    'button[onclick="submitAllPayments()"]'
  );

  if (submitBtn) {
    submitBtn.disabled = true;
    submitBtn.innerText = "Submitting...";
  }

  const payload = tempTable.map(row => ({
    ano: Number(row.ano),
    pdt: row.pdt,
    amt: Number(row.amt)
  }));

  csrfFetch("/submit_post_payment", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload)
  })
    .then(res => {
      if (!res.ok) {
        throw new Error(`Server responded with status: ${res.status}`);
      }
      return res.json();
    })
    .then(data => {
      const successMsg = document.getElementById("successMsg");

      successMsg.style.display = "block";
      successMsg.innerText = data.message;

      tempTable = data.skipped_rows;
      saveAndUpdate(); 
      // Refresh analytics graph as well
      loadAnalytics();
    })
    .catch(err => {
      showError(`An error occurred: ${err.message}`);
    })
    .finally(() => {

      isSubmittingPayments = false;

      if (submitBtn) {
        submitBtn.disabled = false;
        submitBtn.innerText = "📤 Submit All Payments";
      }
    });
}
document.getElementById("ano").addEventListener("input", function () {
    this.value = this.value.replace(/[^0-9]/g, "");
});
document.getElementById("paymentForm").addEventListener("submit", function (e) {
  e.preventDefault();

  const pdt = document.getElementById("pdt").value.trim();
  const ano = document.getElementById("ano").value.trim();
  const amt = parseFloat(document.getElementById("amt").value);


  if (!pdt) {
    showError("❌ Please enter payment date.");
    return;
  }

  if (!ano) {
    showError("❌ Please enter account number.");
    return;
  }

  if (isNaN(amt)) {
    showError("❌ Please enter amount.");
    return;
  }

  if (amt <= 0) {
    showError("❌ Enter amount > 0.");
    document.getElementById("amt").focus();
    return;
  }

  const customer = CUSTOMER_MAP[String(ano)];


  if (!customer) {
    showError("❌ A.no not found in database!");
    return;
  }

  const postingDateIso = normalizeDateForComparison(pdt);
  const customerStartDateIso = normalizeDateForComparison(customer.start_date);
  const customerStartDateDisplay = formatDateDDMMYYYY(customer.start_date);

  if (postingDateIso && customerStartDateIso && postingDateIso < customerStartDateIso) {
    showError(`❌ Customer ANO - ${ano} start_date is ${customerStartDateDisplay}. Posting date must be greater than or equal to start_date.`);
    document.getElementById("pdt").focus();
    return;
  }

  const duplicate = tempTable.some(
    row => String(row.ano) === String(ano) && row.pdt === pdt
  );


  if (duplicate) {
    showError("❌ Duplicate A.no + Date combo exists.");
    return;
  }

  tempTable.unshift({
    ano: String(ano),
    pdt,
    amt: Number(amt)
  });

  saveAndUpdate();

  // Automatically highlight the newly added row
  const firstRow = document.querySelector("#tempTable tbody tr");
  if (firstRow) {
      if (window.currentRow) {
          window.currentRow.classList.remove("highlighted-row");
      }
      window.currentRow = firstRow;
      window.currentRow.classList.add("highlighted-row");
  }

  document.getElementById("ano").value = "";
  document.getElementById("amt").value = "";

  document.getElementById("customerInfo").style.display = "none";

  document.getElementById("ano").focus();
});

document.getElementById("amt").disabled = true;
document.getElementById("amt").addEventListener("input", function () {
    const rawValue = this.value;
    const numericValue = parseFloat(rawValue);

    if (rawValue.trim() !== "" && !isNaN(numericValue) && numericValue <= 0) {
        showError("❌ Enter amount > 0.");
    }
});

document.getElementById("ano").addEventListener("keydown", function (e) {
    if (e.key !== "Enter") return;

    e.preventDefault();
    const ano = this.value.trim();
    const pdt = document.getElementById("pdt").value.trim();
    const errorMsg = document.getElementById("errorMsg");
    const customerInfo = document.getElementById("customerInfo");
    const amtInput = document.getElementById("amt");

    errorMsg.style.display = "none";
    customerInfo.style.display = "none";
    amtInput.disabled = true;

    if (!pdt) {
        showError("❌ Please enter a Payment Date first.");
        document.getElementById("pdt").focus();
        return;
    }

    const duplicateInTempTable = tempTable.some(row => row.ano === ano && row.pdt === pdt);
    if (duplicateInTempTable) {
        showError("❌ Duplicate: This payment is already in the temporary table below.");
        return;
    }

    // ---- INSTANT VALIDATION ----
    const customer = CUSTOMER_MAP[String(ano).trim()];
    if (!customer) {
        showError("❌ A.no not found in database!");
        return;
    }

    const startDateValidation = isPostingDateValidForCustomer(ano, pdt);
    if (!startDateValidation.valid) {
        showError(startDateValidation.error);
        return;
    }

    // SUCCESS
    document.getElementById("customerName").innerText = customer.name;
    document.getElementById("customerLoanAmount").innerText = customer.amt;
    document.getElementById("customerOutstanding").innerText = customer.bamt;
    document.getElementById("customerInstallmentAmount").innerText = customer.da;

    customerInfo.style.display = "grid"; // Show tiles grid
    amtInput.disabled = false;
    amtInput.focus();
});

// --- Helper short formatting function (e.g. 1.2L, 60K) ---
function formatAmountShort(value) {
  if (value >= 100000) {
    return (value / 100000).toFixed(value % 100000 === 0 ? 0 : 1) + 'L';
  } else if (value >= 1000) {
    return (value / 1000).toFixed(value % 1000 === 0 ? 0 : 1) + 'K';
  }
  return value;
}

// --- Weekly Analytics Graph & Details Card ---
let collectionChartInstance = null;

function renderCollectionChart(weeks) {
  const canvas = document.getElementById("collectionChart");
  if (!canvas) return;

  const ctx = canvas.getContext("2d");
  if (collectionChartInstance) {
    collectionChartInstance.destroy();
  }

  // Use CSS Variables dynamically to match the light theme
  const gridColor = getComputedStyle(document.documentElement).getPropertyValue('--border').trim() || '#e5e7eb';
  const tickColor = getComputedStyle(document.documentElement).getPropertyValue('--text-secondary').trim() || '#6b7280';
  const surfaceColor = getComputedStyle(document.documentElement).getPropertyValue('--surface').trim() || '#ffffff';
  const textColor = getComputedStyle(document.documentElement).getPropertyValue('--text').trim() || '#1f2937';

  // Use the exact week ending dates as X-axis labels
  const labels = weeks.map(w => w.end);
  const paidCustomers = weeks.map(w => w.paid_customers);
  const unpaidCustomers = weeks.map(w => w.unpaid_customers);
  const expectedAmounts = weeks.map(w => w.expected_collection);
  const actualAmounts = weeks.map(w => w.actual_collection);

  collectionChartInstance = new Chart(ctx, {
    type: 'bar',
    data: {
      labels: labels,
      datasets: [
        {
          label: 'Paid Customers',
          data: paidCustomers,
          type: 'bar',
          yAxisID: 'y-axis-counts',
          backgroundColor: '#1a4d2e', // Forest green
          borderColor: '#1a4d2e',
          borderWidth: 0,
          stack: 'stack-counts',
          borderRadius: 0,
          order: 3
        },
        {
          label: 'Unpaid Customers',
          data: unpaidCustomers,
          type: 'bar',
          yAxisID: 'y-axis-counts',
          backgroundColor: '#bbf7d0', // Soft mint green
          borderColor: '#bbf7d0',
          borderWidth: 0,
          stack: 'stack-counts',
          borderRadius: { topLeft: 6, topRight: 6, bottomLeft: 0, bottomRight: 0 },
          order: 4
        },
        {
          label: 'Expected Collection (₹)',
          data: expectedAmounts,
          type: 'line',
          yAxisID: 'y-axis-amounts',
          borderColor: '#10b981', // Flowy green line
          backgroundColor: 'transparent',
          pointBackgroundColor: '#10b981',
          pointRadius: 3.5,
          pointHoverRadius: 6,
          tension: 0.45,
          borderWidth: 2.5,
          order: 1
        },
        {
          label: 'Actual Collected (₹)',
          data: actualAmounts,
          type: 'line',
          yAxisID: 'y-axis-amounts',
          borderColor: '#f59e0b', // Flowy orange line
          backgroundColor: 'transparent',
          pointBackgroundColor: '#f59e0b',
          pointRadius: 3.5,
          pointHoverRadius: 6,
          tension: 0.45,
          borderWidth: 2.5,
          order: 2
        }
      ]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      interaction: {
        mode: 'index',
        intersect: false
      },
      plugins: {
        tooltip: {
          enabled: true,
          backgroundColor: surfaceColor,
          titleColor: textColor,
          bodyColor: textColor,
          borderColor: gridColor,
          borderWidth: 1,
          padding: 10,
          titleFont: { size: 11, weight: 'bold' },
          bodyFont: { size: 11 },
          callbacks: {
            title: function(context) {
              return "Date: " + context[0].label;
            },
            label: function(context) {
              let label = context.dataset.label || '';
              if (label) {
                label = label.replace(' (₹)', '') + ': ';
              }
              if (context.parsed.y !== null) {
                if (context.dataset.yAxisID === 'y-axis-amounts') {
                  label += new Intl.NumberFormat('en-IN', { style: 'currency', currency: 'INR', maximumFractionDigits: 0 }).format(context.parsed.y);
                } else {
                  label += context.parsed.y;
                }
              }
              return label;
            }
          }
        },
        legend: {
          display: false // Hide legend to match reference image
        }
      },
      scales: {
        'y-axis-counts': {
          type: 'linear',
          position: 'left',
          stacked: true, // Stack the Paid and Unpaid bars
          grid: {
            color: gridColor,
            drawOnChartArea: true
          },
          ticks: {
            color: tickColor,
            font: { size: 9 },
            precision: 0
          }
        },
        'y-axis-amounts': {
          type: 'linear',
          position: 'right',
          grid: {
            drawOnChartArea: false // prevent grid lines overlap
          },
          ticks: {
            color: tickColor,
            font: { size: 9 },
            callback: function(value) {
              return '₹' + formatAmountShort(value);
            }
          }
        },
        x: {
          stacked: true, // X stack align
          grid: {
            color: gridColor
          },
          ticks: {
            color: tickColor,
            font: { size: 9 }
          }
        }
      }
    }
  });
}

function renderAnalyticsTable(weeks) {
  const tbody = document.getElementById("analyticsTableBody");
  if (!tbody) return;
  tbody.innerHTML = "";

  weeks.forEach(w => {
    const tr = document.createElement("tr");

    const weekCell = document.createElement("td");
    // Show exact posting date instead of relative weeks
    weekCell.innerHTML = `<strong>${w.end}</strong>`;

    const activeCell = document.createElement("td");
    activeCell.textContent = w.active_customers;

    const paidCell = document.createElement("td");
    paidCell.textContent = w.paid_customers;

    const expectedCell = document.createElement("td");
    expectedCell.textContent = w.expected_collection.toFixed(2);
    expectedCell.setAttribute("data-money", "");

    const actualCell = document.createElement("td");
    actualCell.textContent = w.actual_collection.toFixed(2);
    actualCell.setAttribute("data-money", "");

    const failedCell = document.createElement("td");
    failedCell.textContent = w.failed_to_collect.toFixed(2);
    failedCell.setAttribute("data-money", "");
    failedCell.style.color = "#ef4444"; // red text for unpaid

    tr.appendChild(weekCell);
    tr.appendChild(activeCell);
    tr.appendChild(paidCell);
    tr.appendChild(expectedCell);
    tr.appendChild(actualCell);
    tr.appendChild(failedCell);

    tbody.appendChild(tr);
  });

  applyGlobalMoneyFormatting();
}

function updateComparativeStats() {
  const currentAno = parseInt(document.getElementById("totalAnotop").textContent) || 0;
  const currentAmt = parseFloat(document.getElementById("totalAmttop").textContent.replace(/[^\d.-]/g, '')) || 0;

  const lastAnoEl = document.getElementById("lastAnotop");
  const lastAmtEl = document.getElementById("lastAmttop");
  
  if (lastAnoEl) lastAnoEl.textContent = lastWeekPaidCount;
  if (lastAmtEl) {
    lastAmtEl.textContent = lastWeekCollection.toFixed(2);
    lastAmtEl.setAttribute("data-money", "");
  }

  // A.No comparison: Green up arrow if current > last, Red down arrow if current < last
  const lastAnoArrow = document.getElementById("lastAnoArrow");
  if (lastAnoArrow) {
    if (currentAno > lastWeekPaidCount) {
      lastAnoArrow.innerHTML = '<span style="color: #10b981;"><i class="fas fa-arrow-up"></i></span>';
    } else if (currentAno < lastWeekPaidCount) {
      lastAnoArrow.innerHTML = '<span style="color: #ef4444;"><i class="fas fa-arrow-down"></i></span>';
    } else {
      lastAnoArrow.innerHTML = '<span style="color: var(--text-secondary);"><i class="fas fa-minus"></i></span>';
    }
  }

  // Amount comparison: Green up arrow if current > last, Red down arrow if current < last
  const lastAmtArrow = document.getElementById("lastAmtArrow");
  if (lastAmtArrow) {
    if (currentAmt > lastWeekCollection) {
      lastAmtArrow.innerHTML = '<span style="color: #10b981;"><i class="fas fa-arrow-up"></i></span>';
    } else if (currentAmt < lastWeekCollection) {
      lastAmtArrow.innerHTML = '<span style="color: #ef4444;"><i class="fas fa-arrow-down"></i></span>';
    } else {
      lastAmtArrow.innerHTML = '<span style="color: var(--text-secondary);"><i class="fas fa-minus"></i></span>';
    }
  }

  applyGlobalMoneyFormatting();
}

function loadAnalytics() {
  fetch("/api/post_payment_analytics")
    .then(res => res.json())
    .then(data => {
      if (data.weeks && data.weeks.length > 0) {
        const lastWeek = data.weeks[data.weeks.length - 1];
        lastWeekPaidCount = lastWeek.paid_customers || 0;
        lastWeekCollection = lastWeek.actual_collection || 0;
      }
      const lastPostingDisplay = document.getElementById("lastPostingDisplay");
      if (lastPostingDisplay) {
        lastPostingDisplay.textContent = data.last_posting_date;
      }
      renderCollectionChart(data.weeks);
      renderAnalyticsTable(data.weeks);
      updateComparativeStats();
    })
    .catch(err => console.error("Failed to load analytics data:", err));
}

// Async load of posting customers list
function loadPostingCustomersAsync() {
  fetch('/api/posting/customers')
    .then(res => res.json())
    .then(data => {
      if (data.success) {
        window.CUSTOMERS = data.customers || [];
        initCustomerMapAndStats();
        
        // Run initializations now that data is present
        updateTable();
        applyGlobalMoneyFormatting();
        loadAnalytics();
      } else {
        showError("Failed to load customer list: " + (data.error || "Unknown error"));
      }
    })
    .catch(err => {
      console.error("Error loading posting customers:", err);
      showError("Connection error. Could not load customer list.");
    });
}

loadPostingCustomersAsync();

// --- Auto-focus & flatpickr & live collection stats loader & flip card listeners ---
document.addEventListener("DOMContentLoaded", () => {
    const pdtInput = document.getElementById("pdt");
    if (pdtInput) {
        window.initCustomCalendar(pdtInput, {
            clickOpens: true
        });
    }

    const pdtInput_init = document.getElementById("pdt");
    if (pdtInput_init) {
        pdtInput_init.focus();

        // Place cursor at the end — Safari-safe fallback
        const len = pdtInput_init.value.length;
        try { pdtInput_init.setSelectionRange(len, len); } catch (e) {}
        setTimeout(() => {
            try { pdtInput_init.setSelectionRange(len, len); } catch (e) {}
        }, 0);
    }

    // ── Flip Card Setup ──
    const flipCardInner = document.getElementById("analyticsFlipCardInner");
    const btnFlipToBack = document.getElementById("btnFlipToBack");
    const btnFlipToFront = document.getElementById("btnFlipToFront");
    const flipCard = document.querySelector(".flip-card");

    if (flipCard && flipCardInner) {
      flipCard.addEventListener("dblclick", () => {
        flipCardInner.classList.toggle("flipped");
      });
    }

    if (btnFlipToBack && flipCardInner) {
      btnFlipToBack.addEventListener("click", (e) => {
        e.stopPropagation();
        flipCardInner.classList.add("flipped");
      });
    }

    if (btnFlipToFront && flipCardInner) {
      btnFlipToFront.addEventListener("click", (e) => {
        e.stopPropagation();
        flipCardInner.classList.remove("flipped");
      });
    }

    // ── Centralized Stats Loader (Live stats) ──
    if (pdtInput) {
        let lastLoadedDate = "";

        const triggerStatsLoad = () => {
            const currentDate = pdtInput.value.trim();

            // Prevent duplicate unnecessary calls
            if (!currentDate || currentDate === lastLoadedDate) {
                return;
            }

            lastLoadedDate = currentDate;

            console.log(
                "AUTO LOADING PAYMENT STATS FOR =>",
                currentDate
            );

            loadPaymentDayStats();
        };

        // Safari/macOS calendar compatibility
        pdtInput.addEventListener("change", triggerStatsLoad);
        pdtInput.addEventListener("input", triggerStatsLoad);
        pdtInput.addEventListener("blur", triggerStatsLoad);
        pdtInput.addEventListener("keyup", triggerStatsLoad);

        // IMPORTANT:
        // Detect programmatic value changes too
        let previousValue = pdtInput.value;

        setInterval(() => {
            if (pdtInput.value !== previousValue) {
                previousValue = pdtInput.value;
                triggerStatsLoad();
            }
        }, 150);

        // Initial load if date already exists
        setTimeout(() => {
            triggerStatsLoad();
        }, 100);
    }

    // ── Posting Report Filter Flatpickrs ──
    const filterDateRange = document.getElementById("filterDateRange");
    if (filterDateRange) {
        window.initCustomCalendar(filterDateRange, {
            mode: "range",
            clickOpens: true
        });
    }

    const bulkFindDate = document.getElementById("bulkFindDate");
    if (bulkFindDate) {
        window.initCustomCalendar(bulkFindDate, {
            clickOpens: true,
            onClose: function() {
                applyReportFiltersOnly();
            }
        });
    }

    // Handle typing filter input directly on Find Date input
    document.getElementById("bulkFindDate")?.addEventListener("input", () => {
        applyReportFiltersOnly();
    });

    const bulkReplaceDate = document.getElementById("bulkReplaceDate");
    if (bulkReplaceDate) {
        window.initCustomCalendar(bulkReplaceDate, {
            clickOpens: true
        });
    }

    // Handle typing filter input directly on ANO filter
    document.getElementById("filterAno")?.addEventListener("input", () => {
        applyReportFiltersOnly();
    });

    // Handle change event on filterDateRange (when calendar date/range is selected)
    document.getElementById("filterDateRange")?.addEventListener("change", () => {
        applyReportFilters();
    });

    // Support pressing Enter in filter inputs to trigger the query
    document.getElementById("filterDateRange")?.addEventListener("keydown", (e) => {
        if (e.key === "Enter") {
            e.preventDefault();
            applyReportFilters();
        }
    });

    document.getElementById("filterAno")?.addEventListener("keydown", (e) => {
        if (e.key === "Enter") {
            e.preventDefault();
            applyReportFilters();
        }
    });

    // Close button for column selector modal
    document.getElementById("closeColumnModal")?.addEventListener("click", () => {
        document.getElementById("columnModal")?.classList.add("hidden");
    });
});

// --- Consolidated Posting Report State and Logic ---
let originalReportData = [];
let filteredReportData = [];
let currentView = 'table';
let highlightedPids = new Set();

window.switchTab = function(tab) {
    const tabNew = document.getElementById("tabNewPayments");
    const tabRep = document.getElementById("tabReport");
    const inputForm = document.getElementById("inputFormBox");
    const tempTable = document.getElementById("tempTableBox");
    const reportContainer = document.getElementById("reportContainer");

    if (!tabNew || !tabRep) return;

    if (tab === 'new-payments') {
        if (tabNew.classList.contains("active")) return;
        tabNew.classList.add("active");
        tabRep.classList.remove("active");
        if (inputForm) inputForm.style.display = "block";
        if (tempTable) tempTable.style.display = "block";
        if (reportContainer) reportContainer.style.display = "none";
        updateTable();
    } else if (tab === 'report') {
        if (tabRep.classList.contains("active")) return;
        tabNew.classList.remove("active");
        tabRep.classList.add("active");
        if (inputForm) inputForm.style.display = "none";
        if (tempTable) tempTable.style.display = "none";
        if (reportContainer) reportContainer.style.display = "block";
        fetchReportData();
    }
};

window.currentReportView = "current";

window.togglePostingReportView = function() {
    const toggleContainer = document.getElementById("postingReportToggle");
    if (!toggleContainer) return;
    
    if (window.currentReportView === "current") {
        window.currentReportView = "historic";
        toggleContainer.classList.remove("mode-current");
        toggleContainer.classList.add("mode-historic");
    } else {
        window.currentReportView = "current";
        toggleContainer.classList.remove("mode-historic");
        toggleContainer.classList.add("mode-current");
    }
    
    fetchReportData();
};

function formatDateToYYYYMMDD(dateObj) {
    if (!dateObj || isNaN(dateObj.getTime())) return "";
    const yyyy = dateObj.getFullYear();
    const mm = String(dateObj.getMonth() + 1).padStart(2, '0');
    const dd = String(dateObj.getDate()).padStart(2, '0');
    return `${yyyy}-${mm}-${dd}`;
}

function fetchReportData() {
    const view = window.currentReportView;
    const dateRangeVal = document.getElementById("filterDateRange")?.value?.trim() || "";
    const filterAnoVal = document.getElementById("filterAno")?.value?.trim() || "";
    
    let url = `/api/posting_report?view=${view}`;
    if (dateRangeVal) {
        const dates = dateRangeVal.split(" to ");
        const startDate = parseISOorDDMMYYYY(dates[0]);
        const endDate = (dates.length === 2 && dates[1].trim()) ? parseISOorDDMMYYYY(dates[1]) : startDate;
        if (startDate && endDate) {
            url += `&start_date=${formatDateToYYYYMMDD(startDate)}&end_date=${formatDateToYYYYMMDD(endDate)}`;
        }
    }
    if (filterAnoVal) {
        url += `&ano=${encodeURIComponent(filterAnoVal)}`;
    }

    fetch(url)
    .then(res => res.json())
    .then(data => {
        if (data.success) {
            originalReportData = data.payments;
            applyReportFiltersOnly();
        } else {
            console.error("Failed to fetch report data:", data.error);
        }
    })
    .catch(err => console.error("Error fetching report data:", err));
}

function fetchReportDataSilently(updatedPid) {
    if (updatedPid) {
        highlightReportRecord(updatedPid);
    }
    const view = window.currentReportView;
    const dateRangeVal = document.getElementById("filterDateRange")?.value?.trim() || "";
    const filterAnoVal = document.getElementById("filterAno")?.value?.trim() || "";
    
    let url = `/api/posting_report?view=${view}`;
    if (dateRangeVal) {
        const dates = dateRangeVal.split(" to ");
        const startDate = parseISOorDDMMYYYY(dates[0]);
        const endDate = (dates.length === 2 && dates[1].trim()) ? parseISOorDDMMYYYY(dates[1]) : startDate;
        if (startDate && endDate) {
            url += `&start_date=${formatDateToYYYYMMDD(startDate)}&end_date=${formatDateToYYYYMMDD(endDate)}`;
        }
    }
    if (filterAnoVal) {
        url += `&ano=${encodeURIComponent(filterAnoVal)}`;
    }

    fetch(url)
    .then(res => res.json())
    .then(data => {
        if (data.success) {
            originalReportData = data.payments;
            applyReportFiltersOnly();
        }
    })
    .catch(err => console.error("Silent refresh failed:", err));
}

window.applyReportFilters = function() {
    fetchReportData();
};

window.resetReportFilters = function() {
    const filterDate = document.getElementById("filterDateRange");
    const filterAno = document.getElementById("filterAno");
    if (filterDate) filterDate.value = "";
    if (filterAno) filterAno.value = "";
    
    const bulkFindDate = document.getElementById("bulkFindDate");
    const bulkReplaceDate = document.getElementById("bulkReplaceDate");
    if (bulkFindDate) bulkFindDate.value = "";
    if (bulkReplaceDate) bulkReplaceDate.value = "";

    fetchReportData();
};

function applyReportFiltersOnly() {
    let data = [...originalReportData];

    // Date Range Filter
    const dateRangeVal = document.getElementById("filterDateRange")?.value?.trim();
    if (dateRangeVal) {
        const dates = dateRangeVal.split(" to ");
        const startDate = parseISOorDDMMYYYY(dates[0]);
        const endDate = (dates.length === 2 && dates[1].trim()) ? parseISOorDDMMYYYY(dates[1]) : startDate;

        if (startDate && endDate) {
            const startTime = new Date(startDate.getFullYear(), startDate.getMonth(), startDate.getDate()).getTime();
            const endTime = new Date(endDate.getFullYear(), endDate.getMonth(), endDate.getDate()).getTime();

            data = data.filter(p => {
                const payDate = parseISOorDDMMYYYY(p.payment_date);
                if (!payDate) return false;
                const payTime = new Date(payDate.getFullYear(), payDate.getMonth(), payDate.getDate()).getTime();
                return payTime >= startTime && payTime <= endTime;
            });
        }
    }

    // Account Number Filter
    const filterAnoVal = document.getElementById("filterAno")?.value?.trim();
    if (filterAnoVal) {
        data = data.filter(p => String(p.ano).trim() === filterAnoVal);
    }

    // Bulk Find Date Filter (when bulk date panel is open)
    const bulkPanel = document.getElementById("bulkDatePanel");
    const bulkFindDateVal = document.getElementById("bulkFindDate")?.value?.trim();
    if (bulkPanel && bulkPanel.style.display !== "none" && bulkFindDateVal) {
        const findDate = parseISOorDDMMYYYY(bulkFindDateVal);
        if (findDate) {
            const findTime = new Date(findDate.getFullYear(), findDate.getMonth(), findDate.getDate()).getTime();
            data = data.filter(p => {
                const payDate = parseISOorDDMMYYYY(p.payment_date);
                if (!payDate) return false;
                const payTime = new Date(payDate.getFullYear(), payDate.getMonth(), payDate.getDate()).getTime();
                return payTime === findTime;
            });
        }
    }

    filteredReportData = data;
    renderReport();
}

window.toggleBulkDatePanel = function() {
    const panel = document.getElementById("bulkDatePanel");
    const btn = document.getElementById("btnToggleBulkDate");
    if (!panel || !btn) return;

    if (panel.style.display === "none") {
        panel.style.display = "flex";
        btn.classList.add("active");
    } else {
        panel.style.display = "none";
        btn.classList.remove("active");
        const bulkFind = document.getElementById("bulkFindDate");
        const bulkReplace = document.getElementById("bulkReplaceDate");
        if (bulkFind) bulkFind.value = "";
        if (bulkReplace) bulkReplace.value = "";
    }
    applyReportFiltersOnly();
};

window.submitBulkDateReplace = function() {
    const findDate = document.getElementById("bulkFindDate")?.value?.trim();
    const replaceDate = document.getElementById("bulkReplaceDate")?.value?.trim();

    if (!findDate || !replaceDate) {
        alert("❌ Please enter both Find Date and Replace Date.");
        return;
    }

    const fDate = parseISOorDDMMYYYY(findDate);
    const affectedPids = [];
    if (fDate) {
        const findTime = new Date(fDate.getFullYear(), fDate.getMonth(), fDate.getDate()).getTime();
        originalReportData.forEach(p => {
            const payDate = parseISOorDDMMYYYY(p.payment_date);
            if (payDate) {
                const payTime = new Date(payDate.getFullYear(), payDate.getMonth(), payDate.getDate()).getTime();
                if (payTime === findTime) {
                    affectedPids.push(p.pid);
                }
            }
        });
    }

    if (affectedPids.length === 0) {
        alert("❌ No payment records found matching the Find Date.");
        return;
    }

    if (!confirm(`Are you sure you want to change the date of ${affectedPids.length} payment record(s) from ${findDate} to ${replaceDate}?`)) {
        return;
    }

    csrfFetch("/update_payment_date_bulk", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
            find_date: findDate,
            replace_date: replaceDate
        })
    })
    .then(res => res.json())
    .then(data => {
        if (data.success) {
            const reportDisplayBox = document.getElementById("reportDisplayBox");

            affectedPids.forEach(pid => {
                highlightReportRecord(pid);
            });

            triggerSuccessFeedback({
                sectionElement: reportDisplayBox,
                message: `${affectedPids.length} dates updated successfully`,
                highlightDuration: 5000
            });

            const bulkFind = document.getElementById("bulkFindDate");
            const bulkReplace = document.getElementById("bulkReplaceDate");
            if (bulkFind) bulkFind.value = "";
            if (bulkReplace) bulkReplace.value = "";

            fetchReportDataSilently();
        } else {
            alert("❌ Failed to bulk update dates: " + (data.error || "Unknown error"));
        }
    })
    .catch(err => {
        alert("❌ Error: " + err.message);
    });
};

window.toggleReportView = function() {
    const toggle = document.getElementById("viewToggle");
    const tableView = document.getElementById("reportTableView");
    const tileView = document.getElementById("reportTileViewWrapper");
    const columnBtn = document.getElementById("tableViewBtn");

    if (!toggle || !tableView || !tileView || !columnBtn) return;

    if (toggle.classList.contains("mode-active")) {
        toggle.classList.remove("mode-active");
        toggle.classList.add("mode-closed");
        tableView.style.display = "none";
        tileView.style.display = "block";
        columnBtn.style.display = "none";
        currentView = 'tile';
    } else {
        toggle.classList.remove("mode-closed");
        toggle.classList.add("mode-active");
        tableView.style.display = "block";
        tileView.style.display = "none";
        columnBtn.style.display = "block";
        currentView = 'table';
    }
    renderReport();
};

window.toggleColumnModal = function() {
    const modal = document.getElementById("columnModal");
    const list = document.getElementById("columnCheckboxList");
    const table = document.getElementById("reportTable");

    if (!modal || !list || !table) return;

    if (modal.classList.contains("hidden")) {
        list.innerHTML = "";
        table.querySelectorAll("thead th").forEach((th, index) => {
            const wrapper = document.createElement("label");
            wrapper.className = "column-item";

            const checkbox = document.createElement("input");
            checkbox.type = "checkbox";
            checkbox.checked = th.style.display !== "none";

            checkbox.addEventListener("change", () => {
                table.querySelectorAll("tr").forEach(row => {
                    if (row.children[index]) {
                        row.children[index].style.display = checkbox.checked ? "" : "none";
                    }
                });
            });

            wrapper.appendChild(checkbox);
            wrapper.appendChild(document.createTextNode(th.innerText));
            list.appendChild(wrapper);
        });
        modal.classList.remove("hidden");
    } else {
        modal.classList.add("hidden");
    }
};

function renderReport() {
    if (currentView === 'table') {
        renderReportTable();
    } else {
        renderReportTileView();
    }
}

function createReportDeleteButton(payment) {
    const btn = document.createElement("button");
    btn.type = "button";
    btn.className = "delete-row-btn report-delete-btn";
    btn.title = `Delete payment for ANO ${payment.ano}`;
    btn.innerHTML = '<i class="fas fa-trash-alt"></i>';

    btn.addEventListener("click", async (e) => {
        e.stopPropagation();

        const parsedDate = parseISOorDDMMYYYY(payment.payment_date);
        const displayDate = parsedDate ? formatDateDDMMYYYY(parsedDate) : payment.payment_date;
        const isoDate = parsedDate ? formatDateToYYYYMMDD(parsedDate) : String(payment.payment_date || "").trim();

        const confirmed = confirm(`Delete payment for ANO ${payment.ano} on ${displayDate}?`);
        if (!confirmed) return;

        btn.disabled = true;

        try {
            const response = await csrfFetch("/delete_payment", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    ano: payment.ano,
                    pdt: isoDate
                })
            });

            const result = await response.json();

            if (!response.ok || !result.success) {
                throw new Error(result.error || "Failed to delete payment");
            }

            highlightedPids.delete(Number(payment.pid));
            fetchReportDataSilently(payment.pid);
        } catch (err) {
            console.error("Delete payment failed:", err);
            alert(err.message || "Unable to delete payment");
            btn.disabled = false;
        }
    });

    return btn;
}

function renderReportTable() {
    const table = document.getElementById("reportTable");
    if (!table) return;
    const thead = table.querySelector("thead");
    const tbody = table.querySelector("tbody");
    const tfoot = table.querySelector("tfoot");

    if ($.fn.DataTable.isDataTable(table)) {
        $(table).DataTable().destroy();
    }

    const hiddenColumnIndexes = [];
    const existingHeaders = table.querySelectorAll("thead th");
    if (existingHeaders.length === 0) {
        hiddenColumnIndexes.push(0, 2, 5); // Default hidden: PID (0), Customer Name (2), Status (5)
    } else {
        existingHeaders.forEach((th, index) => {
            if (th.style.display === "none") {
                hiddenColumnIndexes.push(index);
            }
        });
    }

    thead.innerHTML = `
        <tr>
            <th>PID</th>
            <th>ANO</th>
            <th>Customer Name</th>
            <th>Payment Date</th>
            <th class="amount-paid">Amount</th>
            <th>Status</th>
            <th>Action</th>
        </tr>
    `;

    tbody.innerHTML = "";
    let totalUniqueAnos = new Set();
    let totalAmount = 0;

    filteredReportData.forEach(p => {
        const tr = document.createElement("tr");
        tr.setAttribute("data-pid", p.pid);
        if (highlightedPids.has(Number(p.pid))) {
            tr.classList.add("field-highlight");
        }

        const pidCell = document.createElement("td");
        pidCell.textContent = p.pid;
        pidCell.setAttribute("data-order", Number(p.pid) || 0);
        tr.appendChild(pidCell);

        const anoCell = document.createElement("td");
        anoCell.textContent = p.ano;
        anoCell.setAttribute("data-order", Number(p.ano) || 0);
        anoCell.style.cursor = "pointer";
        anoCell.title = "Double-click to edit";
        anoCell.addEventListener("dblclick", (e) => {
            e.stopPropagation();
            makeReportCellEditable(anoCell, p.pid, 'ano', p.ano);
        });
        tr.appendChild(anoCell);

        const nameCell = document.createElement("td");
        nameCell.textContent = p.customer_name || "Unknown";
        tr.appendChild(nameCell);

        const dateCell = document.createElement("td");
        const dateObj = parseISOorDDMMYYYY(p.payment_date);
        const displayDate = dateObj ? formatDateDDMMYYYY(dateObj) : p.payment_date;
        dateCell.textContent = displayDate;
        dateCell.setAttribute("data-order", dateObj ? dateObj.getTime() : 0);
        dateCell.style.cursor = "pointer";
        dateCell.title = "Double-click to edit";
        dateCell.addEventListener("dblclick", (e) => {
            e.stopPropagation();
            makeReportCellEditable(dateCell, p.pid, 'payment_date', displayDate);
        });
        tr.appendChild(dateCell);

        const amtCell = document.createElement("td");
        amtCell.classList.add("amount-paid");
        amtCell.setAttribute("data-order", Number(p.amt) || 0);
        amtCell.style.cursor = "pointer";
        amtCell.title = "Double-click to edit";
        
        const amtText = document.createElement("span");
        amtText.textContent = Number(p.amt).toFixed(2);
        amtText.setAttribute('data-money', '');
        amtCell.appendChild(amtText);
        
        amtCell.addEventListener("dblclick", (e) => {
            e.stopPropagation();
            makeReportCellEditable(amtCell, p.pid, 'amt', p.amt);
        });
        tr.appendChild(amtCell);

        const statusCell = document.createElement("td");
        statusCell.textContent = p.payment_status || "active";
        statusCell.setAttribute("data-order", p.payment_status || "active");
        tr.appendChild(statusCell);

        const actionCell = document.createElement("td");
        actionCell.style.textAlign = "center";
        actionCell.appendChild(createReportDeleteButton(p));
        tr.appendChild(actionCell);

        tbody.appendChild(tr);

        totalUniqueAnos.add(p.ano);
        totalAmount += Number(p.amt);
    });

    tfoot.innerHTML = `
        <tr>
            <td colspan="7">
                <div class="summary-row" style="display: flex; gap: 40px; font-weight: bold; padding: 10px 0;">
                    <div>Total Unique ANOs: <span id="reportTotalAno">${totalUniqueAnos.size}</span></div>
                    <div>Total Amount: <span id="reportTotalAmt" data-money>${totalAmount.toFixed(2)}</span></div>
                </div>
            </td>
        </tr>
    `;

    hiddenColumnIndexes.forEach(index => {
        table.querySelectorAll("tr").forEach(row => {
            if (row.children[index]) {
                row.children[index].style.display = "none";
            }
        });
    });

    $(table).DataTable({
        paging: false,
        info: false,
        searching: false,
        ordering: true,
        responsive: true,
        order: [[3, 'desc'], [1, 'desc']],
        columnDefs: [
            { type: 'date-ddmmyyyy', targets: 3 }
        ]
    });

    applyGlobalMoneyFormatting();
}

function renderReportTileView() {
    const container = document.getElementById("reportTileView");
    if (!container) return;
    container.innerHTML = "";

    const groups = groupPaymentsByDate(filteredReportData);
    
    const sortedDates = Object.keys(groups).sort((a, b) => {
        const da = parseISOorDDMMYYYY(a);
        const db = parseISOorDDMMYYYY(b);
        if (!da && !db) return 0;
        if (!da) return 1;
        if (!db) return -1;
        return db - da;
    });

    if (sortedDates.length === 0) {
        container.innerHTML = `<div style="text-align: center; padding: 20px; color: var(--text-secondary);">No records found</div>`;
        return;
    }

    sortedDates.forEach(dateStr => {
        const groupPayments = groups[dateStr];
        const groupTotal = groupPayments.reduce((sum, p) => sum + Number(p.amt), 0);
        const uniqueCustomers = new Set(groupPayments.map(p => p.ano)).size;

        const tileContainer = document.createElement("div");
        tileContainer.className = "date-tile-container";
        tileContainer.setAttribute("data-date", dateStr);
        if (window.expandedDateTiles.has(dateStr)) {
            tileContainer.classList.add("expanded");
        }

        const headerDiv = document.createElement("div");
        headerDiv.className = "date-tile-header";
        headerDiv.onclick = () => toggleDateTileDropdown(dateStr);
        
        headerDiv.innerHTML = `
            <div class="date-tile-left">
                <i class="far fa-calendar-alt" style="color: var(--primary); margin-right: 8px;"></i>
                <span class="date-tile-date-label">${dateStr}</span>
            </div>
            <div class="date-tile-right">
                <span class="date-tile-badge badge-customers"><i class="fas fa-users"></i> ${uniqueCustomers} ${uniqueCustomers === 1 ? 'Customer' : 'Customers'}</span>
                <span class="date-tile-badge badge-amount"><i class="fas fa-rupee-sign"></i> <span data-money>${groupTotal.toFixed(2)}</span></span>
                <i class="fas fa-chevron-down date-tile-chevron"></i>
            </div>
        `;
        tileContainer.appendChild(headerDiv);

        const dropdownDiv = document.createElement("div");
        dropdownDiv.className = "date-tile-dropdown";
        if (!window.expandedDateTiles.has(dateStr)) {
            dropdownDiv.classList.add("hidden");
        } else {
            renderTileDropdownTable(dateStr, dropdownDiv, groupPayments);
        }
        tileContainer.appendChild(dropdownDiv);

        container.appendChild(tileContainer);
    });

    applyGlobalMoneyFormatting();
}

window.toggleDateTileDropdown = function(dateStr) {
    const container = document.querySelector(`.date-tile-container[data-date="${dateStr}"]`);
    if (!container) return;
    
    const dropdown = container.querySelector(".date-tile-dropdown");
    if (!dropdown) return;
    
    if (window.expandedDateTiles.has(dateStr)) {
        window.expandedDateTiles.delete(dateStr);
        container.classList.remove("expanded");
        dropdown.classList.add("hidden");
    } else {
        window.expandedDateTiles.add(dateStr);
        container.classList.add("expanded");
        dropdown.classList.remove("hidden");
        const groups = groupPaymentsByDate(filteredReportData);
        const groupPayments = groups[dateStr] || [];
        renderTileDropdownTable(dateStr, dropdown, groupPayments);
        applyGlobalMoneyFormatting();
    }
};

function renderTileDropdownTable(dateStr, dropdownDiv, groupPayments) {
    dropdownDiv.innerHTML = "";
    
    const sortState = window.tileSortStates[dateStr] || { column: 'ano', direction: 'asc' };
    window.tileSortStates[dateStr] = sortState;

    const sortedPayments = [...groupPayments];
    sortedPayments.sort((a, b) => {
        let valA, valB;
        if (sortState.column === 'ano') {
            valA = Number(a.ano) || 0;
            valB = Number(b.ano) || 0;
        } else if (sortState.column === 'payment_date') {
            valA = parseISOorDDMMYYYY(a.payment_date) || 0;
            valB = parseISOorDDMMYYYY(b.payment_date) || 0;
        } else if (sortState.column === 'amt') {
            valA = Number(a.amt) || 0;
            valB = Number(b.amt) || 0;
        } else {
            valA = 0; valB = 0;
        }
        
        if (valA < valB) return sortState.direction === 'asc' ? -1 : 1;
        if (valA > valB) return sortState.direction === 'asc' ? 1 : -1;
        return 0;
    });

    const table = document.createElement("table");
    table.className = "tile-dropdown-table";

    const thead = document.createElement("thead");
    thead.innerHTML = `
        <tr>
            <th class="sortable-header" onclick="event.stopPropagation(); sortTileTable('${dateStr}', 'ano')">ANO${getSortIcon(dateStr, 'ano')}</th>
            <th class="sortable-header" onclick="event.stopPropagation(); sortTileTable('${dateStr}', 'payment_date')">Payment Date${getSortIcon(dateStr, 'payment_date')}</th>
            <th class="sortable-header" onclick="event.stopPropagation(); sortTileTable('${dateStr}', 'amt')">Amount${getSortIcon(dateStr, 'amt')}</th>
            <th>Cumulative Amount</th>
            <th>Action</th>
        </tr>
    `;
    table.appendChild(thead);

    const tbody = document.createElement("tbody");
    let cumulativeAmount = 0;

    sortedPayments.forEach(p => {
        const tr = document.createElement("tr");
        tr.setAttribute("data-pid", p.pid);
        if (highlightedPids.has(Number(p.pid))) {
            tr.classList.add("field-highlight");
        }

        const anoCell = document.createElement("td");
        anoCell.textContent = p.ano;
        anoCell.style.cursor = "pointer";
        anoCell.title = "Double-click to edit";
        anoCell.addEventListener("dblclick", (e) => {
            e.stopPropagation();
            makeReportCellEditable(anoCell, p.pid, 'ano', p.ano);
        });
        tr.appendChild(anoCell);

        const dateCell = document.createElement("td");
        const dateObj = parseISOorDDMMYYYY(p.payment_date);
        const displayDate = dateObj ? formatDateDDMMYYYY(dateObj) : p.payment_date;
        dateCell.textContent = displayDate;
        dateCell.style.cursor = "pointer";
        dateCell.title = "Double-click to edit";
        dateCell.addEventListener("dblclick", (e) => {
            e.stopPropagation();
            makeReportCellEditable(dateCell, p.pid, 'payment_date', displayDate);
        });
        tr.appendChild(dateCell);

        const amtCell = document.createElement("td");
        amtCell.style.cursor = "pointer";
        amtCell.title = "Double-click to edit";
        const amtText = document.createElement("span");
        amtText.textContent = Number(p.amt).toFixed(2);
        amtText.setAttribute('data-money', '');
        amtCell.appendChild(amtText);
        amtCell.addEventListener("dblclick", (e) => {
            e.stopPropagation();
            makeReportCellEditable(amtCell, p.pid, 'amt', p.amt);
        });
        tr.appendChild(amtCell);

        cumulativeAmount += Number(p.amt);
        const cumCell = document.createElement("td");
        cumCell.innerHTML = `<span data-money>${cumulativeAmount.toFixed(2)}</span>`;
        tr.appendChild(cumCell);

        const actionCell = document.createElement("td");
        actionCell.style.textAlign = "center";
        actionCell.appendChild(createReportDeleteButton(p));
        tr.appendChild(actionCell);

        tbody.appendChild(tr);
    });

    table.appendChild(tbody);
    dropdownDiv.appendChild(table);
}

window.sortTileTable = function(dateStr, column) {
    if (!window.tileSortStates[dateStr]) {
        window.tileSortStates[dateStr] = { column: 'ano', direction: 'asc' };
    }
    
    if (window.tileSortStates[dateStr].column === column) {
        window.tileSortStates[dateStr].direction = window.tileSortStates[dateStr].direction === 'asc' ? 'desc' : 'asc';
    } else {
        window.tileSortStates[dateStr].column = column;
        window.tileSortStates[dateStr].direction = 'asc';
    }
    
    renderReportTileView();
};

function getSortIcon(dateStr, column) {
    const state = window.tileSortStates[dateStr] || { column: 'ano', direction: 'asc' };
    if (state.column === column) {
        return state.direction === 'asc' ? ' <i class="fas fa-sort-up"></i>' : ' <i class="fas fa-sort-down"></i>';
    }
    return ' <i class="fas fa-sort" style="opacity: 0.3;"></i>';
}

function groupPaymentsByDate(payments) {
    const groups = {};
    payments.forEach(p => {
        const dObj = parseISOorDDMMYYYY(p.payment_date);
        const groupKey = dObj ? formatDateDDMMYYYY(dObj) : p.payment_date;
        if (!groups[groupKey]) {
            groups[groupKey] = [];
        }
        groups[groupKey].push(p);
    });
    return groups;
}

function makeReportCellEditable(cell, pid, field, currentValue) {
    if (isEditingCell) return;
    isEditingCell = true;

    const input = document.createElement("input");
    input.className = "inline-edit-input";

    if (field === 'amt') {
        input.type = "number";
        input.step = "0.01";
        input.value = Number(currentValue).toFixed(2);
    } else {
        input.type = "text";
        input.value = currentValue;
    }

    cell.innerHTML = "";
    cell.appendChild(input);
    input.focus();

    // Show save button immediately on any keystroke (input event)
    input.addEventListener("input", function() {
        toggleSaveReportButton(true);
    });

    let isFinished = false;

    function finishEdit(save) {
        if (isFinished) return;
        isFinished = true;
        isEditingCell = false;

        if (!save) {
            renderReport();
            return;
        }

        const rawVal = input.value.trim();
        let parsedValue = rawVal;

        if (field === 'ano') {
            if (!parsedValue) {
                alert("❌ Account Number cannot be empty.");
                renderReport();
                return;
            }
            if (!/^\d+$/.test(parsedValue)) {
                alert("❌ Account Number must contain numbers only.");
                renderReport();
                return;
            }
            const customer = CUSTOMER_MAP[parsedValue];
            if (!customer) {
                alert("❌ Account Number not found in database!");
                renderReport();
                return;
            }
        } else if (field === 'payment_date') {
            if (!parsedValue) {
                alert("❌ Payment Date cannot be empty.");
                renderReport();
                return;
            }
        } else if (field === 'amt') {
            parsedValue = parseFloat(rawVal);
            if (isNaN(parsedValue) || parsedValue <= 0) {
                alert("❌ Please enter a valid positive amount.");
                renderReport();
                return;
            }
        }

        // Store pending change instead of saving immediately
        const existing = pendingReportChanges.get(pid) || {};
        existing[field] = parsedValue;
        pendingReportChanges.set(pid, existing);
        toggleSaveReportButton(true);

        // Mark cell as changed visually
        cell.textContent = field === 'amt' ? Number(parsedValue).toFixed(2) : parsedValue;
        cell.style.outline = '2px solid var(--accent-cyan, #22d3ee)';
        cell.style.borderRadius = '4px';
        cell.style.background = 'rgba(34, 211, 238, 0.06)';

        // Re-attach double-click so user can re-edit the cell
        cell.ondblclick = () => makeReportCellEditable(cell, pid, field, parsedValue);
    }

    input.addEventListener("keydown", function(e) {
        if (e.key === "Enter") {
            e.preventDefault();
            finishEdit(true);
        } else if (e.key === "Escape") {
            e.preventDefault();
            finishEdit(false);
        }
    });

    if (field === 'payment_date') {
        window.initCustomCalendar(input, {
            clickOpens: true,
            noWrapper: true,
            onClose: function() {
                setTimeout(() => finishEdit(true), 150);
            }
        });
        setTimeout(() => {
            if (document.activeElement === input) {
                input.click();
            }
        }, 50);
    } else {
        input.addEventListener("blur", function() {
            setTimeout(() => finishEdit(true), 150);
        });
    }
}


function updateReportRecord(pid, field, value) {
    const currentPayment = originalReportData.find(p => p.pid === pid);
    if (!currentPayment) {
        alert("❌ Error: Payment record not found locally.");
        renderReport();
        return;
    }

    const updatedPayment = { ...currentPayment };
    if (field === 'payment_date') {
        updatedPayment.payment_date = normalizeDateForComparison(value);
    } else {
        updatedPayment[field] = value;
    }

    csrfFetch("/api/payment/update_record_pg", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
            data: {
                pid: updatedPayment.pid,
                ano: updatedPayment.ano,
                amt: updatedPayment.amt,
                payment_date: updatedPayment.payment_date
            }
        })
    })
    .then(res => res.json())
    .then(data => {
        if (data.success) {
            const reportDisplayBox = document.getElementById("reportDisplayBox");

            triggerSuccessFeedback({
                sectionElement: reportDisplayBox,
                message: "Change successful",
                highlightDuration: 5000
            });

            fetchReportDataSilently(pid);
        } else {
            alert("❌ Failed to update payment: " + (data.error || "Unknown error"));
            renderReport();
        }
    })
    .catch(err => {
        alert("❌ Error updating payment: " + err.message);
        renderReport();
    });
}

// --- Pending Report Changes: Save Button Logic ---
function toggleSaveReportButton(show) {
    const btn = document.getElementById('btnSaveReportChanges');
    if (!btn) return;
    if (show && pendingReportChanges.size > 0) {
        btn.style.display = '';
    } else if (show) {
        // Show even before finishEdit stores the change (input event triggered)
        btn.style.display = '';
    } else {
        btn.style.display = 'none';
    }
}

function saveAllReportChanges() {
    if (pendingReportChanges.size === 0) return;

    const btn = document.getElementById('btnSaveReportChanges');
    if (btn) {
        btn.disabled = true;
        btn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Saving...';
    }

    const promises = [];

    pendingReportChanges.forEach((fields, pid) => {
        const currentPayment = originalReportData.find(p => p.pid === pid);
        if (!currentPayment) return;

        const updatedPayment = { ...currentPayment };
        Object.keys(fields).forEach(field => {
            if (field === 'payment_date') {
                updatedPayment.payment_date = normalizeDateForComparison(fields[field]);
            } else {
                updatedPayment[field] = fields[field];
            }
        });

        const promise = csrfFetch("/api/payment/update_record_pg", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                data: {
                    pid: updatedPayment.pid,
                    ano: updatedPayment.ano,
                    amt: updatedPayment.amt,
                    payment_date: updatedPayment.payment_date
                }
            })
        })
        .then(res => res.json())
        .then(data => {
            if (!data.success) {
                throw new Error(data.error || "Unknown error for PID " + pid);
            }
            return pid;
        });

        promises.push(promise);
    });

    Promise.all(promises)
        .then(savedPids => {
            pendingReportChanges.clear();
            toggleSaveReportButton(false);

            const reportDisplayBox = document.getElementById("reportDisplayBox");
            triggerSuccessFeedback({
                sectionElement: reportDisplayBox,
                message: savedPids.length + " record" + (savedPids.length !== 1 ? "s" : "") + " saved successfully",
                highlightDuration: 5000
            });

            fetchReportDataSilently();
        })
        .catch(err => {
            alert("❌ Error saving changes: " + err.message);
            // Don't clear pending changes on error so user can retry
        })
        .finally(() => {
            if (btn) {
                btn.disabled = false;
                btn.innerHTML = '<i class="fas fa-save"></i> Save Changes';
            }
        });
}

function highlightReportRecord(pid) {
    highlightedPids.add(Number(pid));
    
    const el = getReportElementByPid(pid);
    if (el) el.classList.add("field-highlight");

    setTimeout(() => {
        highlightedPids.delete(Number(pid));
        const el2 = getReportElementByPid(pid);
        if (el2) el2.classList.remove("field-highlight");
    }, 5000);
}

function getReportElementByPid(pid) {
    if (currentView === 'table') {
        return document.querySelector(`#reportTable tbody tr[data-pid="${pid}"]`);
    } else {
        return document.querySelector(`#reportTileView tr[data-pid="${pid}"]`);
    }
}

function parseISOorDDMMYYYY(dateStr) {
    if (!dateStr) return null;
    const str = String(dateStr).trim();
    
    // Match yyyy-mm-dd or yyyy/mm/dd
    const matchIso = str.match(/^(\d{4})[-/](\d{2})[-/](\d{2})/);
    if (matchIso) {
        return new Date(parseInt(matchIso[1], 10), parseInt(matchIso[2], 10) - 1, parseInt(matchIso[3], 10));
    }
    
    // Match dd-mm-yyyy or dd/mm/yyyy
    const matchDd = str.match(/^(\d{2})[-/](\d{2})[-/](\d{4})/);
    if (matchDd) {
        return new Date(parseInt(matchDd[3], 10), parseInt(matchDd[2], 10) - 1, parseInt(matchDd[1], 10));
    }
    
    const d = new Date(str);
    return isNaN(d.getTime()) ? null : d;
}

const formatDateDDMMYYYY = window.formatDate;

// --- Shortfall / Non-paying Customers Modal ---
window.showShortfallModal = function() {
    const uniquePaidAnos = new Set(tempTable.map(row => String(row.ano).trim()));
    const shortfallCustomers = activeCustomers
        .map(c => CUSTOMER_MAP[String(c.ano).trim()])
        .filter(c => c && !uniquePaidAnos.has(c.ano));

    const tbody = document.getElementById("shortfallTableBody");
    if (!tbody) return;
    tbody.innerHTML = "";

    if (shortfallCustomers.length === 0) {
        const tr = document.createElement("tr");
        tr.innerHTML = `<td colspan="4" style="text-align: center; padding: 12px; color: var(--text-secondary);">No short/non-paying customers for this week!</td>`;
        tbody.appendChild(tr);
    } else {
        shortfallCustomers.forEach(c => {
            const tr = document.createElement("tr");
            tr.style.borderBottom = "1px solid var(--border)";
            tr.style.cursor = "pointer";
            tr.addEventListener("click", () => {
                closeShortfallModal();
                if (typeof window.openCustomerPopup === "function") {
                    window.openCustomerPopup(c.ano);
                } else {
                    console.error("openCustomerPopup not found globally");
                }
            });
            
            const expectedAmt = Number(c.da) || 0;
            const balanceAmt = Number(c.bamt) || 0;
            
            tr.innerHTML = `
                <td style="padding: 10px; text-align: left;">${c.ano}</td>
                <td style="padding: 10px; text-align: left;">${c.name || ""}</td>
                <td style="padding: 10px; text-align: right;" data-money>${expectedAmt.toFixed(2)}</td>
                <td style="padding: 10px; text-align: right;" data-money>${balanceAmt.toFixed(2)}</td>
            `;
            tbody.appendChild(tr);
        });
    }

    const modal = document.getElementById("shortfallModal");
    if (modal) {
        modal.style.display = "flex";
    }
};

window.closeShortfallModal = function() {
    const modal = document.getElementById("shortfallModal");
    if (modal) {
        modal.style.display = "none";
    }
};

function bindShortfallListeners() {
    const shortAccsEl = document.getElementById("shortAccs");
    const shortAmtEl = document.getElementById("shortAmt");
    if (shortAccsEl) {
        shortAccsEl.addEventListener("click", window.showShortfallModal);
    }
    if (shortAmtEl) {
        shortAmtEl.addEventListener("click", window.showShortfallModal);
    }
}

if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", bindShortfallListeners);
} else {
    bindShortfallListeners();
}
