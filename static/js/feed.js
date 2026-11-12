// Global set of in-flight feed actions to prevent duplicate concurrent submissions
const _inFlightFeedActions = new Set();

function handleFeedAction(url, successMessage, failureFallback, body = null, triggerBtn = null) {
  if (_inFlightFeedActions.has(url)) {
    console.warn("Feed action already processing:", url);
    return Promise.resolve({ success: false, error: "Action already processing" });
  }

  // Identify triggering button (passed explicitly or inferred from active event)
  let btn = triggerBtn;
  if (!btn && typeof window !== "undefined" && window.event && window.event.target) {
    btn = window.event.target.closest("button") || window.event.target;
  }

  _inFlightFeedActions.add(url);

  let originalHtml = "";
  let siblingButtons = [];

  if (btn && btn.tagName === "BUTTON") {
    originalHtml = btn.innerHTML;
    btn.disabled = true;
    btn.style.pointerEvents = "none";
    btn.classList.add("btn-loading");
    btn.innerHTML = `<i class="fas fa-spinner fa-spin me-1"></i> Processing...`;

    // Also disable nearby sibling action buttons in the same action group (e.g., Accept vs Delete)
    const container = btn.closest(".cust-topbar-actions, .feed-card-actions, .pay-row-actions, td, .posting-actions");
    if (container) {
      siblingButtons = Array.from(container.querySelectorAll("button:not([disabled])"));
      siblingButtons.forEach(b => {
        if (b !== btn) {
          b.disabled = true;
          b.style.pointerEvents = "none";
        }
      });
    }
  }

  const options = {
    method: "POST"
  };
  if (body) {
    options.headers = { "Content-Type": "application/json" };
    options.body = JSON.stringify(body);
  }

  return csrfFetch(url, options)
    .then(res => res.json())
    .then(data => {
      if (data.success) {
        if (typeof window.showSuccessToast === "function") {
          window.showSuccessToast(successMessage);
          setTimeout(() => location.reload(), 600);
        } else {
          alert(successMessage);
          location.reload();
        }
      } else {
        const errTxt = data.error || failureFallback;
        if (typeof window.showErrorToast === "function") {
          window.showErrorToast(errTxt);
        } else {
          alert(errTxt);
        }
        if (btn) {
          btn.disabled = false;
          btn.style.pointerEvents = "";
          btn.classList.remove("btn-loading");
          btn.innerHTML = originalHtml;
        }
        siblingButtons.forEach(b => {
          b.disabled = false;
          b.style.pointerEvents = "";
        });
      }
      return data;
    })
    .catch(err => {
      console.error(err);
      if (typeof window.showErrorToast === "function") {
        window.showErrorToast("Server error: " + (err.message || "Unknown"));
      } else {
        alert("Server error");
      }
      if (btn) {
        btn.disabled = false;
        btn.style.pointerEvents = "";
        btn.classList.remove("btn-loading");
        btn.innerHTML = originalHtml;
      }
      siblingButtons.forEach(b => {
        b.disabled = false;
        b.style.pointerEvents = "";
      });
      return { success: false, error: "Server error" };
    })
    .finally(() => {
      _inFlightFeedActions.delete(url);
    });
}

function accept(feed_id, btn = null) {
  if (!btn && typeof window !== "undefined" && window.event && window.event.target) {
    btn = window.event.target.closest("button") || window.event.target;
  }

  const dupeDataEl = document.getElementById(`cust-dupe-data-${feed_id}`);
  let dupes = [];
  if (dupeDataEl) {
    try {
      dupes = JSON.parse(dupeDataEl.textContent || '[]');
    } catch (e) {}
  }

  if (dupes && dupes.length > 0) {
    const proceed = confirm(`⚠️ DUPLICATE AADHAAR WARNING:\n\nThis customer has ${dupes.length} existing account(s) registered under the same Aadhaar card across villages.\n\n• Click OK to confirm and accept this customer into records.\n• Click Cancel to review the duplicate accounts.`);
    if (!proceed) {
      openAadhaarModalFromData(feed_id);
      return false;
    }
  }

  return handleFeedAction(
    `/feed/customer/accept/${feed_id}`,
    "Customer accepted successfully",
    "Failed to accept customer",
    null,
    btn
  );
}

function acceptPayment(feed_payment_id, btn = null) {
  if (!btn && typeof window !== "undefined" && window.event && window.event.target) {
    btn = window.event.target.closest("button") || window.event.target;
  }
  return handleFeedAction(
    `/feed/payment/accept/${feed_payment_id}`,
    "Payment accepted",
    "Failed to accept payment",
    null,
    btn
  );
}

function acceptDocs(feed_id, btn = null) {
  if (!btn && typeof window !== "undefined" && window.event && window.event.target) {
    btn = window.event.target.closest("button") || window.event.target;
  }
  return handleFeedAction(
    `/feed/docs/accept/${feed_id}`,
    "Customer documents accepted",
    "Failed to accept customer documents",
    null,
    btn
  );
}

function acceptExistingDocs(docs_feed_id, btn = null) {
  if (!btn && typeof window !== "undefined" && window.event && window.event.target) {
    btn = window.event.target.closest("button") || window.event.target;
  }
  return handleFeedAction(
    `/feed/existing-docs/accept/${docs_feed_id}`,
    "Documents accepted into customer records",
    "Failed to accept documents",
    null,
    btn
  );
}

function openEditModal(modalId) {
  const modal = document.getElementById(modalId);
  if (modal) {
    modal.style.display = "flex";
  }
}

function closeEditModal(modalId) {
  const modal = document.getElementById(modalId);
  if (modal) {
    modal.style.display = "none";
  }
}

/* Edit Customer Feed */
function editCustomer(feed_id) {
  const scriptTag = document.getElementById(`cust-data-${feed_id}`);
  if (!scriptTag) {
    alert("Customer data not found");
    return;
  }
  let data = {};
  try {
    data = JSON.parse(scriptTag.textContent || "{}");
  } catch (e) {
    console.error("Failed to parse customer JSON:", e);
  }

  document.getElementById("edit_cust_feed_id").value = feed_id;
  document.getElementById("edit_cust_name").value = data.name || "";
  document.getElementById("edit_cust_ano").value = data.ano || "";
  document.getElementById("edit_cust_vid").value = data.vid || "";
  document.getElementById("edit_cust_pano").value = data.pano || "";
  document.getElementById("edit_cust_total_amount").value = data.total_amount || "";
  document.getElementById("edit_cust_installment_amount").value = data.installment_amount || "";
  document.getElementById("edit_cust_type").value = data.type || "weekly";
  document.getElementById("edit_cust_period").value = data.period || "";
  document.getElementById("edit_cust_start_date").value = data.start_date || "";
  document.getElementById("edit_cust_end_date").value = data.end_date || "";
  document.getElementById("edit_cust_aadhaar_number").value = data.aadhaar_number || "";
  document.getElementById("edit_cust_phone_number").value = data.phone_number || "";
  document.getElementById("edit_cust_notes").value = data.notes || "";

  openEditModal("editCustomerModal");
}

function saveCustomerEdit(e) {
  e.preventDefault();
  const feed_id = document.getElementById("edit_cust_feed_id").value;
  const payload = {
    name: document.getElementById("edit_cust_name").value.trim(),
    ano: document.getElementById("edit_cust_ano").value.trim(),
    vid: document.getElementById("edit_cust_vid").value.trim(),
    pano: document.getElementById("edit_cust_pano").value.trim(),
    total_amount: document.getElementById("edit_cust_total_amount").value.trim(),
    installment_amount: document.getElementById("edit_cust_installment_amount").value.trim(),
    type: document.getElementById("edit_cust_type").value,
    period: document.getElementById("edit_cust_period").value.trim(),
    start_date: document.getElementById("edit_cust_start_date").value,
    end_date: document.getElementById("edit_cust_end_date").value,
    aadhaar_number: document.getElementById("edit_cust_aadhaar_number").value.trim(),
    phone_number: document.getElementById("edit_cust_phone_number").value.trim(),
    notes: document.getElementById("edit_cust_notes").value.trim()
  };

  handleFeedAction(
    `/feed/customer/edit/${feed_id}`,
    "Customer feed item updated successfully",
    "Failed to update customer feed item",
    payload
  );
  closeEditModal("editCustomerModal");
}

