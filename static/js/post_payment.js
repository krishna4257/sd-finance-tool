// --- Initialize sound effect ---
// Make sure you have a file at static/sounds/error.mp3
const errorSound = new Audio('static/sounds/error.mp3');
let tempTable = JSON.parse(localStorage.getItem('postPayments') || '[]');
let selectedDate = null;


// --- Instant lookup mapping ---
const CUSTOMER_MAP = {};
window.CUSTOMERS.forEach(c => {
    // Normalize backend keys to the frontend expected shape
    const normalized = {
        // ANO might be under ANO (uppercase) or ano (lowercase) or Ano
        ano: (c.ANO !== undefined ? String(c.ANO) :
              (c.ano !== undefined ? String(c.ano) :
              (c.Ano !== undefined ? String(c.Ano) : ''))).trim(),

        // name may be in NAME, name, or ANO1 depending on backend
        name: (c.NAME !== undefined ? String(c.NAME) :
               (c.name !== undefined ? String(c.name) :
               (c.ANO1 !== undefined ? String(c.ANO1) : ''))).trim(),

        // Numeric fields: convert to Number (fallback 0)
        amt: Number(c.AMT ?? c.amt ?? 0) || 0,
        pamt: Number(c.PAMT ?? c.pamt ?? 0) || 0,
        bamt: Number(c.BAMT ?? c.bamt ?? 0) || 0,
        da: Number(c.DA ?? c.da ?? 0) || 0
    };

    console.log("DEBUG: Loading customer into CUSTOMER_MAP:", normalized.ano, normalized.name);
    if (normalized.ano) {
        CUSTOMER_MAP[normalized.ano] = normalized;
    }
});

// --- Helper function to show errors and play sound ---
function showError(message) {
    const errorMsg = document.getElementById("errorMsg");
    errorMsg.innerText = message;
    errorMsg.style.display = "block";
    // Play the sound, catching potential browser errors
    errorSound.play().catch(e => console.warn("Could not play error sound:", e));
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

    const pdtCell = document.createElement("td");
    pdtCell.textContent = row.pdt;

    const amtCell = document.createElement("td");
    amtCell.classList.add("amount-paid");

    const amtText = document.createElement("span");
    amtText.textContent = row.amt?.toFixed(2) || "0.00";
    amtText.setAttribute('data-money', '');  // ✅ ✅ Only on <span>
    amtCell.appendChild(amtText);

    const amtInput = document.createElement("input");
    amtInput.type = "number";
    amtInput.value = row.amt?.toFixed(2) || "0.00";
    amtInput.style.display = "none";
    amtInput.style.width = "100%";
    amtCell.appendChild(amtInput);

    const cumulativeCell = document.createElement("td");
    cumulativeCell.classList.add("cumulative-amt");
    cumulativeCell.textContent = "";

    const editBtn = document.createElement("button");
    editBtn.textContent = "✏️";
    editBtn.classList.add("neumorphic-btn", "ultrasmall");
    editBtn.onclick = () => {
      if (editBtn.textContent === "✏️") {
        amtText.style.display = "none";
        amtInput.style.display = "inline-block";
        amtInput.focus();
        editBtn.textContent = "💾";
      } else {
        const newAmt = parseFloat(amtInput.value);
        if (!isNaN(newAmt)) {
          row.amt = newAmt;
          tempTable[index].amt = newAmt;  // ✅ Update memory
          amtText.textContent = newAmt.toFixed(2);
          saveAndUpdate();
        }
        amtText.style.display = "inline-block";
        amtInput.style.display = "none";
        editBtn.textContent = "✏️";
      }
    };

    const deleteBtn = document.createElement("button");
    deleteBtn.textContent = "🗑️";
    deleteBtn.classList.add("neumorphic-btn", "ultrasmall");
    deleteBtn.onclick = () => {
      tempTable.splice(index, 1);
      saveAndUpdate();
    };

    tr.appendChild(anoCell);
    tr.appendChild(pdtCell);
    tr.appendChild(amtCell);
    tr.appendChild(cumulativeCell);

    const editCell = document.createElement("td");
    editCell.appendChild(editBtn);
    tr.appendChild(editCell);

    const deleteCell = document.createElement("td");
    deleteCell.appendChild(deleteBtn);
    tr.appendChild(deleteCell);

    tbody.appendChild(tr);
    uniqueAno.add(row.ano);
    totalAmt += row.amt;
  });

  document.getElementById("totalAnotop").textContent = uniqueAno.size;
  document.getElementById("totalAmttop").textContent = totalAmt.toFixed(2);
  document.getElementById("totalAno").textContent = uniqueAno.size;
  document.getElementById("totalAmt").textContent = totalAmt.toFixed(2);
  localStorage.setItem("postPayments", JSON.stringify(tempTable));

  // Cumulative Sum Logic
  let runningTotal = 0;
  const rows = Array.from(document.querySelectorAll("#tempTable tbody tr")).reverse();

  rows.forEach(row => {
    const amtSpan = row.querySelector("td.amount-paid span");
    const cumulativeCell = row.querySelector("td.cumulative-amt");
    const amt = parseFloat(amtSpan?.textContent.trim().replace(/[^\d.-]/g, '')) || 0;
    runningTotal += amt;
    cumulativeCell.textContent = runningTotal.toFixed(2);
    cumulativeCell.setAttribute('data-money', '');
  });

  applyGlobalMoneyFormatting();
}



