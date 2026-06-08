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


// --- Instant lookup mapping ---
const CUSTOMER_MAP = {};

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
            da: Number(c.installment_amount) || 0
        };

        console.log("DEBUG: Loading customer into CUSTOMER_MAP:", normalized.ano, normalized.name);

        if (normalized.ano) {
            CUSTOMER_MAP[normalized.ano] = normalized;
        }

    } catch (err) {
        console.error("Failed loading customer:", c, err);
    }
});

// --- Expected Stats Calculations ---
const activeCustomers = window.CUSTOMERS.filter(c => (Number(c.balance_amount) || 0) > 0);
const expectedAccCount = activeCustomers.length;
const expectedTotalAmount = activeCustomers.reduce((sum, c) => sum + (Number(c.installment_amount) || 0), 0);

// --- Helper function to show errors and play sound ---
function showError(message) {
    const errorMsg = document.getElementById("errorMsg");
    errorMsg.innerText = message;
    errorMsg.style.display = "block";
    // Play the sound, catching potential browser errors
    errorSound.play().catch(e => console.warn("Could not play error sound:", e));
}


function ddmmyyyyToIso(dateStr) {
  // "10/01/2026" → "2026-01-10"
  const [dd, mm, yyyy] = dateStr.split('/');
  return `${yyyy}-${mm}-${dd}`;
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

        console.log("DEBUG PAYMENT STATS DATE =>", {
            original: pdt
        });

        const response = await fetch(
            `/api/payment_day_stats?date=${encodeURIComponent(pdt)}`
        );

        console.log("DEBUG PAYMENT STATS STATUS =>", response.status);

        if (!response.ok) {
            throw new Error(`HTTP ${response.status}`);
        }

        const data = await response.json();

        console.log("DEBUG PAYMENT DAY STATS RESPONSE =>", data);

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

        console.log("DEBUG FINAL COUNTS =>", {
            expectedPayments,
            alreadyPaidPayments
        });

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

document.addEventListener('click', function(e) {
    const row = e.target.closest('tr');
    if (row && row.parentElement.tagName === 'TBODY' && row.closest('.customer-table')) {
        document.querySelectorAll('.customer-table tbody tr').forEach(r => r.classList.remove('highlighted'));
        row.classList.add('highlighted');
    }
});

document.addEventListener('keydown', function (e) {
  const highlighted = document.querySelector('tbody tr.highlighted');
  if (!highlighted) return;

  const tbody = highlighted.closest('tbody');
  if (!tbody) return;

  // Only navigate within THIS table body, and only across visible rows
  const rows = Array.from(tbody.querySelectorAll('tr'))
    .filter(r => r.offsetParent !== null); // skip hidden rows

  const currIndex = rows.indexOf(highlighted);
  if (currIndex === -1) return;

  let nextIndex = currIndex;

  if (e.key === 'ArrowDown' || e.keyCode === 40) {
    e.preventDefault();
    nextIndex = Math.min(currIndex + 1, rows.length - 1);
  } else if (e.key === 'ArrowUp' || e.keyCode === 38) {
    e.preventDefault();
    nextIndex = Math.max(currIndex - 1, 0);
  } else {
    return;
  }

  rows.forEach(r => r.classList.remove('highlighted'));
  rows[nextIndex].classList.add('highlighted');
  rows[nextIndex].scrollIntoView({ block: 'nearest' });
});

let isEditingCell = false; // Prevent multiple cell editing sessions simultaneously

function makeCellEditable(cell, index, field, currentValue) {
    if (isEditingCell) return;
    isEditingCell = true;

    // Clear highlights temporarily to avoid visual clash
    document.querySelectorAll('#tempTable tbody tr').forEach(r => r.classList.remove('highlighted'));

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
        flatpickr(input, {
            dateFormat: 'd/m/Y',
            allowInput: true,
            onClose: function() {
                setTimeout(() => finishEdit(true), 150);
            }
        });
    } else {
        input.addEventListener("blur", function() {
            setTimeout(() => finishEdit(true), 150);
        });
    }
}

function updateTable() {
  console.log("DEBUG: updateTable() called. TempTable length:", tempTable.length, "Contents:", tempTable);
  const tbody = document.querySelector("#tempTable tbody");
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
  persistTempPayments();
  updateTable();
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

  console.log("DEBUG FORM SUBMIT =>", { pdt, ano, amt });

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

  const customer = CUSTOMER_MAP[String(ano)];

  console.log("DEBUG CUSTOMER LOOKUP =>", customer);

  if (!customer) {
    showError("❌ A.no not found in database!");
    return;
  }

  const duplicate = tempTable.some(
    row => String(row.ano) === String(ano) && row.pdt === pdt
  );

  console.log("DEBUG DUPLICATE CHECK =>", duplicate);

  if (duplicate) {
    showError("❌ Duplicate A.no + Date combo exists.");
    return;
  }

  tempTable.unshift({
    ano: String(ano),
    pdt,
    amt: Number(amt)
  });

  console.log("DEBUG ROW ADDED =>", tempTable[0]);

  saveAndUpdate();

  document.getElementById("ano").value = "";
  document.getElementById("amt").value = "";

  document.getElementById("customerInfo").style.display = "none";

  document.getElementById("ano").focus();
});

document.getElementById("amt").disabled = true;

document.getElementById("ano").addEventListener("keydown", function (e) {
    if (e.key !== "Enter") return;

    e.preventDefault();
    const ano = this.value.trim();
    console.log("DEBUG: Enter pressed on ANO field. ANO typed:", ano);
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
    console.log("DEBUG: Typed ANO:", ano, "Lookup result:", customer);
    if (!customer) {
        showError("❌ A.no not found in database!");
        return;
    }

    // SUCCESS
    console.log("DEBUG: Customer found, displaying info:", customer);
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

updateTable();
applyGlobalMoneyFormatting();
loadAnalytics(); // Fetch analytics and render mixed chart on page load

// --- Auto-focus & flatpickr & live collection stats loader & flip card listeners ---
document.addEventListener("DOMContentLoaded", () => {
    flatpickr("#pdt", {
        dateFormat: 'd/m/Y',
        allowInput: true,
        clickOpens: true,
        wrap: false
    });

    const pdtInput = document.getElementById("pdt");
    if (pdtInput) {
        pdtInput.focus();

        // Place cursor at the end — Safari-safe fallback
        const len = pdtInput.value.length;
        try { pdtInput.setSelectionRange(len, len); } catch (e) {}
        setTimeout(() => {
            try { pdtInput.setSelectionRange(len, len); } catch (e) {}
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
});