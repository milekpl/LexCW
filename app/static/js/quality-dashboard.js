(function () {
  'use strict';

  function esc(str) {
    if (str === null || str === undefined) return '';
    return String(str)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;')
      .replace(/'/g, '&#039;');
  }

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

  // ----- Redundant Examples -----
  const runExamplesBtn = document.getElementById('run-examples-btn');
  const examplesContent = document.getElementById('examples-content');
  const examplesProgress = document.getElementById('examples-progress');
  const examplesSummary = document.getElementById('examples-summary');

  if (runExamplesBtn) {
    function renderRedundantExamples(list) {
      if (list.length === 0) {
        examplesSummary.textContent = 'No redundant examples found';
        examplesContent.innerHTML = '<p class="text-muted small mb-0"><i class="fas fa-check-circle me-1"></i>No redundant examples detected.</p>';
        return;
      }

      examplesSummary.textContent = 'Found ' + list.length + ' redundant example(s)';

      var html = '<table class="table table-sm table-striped table-hover mb-0 small">';
      html += '<thead><tr><th>Phrase Subentry</th><th>Match %</th><th>Redundant Example Text</th><th>Actions</th></tr></thead><tbody>';
      for (var i = 0; i < list.length; i++) {
        var item = list[i];
        var dismissId = 'example-' + item.phrase_entry_id + '-' + item.example_entry_id;
        html += '<tr data-dismiss-id="' + dismissId + '">';
        
        // Phrase Subentry
        html += '<td>';
        if (item.phrase_url) {
          html += '<a href="' + item.phrase_url + '" class="text-decoration-none fw-semibold">' + item.phrase_headword + '</a>';
        } else {
          html += '<strong>' + item.phrase_headword + '</strong>';
        }
        html += ' <span class="badge bg-secondary">Phrase</span>';
        html += '</td>';

        // Match %
        html += '<td><span class="badge bg-warning text-dark">' + (item.similarity * 100).toFixed(0) + '%</span></td>';

        // Example Text
        html += '<td>';
        html += '<em>"' + item.example_text + '"</em>';
        html += '<div class="text-muted small mt-1">';
        html += 'Under entry: ';
        if (item.example_entry_url) {
          html += '<a href="' + item.example_entry_url + '" class="text-decoration-none text-muted fw-semibold">' + item.example_entry_headword + '</a>';
        } else {
          html += '<strong>' + item.example_entry_headword + '</strong>';
        }
        html += '</div>';
        html += '</td>';

        // Actions
        html += '<td>';
        html += '<button type="button" class="btn btn-outline-secondary btn-sm dismiss-example-btn" data-dismiss-id="' + dismissId + '"><i class="fas fa-eye-slash"></i> Dismiss</button>';
        html += '</td>';
        
        html += '</tr>';
      }
      html += '</tbody></table>';
      examplesContent.innerHTML = html;

      // Wire dismiss buttons
      examplesContent.querySelectorAll('.dismiss-example-btn').forEach(function (btn) {
        btn.addEventListener('click', function () {
          var dismissId = this.getAttribute('data-dismiss-id');
          var row = this.closest('tr');
          var dismissUrl = '/api/dashboard/duplicates/' + encodeURIComponent(dismissId) + '/dismiss' + (projectId ? '?project_id=' + encodeURIComponent(projectId) : '');
          fetch(dismissUrl, { method: 'POST', headers: {'X-CSRF-TOKEN': getCsrf()} })
            .then(function (r) { return r.json(); })
            .then(function (resp) {
              if (resp.success && row) {
                row.remove();
                if (examplesContent.querySelectorAll('tbody tr').length === 0) {
                  examplesSummary.textContent = 'No redundant examples found';
                  examplesContent.innerHTML = '<p class="text-muted small mb-0"><i class="fas fa-check-circle me-1"></i>No redundant examples detected.</p>';
                }
              }
            })
            .catch(function () {
              alert('Failed to dismiss redundant example.');
            });
        });
      });
    }

    runExamplesBtn.addEventListener('click', function () {
      runExamplesBtn.disabled = true;
      runExamplesBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Scanning...';
      if (examplesProgress) examplesProgress.classList.remove('d-none');
      examplesContent.innerHTML = '<p class="text-muted small mb-0"><i class="fas fa-spinner fa-spin"></i> Fetching phrases and examples...</p>';

      var qs = (projectId ? '?project_id=' + encodeURIComponent(projectId) : '');
      fetch('/api/dashboard/redundant-examples' + qs)
        .then(function (r) { return r.json(); })
        .then(function (resp) {
          if (resp.success && resp.data) {
            renderRedundantExamples(resp.data);
          } else {
            examplesContent.innerHTML = '<p class="text-danger small mb-0">' + (resp.error || 'Failed to complete scan') + '</p>';
          }
        })
        .catch(function () {
          examplesContent.innerHTML = '<p class="text-danger small mb-0">Network error while scanning examples.</p>';
        })
        .finally(function () {
          runExamplesBtn.disabled = false;
          runExamplesBtn.innerHTML = '<i class="fas fa-search"></i> Scan Examples';
          if (examplesProgress) examplesProgress.classList.add('d-none');
        });
    });
  }

  // ----- Data Anomalies & ML POS Coherence -----
  var anomaliesLoading = document.getElementById('anomalies-loading');
  if (anomaliesLoading) {
    fetch('/api/dashboard/anomalies')
      .then(function (r) { return r.json(); })
      .then(function (resp) {
        anomaliesLoading.style.display = 'none';
        if (!resp.success || !resp.anomalies) {
          var ncList = document.getElementById('non-canon-list');
          if (ncList) ncList.innerHTML = '<p class="text-danger small mb-0">Failed to load anomaly data.</p>';
          return;
        }

        var a = resp.anomalies;
        var s = resp.summary || {};

        // Non-canonical POS
        var ncCount = document.getElementById('non-canon-count');
        if (ncCount) ncCount.textContent = s.non_canonical_pos_count || 0;
        var ncList = document.getElementById('non-canon-list');
        if (ncList) {
          if (a.non_canonical_pos && a.non_canonical_pos.length > 0) {
            var ncHtml = '<ul class="list-unstyled mt-1 mb-0">';
            a.non_canonical_pos.slice(0, 10).forEach(function (item) {
              var eid = String(item.entry_id || '');
              var label = eid.length > 12 ? eid.substring(0, 12) + '…' : eid;
              ncHtml += '<li><a href="/entries/' + encodeURIComponent(eid) + '"><i class="fas fa-external-link-alt fa-xs me-1"></i>Entry ' + esc(label) + '</a>';
              ncHtml += ' <span class="badge bg-warning text-dark">' + esc(item.pos_value || '') + '</span>';
              if (item.suggested) {
                ncHtml += ' <i class="fas fa-arrow-right text-muted mx-1"></i><span class="badge bg-success">' + esc(item.suggested) + '</span>';
              }
              ncHtml += '</li>';
            });
            ncHtml += '</ul>';
            ncList.innerHTML = ncHtml;
          } else {
            ncList.innerHTML = '<p class="text-success small mb-0"><i class="fas fa-check-circle me-1"></i>All POS values are canonical.</p>';
          }
        }

        // ML POS Coherence Mismatches
        var misCount = document.getElementById('mismatch-count');
        if (misCount) misCount.textContent = s.pos_coherence_mismatch_count || 0;
        var misList = document.getElementById('mismatch-list');
        if (misList) {
          if (a.pos_coherence_mismatches && a.pos_coherence_mismatches.length > 0) {
            var mHtml = '<ul class="list-unstyled mt-1 mb-0">';
            a.pos_coherence_mismatches.slice(0, 10).forEach(function (item) {
              var eid = String(item.entry_id || '');
              var hw = String(item.headword || eid || 'entry');
              mHtml += '<li><a href="/entries/' + encodeURIComponent(eid) + '"><i class="fas fa-external-link-alt fa-xs me-1"></i>' + esc(hw) + '</a>';
              mHtml += ' <span class="badge bg-secondary">' + esc(item.actual_pos || '') + '</span>';
              mHtml += ' <i class="fas fa-arrow-right text-muted mx-1"></i><span class="badge bg-danger">' + esc(item.predicted_pos || '') + ' (' + Math.round((item.confidence || 0) * 100) + '%)</span>';
              mHtml += '</li>';
            });
            mHtml += '</ul>';
            misList.innerHTML = mHtml;
          } else {
            misList.innerHTML = '<p class="text-success small mb-0"><i class="fas fa-check-circle me-1"></i>No ML POS definition mismatches detected.</p>';
          }
        }
      })
      .catch(function (err) {
        console.error('Error loading anomalies:', err);
        if (anomaliesLoading) anomaliesLoading.style.display = 'none';
        var ncList = document.getElementById('non-canon-list');
        if (ncList) ncList.innerHTML = '<p class="text-danger small mb-0">Error loading anomaly data.</p>';
      });
  }
})();

