/**
 * lexicalUnit — Alpine.data component for the lexical-unit (headword) forms section.
 *
 * Follows the same pattern as senseTree: arrays-of-objects with stable ids,
 * mutations via Alpine-scope methods, no _x_dataStack access.
 *
 * Registered as Alpine.data('lexicalUnit', ...) on alpine:init.
 */

(function () {
  'use strict';

  document.addEventListener('alpine:init', function () {
    Alpine.data('lexicalUnit', function (rawEntry) {
      var entry = (window.AlpineNormalize && window.AlpineNormalize.normalizeEntry)
        ? window.AlpineNormalize.normalizeEntry(rawEntry)
        : rawEntry;

      return {
        // The lexical-unit forms array (reactive)
        forms: entry.lexicalUnitForms || [],

        // Seed an empty row for new entries so the headword field is usable.
        init: function () {
          if (this.forms.length === 0) {
            this.addRow();
          }
        },

        // Language options for <select> dropdowns
        get languageOptions() {
          if (window.DictionaryApp && window.DictionaryApp.data && window.DictionaryApp.data.projectLanguages) {
            return window.DictionaryApp.data.projectLanguages.map(function (pair) {
              // Strip HTML tags from labels (projectLanguages may have styled labels)
              var label = String(pair[1]).replace(/<[^>]*>/g, '');
              return { code: pair[0], label: label };
            });
          }
          return [];
        },

        /**
         * Add a new language form row.
         */
        addRow: function () {
          var used = new Set(this.forms.map(function (r) { return r.lang; }));
          var opts = this.languageOptions;
          var next = '';
          for (var i = 0; i < opts.length; i++) {
            if (!used.has(opts[i].code)) {
              next = opts[i].code;
              break;
            }
          }
          this.forms.push({
            id: (window.AlpineNormalize && window.AlpineNormalize.generateId)
              ? window.AlpineNormalize.generateId()
              : 'id-' + Date.now() + '-' + Math.random().toString(36).slice(2, 11),
            lang: next,
            text: ''
          });
        },

        /**
         * Remove a language form row by id.
         */
        removeRow: function (id) {
          var idx = -1;
          for (var i = 0; i < this.forms.length; i++) {
            if (this.forms[i].id === id) {
              idx = i;
              break;
            }
          }
          if (idx !== -1) {
            this.forms.splice(idx, 1);
          }
        }
      };
    });
  });
})();
