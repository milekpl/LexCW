(function () {
  'use strict';

  /* ---- DOM refs ---- */
  var container = document.querySelector('.container-fluid[data-project-id]');
  if (!container) return;

  var projectId = container.getAttribute('data-project-id') || '';

  var runBtn = document.getElementById('run-discovery-btn');
  var cancelBtn = document.getElementById('cancel-discovery-btn');
  var currentJobId = null;
  var thresholdInput = document.getElementById('discovery-threshold');
  var thresholdLabel = document.getElementById('discovery-threshold-label');
  var sampleSizeInput = document.getElementById('discovery-sample-size');
  var posInput = document.getElementById('discovery-pos');
  var scanModeInput = document.getElementById('discovery-scan-mode');
  var relationTypeInput = document.getElementById('discovery-relation-type');
  var progressEl = document.getElementById('discovery-progress');
  var summaryEl = document.getElementById('discovery-summary');
  var contentEl = document.getElementById('discovery-content');

  /* ---- Load lexical relation types from LIFT Ranges ---- */
  (function loadRelationTypes() {
    fetch('/api/ranges-editor/lexical-relation')
      .then(function (r) { return r.json(); })
      .then(function (resp) {
        if (!resp.success || !resp.data || !resp.data.values) return;
        var values = resp.data.values;
        relationTypeInput.innerHTML = '';
        values.forEach(function (v) {
          var opt = document.createElement('option');
          opt.value = v.id;
          var label = '';
          if (v.labels && v.labels.en) label = v.labels.en;
          else if (v.abbrev && v.abbrev.en) label = v.abbrev.en;
          else label = v.id;
          opt.textContent = label;
          if (v.id === 'synonym') opt.selected = true;
          relationTypeInput.appendChild(opt);
        });
      })
      .catch(function () {
        // Fallback: populate with common types
        ['synonym', 'antonym', 'hypernym', 'hyponym', 'compare'].forEach(function (id) {
          var opt = document.createElement('option');
          opt.value = id;
          opt.textContent = id;
          if (id === 'synonym') opt.selected = true;
          relationTypeInput.appendChild(opt);
        });
      });
  })();

  /* ---- Scan mode changes filter relation types ---- */
  if (scanModeInput && relationTypeInput) {
    scanModeInput.addEventListener('change', function () {
      if (this.value === 'subentry' || this.value === 'semantic_subentry') {
        relationTypeInput.value = '_component-lexeme';
        relationTypeInput.disabled = true;
      } else {
        relationTypeInput.disabled = false;
        // For trigram synonym mode, lock to 'synonym'
        if (this.value === 'synonym') {
          relationTypeInput.value = 'synonym';
          relationTypeInput.disabled = true;
        }
      }
    });
  }

  /* ---- Threshold slider live update ---- */
  if (thresholdInput && thresholdLabel) {
    thresholdInput.addEventListener('input', function () {
      thresholdLabel.textContent = this.value;
    });
  }

  /* ---- CSRF helper ---- */
  function getCsrf() {
    var meta = document.querySelector('meta[name="csrf-token"]');
    return meta ? meta.getAttribute('content') : '';
  }

  /* ---- Similarity CSS class ---- */
  function simClass(sim) {
    if (sim >= 0.7) return 'sim-high';
    if (sim >= 0.4) return 'sim-mid';
    return 'sim-low';
  }

  /* ---- Render candidate card ---- */
  function renderCandidate(c) {
    var sim = c.similarity || 0;
    var simLabel = (sim * 100).toFixed(0) + '%';
    var senseSim = c.sense_similarity;
    var level = c.level || 'entry';
    var levelLabel = level === 'sense' ? 'sense-level' : 'entry-level';
    var levelClass = level === 'sense' ? 'sim-high' : 'sim-mid';
    var linkedBadge = c.already_linked
      ? '<span class="linked-badge ms-2"><i class="fas fa-link"></i> Already linked</span>'
      : '';

    var senseInfo = '';
    if (typeof senseSim === 'number' && senseSim > 0) {
      senseInfo = '<span class="similarity-badge ' + simClass(senseSim) + ' ms-1" style="font-size:0.75rem;">sense ' + (senseSim * 100).toFixed(0) + '%</span>';
    }

    return (
      '<div class="card candidate-card" data-candidate-id="' + c.id + '">' +
        '<div class="card-header d-flex justify-content-between align-items-center">' +
          '<div>' +
            '<span class="similarity-badge ' + simClass(sim) + '">' + simLabel + '</span>' +
            senseInfo +
            '<span class="ms-2 small text-muted">' + c.relation_type + ' &middot; ' + levelLabel + '</span>' +
            linkedBadge +
          '</div>' +
          '<div>' +
            (c.already_linked
              ? ''
              : '<button type="button" class="btn btn-outline-success btn-sm create-relation-btn"' +
                ' data-source-id="' + c.source.entry_id + '"' +
                ' data-target-id="' + c.target.entry_id + '"' +
                ' data-relation-type="' + c.relation_type + '"' +
                ' data-level="' + level + '"' +
                ' data-complex-form-type="' + (c.complex_form_type || '') + '"' +
                ' data-source-sense-id="' + (c.source_sense_id || '') + '"' +
                ' data-target-sense-id="' + (c.target_sense_id || '') + '"' +
                '><i class="fas fa-plus-circle"></i> Create Relation</button>'
            ) +
          '</div>' +
        '</div>' +
        '<div class="card-body">' +
          '<div class="row">' +
            '<div class="col-md-6 entry-panel">' +
              '<div class="entry-hw">' +
                '<a href="' + (c.source.entry_url || '#') + '" target="_blank">' + escHtml(c.source.headword) + '</a>' +
                ' <span class="entry-pos">(' + escHtml(c.source.pos || '') + ')</span>' +
              '</div>' +
              (c.source.citation_form && c.source.citation_form !== c.source.headword
                ? '<div class="small text-muted">' + escHtml(c.source.citation_form) + '</div>'
                : '') +
              '<div class="entry-def">' + escHtml(truncate(c.source.definition || c.source.gloss || '', 200)) + '</div>' +
            '</div>' +
            '<div class="col-md-6 entry-panel">' +
              '<div class="entry-hw">' +
                '<a href="' + (c.target.entry_url || '#') + '" target="_blank">' + escHtml(c.target.headword) + '</a>' +
                ' <span class="entry-pos">(' + escHtml(c.target.pos || '') + ')</span>' +
              '</div>' +
              (c.target.citation_form && c.target.citation_form !== c.target.headword
                ? '<div class="small text-muted">' + escHtml(c.target.citation_form) + '</div>'
                : '') +
              '<div class="entry-def">' + escHtml(truncate(c.target.definition || c.target.gloss || '', 200)) + '</div>' +
            '</div>' +
          '</div>' +
        '</div>' +
      '</div>'
    );
  }

  /* ---- Helpers ---- */
  function escHtml(s) {
    if (!s) return '';
    var d = document.createElement('div');
    d.appendChild(document.createTextNode(s));
    return d.innerHTML;
  }

  function truncate(s, max) {
    if (!s || s.length <= max) return s || '';
    return s.substring(0, max) + '…';
  }

  /* ---- Render all candidates ---- */
  function renderCandidates(data) {
    if (!data || !data.candidates || data.candidates.length === 0) {
      contentEl.innerHTML = '<p class="text-muted small mb-0">No candidate pairs found. Try lowering the threshold or removing the POS filter.</p>';
      return;
    }
    var html = '<div id="candidates-list">';
    for (var i = 0; i < data.candidates.length; i++) {
      html += renderCandidate(data.candidates[i]);
    }
    html += '</div>';
    contentEl.innerHTML = html;
  }

  /* ---- Poll for job completion ---- */
  function pollJob(jobId) {
    fetch('/api/discovery/progress/' + encodeURIComponent(jobId))
      .then(function (r) { return r.json(); })
      .then(function (resp) {
        if (!resp.success) { finishScan(); return; }
        if (resp.done) {
          if (resp.phase === 'Cancelled') {
            contentEl.innerHTML = '<p class="text-muted small"><i class="fas fa-ban me-1"></i>Scan cancelled.</p>';
          } else if (resp.error) {
            contentEl.innerHTML = '<p class="text-danger">Scan failed: ' + escHtml(resp.error) + '</p>';
          } else if (resp.data) {
            renderCandidates(resp.data);
            if (summaryEl) {
              summaryEl.classList.remove('d-none');
              summaryEl.textContent = 'Found ' + resp.data.total_candidates + ' candidate pair' + (resp.data.total_candidates === 1 ? '' : 's') + ' from ' + resp.data.scanned_entries + ' entries' + (resp.data.sample_size ? ' (sample: ' + resp.data.sample_size + ')' : '');
            }
          }
          finishScan();
          return;
        }
        var phase = resp.phase || 'Scanning';
        var progressText;
        if (!resp.total || resp.total === 0) {
          progressText = phase;  // just the phase text, no "0 / 0" noise
        } else {
          progressText = phase + ' — ' + (resp.processed || 0) + ' / ' + resp.total;
        }
        contentEl.innerHTML = '<p class="text-muted small"><i class="fas fa-spinner fa-spin"></i> ' + escHtml(progressText) + '</p>';
        setTimeout(function () { pollJob(jobId); }, 1000);
      })
      .catch(function () {
        contentEl.innerHTML = '<p class="text-danger small">Network error while polling</p>';
        finishScan();
      });
  }

  function cancelDiscovery() {
    if (!currentJobId) return;
    var qs = projectId ? '?project_id=' + encodeURIComponent(projectId) : '';
    fetch('/api/discovery/scan/' + encodeURIComponent(currentJobId) + '/cancel' + qs, {
      method: 'POST',
      headers: {'X-CSRF-TOKEN': getCsrf()},
    }).then(function (r) { return r.json(); }).then(function (resp) {
      if (resp.success) {
        contentEl.innerHTML = '<p class="text-muted small"><i class="fas fa-spinner fa-spin"></i> Cancelling...</p>';
      }
    }).catch(function () {});
  }

  function finishScan() {
    if (runBtn) {
      runBtn.disabled = false;
      runBtn.innerHTML = '<i class="fas fa-search"></i> Find Relations';
    }
    currentJobId = null;
    if (cancelBtn) cancelBtn.classList.add('d-none');
    if (progressEl) {
      progressEl.classList.add('d-none');
      progressEl.textContent = '';
    }
  }

  /* ---- Start scan ---- */
  function runDiscovery() {
    var threshold = thresholdInput ? parseInt(thresholdInput.value, 10) : 2;
    var sampleSize = sampleSizeInput ? sampleSizeInput.value : '';
    var pos = posInput ? posInput.value : '';
    var scanMode = scanModeInput ? scanModeInput.value : 'synonym';
    var relationType = relationTypeInput ? relationTypeInput.value : scanMode;
    var qs = projectId ? '?project_id=' + encodeURIComponent(projectId) : '';

    if (runBtn) {
      runBtn.disabled = true;
      runBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Scanning...';
    }
    if (cancelBtn) cancelBtn.classList.remove('d-none');
    if (progressEl) {
      progressEl.classList.remove('d-none');
      progressEl.textContent = 'Starting…';
    }
    if (summaryEl) {
      summaryEl.classList.add('d-none');
    }
    contentEl.innerHTML = '<p class="text-muted small"><i class="fas fa-spinner fa-spin"></i> Starting scan…</p>';

    fetch('/api/discovery/scan' + qs, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', 'X-CSRF-TOKEN': getCsrf() },
      body: JSON.stringify({
        threshold: threshold,
        sample_size: sampleSize || null,
        pos: pos || null,
        relation_type: relationType,
        scan_mode: scanMode,
      }),
    })
      .then(function (r) { return r.json(); })
      .then(function (resp) {
        if (!resp.success || !resp.job_id) throw new Error(resp.error || 'Failed to start scan');
        currentJobId = resp.job_id;
        pollJob(resp.job_id);
      })
      .catch(function (err) {
        contentEl.innerHTML = '<p class="text-danger small mb-0">' + escHtml(err.message) + '</p>';
        finishScan();
      });
  }

  /* ---- Create relation ---- */
  function handleCreateRelation(e) {
    var btn = e.target.closest('.create-relation-btn');
    if (!btn) return;

    var sourceId = btn.getAttribute('data-source-id');
    var targetId = btn.getAttribute('data-target-id');
    var relationType = btn.getAttribute('data-relation-type') || 'synonym';
    var level = btn.getAttribute('data-level') || null;
    var complexFormType = btn.getAttribute('data-complex-form-type') || null;
    var sourceSenseId = btn.getAttribute('data-source-sense-id') || null;
    var targetSenseId = btn.getAttribute('data-target-sense-id') || null;
    var qs = projectId ? '?project_id=' + encodeURIComponent(projectId) : '';

    btn.disabled = true;
    btn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Creating\u2026';

    fetch('/api/discovery/relations' + qs, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', 'X-CSRF-TOKEN': getCsrf() },
      body: JSON.stringify({
        source_id: sourceId,
        target_id: targetId,
        relation_type: relationType,
        level: level,
        complex_form_type: complexFormType,
        source_sense_id: sourceSenseId,
        target_sense_id: targetSenseId,
      }),
    })
      .then(function (r) { return r.json(); })
      .then(function (resp) {
        if (resp.success) {
          var parent = btn.closest('.card-header');
          if (parent) {
            var actionsDiv = parent.querySelector('div:last-child');
            if (actionsDiv) {
              var lvlText = resp.level === 'sense' ? 'sense-level' : 'entry-level';
              actionsDiv.innerHTML = '<span class="linked-badge"><i class="fas fa-check-circle text-success"></i> Created (' + lvlText + ')</span>';
            }
          }
        } else {
          btn.disabled = false;
          btn.innerHTML = '<i class="fas fa-plus-circle"></i> Create Relation';
          alert('Failed: ' + (resp.error || 'Unknown error'));
        }
      })
      .catch(function (err) {
        btn.disabled = false;
        btn.innerHTML = '<i class="fas fa-plus-circle"></i> Create Relation';
        alert('Network error: ' + err.message);
      });
  }

  /* ---- Event listeners ---- */
  if (runBtn) {
    runBtn.addEventListener('click', runDiscovery);
  }
  if (cancelBtn) {
    cancelBtn.addEventListener('click', cancelDiscovery);
  }

  if (contentEl) {
    contentEl.addEventListener('click', handleCreateRelation);
  }
})();
