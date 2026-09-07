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
let activeCustomers = [];

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
    activeCustomers = window.CUSTOMERS.filter(c => (Number(c.balance_amount) || 0) > 0);
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
        input.step = "1";
        input.value = Number(currentValue).toFixed(0);
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
    amtText.textContent = row.amt?.toFixed(0) || "0";
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
  document.getElementById("totalAmttop").textContent = totalAmt.toFixed(0);
  document.getElementById("totalAno").textContent = uniqueAno.size;
  document.getElementById("totalAmt").textContent = totalAmt.toFixed(0);

  // Update expected and short-by stats in summary card widgets
  document.getElementById("expectedAccs").textContent = expectedAccCount;
  document.getElementById("shortAccs").textContent = Math.max(0, expectedAccCount - uniqueAno.size);

  document.getElementById("expectedAmt").textContent = expectedTotalAmount.toFixed(0);
  document.getElementById("expectedAmt").setAttribute("data-money", "");
  
  const shortAmtVal = Math.max(0, expectedTotalAmount - totalAmt);
  document.getElementById("shortAmt").textContent = shortAmtVal.toFixed(0);
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
        cumulativeCell.textContent = runningTotal.toFixed(0);
        cumulativeCell.setAttribute('data-money', '');
    } else {
        const input = row.querySelector("td.amount-paid input");
        const amt = parseFloat(input?.value) || 0;
        runningTotal += amt;
        cumulativeCell.textContent = runningTotal.toFixed(0);
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
    printHTML += `<tr><td>${row.ano}</td><td>${row.pdt}</td><td>${row.amt.toFixed(0)}</td></tr>`;
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
    expectedCell.textContent = w.expected_collection.toFixed(0);
    expectedCell.setAttribute("data-money", "");

    const actualCell = document.createElement("td");
    actualCell.textContent = w.actual_collection.toFixed(0);
    actualCell.setAttribute("data-money", "");

    const failedCell = document.createElement("td");
    failedCell.textContent = w.failed_to_collect.toFixed(0);
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
    lastAmtEl.textContent = lastWeekCollection.toFixed(0);
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
    
    const payload = { view: view };
    if (dateRangeVal) {
        const dates = dateRangeVal.split(" to ");
        const startDate = parseISOorDDMMYYYY(dates[0]);
        const endDate = (dates.length === 2 && dates[1].trim()) ? parseISOorDDMMYYYY(dates[1]) : startDate;
        if (startDate && endDate) {
            payload.start_date = formatDateToYYYYMMDD(startDate);
            payload.end_date = formatDateToYYYYMMDD(endDate);
        }
    }
    if (filterAnoVal) {
        payload.ano = filterAnoVal;
    }

    csrfFetch("/api/posting_report", {
        method: "QUERY",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload)
    })
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
    
    const payload = { view: view };
    if (dateRangeVal) {
        const dates = dateRangeVal.split(" to ");
        const startDate = parseISOorDDMMYYYY(dates[0]);
        const endDate = (dates.length === 2 && dates[1].trim()) ? parseISOorDDMMYYYY(dates[1]) : startDate;
        if (startDate && endDate) {
            payload.start_date = formatDateToYYYYMMDD(startDate);
            payload.end_date = formatDateToYYYYMMDD(endDate);
        }
    }
    if (filterAnoVal) {
        payload.ano = filterAnoVal;
    }

    csrfFetch("/api/posting_report", {
        method: "QUERY",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload)
    })
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
        amtText.textContent = Number(p.amt).toFixed(0);
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
                    <div>Total Amount: <span id="reportTotalAmt" data-money>${totalAmount.toFixed(0)}</span></div>
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
                <span class="date-tile-badge badge-amount"><i class="fas fa-rupee-sign"></i> <span data-money>${groupTotal.toFixed(0)}</span></span>
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
        amtText.textContent = Number(p.amt).toFixed(0);
        amtText.setAttribute('data-money', '');
        amtCell.appendChild(amtText);
        amtCell.addEventListener("dblclick", (e) => {
            e.stopPropagation();
            makeReportCellEditable(amtCell, p.pid, 'amt', p.amt);
        });
        tr.appendChild(amtCell);

        cumulativeAmount += Number(p.amt);
        const cumCell = document.createElement("td");
        cumCell.innerHTML = `<span data-money>${cumulativeAmount.toFixed(0)}</span>`;
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
        input.step = "1";
        input.value = Number(currentValue).toFixed(0);
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
        cell.textContent = field === 'amt' ? Number(parsedValue).toFixed(0) : parsedValue;
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
                <td style="padding: 10px; text-align: right;" data-money>${expectedAmt.toFixed(0)}</td>
                <td style="padding: 10px; text-align: right;" data-money>${balanceAmt.toFixed(0)}</td>
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
        shortAccsEl.addEventListener("dblclick", window.showShortfallModal);
    }
    if (shortAmtEl) {
        shortAmtEl.addEventListener("click", window.showShortfallModal);
        shortAmtEl.addEventListener("dblclick", window.showShortfallModal);
    }
}

if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", bindShortfallListeners);
} else {
    bindShortfallListeners();
}

// ============================================================
// BULK ENTRY MODAL  (v2 – Ledger Layout)
// ============================================================

let _bulkPages = [];

function openBulkEntryModal() {
    document.getElementById('bulkEntryModal').style.display = 'flex';
    document.getElementById('bulkStep1').style.display = 'flex';
    document.getElementById('bulkStep2').style.display = 'none';
    const bi = document.getElementById('bulkDate');
    if (bi && !bi._calInit) {
        window.initCustomCalendar(bi, { clickOpens: true });
        bi._calInit = true;
    }
    bi.focus();
}

function closeBulkEntryModal() {
    document.getElementById('bulkEntryModal').style.display = 'none';
    document.getElementById('bulkStep1').style.display = 'flex';
    document.getElementById('bulkStep2').style.display = 'none';
    document.getElementById('bulkText').value = '';
    document.getElementById('bulkDate').value = '';
    document.getElementById('bulkModalError').style.display = 'none';
    document.getElementById('bulkPreviewError').style.display = 'none';
    document.getElementById('bulkLedgerContainer').innerHTML = '';
    document.getElementById('bulkGrandTotal').textContent = '';
    _bulkPages = [];
    if (typeof clearBulkImages === 'function') {
        clearBulkImages();
    }
    if (window._highlightedInput) {
        window._highlightedInput.classList.remove('ledger-highlight-cell');
        window._highlightedInput = null;
    }
}

function showBulkStep1() {
    document.getElementById('bulkStep2').style.display = 'none';
    document.getElementById('bulkStep1').style.display = 'flex';
}

