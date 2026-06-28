/**
 * merge-harness.js — TEMPORARY scaffolding (deleted in Stage 3, §4.3, §8 item 1).
 *
 * During migration, submit, auto-save, and live-preview must serialize through ONE function
 * that merges legacy-DOM-serialized sections + Alpine-serialized sections into the
 * serializer's input contract.
 *
 * Every stage moves one subtree from the "legacy" half to the "Alpine" half of this merge.
 * Once all sections are Alpine-owned, the merge harness has nothing left to merge and is deleted.
 *
 * Usage:
 *   const merged = await MergeHarness.merge(formElement, alpineState);
 *   // merged is the serializer-input-ready object
 */

(function () {
  'use strict';

  var MergeHarness = {
    /**
     * Sections currently owned by Alpine (populated per stage).
     * Stage 0: none (empty)
     * Stage 1: ['senses']
     * Stage 2: ['senses', 'lexical_unit', 'pronunciations', ...]
     */
    alpineSections: [],

    /**
     * Merge legacy DOM state + Alpine state into one serializer input.
     *
     * @param {HTMLFormElement} form - The entry form element
     * @param {Object} alpineState - The Alpine reactive state (extracted via Alpine.raw() + structuredClone)
     * @returns {Promise<Object>} Merged object ready for serializeEntry()
     */
    merge: async function (form, alpineState) {
      // 1. Serialize the legacy DOM (sections not yet migrated)
      var legacyData = {};
      if (window.FormSerializer && window.FormSerializer.serializeFormToJSONSafe) {
        try {
          legacyData = await window.FormSerializer.serializeFormToJSONSafe(form, {
            includeEmpty: false
          });
        } catch (e) {
          console.warn('[MergeHarness] Legacy serialization failed:', e);
          legacyData = {};
        }
      }

      // 2. Convert Alpine state to serializer input
      var alpineData = {};
      if (alpineState && window.AlpineAdapter && window.AlpineAdapter.alpineStateToSerializerInput) {
        alpineData = window.AlpineAdapter.alpineStateToSerializerInput(alpineState);
      }

      // 3. Merge: Alpine sections override legacy sections
      var merged = this._deepMerge(legacyData, alpineData, this.alpineSections);

      // 4. Ensure id is present
      if (!merged.id) {
        merged.id = legacyData.id || alpineData.id || '';
      }

      return merged;
    },

    /**
     * Synchronous merge (for cases where async isn't needed).
     */
    mergeSync: function (legacyData, alpineState) {
      var alpineData = {};
      if (alpineState && window.AlpineAdapter && window.AlpineAdapter.alpineStateToSerializerInput) {
        alpineData = window.AlpineAdapter.alpineStateToSerializerInput(alpineState);
      }

      var merged = this._deepMerge(legacyData || {}, alpineData, this.alpineSections);

      if (!merged.id) {
        merged.id = (legacyData && legacyData.id) || (alpineData && alpineData.id) || '';
      }

      return merged;
    },

    /**
     * Deep merge alpine data into legacy data, but ONLY for sections listed in alpineSections.
     * For alpine-owned sections, Alpine data completely replaces legacy data.
     * For legacy sections, legacy data is kept as-is.
     */
    _deepMerge: function (legacy, alpine, alpineSections) {
      var result = {};

      // Copy all legacy keys
      for (var key in legacy) {
        if (legacy.hasOwnProperty(key)) {
          result[key] = legacy[key];
        }
      }

      // Override ONLY the registered Alpine-owned sections.
      // (The adapter emits a full entry skeleton; copying its non-registered keys would
      //  inject empty sections like lexicalUnit:{} and clobber populated legacy data.)
      for (var i = 0; i < alpineSections.length; i++) {
        var section = alpineSections[i];
        if (alpine.hasOwnProperty(section)) {
          result[section] = alpine[section];
        }
      }

      return result;
    },

    /**
     * Map of Alpine-owned serializer sections → how to read them from the live DOM.
     *   selector: the component's x-data root
     *   dataKey:  the reactive property on that component holding the section data
     *   stateKey: the key to expose on the extracted state (what the adapter reads)
     *
     * Stage 1 migrates only `senses`. Stage 2 sections (lexical_unit, pronunciations,
     * notes) add entries here once their components are name-free and adapter-keyed.
     */
    sectionReaders: [
      { selector: '[x-data^="senseTree"]',     dataKey: 'senses', stateKey: 'senses' },          // Stage 1
      { selector: '[x-data^="lexicalUnit"]',   dataKey: 'forms',  stateKey: 'lexicalUnitForms' }, // Stage 2.1
      { selector: '[x-data^="notes"]',         dataKey: 'items',  stateKey: 'notes' },            // Stage 2.2
      { selector: '[x-data^="pronunciation"]', dataKey: 'items',  stateKey: 'pronunciations' },   // Stage 2.3
      { selector: '[x-data^="etymology"]',     dataKey: 'items',  stateKey: 'etymologies' },      // Stage 3
      { selector: '[x-data^="entryAnnotations"]', dataKey: 'items',  stateKey: 'annotations' },   // §16.2
      { selector: '[x-data^="entryRelations"]',  dataKey: 'items',  stateKey: 'relations' },      // §16.2.2
      { selector: '[x-data^="entryVariantRelations"]', dataKey: 'items',  stateKey: 'variantRelations' }, // §16.2.3
      { selector: '[x-data^="entryDirectVariants"]', dataKey: 'items',  stateKey: 'variants' },          // §16.2.3
    ],

    /**
     * Collect plain (function-free) state from the Alpine-owned components.
     *
     * NOTE: Alpine v3's `$data` is a merge-proxy whose keys are NOT enumerable
     * (Object.keys/for-in return []), and component objects also contain methods that
     * structuredClone() rejects. So we read each known reactive key by name and
     * JSON-clone it (detaches the proxy and drops any nested functions).
     *
     * @returns {Object} plain Alpine state keyed for the adapter (e.g. { senses: [...] })
     */
    extractAlpineState: function () {
      var state = {};
      if (typeof window === 'undefined' || !window.Alpine || !document.querySelector) {
        return state;
      }
      this.sectionReaders.forEach(function (r) {
        var el = document.querySelector(r.selector);
        if (!el) return;
        try {
          var data = window.Alpine.$data(el);
          if (data && data[r.dataKey] !== undefined) {
            state[r.stateKey] = JSON.parse(JSON.stringify(data[r.dataKey]));
          }
        } catch (e) {
          if (window.console) console.warn('[MergeHarness] extract failed for', r.selector, e);
        }
      });
      return state;
    },

    /**
     * Build a fully-merged serializer input from a form element, combining legacy DOM
     * state with all Alpine-owned component state.
     *
     * This is the single canonical sync path used by live-preview, XML-preview, auto-save,
     * and change-detection.  It mirrors exactly what updateXmlPreview / _serializeFormData
     * do: serialize legacy DOM → strip alpineSections → mergeSync with extractAlpineState().
     *
     * Call sites that already have the entry form element should pass it; callers without
     * a reference can fall back to `document.getElementById('entry-form')`.
     *
     * @param {HTMLFormElement} form - The entry form element
     * @param {Object} [serializerOptions] - Options forwarded to serializeFormToJSON
     * @returns {Object} Merged object ready for serializeEntry(), or {} if Alpine is absent
     */
    buildSerializerInput: function (form, serializerOptions) {
      var opts = serializerOptions || { includeEmpty: false };
      var legacyData = {};
      if (window.FormSerializer && window.FormSerializer.serializeFormToJSON) {
        try {
          legacyData = window.FormSerializer.serializeFormToJSON(form, opts);
        } catch (e) {
          console.warn('[MergeHarness.buildSerializerInput] Legacy serialization failed:', e);
          legacyData = {};
        }
      }
      var alpineState = this.extractAlpineState();
      // Strip Alpine-owned sections from legacy before merge
      this.alpineSections.forEach(function (section) {
        delete legacyData[section];
      });
      var merged = this.mergeSync(legacyData, alpineState);
      return merged;
    },

    /**
     * Register a section as Alpine-owned.
     * Called at the start of each stage.
     */
    registerAlpineSection: function (sectionName) {
      if (this.alpineSections.indexOf(sectionName) === -1) {
        this.alpineSections.push(sectionName);
      }
    }
  };

  // Export
  if (typeof module !== 'undefined' && module.exports) {
    module.exports = MergeHarness;
  } else if (typeof window !== 'undefined') {
    window.MergeHarness = MergeHarness;
  }
})();
