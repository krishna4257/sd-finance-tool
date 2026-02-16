document.addEventListener("DOMContentLoaded", function () {

  const table = document.getElementById("villageTable");
  const body = document.getElementById("villageTableBody");
  const rows = Array.from(body.querySelectorAll("tr"));

  const snapshot = rows.map(row => ({
    row,
    text: row.innerText.toLowerCase()
  }));

  function updateSummary() {
    const visible = snapshot.filter(d => d.row.style.display !== "none");
    document.getElementById("totalCount").textContent = visible.length;
  }

  window.applySearch = function () {
    const term = document.getElementById("searchBox").value.toLowerCase();
    snapshot.forEach(d => {
      d.row.style.display = term === "" || d.text.includes(term) ? "" : "none";
    });
    updateSummary();
  };

  window.resetSearch = function () {
    document.getElementById("searchBox").value = "";
    snapshot.forEach(d => d.row.style.display = "");
    updateSummary();
  };

  window.toggleAll = function (source) {
    body.querySelectorAll("input[type='checkbox']")
        .forEach(cb => cb.checked = source.checked);
  };

  window.printSelected = function () {
    window.print();
  };

  /* ===== COLUMN SELECTOR (same logic as customers page) ===== */

  const modal = document.getElementById("columnModal");
  const list = document.getElementById("columnCheckboxList");
  const openBtn = document.getElementById("tableViewBtn");
  const closeBtn = document.getElementById("closeColumnModal");

  openBtn.addEventListener("click", () => {

    list.innerHTML = "";

    table.querySelectorAll("thead th").forEach((th, index) => {
      if (index === 0) return; // skip checkbox

      const wrapper = document.createElement("label");
      wrapper.className = "column-item";

      const checkbox = document.createElement("input");
      checkbox.type = "checkbox";
      checkbox.checked = true;

      checkbox.addEventListener("change", () => {
        toggleColumn(index, checkbox.checked);
      });

      wrapper.appendChild(checkbox);
      wrapper.appendChild(document.createTextNode(th.innerText));

      list.appendChild(wrapper);
    });

    modal.classList.remove("hidden");
  });

  closeBtn.addEventListener("click", () => {
    modal.classList.add("hidden");
  });

  function toggleColumn(index, show) {
    table.querySelectorAll("tr").forEach(row => {
      if (row.children[index])
        row.children[index].style.display = show ? "" : "none";
    });
  }

  updateSummary();
});

/* ===== ENABLE EDIT ===== */

/* ===== ENABLE EDIT + SAVE TO DB ===== */

function enableEdit(btn) {
  const row = btn.closest("tr");
  const vidCell = row.querySelector("td[data-field='vid']");
  const vid = vidCell ? vidCell.innerText.trim() : null;

  // If currently in Edit mode → switch to Save
  if (btn.innerText === "Edit") {

    row.querySelectorAll("td[data-field]").forEach(td => {
      if (td.dataset.field !== "vid") { // never edit primary key
        td.contentEditable = true;
        td.classList.add("highlighted");
      }
    });

    btn.innerText = "Save";
    btn.classList.remove("edit-btn");
    btn.classList.add("save-btn");

  } else {

    // Collect updated data
    const updatedData = {};
    row.querySelectorAll("td[data-field]").forEach(td => {
      updatedData[td.dataset.field] = td.innerText.trim();
      td.contentEditable = false;
      td.classList.remove("highlighted");
    });

    fetch("/api/update_village", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(updatedData)
    })
    .then(res => res.json())
    .then(data => {
      if (data.success) {
        btn.innerText = "Edit";
        btn.classList.remove("save-btn");
        btn.classList.add("edit-btn");
      } else {
        alert("Update failed: " + data.error);
      }
    });
  }
}

/* ===== DELETE ===== */

function deleteVillage(vid) {

  if (!confirm("Delete this village?")) return;

  fetch("/api/delete_village", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ vid })
  })
  .then(res => res.json())
  .then(data => {
    if (data.success) {
      location.reload();
    } else {
      alert("Delete failed");
    }
  });
}