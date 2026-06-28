/**
 * entryAnnotations — Alpine.data component for entry-level annotations (§16.2).
 *
 * Each annotation has name, value, who, when, and multilingual content forms.
 * No seeding — annotations are optional.
 */

(function () {
  'use strict';

  document.addEventListener('alpine:init', function () {
    Alpine.data('entryAnnotations', function (rawEntry) {
      var entry = (window.AlpineNormalize && window.AlpineNormalize.normalizeEntry)
        ? window.AlpineNormalize.normalizeEntry(rawEntry)
        : rawEntry;

      return {
        items: entry.annotations || [],

        // Project language options for content-form language selects
        languageOptions: [],

        init: function () {
          this._loadLanguageOptions();
        },

        _loadLanguageOptions: function () {
          var self = this;
          try {
            var appData = window.DictionaryApp && window.DictionaryApp.data;
            if (appData && appData.projectLanguages) {
              self.languageOptions = appData.projectLanguages.map(function (pl) {
                return { code: pl[0], label: pl[1] };
              });
            }
          } catch (e) { /* ignore */ }
        },

        addItem: function () {
          this.items.push({
            id: (window.AlpineNormalize && window.AlpineNormalize.generateId)
              ? window.AlpineNormalize.generateId()
              : 'id-' + Date.now() + '-' + Math.random().toString(36).slice(2, 11),
            name: '',
            value: '',
            who: '',
            when: '',
            content: {},
            contentForms: []
          });
        },

        removeItem: function (id) {
          var idx = -1;
          for (var i = 0; i < this.items.length; i++) {
            if (this.items[i].id === id) { idx = i; break; }
          }
          if (idx !== -1) this.items.splice(idx, 1);
        },

        // --- Multilingual content row management ---

        addContentRow: function (ann) {
          if (!ann.contentForms) ann.contentForms = [];
          var used = new Set(ann.contentForms.map(function (r) { return r.lang; }));
          var opts = this.languageOptions;
          var next = '';
          for (var i = 0; i < opts.length; i++) {
            if (!used.has(opts[i].code)) { next = opts[i].code; break; }
          }
          ann.contentForms.push({
            id: (window.AlpineNormalize && window.AlpineNormalize.generateId)
              ? window.AlpineNormalize.generateId()
              : 'id-' + Date.now() + '-' + Math.random().toString(36).slice(2, 11),
            lang: next,
            text: ''
          });
        },

        removeContentRow: function (ann, rowId) {
          if (!ann.contentForms) return;
          var idx = -1;
          for (var i = 0; i < ann.contentForms.length; i++) {
            if (ann.contentForms[i].id === rowId) { idx = i; break; }
          }
          if (idx !== -1) ann.contentForms.splice(idx, 1);
        }
      };
    });
  });
})();
