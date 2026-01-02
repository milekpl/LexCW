document.addEventListener('DOMContentLoaded', function() {
    // Helper function to get CSRF token
    function getCsrfToken() {
        return document.querySelector('meta[name="csrf-token"]')?.getAttribute('content') || '';
    }

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
                    alert('Failed to install recommended ranges: ' + (data.error || 'unknown'));
                    btn.disabled = false;
                }
            } catch (err) {
                alert('Failed to install recommended ranges: ' + err);
                btn.disabled = false;
            }
        });
    }
});