// ── Parse text → pages → sections → pairs ──
function parseBulkInput(text) {
    const pages = [];
    let curPage = null;
    let curSec = [];

    function flushSec() {
        if (curSec.length > 0) {
            if (!curPage) {
                curPage = { label: 'Page 1', sections: [] };
                pages.push(curPage);
            }
            if (curPage.sections.length >= 3) {
                const nextP = pages.length + 1;
                curPage = { label: `Page ${nextP}`, sections: [] };
                pages.push(curPage);
            }
            curPage.sections.push([...curSec]);
            curSec = [];
        }
    }

    const lines = text.split('\n');
    for (let raw of lines) {
        const line = raw.trim();

        if (/^page\s*\d+/i.test(line)) {
            flushSec();
            const label = line.replace(/^page\s*/i, 'Page ');
            curPage = { label: label, sections: [] };
            pages.push(curPage);
            continue;
        }

        if (!line || /^total\s*:/i.test(line)) {
            flushSec();
            continue;
        }

        // Match non-comma/parenthesis characters for both account number and amount to allow 'N' and '-'
        const re = /\(\s*([^,)]+?)\s*,\s*([^)]+?)\s*\)/g;
        let match;
        const pairs = [];
        while ((match = re.exec(line)) !== null) {
            pairs.push({ ano: match[1].trim(), amt: match[2].trim() });
        }

        if (pairs.length > 0) {
            curSec = curSec.concat(pairs);
        }
    }
    flushSec();

    // Pad each page to exactly 3 sections; pad each section to the max row count across
    // the 3 sections (minimum 20) so columns align and pages with >20 rows per section are supported.
    pages.forEach(page => {
        while (page.sections.length < 3) {
            page.sections.push([]);
        }
        const maxRows = Math.max(20, ...page.sections.map(s => s.length));
        page.sections.forEach(sec => {
            while (sec.length < maxRows) {
                sec.push({ ano: '', amt: '' });
            }
        });
    });

    return pages;
}

// ── Validate one (ano, amt, date) triple ──
// Returns: { severity: 'strict'|'medium'|'ignoring'|'empty'|'skip', message: '...' }
//   severity='empty' → skip silently (both blank)
//   severity='skip'  → skip execute but visually fine (dash slot)
//   severity='ignoring' → yellow/muted, not counted in footer
//   severity='medium'   → orange, counted in footer
//   severity='strict'   → red, counted in footer, blocks Execute
function validateBulkRow(ano, amt, date) {
    const anoStr = String(ano || '').trim();
    const amtStr = String(amt === null || amt === undefined ? '' : amt).trim();

    const hasLettersAno = /[a-zA-Z]/.test(anoStr);
    const hasLettersAmt = /[a-zA-Z]/.test(amtStr);
    const isDashAno = anoStr === '-';
    const isDashAmt = amtStr === '-';
    const amtBlankOrDash = !amtStr || isDashAmt;

    // Both cells empty → ignoring (silent)
    if (!anoStr && !amtStr) return { severity: 'empty', message: '' };

    // Letters/words in account number
    if (hasLettersAno || anoStr.toUpperCase() === 'N') {
        if (amtBlankOrDash) {
            // No real amount → ignoring
            return { severity: 'ignoring', message: 'Letters in A.No (no amount — ignored)' };
        } else {
            // Real amount present → strict
            return { severity: 'strict', message: '❌ Invalid A.No (letters/words) with amount present' };
        }
    }

    // Letters/words in amount → always strict
    if (hasLettersAmt || amtStr.toUpperCase() === 'N') {
        return { severity: 'strict', message: '❌ Invalid amount (letters/words not acceptable)' };
    }

    // Missing account number (blank ano)
    if (!anoStr && amtStr) {
        if (amtBlankOrDash) {
            return { severity: 'ignoring', message: 'Missing A.No (no amount — ignored)' };
        } else {
            return { severity: 'strict', message: '❌ Account number is missing but amount is present' };
        }
    }

    // Missing amount (ano present, amt blank) → ignoring
    if (anoStr && !amtStr) {
        return { severity: 'ignoring', message: 'Amount is missing (ignored)' };
    }

    // Dash in A.No
    if (isDashAno) {
        if (amtBlankOrDash) {
            return { severity: 'ignoring', message: 'Dash in A.No with no amount (ignored)' };
        } else {
            return { severity: 'strict', message: '❌ Dash in A.No but real amount present' };
        }
    }

    // Dash in amount → ignoring (skip from execution)
    if (isDashAmt) {
        // A.No is present and not a dash — check if it exists in DB
        const customer = CUSTOMER_MAP[anoStr];
        if (!customer) {
            return { severity: 'ignoring', message: 'A.No not in DB with dash amount (ignored)' };
        }
        return { severity: 'skip', message: '' };
    }

    // Amount ≤ 0 or not a number → strict
    const amtNum = parseFloat(amtStr);
    if (isNaN(amtNum) || amtNum <= 0) {
        return { severity: 'strict', message: '❌ Amount must be > 0' };
    }

    // A.No not found in database WITH a real amount → strict
    const customer = CUSTOMER_MAP[anoStr];
    if (!customer) {
        return { severity: 'strict', message: '❌ A.No not found in database!' };
    }

    // Date validation
    const validation = isPostingDateValidForCustomer(anoStr, date);
    if (!validation.valid) {
        // Determine if it's a medium (date-related) or strict (invalid format)
        if (validation.error.includes('Invalid posting date')) {
            return { severity: 'strict', message: validation.error };
        }
        if (validation.error.includes('invalid start date')) {
            return { severity: 'medium', message: validation.error };
        }
        // Posting date earlier than start date → medium
        return { severity: 'medium', message: validation.error };
    }

    // Duplicate A.No + Date in tempTable → strict
    const dup = tempTable.some(r => String(r.ano) === anoStr && r.pdt === date);
    if (dup) {
        return { severity: 'strict', message: '❌ Duplicate A.No + Date combo exists in temp table.' };
    }

    // All good
    return null;
}

