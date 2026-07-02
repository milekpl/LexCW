(function () {
  'use strict';

  const refreshBtn = document.getElementById('refresh-quality-btn');
  if (refreshBtn) {
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
  }

  // --- Data Composition ---
  function renderPie(data) {
    const total = Object.values(data).reduce(function (a, b) { return a + b; }, 0);
    if (total === 0) return '<p class="text-muted">No data</p>';

    const colors = ['#0d6efd', '#198038', '#b35c00', '#a2191f', '#6f42c1', '#20c997', '#fd7e14', '#d63384', '#0dcaf0'];
    var i = 0;
    var html = '<div style="display:flex;flex-wrap:wrap;gap:0.25rem 1rem;">';
    for (var key in data) {
      var pct = ((data[key] / total) * 100).toFixed(1);
      var color = colors[i % colors.length];
      html += '<div style="display:flex;align-items:center;gap:0.35rem;min-width:8rem;">';
      html += '<span style="display:inline-block;width:0.75rem;height:0.75rem;background:' + color + ';border-radius:50%;"></span>';
      html += '<span><strong>' + key + '</strong> ' + data[key] + ' (' + pct + '%)</span>';
      html += '</div>';
      i++;
    }
    html += '</div>';
    return html;
  }

  function renderFieldCoverage(data) {
    var html = '';
    for (var key in data) {
      var item = data[key];
      var pct = item.pct;
      var barColor = pct >= 90 ? '#198038' : pct >= 70 ? '#b35c00' : '#a2191f';
      html += '<div class="mb-2">';
      html += '<div style="display:flex;justify-content:space-between;font-size:0.85rem;">';
      html += '<span>' + key + '</span>';
      html += '<span>' + item.count + ' (' + pct + '%)</span>';
      html += '</div>';
      html += '<div style="background:#e9ecef;border-radius:0.25rem;overflow:hidden;">';
      html += '<div class="progress-field" style="width:' + Math.max(pct, 2) + '%;background:' + barColor + ';"></div>';
      html += '</div>';
      html += '</div>';
    }
    return html;
  }

  function renderHistogram(data, maxLabel) {
    var maxCount = 0;
    for (var i = 0; i < data.length; i++) {
      if (data[i].count > maxCount) maxCount = data[i].count;
    }
    if (maxCount === 0) return '<p class="text-muted">No data</p>';

    var html = '';
    for (var i = 0; i < data.length; i++) {
      var item = data[i];
      var pct = maxCount > 0 ? (item.count / maxCount) * 100 : 0;
      html += '<div class="histogram-bar">';
      html += '<span class="label">' + item.bucket + '</span>';
      html += '<div class="bar" style="width:' + Math.max(pct, 2) + '%"></div>';
      html += '<span class="count">' + item.count + '</span>';
      html += '</div>';
    }
    return html;
  }

  var loadingEl = document.getElementById('composition-loading');
  if (!loadingEl) return;

  fetch('/api/dashboard/composition')
    .then(function (r) { return r.json(); })
    .then(function (resp) {
      loadingEl.style.display = 'none';
      if (!resp.success || !resp.data) return;

      var data = resp.data;

      var posEl = document.getElementById('pos-chart');
      if (posEl) posEl.innerHTML = renderPie(data.pos_distribution);

      var fieldEl = document.getElementById('field-coverage');
      if (fieldEl) fieldEl.innerHTML = renderFieldCoverage(data.field_coverage);

      var sensesEl = document.getElementById('senses-histogram');
      if (sensesEl) sensesEl.innerHTML = renderHistogram(data.senses_per_entry, 'Senses');

      var exEl = document.getElementById('examples-histogram');
      if (exEl) exEl.innerHTML = renderHistogram(data.examples_per_sense, 'Examples');
    })
    .catch(function () {
      loadingEl.textContent = 'Failed to load composition data.';
    });
})();