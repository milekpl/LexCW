/**
 * etymology — Alpine.data component for the etymology section (§13).
 *
 * Manages a list of etymology items, each with type, source language,
 * multilingual form and gloss fields.
 *
 * The type dropdown uses plain <select x-model> + x-for options from
 * reactive rangeData (Stage-1.5 pattern, no Select2).
 */

(function () {
  'use strict';

  /**
   * Flatten a hierarchical range value tree into a flat options array.
   */
  function flattenRangeValues(values, level) {
    if (!Array.isArray(values)) return [];
    level = level || 0;
    var result = [];
    values.forEach(function (v) {
      var label = v.effective_label || v.value || v.id || v.name || '';
      if (level > 0) {
        label = '\u00A0\u00A0'.repeat(level) + label;
      }
      result.push({ value: v.id || v.value || '', label: label });
      if (v.children && v.children.length > 0) {
        result = result.concat(flattenRangeValues(v.children, level + 1));
      }
    });
    return result;
  }

  document.addEventListener('alpine:init', function () {
    Alpine.data('etymology', function (rawEntry) {
      var entry = (window.AlpineNormalize && window.AlpineNormalize.normalizeEntry)
        ? window.AlpineNormalize.normalizeEntry(rawEntry)
        : rawEntry;

      return {
        items: entry.etymologies || [],

        // Range data loaded async (type dropdown)
        rangeData: { 'etymology': [] },

        get etymologyTypeOptions() {
          return this.rangeData['etymology'] || [];
        },

        get languageOptions() {
          var options = [];
          if (window.DictionaryApp && window.DictionaryApp.data && window.DictionaryApp.data.projectLanguages) {
            options = window.DictionaryApp.data.projectLanguages.map(function (pair) {
              var label = String(pair[1]).replace(/<[^>]*>/g, '');
              return { code: pair[0], label: label };
            });
          }
          // Always expose a standard IPA writing-system option for etymology forms.
          if (!options.some(function (opt) { return opt.code === 'seh-fonipa'; })) {
            options.push({ code: 'seh-fonipa', label: 'IPA' });
          }
          return options;
        },

        getLanguageSelectOptions: function (currentLang) {
          var options = this.languageOptions.slice();
          if (currentLang && !options.some(function (opt) { return opt.code === currentLang; })) {
            options.unshift({ code: currentLang, label: currentLang });
          }
          return options;
        },

        /**
         * Load etymology range types asynchronously.
         */
        init: function () {
          this.loadRanges();
        },

        loadRanges: async function () {
          var self = this;
          var loader = await this._whenRangesLoader();
          if (!loader) return;
          try {
            var data = await loader.loadRange('etymology');
            if (data && data.values) {
              // Unique key per option — duplicate `value`s in a flattened range break
              // Alpine x-for keyed on opt.value (see sense-tree.js loadRanges).
              self.rangeData['etymology'] = flattenRangeValues(data.values).map(function (o, i) {
                o.key = i;
                return o;
              });
            }
          } catch (e) {
            console.warn('[etymology] range load failed', e);
          }
        },

        _whenRangesLoader: function () {
          return new Promise(function (resolve) {
            if (window.rangesLoader && window.rangesLoader.loadRange) {
              return resolve(window.rangesLoader);
            }
            var n = 0;
            var t = setInterval(function () {
              if (window.rangesLoader && window.rangesLoader.loadRange) {
                clearInterval(t);
                resolve(window.rangesLoader);
              } else if (++n > 50) {
                clearInterval(t);
                resolve(null);
              }
            }, 100);
          });
        },

        addItem: function () {
          this.items.push({
            id: (window.AlpineNormalize && window.AlpineNormalize.generateId)
              ? window.AlpineNormalize.generateId()
              : 'id-' + Date.now() + '-' + Math.random().toString(36).slice(2, 11),
            type: '',
            source: '',
            formForms: [],
            glossForms: [],
            protoform: '',
            comment: ''
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
         * Return true when a language code represents an IPA writing system.
         */
        isIpaLanguage: function (langCode) {
          if (!langCode) return false;
          var normalized = String(langCode).toLowerCase();
          return normalized.indexOf('fonipa') !== -1 || normalized.indexOf('ipa') !== -1;
        },

        /**
         * Validate an etymology form value as IPA only for IPA language rows.
         */
        validateFormIpa: function (el, langCode) {
          if (!el) return;
          if (!this.isIpaLanguage(langCode)) {
            el.classList.remove('is-invalid', 'is-valid');
            return;
          }
          if (typeof validateIpaField === 'function') {
            validateIpaField(el);
          }
        },

        onFormLanguageChange: function (selectEl, langCode) {
          if (!selectEl || !selectEl.closest) return;
          var row = selectEl.closest('.etymology-form-lang-row');
          if (!row) return;
          var input = row.querySelector('.etymology-form-text-input');
          this.validateFormIpa(input, langCode);
        }
      };
    });
  });
})();
