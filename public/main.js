document.addEventListener("DOMContentLoaded", () => {
     // BLAST Tool Form Submission
    const blastForm = document.getElementById("blast-upload-form");
    blastForm.addEventListener("submit", async (e) => {
        e.preventDefault();
        const blastFile = document.getElementById("blast-file").files[0];
        const message = document.getElementById("blast-message");
        
        if (!blastFile) {
            message.textContent = "Please upload a BLAST file.";
            return;
        }
        
        const formData = new FormData();
        formData.append("file", blastFile);

        try {
            const response = await fetch("/upload", {
                method: "POST",
                body: formData
            });
            const result = await response.json();
            message.textContent = result.message;
        } catch (error) {
            message.textContent = "An error occurred during file upload.";
        }
    });

    // Heatmap Tool Form Submission
    const heatmapForm = document.getElementById("heatmap-upload-form");
    heatmapForm.addEventListener("submit", async (e) => {
        e.preventDefault();
        const heatmapFile = document.getElementById("heatmap-file").files[0];
        const message = document.getElementById("heatmap-message");

        if (!heatmapFile) {
            message.textContent = "Please upload a dataset.";
            return;
        }

        const formData = new FormData();
        formData.append("file", heatmapFile);

        try {
            const response = await fetch("/upload", {
                method: "POST",
                body: formData
            });
            const result = await response.json();
            message.textContent = result.message;
        } catch (error) {
            message.textContent = "An error occurred during file upload.";
        }
    });
    });
    