/* ----------------------------------------------------
   Inline Customer Feed Auto-Save & Highlight Sync
---------------------------------------------------- */
let custInlineTimerMap = {};

function onInlineCustomerEdit(feed_id, fieldName, fieldValue) {
  const tile = document.getElementById(`cust-tile-${feed_id}`);
  if (!tile) return;

  if (fieldName === "name") {
    document.querySelectorAll(`.hl-display-name-${feed_id}, #hl-name-${feed_id}`).forEach(el => {
      el.innerText = fieldValue || (el.tagName === 'SPAN' ? '-' : 'Unnamed Customer');
    });
  } else if (fieldName === "ano") {
    document.querySelectorAll(`.hl-display-ano-${feed_id}`).forEach(el => {
      el.innerText = fieldValue ? `#${fieldValue}` : '—';
    });
  } else if (fieldName === "vid") {
    const vName = (window.villageMap && window.villageMap[fieldValue]) ? window.villageMap[fieldValue] : (`Village ${fieldValue}`);
    document.querySelectorAll(`.hl-display-village-${feed_id}`).forEach(el => {
      el.innerText = vName;
    });
    const hlAddressDoc = document.getElementById(`hl-address-${feed_id}`);
    if (hlAddressDoc && (!hlAddressDoc.innerText || hlAddressDoc.innerText.startsWith('Village'))) {
      hlAddressDoc.innerText = vName;
    }
  } else if (fieldName === "aadhaar_number") {
    const hlAadhaarDoc = document.getElementById(`hl-aadhaar-${feed_id}`);
    if (hlAadhaarDoc) hlAadhaarDoc.innerText = fieldValue || "-";

    // Debounced dynamic Aadhaar duplicate re-check
    const cleanAadhaar = (fieldValue || "").replace(/[^0-9]/g, "");
    const dupeDataEl = document.getElementById(`cust-dupe-data-${feed_id}`);
    const warnBanner = document.getElementById(`cust-aadhaar-warn-${feed_id}`);
    const countEl = document.getElementById(`cust-dupe-count-${feed_id}`);
    const tileBadge = document.getElementById(`cust-tile-dupe-badge-${feed_id}`);

    if (cleanAadhaar.length === 12) {
      fetch(`/api/customer/check_aadhaar?aadhaar=${cleanAadhaar}`)
        .then(r => r.json())
        .then(data => {
          if (data.duplicate && data.accounts && data.accounts.length > 0) {
            if (dupeDataEl) dupeDataEl.textContent = JSON.stringify(data.accounts);
            if (countEl) countEl.textContent = data.accounts.length;
            if (warnBanner) warnBanner.style.display = 'block';
            if (tileBadge) {
              tileBadge.innerHTML = `<i class="fas fa-exclamation-triangle"></i> Dupe (${data.accounts.length})`;
              tileBadge.style.display = 'inline-flex';
            }
          } else {
            if (dupeDataEl) dupeDataEl.textContent = '[]';
            if (warnBanner) warnBanner.style.display = 'none';
            if (tileBadge) tileBadge.style.display = 'none';
          }
        })
        .catch(err => console.error("Error re-checking Aadhaar:", err));
    } else {
      if (dupeDataEl) dupeDataEl.textContent = '[]';
      if (warnBanner) warnBanner.style.display = 'none';
      if (tileBadge) tileBadge.style.display = 'none';
    }
  } else if (fieldName === "notes") {
    const hlAddressDoc = document.getElementById(`hl-address-${feed_id}`);
    if (hlAddressDoc) hlAddressDoc.innerText = fieldValue || "-";
  }

  if (custInlineTimerMap[feed_id]) {
    clearTimeout(custInlineTimerMap[feed_id]);
  }

  custInlineTimerMap[feed_id] = setTimeout(() => {
    const inputs = tile.querySelectorAll(".feed-inline-input");
    const payload = {};
    inputs.forEach(inp => {
      const field = inp.getAttribute("onchange");
      if (field) {
        const match = field.match(/onInlineCustomerEdit\('[^']+',\s*'([^']+)'/);
        if (match && match[1]) {
          payload[match[1]] = inp.value.trim();
        }
      }
    });

    csrfFetch(`/feed/customer/edit/${feed_id}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload)
    })
      .then(r => r.json())
      .then(res => {
        if (!res.success) {
          showToast(res.error || "Failed to update customer details");
        }
      })
      .catch(err => console.error("Customer inline edit save error:", err));
  }, 600);
}

/* ----------------------------------------------------
   Open/Close Customer Detail Full-Page Overlay
---------------------------------------------------- */
function openCustDetail(feed_id) {
  const overlay = document.getElementById(`cust-detail-${feed_id}`);
  if (!overlay) return;
  overlay.classList.add('active');
  document.body.style.overflow = 'hidden';
}

function closeCustDetail(feed_id) {
  const overlay = document.getElementById(`cust-detail-${feed_id}`);
  if (!overlay) return;
  overlay.classList.remove('active');
  document.body.style.overflow = '';
}

// Close overlay when clicking backdrop (outside the panel)
document.addEventListener('click', function(e) {
  if (e.target.classList.contains('cust-detail-overlay')) {
    e.target.classList.remove('active');
    document.body.style.overflow = '';
  }
});

// Close overlay with Escape key
document.addEventListener('keydown', function(e) {
  if (e.key === 'Escape') {
    const activeOverlay = document.querySelector('.cust-detail-overlay.active');
    if (activeOverlay) {
      activeOverlay.classList.remove('active');
      document.body.style.overflow = '';
    }
  }
});



/* ----------------------------------------------------
   Open/Close Account Closure Detail Full-Page Overlay
---------------------------------------------------- */
function openClosureDetail(feed_id) {
  const overlay = document.getElementById(`closure-detail-${feed_id}`);
  if (!overlay) return;
  overlay.classList.add('active');
  document.body.style.overflow = 'hidden';
}

function closeClosureDetail(feed_id) {
  const overlay = document.getElementById(`closure-detail-${feed_id}`);
  if (!overlay) return;
  overlay.classList.remove('active');
  document.body.style.overflow = '';
}

function toggleClosurePayload(feed_id) {
  const block = document.getElementById(`closure-payload-content-${feed_id}`);
  const btn = document.getElementById(`closure-btn-payload-${feed_id}`);
  if (!block) return;
  const isHidden = (block.style.display === "none" || !block.style.display);
  block.style.display = isHidden ? "block" : "none";
  if (btn) {
    btn.innerHTML = isHidden 
      ? '<i class="fas fa-eye-slash me-1"></i> 📦 Hide Payload'
      : '<i class="fas fa-code me-1"></i> &lt;/&gt; View JSON';
  }
}

function closeZeroBalanceCustomer(feed_id, cid, name) {
  if (!confirm(`Are you sure you want to close customer account for ${name || 'Customer'}? Balance is ₹0.`)) {
    return;
  }
  acceptClosure(feed_id, cid, null);
}

/* ----------------------------------------------------
   Inline Closure Feed Auto-Save
---------------------------------------------------- */
let closureInlineTimerMap = {};

function onInlineClosureEdit(feed_id, fieldName, fieldValue) {
  const tile = document.getElementById(`closure-tile-${feed_id}`);
  if (!tile) return;

  if (closureInlineTimerMap[feed_id]) {
    clearTimeout(closureInlineTimerMap[feed_id]);
  }

  closureInlineTimerMap[feed_id] = setTimeout(() => {
    const inputs = tile.querySelectorAll(".feed-inline-input");
    const payload = {};
    inputs.forEach(inp => {
      const field = inp.getAttribute("onchange");
      if (field) {
        const match = field.match(/onInlineClosureEdit\('[^']+',\s*'([^']+)'/);
        if (match && match[1]) {
          payload[match[1]] = inp.value.trim();
        }
      }
    });

    csrfFetch(`/feed/closure/edit/${feed_id}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload)
    })
      .then(r => r.json())
      .then(res => {
        if (!res.success) {
          showToast(res.error || "Failed to update closure entry");
        }
      })
      .catch(err => console.error("Closure inline edit save error:", err));
  }, 600);
}

