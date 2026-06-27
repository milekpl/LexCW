(function () {
  'use strict';

  const refreshBtn = document.getElementById('refresh-quality-btn');
  if (!refreshBtn) return;

  refreshBtn.addEventListener('click', function () {
    const icon = this.querySelector('.fas');
    if (icon) icon.classList.add('fa-spin');

    fetch('/api/dashboard/quality')
      .then(function (r) { return r.json(); })
      .then(function (resp) {
        if (resp.success && resp.data) {
          location.reload();
        } else {
          alert('Failed to refresh quality metrics.');
        }
      })
      .catch(function () {
        alert('Network error while refreshing quality metrics.');
      })
      .finally(function () {
        if (icon) icon.classList.remove('fa-spin');
      });
  });
})();