/**
 * merge-harness.js — Alpine-only serializer input builder (§16.3 B2).
 *
 * Every editable entry section is Alpine-owned. This module reads Alpine state,
 * converts it via the adapter, and returns the serializer-ready object.
 * No legacy FormSerializer branches remain.
 *
 * Usage:
 *   const data = MergeHarness.buildSerializerInput();
 *   const xml = serializer.serializeEntry(data);
 */

(function () {
  'use strict';

  var MergeHarness = {
    /** Vestigial — kept for backward compat. No-op: no legacy half remains. */
    alpineSections: [],

    /**
     * Map of Alpine-owned serializer sections → how to read them from the live DOM.
     *   selector: the component's x-data root
     *   dataKey:  the reactive property on that component holding the section data
     *   stateKey: the key to expose on the extracted state (what the adapter reads)
     */
    sectionReaders: [
      { selector: '[x-data^="senseTree"]',     dataKey: 'senses', stateKey: 'senses' },
      { selector: '[x-data^="lexicalUnit"]',   dataKey: 'forms',  stateKey: 'lexicalUnitForms' },
      { selector: '[x-data^="notes"]',         dataKey: 'items',  stateKey: 'notes' },
      { selector: '[x-data^="pronunciation"]', dataKey: 'items',  stateKey: 'pronunciations' },
      { selector: '[x-data^="etymology"]',     dataKey: 'items',  stateKey: 'etymologies' },
      { selector: '[x-data^="entryAnnotations"]', dataKey: 'items',  stateKey: 'annotations' },
      { selector: '[x-data^="entryRelations"]',  dataKey: 'items',  stateKey: 'relations' },
      { selector: '[x-data^="entryVariantRelations"]', dataKey: 'items',  stateKey: 'variantRelations' },
      { selector: '[x-data^="entryDirectVariants"]', dataKey: 'items',      stateKey: 'variants' },
      { selector: '[x-data^="entryMeta"]',          dataKey: 'serialized', stateKey: 'entryMeta' },
      { selector: '[x-data^="entryCustomFields"]',  dataKey: 'serialized', stateKey: 'custom_fields' },
    ],

    /**
     * Collect plain (function-free) state from all Alpine-owned components.
     * Reads each known reactive key by name and JSON-clones to strip reactivity.
     *
     * @returns {Object} plain state keyed for the adapter (e.g. { senses: [...] })
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
     * Build a serializer-ready input object from Alpine state only.
     * This is the SINGLE canonical sync path — used by save, preview, auto-save,
     * and change-detection.
     *
     * @param {HTMLFormElement} [form] - Ignored (kept for backward compat).
     * @returns {Object} Ready for serializeEntry()
     */
    buildSerializerInput: function (form) {
      var alpineState = this.extractAlpineState();
      var result = {};
      if (window.AlpineAdapter && window.AlpineAdapter.alpineStateToSerializerInput) {
        result = window.AlpineAdapter.alpineStateToSerializerInput(alpineState);
      }
      // Ensure id from the hidden input if the adapter didn't get it
      if (!result.id && form) {
        var idInput = form.querySelector('[name="id"]');
        if (idInput && idInput.value) result.id = idInput.value;
      }
      return result;
    },

    /**
     * Vestigial — no-op. Kept so existing callers don't break.
     */
    registerAlpineSection: function () {}
  };

  // Export
  if (typeof module !== 'undefined' && module.exports) {
    module.exports = MergeHarness;
  } else if (typeof window !== 'undefined') {
    window.MergeHarness = MergeHarness;
  }
})();
