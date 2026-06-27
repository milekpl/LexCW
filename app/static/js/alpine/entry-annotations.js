/**
 * entryAnnotations — Alpine.data component for entry-level annotations (§16.2).
 *
 * Each annotation has name, value, who, when, and a content object.
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

        init: function () {
          // No seeding — annotations are optional.
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
            content: {}
          });
        },

        removeItem: function (id) {
          var idx = -1;
          for (var i = 0; i < this.items.length; i++) {
            if (this.items[i].id === id) { idx = i; break; }
          }
          if (idx !== -1) this.items.splice(idx, 1);
        }
      };
    });
  });
})();