// ── Render the ledger table ──
function renderBulkLedger(pages, date) {
    const container = document.getElementById('bulkLedgerContainer');
    container.innerHTML = '';
    document.getElementById('bulkPreviewDateLabel').textContent = date;

    pages.forEach((page, pi) => {
        const pageDiv = document.createElement('div');
        pageDiv.className = 'ledger-page-card';

        // Page label
        const lbl = document.createElement('div');
        lbl.style.cssText = 'font-weight:700; font-size:14px; color:var(--text); border-bottom:2px solid var(--border); padding-bottom:6px; margin-bottom:8px;';
        lbl.textContent = page.label;
        pageDiv.appendChild(lbl);

        // Table
        const table = document.createElement('table');
        table.className = 'ledger-table';

        // Column header row
        const thead = document.createElement('thead');
        const hr = document.createElement('tr');
        [1, 2, 3].forEach(secNum => {
            const th1 = document.createElement('th');
            th1.textContent = 'A.No';
            hr.appendChild(th1);

            const th2 = document.createElement('th');
            th2.textContent = 'Amount';
            th2.style.textAlign = 'right';
            if (secNum < 3) th2.className = 'ledger-divider';
            hr.appendChild(th2);
        });
        thead.appendChild(hr);
        table.appendChild(thead);

        // Body rows (dynamic row count — sections are pre-padded to the same length)
        const tbody = document.createElement('tbody');
        const secs = page.sections;
        const rowCount = secs[0].length;

        for (let ri = 0; ri < rowCount; ri++) {
            const tr = document.createElement('tr');

            [0, 1, 2].forEach((si) => {
                const pair = secs[si][ri];
                const anoValue = pair ? pair.ano : '';
                const amtValue = pair ? pair.amt : '';

                // A.No cell
                const anoTd = document.createElement('td');
                const anoInp = document.createElement('input');
                anoInp.type = 'text';
                anoInp.inputMode = 'numeric';
                anoInp.value = anoValue.toUpperCase() === 'N' ? '' : anoValue;
                anoInp.className = 'ledger-input';
                anoInp.dataset.page = pi;
                anoInp.dataset.sec = si;
                anoInp.dataset.row = ri;
                anoInp.dataset.field = 'ano';

                anoInp.addEventListener('focus', () => {
                    highlightInput(anoInp);
                    anoInp._oldVal = pair.ano;
                    anoInp.value = '';
                    pair.ano = '';
                    updateBulkState(pages, date);
                });
                anoInp.addEventListener('blur', () => {
                    if (anoInp.value.trim() === '') {
                        anoInp.value = anoInp._oldVal.toUpperCase() === 'N' ? '' : anoInp._oldVal;
                        pair.ano = anoInp._oldVal;
                    }
                    updateBulkState(pages, date);
                });
                anoInp.addEventListener('input', () => {
                    pair.ano = anoInp.value.trim();
                    updateBulkState(pages, date);
                });
                anoInp.addEventListener('keydown', (e) => {
                    if (e.key === 'Enter') {
                        anoInp.blur();
                    }
                });
                anoInp.addEventListener('contextmenu', (e) => {
                    e.preventDefault();
                    highlightInput(anoInp);
                });
                anoTd.appendChild(anoInp);
                tr.appendChild(anoTd);

                // Amount cell
                const amtTd = document.createElement('td');
                if (si < 2) amtTd.className = 'ledger-divider';
                const amtInp = document.createElement('input');
                amtInp.type = 'text';
                amtInp.value = amtValue.toUpperCase() === 'N' ? '' : amtValue;
                amtInp.className = 'ledger-input';
                amtInp.style.textAlign = 'right';
                amtInp.dataset.page = pi;
                amtInp.dataset.sec = si;
                amtInp.dataset.row = ri;
                amtInp.dataset.field = 'amt';

                amtInp.addEventListener('focus', () => {
                    highlightInput(amtInp);
                    amtInp._oldVal = pair.amt;
                    amtInp.value = '';
                    pair.amt = '';
                    updateBulkState(pages, date);
                });
                amtInp.addEventListener('blur', () => {
                    if (amtInp.value.trim() === '') {
                        amtInp.value = amtInp._oldVal.toUpperCase() === 'N' ? '' : amtInp._oldVal;
                        pair.amt = amtInp._oldVal;
                    }
                    updateBulkState(pages, date);
                });
                amtInp.addEventListener('input', () => {
                    pair.amt = amtInp.value.trim();
                    updateBulkState(pages, date);
                });
                amtInp.addEventListener('keydown', (e) => {
                    if (e.key === 'Enter') {
                        amtInp.blur();
                    }
                });
                amtInp.addEventListener('contextmenu', (e) => {
                    e.preventDefault();
                    highlightInput(amtInp);
                });
                amtTd.appendChild(amtInp);
                tr.appendChild(amtTd);
            });

            tbody.appendChild(tr);
        }
        table.appendChild(tbody);

        // Footer: section totals row
        const tfoot = document.createElement('tfoot');
        const fr = document.createElement('tr');
        [0, 1, 2].forEach((si) => {
            const cntTd = document.createElement('td');
            cntTd.className = 'ledger-footer-cell';
            cntTd.id = `bulk-cnt-${pi}-${si}`;
            fr.appendChild(cntTd);

            const totTd = document.createElement('td');
            totTd.className = 'ledger-footer-cell';
            if (si < 2) totTd.className += ' ledger-divider';
            totTd.id = `bulk-stotal-${pi}-${si}`;
            totTd.style.textAlign = 'right';
            fr.appendChild(totTd);
        });
        tfoot.appendChild(fr);
        table.appendChild(tfoot);
        pageDiv.appendChild(table);

        // Page total line
        const ptDiv = document.createElement('div');
        ptDiv.id = `bulk-ptotal-${pi}`;
        ptDiv.style.cssText = 'align-self:flex-end; font-size:13px; font-weight:700; margin-top:12px; color:var(--text); background:rgba(59, 130, 246, 0.08); border:1px solid rgba(59, 130, 246, 0.2); padding:6px 16px; border-radius:20px;';
        pageDiv.appendChild(ptDiv);

        container.appendChild(pageDiv);
    });

    updateBulkState(pages, date);
}

function getAmountColor(val) {
    if (isNaN(val) || val <= 0) return '';
    if (val <= 200) return '#64748b'; // Slate gray for small amounts (<= 200)
    if (val <= 500) return '#2563eb'; // Blue (201 - 500)
    if (val <= 1000) return '#0891b2'; // Cyan/Teal (501 - 1000)
    if (val <= 2000) return '#0d9488'; // Forest Teal (1001 - 2000)
    if (val <= 5000) return '#d97706'; // Warm Amber/Orange (2001 - 5000)
    return '#9333ea'; // Rich Purple for large amounts (5001+)
}

function getAmountFontWeight(val) {
    if (isNaN(val) || val <= 0) return 'normal';
    if (val > 2000) return '600'; // Semibold for larger payments (> 2000)
    return 'normal';
}

