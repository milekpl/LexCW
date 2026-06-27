/**
 * entryDirectVariants — Alpine.data component for direct variants (allomorphs) (§16.2.3).
 *
 * Manages <variant> elements with inline form, traits, grammatical_info,
 * and grammatical_traits. The form is a {lang: text} dict (not array-of-objects)
 * to match the serializer's createVariant() contract and the template's field naming.
 */

(function () {
  'use strict';

  /**
   * Get the project source language from the form's data attribute.
   */
  function getSourceLang() {
    try {
      var form = document.getElementById('entry-form');
      return form ? (form.dataset.sourceLanguage || 'en') : 'en';
    } catch (e) { return 'en'; }
  }

  document.addEventListener('alpine:init', function () {
    Alpine.data('entryDirectVariants', function (rawEntry) {
      var entry = (window.AlpineNormalize && window.AlpineNormalize.normalizeEntry)
        ? window.AlpineNormalize.normalizeEntry(rawEntry)
        : rawEntry;

      return {
        items: entry.variants || [],

        sourceLang: getSourceLang(),

        init: function () {
          // Ensure every item has the required shape
          // (normalizeVariant already provides defaults, but new items need it too)
        },

        addItem: function () {
          var form = {};
          form[this.sourceLang] = '';
          this.items.push({
            id: (window.AlpineNormalize && window.AlpineNormalize.generateId)
              ? window.AlpineNormalize.generateId()
              : 'id-' + Date.now() + '-' + Math.random().toString(36).slice(2, 11),
            form: form,
            traits: {},
            grammatical_info: '',
            grammatical_traits: {}
          });
        },

        removeItem: function (id) {
          var idx = -1;
          for (var i = 0; i < this.items.length; i++) {
            if (this.items[i].id === id) { idx = i; break; }
          }
          if (idx !== -1) this.items.splice(idx, 1);
        },

        // --- Multilingual form helpers ---
        // The form is stored as {lang: text} dict (serializer contract).
        // Iterate via Object.keys for display; add/remove keys directly.

        getFormLangs: function (item) {
          if (!item.form || typeof item.form !== 'object') return [];
          var keys = Object.keys(item.form);
          // Filter out placeholder keys
          return keys.filter(function (k) { return k.indexOf('_new_') !== 0; });
        },

        addFormLang: function (item) {
          if (!item.form) item.form = {};
          // Prompt for language code (avoids inline-key-editing complexity)
          var lang = prompt('Enter language code (e.g. en, fr):');
          if (lang && lang.trim()) {
            lang = lang.trim();
            // Check for duplicate
            if (item.form.hasOwnProperty(lang)) {
              alert('Language "' + lang + '" already exists.');
              return;
            }
            item.form[lang] = '';
          }
        },

        removeFormLang: function (item, lang) {
          if (item.form && item.form.hasOwnProperty(lang)) {
            delete item.form[lang];
          }
        },

        // --- Trait helpers ---

        getTraitKeys: function (item) {
          if (!item.traits || typeof item.traits !== 'object') return [];
          return Object.keys(item.traits);
        },

        addTrait: function (item) {
          if (!item.traits) item.traits = {};
          var key = '_new_' + Date.now();
          item.traits[key] = '';
        },

        removeTrait: function (item, key) {
          if (item.traits && item.traits.hasOwnProperty(key)) {
            delete item.traits[key];
          }
        },

        renameTrait: function (item, oldKey, newKey) {
          if (!item.traits || !item.traits.hasOwnProperty(oldKey)) return;
          if (!newKey || newKey === oldKey) return;
          item.traits[newKey] = item.traits[oldKey];
          delete item.traits[oldKey];
        },

        // --- Grammatical trait helpers ---

        getGrammaticalTraitKeys: function (item) {
          if (!item.grammatical_traits || typeof item.grammatical_traits !== 'object') return [];
          return Object.keys(item.grammatical_traits);
        },

        addGrammaticalTrait: function (item) {
          if (!item.grammatical_traits) item.grammatical_traits = {};
          var key = '_new_' + Date.now();
          item.grammatical_traits[key] = '';
        },

        removeGrammaticalTrait: function (item, key) {
          if (item.grammatical_traits && item.grammatical_traits.hasOwnProperty(key)) {
            delete item.grammatical_traits[key];
          }
        },

        renameGrammaticalTrait: function (item, oldKey, newKey) {
          if (!item.grammatical_traits || !item.grammatical_traits.hasOwnProperty(oldKey)) return;
          if (!newKey || newKey === oldKey) return;
          item.grammatical_traits[newKey] = item.grammatical_traits[oldKey];
          delete item.grammatical_traits[oldKey];
        }
      };
    });
  });
})();
