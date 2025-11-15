document.addEventListener("DOMContentLoaded", () => {

    loadFileList();

    // -------- Upload Handler --------
    const uploadArea = document.getElementById("uploadArea");
    const fileInput = document.getElementById("fileInput");

    uploadArea.addEventListener("click", () => fileInput.click());

    fileInput.addEventListener("change", () => {
        uploadFiles(fileInput.files);
    });

    uploadArea.addEventListener("dragover", (e) => {
        e.preventDefault();
        uploadArea.classList.add("drag-over");
    });

    uploadArea.addEventListener("dragleave", () => {
        uploadArea.classList.remove("drag-over");
    });

    uploadArea.addEventListener("drop", (e) => {
        e.preventDefault();
        uploadArea.classList.remove("drag-over");
        uploadFiles(e.dataTransfer.files);
    });
});

// ----------------------
// Load Existing Files
// ----------------------

function loadFileList() {
    fetch("/api/list_files")
        .then(r => r.json())
        .then(res => {
            if (!res.success) return;

            const list = document.getElementById("filesList");
            list.innerHTML = "";

            res.files.forEach(f => {
                const item = document.createElement("div");
                item.className = "file-item";

                item.innerHTML = `
                    <div>
                        <strong>${f.name}</strong><br>
                        Size: ${formatBytes(f.size)}<br>
                        Uploaded: ${formatDate(f.updated)}
                    </div>
                    <div class="file-actions">
                        <button class="set-active-btn" onclick="setActive('${f.name}')">Set Active</button>
                        <button class="download-btn" onclick="downloadFile('${f.name}')">Download</button>
                        <button class="delete-btn" onclick="deleteFile('${f.name}')">Delete</button>
                    </div>
                `;

                list.appendChild(item);
            });
        });
}

// ----------------------
// File Upload
// ----------------------

function uploadFiles(files) {
    [...files].forEach(file => {
        const form = new FormData();
        form.append("file", file);

        fetch("/upload_sqlite", {
            method: "POST",
            body: form
        })
        .then(r => r.json())
        .then(() => loadFileList());
    });
}

// ----------------------
// Set Active
// ----------------------

function setActive(filename) {
    fetch("/api/set_active", {
        method: "POST",
        headers: {"Content-Type": "application/json"},
        body: JSON.stringify({ filename })
    })
    .then(r => r.json())
    .then(res => {
        if (res.success) showMessage("Active file changed.");
        else showMessage("Failed to set active file.");
    });
}

// ----------------------
// Download
// ----------------------

function downloadFile(filename) {
    window.location.href = `/api/download_file/${filename}`;
}

// ----------------------
// Delete
// ----------------------

function deleteFile(filename) {
    fetch(`/api/delete_file/${filename}`, {
        method: "DELETE"
    })
    .then(r => r.json())
    .then(res => {
        if (res.success) {
            showMessage("Deleted successfully.");
            loadFileList();
        } else {
            showMessage("Delete failed.");
        }
    });
}

// ----------------------
// Helpers
// ----------------------

function formatBytes(b) {
    if (!b) return "0 B";
    const u = ["B","KB","MB","GB"];
    let i = Math.floor(Math.log(b)/Math.log(1024));
    return (b / Math.pow(1024, i)).toFixed(2) + " " + u[i];
}

function formatDate(dt) {
    return dt ? dt.replace("T", " ").split(".")[0] : "Unknown";
}

function showMessage(msg) {
    alert(msg);
}