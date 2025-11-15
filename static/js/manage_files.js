// manage_files.js
document.addEventListener("DOMContentLoaded", () => {
  const listContainer = document.getElementById("gcsFilesList");
  const uploadInput = document.getElementById("gcsUploadInput");
  const uploadBtn = document.getElementById("gcsUploadBtn");
  const refreshBtn = document.getElementById("gcsRefreshBtn");

  async function fetchFiles() {
    listContainer.innerHTML = "<div class='loading'>Loading files…</div>";
    try {
      const res = await fetch("/api/list_files");
      const data = await res.json();
      if (!data.success) throw new Error(data.error || "Failed to list files");
      renderFiles(data.files || []);
    } catch (err) {
      listContainer.innerHTML = `<div class="error">Error: ${err.message}</div>`;
    }
  }

  function renderFiles(files) {
    if (!files || files.length === 0) {
      listContainer.innerHTML = "<div class='empty'>No .sqlite files found in GCS</div>";
      return;
    }
    listContainer.innerHTML = "";
    files.forEach((f) => {
      // f may be {name,size,updated} or a plain string
      const name = (typeof f === "string") ? f : f.name;
      const size = f.size || "undefined";
      const updated = f.updated || "undefined";

      const item = document.createElement("div");
      item.className = "gcs-file-row";
      item.innerHTML = `
        <div class="meta">
          <div class="filename">${name}</div>
          <div class="sub">Size: ${size} &nbsp;|&nbsp; Uploaded: ${updated}</div>
        </div>
        <div class="actions">
          <button class="btn set-active" data-name="${name}">Set Active</button>
          <button class="btn download" data-name="${name}">Download</button>
          <button class="btn delete" data-name="${name}">Delete</button>
        </div>
      `;
      listContainer.appendChild(item);
    });

    // wire actions
    document.querySelectorAll(".set-active").forEach(btn => {
      btn.addEventListener("click", async (e) => {
        const filename = e.currentTarget.dataset.name;
        await setActive(filename);
      });
    });
    document.querySelectorAll(".download").forEach(btn => {
      btn.addEventListener("click", (e) => {
        const filename = e.currentTarget.dataset.name;
        window.location = `/api/download_file/${encodeURIComponent(filename)}`;
      });
    });
    document.querySelectorAll(".delete").forEach(btn => {
      btn.addEventListener("click", async (e) => {
        const filename = e.currentTarget.dataset.name;
        if (!confirm(`Delete ${filename} from GCS? This cannot be undone.`)) return;
        await deleteFile(filename);
      });
    });
  }

  async function setActive(filename) {
    try {
      const res = await fetch("/api/set_active", {
        method: "POST",
        headers: {"Content-Type": "application/json"},
        body: JSON.stringify({filename})
      });
      const data = await res.json();
      if (!data.success) throw new Error(data.error || "Failed to set active");
      alert(`Set active: ${filename}`);
      // refresh UI to reflect available active file
      await fetchFiles();
      // optionally reload page so templates show new active file
      window.location.reload();
    } catch (err) {
      alert(`Failed to set active file: ${err.message}`);
    }
  }

  async function deleteFile(filename) {
    try {
      const res = await fetch("/api/delete_file", {
        method: "POST",
        headers: {"Content-Type": "application/json"},
        body: JSON.stringify({filename})
      });
      const data = await res.json();
      if (!data.success) throw new Error(data.error || "Delete failed");
      alert(`Deleted: ${filename}`);
      await fetchFiles();
    } catch (err) {
      alert(`Delete failed: ${err.message}`);
    }
  }

  uploadBtn && uploadBtn.addEventListener("click", async () => {
    const files = uploadInput.files;
    if (!files || files.length === 0) {
      alert("Select one or more .sqlite files to upload");
      return;
    }
    const form = new FormData();
    // send as files[] to support multiple
    for (let i = 0; i < files.length; i++) {
      form.append("files[]", files[i]);
    }
    try {
      uploadBtn.disabled = true;
      uploadBtn.textContent = "Uploading...";
      const res = await fetch("/api/upload_sqlite", {
        method: "POST",
        body: form
      });
      const data = await res.json();
      if (!data.success) {
        throw new Error(data.errors && data.errors.length ? JSON.stringify(data.errors) : data.error || "Upload failed");
      }
      alert("Uploaded: " + (data.uploaded || []).join(", "));
      uploadInput.value = "";
      await fetchFiles();
    } catch (err) {
      alert("Upload failed: " + err.message);
    } finally {
      uploadBtn.disabled = false;
      uploadBtn.textContent = "Upload";
    }
  });

  refreshBtn && refreshBtn.addEventListener("click", fetchFiles);

  // initial load
  fetchFiles();
});