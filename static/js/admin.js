(function() {
    const uploadForm = document.getElementById('upload-form');
    const reindexAllBtn = document.getElementById('reindex-all-btn');
    const refreshQuestionsBtn = document.getElementById('refresh-questions-btn');

    if (uploadForm) {
        uploadForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            const fileInput = document.getElementById('file-input');
            const file = fileInput.files[0];
            if (!file) return;

            const formData = new FormData();
            formData.append('file', file);

            try {
                const res = await fetch('/api/upload', {
                    method: 'POST',
                    headers: { 'X-CSRFToken': CSRF_TOKEN },
                    body: formData,
                });
                const data = await res.json();
                if (data.status === 'indexed') {
                    alert(`Indexed: ${data.filename} (${data.chunks} chunks)`);
                    location.reload();
                } else {
                    alert(`Error: ${data.error || 'Upload failed'}`);
                }
            } catch (err) {
                alert('Upload failed');
            }
        });
    }

    if (reindexAllBtn) {
        reindexAllBtn.addEventListener('click', async () => {
            reindexAllBtn.disabled = true;
            reindexAllBtn.textContent = 'Reindexing...';
            try {
                const res = await fetch('/admin/api/reindex-all', {
                    method: 'POST',
                    headers: { 'X-CSRFToken': CSRF_TOKEN },
                });
                const data = await res.json();
                alert(`Reindexed ${data.results.length} documents`);
                location.reload();
            } catch (err) {
                alert('Reindex failed');
            } finally {
                reindexAllBtn.disabled = false;
                reindexAllBtn.textContent = 'Reindex All Documents';
            }
        });
    }

    if (refreshQuestionsBtn) {
        refreshQuestionsBtn.addEventListener('click', async () => {
            try {
                await fetch('/api/suggested-questions/refresh', {
                    method: 'POST',
                    headers: { 'X-CSRFToken': CSRF_TOKEN },
                });
                alert('Questions refreshed');
            } catch (err) {
                alert('Failed to refresh questions');
            }
        });
    }

    window.reindexDoc = async function(filename) {
        try {
            const res = await fetch(`/admin/api/documents/${encodeURIComponent(filename)}/reindex`, {
                method: 'POST',
                headers: { 'X-CSRFToken': CSRF_TOKEN },
            });
            const data = await res.json();
            if (data.status === 'indexed') {
                alert(`Reindexed: ${data.chunks} chunks`);
                location.reload();
            } else {
                alert(`Error: ${data.error || 'Reindex failed'}`);
            }
        } catch (err) {
            alert('Reindex failed');
        }
    };

    window.deleteDoc = async function(filename) {
        if (!confirm(`Delete "${filename}" from the vector store?`)) return;
        try {
            const res = await fetch(`/admin/api/documents/${encodeURIComponent(filename)}`, {
                method: 'DELETE',
                headers: { 'X-CSRFToken': CSRF_TOKEN },
            });
            const data = await res.json();
            alert(`Removed ${data.removed_chunks} chunks`);
            location.reload();
        } catch (err) {
            alert('Delete failed');
        }
    };
})();
