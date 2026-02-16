document.addEventListener("DOMContentLoaded", function () {

  const table = document.getElementById("employeeTable");
  const body = document.getElementById("employeeTableBody");
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

  /* COLUMN SELECTOR */

  const modal = document.getElementById("columnModal");
  const list = document.getElementById("columnCheckboxList");
  const openBtn = document.getElementById("tableViewBtn");
  const closeBtn = document.getElementById("closeColumnModal");

  openBtn.addEventListener("click", () => {

    list.innerHTML = "";

    table.querySelectorAll("thead th").forEach((th, index) => {
      if (index === 0) return;

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

/* ===== EDIT + SAVE ===== */

function enableEdit(btn) {
  const row = btn.closest("tr");

  if (btn.innerText === "Edit") {

    row.querySelectorAll("td[data-field]").forEach(td => {
      if (td.dataset.field !== "eid") {
        td.contentEditable = true;
        td.classList.add("highlighted");
      }
    });

    btn.innerText = "Save";

  } else {

    const updatedData = {};
    row.querySelectorAll("td[data-field]").forEach(td => {
      updatedData[td.dataset.field] = td.innerText.trim();
      td.contentEditable = false;
      td.classList.remove("highlighted");
    });

    fetch("/api/update_employee", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(updatedData)
    })
    .then(res => res.json())
    .then(data => {
      if (data.success) {
        btn.innerText = "Edit";
      } else {
        alert("Update failed: " + data.error);
      }
    });
  }
}

/* ===== DELETE ===== */

function deleteEmployee(eid) {

  if (!confirm("Delete this employee?")) return;

  fetch("/api/delete_employee", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ eid })
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