/* ----------------------------------------------------
   Unified Customer Closure Modal Handler (mirrors customer dashboard view_customer.js)
---------------------------------------------------- */
let activeClosureFeedId = null;
let activeClosureCid = null;
let activeClosureBalance = 0;

function openClosureSettlementModal(feed_id, cid, name, balanceAmount, interestAmount) {
  const balance = parseFloat(balanceAmount || 0);
  const interest = parseFloat(interestAmount || 0);

  activeClosureFeedId = feed_id;
  activeClosureCid = cid;
  activeClosureBalance = balance;

  const modal = document.getElementById("popCloseAccountModal");
  const statusMsg = document.getElementById("popCloseAccountStatusMsg");
  const optionsContainer = document.getElementById("popCloseAccountOptions");
  const discountSection = document.getElementById("popDiscountSection");
  const discountInput = document.getElementById("popDiscountInput");

  if (!modal || !statusMsg || !optionsContainer) {
    console.error("Close options modal element not found.");
    return;
  }

  optionsContainer.innerHTML = "";
  if (discountSection) discountSection.style.display = "none";
  if (discountInput) discountInput.value = "";

  if (balance <= 0) {
    // Automatically close without popup (identical to Customer Dashboard view_customer.js lines 2068-2073)
    const action = balance < 0 ? "written_off" : null;
    const actionLabel = balance < 0 ? "written off" : "zero balance";
    if (!confirm(`Are you sure you want to close account for ${name || 'Customer'}? (${actionLabel})`)) {
      return;
    }
    acceptClosure(feed_id, cid, action);
    return;
  }

  // Balance > 0 (identical to Customer Dashboard view_customer.js lines 2075-2108):
  statusMsg.innerHTML = `Remaining Balance is <strong>₹${balance.toFixed(0)}</strong>.<br>This account will be closed and marked as <strong>Defaulted</strong>.`;

  // Option 1: Default
  const defaultBtn = document.createElement("button");
  defaultBtn.className = "neumorphic-btn small danger-btn";
  defaultBtn.style.width = "100%";
  defaultBtn.style.justifyContent = "center";
  defaultBtn.style.fontWeight = "bold";
  defaultBtn.textContent = "Close Account";
  defaultBtn.addEventListener("click", () => {
    modal.style.display = "none";
    acceptClosure(feed_id, cid, "defaulted");
  });
  optionsContainer.appendChild(defaultBtn);

  // Option 2: Discount Interest (only if balance <= interestAmount)
  if (balance <= interest && interest > 0) {
    const discountBtn = document.createElement("button");
    discountBtn.className = "neumorphic-btn small primary-save-btn glow-cyan";
    discountBtn.style.width = "100%";
    discountBtn.style.justifyContent = "center";
    discountBtn.style.fontWeight = "bold";
    discountBtn.style.marginTop = "10px";
    discountBtn.textContent = "Discount Interest";
    discountBtn.addEventListener("click", () => {
      if (discountSection) discountSection.style.display = "block";
      if (discountInput) {
        discountInput.value = balance.toFixed(0);
        discountInput.focus();
      }
    });
    optionsContainer.appendChild(discountBtn);
  }

  modal.style.display = "flex";
}

function openClosureProcessModal(feed_id, cid, name, balanceAmount, interestAmount) {
  openClosureSettlementModal(feed_id, cid, name, balanceAmount, interestAmount);
}

function closePopCloseAccountModal() {
  const modal = document.getElementById("popCloseAccountModal");
  if (modal) modal.style.display = "none";
}

// Bind Confirm Discount button (matching customer dashboard view_customer.js lines 2143-2160)
document.addEventListener("DOMContentLoaded", function () {
  const popConfirmDiscountBtn = document.getElementById("popConfirmDiscountBtn");
  if (popConfirmDiscountBtn) {
    popConfirmDiscountBtn.addEventListener("click", function () {
      const discountInput = document.getElementById("popDiscountInput");
      const val = parseFloat(discountInput ? discountInput.value : 0) || 0;
      if (val <= 0) {
        showToast("Discount must be greater than 0");
        return;
      }
      if (val > activeClosureBalance) {
        showToast("Discount cannot exceed balance");
        return;
      }
      closePopCloseAccountModal();
      acceptClosureWithDiscount(activeClosureFeedId, activeClosureCid, val);
    });
  }

  // Close modal when clicking on backdrop
  window.addEventListener("click", function (event) {
    const modal = document.getElementById("popCloseAccountModal");
    if (modal && event.target === modal) {
      modal.style.display = "none";
    }
  });
});

/* Edit Payment Feed */
function editPayment(feed_payment_id) {
  const scriptTag = document.getElementById(`pay-data-${feed_payment_id}`);
  let data = {};
  if (scriptTag) {
    try {
      data = JSON.parse(scriptTag.textContent || "{}");
    } catch (e) {
      console.error("Failed to parse payment JSON:", e);
    }
  }

  document.getElementById("edit_pay_feed_id").value = feed_payment_id;
  document.getElementById("edit_pay_ano").value = data.ano || "";
  document.getElementById("edit_pay_amt").value = data.amt || "";
  document.getElementById("edit_pay_date").value = data.pdt || data.payment_date || "";
  document.getElementById("edit_pay_type").value = data.payment_type || "cash";

  openEditModal("editPaymentModal");
}

function savePaymentEdit(e) {
  e.preventDefault();
  const feed_payment_id = document.getElementById("edit_pay_feed_id").value;
  const payload = {
    ano: document.getElementById("edit_pay_ano").value.trim(),
    amt: document.getElementById("edit_pay_amt").value.trim(),
    payment_date: document.getElementById("edit_pay_date").value,
    payment_type: document.getElementById("edit_pay_type").value
  };

  handleFeedAction(
    `/feed/payment/edit/${feed_payment_id}`,
    "Payment feed item updated successfully",
    "Failed to update payment feed item",
    payload
  );
  closeEditModal("editPaymentModal");
}

/* Edit Closure Request */
function editClosure(feed_id, ano, vid) {
  document.getElementById("edit_closure_feed_id").value = feed_id;
  document.getElementById("edit_closure_ano").value = ano || "";
  document.getElementById("edit_closure_vid").value = vid || "";

  openEditModal("editClosureModal");
}

function saveClosureEdit(e) {
  e.preventDefault();
  const feed_id = document.getElementById("edit_closure_feed_id").value;
  const payload = {
    ano: document.getElementById("edit_closure_ano").value.trim(),
    vid: document.getElementById("edit_closure_vid").value.trim()
  };

  handleFeedAction(
    `/feed/closure/edit/${feed_id}`,
    "Account closure request updated successfully",
    "Failed to update closure request",
    payload
  );
  closeEditModal("editClosureModal");
}

/* Edit Existing Docs Review */
function editExistingDocs(docs_feed_id, ano, vid) {
  document.getElementById("edit_docs_feed_id").value = docs_feed_id;
  document.getElementById("edit_docs_ano").value = ano || "";
  document.getElementById("edit_docs_vid").value = vid || "";

  openEditModal("editDocsModal");
}

function saveDocsEdit(e) {
  e.preventDefault();
  const docs_feed_id = document.getElementById("edit_docs_feed_id").value;
  const payload = {
    ano: document.getElementById("edit_docs_ano").value.trim(),
    vid: document.getElementById("edit_docs_vid").value.trim()
  };

  handleFeedAction(
    `/feed/existing-docs/edit/${docs_feed_id}`,
    "Document review entry updated successfully",
    "Failed to update document review entry",
    payload
  );
  closeEditModal("editDocsModal");
}

/* Delete Functions */
function deleteClosure(feed_id, btn = null) {
  if (!btn && typeof window !== "undefined" && window.event && window.event.target) {
    btn = window.event.target.closest("button") || window.event.target;
  }
  if (!confirm("Are you sure you want to delete this closure request entry permanently?")) {
    return;
  }
  return handleFeedAction(
    `/feed/closure/delete/${feed_id}`,
    "Closure request deleted successfully",
    "Failed to delete closure request",
    null,
    btn
  );
}

