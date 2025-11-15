// ===============================
// MANAGE FILES PAGE JS
// ===============================

// Auto-load file list on page load
document.addEventListener("DOMContentLoaded", () => {
    loadFiles();
});

// -----------------------------
// FETCH ALL FILES FROM GCS
// -----------------------------
function loadFiles() {
    fetch("/list_sqlite_files")
        .then(res => res.json())
        .then(data => {
            const container = document.getElementById("fileListContainer");

            if (!data.success) {
                container.innerHTML = `<p class="error">Unable to load files.</p>`;
                return;
            }

            const files = data.files;
            if (!files.length) {
                container.innerHTML = `<p>No files found in Cloud Storage.</p>`;
                return;
            }

            let html = `
                <table class="file-table">
                    <thead>
                        <tr>
                            <th>File Name</th>
                            <th class="actions-col">Actions</th>
                        </tr>
                    </thead>
                    <tbody>
            `;

            files.forEach(f => {
                html += `
                    <tr>
                        <td>${f}</td>
                        <td class="actions-col">
                            <button class="neumorphic-btn-h" onclick="downloadFile('${f}')">⬇️ Download</button>
                            <button class="neumorphic-btn-h delete-btn" onclick="deleteFile('${f}')">🗑 Delete</button>
                        </td>
                    </tr>
                `;
            });

            html += "</tbody></table>";
            container.innerHTML = html;
        })
        .catch(() => {
            document.getElementById("fileListContainer").innerHTML =
                `<p class="error">Error fetching files.</p>`;
        });
}


// -----------------------------
// UPLOAD MULTIPLE FILES
// -----------------------------
function uploadFiles() {
    let input = document.getElementById("uploadInput");
    let files = input.files;

    if (!files.length) {
        showStatus("Please select at least one file.", "error");
        return;
    }

    let formData = new FormData();
    for (let f of files) {
        formData.append("files", f);
    }

    showStatus("Uploading…", "info");

    fetch("/upload_multiple_sqlite", {
        method: "POST",
        body: formData
    })
        .then(res => res.json())
        .then(data => {
            if (!data.success) {
                showStatus(data.error || "Upload failed.", "error");
                return;
            }

            showStatus(`${data.count} file(s) uploaded successfully.`, "success");

            input.value = "";
            loadFiles();
        })
        .catch(() => {
            showStatus("Upload error.", "error");
        });
}


// -----------------------------
// DELETE FILE
// -----------------------------
function deleteFile(filename) {
    if (!confirm(`Delete '${filename}'?`)) return;

    fetch("/delete_sqlite_file", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ filename })
    })
        .then(res => res.json())
        .then(data => {
            if (!data.success) {
                showStatus("Delete failed: " + data.error, "error");
                return;
            }

            showStatus(`Deleted ${filename}`, "success");
            loadFiles();
        });
}


// -----------------------------
// DOWNLOAD FILE
// -----------------------------
function downloadFile(filename) {
    window.location.href = `/download_sqlite_file/${filename}`;
}


// -----------------------------
// STATUS POPUP / TOAST
// -----------------------------
function showStatus(message, type = "info") {
    const box = document.getElementById("uploadStatus");
    box.className = "status-box " + type;
    box.innerText = message;

    box.style.opacity = "1";
    setTimeout(() => (box.style.opacity = "0"), 2500);
}