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
            tone: []
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
        }
      };
    });
  });
})();