function deleteCustomer(feed_id, btn = null) {
  if (!btn && typeof window !== "undefined" && window.event && window.event.target) {
    btn = window.event.target.closest("button") || window.event.target;
  }
  if (!confirm("Are you sure you want to delete this customer registration feed entry permanently?")) {
    return;
  }
  return handleFeedAction(
    `/feed/customer/delete/${feed_id}`,
    "Customer feed entry deleted successfully",
    "Failed to delete customer feed entry",
    null,
    btn
  );
}

function deleteExistingDocs(docs_feed_id, btn = null) {
  if (!btn && typeof window !== "undefined" && window.event && window.event.target) {
    btn = window.event.target.closest("button") || window.event.target;
  }
  if (!confirm("Are you sure you want to delete this document review entry permanently?")) {
    return;
  }
  return handleFeedAction(
    `/feed/existing-docs/delete/${docs_feed_id}`,
    "Document review entry deleted successfully",
    "Failed to delete document review entry",
    null,
    btn
  );
}

function deletePayment(feed_payment_id, btn = null) {
  if (!btn && typeof window !== "undefined" && window.event && window.event.target) {
    btn = window.event.target.closest("button") || window.event.target;
  }
  if (!confirm("Are you sure you want to delete this payment feed entry permanently?")) {
    return;
  }

  const row = document.getElementById(`pay-row-${feed_payment_id}`);
  if (row) {
    row.style.opacity = "0.4";
    row.style.pointerEvents = "none";
    row.querySelectorAll("button").forEach(b => {
      b.disabled = true;
      b.style.pointerEvents = "none";
    });
  }

  if (btn) {
    btn.disabled = true;
    btn.style.pointerEvents = "none";
  }

  csrfFetch(`/feed/payment/delete/${feed_payment_id}`, {
    method: "POST"
  })
    .then(res => res.json())
    .then(data => {
      if (data.success) {
        showToast("Payment feed entry deleted successfully");
        if (row) row.remove();
        checkDuplicatesAndUnmapped();
        renderDateTiles();
        recalculateCumulativeAmounts();
        updateTotalPayment();

        const remainingRows = document.querySelectorAll("#feedPaymentTable tbody tr.feed-pay-row");
        if (remainingRows.length === 0) {
          window.location.reload();
        }
      } else {
        if (row) {
          row.style.opacity = "1";
          row.style.pointerEvents = "auto";
        }
        alert(data.error || "Failed to delete payment feed entry");
      }
    })
    .catch(err => {
      console.error(err);
      if (row) {
        row.style.opacity = "1";
        row.style.pointerEvents = "auto";
      }
      alert("Server error deleting payment feed entry");
    });
}

function togglePayload(button) {
  const payloadId = button.getAttribute("data-target");
  const payload = document.getElementById(payloadId);
  if (!payload) return;

  const isOpen = !payload.hasAttribute("hidden");
  if (isOpen) {
    payload.setAttribute("hidden", "hidden");
    button.innerHTML = '<i class="fas fa-code"></i> View JSON';
    button.setAttribute("aria-expanded", "false");
  } else {
    payload.removeAttribute("hidden");
    button.innerHTML = '<i class="fas fa-box"></i> Hide Payload';
    button.setAttribute("aria-expanded", "true");
  }
}

function openAadhaarModalFromData(feed_id) {
  const dupeDataEl = document.getElementById(`cust-dupe-data-${feed_id}`);
  let accounts = [];
  if (dupeDataEl) {
    try {
      accounts = JSON.parse(dupeDataEl.textContent || '[]');
    } catch (e) {}
  }

  const tile = document.getElementById(`cust-tile-${feed_id}`);
  let currentAadhaar = "—";
  if (tile) {
    const aadhaarInp = tile.querySelector('input[onchange*="aadhaar_number"]');
    if (aadhaarInp && aadhaarInp.value) {
      currentAadhaar = aadhaarInp.value.trim();
    }
  }

  const modal = document.getElementById('duplicateAadhaarModal');
  const tbody = document.getElementById('dupeAccountsTableBody');
  const emptyNotice = document.getElementById('dupeAccountsEmptyNotice');
  const aadhaarSpan = document.getElementById('dupeModalAadhaar');
  const countBadge = document.getElementById('dupeModalCountBadge');

  if (!modal) return;

  if (aadhaarSpan) aadhaarSpan.textContent = currentAadhaar;
  if (countBadge) countBadge.textContent = `${accounts.length} Accounts`;

  if (tbody) {
    tbody.innerHTML = '';
    if (accounts.length === 0) {
      if (emptyNotice) emptyNotice.style.display = 'block';
    } else {
      if (emptyNotice) emptyNotice.style.display = 'none';
      accounts.forEach(acc => {
        const tr = document.createElement('tr');
        tr.style.borderBottom = '1px solid var(--border)';
        const isOpen = acc.status === 'open' || acc.status === 'active';
        const statusBadge = isOpen
          ? '<span style="background: rgba(16, 185, 129, 0.15); color: #10b981; border: 1px solid rgba(16, 185, 129, 0.3); border-radius: 12px; padding: 2px 8px; font-size: 11px; font-weight: 700;">OPEN</span>'
          : '<span style="background: rgba(100, 116, 139, 0.15); color: #64748b; border: 1px solid rgba(100, 116, 139, 0.3); border-radius: 12px; padding: 2px 8px; font-size: 11px; font-weight: 700;">CLOSED</span>';

        tr.innerHTML = `
          <td style="padding: 10px 14px; font-weight: 700; font-family: monospace;">#${acc.ano}</td>
          <td style="padding: 10px 14px; font-weight: 600;">${acc.name}</td>
          <td style="padding: 10px 14px; color: var(--text-secondary);"><i class="fas fa-map-marker-alt text-danger me-1"></i>${acc.village_name}</td>
          <td style="padding: 10px 14px; font-family: monospace;">${acc.phone_number || '—'}</td>
          <td style="padding: 10px 14px; font-weight: 600;">₹${Number(acc.total_amount).toLocaleString('en-IN')}</td>
          <td style="padding: 10px 14px; font-weight: 700; color: ${Number(acc.balance_amount) > 0 ? '#ef4444' : 'var(--text)'};">₹${Number(acc.balance_amount).toLocaleString('en-IN')}</td>
          <td style="padding: 10px 14px; text-align: center;">${statusBadge}</td>
        `;
        tbody.appendChild(tr);
      });
    }
  }

  modal.style.display = 'flex';
}

function closeAadhaarDuplicatesModal() {
  const modal = document.getElementById('duplicateAadhaarModal');
  if (modal) modal.style.display = 'none';
}

// Close duplicate Aadhaar modal on backdrop click
document.addEventListener('click', function (e) {
  const modal = document.getElementById('duplicateAadhaarModal');
  if (modal && e.target === modal) {
    modal.style.display = 'none';
  }
});

function openImageModal(label, base64Data) {
  const modal = document.getElementById("imageModal");
  const image = document.getElementById("modalImage");
  if (!modal || !image) return;

  let src = "";
  if (!base64Data) {
    return;
  } else if (typeof base64Data === "string") {
    src = base64Data.trim();
    if (!src.startsWith("data:") && !src.startsWith("http") && !src.startsWith("/")) {
      src = `data:image/jpeg;base64,${src}`;
    }
  } else if (base64Data instanceof HTMLElement) {
    src = base64Data.src || base64Data.getAttribute("src") || "";
  } else if (base64Data && base64Data.src) {
    src = base64Data.src;
  }

  if (!src) return;

  let cleanLabel = label || "Document Preview";
  if (cleanLabel.toLowerCase() === "aadhaar_front" || cleanLabel.toLowerCase() === "aadhaar front") {
    cleanLabel = "Aadhaar Front";
  } else if (cleanLabel.toLowerCase() === "aadhaar_back" || cleanLabel.toLowerCase() === "aadhaar back") {
    cleanLabel = "Aadhaar Back";
  } else if (cleanLabel.toLowerCase() === "house" || cleanLabel.toLowerCase() === "house photo") {
    cleanLabel = "House Photo";
  }

  const iconClass = cleanLabel.includes("House") ? "fa-home" : "fa-id-card";

  image.src = src;
  image.alt = cleanLabel;

  const labelEl = document.getElementById("modalImageLabel");
  if (labelEl) {
    labelEl.innerHTML = `<i class="fas ${iconClass} me-1.5 text-primary"></i> ${cleanLabel}`;
  }
  const dlBtn = document.getElementById("modalImageDownloadBtn");
  if (dlBtn) {
    dlBtn.href = src;
    dlBtn.download = `${cleanLabel.toLowerCase().replace(/\s+/g, "_")}.jpg`;
  }

  modal.style.display = "flex";
}