// ── Re-validate all cells; refresh highlighting, totals, execute button ──
// Three tiers: strict (red, blocks Execute), medium (orange), ignoring (yellow/muted)
function updateBulkState(pages, date) {
    const seenKeys = {};
    let totalStrictErrors = 0;
    let totalMediumErrors = 0;
    let grandTotalAmount = 0;
    let grandTotalCustomers = 0;

    // Style maps for each severity tier
    const severityStyles = {
        strict:   { bg: 'rgba(220, 38, 38, 0.18)', color: '#b91c1c', rowBg: 'rgba(220, 38, 38, 0.08)' },
        medium:   { bg: 'rgba(234, 88, 12, 0.18)', color: '#c2410c', rowBg: 'rgba(234, 88, 12, 0.06)' },
        ignoring: { bg: 'rgba(202, 138, 4, 0.15)', color: '#a16207', rowBg: '' },
    };

    pages.forEach((page, pi) => {
        let pageTotalAmount = 0;
        let pageTotalCustomers = 0;

        (page.sections || []).forEach((sec, si) => {
            let sectionTotalAmount = 0;
            let sectionTotalCustomers = 0;

            sec.forEach((pair, ri) => {
                const anoStr = String(pair.ano || '').trim();
                const amtStr = String(pair.amt || '').trim();

                let result = validateBulkRow(pair.ano, pair.amt, date);

                // Intra-bulk duplicate check (strict) — only for valid rows with real A.No
                if (anoStr && anoStr !== '-' && result === null) {
                    const key = `${anoStr}__${date}`;
                    if (seenKeys[key]) {
                        result = { severity: 'strict', message: '❌ Duplicate A.No within this bulk entry' };
                    }
                    seenKeys[key] = true;
                }

                const severity = result ? result.severity : null;
                const message = result ? result.message : '';

                const anoInp = document.querySelector(`input[data-page="${pi}"][data-sec="${si}"][data-row="${ri}"][data-field="ano"]`);
                const amtInp = document.querySelector(`input[data-page="${pi}"][data-sec="${si}"][data-row="${ri}"][data-field="amt"]`);
                const tr = anoInp ? anoInp.closest('tr') : null;

                // Reset row background
                if (tr) tr.style.backgroundColor = '';

                // Apply styling based on severity
                if (severity === 'strict' || severity === 'medium' || severity === 'ignoring') {
                    const style = severityStyles[severity];

                    if (anoInp) {
                        anoInp.style.backgroundColor = style.bg;
                        anoInp.style.color = style.color;
                        anoInp.title = message;
                    }
                    if (amtInp) {
                        amtInp.style.backgroundColor = style.bg;
                        amtInp.style.color = style.color;
                        amtInp.style.fontWeight = 'normal';
                        amtInp.title = message;
                    }
                    if (tr && style.rowBg) {
                        tr.style.backgroundColor = style.rowBg;
                    }

                    if (severity === 'strict') totalStrictErrors++;
                    if (severity === 'medium') totalMediumErrors++;
                } else if (severity === 'skip') {
                    // Dash/skip slots — muted style like ignoring
                    const skipStyle = severityStyles.ignoring;
                    if (anoInp) {
                        anoInp.style.backgroundColor = skipStyle.bg;
                        anoInp.style.color = skipStyle.color;
                        anoInp.title = 'Non-paying slot (dash)';
                    }
                    if (amtInp) {
                        amtInp.style.backgroundColor = skipStyle.bg;
                        amtInp.style.color = skipStyle.color;
                        amtInp.style.fontWeight = 'normal';
                        amtInp.title = 'Non-paying slot (dash)';
                    }
                } else {
                    // Clean cell (null = OK, or empty)
                    if (anoInp) {
                        anoInp.style.backgroundColor = '';
                        anoInp.title = '';
                        anoInp.style.color = '';
                    }
                    if (amtInp) {
                        amtInp.style.backgroundColor = '';
                        amtInp.title = '';
                        const valNum = parseFloat(amtStr);
                        amtInp.style.color = getAmountColor(valNum);
                        amtInp.style.fontWeight = getAmountFontWeight(valNum);
                    }

                    // Count valid rows for totals
                    if (severity !== 'empty' && anoStr && anoStr !== '-') {
                        sectionTotalCustomers++;
                        sectionTotalAmount += parseFloat(amtStr) || 0;
                    }
                }
            });

            const cntEl = document.getElementById(`bulk-cnt-${pi}-${si}`);
            const stEl = document.getElementById(`bulk-stotal-${pi}-${si}`);
            if (cntEl) {
                cntEl.textContent = sectionTotalCustomers > 0 ? `${sectionTotalCustomers}` : '-';
            }
            if (stEl) {
                stEl.textContent = sectionTotalAmount > 0 ? `₹${sectionTotalAmount.toLocaleString('en-IN')}` : '-';
            }

            pageTotalCustomers += sectionTotalCustomers;
            pageTotalAmount += sectionTotalAmount;
        });

        const ptEl = document.getElementById(`bulk-ptotal-${pi}`);
        if (ptEl) {
            ptEl.textContent = `Page Total: ${pageTotalCustomers} customers | ₹${pageTotalAmount.toLocaleString('en-IN')}`;
        }

        grandTotalCustomers += pageTotalCustomers;
        grandTotalAmount += pageTotalAmount;
    });

    // Grand total with separate strict/medium counts
    const gtEl = document.getElementById('bulkGrandTotal');
    if (gtEl) {
        const hasIssues = totalStrictErrors > 0 || totalMediumErrors > 0;
        let gtText = `Grand Total: ₹${grandTotalAmount.toLocaleString('en-IN')} · ${grandTotalCustomers} customers`;
        if (totalStrictErrors > 0) gtText += ` · 🔴 ${totalStrictErrors} strict error(s)`;
        if (totalMediumErrors > 0) gtText += ` · 🟠 ${totalMediumErrors} warning(s)`;
        gtEl.textContent = gtText;

        if (totalStrictErrors > 0) {
            gtEl.style.cssText = 'font-size:14px; font-weight:700; color:#dc2626; background:rgba(220, 38, 38, 0.08); border:1px solid rgba(220, 38, 38, 0.2); padding:6px 16px; border-radius:20px;';
        } else if (totalMediumErrors > 0) {
            gtEl.style.cssText = 'font-size:14px; font-weight:700; color:#c2410c; background:rgba(234, 88, 12, 0.08); border:1px solid rgba(234, 88, 12, 0.2); padding:6px 16px; border-radius:20px;';
        } else {
            gtEl.style.cssText = 'font-size:14px; font-weight:700; color:var(--text); background:rgba(22, 163, 74, 0.08); border:1px solid rgba(22, 163, 74, 0.25); padding:6px 16px; border-radius:20px;';
        }
    }

    // Execute button — only strict errors block it
    const execBtn = document.getElementById('bulkExecuteBtn');
    if (execBtn) {
        const canExecute = totalStrictErrors === 0 && grandTotalCustomers > 0;
        execBtn.disabled = !canExecute;
        if (canExecute) {
            execBtn.style.backgroundColor = '#16a34a';
            execBtn.style.cursor = 'pointer';
            execBtn.style.opacity = '1';
        } else {
            execBtn.style.backgroundColor = '#dc2626';
            execBtn.style.cursor = 'not-allowed';
            execBtn.style.opacity = '0.65';
        }
    }

    // Error summary message
    const errEl = document.getElementById('bulkPreviewError');
    if (errEl) {
        if (totalStrictErrors > 0) {
            errEl.textContent = `⚠ ${totalStrictErrors} strict error(s) found (red rows). Fix them — the Execute button will turn green when all strict errors are resolved.`;
            errEl.style.display = 'block';
            errEl.style.color = '#dc2626';
        } else if (totalMediumErrors > 0) {
            errEl.textContent = `ℹ ${totalMediumErrors} warning(s) found (orange). These won't block execution but may need attention.`;
            errEl.style.display = 'block';
            errEl.style.color = '#c2410c';
        } else {
            errEl.style.display = 'none';
        }
    }
}

