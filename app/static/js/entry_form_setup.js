document.addEventListener('DOMContentLoaded', function() {
    // getCsrfToken() is provided by api-utils.js (loaded before this file)

    const btn = document.getElementById('install-recommended-ranges-btn');
    if (btn) {
        btn.addEventListener('click', async function() {
            try {
                btn.disabled = true;
                const csrfToken = getCsrfToken();
                const headers = {};
                if (csrfToken) {
                    headers['X-CSRF-TOKEN'] = csrfToken;
                }
                const resp = await fetch('/api/ranges-editor/install_recommended', { method: 'POST', headers: headers });
                const data = await resp.json();
                if (resp.ok && data.success) {
                    // Reload page to populate selects
                    window.location.reload();
                } else {
                    showToast('Failed to install recommended ranges: ' + (data.error || 'unknown'), 'error');
                    btn.disabled = false;
                }
            } catch (err) {
                Logger.error('Failed to install recommended ranges:', err);
                showToast('Failed to install recommended ranges: ' + err, 'error');
                btn.disabled = false;
            }
        });
    }
});
