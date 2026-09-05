function handleFeedAction(url, successMessage, failureFallback, body = null) {
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
        alert(successMessage);
        location.reload();
      } else {
        alert(data.error || failureFallback);
      }
    })
    .catch(err => {
      console.error(err);
      alert("Server error");
    });
}

function accept(feed_id) {
  return handleFeedAction(
    `/feed/customer/accept/${feed_id}`,
    "Customer accepted successfully",
    "Failed to accept customer"
  );
}

function acceptPayment(feed_payment_id) {
  return handleFeedAction(
    `/feed/payment/accept/${feed_payment_id}`,
    "Payment accepted",
    "Failed to accept payment"
  );
}

function acceptDocs(feed_id) {
  return handleFeedAction(
    `/feed/docs/accept/${feed_id}`,
    "Customer documents accepted",
    "Failed to accept customer documents"
  );
}

function acceptExistingDocs(docs_feed_id) {
  return handleFeedAction(
    `/feed/existing-docs/accept/${docs_feed_id}`,
    "Documents accepted into customer records",
    "Failed to accept documents"
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
function deleteClosure(feed_id) {
  if (!confirm("Are you sure you want to delete this closure request entry permanently?")) {
    return;
  }
  return handleFeedAction(
    `/feed/closure/delete/${feed_id}`,
    "Closure request deleted successfully",
    "Failed to delete closure request"
  );
}

function deleteCustomer(feed_id) {
  if (!confirm("Are you sure you want to delete this customer registration feed entry permanently?")) {
    return;
  }
  return handleFeedAction(
    `/feed/customer/delete/${feed_id}`,
    "Customer feed entry deleted successfully",
    "Failed to delete customer feed entry"
  );
}

function deleteExistingDocs(docs_feed_id) {
  if (!confirm("Are you sure you want to delete this document review entry permanently?")) {
    return;
  }
  return handleFeedAction(
    `/feed/existing-docs/delete/${docs_feed_id}`,
    "Document review entry deleted successfully",
    "Failed to delete document review entry"
  );
}

function deletePayment(feed_payment_id) {
  if (!confirm("Are you sure you want to delete this payment feed entry permanently?")) {
    return;
  }
  return handleFeedAction(
    `/feed/payment/delete/${feed_payment_id}`,
    "Payment feed entry deleted successfully",
    "Failed to delete payment feed entry"
  );
}

function togglePayload(button) {
  const payloadId = button.getAttribute("data-target");
  const payload = document.getElementById(payloadId);
  if (!payload) return;

  const isOpen = !payload.hasAttribute("hidden");
  if (isOpen) {
    payload.setAttribute("hidden", "hidden");
    button.textContent = "📦 View Payload";
    button.setAttribute("aria-expanded", "false");
  } else {
    payload.removeAttribute("hidden");
    button.textContent = "📦 Hide Payload";
    button.setAttribute("aria-expanded", "true");
  }
}

function openImageModal(label, base64Data) {
  const modal = document.getElementById("imageModal");
  const image = document.getElementById("modalImage");
  if (!modal || !image) return;

  image.src = `data:image/jpeg;base64,${base64Data}`;
  image.alt = label;
  modal.style.display = "flex";
}

function closeImageModal() {
  const modal = document.getElementById("imageModal");
  const image = document.getElementById("modalImage");
  if (!modal || !image) return;

  modal.style.display = "none";
  image.src = "";
}

function showToast(msg) {
  const toast = document.getElementById("toast");
  if (!toast) return;

  toast.innerText = msg;
  toast.style.display = "block";
  setTimeout(() => {
    toast.style.display = "none";
  }, 3000);
}

function toggleAll(source) {
  document.querySelectorAll(".pay-checkbox").forEach(cb => {
    cb.checked = source.checked;
  });
  updateTotalPayment();
}

function selectAllPayments() {
  document.querySelectorAll(".pay-checkbox").forEach(cb => {
    cb.checked = true;
  });
  updateTotalPayment();
}

function updateTotalPayment() {
  let total = 0;

  document.querySelectorAll(".pay-checkbox:checked").forEach(cb => {
    const row = cb.closest("tr");
    if (!row) return;

    const amountEl = row.querySelector("[data-money]");
    const raw = amountEl ? amountEl.getAttribute("data-money") || "0" : "0";
    total += parseFloat(raw || 0);
  });

  const totalEl = document.getElementById("selectedTotal");
  if (totalEl) {
    totalEl.innerText = total.toLocaleString("en-IN");
  }
}

function acceptSelected() {
  const btn = document.getElementById("acceptBtn");
  const selected = [];

  document.querySelectorAll(".pay-checkbox:checked").forEach(cb => {
    selected.push(cb.value);
  });

  if (selected.length === 0) {
    showToast("Select at least one payment");
    return;
  }

  const originalText = btn ? btn.innerText : "";
  if (btn) {
    btn.disabled = true;
    btn.innerText = "Processing...";
  }

  csrfFetch("/feed/payment/accept_batch", {
    method: "POST",
    headers: {
      "Content-Type": "application/json"
    },
    body: JSON.stringify({ ids: selected })
  })
    .then(res => res.json())
    .then(data => {
      if (data.success) {
        showToast(data.message || "Payments accepted");
        setTimeout(() => location.reload(), 1000);
      } else {
        showToast(data.error || "Failed");
        if (btn) {
          btn.disabled = false;
          btn.innerText = originalText;
        }
      }
    })
    .catch(err => {
      console.error(err);
      showToast("Error processing payments");
      if (btn) {
        btn.disabled = false;
        btn.innerText = originalText;
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
        alert("Account closed and moved to closed customers!");
        location.reload();
      } else {
        alert(data.error || "Failed to close account");
      }
    })
    .catch(err => {
      console.error(err);
      alert("Server error");
    });
}

function acceptClosureWithDiscount(feed_id, cid) {
  const discountInput = document.getElementById(`discount-${feed_id}`);
  const val = parseFloat(discountInput.value) || 0;
  if (val <= 0) {
    alert("Discount must be greater than 0");
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
        alert("Account closed with discount successfully!");
        location.reload();
      } else {
        alert(data.error || "Failed to close account");
      }
    })
    .catch(err => {
      console.error(err);
      alert("Server error");
    });
}