// ── Parse button ──
function parseBulkEntry() {
    const date = document.getElementById('bulkDate').value.trim();
    const text = document.getElementById('bulkText').value.trim();
    const errEl = document.getElementById('bulkModalError');
    errEl.style.display = 'none';

    if (!date) {
        errEl.textContent = '❌ Please enter a Payment Date first.';
        errEl.style.display = 'block';
        return;
    }
    if (!text) {
        errEl.textContent = '❌ Please paste entries in the text area.';
        errEl.style.display = 'block';
        return;
    }

    const pages = parseBulkInput(text);
    if (!pages.length || pages.every(p => !p.sections.length)) {
        errEl.textContent = '❌ No valid (ano, amount) pairs found. Check your input format.';
        errEl.style.display = 'block';
        return;
    }

    _bulkPages = pages;
    document.getElementById('bulkStep1').style.display = 'none';
    const s2 = document.getElementById('bulkStep2');
    s2.style.display = 'flex';
    renderBulkLedger(_bulkPages, date);
}

// ── Execute button ──
function executeBulkEntry() {
    const execBtn = document.getElementById('bulkExecuteBtn');
    if (execBtn && execBtn.disabled) return;

    const date = document.getElementById('bulkDate').value.trim();
    if (!date) return;

    const seenKeys = {};
    let added = 0;

    _bulkPages.forEach(page => {
        (page.sections || []).forEach(sec => {
            sec.forEach(pair => {
                const anoStr = String(pair.ano || '').trim();
                const amtStr = String(pair.amt || '').trim();
                if (!anoStr) return; // skip empty
                const key = `${anoStr}__${date}`;
                if (seenKeys[key]) return; // skip intra-bulk dup
                const result = validateBulkRow(pair.ano, pair.amt, date);
                // Only add rows that pass validation (result === null)
                if (result !== null) return; // skip any severity (strict/medium/ignoring/skip/empty)
                seenKeys[key] = true;
                tempTable.unshift({ ano: anoStr, pdt: date, amt: Number(amtStr) });
                added++;
            });
        });
    });

    if (!added) {
        const errEl = document.getElementById('bulkPreviewError');
        if (errEl) { errEl.textContent = '❌ No valid rows to add.'; errEl.style.display = 'block'; }
        return;
    }

    saveAndUpdate();
    closeBulkEntryModal();

    const firstRow = document.querySelector('#tempTable tbody tr');
    if (firstRow) {
        if (window.currentRow) window.currentRow.classList.remove('highlighted-row');
        window.currentRow = firstRow;
        firstRow.classList.add('highlighted-row');
        firstRow.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
    }
}

// Close on backdrop click
document.getElementById('bulkEntryModal').addEventListener('click', function(e) {
    if (e.target === this) closeBulkEntryModal();
});

// ── Keyboard Navigation & Highlight Helpers ──
window._highlightedInput = null;

function highlightInput(inp) {
    if (window._highlightedInput) {
        window._highlightedInput.classList.remove('ledger-highlight-cell');
    }
    window._highlightedInput = inp;
    if (inp) {
        inp.classList.add('ledger-highlight-cell');
    }
}

document.addEventListener('keydown', (e) => {
    // Only intercept keys when Step 2 of Bulk Entry Modal (preview) is open and we have a highlight
    const s2 = document.getElementById('bulkStep2');
    if (s2 && s2.style.display === 'flex' && window._highlightedInput) {
        // If an input is focused, we don't want arrow keys to move the highlight (user is editing text)
        if (document.activeElement && document.activeElement.tagName === 'INPUT') {
            return;
        }

        const inp = window._highlightedInput;
        const page = parseInt(inp.dataset.page);
        const sec = parseInt(inp.dataset.sec);
        const row = parseInt(inp.dataset.row);
        const field = inp.dataset.field; // 'ano' or 'amt'

        let nextInp = null;

        // Dynamic max row for the current page/section
        const maxRow = (_bulkPages && _bulkPages[page] && _bulkPages[page].sections[sec])
            ? _bulkPages[page].sections[sec].length - 1
            : 19;

        if (e.key === 'ArrowDown') {
            e.preventDefault();
            if (row < maxRow) {
                nextInp = document.querySelector(`input[data-page="${page}"][data-sec="${sec}"][data-row="${row + 1}"][data-field="${field}"]`);
            } else {
                const nextPage = page + 1;
                nextInp = document.querySelector(`input[data-page="${nextPage}"][data-sec="${sec}"][data-row="0"][data-field="${field}"]`);
            }
        } else if (e.key === 'ArrowUp') {
            e.preventDefault();
            if (row > 0) {
                nextInp = document.querySelector(`input[data-page="${page}"][data-sec="${sec}"][data-row="${row - 1}"][data-field="${field}"]`);
            } else if (page > 0) {
                const prevPage = page - 1;
                const prevMaxRow = (_bulkPages && _bulkPages[prevPage] && _bulkPages[prevPage].sections[sec])
                    ? _bulkPages[prevPage].sections[sec].length - 1
                    : 19;
                nextInp = document.querySelector(`input[data-page="${prevPage}"][data-sec="${sec}"][data-row="${prevMaxRow}"][data-field="${field}"]`);
            }
        } else if (e.key === 'ArrowRight') {
            e.preventDefault();
            if (field === 'ano') {
                nextInp = document.querySelector(`input[data-page="${page}"][data-sec="${sec}"][data-row="${row}"][data-field="amt"]`);
            } else if (sec < 2) {
                nextInp = document.querySelector(`input[data-page="${page}"][data-sec="${sec + 1}"][data-row="${row}"][data-field="ano"]`);
            }
        } else if (e.key === 'ArrowLeft') {
            e.preventDefault();
            if (field === 'amt') {
                nextInp = document.querySelector(`input[data-page="${page}"][data-sec="${sec}"][data-row="${row}"][data-field="ano"]`);
            } else if (sec > 0) {
                nextInp = document.querySelector(`input[data-page="${page}"][data-sec="${sec - 1}"][data-row="${row}"][data-field="amt"]`);
            }
        } else if (e.key === 'Enter') {
            e.preventDefault();
            inp.focus();
        }

        if (nextInp) {
            highlightInput(nextInp);
            nextInp.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
        }
    }
});
// ============================================================
// END BULK ENTRY MODAL
// ============================================================

