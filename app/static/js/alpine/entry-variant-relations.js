/**
 * entryVariantRelations — Alpine.data component for entry-level variant relations (§16.2.3).
 *
 * Manages outgoing variant relations (this entry IS a variant of another entry).
 * Incoming variant relations (other entries ARE variants of this one) stay display-only.
 *
 * Each relation has variant_type (from variant-type range), ref (target entry ID),
 * type (always '_component-lexeme'), and order.
 */

(function () {
  'use strict';

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
      result.push({ value: v.id || v.value || '', label: label, key: result.length });
      if (v.children && v.children.length > 0) {
        result = result.concat(flattenRangeValues(v.children, level + 1));
      }
    });
    return result;
  }

  /**
   * Normalize a variant relation from the server shape to Alpine state.
   * Preserves variant_type, ref, type, order, traits.
   */
  function normalizeVariantRelation(raw) {
    if (!raw) raw = {};
    return {
      id: raw.id || (window.AlpineNormalize && window.AlpineNormalize.generateId
        ? window.AlpineNormalize.generateId()
        : 'id-' + Date.now() + '-' + Math.random().toString(36).slice(2, 11)),
      variant_type: raw.variant_type || raw.variantType || '',
      ref: raw.ref || '',
      type: raw.type || '_component-lexeme',
      order: raw.order !== undefined ? raw.order : 0,
      traits: raw.traits || {}
    };
  }

  document.addEventListener('alpine:init', function () {
    Alpine.data('entryVariantRelations', function (rawEntry) {
      var entry = (window.AlpineNormalize && window.AlpineNormalize.normalizeEntry)
        ? window.AlpineNormalize.normalizeEntry(rawEntry)
        : rawEntry;

      // Seed only outgoing variant relations (no direction = outgoing)
      var initialItems = [];
      if (entry.variantRelations && entry.variantRelations.length > 0) {
        entry.variantRelations.forEach(function (vr) {
          // Use direction if available; no-direction means outgoing
          var dir = vr.direction || 'outgoing';
          if (dir !== 'incoming') {
            initialItems.push(normalizeVariantRelation(vr));
          }
        });
      }

      return {
        items: initialItems,

        rangeData: {
          'variant-type': []
        },

        get variantTypeOptions() {
          return this.rangeData['variant-type'] || [];
        },

        init: function () {
          this.loadRanges();
        },

        loadRanges: async function () {
          var self = this;
          var loader = await this._whenRangesLoader();
          if (!loader) return;
          try {
            var data = await loader.loadRange('variant-type');
            if (data && data.values) {
              self.rangeData['variant-type'] = flattenRangeValues(data.values);
            }
          } catch (e) { console.warn('[entryVariantRelations] range load failed', e); }
        },

        _whenRangesLoader: function () {
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
            variant_type: '',
            ref: '',
            type: '_component-lexeme',
            order: this.items.length,
            traits: {}
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
