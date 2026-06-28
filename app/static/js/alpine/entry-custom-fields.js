/**
 * entryCustomFields — Alpine.data component for entry-level custom fields (§16.3 Phase B0).
 *
 * Custom fields are LIFT <field type="..."> elements with multilingual form children.
 * The shape is {field_type: {lang: text}} — preserved as-is from normalizeEntry.
 * Edit-only of existing fields (no "add field" affordance).
 */

(function () {
  'use strict';

  document.addEventListener('alpine:init', function () {
    Alpine.data('entryCustomFields', function (rawEntry) {
      var entry = (window.AlpineNormalize && window.AlpineNormalize.normalizeEntry)
        ? window.AlpineNormalize.normalizeEntry(rawEntry)
        : rawEntry;

      return {
        fields: entry.customFields || {},

        /** Return a flat list of {type, lang, text} for x-for iteration. */
        get fieldList() {
          var out = [];
          var types = Object.keys(this.fields);
          for (var ti = 0; ti < types.length; ti++) {
            var type = types[ti];
            var content = this.fields[type];
            if (typeof content === 'object' && content !== null) {
              var langs = Object.keys(content);
              for (var li = 0; li < langs.length; li++) {
                out.push({ type: type, lang: langs[li], text: content[langs[li]] });
              }
            }
          }
          return out;
        },

        /**
         * The serialized shape expected by LIFTXMLSerializer.serializeEntry:
         * {field_type: {lang: text}}.
         * The adapter reads this and passes it to serializeEntry as formData.custom_fields.
         */
        get serialized() {
          var out = {};
          var types = Object.keys(this.fields);
          for (var ti = 0; ti < types.length; ti++) {
            var type = types[ti];
            var content = this.fields[type];
            if (typeof content === 'object' && content !== null) {
              var clean = {};
              var langs = Object.keys(content);
              for (var li = 0; li < langs.length; li++) {
                if (content[langs[li]]) clean[langs[li]] = content[langs[li]];
              }
              if (Object.keys(clean).length > 0) out[type] = clean;
            }
          }
          return out;
        }
      };
    });
  });
})();