// ============================================================
// BULK ENTRY MODAL — AI OCR IMAGE UPLOAD (GEMINI AI)
// ============================================================
let _bulkImageFiles = [];

function handleBulkImageSelect(files) {
    if (!files || !files.length) return;
    const newFiles = Array.from(files).filter(f => f.type.startsWith('image/'));
    if (!newFiles.length) {
        const errEl = document.getElementById('bulkModalError');
        if (errEl) {
            errEl.style.display = 'block';
            errEl.style.background = '#fef2f2';
            errEl.style.color = '#b91c1c';
            errEl.style.borderColor = '#fca5a5';
            errEl.textContent = '❌ Please select valid image files (JPG, PNG, WebP, etc.).';
        }
        return;
    }
    _bulkImageFiles = _bulkImageFiles.concat(newFiles);
    renderBulkImageThumbnails();
}

function renderBulkImageThumbnails() {
    const container = document.getElementById('bulkThumbnailsContainer');
    const placeholder = document.getElementById('bulkDropPlaceholder');
    const extractBtn = document.getElementById('bulkExtractBtn');
    const clearBtn = document.getElementById('bulkClearImagesBtn');
    const errEl = document.getElementById('bulkModalError');

    if (errEl) errEl.style.display = 'none';
    if (!container || !placeholder) return;

    container.innerHTML = '';

    if (_bulkImageFiles.length === 0) {
        container.style.display = 'none';
        placeholder.style.display = 'flex';
        if (extractBtn) extractBtn.style.display = 'none';
        if (clearBtn) clearBtn.style.display = 'none';
        return;
    }

    placeholder.style.display = 'none';
    container.style.display = 'flex';
    if (extractBtn) {
        extractBtn.style.display = 'inline-flex';
        const pageCountText = _bulkImageFiles.length + ' page' + (_bulkImageFiles.length > 1 ? 's' : '');
        extractBtn.innerHTML = '<i class="fas fa-magic"></i> Extract with AI (' + pageCountText + ')';
    }
    if (clearBtn) clearBtn.style.display = 'inline-flex';

    _bulkImageFiles.forEach((file, idx) => {
        const thumbCard = document.createElement('div');
        thumbCard.style.cssText = 'position:relative; width:64px; height:64px; border-radius:6px; border:1px solid var(--border); overflow:visible; background:#000; flex-shrink:0;';

        const img = document.createElement('img');
        img.src = URL.createObjectURL(file);
        img.alt = 'Page ' + (idx + 1);
        img.style.cssText = 'width:100%; height:100%; object-fit:cover; border-radius:6px;';
        thumbCard.appendChild(img);

        const badge = document.createElement('span');
        badge.className = 'bulk-thumb-badge';
        badge.textContent = 'P' + (idx + 1);
        thumbCard.appendChild(badge);

        const removeBtn = document.createElement('button');
        removeBtn.type = 'button';
        removeBtn.className = 'bulk-thumb-remove';
        removeBtn.innerHTML = '&times;';
        removeBtn.title = 'Remove this image';
        removeBtn.onclick = function (e) {
            e.stopPropagation();
            removeBulkImage(idx);
        };
        thumbCard.appendChild(removeBtn);

        container.appendChild(thumbCard);
    });
}

function removeBulkImage(index) {
    if (index >= 0 && index < _bulkImageFiles.length) {
        _bulkImageFiles.splice(index, 1);
        const input = document.getElementById('bulkImageInput');
        if (input) input.value = '';
        renderBulkImageThumbnails();
    }
}

function clearBulkImages() {
    _bulkImageFiles = [];
    const input = document.getElementById('bulkImageInput');
    if (input) input.value = '';
    renderBulkImageThumbnails();
    const prog = document.getElementById('bulkExtractProgress');
    if (prog) prog.style.display = 'none';
}

function compressImageForOcr(file, maxDimension = 1600, quality = 0.85) {
    return new Promise((resolve) => {
        if (!file.type.startsWith('image/') || file.size < 250 * 1024) {
            return resolve(file);
        }
        const img = new Image();
        const objectUrl = URL.createObjectURL(file);
        img.onload = function () {
            URL.revokeObjectURL(objectUrl);
            let width = img.width;
            let height = img.height;

            if (width > maxDimension || height > maxDimension) {
                if (width > height) {
                    height = Math.round((height * maxDimension) / width);
                    width = maxDimension;
                } else {
                    width = Math.round((width * maxDimension) / height);
                    height = maxDimension;
                }
            }

            const canvas = document.createElement('canvas');
            canvas.width = width;
            canvas.height = height;
            const ctx = canvas.getContext('2d');
            ctx.drawImage(img, 0, 0, width, height);

            canvas.toBlob((blob) => {
                if (!blob || blob.size >= file.size) {
                    resolve(file);
                } else {
                    const newName = file.name.replace(/\.[^.]+$/, '') + '.jpg';
                    const compressed = new File([blob], newName, {
                        type: 'image/jpeg',
                        lastModified: Date.now()
                    });
                    resolve(compressed);
                }
            }, 'image/jpeg', quality);
        };
        img.onerror = function () {
            URL.revokeObjectURL(objectUrl);
            resolve(file);
        };
        img.src = objectUrl;
    });
}

