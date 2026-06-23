// Shared fallback upload handlers. Each tool page also has its own inline
// script; these handlers only attach when their form actually exists on the
// page, so loading main.js everywhere never throws.
document.addEventListener("DOMContentLoaded", () => {
    async function uploadFile(file, messageEl) {
        if (!file) {
            if (messageEl) messageEl.textContent = "Please choose a file.";
            return;
        }
        const formData = new FormData();
        formData.append("file", file);
        try {
            const response = await fetch("/upload", { method: "POST", body: formData });
            const result = await response.json();
            if (messageEl) messageEl.textContent = result.message;
        } catch (error) {
            if (messageEl) messageEl.textContent = "An error occurred during file upload.";
            console.error(error);
        }
    }

    const blastForm = document.getElementById("blast-upload-form");
    if (blastForm && !blastForm.dataset.handled) {
        blastForm.addEventListener("submit", (e) => {
            e.preventDefault();
            const file = document.getElementById("blast-file")?.files[0];
            uploadFile(file, document.getElementById("upload-message"));
        });
    }

    const heatmapForm = document.getElementById("heatmap-upload-form");
    if (heatmapForm && !heatmapForm.dataset.handled) {
        heatmapForm.addEventListener("submit", (e) => {
            e.preventDefault();
            const file = document.getElementById("heatmap-file")?.files[0];
            uploadFile(file, document.getElementById("heatmap-message"));
        });
    }
});
