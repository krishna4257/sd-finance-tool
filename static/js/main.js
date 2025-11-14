// Declare currentRow at a higher scope (global via window) for cross-script access.
// This variable will store the currently highlighted table row element.
window.currentRow = null;

let tooltipTimeout = null;



document.addEventListener("DOMContentLoaded", function () {
  // Auto-focus first input on form pages (optional)
  const firstInput = document.querySelector("form input:not([type='hidden'])");
  if (firstInput) {
    firstInput.focus();
  }

  // Initialize DataTables for any tables with data
  const tables = document.querySelectorAll("table");
  tables.forEach(function (table) {
    // Exclude tables that are specifically handled by other JS files (e.g., search.js, post_payment.js, view_customers.html's inline script)
    const excludedIds = ["customerTable", "paymentTable", "tempTable", "postingTable"];
    if (excludedIds.includes(table.id)) {
        return; // Skip initialization for these tables
    }

    if (table.querySelector("thead") && !$.fn.DataTable.isDataTable(table)) {
      $(table).DataTable({
        dom: 'Bfrtip',
        paging: false,
        responsive: true,
        ordering: true,
        info: false,
        dom: 't',
        columnDefs: [
          { type: 'date-ddmmyyyy', targets: '_all' } // Apply to all columns by default for generic tables
        ]
      });
    }
  });


  // Smooth scroll to main content (optional UX touch)
  const main = document.getElementById("main-content");
  if (main) {
    main.scrollIntoView({ behavior: "smooth" });
  }

  // If there's a message box, auto-dismiss after 5 seconds
  const alerts = document.querySelectorAll(".alert, .flash-message");
  alerts.forEach(alert => {
    setTimeout(() => {
      alert.style.display = "none";
    }, 8080);
  });


    // NEW: Listen for DataTables redraw events and re-apply highlighting
    // This handles tables managed by DataTables (like paymentTable, postingTable)
    $(document).on('draw.dt', function(e, settings) {
        // Only proceed if a row was previously highlighted globally
        if (window.currentRow) {
            const currentTable = $(window.currentRow).closest('table');
            if (!currentTable.length) { // currentRow's table might no longer exist
                window.currentRow = null; // Clear stale reference
                return;
            }

            const tableId = currentTable.attr('id');
            // Ensure this is a DataTable instance to avoid errors on plain tables
            if ($.fn.DataTable.isDataTable(`#${tableId}`)) {
                const dt = $(`#${tableId}`).DataTable();
                
                // Get the unique identifier(s) of the previously highlighted row.
                // Assuming ANO is in the first column for ALL DataTables in your app (index 0).
                // If the table uses a different identifying column for `window.currentRow`, you'd need more specific logic.
                const previouslyHighlightedAno = $(window.currentRow).find('td:eq(0)').text().trim(); 
                
                // Ensure *all* existing highlights are removed before re-applying
                // This targets ALL highlighted rows within this specific table, regardless of window.currentRow state.
                $(`#${tableId} tbody tr.highlighted-row`).removeClass('highlighted-row');
                
                // Reset window.currentRow before finding the new one
                window.currentRow = null; 

                if (previouslyHighlightedAno) { // Only try to re-highlight if there was a previous ANO
                    // Find the new row in the current DataTable instance by its ANO
                    dt.rows().every(function() {
                        const rowNode = this.node();
                        // Get ANO from the current DataTables row in the *newly drawn* table
                        const anoInNewRow = $(rowNode).find('td:eq(0)').text().trim(); 

                        if (anoInNewRow === previouslyHighlightedAno) {
                            $(rowNode).addClass('highlighted-row');
                            window.currentRow = rowNode; // Update to the new DOM element
                            // Optional: Scroll the newly highlighted row into view if it wasn't already
                            // $(rowNode).get(0).scrollIntoView({ block: "nearest", behavior: "smooth" });
                            return false; // Break the loop once found the first match
                        }
                    });
                }
            }
        }
    });

  // Highlight active navigation based on current path (optional)
  const currentPath = window.location.pathname;
  const links = document.querySelectorAll("aside a");
  links.forEach(link => {
    if (link.getAttribute("href") === currentPath) {
      link.classList.add("active");
    }
  });


  // --- Row highlighting and arrow key navigation for ALL tables ---
  // Event delegation for row click highlighting
  document.body.addEventListener("click", function (e) {
    const row = e.target.closest("tr");
    // Ensure it's a row within a table and not excluded (e.g., the tempTable which has its own row interaction)
    if (row && row.closest("table") && row.closest("table").id !== "tempTable" ) {
      // Remove highlight from previously selected row if it exists and is not the current row
      if (window.currentRow && window.currentRow !== row) {
        window.currentRow.classList.remove("highlighted-row");
      }
      // Add highlight to the current row and update global currentRow
      window.currentRow = row;
      window.currentRow.classList.add("highlighted-row");
    }
  });

  // Arrow key navigation
  document.addEventListener("keydown", function (e) {
    if (!window.currentRow) return;

    // Ensure the current table is still valid
    const currentTable = window.currentRow.closest("table");
    if (!currentTable) {
      window.currentRow = null; // Reset if table no longer exists
      return;
    }

    // Get all visible rows of the current table
    const tbody = currentTable.querySelector("tbody");
    if (!tbody) return;

    const rows = [...tbody.querySelectorAll("tr")].filter(r => r.style.display !== "none");
    const currentIndex = rows.indexOf(window.currentRow);
    let nextIndex = currentIndex;

    if (e.key === "ArrowDown") {
      nextIndex = Math.min(rows.length - 1, currentIndex + 1);
    } else if (e.key === "ArrowUp") {
      nextIndex = Math.max(0, currentIndex - 1);
    } else {
      return; // Not an arrow key we care about
    }

    if (nextIndex !== currentIndex) {
      e.preventDefault(); // Prevent page scrolling

      // Remove highlight from current and apply to next
      window.currentRow.classList.remove("highlighted-row");
      window.currentRow = rows[nextIndex];
      window.currentRow.classList.add("highlighted-row");

      // Scroll the new current row into view
      window.currentRow.scrollIntoView({ block: "nearest", behavior: "smooth" });
    }
  });
});