function closeImageModal() {
  const modal = document.getElementById("imageModal");
  const image = document.getElementById("modalImage");
  if (!modal) return;

  modal.style.display = "none";
  if (image) image.src = "";
}

// Close image modal on Escape key press
document.addEventListener("keydown", function(e) {
  if (e.key === "Escape") {
    const modal = document.getElementById("imageModal");
    if (modal && modal.style.display !== "none") {
      closeImageModal();
    }
  }
});

function showImageModal(src, label) {
  openImageModal(label || "Document Preview", src);
}

function showToast(msg) {
  const toast = document.getElementById("toast");
  if (!toast) {
    alert(msg);
    return;
  }

  toast.innerText = msg;
  toast.style.display = "block";
  setTimeout(() => {
    toast.style.display = "none";
  }, 3000);
}

function toggleAll(source) {
  document.querySelectorAll(".pay-checkbox:not(:disabled)").forEach(cb => {
    cb.checked = source.checked;
  });
  updateTotalPayment();
}

function selectAllPayments() {
  toggleSelectAllFeedPayments();
}

/* ----------------------------------------------------
   PhonePe Audio & Modal Animation
---------------------------------------------------- */
function playPhonePeChime() {
  try {
    const ctx = new (window.AudioContext || window.webkitAudioContext)();
    const osc1 = ctx.createOscillator();
    const osc2 = ctx.createOscillator();
    const gain = ctx.createGain();

    osc1.type = "sine";
    osc2.type = "sine";
    osc1.frequency.setValueAtTime(587.33, ctx.currentTime); // D5
    osc2.frequency.setValueAtTime(880.00, ctx.currentTime + 0.08); // A5

    gain.gain.setValueAtTime(0.35, ctx.currentTime);
    gain.gain.exponentialRampToValueAtTime(0.001, ctx.currentTime + 0.6);

    osc1.connect(gain);
    osc2.connect(gain);
    gain.connect(ctx.destination);

    osc1.start(ctx.currentTime);
    osc2.start(ctx.currentTime + 0.08);
    osc1.stop(ctx.currentTime + 0.6);
    osc2.stop(ctx.currentTime + 0.6);
  } catch (e) {
    console.log("Audio playback error or deferred", e);
  }
}

function showPhonePeSuccessModal(totalAmt, count) {
  const modal = document.getElementById("phonepeSuccessModal");
  const amtEl = document.getElementById("phonepeModalAmount");
  const countEl = document.getElementById("phonepeModalCount");

  if (amtEl) amtEl.innerText = `₹${parseFloat(totalAmt || 0).toLocaleString("en-IN")}`;
  if (countEl) countEl.innerText = `${count} Payment${count > 1 ? "s" : ""}`;

  if (modal) {
    modal.style.display = "flex";
    playPhonePeChime();
  } else {
    alert(`Success! ${count} payments (₹${totalAmt}) accepted into ledger.`);
    location.reload();
  }
}

function closePhonePeModalAndReload() {
  const modal = document.getElementById("phonepeSuccessModal");
  if (modal) modal.style.display = "none";
  location.reload();
}

/* ----------------------------------------------------
   Date Normalization Helpers (Strict DD-MM-YYYY)
---------------------------------------------------- */
function normalizeToDisplayDate(val) {
  if (!val) return "";
  const s = String(val).trim();
  // YYYY-MM-DD -> DD-MM-YYYY
  if (/^\d{4}-\d{2}-\d{2}$/.test(s)) {
    const [y, m, d] = s.split("-");
    return `${d}-${m}-${y}`;
  }
  // DD-MM-YYYY -> DD-MM-YYYY
  if (/^\d{2}-\d{2}-\d{4}$/.test(s)) {
    return s;
  }
  if (typeof formatDate === "function") {
    const formatted = formatDate(s);
    if (formatted) return formatted;
  }
  return s;
}

function normalizeToIsoDate(val) {
  if (!val) return "";
  const s = String(val).trim();
  // DD-MM-YYYY -> YYYY-MM-DD
  if (/^\d{2}-\d{2}-\d{4}$/.test(s)) {
    const [d, m, y] = s.split("-");
    return `${y}-${m}-${d}`;
  }
  // YYYY-MM-DD
  if (/^\d{4}-\d{2}-\d{2}$/.test(s)) {
    return s;
  }
  if (typeof formatDateToISO === "function") {
    const iso = formatDateToISO(s);
    if (iso) return iso;
  }
  return s;
}

function onInlineDateTextEdit(inputEl, feed_payment_id) {
  const row = document.getElementById(`pay-row-${feed_payment_id}`);
  if (!row) return;

  const rawVal = inputEl.value.trim();
  const displayVal = normalizeToDisplayDate(rawVal);
  const isoVal = normalizeToIsoDate(rawVal);

  if (displayVal) {
    inputEl.value = displayVal;
    row.dataset.date = displayVal;
    row.dataset.isoDate = isoVal;
    const hiddenPicker = row.querySelector(".hidden-date-trigger");
    if (hiddenPicker && isoVal) hiddenPicker.value = isoVal;
  }

  onInlineFeedEdit(inputEl, feed_payment_id, "pdt");
}

function openNativeDatePicker(btnEl) {
  const wrap = btnEl.closest(".date-cell-wrap") || btnEl.closest(".posting-input-wrap") || btnEl.closest("td");
  if (!wrap) return;
  const picker = wrap.querySelector(".hidden-date-trigger");
  if (!picker) return;

  if (typeof picker.showPicker === "function") {
    try {
      picker.showPicker();
      return;
    } catch (e) {}
  }
  picker.focus();
  picker.click();
}

function onHiddenDatePicked(pickerEl, feed_payment_id) {
  const row = document.getElementById(`pay-row-${feed_payment_id}`);
  if (!row) return;

  const isoVal = pickerEl.value;
  const displayVal = normalizeToDisplayDate(isoVal);

  const textInput = row.querySelector(".date-input");
  if (textInput) textInput.value = displayVal;

  row.dataset.date = displayVal;
  row.dataset.isoDate = isoVal;

  onInlineFeedEdit(textInput || pickerEl, feed_payment_id, "pdt");
}

/* ----------------------------------------------------
   Inline Feed Edit Mode & Validation
---------------------------------------------------- */
let inlineEditTimerMap = {};