document.addEventListener("DOMContentLoaded", function () {
  updateTotalPayment();

  if (document.getElementById("feedPaymentTable")) {
    $('#feedPaymentTable').DataTable({
      paging: false,
      info: false,
      searching: true,
      ordering: true,
      autoWidth: false,
      columnDefs: [
        { targets: [0, 6], orderable: false }
      ]
    });
  }

  const groupByEl = document.getElementById("groupBy");
  const groupSelect = document.getElementById("groupSelect");
  if (!groupByEl || !groupSelect) return;

  function populateGroupSelect(type) {
    groupSelect.innerHTML = "";

    if (type === "none") {
      groupSelect.style.display = "none";
      document.querySelectorAll(".pay-checkbox").forEach(cb => {
        cb.checked = false;
      });
      updateTotalPayment();
      return;
    }

    groupSelect.style.display = "inline-block";

    const uniqueValues = new Set();
    const rows = document.querySelectorAll(".payment-feed-table tbody tr");

    rows.forEach(row => {
      if (type === "date") {
        const d = (row.dataset.date || row.dataset.isoDate || "").trim();
        if (d) uniqueValues.add(d);
      } else if (type === "ano") {
        const a = (row.dataset.ano || "").trim();
        if (a) uniqueValues.add(a);
      }
    });

    const defaultOpt = document.createElement("option");
    defaultOpt.value = "";
    defaultOpt.textContent = type === "date" ? "-- Select Date --" : "-- Select ANO --";
    groupSelect.appendChild(defaultOpt);

    const sortedValues = Array.from(uniqueValues).sort((a, b) => {
      if (type === "ano") {
        return (parseInt(a) || 0) - (parseInt(b) || 0);
      }
      return a.localeCompare(b);
    });

    sortedValues.forEach(val => {
      const opt = document.createElement("option");
      opt.value = val;
      opt.textContent = val;
      groupSelect.appendChild(opt);
    });

    document.querySelectorAll(".pay-checkbox").forEach(cb => {
      cb.checked = false;
    });
    updateTotalPayment();
  }

  groupByEl.addEventListener("change", function () {
    populateGroupSelect(this.value);
  });

  groupSelect.addEventListener("change", function () {
    const type = groupByEl.value;
    const selectedVal = this.value.trim();

    document.querySelectorAll(".payment-feed-table tbody tr").forEach(row => {
      const cb = row.querySelector(".pay-checkbox");
      if (!cb) return;

      if (!selectedVal) {
        cb.checked = false;
      } else if (type === "date") {
        const rowDate = (row.dataset.date || "").trim();
        const rowIsoDate = (row.dataset.isoDate || "").trim();
        cb.checked = (rowDate === selectedVal || rowIsoDate === selectedVal);
      } else if (type === "ano") {
        const rowAno = (row.dataset.ano || "").trim();
        cb.checked = (rowAno === selectedVal);
      }
    });

    updateTotalPayment();
  });
});