async function extractBulkImagesWithAI() {
    if (!_bulkImageFiles.length) {
        const errEl = document.getElementById('bulkModalError');
        if (errEl) {
            errEl.style.display = 'block';
            errEl.style.background = '#fef2f2';
            errEl.style.color = '#b91c1c';
            errEl.style.borderColor = '#fca5a5';
            errEl.textContent = '❌ Please select at least one ledger image first.';
        }
        return;
    }

    const extractBtn = document.getElementById('bulkExtractBtn');
    const clearBtn = document.getElementById('bulkClearImagesBtn');
    const prog = document.getElementById('bulkExtractProgress');
    const progText = document.getElementById('bulkExtractProgressText');
    const errEl = document.getElementById('bulkModalError');

    if (errEl) errEl.style.display = 'none';

    if (extractBtn) {
        extractBtn.disabled = true;
        extractBtn.style.opacity = '0.6';
    }
    if (clearBtn) clearBtn.disabled = true;

    const startTime = Date.now();
    const count = _bulkImageFiles.length;

    if (prog) {
        prog.style.display = 'flex';
        if (progText) {
            progText.textContent = 'Optimizing ' + count + ' image' + (count > 1 ? 's' : '') + ' for fast upload...';
        }
    }

    const abortCtrl = new AbortController();
    const timeoutId = setTimeout(() => {
        abortCtrl.abort();
    }, 180000);

    let progressInterval = null;

    try {
        const compressedFiles = await Promise.all(
            _bulkImageFiles.map(f => compressImageForOcr(f))
        );

        let elapsedSec = 0;
        if (progText) {
            progText.textContent = 'Analyzing ' + count + ' page' + (count > 1 ? 's' : '') + ' with Gemini Flash... (1s)';
        }

        progressInterval = setInterval(() => {
            elapsedSec++;
            if (progText) {
                progText.textContent = 'Analyzing ' + count + ' page' + (count > 1 ? 's' : '') + ' with Gemini Flash... (' + elapsedSec + 's)';
            }
        }, 1000);

        const formData = new FormData();
        compressedFiles.forEach(file => {
            formData.append('images', file);
        });

        const response = await csrfFetch('/api/ocr_extract_bulk', {
            method: 'POST',
            body: formData,
            signal: abortCtrl.signal
        });

        clearTimeout(timeoutId);
        if (progressInterval) clearInterval(progressInterval);

        const data = await response.json();

        if (!response.ok || !data.success) {
            throw new Error(data.error || ('Server responded with status ' + response.status));
        }

        const textArea = document.getElementById('bulkText');
        if (textArea) {
            textArea.value = data.text;
            textArea.focus();
        }

        const totalSec = ((Date.now() - startTime) / 1000).toFixed(1);

        if (errEl) {
            errEl.style.display = 'block';
            errEl.style.background = '#f0fdf4';
            errEl.style.color = '#15803d';
            errEl.style.borderColor = '#86efac';
            const pageNum = data.pages_count || count;
            errEl.textContent = '✅ Extracted ' + pageNum + ' page(s) in ' + totalSec + 's! Review the text below, then click "Parse & Preview".';
        }

    } catch (err) {
        clearTimeout(timeoutId);
        if (progressInterval) clearInterval(progressInterval);
        console.error('OCR extraction failed:', err);
        let msg = err.message || err;
        if (err.name === 'AbortError') {
            msg = 'Request timed out after 3 minutes. Please check your internet connection or try with fewer images.';
        }
        if (errEl) {
            errEl.style.display = 'block';
            errEl.style.background = '#fef2f2';
            errEl.style.color = '#b91c1c';
            errEl.style.borderColor = '#fca5a5';
            errEl.textContent = '❌ AI Extraction failed: ' + msg;
        }
    } finally {
        if (progressInterval) clearInterval(progressInterval);
        if (extractBtn) {
            extractBtn.disabled = false;
            extractBtn.style.opacity = '1';
        }
        if (clearBtn) clearBtn.disabled = false;
        if (prog) prog.style.display = 'none';
    }
}

// Wire drag & drop and file input on DOM ready
document.addEventListener('DOMContentLoaded', function () {
    const dropArea = document.getElementById('bulkDropArea');
    const imageInput = document.getElementById('bulkImageInput');

    if (dropArea) {
        ['dragenter', 'dragover'].forEach(eventName => {
            dropArea.addEventListener(eventName, function (e) {
                e.preventDefault();
                e.stopPropagation();
                dropArea.style.borderColor = '#2563eb';
                dropArea.style.backgroundColor = 'rgba(37, 99, 235, 0.05)';
            });
        });

        ['dragleave', 'drop'].forEach(eventName => {
            dropArea.addEventListener(eventName, function (e) {
                e.preventDefault();
                e.stopPropagation();
                dropArea.style.borderColor = 'rgba(0,0,0,0.15)';
                dropArea.style.backgroundColor = 'var(--surface)';
            });
        });

        dropArea.addEventListener('drop', function (e) {
            const dt = e.dataTransfer;
            if (dt && dt.files && dt.files.length) {
                handleBulkImageSelect(dt.files);
            }
        });
    }

    if (imageInput) {
        imageInput.addEventListener('change', function () {
            if (this.files && this.files.length) {
                handleBulkImageSelect(this.files);
            }
        });
    }
});


// ============================================================
// MOBILE SCANNER 2-STEP LIVE SESSION
// ============================================================
let _bulkCaptureSessionId = null;
let _bulkCapturePollInterval = null;

async function openBulkCaptureModal() {
    const modal = document.getElementById('bulkCaptureModal');
    const step1 = document.getElementById('captureStep1');
    const step2 = document.getElementById('captureStep2');
    const qrLoading = document.getElementById('bulkCaptureQrLoading');
    const qrImg = document.getElementById('bulkCaptureQrImg');
    const badge = document.getElementById('captureStepBadge');
    const title = document.getElementById('captureModalTitle');

    if (!modal) return;

    modal.style.display = 'flex';
    if (step1) step1.style.display = 'flex';
    if (step2) step2.style.display = 'none';
    if (badge) {
        badge.textContent = 'STEP 1 OF 2';
        badge.style.background = 'var(--primary-light)';
        badge.style.color = 'var(--primary)';
    }
    if (title) title.textContent = 'Scan with Phone';

    if (qrLoading) qrLoading.style.display = 'flex';
    if (qrImg) {
        qrImg.style.display = 'none';
        qrImg.src = '';
    }

    if (_bulkCapturePollInterval) {
        clearInterval(_bulkCapturePollInterval);
        _bulkCapturePollInterval = null;
    }
    _bulkCaptureSessionId = null;

    try {
        const resp = await window.csrfFetch('/api/bulk_capture/session/create', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' }
        });
        const data = await resp.json();

        if (!data.success) {
            throw new Error(data.error || 'Failed to initialize capture session');
        }

        _bulkCaptureSessionId = data.session_id;

        if (data.qr_code && qrImg) {
            qrImg.src = data.qr_code;
            qrImg.style.display = 'block';
            if (qrLoading) qrLoading.style.display = 'none';
        } else if (qrLoading) {
            qrLoading.innerHTML = '<span style="font-size:12px; color:#b91c1c;">QR generation error</span>';
        }

        // Poll for phone connection and image upload
        _bulkCapturePollInterval = setInterval(pollBulkCaptureStatus, 1500);

    } catch (err) {
        console.error('Error starting capture session:', err);
        if (qrLoading) {
            qrLoading.innerHTML = '<span style="font-size:12px; color:#b91c1c;">' + (err.message || 'Error connecting to server') + '</span>';
        }
    }
}

