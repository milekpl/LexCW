(function () {
  'use strict';

  // ----- Refresh button -----
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

  // ----- Data Composition -----
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
  if (loadingEl) {
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
  }

  // ----- Duplicate Detection -----
  var runBtn = document.getElementById('run-detection-btn');
  if (!runBtn) return;

  var cancelBtn = document.getElementById('cancel-scan-btn');
  var currentJobId = null;
  var dashboardRoot = document.querySelector('[data-project-id]');
  var projectId = dashboardRoot ? dashboardRoot.getAttribute('data-project-id') : '';
  var dupContent = document.getElementById('duplicates-content');
  var dupSummary = document.getElementById('duplicates-summary');
  var thresholdInput = document.getElementById('dup-threshold');
  var thresholdVal = document.getElementById('dup-threshold-val');
  var sampleSizeInput = document.getElementById('dup-sample-size');
  var duplicatesProgress = document.getElementById('duplicates-progress');

  function getActiveMode() {
    var active = document.querySelector('#dup-mode-pills .active');
    return active ? active.getAttribute('data-mode') : 'all';
  }

  // Threshold slider display
  if (thresholdInput && thresholdVal) {
    thresholdInput.addEventListener('input', function () {
      thresholdVal.textContent = this.value;
    });
  }

  // Mode pills
  document.querySelectorAll('#dup-mode-pills .btn').forEach(function (btn) {
    btn.addEventListener('click', function () {
      document.querySelectorAll('#dup-mode-pills .btn').forEach(function (b) {
        b.classList.remove('active');
      });
      this.classList.add('active');
    });
  });

   function renderDuplicateGroups(data) {
    var groups = data.groups || [];
    if (groups.length === 0) {
      dupSummary.textContent = 'No duplicates found';
      dupContent.innerHTML = '<p class="text-muted small mb-0"><i class="fas fa-check-circle me-1"></i>No potential duplicates detected.</p>';
      return;
    }

    dupSummary.textContent = 'Found ' + groups.length + ' potential duplicate group(s)';

    var html = '';
    for (var i = 0; i < groups.length; i++) {
      var g = groups[i];
      var confidenceClass = g.confidence >= 0.9 ? 'bg-success' : g.confidence >= 0.7 ? 'bg-warning text-dark' : 'bg-danger';
      var modeBadge = ' <span class="badge bg-secondary">' + g.mode + '</span>';

      html += '<div class="card mb-2 border" data-group-id="' + g.id + '">';
      html += '<div class="card-body py-2 px-3">';
      html += '<div class="d-flex justify-content-between align-items-center mb-1">';
      html += '<div>';
      html += '<span class="badge ' + confidenceClass + ' me-1">' + (g.confidence * 100).toFixed(0) + '%</span>';
      html += modeBadge;
      html += ' <small class="text-muted">' + g.merge_suggestion + '</small>';
      html += '</div>';
      html += '<div>';
      html += '<button type="button" class="btn btn-outline-success btn-sm merge-btn me-1" data-entry-id="' + (g.entries && g.entries[0] ? g.entries[0].entry_id : '') + '" data-group-id="' + g.id + '"><i class="fas fa-compress-alt"></i> Merge</button>';
      html += '<button type="button" class="btn btn-outline-secondary btn-sm dismiss-btn" data-group-id="' + g.id + '"><i class="fas fa-eye-slash"></i> Dismiss</button>';
      html += '</div>';
      html += '</div>';

      html += '<table class="table table-sm table-borderless mb-0 small">';
      html += '<thead><tr><th>Entry</th><th>POS</th><th>Definition / Gloss</th></tr></thead><tbody>';
      for (var j = 0; j < g.entries.length; j++) {
        var e = g.entries[j];
        html += '<tr>';
        html += '<td>';
        if (e.entry_url) {
          html += '<a href="' + e.entry_url + '" class="text-decoration-none fw-semibold">' + e.headword + '</a>';
        } else {
          html += '<strong>' + e.headword + '</strong>';
        }
        if (e.pronunciation) {
          html += '<div class="text-muted small"><em>' + e.pronunciation + '</em></div>';
        }
        html += '</td>';
        html += '<td>' + (e.pos || '-') + '</td>';
        html += '<td>';
        if (e.definition) html += '<div class="small">' + e.definition + '</div>';
        if (e.gloss) html += '<div class="text-muted small"><em>' + e.gloss + '</em></div>';
        if (!e.definition && !e.gloss) html += '<span class="text-muted small">—</span>';
        html += '</td>';
        html += '</tr>';
      }
      html += '</tbody></table>';
      html += '</div></div>';
    }

    dupContent.innerHTML = html;

    // Wire dismiss buttons
    dupContent.querySelectorAll('.dismiss-btn').forEach(function (btn) {
      btn.addEventListener('click', function () {
        var groupId = this.getAttribute('data-group-id');
        var card = this.closest('[data-group-id]');
        var dismissUrl = '/api/dashboard/duplicates/' + encodeURIComponent(groupId) + '/dismiss' + (projectId ? '?project_id=' + encodeURIComponent(projectId) : '');
        fetch(dismissUrl, { method: 'POST' })
          .then(function (r) { return r.json(); })
          .then(function (resp) {
            if (resp.success && card) {
              card.style.transition = 'opacity 0.3s';
              card.style.opacity = '0';
              setTimeout(function () { card.remove(); }, 300);
            }
          })
          .catch(function () {
            alert('Failed to dismiss group.');
          });
      });
    });

    // Wire merge buttons using the existing merge/search flow
    dupContent.querySelectorAll('.merge-btn').forEach(function (btn) {
      btn.addEventListener('click', function () {
        var entryId = this.getAttribute('data-entry-id');
        if (entryId && window.openMergeEntrySearch) {
          window.openMergeEntrySearch(entryId);
          return;
        }
        alert('Could not open the merge dialog for this group.');
      });
    });
  }

  function getCsrf() {
    var meta = document.querySelector('meta[name="csrf-token"]');
    return meta ? meta.getAttribute('content') : '';
  }

  function runDetection() {
    var mode = getActiveMode();
    var threshold = thresholdInput ? thresholdInput.value : 1;
    var sampleSize = sampleSizeInput ? sampleSizeInput.value : '';
    var qs = (projectId ? '?project_id=' + encodeURIComponent(projectId) : '');

    runBtn.disabled = true;
    runBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Scanning...';
    if (cancelBtn) cancelBtn.classList.remove('d-none');
    if (duplicatesProgress) duplicatesProgress.classList.remove('d-none');
    dupContent.innerHTML = '<p class="text-muted small mb-0"><i class="fas fa-spinner fa-spin"></i> Starting scan...</p>';

    fetch('/api/dashboard/duplicates/scan' + qs, {
      method: 'POST',
      headers: {'Content-Type': 'application/json', 'X-CSRF-TOKEN': getCsrf()},
      body: JSON.stringify({mode: mode, threshold: threshold, sample_size: sampleSize || null}),
    })
      .then(function (r) { return r.json(); })
      .then(function (resp) {
        if (!resp.success || !resp.job_id) {
          throw new Error(resp.error || 'Failed to start scan');
        }
        currentJobId = resp.job_id;
        pollJob(resp.job_id);
      })
      .catch(function (err) {
        dupContent.innerHTML = '<p class="text-danger small mb-0">' + err.message + '</p>';
        finishScan();
      });
  }

  function pollJob(jobId) {
    fetch('/api/dashboard/duplicates/progress/' + encodeURIComponent(jobId))
      .then(function (r) { return r.json(); })
      .then(function (resp) {
        if (!resp.success) {
          dupContent.innerHTML = '<p class="text-danger small mb-0">' + (resp.error || 'Polling failed') + '</p>';
          finishScan();
          return;
        }
        if (resp.done) {
          if (resp.phase === 'Cancelled') {
            dupContent.innerHTML = '<p class="text-muted small mb-0"><i class="fas fa-ban me-1"></i>Scan cancelled.</p>';
          } else if (resp.error) {
            dupContent.innerHTML = '<p class="text-danger small mb-0">Scan failed: ' + resp.error + '</p>';
          } else if (resp.data) {
            renderDuplicateGroups(resp.data);
          }
          finishScan();
          return;
        }
        var total = resp.total || 0;
        var processed = resp.processed || 0;
        var phase = resp.phase || 'Scanning';
        var progressText = phase;
        if (total > 0) {
          var pct = Math.round((processed / total) * 100);
          progressText += ' - ' + processed + ' / ' + total + ' (' + pct + '%)';
        }
        if (duplicatesProgress) duplicatesProgress.textContent = progressText;
        dupContent.innerHTML = '<p class="text-muted small mb-0"><i class="fas fa-spinner fa-spin"></i> ' + progressText + '</p>';
        setTimeout(function () { pollJob(jobId); }, 1000);
      })
      .catch(function () {
        dupContent.innerHTML = '<p class="text-danger small mb-0">Network error while polling progress.</p>';
        finishScan();
      });
  }

  function cancelScan() {
    if (!currentJobId) return;
    var qs = projectId ? '?project_id=' + encodeURIComponent(projectId) : '';
    fetch('/api/dashboard/duplicates/scan/' + encodeURIComponent(currentJobId) + '/cancel' + qs, {
      method: 'POST',
      headers: {'X-CSRF-TOKEN': getCsrf()},
    }).then(function (r) { return r.json(); }).then(function (resp) {
      if (resp.success) {
        dupContent.innerHTML = '<p class="text-muted small mb-0"><i class="fas fa-spinner fa-spin"></i> Cancelling...</p>';
      }
    }).catch(function () {});
  }

  function finishScan() {
    runBtn.disabled = false;
    runBtn.innerHTML = '<i class="fas fa-search"></i> Run Detection';
    currentJobId = null;
    if (cancelBtn) cancelBtn.classList.add('d-none');
    if (duplicatesProgress) {
      duplicatesProgress.classList.add('d-none');
      duplicatesProgress.textContent = '';
    }
  }

  runBtn.addEventListener('click', runDetection);
  if (cancelBtn) cancelBtn.addEventListener('click', cancelScan);
})();
