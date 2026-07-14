/**
 * pronunciation — Alpine.data component for the pronunciation section.
 *
 * Manages a list of pronunciation items, each with IPA, CV pattern, tone,
 * and a default checkbox. Audio handling stays in legacy code.
 *
 * IPA validation is wired via @input and @blur calling the existing
 * validateIpaField() from ipa-validation.js.
 */

(function () {
  'use strict';

  document.addEventListener('alpine:init', function () {
    Alpine.data('pronunciation', function (rawEntry) {
      var entry = (window.AlpineNormalize && window.AlpineNormalize.normalizeEntry)
        ? window.AlpineNormalize.normalizeEntry(rawEntry)
        : rawEntry;

      return {
        items: entry.pronunciations || [],

        get languageOptions() {
          if (window.DictionaryApp && window.DictionaryApp.data && window.DictionaryApp.data.projectLanguages) {
            return window.DictionaryApp.data.projectLanguages.map(function (pair) {
              var label = String(pair[1]).replace(/<[^>]*>/g, '');
              return { code: pair[0], label: label };
            });
          }
          return [];
        },

        addItem: function () {
          this.items.push({
            id: (window.AlpineNormalize && window.AlpineNormalize.generateId)
              ? window.AlpineNormalize.generateId()
              : 'id-' + Date.now() + '-' + Math.random().toString(36).slice(2, 11),
            value: '',
            type: 'seh-fonipa',
            audioPath: '',
            isDefault: this.items.length === 0,
            cvPattern: [],
            tone: [],
            _showExtras: false
          });
          // After Alpine renders the new item, attach IPA validation listeners
          var self = this;
          queueMicrotask(function () {
            if (typeof initializeIPAValidation === 'function') {
              initializeIPAValidation();
            }
          });
        },

        removeItem: function (id) {
          var idx = -1;
          for (var i = 0; i < this.items.length; i++) {
            if (this.items[i].id === id) { idx = i; break; }
          }
          if (idx !== -1) this.items.splice(idx, 1);
        },

        addRow: function (list) {
          var used = new Set(list.map(function (r) { return r.lang; }));
          var opts = this.languageOptions;
          var next = '';
          for (var i = 0; i < opts.length; i++) {
            if (!used.has(opts[i].code)) { next = opts[i].code; break; }
          }
          list.push({
            id: (window.AlpineNormalize && window.AlpineNormalize.generateId)
              ? window.AlpineNormalize.generateId()
              : 'id-' + Date.now() + '-' + Math.random().toString(36).slice(2, 11),
            lang: next,
            text: ''
          });
        },

        removeRow: function (list, id) {
          var idx = -1;
          for (var i = 0; i < list.length; i++) {
            if (list[i].id === id) { idx = i; break; }
          }
          if (idx !== -1) list.splice(idx, 1);
        },

        /**
         * Validate IPA on this input element (delegates to ipa-validation.js).
         */
        validateIpa: function (el) {
          if (typeof validateIpaField === 'function') {
            validateIpaField(el);
          }
        },

        /**
         * Predict IPA via ByT5 model. Calls /api/pronunciation/draft.
         */
        draftIpaBtn: null,

        predictIpa: function (idx) {
          if (this.draftIpaBtn) return; // already running
          var item = this.items[idx];
          if (!item) return;

          var headword = '';
          if (window.__entryData && window.__entryData.lexical_unit) {
            var lu = window.__entryData.lexical_unit;
            headword = lu.en || Object.values(lu)[0] || '';
          }
          if (!headword) {
            if (typeof showToast === 'function') {
              showToast('No headword available to predict IPA.', 'warning');
            }
            return;
          }

          var self = this;
          var btn = document.querySelector('[data-predict-ipa="' + idx + '"]');
          if (btn) {
            btn.disabled = true;
            btn.innerHTML = '<span class="spinner-border spinner-border-sm"></span>';
            self.draftIpaBtn = btn;
          }

          fetch('/api/pronunciation/draft', {
            method: 'POST',
            headers: {
              'Content-Type': 'application/json',
              'X-CSRF-TOKEN': document.querySelector('meta[name="csrf-token"]')?.getAttribute('content') || ''
            },
            body: JSON.stringify({ headword: headword, num_candidates: 1 })
          })
          .then(function (r) {
            // 401/403 never arrive here: auth.js rejects them centrally and sends
            // the user to log in. Anything else non-OK is a genuine draft failure.
            if (!r.ok) {
              throw new Error('Draft request failed (HTTP ' + r.status + ').');
            }
            return r.json();
          })
          .then(function (data) {
            if (data.available && data.candidates && data.candidates.length > 0) {
              item.value = data.candidates[0];
              // Trigger validation on the input
              var input = document.querySelector('.pronunciation-item[data-index="' + idx + '"] .ipa-input');
              if (input && typeof validateIpaField === 'function') {
                validateIpaField(input);
              }
              if (typeof showToast === 'function') {
                showToast('IPA drafted: ' + data.candidates[0], 'success');
              }
            } else {
              if (typeof showToast === 'function') {
                showToast('ByT5 model not available. Train and deploy one via Colab.', 'warning');
              }
            }
          })
          .catch(function (err) {
            if (typeof showToast === 'function') {
              showToast('Error drafting IPA: ' + err.message, 'error');
            }
          })
          .finally(function () {
            if (btn) {
              btn.disabled = false;
              btn.innerHTML = '<i class="fas fa-magic"></i>';
              self.draftIpaBtn = null;
            }
          });
        }
      };
    });
  });
})();