function closeBulkCaptureModal() {
    const modal = document.getElementById('bulkCaptureModal');
    if (modal) modal.style.display = 'none';

    if (_bulkCapturePollInterval) {
        clearInterval(_bulkCapturePollInterval);
        _bulkCapturePollInterval = null;
    }

    // Immediately cancel session so the mobile URL gets invalidated
    if (_bulkCaptureSessionId) {
        const sid = _bulkCaptureSessionId;
        _bulkCaptureSessionId = null;
        window.csrfFetch('/api/bulk_capture/session/cancel/' + sid, { method: 'POST' }).catch(() => {});
    }
}

async function pollBulkCaptureStatus() {
    if (!_bulkCaptureSessionId) return;

    try {
        const resp = await fetch('/api/bulk_capture/session/status/' + _bulkCaptureSessionId);
        if (!resp.ok) {
            if (resp.status === 404) {
                clearInterval(_bulkCapturePollInterval);
                _bulkCapturePollInterval = null;
            }
            return;
        }

        const data = await resp.json();
        if (!data.success) return;

        const step1 = document.getElementById('captureStep1');
        const step2 = document.getElementById('captureStep2');
        const badge = document.getElementById('captureStepBadge');
        const title = document.getElementById('captureModalTitle');
        const heading = document.getElementById('captureStep2Heading');
        const sub = document.getElementById('captureStep2Sub');
        const iconWrap = document.getElementById('captureStep2IconWrap');
        const icon = document.getElementById('captureStep2Icon');
        const pill = document.getElementById('capturePagesPill');
        const countSpan = document.getElementById('capturePagesReceivedCount');
        const processAiBtn = document.getElementById('captureProcessAiBtn');

        // Transition to STEP 2 once phone connects or when images are being uploaded
        if (data.status === 'connected' || data.status === 'completed') {
            if (step1 && step1.style.display !== 'none') {
                step1.style.display = 'none';
                if (step2) step2.style.display = 'flex';
                if (badge) {
                    badge.textContent = 'STEP 2 OF 2';
                    badge.style.background = 'var(--primary-lighter)';
                    badge.style.color = 'var(--primary)';
                }
                if (title) title.textContent = 'Capture & Extract';
            }
        }

        if (data.status === 'connected') {
            if (heading) heading.textContent = 'Phone Connected!';
            if (sub) sub.innerHTML = 'Snap your ledger pages and tap <strong>"Send to Desktop"</strong> on your phone.';
            if (iconWrap) {
                iconWrap.style.background = 'var(--primary-light)';
                iconWrap.style.color = 'var(--primary)';
            }
            if (icon) icon.className = 'fas fa-camera';
            if (pill) pill.style.display = 'none';
            if (processAiBtn) processAiBtn.style.display = 'none';

        } else if (data.status === 'completed' && data.images && data.images.length > 0) {
            // Stop polling - all images are in
            clearInterval(_bulkCapturePollInterval);
            _bulkCapturePollInterval = null;

            // Load images into bulk memory
            await loadCapturedImagesIntoBulk(data.images);

            if (heading) heading.textContent = 'Pages Received!';
            if (sub) sub.textContent = 'Scanned pages successfully transferred from your phone.';
            if (iconWrap) {
                iconWrap.style.background = '#e8f5e9';
                iconWrap.style.color = '#16a34a';
            }
            if (icon) icon.className = 'fas fa-check-circle';

            if (countSpan) countSpan.textContent = data.images.length;
            if (pill) pill.style.display = 'inline-flex';

            // Show "Process with AI" button prominently
            if (processAiBtn) {
                processAiBtn.style.display = 'inline-flex';
                const pageWord = data.images.length + ' page' + (data.images.length > 1 ? 's' : '');
                processAiBtn.innerHTML = '<i class="fas fa-magic"></i> Process with AI (' + pageWord + ')';
            }
        }

    } catch (err) {
        console.warn('Capture polling error:', err);
    }
}

async function loadCapturedImagesIntoBulk(imagesMeta) {
    if (!imagesMeta || !imagesMeta.length) return;

    const newFiles = [];
    for (let i = 0; i < imagesMeta.length; i++) {
        const meta = imagesMeta[i];
        try {
            const res = await fetch(meta.url);
            const blob = await res.blob();
            const filename = meta.filename || ('scanned_page_' + (i + 1) + '.jpg');
            const file = new File([blob], filename, { type: blob.type || 'image/jpeg' });
            newFiles.push(file);
        } catch (downloadErr) {
            console.error('Failed to load captured image ' + i, downloadErr);
        }
    }

    if (newFiles.length > 0) {
        _bulkImageFiles = _bulkImageFiles.concat(newFiles);
        renderBulkImageThumbnails();
    }
}

async function triggerAiExtractionFromModal() {
    const processAiBtn = document.getElementById('captureProcessAiBtn');
    const heading = document.getElementById('captureStep2Heading');
    const sub = document.getElementById('captureStep2Sub');

    if (processAiBtn) {
        processAiBtn.disabled = true;
        processAiBtn.innerHTML = '<div style="width:16px; height:16px; border:2px solid #ffffff; border-top-color:transparent; border-radius:50%; animation:bulk-spin 0.8s linear infinite;"></div> Extracting with Gemini Flash...';
    }
    if (heading) heading.textContent = 'Processing with Gemini AI...';
    if (sub) sub.textContent = 'Extracting names and payment amounts from scanned pages.';

    try {
        await extractBulkImagesWithAI();

        // Once output is ready in bulk, close the modal smoothly
        setTimeout(() => {
            closeBulkCaptureModal();
        }, 500);

    } catch (err) {
        console.error('AI extraction error from modal:', err);
        if (heading) heading.textContent = 'Extraction Failed';
        if (sub) sub.textContent = err.message || 'Please check API key and try again.';
        if (processAiBtn) {
            processAiBtn.disabled = false;
            processAiBtn.innerHTML = '<i class="fas fa-redo"></i> Retry AI Extraction';
        }
    }
}

async function simulateMobileCaptureUpload() {
    if (!_bulkCaptureSessionId) {
        alert('No active capture session. Please reopen the dialog.');
        return;
    }

    try {
        const resp = await window.csrfFetch('/api/bulk_capture/simulate_upload/' + _bulkCaptureSessionId, {
            method: 'POST'
        });
        const data = await resp.json();
        if (!data.success) {
            alert('Simulation error: ' + (data.error || 'Unknown error'));
        }
    } catch (err) {
        console.error('Simulation error:', err);
        alert('Simulation error: ' + err.message);
    }
}