function onInlineFeedEdit(inputEl, feed_payment_id, fieldType) {
  const row = document.getElementById(`pay-row-${feed_payment_id}`);
  if (!row) return;

  const anoInput = row.querySelector(".ano-input");
  const dateInput = row.querySelector(".date-input");
  const amtInput = row.querySelector(".amt-input");

  const newAno = anoInput ? anoInput.value.trim() : row.dataset.ano;
  const rawDate = dateInput ? dateInput.value.trim() : (row.dataset.date || row.dataset.isoDate);
  const newAmt = amtInput ? parseFloat(amtInput.value) || 0 : parseFloat(row.dataset.amount) || 0;

  const normDisplayDate = normalizeToDisplayDate(rawDate);
  const normIsoDate = normalizeToIsoDate(rawDate);

  row.dataset.ano = newAno;
  row.dataset.date = normDisplayDate;
  row.dataset.isoDate = normIsoDate;
  row.dataset.amount = newAmt;

  checkDuplicatesAndUnmapped();
  recalculateCumulativeAmounts();
  renderDateTiles();
  updateTotalPayment();

  if (inlineEditTimerMap[feed_payment_id]) {
    clearTimeout(inlineEditTimerMap[feed_payment_id]);
  }

  inlineEditTimerMap[feed_payment_id] = setTimeout(() => {
    csrfFetch(`/feed/payment/edit/${feed_payment_id}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        ano: newAno,
        payment_date: normDisplayDate,
        pdt: normDisplayDate,
        amt: newAmt
      })
    })
      .then(r => r.json())
      .then(res => {
        if (!res.success) {
          showToast(res.error || "Failed to update payment item");
        } else {
          const anoWrap = row.querySelector(".row-ano-wrap");
          if (res.mapped === true) {
            row.classList.remove("row-unmapped");
            row.dataset.cid = res.cid || "";
            if (anoWrap) {
              const dot = anoWrap.querySelector(".row-warn-dot.unmapped");
              if (dot) dot.remove();
            }
          } else if (res.mapped === false) {
            row.classList.add("row-unmapped");
            row.dataset.cid = "";
            if (anoWrap && !anoWrap.querySelector(".row-warn-dot.unmapped")) {
              const dot = document.createElement("span");
              dot.className = "row-warn-dot unmapped";
              dot.title = "Unmapped account for this village";
              anoWrap.appendChild(dot);
            }
          }
        }
      })
      .catch(err => console.error("Inline edit save error:", err));
  }, 600);
}

/* ----------------------------------------------------
   Duplicate Prevention & Unmapped Highlighting
---------------------------------------------------- */
function checkDuplicatesAndUnmapped() {
  const rows = document.querySelectorAll("#feedPaymentTable tbody tr.feed-pay-row");
  const pairCounts = {};

  rows.forEach(row => {
    const ano = (row.dataset.ano || "").trim();
    const date = normalizeToDisplayDate(row.dataset.date || row.dataset.isoDate || "");

    if (ano && date) {
      const key = `${ano}__${date}`;
      pairCounts[key] = (pairCounts[key] || 0) + 1;
    }
  });

  rows.forEach(row => {
    const ano = (row.dataset.ano || "").trim();
    const date = normalizeToDisplayDate(row.dataset.date || row.dataset.isoDate || "");
    const key = `${ano}__${date}`;
    const cb = row.querySelector(".pay-checkbox");
    const anoWrap = row.querySelector(".row-ano-wrap");
    const isDuplicate = pairCounts[key] > 1;

    row.classList.remove("row-duplicate");
    const oldDupDot = anoWrap ? anoWrap.querySelector(".row-warn-dot.duplicate") : null;
    if (oldDupDot) oldDupDot.remove();

    if (isDuplicate) {
      row.classList.add("row-duplicate");
      if (cb) {
        cb.disabled = false;
        cb.title = "Duplicate entry: Select to delete";
      }
      if (anoWrap) {
        const dupDot = document.createElement("span");
        dupDot.className = "row-warn-dot duplicate";
        dupDot.title = "Duplicate Account Number and Date entry (delete or edit to resolve)";
        anoWrap.appendChild(dupDot);
      }
    } else {
      if (cb) {
        cb.disabled = false;
        cb.title = "";
      }
    }
  });
}

/* ----------------------------------------------------
   Cumulative Amount Calculation (Plain Elegant Typography)
---------------------------------------------------- */
function recalculateCumulativeAmounts() {
  const rows = document.querySelectorAll("#feedPaymentTable tbody tr.feed-pay-row");
  let runningTotal = 0;

  rows.forEach(row => {
    if (row.style.display === "none") return;

    const amt = parseFloat(row.dataset.amount) || 0;
    runningTotal += amt;

    const cumCell = row.querySelector(".cumulative-cell");
    if (cumCell) {
      cumCell.innerHTML = `<span class="cell-plain-val cumul-val">₹${runningTotal.toLocaleString("en-IN")}</span>`;
    }
  });
}

function focusLastRowInput() {
  const lastRow = document.querySelector("#feedPaymentTable tbody tr.feed-pay-row:last-child");
  if (lastRow) {
    const anoInput = lastRow.querySelector(".ano-input");
    if (anoInput) {
      anoInput.focus();
      anoInput.select();
    }
  }
}

/* ----------------------------------------------------
   Date Grouping Filter Tiles (Standardized DD-MM-YYYY)
---------------------------------------------------- */
let activeDateFilter = "ALL";

function renderDateTiles() {
  const container = document.getElementById("feedDateTilesContainer");
  if (!container) return;

  const rows = document.querySelectorAll("#feedPaymentTable tbody tr.feed-pay-row");
  const dateMap = {};
  let grandTotal = 0;
  let grandCount = 0;

  rows.forEach(row => {
    const d = normalizeToDisplayDate(row.dataset.date || row.dataset.isoDate || "");
    const amt = parseFloat(row.dataset.amount) || 0;

    if (d) {
      if (!dateMap[d]) dateMap[d] = { count: 0, total: 0 };
      dateMap[d].count += 1;
      dateMap[d].total += amt;

      grandCount += 1;
      grandTotal += amt;
    }
  });

  const uniqueDates = Object.keys(dateMap).sort((a, b) => {
    return normalizeToIsoDate(a).localeCompare(normalizeToIsoDate(b));
  });

  if (uniqueDates.length < 2) {
    container.style.display = "none";
    return;
  }

  container.style.display = "flex";
  let html = `<button type="button" class="date-tile-btn ${activeDateFilter === "ALL" ? "active" : ""}" onclick="filterFeedByDate('ALL')">
    <i class="fas fa-layer-group text-primary"></i>
    <span class="date-tile-title">All Dates</span>
    <span class="date-tile-count">${grandCount}</span>
    <span class="date-tile-amount">₹${grandTotal.toLocaleString("en-IN")}</span>
  </button>`;

  uniqueDates.forEach(d => {
    const item = dateMap[d];
    html += `<button type="button" class="date-tile-btn ${activeDateFilter === d ? "active" : ""}" onclick="filterFeedByDate('${d}')">
      <i class="fas fa-calendar-day"></i>
      <span class="date-tile-title">${d}</span>
      <span class="date-tile-count">${item.count}</span>
      <span class="date-tile-amount">₹${item.total.toLocaleString("en-IN")}</span>
    </button>`;
  });

  container.innerHTML = html;
}

function filterFeedByDate(targetDate) {
  activeDateFilter = targetDate;
  const rows = document.querySelectorAll("#feedPaymentTable tbody tr.feed-pay-row");

  rows.forEach(row => {
    const rowDate = normalizeToDisplayDate(row.dataset.date || row.dataset.isoDate || "");
    if (targetDate === "ALL" || rowDate === targetDate) {
      row.style.display = "";
    } else {
      row.style.display = "none";
    }
  });

  renderDateTiles();
  recalculateCumulativeAmounts();
  updateTotalPayment();
}

/* ----------------------------------------------------
   Selection & Dynamic Totals
---------------------------------------------------- */
function toggleSelectAllFeedPayments() {
  const visibleRows = document.querySelectorAll("#feedPaymentTable tbody tr.feed-pay-row");
  const enabledCbs = [];

  visibleRows.forEach(row => {
    if (row.style.display === "none") return;
    // Skip duplicate entries and unmapped accounts from bulk selection
    if (row.classList.contains("row-duplicate") || row.classList.contains("row-unmapped")) return;
    const cb = row.querySelector(".pay-checkbox:not(:disabled)");
    if (cb) enabledCbs.push(cb);
  });

  if (enabledCbs.length === 0) return;

  const allChecked = enabledCbs.every(cb => cb.checked);
  const targetState = !allChecked;

  enabledCbs.forEach(cb => {
    cb.checked = targetState;
  });

  const headerCheck = document.getElementById("feedHeaderCheck");
  if (headerCheck) headerCheck.checked = targetState;

  const btn = document.getElementById("feedSelectAllBtn");
  if (btn) {
    btn.innerHTML = targetState ? '<i class="fas fa-times me-1"></i> Deselect' : '<i class="fas fa-check-double me-1"></i> Select All';
  }

  updateTotalPayment();
}

function updateTotalPayment() {
  let selectedTotal = 0;
  let selectedCount = 0;
  let grandTotal = 0;
  let grandCount = 0;
  let hasSelectedDuplicates = false;

  const visibleRows = document.querySelectorAll("#feedPaymentTable tbody tr.feed-pay-row");

  visibleRows.forEach(row => {
    if (row.style.display === "none") return;
    const isDup = row.classList.contains("row-duplicate");
    const amt = parseFloat(row.dataset.amount) || 0;

    if (!isDup) {
      grandTotal += amt;
      grandCount += 1;
    }

    const cb = row.querySelector(".pay-checkbox");
    if (cb && cb.checked) {
      selectedTotal += amt;
      selectedCount += 1;
      row.classList.add("row-selected");
      if (isDup) {
        hasSelectedDuplicates = true;
      }
    } else {
      row.classList.remove("row-selected");
    }
  });

  const labelEl = document.getElementById("totalBadgeLabel");
  const totalEl = document.getElementById("selectedTotal");
  const acceptBtn = document.getElementById("acceptBtn");
  const deleteBtn = document.getElementById("deleteSelectedBtn");

  if (selectedCount > 0) {
    if (labelEl) labelEl.innerText = `Selected (${selectedCount} of ${grandCount}):`;
    if (totalEl) totalEl.innerText = selectedTotal.toLocaleString("en-IN");
    if (deleteBtn) {
      deleteBtn.innerHTML = `<i class="fas fa-trash-alt me-1"></i> Delete (${selectedCount})`;
      deleteBtn.style.display = "inline-flex";
      deleteBtn.disabled = false;
      deleteBtn.style.opacity = "1";
    }
    if (acceptBtn) {
      acceptBtn.innerHTML = `<i class="fas fa-check-double me-1"></i> Submit (${selectedCount})`;
      acceptBtn.style.display = "inline-flex";
      if (hasSelectedDuplicates) {
        acceptBtn.disabled = true;
        acceptBtn.style.opacity = "0.45";
        acceptBtn.title = "Cannot submit: Duplicate rows selected. Delete duplicates or uncheck them before submitting.";
      } else {
        acceptBtn.disabled = false;
        acceptBtn.style.opacity = "1";
        acceptBtn.title = "Submit selected payments to ledger";
      }
    }
  } else {
    if (labelEl) labelEl.innerText = `Grand Total (${grandCount} items):`;
    if (totalEl) totalEl.innerText = grandTotal.toLocaleString("en-IN");
    if (acceptBtn) {
      acceptBtn.style.display = "none";
    }
    if (deleteBtn) {
      deleteBtn.style.display = "none";
    }
  }

  const feedTable = document.getElementById("feedPaymentTable");
  if (feedTable) {
    if (selectedCount > 0) {
      feedTable.classList.add("has-selection");
    } else {
      feedTable.classList.remove("has-selection");
    }
  }

  const headerCheck = document.getElementById("feedHeaderCheck");
  if (headerCheck) {
    headerCheck.checked = (selectedCount > 0 && selectedCount === grandCount && !hasSelectedDuplicates);
  }

  const countPill = document.querySelector(".posting-count-pill");
  if (countPill) {
    const totalCount = document.querySelectorAll("#feedPaymentTable tbody tr.feed-pay-row").length;
    countPill.innerHTML = `<i class="fas fa-layer-group me-1"></i> ${totalCount} Records`;
  }
}

/* ----------------------------------------------------
   Payment Accept Handlers with PhonePe Animation
---------------------------------------------------- */
function acceptSinglePaymentRow(feed_payment_id, btnEl) {
  const row = document.getElementById(`pay-row-${feed_payment_id}`);
  if (!row) return;

  const amount = parseFloat(row.dataset.amount) || 0;
  const ano = (row.dataset.ano || "").trim();

  if (row.classList.contains("row-duplicate")) {
    alert(`Cannot submit duplicate payment entry for Account #${ano}.\n\nPlease delete one of the duplicate entries or edit the account number first.`);
    return;
  }

  if (row.classList.contains("row-unmapped")) {
    alert(`Account #${ano} is not mapped to an active customer in this village.\n\nPlease verify the account number or approve the new customer registration first.`);
    return;
  }

  const originalHtml = btnEl ? btnEl.innerHTML : "";
  if (btnEl) {
    btnEl.disabled = true;
    btnEl.innerHTML = '<i class="fas fa-spinner fa-spin"></i>';
  }

  csrfFetch(`/feed/payment/accept/${feed_payment_id}`, {
    method: "POST"
  })
    .then(res => res.json())
    .then(data => {
      if (data.success) {
        showPhonePeSuccessModal(amount, 1);
      } else {
        alert(data.error || "Failed to accept payment");
        if (btnEl) {
          btnEl.disabled = false;
          btnEl.innerHTML = originalHtml;
        }
      }
    })
    .catch(err => {
      console.error(err);
      alert("Server error");
      if (btnEl) {
        btnEl.disabled = false;
        btnEl.innerHTML = originalHtml;
      }
    });
}

function acceptSelected() {
  const btn = document.getElementById("acceptBtn");

  // Non-blocking selection: automatically exclude duplicates and unmapped accounts from submission
  const selectedDuplicates = [];
  const selectedUnmapped = [];
  const selectedIds = [];
  let selectedSum = 0;

  document.querySelectorAll(".pay-checkbox:checked").forEach(cb => {
    const row = cb.closest("tr");
    if (!row) return;

    if (row.classList.contains("row-duplicate")) {
      const ano = (row.dataset.ano || "").trim();
      if (ano && !selectedDuplicates.includes(ano)) {
        selectedDuplicates.push(ano);
      }
      cb.checked = false;
      return;
    }

    if (row.classList.contains("row-unmapped")) {
      const ano = (row.dataset.ano || "").trim();
      if (ano && !selectedUnmapped.includes(ano)) {
        selectedUnmapped.push(ano);
      }
      cb.checked = false;
      return;
    }

    selectedIds.push(cb.value);
    selectedSum += parseFloat(row.dataset.amount) || 0;
  });

  if (selectedDuplicates.length > 0 || selectedUnmapped.length > 0) {
    let warnMsg = [];
    if (selectedDuplicates.length > 0) {
      warnMsg.push(`Duplicate Account(s) skipped: ${selectedDuplicates.join(", ")}`);
    }
    if (selectedUnmapped.length > 0) {
      warnMsg.push(`Unmapped Account(s) skipped: ${selectedUnmapped.join(", ")}`);
    }
    showToast(`⚠️ ${warnMsg.join(" | ")}. Proceeding with ${selectedIds.length} valid payment(s).`, 4000);
  }

  if (selectedIds.length === 0) {
    showToast("Select at least one payment");
    return;
  }

  const originalHtml = btn ? btn.innerHTML : "";
  if (btn) {
    btn.disabled = true;
    btn.innerHTML = '<i class="fas fa-spinner fa-spin me-1"></i> Submitting...';
  }

  csrfFetch("/feed/payment/accept_batch", {
    method: "POST",
    headers: {
      "Content-Type": "application/json"
    },
    body: JSON.stringify({ ids: selectedIds })
  })
    .then(res => res.json())
    .then(data => {
      if (data.success) {
        if (data.failed_items && data.failed_items.length > 0) {
          const failedDetails = data.failed_items.map(f => `• Account #${f.ano}: ${f.reason}`).join("\n");
          if (data.accepted_count > 0) {
            alert(`✅ Successfully posted ${data.accepted_count} payment(s).\n\n⚠️ ${data.failed_items.length} payment(s) were NOT posted and remain in the queue:\n${failedDetails}`);
            showPhonePeSuccessModal(data.accepted_sum || selectedSum, data.accepted_count);
          } else {
            alert(`⚠️ None of the selected payments were posted. The following items require attention:\n\n${failedDetails}`);
            location.reload();
          }
        } else {
          showPhonePeSuccessModal(data.accepted_sum || selectedSum, data.accepted_count || selectedIds.length);
        }
      } else {
        if (data.failed_items && data.failed_items.length > 0) {
          const failedDetails = data.failed_items.map(f => `• Account #${f.ano}: ${f.reason}`).join("\n");
          alert(`❌ Unable to post payments:\n\n${failedDetails}`);
        } else {
          alert(data.error || "Failed to submit payments");
        }
        if (btn) {
          btn.disabled = false;
          btn.innerHTML = originalHtml;
        }
      }
    })
    .catch(err => {
      console.error(err);
      showToast("Error processing payments");
      if (btn) {
        btn.disabled = false;
        btn.innerHTML = originalHtml;
      }
    });
}

function deleteSelectedPayments() {
  const selectedCbs = document.querySelectorAll(".pay-checkbox:checked");
  const selectedIds = [];
  selectedCbs.forEach(cb => {
    if (cb.value) selectedIds.push(cb.value);
  });

  if (selectedIds.length === 0) {
    showToast("Select at least one payment to delete");
    return;
  }

  if (!confirm(`Are you sure you want to permanently delete the ${selectedIds.length} selected payment entries?`)) {
    return;
  }

  const btn = document.getElementById("deleteSelectedBtn");
  const originalHtml = btn ? btn.innerHTML : "";
  if (btn) {
    btn.disabled = true;
    btn.innerHTML = '<i class="fas fa-spinner fa-spin me-1"></i> Deleting...';
  }

  csrfFetch("/feed/payment/delete_batch", {
    method: "POST",
    headers: {
      "Content-Type": "application/json"
    },
    body: JSON.stringify({ ids: selectedIds })
  })
    .then(res => res.json())
    .then(data => {
      if (data.success) {
        showToast(`${selectedIds.length} payments deleted successfully`);
        selectedIds.forEach(id => {
          const row = document.getElementById(`pay-row-${id}`);
          if (row) row.remove();
        });
        checkDuplicatesAndUnmapped();
        renderDateTiles();
        recalculateCumulativeAmounts();
        updateTotalPayment();

        const remainingRows = document.querySelectorAll("#feedPaymentTable tbody tr.feed-pay-row");
        if (remainingRows.length === 0) {
          window.location.reload();
        }
      } else {
        alert(data.error || "Failed to delete payments");
        if (btn) {
          btn.disabled = false;
          btn.innerHTML = originalHtml;
        }
      }
    })
    .catch(err => {
      console.error(err);
      alert("Server error deleting payments");
      if (btn) {
        btn.disabled = false;
        btn.innerHTML = originalHtml;
      }
    });
}

function acceptClosure(feed_id, cid, action) {
  if (action === "defaulted" && !confirm("Are you sure you want to close this account and mark it as Defaulted?")) {
    return;
  }
  if (action === "written_off" && !confirm("Are you sure you want to close this account and mark it as Written Off?")) {
    return;
  }

  return csrfFetch(`/feed/closure/accept/${feed_id}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ action: action })
  })
    .then(res => res.json())
    .then(data => {
      if (data.success) {
        showToast("Account closed successfully!");
        setTimeout(() => location.reload(), 1000);
      } else {
        showToast(data.error || "Failed to close account");
      }
    })
    .catch(err => {
      console.error(err);
      showToast("Server error");
    });
}

function acceptClosureWithDiscount(feed_id, cid, discountVal) {
  let val = discountVal;
  if (val === undefined || val === null) {
    const discountInput = document.getElementById("popDiscountInput") || document.getElementById(`discount-${feed_id}`);
    val = parseFloat(discountInput ? discountInput.value : 0) || 0;
  }
  if (val <= 0) {
    showToast("Discount must be greater than 0");
    return;
  }

  if (!confirm(`Are you sure you want to close this account with a discount of ₹${val}?`)) {
    return;
  }

  return csrfFetch(`/feed/closure/accept/${feed_id}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ action: "discount_interest", discount_amount: val })
  })
    .then(res => res.json())
    .then(data => {
      if (data.success) {
        showToast("Account closed with discount successfully!");
        setTimeout(() => location.reload(), 1000);
      } else {
        showToast(data.error || "Failed to close account");
      }
    })
    .catch(err => {
      console.error(err);
      showToast("Server error");
    });
}

