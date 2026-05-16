/* ---------- Globals ---------- */
let originalData = [];
let filteredData = [];

/* Default visible columns */
const DEFAULT_COLUMNS = ["ano", "payment_date", "amt", "payment_status"];

/* Column definitions (order + labels) */
const COLUMN_DEFS = [
  { key: "pid", label: "PID" },
  { key: "ano", label: "ANO" },
  { key: "payment_date", label: "Paid Date" },
  { key: "amt", label: "Amount" },
  { key: "created_at", label: "Created At" },
  { key: "eid", label: "EID" },
  { key: "cid", label: "CID" },
  { key: "vid", label: "VID" },
  { key: "payment_status", label: "Payment Status" }
];

let visibleColumns = [...DEFAULT_COLUMNS];

/* ---------- Init ---------- */
document.addEventListener("DOMContentLoaded", () => {
  try {
    const raw = document.getElementById("payment-data").textContent;
    const rows = JSON.parse(raw);

    originalData = rows.map(r => ({
      pid: r.pid,
      ano: r.ano,
      payment_date: r.payment_date,
      amt: Number(r.amt || 0),
      created_at: r.created_at,
      eid: r.eid,
      cid: r.cid,
      vid: r.vid,
      payment_status: r.payment_status
    }));
  } catch (e) {
    console.error("Failed to parse payment data", e);
    return;
  }

  filteredData = [...originalData];

  renderColumnSelector();
  renderTable(filteredData);

  document.getElementById("filterAno")?.addEventListener("input", applyFilters);
  document.getElementById("filterFrom")?.addEventListener("change", applyFilters);
  document.getElementById("filterTo")?.addEventListener("change", applyFilters);

  document.getElementById("tableViewBtn")?.addEventListener("click", toggleColumnModal);
  document.getElementById("closeColumnModal")?.addEventListener("click", toggleColumnModal);
});

/* ---------- Date Utils ---------- */
function parseISODate(d) {
  return d ? new Date(d) : null;
}

function parseDDMMYYYY(str) {
  if (!str) return null;
  const [dd, mm, yyyy] = str.split("/");
  return new Date(`${yyyy}-${mm}-${dd}`);
}

function formatDateDDMMYYYY(isoDate) {
  if (!isoDate) return "";
  const d = new Date(isoDate);
  if (isNaN(d)) return isoDate;
  const dd = String(d.getDate()).padStart(2, "0");
  const mm = String(d.getMonth() + 1).padStart(2, "0");
  const yyyy = d.getFullYear();
  return `${dd}-${mm}-${yyyy}`;
}

/* ---------- Render Table ---------- */
function renderTable(data) {
  const table = document.getElementById("postingTable");
  const thead = table.querySelector("thead tr");
  const tbody = table.querySelector("tbody");

  thead.innerHTML = "";
  tbody.innerHTML = "";

  visibleColumns.forEach(col => {
    const def = COLUMN_DEFS.find(c => c.key === col);
    if (!def) return;
    const th = document.createElement("th");
    th.textContent = def.label;
    th.onclick = () => sortReport(col);
    thead.appendChild(th);
  });

  let totalAmt = 0;
  const uniqueAno = new Set();

  data.forEach(row => {
    uniqueAno.add(row.ano);
    totalAmt += row.amt;

    const tr = document.createElement("tr");
    visibleColumns.forEach(col => {
      const td = document.createElement("td");
      if (col === "amt") {
        td.innerHTML = `<span data-money>${row[col]}</span>`;

      } else if (col === "payment_date") {
        td.textContent = formatDateDDMMYYYY(row[col]);

      } else if (col === "payment_status") {

        const status = String(row[col] || "")
          .trim()
          .toLowerCase()
          .replace(/\s+/g, "-");

        td.innerHTML = `
          <span class="status-badge status-${status}">
            ${row[col] ?? ""}
          </span>
        `;

      } else {
        td.textContent = row[col] ?? "";
      }
      tr.appendChild(td);
    });
    tbody.appendChild(tr);
  });

  document.getElementById("totalAmt").textContent = totalAmt.toFixed(2);
  document.getElementById("totalAno").textContent = uniqueAno.size;
}

/* ---------- Filters ---------- */
function applyFilters() {
  const ano = document.getElementById("filterAno").value.trim();
  const from = parseDDMMYYYY(document.getElementById("filterFrom").value.trim());
  const to = parseDDMMYYYY(document.getElementById("filterTo").value.trim());

  filteredData = originalData.filter(r => {
    if (ano && String(r.ano) !== ano) return false;
    const d = parseISODate(r.payment_date);
    if (from && d < from) return false;
    if (to && d > to) return false;
    return true;
  });

  renderTable(filteredData);
}

function resetFilters() {
  document.getElementById("filterAno").value = "";
  document.getElementById("filterFrom").value = "";
  document.getElementById("filterTo").value = "";
  filteredData = [...originalData];
  renderTable(filteredData);
}

/* ---------- Sorting ---------- */
function sortReport(col) {
  filteredData.sort((a, b) =>
    typeof a[col] === "number"
      ? a[col] - b[col]
      : String(a[col]).localeCompare(String(b[col]))
  );
  renderTable(filteredData);
}

/* ---------- Column Selector ---------- */
function renderColumnSelector() {
  const list = document.getElementById("columnCheckboxList");
  if (!list) return;

  list.innerHTML = "";

  COLUMN_DEFS.forEach(c => {
    const label = document.createElement("label");
    const cb = document.createElement("input");
    cb.type = "checkbox";
    cb.checked = visibleColumns.includes(c.key);

    cb.onchange = () => {
      visibleColumns = cb.checked
        ? [...new Set([...visibleColumns, c.key])]
        : visibleColumns.filter(k => k !== c.key);
      renderTable(filteredData);
    };

    label.appendChild(cb);
    label.append(" " + c.label);
    list.appendChild(label);
  });
}

function toggleColumnModal() {
  document.getElementById("columnModal")?.classList.toggle("hidden");
}
