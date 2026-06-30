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
  const formatDateToDDMMYYYY = window.formatDate;
  // --- Element Selectors ---
  let activeReplaceMode = null;

  function openBulkDateReplace(mode) {
      activeReplaceMode = mode;
      document.getElementById("dateReplaceModal").style.display = "block";
  }
  window.openBulkDateReplace = openBulkDateReplace;
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
  const closeAccountBtn = document.getElementById("closeAccountBtn");

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

  function parseDisplayDate(dateStr) {
  if (!dateStr) return null;

  // yyyy-mm-dd
  if (/^\d{4}-\d{2}-\d{2}$/.test(dateStr)) {
    return new Date(dateStr);
  }

  // dd-mm-yyyy
  if (/^\d{2}-\d{2}-\d{4}$/.test(dateStr)) {
    const [d, m, y] = dateStr.split("-");
    return new Date(`${y}-${m}-${d}`);
  }

  // dd/mm/yyyy
  if (/^\d{2}\/\d{2}\/\d{4}$/.test(dateStr)) {
    const [d, m, y] = dateStr.split("/");
    return new Date(`${y}-${m}-${d}`);
  }

  return null;
}

const formatDateForDisplay = window.formatDate;

function recalculateCustomerLoanFields(row) {
  const startDateCell = row.querySelector("td[data-field='start_date']");
  const endDateCell = row.querySelector("td[data-field='end_date']");
  const typeCell = row.querySelector("td[data-field='type']");
  const periodCell = row.querySelector("td[data-field='period']");
  const totalAmountCell = row.querySelector("td[data-field='total_amount']");
  const installmentCell = row.querySelector("td[data-field='installment_amount']");
  const paidAmountCell = row.querySelector("td[data-field='paid_amount']");
  const balanceAmountCell = row.querySelector("td[data-field='balance_amount']");

  if (
    !startDateCell ||
    !endDateCell ||
    !typeCell ||
    !periodCell ||
    !totalAmountCell ||
    !installmentCell
  ) {
    return;
  }

  const type = typeCell.textContent.trim().toUpperCase();
  const period = parseInt(periodCell.textContent.trim(), 10);

  const totalAmount = parseFloat(
    totalAmountCell.textContent.replace(/[^0-9.-]/g, "")
  ) || 0;

  // Installment calculation
  if (!isNaN(period) && period > 0) {
    installmentCell.textContent = (totalAmount / period).toFixed(2);
  }

  // Balance recalculation
  if (paidAmountCell && balanceAmountCell) {
    const paidAmount = parseFloat(
      paidAmountCell.textContent.replace(/[^0-9.-]/g, "")
    ) || 0;

    balanceAmountCell.textContent = (totalAmount - paidAmount).toFixed(2);
  }

  // End date calculation
  const startDate = parseDisplayDate(startDateCell.textContent.trim());

  if (!startDate || isNaN(period)) return;

  const endDate = new Date(startDate);

  if (type === "W") {
    endDate.setDate(endDate.getDate() + (period * 7));
  } else if (type === "M") {
    endDate.setMonth(endDate.getMonth() + period);
  } else {
    return;
  }

  endDateCell.textContent = formatDateForDisplay(endDate);
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

        // Store original value for rollback
        td.dataset.originalValue = td.textContent.trim();

        const editableFields = [
          "name",
          "total_amount",
          "start_date",
          "type",
          "period",
          "pano",
          "notes",
          "phone_number"
        ];

        if (editableFields.includes(td.dataset.field)) {
          td.setAttribute("contenteditable", "true");
          td.classList.add("highlighted");
        }
      });
      editCustomerBtn.style.display = "none";
      saveCustomerBtn.style.display = "inline-block";
    });

    // Restrict invalid customer names during edit
    customerRow.addEventListener("input", (e) => {
      const td = e.target;

      if (!td.dataset.field) return;

      // Name validation
      if (td.dataset.field === "name") {
        // Do not rewrite text while typing.
        // Validation already happens when Save is clicked.
      }

      // Amount validation
      if (td.dataset.field === "total_amount") {
        td.textContent = td.textContent.replace(/[^0-9.]/g, "");
      }

      // Period validation
      if (td.dataset.field === "period") {
        td.textContent = td.textContent.replace(/[^0-9]/g, "");
      }

      // Phone validation
      if (td.dataset.field === "phone_number") {
        td.textContent = td.textContent.replace(/[^0-9]/g, "").slice(0, 10);
      }

      // Type validation
      if (td.dataset.field === "type") {
          let value = td.textContent.toUpperCase().replace(/[^WM]/g, "");

        if (value.length > 1) {
          value = value[0];
        }

        td.textContent = value;
      }

      // Recalculate loan fields instantly
      if (
        [
          "start_date",
          "type",
          "period",
          "total_amount"
        ].includes(td.dataset.field)
      ) {
        recalculateCustomerLoanFields(customerRow);
      }
    });

    saveCustomerBtn.addEventListener("click", () => {
      const updatedData = {
         cid: customerRow.dataset.cid
      };

      const nameCell = customerRow.querySelector("td[data-field='name']");
      const customerName = (nameCell?.textContent || "").trim();

      // Remove spaces to calculate actual letters
      const lettersOnly = customerName.replace(/\s/g, "");

      // Must contain only alphabets and spaces
      const validNamePattern = /^[A-Za-z ]+$/;

      if (
        !customerName ||
        !validNamePattern.test(customerName) ||
        lettersOnly.length < 3
      ) {

        // Restore original value
        if (nameCell) {
          nameCell.textContent = nameCell.dataset.originalValue || "";
          nameCell.setAttribute("contenteditable", "false");
          nameCell.classList.remove("highlighted");
        }

        saveCustomerBtn.style.display = "none";
        editCustomerBtn.style.display = "inline-block";

        alert("Customer name must contain at least 3 letters and cannot contain numbers or special characters");
        return;
      }

      customerRow.querySelectorAll("td[data-field]").forEach(td => {
          updatedData[td.dataset.field] = td.textContent.trim();
      });

      csrfFetch("/api/customer/update_pg", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ type: "customer", data: updatedData })
      })
      .then((res) => res.json())
      .then((data) => {
        if (data.success) {
          customerRow.querySelectorAll("td").forEach((td) => {
            td.setAttribute("contenteditable", "false");
            td.classList.remove("highlighted");
          });
          saveCustomerBtn.style.display = "none";
          editCustomerBtn.style.display = "inline-block";
        } else {

          // Restore original values on failed save
          customerRow.querySelectorAll("td[data-field]").forEach((td) => {
            td.textContent = td.dataset.originalValue || td.textContent;
            td.setAttribute("contenteditable", "false");
            td.classList.remove("highlighted");
          });

          saveCustomerBtn.style.display = "none";
          editCustomerBtn.style.display = "inline-block";

          alert("Update failed: " + data.error);
        }
      })
      .catch((err) => {

        // Restore original values on request failure
        customerRow.querySelectorAll("td[data-field]").forEach((td) => {
          td.textContent = td.dataset.originalValue || td.textContent;
          td.setAttribute("contenteditable", "false");
          td.classList.remove("highlighted");
        });

        saveCustomerBtn.style.display = "none";
        editCustomerBtn.style.display = "inline-block";

        alert("Error: " + err.message);
      });
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

    savePaymentsBtn.addEventListener("click", async () => {
  const rows = document.querySelectorAll("#paymentTable tbody tr");

  for (const row of rows) {
    const ano = row.dataset.ano;
    const oldPdt = row.dataset.pdt;              // already YYYY-MM-DD
    const newPdt = row.querySelector("td[data-field='PDT']").textContent.trim();   // user edited YYYY-MM-DD
    const amtCell = row.querySelector("td[data-field='AMT']");
    if (!amtCell) continue;

    const amt = parseFloat(amtCell.textContent.replace(/[^\d.-]/g, "")) || 0;

    const payload = {
      data: {
        ano: ano,
        old_pdt: oldPdt,
        pdt: newPdt,   // use new date value from user input
        amt: amt
      }
    };

    const res = await csrfFetch("/api/payment/update_pg", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload)
    });

    const result = await res.json();
    if (!result.success) {
      alert("Payment update failed: " + result.error);
      return;
    }
  }

  // UI reset
  document.querySelectorAll("td[data-field='AMT']").forEach(td =>
    td.setAttribute("contenteditable", "false")
  );

  savePaymentsBtn.style.display = "none";
  editPaymentsBtn.style.display = "inline-block";

  alert("Payments updated successfully");
});
  }

  // --- Logic for: Close Customer Account ---
  // Disable/enable Close Account button based on status; enable "Retrieve" for closed/defaulted/written_off
  if (closeAccountBtn && customerRow) {
    const statusCell = customerRow.querySelector("td[data-field='status']");
    if (statusCell) {
      const status = statusCell.textContent.trim().toLowerCase();

      if (["closed", "defaulted", "written_off", "written off"].includes(status)) {
        closeAccountBtn.disabled = false;
        closeAccountBtn.textContent = "♻️ Retrieve";
        closeAccountBtn.classList.add("retrieve-btn");
      }
    }
  }
  if (closeAccountBtn && customerRow) {
    closeAccountBtn.addEventListener("click", async () => {
      const statusCell = customerRow.querySelector("td[data-field='status']");
      const currentStatus = statusCell ? statusCell.textContent.trim().toLowerCase() : "";

      if (["closed", "defaulted", "written_off", "written off"].includes(currentStatus)) {
        // 🔥 RETRIEVE FLOW
        try {
          closeAccountBtn.disabled = true;
          const originalText = closeAccountBtn.textContent;
          closeAccountBtn.textContent = "⏳ Retrieving...";

          const res = await csrfFetch("/api/customer/retrieve_account_pg", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ cid: customerRow.dataset.cid })
          });

          const data = await res.json();

          if (data.success) {
            alert("Customer retrieved successfully");

            // ✅ Update status cell immediately
            const statusCell = customerRow.querySelector("td[data-field='status']");
            if (statusCell) {
              statusCell.textContent = "active";
            }

            // ✅ Update button back to Close Account
            closeAccountBtn.disabled = false;
            closeAccountBtn.textContent = "🔒 Close Account";
            closeAccountBtn.classList.remove("retrieve-btn");
          } else {
            alert("Error: " + data.error);
            closeAccountBtn.disabled = false;
            closeAccountBtn.textContent = originalText;
          }
        } catch (err) {
          alert("Request failed: " + err.message);
          closeAccountBtn.disabled = false;
          closeAccountBtn.textContent = originalText;
        }

        return;
      }
      const cid = customerRow.dataset.cid;

      const balanceCell = customerRow.querySelector("td[data-field='balance_amount']");
      if (!balanceCell) {
        alert("Balance not found");
        return;
      }

      const balance = parseFloat(balanceCell.textContent.replace(/[^0-9.-]/g, "")) || 0;

      let action = null;

      if (balance > 0) {
        const confirmDefault = confirm("Balance > 0. Mark as DEFAULTED?");
        if (!confirmDefault) return;
        action = "defaulted";
      } else if (balance < 0) {
        const confirmWriteOff = confirm("Balance < 0. Mark as WRITTEN OFF?");
        if (!confirmWriteOff) return;
        action = "written_off";
      }

      try {
        closeAccountBtn.disabled = true;
        const originalText = closeAccountBtn.textContent;
        closeAccountBtn.textContent = "⏳ Processing...";

        const res = await csrfFetch("/api/customer/close_account_pg", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ cid, action })
        });

        const data = await res.json();

        if (data.success) {
          closeAccountBtn.textContent = "✅ Closed";
          alert("Account closed successfully: " + data.status);
          location.reload();
        } else {
          alert("Error: " + data.error);
          closeAccountBtn.disabled = false;
          closeAccountBtn.textContent = originalText;
        }
      } catch (err) {
        alert("Request failed: " + err.message);
        closeAccountBtn.disabled = false;
        closeAccountBtn.textContent = originalText;
      }
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
              const ano = row.cells[0].textContent.trim();
              const newPdt = toISO(pdtCell.textContent.trim());
              const newAmt = parseFloat(amtCell.textContent.replace(/[^\d.-]/g, '')) || 0;

              csrfFetch("/api/payment/update_pg", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                  data: {
                    ano: row.dataset.ano,
                    old_pdt: row.dataset.pdt,
                    pdt: newPdt,
                    amt: newAmt
                  }
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
                  pdtCell.textContent = formatDateToDDMMYYYY(newPdt);
                  updatePostingTableTotals();
                  updateCumulativeSum('postingTable');
                  applyGlobalMoneyFormatting();
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

          csrfFetch("/search_postings", {
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
                      tr.dataset.ano = row.ANO;
                      tr.dataset.pdt = toISO(row.PDT);
                      const formattedPdt = row.PDT
                          ? row.PDT.split("-").reverse().join("-")
                          : "";
                      tr.innerHTML = `
                          <td>${row.ANO}</td>
                          <td data-field="PDT" contenteditable="false" data-order="${row.PDT}">${formattedPdt}</td>
                          <td data-field="AMT" contenteditable="false" data-money data-order="${row.AMT}">${row.AMT}</td>
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
                      { type: "num", targets: [0, 2] }
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
              const amt = parseFloat((amtCell?.textContent || "0").replace(/[^\d.-]/g, '')) || 0;
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
      $('#paymentTable tbody tr').removeClass('highlighted-row').removeAttr('data-selected');

      // Add highlight & a 'selected' marker to the clicked row
      $(this).addClass('highlighted-row').attr('data-selected', 'true');
      window.currentRow = this; // Update global highlighted row for keyboard navigation!
  });

  // Reapply highlight after sorting
  $('#paymentTable').on('order.dt', function() {
      $('#paymentTable tbody tr').removeClass('highlighted-row');
      $('#paymentTable tbody tr[data-selected="true"]').addClass('highlighted-row');
  });


  // --- Logic for: Toggle between Customer and Posting sections ---
  if (customerForm) {
    customerForm.addEventListener("submit", () => {
      document.getElementById("customer-section").style.display = "block";
      if (postingSection) postingSection.style.display = "none";
    });
  }
  

  // Fix for Payments: Ensure correct button opens modal
  const bulkDateChangeBtnPayments = document.getElementById("bulkDateChangeBtnPayments");
  if (bulkDateChangeBtnPayments) {
      bulkDateChangeBtnPayments.addEventListener("click", () => {
          openBulkDateReplace("payments");
      });
  }

  // Fix for Posting table bulk editing
  const bulkDateChangeBtnPosting = document.getElementById("bulkDateChangeBtnPosting");
  if (bulkDateChangeBtnPosting) {
      bulkDateChangeBtnPosting.addEventListener("click", () => {
          openBulkDateReplace("posting");
      });
  }


  // --- Helper Functions (defined on window to be accessible from HTML) ---
  window.deletePaymentFromElement = (el) => {
    const row = el.closest("tr");
    const ano = row.dataset.ano;
    const pdt = row.dataset.pdt;
    csrfFetch("/delete_payment", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ ano, pdt })
    })
    .then(res => res.json())
    .then(data => {
      if (data.success) {
        row.remove();
        updateTotalsAndLoanee();
        updateCumulativeSum('paymentTable');
      } else {
        alert("Failed to delete: " + data.error);
      }

      // Clear any highlights left (no selection)
      $('#paymentTable tbody tr').removeClass('highlighted').removeAttr('data-selected');   

    })
    .catch(err => alert("Delete error: " + err.message));
  };
  
  window.deletePaymentFromPostingRow = (el, ano, pdt) => {
    csrfFetch("/delete_payment", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        ano,
        pdt: toISO(pdt)
      })
    })
    .then(res => res.json())
    .then(data => {
      if (data.success) {
        const dt = $.fn.DataTable.isDataTable('#postingTable')
          ? $('#postingTable').DataTable()
          : null;

        const rowEl = el.closest("tr");

        if (dt) {
          dt.row(rowEl).remove().draw(false);
        } else {
          rowEl.remove();
        }

        updatePostingTableTotals();
        updateCumulativeSum('postingTable');
        applyGlobalMoneyFormatting();

      } else {
        alert("Delete failed: " + data.error);
      }
    });
  };

window.addPaymentFromForm = addPaymentFromForm;
async function addPaymentFromForm(form) {
    const ano = form.dataset.ano;
    const pdt = document.getElementById("newPDT").value.trim();
    const amt = document.getElementById("newAMT").value.trim();

    if (!pdt || !amt) {
        alert("Please enter both date and amount.");
        return false;
    }

    let payload = {
        ano: ano,
        pdt: pdt,
        amt: amt
    };
    
    try {
        const res = await csrfFetch("/add_payment", {
            method: "POST",
            headers: { "Content-Type": "application/json", "Accept": "application/json"},
            body: JSON.stringify(payload)
        });

        const data = await res.json();

        if (!data.success) {
            alert("Error: " + data.error);
            return false;
        }

        // ---------- INSERT NEW ROW INTO PAYMENT TABLE (using DataTables API) ----------
        const dt = $('#paymentTable').DataTable();
        const newRowHtml = `
<tr data-ano="${ano}" data-pdt="${pdt}">
    <td data-field="ANO" contenteditable="false">${ano}</td>
    <td data-field="PDT" contenteditable="false" data-order="${formatDateToISO(pdt)}">${formatDateToDDMMYYYY(pdt)}</td>
    <td data-field="AMT" data-money="${amt}" data-order="${amt}" contenteditable="false">${amt}</td>
    <td class="cumulative-amt" data-money="0"></td>
    <td>
        <span class="delete-btn" onclick="deletePaymentFromElement(this)">🗑️</span>
    </td>
</tr>`;

        // ---------- FIX NEW ROW STRUCTURE ----------
        dt.row.add($(newRowHtml)).draw(false);

       
        // Recalculate cumulative + totals + customer summary
        // Recalculate cumulative column FIRST
        recalculatePayments();

        // Recalculate DataTables-based cumulative (double safety)
        updateCumulativeSum('paymentTable');

        // Update top summary PAMT/BAMT
        updateTotalsAndLoanee();
        updateCustomerSummary();

        // Apply formatting last
        applyGlobalMoneyFormatting();

        // Clear form fields
        document.getElementById("newPDT").value = "";
        document.getElementById("newAMT").value = "";
    } catch (err) {
        alert("Error: " + err);
    }

    return false;
}

// =========================
// RECALCULATE PAYMENT TABLE
// =========================
function recalculatePayments() {
    let rows = document.querySelectorAll("#paymentTable tbody tr");
    let cumulative = 0;

    rows.forEach(row => {
        // Safely get AMT cell — if missing skip this row
        let amtCell = row.querySelector("[data-field='AMT']");
        if (!amtCell) return;

        // Normalize text then parse number
        let amtText = (amtCell.innerText || amtCell.textContent || "").replace(/[,₹\s]/g, "").replace(/[^0-9.-]/g, "");
        let amt = parseFloat(amtText) || 0;

        cumulative += amt;

        let cumCell = row.querySelector(".cumulative-amt");
        if (cumCell) {
            // keep machine value in data-money and show formatted text
            cumCell.setAttribute("data-money", cumulative.toFixed(2));
            cumCell.innerText = "₹" + cumulative.toLocaleString();
        }
    });

    // Footer totals
    const anoCountEl = document.getElementById("anoCount");
    if (anoCountEl) anoCountEl.innerText = rows.length;

    let totalAmt = Array.from(rows).reduce((sum, r) => {
        const c = r.querySelector("[data-field='AMT']");
        if (!c) return sum;
        const v = (c.innerText || c.textContent || "").replace(/[,₹\s]/g, "").replace(/[^0-9.-]/g, "");
        return sum + (parseFloat(v) || 0);
    }, 0);

    const totalElem = document.getElementById("totalAmt");
    if (totalElem) {
        totalElem.setAttribute("data-money", totalAmt.toFixed(2));
        totalElem.innerText = "₹" + totalAmt.toLocaleString();
    }

    applyGlobalMoneyFormatting();
}


// ===============================
// UPDATE CUSTOMER SUMMARY (PAMT/BAMT)
// ===============================
function updateCustomerSummary() {
    const customerRow = document.querySelector("#customerTable tbody tr");
    if (!customerRow) return;

    const amtCellCust = customerRow.querySelector("td[data-field='total_amount']");
    const amt = parseFloat((amtCellCust?.textContent || "").replace(/[^0-9.-]/g, "")) || 0;

    const paymentRows = document.querySelectorAll("#paymentTable tbody tr");

    let totalPaid = 0;
    paymentRows.forEach(row => {
        const cell = row.querySelector("[data-field='AMT']");
        if (!cell) return;
        let a = parseFloat((cell.textContent || cell.innerText || "").replace(/[^0-9.-]/g, "")) || 0;
        totalPaid += a;
    });

    let pamtCell = customerRow.querySelector("td[data-field='paid_amount']");
    let bamtCell = customerRow.querySelector("td[data-field='balance_amount']");
    let discountCell = customerRow.querySelector("td[data-field='interest_discount']");
    let interestDiscount = discountCell ? (parseFloat(discountCell.textContent.replace(/[^0-9.-]/g, "")) || 0) : 0;

    if (pamtCell) pamtCell.innerText = totalPaid.toLocaleString();
    if (bamtCell) bamtCell.innerText = (amt - totalPaid - interestDiscount).toLocaleString();
}

  
  window.submitDateReplace = () => {
      const oldDate = document.getElementById("findDateInput").value.trim();
      const newDate = document.getElementById("replaceDateInput").value.trim();

      if (!oldDate || !newDate) {
          alert("Please enter both dates.");
          return;
      }

      if (activeReplaceMode === "payments") {
          replacePaymentDates(oldDate, newDate);
      } else if (activeReplaceMode === "posting") {
          replacePostingDates(oldDate, newDate);
      }

      document.getElementById("dateReplaceModal").style.display = "none";
  };

  function replacePaymentDates(oldDate, newDate) {
    csrfFetch("/update_payment_date_bulk", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
            find_date: oldDate,
            replace_date: newDate
        })
    })
    .then(res => res.json())
    .then(data => {
        if (data.success) {
            alert("Payment dates updated successfully");
            location.reload();
        } else {
            alert("Error: " + data.error);
        }
    });
}

  function replacePostingDates(oldDate, newDate) {
      csrfFetch("/update_payment_date_bulk", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ find_date: oldDate, replace_date: newDate })
      })
      .then(res => res.json())
      .then(data => {
          const msgBox = document.getElementById("postingMessageBox");
          msgBox.style.display = "block";
          msgBox.className = "message-box " + (data.success ? "success" : "error");
          msgBox.textContent = data.message || data.error;

          if (data.success) {
              if (postingForm) postingForm.dispatchEvent(new Event("submit"));
          }
      });
  }

  function updateTotalsAndLoanee() {
    if (!paymentTable) return;
    const rows = paymentTable.querySelectorAll("tbody tr");
    let totalAmt = 0;
    rows.forEach(row => {
        const amtCell = row.querySelector("td[data-field='AMT']");
        if (!amtCell) {
            // Skip rows that do not contain an AMT cell (prevents null errors)
            return;
        }

        let cleanedText = amtCell.textContent.trim().replace(/[^\d.-]/g, '');
        let amt = parseFloat(cleanedText);
        if (isNaN(amt)) amt = 0;

        if (!isNaN(amt)) totalAmt += amt;
    });
    document.getElementById("totalAmt").textContent = totalAmt.toFixed(2);
    document.getElementById("anoCount").textContent = rows.length;
    applyGlobalMoneyFormatting();
    if (customerRow) {
      const amtCell = customerRow.querySelector("td[data-field='total_amount']");
      const pamtCell = customerRow.querySelector("td[data-field='paid_amount']");
      const bamtCell = customerRow.querySelector("td[data-field='balance_amount']");
      const discountCell = customerRow.querySelector("td[data-field='interest_discount']");
      const interestDiscount = discountCell ? (parseFloat(discountCell.textContent.replace(/[^0-9.-]/g, "")) || 0) : 0;
      const amt = parseFloat(amtCell?.textContent.trim()) || 0;
      if (pamtCell && bamtCell) {
        pamtCell.textContent = totalAmt.toFixed(2);
        bamtCell.textContent = (amt - totalAmt - interestDiscount).toFixed(2);
      }
    }
  }

  // --- Auto-calculation Functions ---
  function recalculateBAMT(row) {
    const amtCell = row.querySelector('td[data-field="total_amount"]');
    const pamtCell = row.querySelector('td[data-field="paid_amount"]');
    const bamtCell = row.querySelector('td[data-field="balance_amount"]');
    const discountCell = row.querySelector('td[data-field="interest_discount"]');
    const interestDiscount = discountCell ? (parseFloat(discountCell.textContent.replace(/[^0-9.-]/g, "")) || 0) : 0;
    const amt = parseFloat(amtCell.textContent.trim());
    const pamt = parseFloat(pamtCell.textContent.trim());
    if (!isNaN(amt) && !isNaN(pamt)) {
      bamtCell.textContent = (amt - pamt - interestDiscount).toFixed(2);
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
      ["total_amount"].forEach((field) => {
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
         { type: 'num', targets: [0, 2] }
       ]
     });
   }


function updateCumulativeSum(tableId) {
    let dt;
    try {
        dt = $(`#${tableId}`).DataTable();
    } catch (e) {
        console.warn("Table not initialized:", tableId);
        return;
    }

    const rows = dt.rows({ order: "applied" }).nodes(); 
    let cumulative = 0;

    rows.each(function (row) {
        if (!row || row.classList.contains("dataTables_empty")) return;

        const amtCell = row.querySelector("td[data-field='AMT']");
        const cumCell = row.querySelector("td.cumulative-amt");
        if (!amtCell || !cumCell) return;

        const raw = amtCell.textContent.replace(/[^0-9.-]/g, "");
        const amt = parseFloat(raw) || 0;
        cumulative += amt;

        cumCell.setAttribute("data-money", cumulative.toFixed(2));
        cumCell.textContent = "₹" + cumulative.toLocaleString();
    });

    applyGlobalMoneyFormatting();
}

function toISO(dateStr) {
  if (!dateStr) return "";

  // Already ISO format
  if (/^\d{4}-\d{2}-\d{2}$/.test(dateStr)) {
    return dateStr;
  }

  // Convert dd/mm/yyyy -> yyyy-mm-dd
  if (/^\d{2}\/\d{2}\/\d{4}$/.test(dateStr)) {
    const [d, m, y] = dateStr.split("/");
    return `${y}-${m}-${d}`;
  }

  return dateStr;
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

// Format existing PDT values in already-rendered payment table
const existingPaymentDateCells = document.querySelectorAll('#paymentTable td[data-field="PDT"]');

existingPaymentDateCells.forEach((cell) => {
  cell.textContent = formatDateToDDMMYYYY(cell.textContent.trim());
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