// Employee Detail Page Unified Management Script
document.addEventListener("DOMContentLoaded", function () {
  
  /* ── Tab Switching ── */
  window.switchProfileTab = function (tabId, btn) {
    if (btn && btn.classList.contains("locked")) return;

    document.querySelectorAll(".tab-pane").forEach(pane => pane.classList.remove("active"));
    document.querySelectorAll(".profile-tab-btn").forEach(b => b.classList.remove("active"));

    const targetPane = document.getElementById(tabId);
    if (targetPane) targetPane.classList.add("active");
    if (btn) btn.classList.add("active");
  };

  /* ── Datepicker Init ── */
  const dateInput = document.getElementById("detailJoiningDate");
  if (dateInput && typeof window.initCustomCalendar === "function") {
    window.initCustomCalendar(dateInput, {
      dateFormat: 'd-m-Y',
      clickOpens: true
    });
  }

  /* ── Helper: Date Formatting ── */
  function ddmmyyyyToIso(dateStr) {
    if (!dateStr) return "";
    const parts = dateStr.split('-');
    if (parts.length === 3) {
      const [dd, mm, yyyy] = parts;
      return `${yyyy}-${mm}-${dd}`;
    }
    return dateStr;
  }

  async function getCsrfToken() {
    return document.querySelector('meta[name="csrf-token"]')?.getAttribute('content') ||
           document.querySelector('input[name="csrf_token"]')?.value || "";
  }

  /* ── Photo Upload ── */
  const photoInput = document.getElementById("profilePhotoInput");
  if (photoInput) {
    photoInput.addEventListener("change", async function () {
      if (!this.files || !this.files[0]) return;
      const file = this.files[0];
      const formData = new FormData();
      formData.append("eid", window.DETAIL_EMP_ID);
      formData.append("photo", file);

      try {
        const csrfToken = await getCsrfToken();
        const res = await fetch("/api/employee/upload_photo", {
          method: "POST",
          headers: { "X-CSRFToken": csrfToken },
          body: formData
        });
        const data = await res.json();
        if (data.success) {
          const squircle = document.querySelector(".profile-avatar-squircle");
          if (squircle) {
            squircle.innerHTML = `<img src="${data.photo_url}" alt="Employee Photo" class="profile-avatar-img" id="detailAvatarImg">`;
          }
          if (typeof showToast === "function") {
            showToast("Profile photo updated successfully!", "success");
          } else {
            alert("Profile photo updated successfully!");
          }
        } else {
          alert(data.error || "Failed to upload photo");
        }
      } catch (err) {
        alert("Upload error: " + err.message);
      }
    });
  }

  /* ── Employee Details Save ── */
  window.saveEmployeeDetails = async function (e) {
    e.preventDefault();
    const form = e.target;
    const formData = new FormData(form);

    const eid = formData.get("eid");
    const name = formData.get("name").trim();
    const phone_number = (formData.get("phone_number") || "").trim();
    const level = formData.get("level");
    const city = (formData.get("city") || "").trim();
    const state = (formData.get("state") || "").trim();
    const display_date = (formData.get("joining_date") || "").trim();
    const joining_date = ddmmyyyyToIso(display_date);

    try {
      const csrfToken = await getCsrfToken();
      const res = await fetch("/api/update_employee", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "X-CSRFToken": csrfToken
        },
        body: JSON.stringify({
          eid,
          name,
          phone_number,
          level,
          city,
          state,
          joining_date
        })
      });
      const data = await res.json();
      if (data.success) {
        // Update header UI
        const nameEl = document.querySelector(".profile-hero-name");
        if (nameEl) nameEl.textContent = name;

        if (typeof showToast === "function") {
          showToast("Employee details saved successfully!", "success");
        } else {
          alert("Employee details saved successfully!");
        }
      } else {
        alert(data.error || "Failed to update employee details");
      }
    } catch (err) {
      alert("Error saving: " + err.message);
    }
  };

  /* ── Village Management ── */
  let allVillages = Array.isArray(window.ALL_VILLAGES) ? [...window.ALL_VILLAGES] : [];
  let availableVillages = allVillages.filter(v => !v.is_assigned);
  let assignedVillages = allVillages.filter(v => v.is_assigned);

  function renderVillages() {
    const availBox = document.getElementById("availableVillagesList");
    const assignedBox = document.getElementById("assignedVillagesList");
    const availCount = document.getElementById("availableCount");
    const assignedCount = document.getElementById("assignedCount");
    const chipsBox = document.getElementById("assignedChipsContainer");

    if (availBox) {
      availBox.innerHTML = "";
      availableVillages.forEach(v => {
        const item = document.createElement("div");
        item.className = "village-option";
        item.dataset.vid = v.vid;
        item.innerHTML = `<span>${v.village_name}</span><small style="color:var(--text-secondary);font-size:0.75rem;">${v.district || ''}</small>`;
        item.onclick = () => item.classList.toggle("selected");
        availBox.appendChild(item);
      });
    }

    if (assignedBox) {
      assignedBox.innerHTML = "";
      assignedVillages.forEach(v => {
        const item = document.createElement("div");
        item.className = "village-option";
        item.dataset.vid = v.vid;
        item.innerHTML = `<span>${v.village_name}</span><small style="color:var(--text-secondary);font-size:0.75rem;">${v.district || ''}</small>`;
        item.onclick = () => item.classList.toggle("selected");
        assignedBox.appendChild(item);
      });
    }

    if (availCount) availCount.textContent = availableVillages.length;
    if (assignedCount) assignedCount.textContent = assignedVillages.length;

    if (chipsBox) {
      chipsBox.innerHTML = "";
      if (assignedVillages.length === 0) {
        chipsBox.innerHTML = `<span style="color:var(--text-secondary);font-size:0.85rem;font-style:italic;">No villages currently assigned.</span>`;
      } else {
        assignedVillages.forEach(v => {
          const chip = document.createElement("span");
          chip.className = "village-chip";
          chip.innerHTML = `${v.village_name} <button type="button" class="chip-remove" onclick="unassignSingleVillage(${v.vid})" title="Remove">×</button>`;
          chipsBox.appendChild(chip);
        });
      }
    }
  }

  window.filterVillages = function () {
    const term = (document.getElementById("villageSearchBox")?.value || "").toLowerCase().trim();
    document.querySelectorAll("#availableVillagesList .village-option").forEach(el => {
      const match = el.textContent.toLowerCase().includes(term);
      el.style.display = match ? "flex" : "none";
    });
  };

  window.selectAllVillages = function () {
    document.querySelectorAll("#availableVillagesList .village-option").forEach(el => {
      if (el.style.display !== "none") el.classList.add("selected");
    });
  };

  window.clearAllVillages = function () {
    availableVillages = [...availableVillages, ...assignedVillages];
    assignedVillages = [];
    renderVillages();
  };

  window.transferSelected = function (direction) {
    if (direction === "right") {
      const selectedEls = Array.from(document.querySelectorAll("#availableVillagesList .village-option.selected"));
      const selectedVids = new Set(selectedEls.map(el => parseInt(el.dataset.vid)));
      const moved = availableVillages.filter(v => selectedVids.has(v.vid));
      availableVillages = availableVillages.filter(v => !selectedVids.has(v.vid));
      assignedVillages = [...assignedVillages, ...moved];
    } else {
      const selectedEls = Array.from(document.querySelectorAll("#assignedVillagesList .village-option.selected"));
      const selectedVids = new Set(selectedEls.map(el => parseInt(el.dataset.vid)));
      const moved = assignedVillages.filter(v => selectedVids.has(v.vid));
      assignedVillages = assignedVillages.filter(v => !selectedVids.has(v.vid));
      availableVillages = [...availableVillages, ...moved];
    }
    renderVillages();
  };

  window.unassignSingleVillage = function (vid) {
    const vObj = assignedVillages.find(v => v.vid === vid);
    if (vObj) {
      assignedVillages = assignedVillages.filter(v => v.vid !== vid);
      availableVillages.push(vObj);
      renderVillages();
    }
  };

  window.saveVillageAssignments = async function () {
    const vids = assignedVillages.map(v => v.vid);
    try {
      const csrfToken = await getCsrfToken();
      const res = await fetch(`/api/employee/${window.DETAIL_EMP_ID}/update_villages`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "X-CSRFToken": csrfToken
        },
        body: JSON.stringify({ village_ids: vids })
      });
      const data = await res.json();
      if (data.ok || data.success) {
        if (typeof showToast === "function") {
          showToast("Village assignments saved successfully!", "success");
        } else {
          alert("Village assignments saved successfully!");
        }
      } else {
        alert(data.error || data.msg || "Failed to save village assignments");
      }
    } catch (err) {
      alert("Error saving villages: " + err.message);
    }
  };

  renderVillages();

  /* ── Device Management ── */
  window.resetEmployeeDevice = async function (userId, deviceId, deviceModel) {
    const isSingle = deviceId && deviceId !== "ALL" && deviceId !== "PENDING";
    const msg = isSingle
      ? `Are you sure you want to reset hardware lock for ${deviceModel || 'this device'}? The employee will be able to bind a new phone on their next login.`
      : "Are you sure you want to reset all device hardware locks for this employee? They will need to bind their new device upon next login.";
    if (!confirm(msg)) {
      return;
    }
    try {
      const csrfToken = await getCsrfToken();
      const res = await fetch("/api/users/reset_device", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "X-CSRFToken": csrfToken
        },
        body: JSON.stringify({ id: userId, device_id: isSingle ? deviceId : null })
      });
      const data = await res.json();
      if (data.ok || data.success) {
        if (typeof showToast === "function") {
          showToast(data.message || "Device lock reset successfully! Re-binding pending.", "success");
        } else {
          alert(data.message || "Device lock reset successfully! Re-binding pending.");
        }
        setTimeout(() => location.reload(), 1200);
      } else {
        alert(data.error || data.msg || "Failed to reset device");
      }
    } catch (err) {
      alert("Reset failed: " + err.message);
    }
  };

  /* ── Admin Controls: 30-min Download Link ── */
  let linkCountdownInterval = null;

  window.generateDetailInstallLink = async function (eid, empName) {
    try {
      const csrfToken = await getCsrfToken();
      const res = await fetch("/admin/generate_download_link", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "X-CSRFToken": csrfToken
        },
        body: JSON.stringify({ employee_id: eid })
      });
      const data = await res.json();
      if (data.success) {
        const container = document.getElementById("generatedLinkContainer");
        const urlInput = document.getElementById("detailInstallUrlInput");
        const waBtn = document.getElementById("detailWhatsappShareBtn");
        const smsBtn = document.getElementById("detailSmsShareBtn");

        if (container) container.style.display = "block";
        if (urlInput) urlInput.value = data.url;

        // Message text
        const shareMsg = `Hello ${empName}, here is your temporary link to install the Smart Counting Mobile App: ${data.url}\n\nNote: This link will expire in 30 minutes.`;

        if (waBtn) {
          let cleanPhone = (data.phone || "").replace(/\D/g, "");
          if (cleanPhone.length === 10) cleanPhone = "91" + cleanPhone;
          const waUrl = cleanPhone 
            ? `https://api.whatsapp.com/send?phone=${cleanPhone}&text=${encodeURIComponent(shareMsg)}`
            : `https://api.whatsapp.com/send?text=${encodeURIComponent(shareMsg)}`;
          waBtn.href = waUrl;
        }

        if (smsBtn) {
          const smsPhone = data.phone || "";
          smsBtn.href = `sms:${smsPhone}?&body=${encodeURIComponent(shareMsg)}`;
        }

        // Start countdown
        startCountdown(data.expires_at);

      } else {
        alert(data.error || "Failed to generate link");
      }
    } catch (err) {
      alert("Error: " + err.message);
    }
  };

  function startCountdown(expiresAt) {
    if (linkCountdownInterval) clearInterval(linkCountdownInterval);
    const target = new Date(expiresAt).getTime();

    function update() {
      const now = Date.now();
      const diff = Math.max(0, target - now);
      const minutes = Math.floor(diff / 60000);
      const seconds = Math.floor((diff % 60000) / 1000);

      const timerEl = document.getElementById("detailCountdownTimer");
      const boxEl = document.getElementById("detailCountdownBox");

      if (diff <= 0) {
        clearInterval(linkCountdownInterval);
        if (timerEl) timerEl.textContent = "EXPIRED";
        if (boxEl) {
          boxEl.style.background = "rgba(239, 68, 68, 0.12)";
          boxEl.style.color = "#f87171";
          boxEl.style.borderColor = "rgba(239, 68, 68, 0.3)";
        }
        return;
      }

      if (timerEl) {
        timerEl.textContent = `${String(minutes).padStart(2, '0')}:${String(seconds).padStart(2, '0')}`;
      }
    }

    update();
    linkCountdownInterval = setInterval(update, 1000);
  }

  window.copyDetailLink = function () {
    const input = document.getElementById("detailInstallUrlInput");
    if (!input) return;
    input.select();
    navigator.clipboard.writeText(input.value).then(() => {
      if (typeof showToast === "function") {
        showToast("Link copied to clipboard!", "success");
      } else {
        alert("Link copied to clipboard!");
      }
    });
  };

  /* ── Password Reset & User Provisioning ── */
  window.resetPasswordFromDetail = async function (e) {
    e.preventDefault();
    const userId = document.getElementById("detailUserId")?.value;
    const password = document.getElementById("detailNewPassword")?.value;

    if (!userId || !password) {
      alert("Please enter a new password");
      return;
    }

    try {
      const csrfToken = await getCsrfToken();
      const res = await fetch("/api/users/reset_password", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "X-CSRFToken": csrfToken
        },
        body: JSON.stringify({ id: userId, password: password })
      });
      const data = await res.json();
      if (data.ok) {
        if (typeof showToast === "function") {
          showToast("Password updated successfully!", "success");
        } else {
          alert("Password updated successfully!");
        }
        document.getElementById("detailNewPassword").value = "";
      } else {
        alert(data.msg || "Failed to reset password");
      }
    } catch (err) {
      alert("Reset error: " + err.message);
    }
  };

  window.createUserFromDetail = async function (e) {
    e.preventDefault();
    const username = document.getElementById("newEmpUsername")?.value.trim();
    const password = document.getElementById("newEmpPassword")?.value;

    if (!username || !password) {
      alert("Please enter username and password");
      return;
    }

    try {
      const csrfToken = await getCsrfToken();
      const res = await fetch(`/api/employee/${window.DETAIL_EMP_ID}/create_user`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "X-CSRFToken": csrfToken
        },
        body: JSON.stringify({ username: username, password: password })
      });
      const data = await res.json();
      if (data.ok || data.success) {
        if (typeof showToast === "function") {
          showToast("User account created successfully!", "success");
        } else {
          alert("User account created successfully!");
        }
        setTimeout(() => location.reload(), 1200);
      } else {
        alert(data.msg || "Failed to create user account");
      }
    } catch (err) {
      alert("Creation error: " + err.message);
    }
  };

});
