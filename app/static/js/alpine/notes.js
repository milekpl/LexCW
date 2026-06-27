/**
 * notes — Alpine.data component for entry notes section.
 *
 * Each note has a type (from server-provided note_types) and multilingual content.
 */

(function () {
  'use strict';

  document.addEventListener('alpine:init', function () {
    Alpine.data('notes', function (rawEntry) {
      var entry = (window.AlpineNormalize && window.AlpineNormalize.normalizeEntry)
        ? window.AlpineNormalize.normalizeEntry(rawEntry)
        : rawEntry;

      return {
        items: entry.notes || [],

        get languageOptions() {
          if (window.DictionaryApp && window.DictionaryApp.data && window.DictionaryApp.data.projectLanguages) {
            return window.DictionaryApp.data.projectLanguages.map(function (pair) {
              return { code: pair[0], label: String(pair[1]).replace(/<[^>]*>/g, '') };
            });
          }
          return [];
        },

        /** Note types from the server (injected via a data attribute or global) */
        get noteTypes() {
          // note_types is embedded in the page by the server
          return window.__noteTypes || [];
        },

        addItem: function () {
          this.items.push({
            id: (window.AlpineNormalize && window.AlpineNormalize.generateId)
              ? window.AlpineNormalize.generateId()
              : 'id-' + Date.now() + '-' + Math.random().toString(36).slice(2, 11),
            type: '',
            content: []
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
        }
      };
    });
  });
})();
