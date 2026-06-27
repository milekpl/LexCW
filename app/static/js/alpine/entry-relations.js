/**
 * entryRelations — Alpine.data component for entry-level semantic relations (§16.2.2).
 *
 * Each relation has type (from lexical-relation range) and ref (target entry ID).
 * Pattern follows senseTree.addRelation/removeRelation.
 * No seeding — relations are optional.
 */

(function () {
  'use strict';

  /**
   * Flatten a hierarchical range value tree into a flat options array.
   * (Duplicated from sense-tree.js; shared helper TBD post-migration.)
   */
  function pickLabel(labels) {
    if (!labels || typeof labels !== 'object') return '';
    var prefLang = '';
    try {
      var form = document.getElementById('entry-form');
      if (form) prefLang = form.dataset.sourceLanguage || '';
    } catch (e) { /* ignore */ }
    if (prefLang && labels[prefLang]) return labels[prefLang];
    if (labels.en) return labels.en;
    var keys = Object.keys(labels);
    if (keys.length > 0) return labels[keys[0]];
    return '';
  }

  function flattenRangeValues(values, level) {
    if (!Array.isArray(values)) return [];
    level = level || 0;
    var result = [];
    values.forEach(function (v) {
      var explicitLabel = pickLabel(v.labels);
      var label = explicitLabel || v.effective_label || v.value || v.id || v.name || '';
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
    Alpine.data('entryRelations', function (rawEntry) {
      var entry = (window.AlpineNormalize && window.AlpineNormalize.normalizeEntry)
        ? window.AlpineNormalize.normalizeEntry(rawEntry)
        : rawEntry;

      return {
        items: entry.relations || [],

        // Range data loaded async (populated in init())
        rangeData: {
          'lexical-relation': []
        },

        get relationTypeOptions() {
          return this.rangeData['lexical-relation'] || [];
        },

        init: function () {
          this.loadRanges();
        },

        loadRanges: async function () {
          var self = this;
          var loader = await this._whenRangesLoader();
          if (!loader) return;
          var ids = ['lexical-relation'];
          await Promise.all(ids.map(async function (id) {
            try {
              var data = await loader.loadRange(id);
              if (data && data.values) {
                self.rangeData[id] = flattenRangeValues(data.values).map(function (o, i) {
                  o.key = i;
                  return o;
                });
              }
            } catch (e) { console.warn('[entryRelations] range load failed', id, e); }
          }));
        },

        _whenRangesLoader: function () {
          var self = this;
          return new Promise(function (resolve) {
            if (window.rangesLoader) return resolve(window.rangesLoader);
            var maxAttempts = 20;
            var interval = 100;
            var attempts = 0;
            var timer = setInterval(function () {
              attempts++;
              if (window.rangesLoader) {
                clearInterval(timer);
                return resolve(window.rangesLoader);
              }
              if (attempts >= maxAttempts) {
                clearInterval(timer);
                return resolve(null);
              }
            }, interval);
          });
        },

        addItem: function () {
          this.items.push({
            id: (window.AlpineNormalize && window.AlpineNormalize.generateId)
              ? window.AlpineNormalize.generateId()
              : 'id-' + Date.now() + '-' + Math.random().toString(36).slice(2, 11),
            type: '',
            ref: '',
            order: this.items.length
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
