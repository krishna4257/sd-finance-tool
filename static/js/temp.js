let tooltipTimeout = null;
let isSelecting = false;
let isDeselecting = false;


// Handle mouse down and drag selection
function initializeRowSelectionSummary() {
  document.addEventListener('mousedown', function(e) {
    const row = e.target.closest('table.customer-table tbody tr');
    if (row) {
        isSelecting = true;
        isDeselecting = row.classList.contains('highlighted-row'); // Determine mode
    }
});


document.addEventListener('mouseover', function(e) {
    if (isSelecting) {
        const row = e.target.closest('table.customer-table tbody tr');
        if (row) {
            if (isDeselecting) {
                row.classList.remove('highlighted-row');
            } else {
                row.classList.add('highlighted-row');
            }
            updateSelectionSummary();
        }
    }
});


document.addEventListener('mouseup', function() {
    isSelecting = false;
});

}

function updateSelectionSummary() {
  const selectedRows = document.querySelectorAll('tr.highlighted-row');
  let total = 0;
  let sumColumnIndex = null;

  if (selectedRows.length === 0) {
    document.getElementById('selectionSummaryPopup').style.display = 'none';
    return;
  }

  // Determine sum column dynamically from table's data attribute
  const table = selectedRows[0].closest('table');
  const sumColumnName = table.getAttribute('data-sum-column');

  if (sumColumnName) {
    const headerCells = table.querySelectorAll('thead th');
    headerCells.forEach((th, index) => {
      if (th.textContent.trim() === sumColumnName) {
        sumColumnIndex = index;
      }
    });
  }

  if (sumColumnIndex !== null) {
    selectedRows.forEach(row => {
      const cell = row.cells[sumColumnIndex];
      const val = parseFloat(cell?.textContent.trim().replace(/[^\d.-]/g, '')) || 0;
      total += val;
    });
  }

  document.getElementById('selectedCount').textContent = selectedRows.length;
  document.getElementById('selectedTotal').textContent = total.toFixed(2);
  document.getElementById('selectionSummaryPopup').style.display = 'block';
}



// Global Input Handling Script

document.addEventListener('DOMContentLoaded', function() {

    // --- Date Input Masking ---
    function applyDateMask(input) {
        input.addEventListener('input', function(e) {
            let val = input.value.replace(/\D/g, ''); // Remove non-digits
            if (val.length > 8) val = val.slice(0, 8);

            let day = val.slice(0, 2);
            let month = val.slice(2, 4);
            let year = val.slice(4, 8);

            let newVal = day;
            if (val.length > 2) newVal += '/' + month;
            if (val.length > 4) newVal += '/' + year;

            input.value = newVal;
        });

        input.addEventListener('keydown', function(e) {
            // Prevent jumping caret on Backspace/Delete
            const pos = this.selectionStart;
            const prevLen = this.value.length;

            setTimeout(() => {
                const newLen = this.value.length;
                const diff = newLen - prevLen;
                const newPos = pos + diff;
                this.setSelectionRange(newPos, newPos);
            }, 0);
        });
    }

    // Apply date mask globally to all inputs with placeholder dd/mm/yyyy
    document.querySelectorAll('input[placeholder*="dd/mm/yyyy"]').forEach(input => {
        applyDateMask(input);
    });

    // --- Preserve Cursor Position on Enter for Search Fields ---
    document.querySelectorAll('input[type="text"]').forEach(input => {
        input.addEventListener('keydown', function(e) {
            if (e.key === 'Enter') {
                const pos = this.selectionStart;
                setTimeout(() => {
                    this.setSelectionRange(pos, pos);
                }, 0);
            }
        });
    });

});

function stripToNumber(text) {
  const raw = text.replace(/[^\d.-]/g, '');
  return raw;
}
function placeCaretAtEnd(el) {
  const range = document.createRange();
  range.selectNodeContents(el);
  range.collapse(false);
  const sel = window.getSelection();
  sel.removeAllRanges();
  sel.addRange(range);
}


// Global Money Formatter (₹ + Commas)
function formatWithRupeeAndCommas(amount) {
    if (isNaN(amount) || amount === '') return '';
    const number = parseFloat(amount);
    return `₹${number.toLocaleString('en-IN', { minimumFractionDigits: 0, maximumFractionDigits: 0 })}`;
}

 function applyGlobalMoneyFormatting() {
   const moneyFields = document.querySelectorAll('[data-money]');
   moneyFields.forEach(el => {
    if (el.dataset.editing === '1') return; // don’t touch while user is typing
     let val = el.textContent.trim();
     val = val.replace(/[^\d.-]/g, ''); // Remove existing symbols/commas
     if (val !== '') {
+      // keep a clean numeric copy for logic/saves
+      el.setAttribute('data-money', String(parseFloat(val)));
       el.textContent = formatWithRupeeAndCommas(val);
     }
   });
 }


window.addEventListener('DOMContentLoaded', applyGlobalMoneyFormatting);
// Initialize on DOM Load
document.addEventListener('DOMContentLoaded', initializeRowSelectionSummary);


const newEmpNameInput = document.getElementById("newEmpName");
if (newEmpNameInput) {
  newEmpNameInput.addEventListener("blur", async () => {
    const name = newEmpNameInput.value.trim();
    if (!name) return;

    const res = await fetch(`/api/employee/check?name=${encodeURIComponent(name)}`);
    const data = await res.json();

    document.getElementById("newEmpFields").style.display =
      data.found ? "none" : "block";
  });
}

const villageCodeInput = document.getElementById("villageCode");
const villageNameInput = document.getElementById("villageName");
const codeError = document.getElementById("villageCodeError");
const nameError = document.getElementById("villageNameError");


function checkVillageDuplicate() {
  const code = villageCodeInput.value.trim();
  const name = villageNameInput.value.trim();
  const emp1 = document.getElementById("emp1Select").value;

  if (!code || !name || !emp1) return;

  fetch(`/api/village/check?code=${encodeURIComponent(code)}&name=${encodeURIComponent(name)}&emp1=${emp1}`)
    .then(res => res.json())
    .then(data => {
      const error = document.getElementById("villageCodeError");
      error.textContent = "Village already exists for this employee";
      error.style.display = data.exists ? "block" : "none";
    });
}

villageCodeInput.addEventListener("input", debounce(checkVillageDuplicate, 400));
villageNameInput.addEventListener("input", debounce(checkVillageDuplicate, 400));
document.getElementById("emp1Select").addEventListener("change", checkVillageDuplicate);