document.addEventListener('click', function(e) {
    const row = e.target.closest('tr');
    if (row && row.parentElement.tagName === 'TBODY' && row.closest('.customer-table')) {
        document.querySelectorAll('.customer-table tbody tr').forEach(r => r.classList.remove('highlighted'));
        row.classList.add('highlighted');
    }
});

document.addEventListener('keydown', function(e) {
    const highlighted = document.querySelector('.customer-table tbody tr.highlighted');
    if (highlighted && highlighted.closest('#tempTable')) return;
    const rows = Array.from(document.querySelectorAll('.customer-table tbody tr'));

    if (!highlighted || rows.length === 0) return;

    let index = rows.indexOf(highlighted);

    if (e.key === 'ArrowDown') {
        e.preventDefault();
        index = (index + 1) % rows.length;
    } else if (e.key === 'ArrowUp') {
        e.preventDefault();
        index = (index - 1 + rows.length) % rows.length;
    } else {
        return; // Don't proceed if not up/down arrow
    }

    rows.forEach(r => r.classList.remove('highlighted'));
    rows[index].classList.add('highlighted');
});



function openEditVillageModal() {
  document.getElementById("editVillageModal").style.display = "block";
}
function closeEditVillageModal() {
  document.getElementById("editVillageModal").style.display = "none";
}
function submitVillageNameChange() {
  const newName = document.getElementById("newVillageName").value.trim();
  if (!newName) return alert("Village name cannot be empty.");

  fetch("/update_village_name", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ new_name: newName })
  })
  .then(res => res.json())
  .then(data => {
    if (data.success) {
      alert("Village name updated successfully.");
      closeEditVillageModal();
    } else {
      alert("Failed to update: " + data.error);
    }
  });
}


function openCreateVillageModal() {
  document.getElementById("createVillageModal").style.display = "block";
}
function closeCreateVillageModal() {
  document.getElementById("createVillageModal").style.display = "none";
}
function submitCreateVillage() {
  const num = document.getElementById("villageNumber").value.trim();
  const name = document.getElementById("villageName").value.trim();
  if (!num || !name) return alert("Both fields are required.");

  fetch("/create_village", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ number: num, name: name })
  })
  .then(res => res.json())
  .then(data => {
    if (data.success) {
      alert("Village created successfully.");
      closeCreateVillageModal();
    } else {
      alert("Error: " + data.error);
    }
  });
}



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


