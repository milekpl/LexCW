/**
 * entryMeta — Alpine.data component that owns entry-level scalar fields.
 *
 * Manages:
 *   - grammaticalInfo (entry POS, range-backed)
 *   - morphType (range-backed)
 *   - citation (single source-language citation text)
 *   - status (range-backed; persists as an entry-level `<trait name="status">`)
 *
 * Design pattern follows §11.2 (range-select): rangeData loaded async in init(),
 * rendered via x-for + x-model, keyed on :key="opt.key" (NEVER opt.value — duplicates
 * in hierarchical ranges silently break x-for when keyed on value).
 *
 * The adapter (alpine-to-serializer.js lines 222-223) already reads
 * state.grammaticalInfo → grammatical_info and state.morphType → morph_type.
 * This component's sectionReader exposes them as { grammaticalInfo, morphType }
 * under stateKey 'entryMeta'; the adapter merges them in alpineStateToSerializerInput.
 */

(function () {
  'use strict';

  /**
   * Pick the best human-readable label from a labels dict (multilingual).
   * Mirrors the same helper in sense-tree.js.
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

  /**
   * Flatten a hierarchical range value tree into a flat options array.
   * Mirrors the same helper in sense-tree.js.
   */
  function flattenRangeValues(values, level) {
    if (!Array.isArray(values)) return [];
    level = level || 0;
    var result = [];
    values.forEach(function (v) {
      var explicitLabel = pickLabel(v.labels);
      var label = explicitLabel || v.effective_label || v.value || v.id || v.name || '';
      if (level > 0) {
        label = '  '.repeat(level) + label;
      }
      result.push({ value: v.id || v.value || '', label: label });
      if (v.children && v.children.length > 0) {
        result = result.concat(flattenRangeValues(v.children, level + 1));
      }
    });
    return result;
  }

  document.addEventListener('alpine:init', function () {
    Alpine.data('entryMeta', function (rawEntry) {
      var entry = (window.AlpineNormalize && window.AlpineNormalize.normalizeEntry)
        ? window.AlpineNormalize.normalizeEntry(rawEntry)
        : rawEntry;

      return {
        // --- Reactive state ---
        grammaticalInfo: entry.grammaticalInfo || '',
        morphType: entry.morphType || '',
        citation: entry.citation || '',
        status: entry.status || '',

        // Range data loaded async in init()
        rangeData: {
          'grammatical-info': [],
          'morph-type': [],
          'status': []
        },
        rangesLoaded: false,

        // Range-derived option lists
        get grammaticalInfoOptions() {
          return this.rangeData['grammatical-info'] || [];
        },
        get morphTypeOptions() {
          return this.rangeData['morph-type'] || [];
        },
        get statusOptions() {
          return this.rangeData['status'] || [];
        },

        /**
         * Serialized getter — exposes the data this component owns for the
         * merge harness sectionReader (dataKey: 'serialized').
         * Returns the shape the adapter expects:
         * { grammaticalInfo, morphType, citation, status }.
         */
        get serialized() {
          return {
            grammaticalInfo: this.grammaticalInfo,
            morphType: this.morphType,
            citation: this.citation,
            status: this.status
          };
        },

        init: function () {
          this.loadRanges();
        },

        /**
         * Load range data for grammatical-info and morph-type.
         * Async — called from init(). Populates reactive rangeData.
         * Keyed with .key (index) so x-for never sees duplicate keys even in
         * hierarchical ranges that repeat the same value under different parents.
         */
        loadRanges: async function () {
          var self = this;
          var loader = await this._whenRangesLoader();
          if (!loader) return;
          var ids = ['grammatical-info', 'morph-type', 'status'];
          await Promise.all(ids.map(async function (id) {
            try {
              var data = await loader.loadRange(id);
              if (data && data.values) {
                self.rangeData[id] = flattenRangeValues(data.values).map(function (o, i) {
                  o.key = i;
                  return o;
                });
              }
            } catch (e) {
              console.warn('[entryMeta] range load failed', id, e);
            }
          }));
          self.rangesLoaded = true;
        },

        /**
         * Bounded one-shot wait for the rangesLoader global (mirrors sense-tree.js).
         */
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
                resolve(null); // ~5s cap
              }
            }, 100);
          });
        }
      };
    });
  });
})();