/* ----------------------------------------------------
   Feed Payment Table Column Sorting
---------------------------------------------------- */
let currentSortCol = null;
let currentSortDir = "none"; // "asc", "desc", "none" (default submission order)

function initFeedTableSorting() {
  const table = document.getElementById("feedPaymentTable");
  if (!table) return;
  const tbody = table.querySelector("tbody");
  if (!tbody) return;

  // Stamp original submission order on each row once
  const initialRows = Array.from(tbody.querySelectorAll("tr.feed-pay-row"));
  initialRows.forEach((row, idx) => {
    if (!row.dataset.originalIndex) {
      row.dataset.originalIndex = String(idx);
    }
  });

  const headers = table.querySelectorAll("th.sortable-th");
  headers.forEach(th => {
    th.addEventListener("click", () => {
      const col = th.dataset.col;
      let nextDir = "asc";
      if (currentSortCol === col) {
        if (currentSortDir === "asc") nextDir = "desc";
        else if (currentSortDir === "desc") nextDir = "none";
        else nextDir = "asc";
      }

      currentSortCol = nextDir === "none" ? null : col;
      currentSortDir = nextDir;

      // Update header icons and styles
      headers.forEach(h => {
        const iconSpan = h.querySelector(".sort-icon");
        if (!iconSpan) return;
        if (h === th && nextDir === "asc") {
          iconSpan.innerHTML = '<i class="fas fa-sort-up text-primary ms-1" style="font-size: 11px;"></i>';
          h.classList.add("sorted-header");
        } else if (h === th && nextDir === "desc") {
          iconSpan.innerHTML = '<i class="fas fa-sort-down text-primary ms-1" style="font-size: 11px;"></i>';
          h.classList.add("sorted-header");
        } else {
          iconSpan.innerHTML = '<i class="fas fa-sort text-muted ms-1" style="font-size: 11px;"></i>';
          h.classList.remove("sorted-header");
        }
      });

      // Sort rows
      const rows = Array.from(tbody.querySelectorAll("tr.feed-pay-row"));
      rows.sort((a, b) => {
        if (nextDir === "none") {
          return parseInt(a.dataset.originalIndex, 10) - parseInt(b.dataset.originalIndex, 10);
        }

        if (col === "ano") {
          const inpA = a.querySelector(".ano-input");
          const inpB = b.querySelector(".ano-input");
          const valA = parseInt(inpA ? inpA.value : a.dataset.ano, 10) || 0;
          const valB = parseInt(inpB ? inpB.value : b.dataset.ano, 10) || 0;
          return nextDir === "asc" ? valA - valB : valB - valA;
        }

        if (col === "pdt") {
          const inpA = a.querySelector(".date-input");
          const inpB = b.querySelector(".date-input");
          const rawA = (inpA ? inpA.value : a.dataset.date || a.dataset.isoDate || "").trim();
          const rawB = (inpB ? inpB.value : b.dataset.date || b.dataset.isoDate || "").trim();
          const valA = normalizeToIsoDate(rawA);
          const valB = normalizeToIsoDate(rawB);
          return nextDir === "asc" ? valA.localeCompare(valB) : valB.localeCompare(valA);
        }

        if (col === "amt" || col === "cumulative") {
          const inpA = a.querySelector(".amt-input");
          const inpB = b.querySelector(".amt-input");
          const valA = parseFloat(inpA ? inpA.value : a.dataset.amount) || 0;
          const valB = parseFloat(inpB ? inpB.value : b.dataset.amount) || 0;
          return nextDir === "asc" ? valA - valB : valB - valA;
        }

        if (col === "status") {
          const getStatusWeight = (row) => {
            if (row.classList.contains("row-unmapped")) return "1_unmapped";
            if (row.classList.contains("row-duplicate")) return "2_duplicate";
            return "0_pending";
          };
          const valA = getStatusWeight(a);
          const valB = getStatusWeight(b);
          return nextDir === "asc" ? valA.localeCompare(valB) : valB.localeCompare(valA);
        }

        return 0;
      });

      // Move rows in DOM to new order
      rows.forEach(row => tbody.appendChild(row));

      // Re-calculate running cumulative amounts based on current sorted order
      recalculateCumulativeAmounts();
    });
  });
}

document.addEventListener("DOMContentLoaded", function () {
  checkDuplicatesAndUnmapped();
  recalculateCumulativeAmounts();
  renderDateTiles();
  updateTotalPayment();
  initFeedTableSorting();

  // Allow clicking anywhere on a row to toggle selection and reveal actions
  const feedTable = document.getElementById("feedPaymentTable");
  if (feedTable) {
    feedTable.addEventListener("click", function (e) {
      if (e.target.closest("input, button, a, label, select, .posting-action-circle")) return;
      const row = e.target.closest("tr.feed-pay-row");
      if (!row) return;
      const cb = row.querySelector(".pay-checkbox:not(:disabled)");
      if (cb) {
        cb.checked = !cb.checked;
        updateTotalPayment();
      }
    });
  }
});

