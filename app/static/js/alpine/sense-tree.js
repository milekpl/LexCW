/**
 * senseTree — Alpine.data component that owns the ENTIRE sense tree (§10).
 *
 * One component owns: senses → definition, gloss, examples → translations,
 * subsenses, grammatical-info, domain-type, semantic-domain, usage-type,
 * sense note, literal meaning, exemplar, scientific name.
 *
 * Design rules (§10.3):
 *   1. Every collection is an array of objects with a stable `id`.
 *   2. Mutate via component methods in Alpine's scope (this.addRow/removeRow).
 *   3. Never touch _x_dataStack or manually Alpine.reactive().
 *   4. SortableJS onEnd → splice the Alpine array; Alpine re-renders.
 *   5. Ranges loaded async in init() → stored as reactive data → rendered as <option>s.
 */

(function () {
  'use strict';

  /**
   * Flatten a hierarchical range value tree into a flat options array.
   * For non-hierarchical ranges, each value becomes one option.
   * For hierarchical ranges, children are indented and nested via level.
   */
  /**
   * Pick the best human-readable label from a labels dict (multilingual).
   * Prefer the project's source language, then 'en', then the first available.
   */
  function pickLabel(labels) {
    if (!labels || typeof labels !== 'object') return '';
    // Prefer the project's source language
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
      // Label resolution chain (matches lift_parser.py resolve_range_labels):
      //   1. labels dict (multilingual) — "Living things"
      //   2. effective_label (computed: label || value || id)
      //   3. value — "1.2.3"
      //   4. id — GUID
      //   5. name — fallback
      var explicitLabel = pickLabel(v.labels);
      var label = explicitLabel || v.effective_label || v.value || v.id || v.name || '';
      if (level > 0) {
        label = '\u00A0\u00A0'.repeat(level) + label;
      }
      // Value: use id (matching populateSelect's valueField default)
      result.push({ value: v.id || v.value || '', label: label });
      if (v.children && v.children.length > 0) {
        result = result.concat(flattenRangeValues(v.children, level + 1));
      }
    });
    return result;
  }

  document.addEventListener('alpine:init', function () {
    Alpine.data('senseTree', function (rawEntry) {
      var entry = (window.AlpineNormalize && window.AlpineNormalize.normalizeEntry)
        ? window.AlpineNormalize.normalizeEntry(rawEntry)
        : rawEntry;

      return {
        // --- Reactive state ---
        senses: entry.senses || [],

        // Range data loaded async (populated in init())
        rangeData: {
          'grammatical-info': [],
          'domain-type': [],
          'semantic-domain-ddp4': [],
          'usage-type': [],
          'lexical-relation': []
        },
        rangesLoaded: false,

        // Language options for <select> dropdowns
        get languageOptions() {
          if (window.DictionaryApp && window.DictionaryApp.data && window.DictionaryApp.data.projectLanguages) {
            return window.DictionaryApp.data.projectLanguages.map(function (pair) {
              var label = String(pair[1]).replace(/<[^>]*>/g, '');
              return { code: pair[0], label: label };
            });
          }
          return [];
        },

        // Range-derived option lists
        get grammaticalInfoOptions() {
          return this.rangeData['grammatical-info'] || [];
        },
        get domainTypeOptions() {
          return this.rangeData['domain-type'] || [];
        },
        get semanticDomainOptions() {
          return this.rangeData['semantic-domain-ddp4'] || [];
        },
        get usageTypeOptions() {
          return this.rangeData['usage-type'] || [];
        },
        get relationTypeOptions() {
          return this.rangeData['lexical-relation'] || [];
        },

        /**
         * Alpine init() — seed empty sense, load ranges async, setup SortableJS.
         */
        init: function () {
          // Seed an empty sense ONLY for a brand-new entry (the add page renders
          // Entry(id_="")). Existing entries are shown as-is — a variant entry legitimately
          // has NO sense (it is just a headword + a relation), and forcing an empty,
          // definition-required sense onto it breaks its save/preview.
          if (this.senses.length === 0 && !entry.id) {
            this.addSense();
          }
          this.loadRanges();      // async; x-for fills options when rangeData arrives
          this.setupSortable();
        },

        /**
         * Load range data for all sense-level range-backed selects.
         * Async — called from init(), populates reactive rangeData.
         * No polling, no populateSelect, no Select2. Options rendered via x-for.
         */
        loadRanges: async function () {
          var self = this;
          var loader = await this._whenRangesLoader();   // wait for the global script (R5 guard)
          if (!loader) return;
          var ids = ['grammatical-info','domain-type','semantic-domain-ddp4','usage-type','lexical-relation'];
          await Promise.all(ids.map(async function (id) {
            try {
              var data = await loader.loadRange(id);
              if (data && data.values) {
                // Assign a unique `key` per option. Range hierarchies can flatten to
                // duplicate `value`s (e.g. a POS value repeated under several parents);
                // Alpine x-for refuses to render a list with duplicate :key, so keying on
                // opt.value silently drops the whole list. Index keys are safe here: the
                // list is replaced wholesale and the <option>s carry no input state.
                self.rangeData[id] = flattenRangeValues(data.values).map(function (o, i) {
                  o.key = i;
                  return o;
                });
              }
            } catch (e) { console.warn('[senseTree] range load failed', id, e); }
          }));
        },

        /**
         * Bounded one-shot wait for the rangesLoader global (NOT per-render polling —
         * this is the allowed R5 "guard a global is ready" case, runs once at init).
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
                resolve(null);   // ~5s cap
              }
            }, 100);
          });
        },

        setupSortable: function () {
          var self = this;
          var container = this.$el.querySelector('#senses-container');
          if (container && typeof Sortable !== 'undefined') {
            Sortable.create(container, {
              handle: '.drag-handle',
              animation: 150,
              onEnd: function (evt) {
                self.reorderSenses(evt.oldIndex, evt.newIndex);
              }
            });
          }
        },

        // --- Multilingual list helpers ---

        // The project's source language (or 'en'), used to seed new rows.
        defaultLang: function () {
          var lang = '';
          try {
            var form = document.getElementById('entry-form');
            if (form) lang = form.dataset.sourceLanguage || '';
          } catch (e) { /* ignore */ }
          return lang || 'en';
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

        // --- Sense management ---

        addSense: function () {
          var newSense = {
            id: (window.AlpineNormalize && window.AlpineNormalize.generateId)
              ? window.AlpineNormalize.generateId()
              : 'id-' + Date.now() + '-' + Math.random().toString(36).slice(2, 11),
            definitionForms: [],
            glossForms: [],
            examples: [],
            subsenses: [],
            grammaticalInfo: '',
            domainType: [],
            usageType: [],
            semanticDomains: [],
            notes: {},
            relations: [],
            variantRelations: [],
            annotations: [],
            reversals: [],
            exemplar: null,
            scientificName: null,
            literalMeaning: null,
            illustrations: [],
            // Multilingual simple fields
            noteForms: [],
            literalMeaningForms: [],
            exemplarForms: [],
            scientificNameForms: []
          };

          var sourceLang = '';
          try {
            var form = document.getElementById('entry-form');
            if (form) sourceLang = form.dataset.sourceLanguage || '';
          } catch (e) { /* ignore */ }
          if (!sourceLang) sourceLang = 'en';

          newSense.definitionForms.push({
            id: (window.AlpineNormalize && window.AlpineNormalize.generateId)
              ? window.AlpineNormalize.generateId()
              : 'id-' + Date.now() + '-' + Math.random().toString(36).slice(2, 11),
            lang: sourceLang,
            text: ''
          });

          this.senses.push(newSense);
          // Options are reactive from rangeData; new senses get them automatically via x-for.
        },

        removeSense: function (id) {
          var idx = -1;
          for (var i = 0; i < this.senses.length; i++) {
            if (this.senses[i].id === id) { idx = i; break; }
          }
          if (idx !== -1) this.senses.splice(idx, 1);
        },

        reorderSenses: function (oldIndex, newIndex) {
          var item = this.senses.splice(oldIndex, 1)[0];
          this.senses.splice(newIndex, 0, item);
        },

        // --- Example management ---

        addExample: function (sense) {
          if (!sense.examples) sense.examples = [];
          var ex = {
            id: (window.AlpineNormalize && window.AlpineNormalize.generateId)
              ? window.AlpineNormalize.generateId()
              : 'id-' + Date.now() + '-' + Math.random().toString(36).slice(2, 11),
            sentence: '',
            sentenceLang: this.defaultLang(),
            translations: [],
            translationType: '',
            reference: '',
            source: '',
            note: ''
          };
          sense.examples.push(ex);
          // Seed one translation row so the field is visible and usable.
          this.addTranslation(ex);
        },

        removeExample: function (sense, exampleId) {
          if (!sense.examples) return;
          var idx = -1;
          for (var i = 0; i < sense.examples.length; i++) {
            if (sense.examples[i].id === exampleId) { idx = i; break; }
          }
          if (idx !== -1) sense.examples.splice(idx, 1);
        },

        // --- Translation management ---

        addTranslation: function (example) {
          if (!example.translations) example.translations = [];
          var used = new Set(example.translations.map(function (r) { return r.lang; }));
          var opts = this.languageOptions;
          var next = '';
          for (var i = 0; i < opts.length; i++) {
            if (!used.has(opts[i].code)) { next = opts[i].code; break; }
          }
          example.translations.push({
            id: (window.AlpineNormalize && window.AlpineNormalize.generateId)
              ? window.AlpineNormalize.generateId()
              : 'id-' + Date.now() + '-' + Math.random().toString(36).slice(2, 11),
            lang: next,
            text: ''
          });
        },

        removeTranslation: function (example, transId) {
          if (!example.translations) return;
          var idx = -1;
          for (var i = 0; i < example.translations.length; i++) {
            if (example.translations[i].id === transId) { idx = i; break; }
          }
          if (idx !== -1) example.translations.splice(idx, 1);
        },

        // --- Subsense management ---

        addSubsense: function (sense) {
          if (!sense.subsenses) sense.subsenses = [];
          var sourceLang = '';
          try {
            var form = document.getElementById('entry-form');
            if (form) sourceLang = form.dataset.sourceLanguage || '';
          } catch (e) { /* ignore */ }
          if (!sourceLang) sourceLang = 'en';

          sense.subsenses.push({
            id: (window.AlpineNormalize && window.AlpineNormalize.generateId)
              ? window.AlpineNormalize.generateId()
              : 'id-' + Date.now() + '-' + Math.random().toString(36).slice(2, 11),
            definitionForms: [{
              id: (window.AlpineNormalize && window.AlpineNormalize.generateId)
                ? window.AlpineNormalize.generateId()
                : 'id-' + Date.now() + '-' + Math.random().toString(36).slice(2, 11),
              lang: sourceLang,
              text: ''
            }],
            glossForms: [],
            examples: [],
            subsenses: [],
            grammaticalInfo: '',
            notes: {},
            noteForms: []
          });
        },

        // --- Sense relation management ---

        addRelation: function (sense) {
          if (!sense.relations) sense.relations = [];
          sense.relations.push({
            id: (window.AlpineNormalize && window.AlpineNormalize.generateId)
              ? window.AlpineNormalize.generateId()
              : 'id-' + Date.now() + '-' + Math.random().toString(36).slice(2, 11),
            type: '',
            ref: '',
            order: sense.relations.length
          });
        },

        removeRelation: function (sense, relId) {
          if (!sense.relations) return;
          var idx = -1;
          for (var i = 0; i < sense.relations.length; i++) {
            if (sense.relations[i].id === relId) { idx = i; break; }
          }
          if (idx !== -1) sense.relations.splice(idx, 1);
        },

        // --- Reversal helpers (§16.1) ---

        addReversal: function (sense) {
          if (!sense.reversals) sense.reversals = [];
          sense.reversals.push({
            id: (window.AlpineNormalize && window.AlpineNormalize.generateId)
              ? window.AlpineNormalize.generateId()
              : 'id-' + Date.now() + '-' + Math.random().toString(36).slice(2, 11),
            type: '',
            forms: {},
            main: null
          });
        },

        removeReversal: function (sense, revId) {
          if (!sense.reversals) return;
          var idx = -1;
          for (var i = 0; i < sense.reversals.length; i++) {
            if (sense.reversals[i].id === revId) { idx = i; break; }
          }
          if (idx !== -1) sense.reversals.splice(idx, 1);
        },

        // --- Illustration helpers (§16.1) ---

        addIllustration: function (sense) {
          if (!sense.illustrations) sense.illustrations = [];
          sense.illustrations.push({
            id: (window.AlpineNormalize && window.AlpineNormalize.generateId)
              ? window.AlpineNormalize.generateId()
              : 'id-' + Date.now() + '-' + Math.random().toString(36).slice(2, 11),
            href: '',
            label: {}
          });
        },

        removeIllustration: function (sense, illId) {
          if (!sense.illustrations) return;
          var idx = -1;
          for (var i = 0; i < sense.illustrations.length; i++) {
            if (sense.illustrations[i].id === illId) { idx = i; break; }
          }
          if (idx !== -1) sense.illustrations.splice(idx, 1);
        },

        removeSubsense: function (sense, subsenseId) {
          if (!sense.subsenses) return;
          var idx = -1;
          for (var i = 0; i < sense.subsenses.length; i++) {
            if (sense.subsenses[i].id === subsenseId) { idx = i; break; }
          }
          if (idx !== -1) sense.subsenses.splice(idx, 1);
        },

        /**
         * Propagate entry-level POS to senses that don't have a POS set.
         * Called by entry-form.js when the entry-level #part-of-speech changes.
         * Only overwrites senses whose grammaticalInfo is empty (preserves existing sense POS).
         */
        applyEntryPos: function (value) {
          if (!value) return;
          var senses = this.senses;
          for (var i = 0; i < senses.length; i++) {
            if (!senses[i].grammaticalInfo || senses[i].grammaticalInfo.trim() === '') {
              senses[i].grammaticalInfo = value;
            }
          }
        }
      };
    });
  });
})();
