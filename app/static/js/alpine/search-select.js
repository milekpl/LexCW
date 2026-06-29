/**
 * searchSelect — reusable Alpine combobox UI for range-backed sense fields.
 *
 * Adds a type-to-filter search box over the existing range options (Part of Speech,
 * Domain Type, Semantic Domain, Usage Type). This is PURE UI state (open/query) plus
 * filter helpers — the selected value(s) live on the parent senseTree scope
 * (e.g. `sense.grammaticalInfo`, `sense.domainType`), so there is NO serialization
 * change: the adapter still reads the same `sense.*` fields.
 *
 * Single-select binds a scalar (model = ''); multi-select binds an array (model = []).
 * Option shape comes from flattenRangeValues(): { value, label, key } where label may
 * carry leading non-breaking-space indentation for hierarchical ranges.
 */
(function () {
  'use strict';

  // Strip leading hierarchy indentation so the selected chip / input shows a clean
  // label, while the dropdown list keeps its indent. \s matches U+00A0 too.
  function cleanLabel(label) {
    return (label || '').replace(/^\s+/, '');
  }

  document.addEventListener('alpine:init', function () {
    Alpine.data('searchSelect', function () {
      return {
        open: false,
        query: '',

        filter: function (options, q) {
          options = options || [];
          q = (q || '').trim().toLowerCase();
          if (!q) return options;
          return options.filter(function (o) {
            return (o.label || '').toLowerCase().indexOf(q) !== -1;
          });
        },

        labelFor: function (val, options) {
          var o = (options || []).find(function (x) { return x.value === val; });
          return o ? cleanLabel(o.label) : val;
        },

        displayValue: function (val, options) {
          if (!val) return '';
          return this.labelFor(val, options);
        },

        toggle: function (arr, val) {
          if (!Array.isArray(arr)) return;
          var i = arr.indexOf(val);
          if (i === -1) { arr.push(val); } else { arr.splice(i, 1); }
        }
      };
    });
  });
})();