let sortState = { ano: 0, pdt: 0, amt: 0 };

function sortTemp(column) {
  for (let key in sortState) {
    if (key !== column) sortState[key] = 0;
  }
  sortState[column] = (sortState[column] + 1) % 3;

  if (sortState[column] === 0) {
    tempTable = JSON.parse(localStorage.getItem("postPayments") || "[]");
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
  localStorage.setItem("postPayments", JSON.stringify(tempTable));
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
  if (tempTable.length === 0) {
    alert("There are no payments to submit.");
    return;
  }

  fetch("/submit_post_payment", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(tempTable)
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
    })
    .catch(err => {
        showError(`An error occurred: ${err.message}`);
    });
}

document.getElementById("paymentForm").addEventListener("submit", function (e) {
  e.preventDefault();
  const pdt = document.getElementById("pdt").value;
  const ano = document.getElementById("ano").value;
  const amt = parseFloat(document.getElementById("amt").value);

  if (!pdt || !ano || isNaN(amt)) return;

  const duplicate = tempTable.some(row => row.ano === ano && row.pdt === pdt);
  console.log("DEBUG: Submit pressed. ANO:", ano, "PDT:", pdt, "Amount:", amt, "Duplicate:", duplicate);
  if (duplicate) {
    showError("Duplicate A.no + Date combo exists.");
    return;
  }

  tempTable.unshift({ ano, pdt, amt });
  saveAndUpdate();
  document.getElementById("ano").value = "";
  document.getElementById("amt").value = "";
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
    const customer = CUSTOMER_MAP[ano];
    console.log("DEBUG: Typed ANO:", ano, "Lookup result:", customer);
    if (!customer) {
        showError("❌ A.no not found in database!");
        return;
    }

    // SUCCESS
    console.log("DEBUG: Customer found, displaying info:", customer);
    document.getElementById("customerName").innerText = customer.name;
    document.getElementById("customerLoanAmount").innerText = customer.amt;
    document.getElementById("customerTotalRepaid").innerText = customer.pamt;
    document.getElementById("customerOutstanding").innerText = customer.bamt;
    document.getElementById("customerInstallmentAmount").innerText = customer.da;

    customerInfo.style.display = "block";
    amtInput.disabled = false;
    amtInput.focus();
});

updateTable();
applyGlobalMoneyFormatting();

// --- Auto-focus the Date (PDT) field when Post Payment page loads ---
document.addEventListener("DOMContentLoaded", () => {
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
});