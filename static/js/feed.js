function handleFeedAction(url, successMessage, failureFallback) {
  return csrfFetch(url, {
    method: "POST"
  })
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

function rejectExistingDocs(docs_feed_id) {
  if (!confirm("Reject these uploaded documents?")) {
    return;
  }

  return handleFeedAction(
    `/feed/existing-docs/reject/${docs_feed_id}`,
    "Documents rejected",
    "Failed to reject documents"
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

document.addEventListener("DOMContentLoaded", function () {
  updateTotalPayment();

  const groupByEl = document.getElementById("groupBy");
  const groupInput = document.getElementById("groupInput");
  if (!groupByEl || !groupInput) return;

  groupByEl.addEventListener("change", function () {
    const type = this.value;

    groupInput.value = "";
    document.querySelectorAll(".pay-checkbox").forEach(cb => {
      cb.checked = false;
    });
    updateTotalPayment();

    if (type === "none") {
      groupInput.style.display = "none";
    } else {
      groupInput.style.display = "inline-block";
      groupInput.placeholder = type === "date" ? "Enter date (YYYY-MM-DD)" : "Enter ANO";
    }
  });

  groupInput.addEventListener("input", function () {
    const type = groupByEl.value;
    const value = this.value.trim();
    if (!value) return;

    document.querySelectorAll(".payment-feed-table tbody tr").forEach(row => {
      const cb = row.querySelector(".pay-checkbox");
      if (!cb) return;
      cb.checked = row.dataset[type] == value;
    });

    updateTotalPayment();
  });
});
