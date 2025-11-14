// --- DataTables Custom Sorting Plugin for dd/mm/yyyy dates ---
$.fn.dataTable.ext.type.order['date-ddmmyyyy-pre'] = function (d) {
    if (!d || typeof d !== 'string') {
        return 0;
    }
    const parts = d.split('/');
    if (parts.length < 3) {
        return 0;
    }
    return parseInt(parts[2] + parts[1] + parts[0], 10);
};
// --- End of Plugin ---


// All code MUST be inside this single DOMContentLoaded listener
document.addEventListener("DOMContentLoaded", () => {

  // --- Element Selectors ---
  const customerRow = document.querySelector(".customer-row");
  const paymentTable = document.getElementById("paymentTable");
  const editCustomerBtn = document.querySelector(".edit-customer");
  const saveCustomerBtn = document.getElementById("saveCustomerBtn");
  const editPaymentsBtn = document.querySelector(".edit-payments");
  const savePaymentsBtn = document.getElementById("savePaymentsBtn");
  const customerForm = document.querySelector("form[method='POST']");
  const postingSection = document.getElementById("posting-section");
  const postingForm = document.getElementById("postingSearchForm");
  const postingTableBody = document.querySelector("#postingTable tbody");

  function stripToNumber(text) {
    return text.replace(/[^\d.-]/g, '');
  }

  function placeCaretAtEnd(el) {
    const range = document.createRange();
    range.selectNodeContents(el);
    range.collapse(false);
    const sel = window.getSelection();
    sel.removeAllRanges();
    sel.addRange(range);
  }

  // Enter edit mode
  document.addEventListener('focusin', (e) => {
    const el = e.target;
    if (el.matches('td[data-money][contenteditable="true"]')) {
      el.dataset.editing = '1';
      el.textContent = stripToNumber(el.textContent);
      placeCaretAtEnd(el);
    }
  });

  // While typing
  document.addEventListener('input', (e) => {
    const el = e.target;
    if (el.matches('td[data-money][contenteditable="true"]')) {
      const raw = stripToNumber(el.textContent);
      el.setAttribute('data-money', raw);
      if (typeof updateTotalsAndLoanee === 'function') updateTotalsAndLoanee();
      if (typeof updatePostingTableTotals === 'function') updatePostingTableTotals();
    }
  });

  // Exit edit mode
  document.addEventListener('focusout', (e) => {
    const el = e.target;
    if (el.matches('td[data-money][contenteditable="true"]')) {
      const raw = stripToNumber(el.textContent) || '0';
      el.setAttribute('data-money', raw);
      el.textContent = formatWithRupeeAndCommas(raw);
      delete el.dataset.editing;
    }
  });


  // --- Logic for: Edit Customer Details ---
  if (editCustomerBtn && customerRow && saveCustomerBtn) {
    editCustomerBtn.addEventListener("click", () => {
      customerRow.querySelectorAll("td[data-field]").forEach((td) => {
        if (!["ANO", "ADD1"].includes(td.dataset.field)) {
          td.setAttribute("contenteditable", "true");
        }
      });
      editCustomerBtn.style.display = "none";
      saveCustomerBtn.style.display = "inline-block";
    });

    saveCustomerBtn.addEventListener("click", () => {
      const updatedData = {};
      customerRow.querySelectorAll("td[data-field]").forEach((td) => {
        updatedData[td.dataset.field] = td.textContent.trim();
      });

      fetch("/update_customer_and_payments", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ type: "customer", data: updatedData })
      })
      .then((res) => res.json())
      .then((data) => {
        if (data.success) {
          customerRow.querySelectorAll("td").forEach((td) => {
            td.setAttribute("contenteditable", "false");
          });
          saveCustomerBtn.style.display = "none";
          editCustomerBtn.style.display = "inline-block";
        } else {
          alert("Update failed: " + data.error);
        }
      })
      .catch((err) => alert("Error: " + err.message));
    });
  }

  // --- Logic for: Edit Payment Amounts in Customer View ---
  if (editPaymentsBtn && paymentTable && savePaymentsBtn) {
    editPaymentsBtn.addEventListener("click", () => {
      paymentTable.querySelectorAll("td[data-field='AMT']").forEach((cell) => {
        cell.setAttribute("contenteditable", "true");
        cell.addEventListener("input", updateTotalsAndLoanee);
      });
      editPaymentsBtn.style.display = "none";
      savePaymentsBtn.style.display = "inline-block";
    });

    savePaymentsBtn.addEventListener("click", () => {
      const updatedPayments = [];
      document.querySelectorAll("#paymentTable tbody tr").forEach((row) => {
        const ano = row.dataset.ano;
        const pdt = row.dataset.pdt;
        const amtCell = row.querySelector("td[data-field='AMT']");
        if (amtCell) {
          const amt = parseFloat(amtCell.textContent.replace(/[^\d.-]/g, '')) || 0;
          updatedPayments.push({ ano, pdt, amt });
        }
      });

      fetch("/update_customer_and_payments", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ type: "payments", data: updatedPayments })
      })
      .then((res) => res.json())
      .then((data) => {
        if (data.success) {
          document.querySelectorAll("td[data-field='AMT']").forEach((cell) => {
            cell.setAttribute("contenteditable", "false");
          });
          savePaymentsBtn.style.display = "none";
          editPaymentsBtn.style.display = "inline-block";
        } else {
          alert("Payment update failed: " + data.error);
        }
      })
      .catch((err) => alert("Error: " + err.message));
    });
  }

  // --- Logic for: Edit/Save individual rows in Posting Table ---
  if (postingTableBody) {
      postingTableBody.addEventListener("click", function (e) {
          if (!e.target.classList.contains("posting-edit-btn")) return;

          const button = e.target;
          const row = button.closest("tr");
          if (!row) return alert("Error: Could not find the parent table row.");

          const pdtCell = row.querySelector("td[data-field='PDT']");
          const amtCell = row.querySelector("td[data-field='AMT']");
          if (!pdtCell || !amtCell) return alert("Error: Could not find Date/Amount cells.");

          const isEditing = button.getAttribute("data-editing") === "true";

          if (!isEditing) {
              pdtCell.setAttribute("contenteditable", "true");
              amtCell.setAttribute("contenteditable", "true");
              pdtCell.focus();
              pdtCell.classList.add("highlighted");
              amtCell.classList.add("highlighted");
              button.textContent = "💾 Save";
              button.setAttribute("data-editing", "true");
          } else {
              const originalPdt = row.dataset.pdt;
              const ano = row.cells[0].textContent.trim();
              const newPdt = pdtCell.textContent.trim();
              const newAmt = parseFloat(amtCell.textContent.replace(/[^\d.-]/g, '')) || 0;

              fetch("/update_customer_and_payments", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                  type: "payment_posting_update",
                  data: { ano: ano, original_pdt: originalPdt, new_pdt: newPdt, new_amt: newAmt }
                })
              })
              .then(res => res.json())
              .then(data => {
                if (data.success) {
                  pdtCell.setAttribute("contenteditable", "false");
                  amtCell.setAttribute("contenteditable", "false");
                  pdtCell.classList.remove("highlighted");
                  amtCell.classList.remove("highlighted");
                  button.textContent = "✏️ Edit";
                  button.setAttribute("data-editing", "false");
                  row.dataset.pdt = newPdt;
                } else {
                  alert("Save failed: " + data.error);
                }
              }).catch(err => alert("Fetch Error: " + err.message));
          }
      });
  }

  // --- Logic for: Posting Search Form Submission ---
  // In search.js, replace your existing postingForm event listener
  if (postingForm) {
      postingForm.addEventListener("submit", (e) => {
          e.preventDefault();
          
          const customerSection = document.getElementById("customer-section");
          if (customerSection) customerSection.style.display = "none";
          if (postingSection) postingSection.style.display = "block";

          const ano = document.getElementById("searchPostingAno").value;
          const date = document.getElementById("searchPostingDate").value;

          fetch("/search_postings", {
              method: "POST",
              headers: { "Content-Type": "application/json" },
              body: JSON.stringify({ ano, date }),
          })
          .then((res) => res.json())
          .then((data) => {
              const tbody = document.querySelector("#postingTable tbody");
              if (!tbody) return;

              if ($.fn.DataTable.isDataTable("#postingTable")) {
                  $("#postingTable").DataTable().destroy();
              }
              tbody.innerHTML = "";
              applyGlobalMoneyFormatting(); 

              if (data.success && data.data) {
                  data.data.forEach((row) => {
                      const tr = document.createElement("tr");
                      tr.dataset.pdt = row.PDT;
                      tr.innerHTML = `
                          <td>${row.ANO}</td>
                          <td data-field="PDT" contenteditable="false">${row.PDT}</td>
                          <td data-field="AMT" contenteditable="false" data-money>${row.AMT}</td>
                          <td class="cumulative-amt"></td>  <!-- New Cumulative Amount Column -->
                          <td>
                              <button class="neumorphic-btn ultrasmall posting-edit-btn">✏️ Edit</button>
                              <span class="delete-btn" onclick="deletePaymentFromPostingRow(this, '${row.ANO}', '${row.PDT}')">🗑️</span>
                          </td>
                      `;
                      tbody.appendChild(tr);
                      applyGlobalMoneyFormatting();  
                  });
              }

              $("#postingTable").DataTable({
                  paging: false,
                  searching: false,
                  ordering: true,
                  info: false,
                  columnDefs: [
                      { targets: "nosort", orderable: false },
                      { type: "num", targets: [0, 2] },
                      { type: "date-ddmmyyyy", targets: 1 },
                  ],
              });

              updatePostingTableTotals();
              updateCumulativeSum('postingTable');
          });
      });
  }

  // Ensure this helper function exists in search.js
  function updatePostingTableTotals() {
      const rows = document.querySelectorAll("#postingTable tbody tr");
      let totalAmt = 0;

      if (rows.length === 0 || (rows.length === 1 && rows[0].querySelector('td.dataTables_empty'))) {
          document.getElementById("postingEntryCount").textContent = 0;
          document.getElementById("postingTotalAmt").setAttribute("data-money", "0.00");
          document.getElementById("postingTotalAmt").textContent = "0.00";
          applyGlobalMoneyFormatting();
          return;
      }

      rows.forEach((row) => {
          const amtCell = row.querySelector("td[data-field='AMT']");
          if (amtCell) {
              const amt = parseFloat(amtCell.textContent.replace(/[^\d.-]/g, '')) || 0;
              totalAmt += amt;
          }
      });

      document.getElementById("postingEntryCount").textContent = rows.length;
      document.getElementById("postingTotalAmt").setAttribute("data-money", totalAmt.toFixed(2));
      document.getElementById("postingTotalAmt").textContent = totalAmt.toFixed(2);
      applyGlobalMoneyFormatting();
  }


  // Add this inside DOMContentLoaded in search.js
  $('#paymentTable tbody').on('click', 'tr', function() {
      // Remove highlight from all rows
      $('#paymentTable tbody tr').removeClass('highlighted').removeAttr('data-selected');

      // Add highlight & a 'selected' marker to the clicked row
      $(this).addClass('highlighted').attr('data-selected', 'true');
  });

  // Reapply highlight after sorting
  $('#paymentTable').on('order.dt', function() {
      $('#paymentTable tbody tr').removeClass('highlighted');
      $('#paymentTable tbody tr[data-selected="true"]').addClass('highlighted');
  });


  // --- Logic for: Toggle between Customer and Posting sections ---
  if (customerForm) {
    customerForm.addEventListener("submit", () => {
      document.getElementById("customer-section").style.display = "block";
      if (postingSection) postingSection.style.display = "none";
    });
  }
  
  // --- Logic for Bulk Date Edit Modal ---
  const bulkDateChangeBtn = document.getElementById("bulkDateChangeBtn");
  if(bulkDateChangeBtn) {
    bulkDateChangeBtn.addEventListener("click", () => {
      const modal = document.getElementById("dateReplaceModal");
      if(modal) modal.style.display = "block";
    });
  }


  // --- Helper Functions (defined on window to be accessible from HTML) ---
  window.deletePaymentFromElement = (el) => {
    const row = el.closest("tr");
    const ano = row.dataset.ano;
    const pdt = row.dataset.pdt;
    fetch("/delete_payment", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ ano, pdt })
    })
    .then(res => res.json())
    .then(data => {
      if (data.success) {
        row.remove();
        updateTotalsAndLoanee();
      } else {
        alert("Failed to delete: " + data.error);
      }

      // Clear any highlights left (no selection)
      $('#paymentTable tbody tr').removeClass('highlighted').removeAttr('data-selected');   

    })
    .catch(err => alert("Delete error: " + err.message));
  };
  
  window.deletePaymentFromPostingRow = (el, ano, pdt) => {
    fetch("/delete_payment", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ ano, pdt })
    })
    .then(res => res.json())
    .then(data => {
      if (data.success) {
        el.closest("tr").remove();
      } else {
        alert("Delete failed: " + data.error);
      }
    });
  };

  window.addPaymentFromForm = (form) => {
    const ano = form.dataset.ano;
    const pdt = document.getElementById("newPDT").value;
    const amt = parseFloat(document.getElementById("newAMT").value || 0);
    fetch("/add_payment", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ ano, pdt, amt })
    })
    .then(res => res.json())
    .then(data => {
      if (data.success) {
        const tbody = paymentTable.querySelector("tbody");
        const newRow = document.createElement("tr");
        newRow.dataset.ano = ano;
        newRow.dataset.pdt = pdt;
        newRow.innerHTML = `
          <td>${ano}</td>
          <td data-field="PDT">${pdt}</td>
          <td data-field="AMT" contenteditable="false" data-money="${amt.toFixed(2)}">${amt.toFixed(2)}</td>
          <td><span class="delete-btn" onclick="deletePaymentFromElement(this)">🗑️</span></td>
        `;
        tbody.appendChild(newRow);
        applyGlobalMoneyFormatting(); 
        updateTotalsAndLoanee();
        form.reset();
      } else {
        alert("Failed to add payment: " + data.error);
      }

      // (optional) highlight just the row we already appended:
      $('#paymentTable tbody tr').removeClass('highlighted').removeAttr('data-selected');
      $(newRow).addClass('highlighted').attr('data-selected', 'true');

    })
    .catch(err => alert("Error: " + err.message));
    return false;
  };
  
  window.submitDateReplace = () => {
    const findDate = document.getElementById("findDateInput").value;
    const replaceDate = document.getElementById("replaceDateInput").value;
    fetch("/update_posting_date_bulk", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ find_date: findDate, replace_date: replaceDate })
    })
    .then(res => res.json())
    .then(data => {
      const msgBox = document.getElementById("postingMessageBox");
      msgBox.style.display = "block";
      msgBox.className = "message-box " + (data.success ? "success" : "error");
      msgBox.textContent = data.message || data.error;
      if (data.success) {
        document.getElementById("dateReplaceModal").style.display = "none";
        if (postingForm) postingForm.dispatchEvent(new Event("submit"));
      }
    });
  };

  function updateTotalsAndLoanee() {
    if (!paymentTable) return;
    const rows = paymentTable.querySelectorAll("tbody tr");
    let totalAmt = 0;
    rows.forEach(row => {
        const amtCell = row.querySelector("td[data-field='AMT']");
        
        // Get the text content, remove non-numeric characters (except for the decimal point and a leading minus sign)
        const cleanedText = amtCell?.textContent.trim().replace(/[^\d.-]/g, '');
        const amt = parseFloat(cleanedText) || 0; // Now this will correctly parse '2500.00'
        
        if (!isNaN(amt)) totalAmt += amt;
    });
    document.getElementById("totalAmt").textContent = totalAmt.toFixed(2);
    document.getElementById("anoCount").textContent = rows.length;
    applyGlobalMoneyFormatting();
    if (customerRow) {
      const amtCell = customerRow.querySelector("td[data-field='AMT']");
      const pamtCell = customerRow.querySelector("td[data-field='PAMT']");
      const bamtCell = customerRow.querySelector("td[data-field='BAMT']");
      const amt = parseFloat(amtCell?.textContent.trim()) || 0;
      if (pamtCell && bamtCell) {
        pamtCell.textContent = totalAmt.toFixed(2);
        bamtCell.textContent = (amt - totalAmt).toFixed(2);
      }
    }
  }

  // --- Auto-calculation Functions ---
  function recalculateBAMT(row) {
    const amtCell = row.querySelector('td[data-field="AMT"]');
    const pamtCell = row.querySelector('td[data-field="PAMT"]');
    const bamtCell = row.querySelector('td[data-field="BAMT"]');
    const amt = parseFloat(amtCell.textContent.trim());
    const pamt = parseFloat(pamtCell.textContent.trim());
    if (!isNaN(amt) && !isNaN(pamt)) {
      bamtCell.textContent = (amt - pamt).toFixed(2);
    }
  }

  function recalculateTDT(row) {
    const fdtCell = row.querySelector('td[data-field="FDT"]');
    const dwCell = row.querySelector('td[data-field="DW"]');
    const dsCell = row.querySelector('td[data-field="DS"]');
    const tdtCell = row.querySelector('td[data-field="TDT"]');
    const fdtStr = fdtCell.textContent.trim();
    const dw = dwCell.textContent.trim().toUpperCase();
    const ds = parseInt(dsCell.textContent.trim());
    if (!fdtStr || !dw || isNaN(ds)) return;
    try {
      const [dd, mm, yyyy] = fdtStr.split("/");
      const fdt = new Date(`${yyyy}-${mm}-${dd}`);
      if (dw === "W") fdt.setDate(fdt.getDate() + ds * 7);
      else if (dw === "M") fdt.setMonth(fdt.getMonth() + ds);
      const newDay = String(fdt.getDate()).padStart(2, '0');
      const newMonth = String(fdt.getMonth() + 1).padStart(2, '0');
      const newYear = fdt.getFullYear();
      tdtCell.textContent = `${newDay}/${newMonth}/${newYear}`;
    } catch (e) {
      console.warn("Invalid FDT format", e);
    }
  }

  function recalculateDA(row) {
    const amtCell = row.querySelector('td[data-field="AMT"]');
    const dsCell = row.querySelector('td[data-field="DS"]');
    const daCell = row.querySelector('td[data-field="DA"]');
    const amt = parseFloat(amtCell.textContent.trim());
    const ds = parseInt(dsCell.textContent.trim());
    if (!isNaN(amt) && !isNaN(ds) && ds !== 0) {
      daCell.textContent = (amt / ds).toFixed(2);
    }
  }
  
  // Attach live calculation listeners
  if (customerRow) {
      ["FDT", "DS", "DW"].forEach((field) => {
        const cell = customerRow.querySelector(`td[data-field="${field}"]`);
        if (cell) {
          cell.addEventListener("input", () => {
            recalculateTDT(customerRow);
            recalculateDA(customerRow);
          });
        }
      });
      ["AMT"].forEach((field) => {
        const cell = customerRow.querySelector(`td[data-field="${field}"]`);
        if (cell) {
          cell.addEventListener("input", () => {
            recalculateDA(customerRow);
            recalculateBAMT(customerRow);
          });
        }
      });
  }
  
  // --- Initial Page Setup ---
  if (document.querySelector("input[name='query']")?.value.trim() !== "") {
    if (postingSection) postingSection.style.display = "none";
    document.getElementById("customer-section").style.display = "block";
  }
  
  updateTotalsAndLoanee();

  const $paymentTable = $('#paymentTable');
  if ($paymentTable.length && !$.fn.DataTable.isDataTable($paymentTable)) {
    $paymentTable.DataTable({
      paging: false,
      searching: false,
      ordering: true,
      info: false,
      columnDefs: [
        { targets: 'nosort', orderable: false },
        { type: 'num', targets: [0, 2] },
        { type: 'date-ddmmyyyy', targets: 1 }
      ]
    });
  }


  function updateCumulativeSum(tableId) {
    const table = $(`#${tableId}`).DataTable();
    const rows = table.rows({ order: 'applied' }).nodes();
    let cumulative = 0;

    rows.each(function(row) {
      const amtCell = $(row).find('td[data-field="AMT"]');
      const cumulativeCell = $(row).find('td.cumulative-amt');
      if (amtCell.length && cumulativeCell.length) {
        const amt = parseFloat(amtCell.text().replace(/[^0-9.-]+/g,"")) || 0;
        cumulative += amt;
        cumulativeCell.attr('data-money', cumulative.toFixed(2)).text(cumulative.toFixed(2));
      }
    });

    applyGlobalMoneyFormatting();  // <- This applies ₹ symbol and commas
  }



  // Initial call after table is ready
  updateCumulativeSum('paymentTable');
  updateCumulativeSum('postingTable');

  // Recalculate after sorting
  $('#paymentTable').on('order.dt', function() {
    updateCumulativeSum('paymentTable');
    applyGlobalMoneyFormatting();
  });
  $('#postingTable').on('order.dt', function() {
    updateCumulativeSum('postingTable');
    applyGlobalMoneyFormatting(); 
  });

applyGlobalMoneyFormatting();

});

document.addEventListener('DOMContentLoaded', () => {
  const q = document.getElementById('searchQuery');
  if (!q) return;
  // If you only want to do this when the input already has a value:
  // if (!q.value) return;

  // Focus and place caret at the end
  const len = q.value.length;
  q.focus();
  try { q.setSelectionRange(len, len); } catch (e) { /* Safari fallback below */ }

  // Safari fallback: defer once to ensure selection sticks
  setTimeout(() => {
    const l = q.value.length;
    try { q.setSelectionRange(l, l); } catch {}
  }, 0);
});