document.addEventListener('DOMContentLoaded', function() {
    const btn = document.getElementById('install-recommended-ranges-btn');
    if (btn) {
        btn.addEventListener('click', async function() {
            try {
                btn.disabled = true;
                const resp = await fetch('/api/ranges/install_recommended', { method: 'POST' });
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
