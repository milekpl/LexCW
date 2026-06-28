/**
 * normalizeEntry — pure, null-safe boundary that converts the server's `entry.to_dict()`
 * shape into the Alpine-friendly arrays-of-objects-with-stable-ids shape.
 *
 * Design rules (from §10.3):
 *   1. Every collection is an array of objects with a stable `id` (not a lang-keyed dict).
 *   2. No `x-model` against `null` — this function ensures every field has a safe default.
 *   3. No null-guards scattered through templates — normalize once at the boundary.
 *
 * The server `to_dict()` shape (from app/models/entry.py:602 and app/models/sense.py:501):
 *   {
 *     id, guid, date_created, date_modified, order,
 *     lexical_unit: {en: "word", pl: "slowo"},
 *     senses: [{id, glosses: {en: "text"}, definitions: {en: "text"}, examples: [...], subsenses: [...]}],
 *     pronunciations: [{id, value, type, ...}],
 *     etymologies: [{id, type, source_language, target_language, glosses: {en: "text"}, ...}],
 *     variants: [...], relations: [...], notes: [...], annotations: [...]
 *   }
 *
 * Alpine state shape (arrays-of-objects, stable ids):
 *   {
 *     lexicalUnitForms: [{id, lang, text}],
 *     senses: [{
 *       id,
 *       definitionForms: [{id, lang, text}],
 *       glossForms: [{id, lang, text}],
 *       examples: [{id, sentence, sentenceLang, translations: [{id, lang, text}], translationType, reference, source, note}],
 *       subsenses: [...recursive...]
 *     }],
 *     pronunciationForms: [{id, lang, text, ...}],
 *     ...
 *   }
 */

(function () {
  'use strict';

  /**
   * Generate a stable id. Uses crypto.randomUUID() when available,
   * falls back to a timestamp-based id.
   */
  function generateId() {
    if (typeof crypto !== 'undefined' && crypto.randomUUID) {
      return crypto.randomUUID();
    }
    return 'id-' + Date.now() + '-' + Math.random().toString(36).slice(2, 11);
  }

  /**
   * Ensure a value is a non-null object.
   */
  function safeObject(val) {
    if (val && typeof val === 'object' && !Array.isArray(val)) return val;
    return {};
  }

  /**
   * Ensure a value is a non-null array.
   */
  function safeArray(val) {
    if (Array.isArray(val)) return val;
    return [];
  }

  /**
   * Ensure a value is a non-null string.
   */
  function safeString(val) {
    if (typeof val === 'string') return val;
    if (val === null || val === undefined) return '';
    return String(val);
  }

  /**
   * Derive a single citation text from the server shape.
   *
   * LIFT `<citation>` is a multitext; `to_dict()` emits it as `citations`
   * (a list of {lang: text} dicts). The entry form has always edited a single
   * citation text (the legacy `entry.citation_form` input), so we surface the
   * first non-empty value. On re-save the adapter re-emits it as `citation_form`,
   * which the serializer wraps under the headword's primary language — matching
   * the long-standing single-language citation behaviour (no new data loss).
   */
  function firstCitationText(raw) {
    if (raw.citation_form) return safeString(raw.citation_form);
    var cits = safeArray(raw.citations);
    for (var i = 0; i < cits.length; i++) {
      var c = cits[i];
      if (c && typeof c === 'object') {
        var keys = Object.keys(c);
        for (var k = 0; k < keys.length; k++) {
          if (c[keys[k]]) return safeString(c[keys[k]]);
        }
      }
    }
    return '';
  }

  /**
   * Convert a lang→text dict (server shape: {en: "text", pl: "tekst"})
   * into an array of {id, lang, text} objects.
   *
   * Used for: lexical_unit, glosses (in the model), definitions (flat in model),
   *           translations, notes content, etc.
   *
   * @param {Object} dict - {lang: text} or {lang: {text: "...", lang: "..."}}
   * @returns {Array<{id: string, lang: string, text: string}>}
   */
  function dictToForms(dict) {
    const obj = safeObject(dict);
    return Object.entries(obj)
      .filter(function (entry) {
        var val = entry[1];
        // Accept strings or objects with .text
        if (typeof val === 'string') return val.length > 0;
        if (val && typeof val === 'object' && typeof val.text === 'string') return val.text.length > 0;
        return false;
      })
      .map(function (entry) {
        var lang = entry[0];
        var val = entry[1];
        var text = typeof val === 'string' ? val : (val && val.text ? val.text : '');
        // Preserve explicit .lang from nested objects (the language-override case)
        var actualLang = (val && typeof val === 'object' && val.lang) ? val.lang : lang;
        return { id: generateId(), lang: actualLang, text: text };
      });
  }

  /**
   * Normalize a single example object from server to Alpine shape.
   *
   * Server example shape (from Example.to_dict()):
   *   {id, form: {en: "text"}, translations: {pl: "tekst"}, source, note}
   *
   * Alpine example shape:
   *   {id, sentence, sentenceLang, translations: [{id, lang, text}], translationType, reference, source, note}
   */
  function normalizeExample(raw) {
    if (!raw) raw = {};
    var formDict = safeObject(raw.form);
    // Pick the first language from the form dict as sentence+sentenceLang
    var formEntries = Object.entries(formDict);
    var firstForm = formEntries.length > 0 ? formEntries[0] : null;
    var sentence = firstForm ? safeString(firstForm[1]) : '';
    var sentenceLang = firstForm ? firstForm[0] : '';

    // Also check for sentence/sentence_lang from form-serializer shape
    if (!sentence && raw.sentence) {
      sentence = safeString(raw.sentence);
      sentenceLang = safeString(raw.sentence_lang || raw.sentenceLang || '');
    }

    var translations = [];
    if (raw.translations && typeof raw.translations === 'object') {
      translations = dictToForms(raw.translations);
    }

    return {
      id: raw.id || generateId(),
      sentence: sentence,
      sentenceLang: sentenceLang,
      translations: translations,
      translationType: safeString(raw.translation_type || raw.translationType || ''),
      reference: safeString(raw.reference || ''),
      source: safeString(raw.source || ''),
      note: safeString(raw.note || '')
    };
  }

  /**
   * Normalize a single sense from server to Alpine shape.
   *
   * Server sense shape (from Sense.to_dict()):
   *   {id, glosses: {en: "text"}, definitions: {en: "text"}, examples: [...], subsenses: [...],
   *    grammatical_info, domain_type, usage_type, semantic_domains, notes, relations, ...}
   *
   * Alpine sense shape:
   *   {id, glossForms: [{id, lang, text}], definitionForms: [{id, lang, text}],
   *    examples: [...], subsenses: [...], grammaticalInfo, ...}
   */
  function normalizeSense(raw) {
    if (!raw) raw = {};
    return {
      id: raw.id || generateId(),
      definitionForms: dictToForms(raw.definitions || raw.definition),
      glossForms: dictToForms(raw.glosses || raw.gloss),
      examples: safeArray(raw.examples).map(normalizeExample),
      subsenses: safeArray(raw.subsenses).map(normalizeSense),
      grammaticalInfo: safeString(raw.grammatical_info || raw.grammaticalInfo || ''),
      domainType: Array.isArray(raw.domain_type) ? raw.domain_type.slice() : (raw.domain_type ? [raw.domain_type] : []),
      usageType: Array.isArray(raw.usage_type) ? raw.usage_type.slice() : (raw.usage_type ? [raw.usage_type] : []),
      semanticDomains: Array.isArray(raw.semantic_domains) ? raw.semantic_domains.slice() : (raw.semantic_domains ? [raw.semantic_domains] : []),
      notes: safeObject(raw.notes),
      relations: safeArray(raw.relations),
      variantRelations: safeArray(raw.variant_relations),
      annotations: safeArray(raw.annotations).map(normalizeAnnotation),
      reversals: safeArray(raw.reversals),
      exemplar: raw.exemplar || null,
      scientificName: raw.scientific_name || raw.scientificName || null,
      literalMeaning: raw.literal_meaning || raw.literalMeaning || null,
      illustrations: safeArray(raw.illustrations),
      // Alpine template fields (converted to arrays for x-for iteration)
      noteForms: dictToForms(raw.notes),
      literalMeaningForms: dictToForms(raw.literal_meaning || raw.literalMeaning),
      exemplarForms: dictToForms(raw.exemplar),
      scientificNameForms: dictToForms(raw.scientific_name || raw.scientificName)
    };
  }

  /**
   * Normalize a pronunciation entry.
   */
  /**
   * Normalize pronunciations from server shape to Alpine array.
   * Server may send a dict {ws_id: value} or an array of objects.
   */
  function normalizePronunciations(raw) {
    if (!raw) return [];
    if (Array.isArray(raw)) return raw.map(normalizePronunciation);
    // Dict shape: {ws_id: value_string}
    if (typeof raw === 'object') {
      return Object.entries(raw).map(function (entry, idx) {
        return {
          id: generateId(),
          value: safeString(entry[1]),
          type: safeString(entry[0] || 'seh-fonipa'),
          audioPath: '',
          isDefault: idx === 0,
          cvPattern: [],
          tone: []
        };
      });
    }
    return [];
  }

  function normalizePronunciation(raw) {
    if (!raw) raw = {};
    return {
      id: raw.id || generateId(),
      value: safeString(raw.value || ''),
      type: safeString(raw.type || 'seh-fonipa'),
      audioPath: safeString(raw.audio_path || raw.audioPath || ''),
      isDefault: !!(raw.is_default || raw.isDefault),
      cvPattern: dictToForms(raw.cv_pattern || raw.cvPattern),
      tone: dictToForms(raw.tone)
    };
  }

  /**
   * Normalize an etymology entry.
   */
  function normalizeEtymology(raw) {
    if (!raw) raw = {};
    return {
      id: raw.id || generateId(),
      type: safeString(raw.type || ''),
      source: safeString(raw.source || raw.source_language || raw.sourceLanguage || ''),
      targetLanguage: safeString(raw.target_language || raw.targetLanguage || ''),
      glossForms: dictToForms(raw.glosses || raw.gloss),
      formForms: dictToForms(raw.form),
      protoform: safeString(raw.protoform || ''),
      comment: safeString(raw.comment || '')
    };
  }

  /**
   * Normalize a variant entry.
   * Preserves the full variant shape including form, traits, grammatical_info,
   * and grammatical_traits for direct variants with inline forms (§16.2.3).
   */
  function normalizeVariant(raw) {
    if (!raw) raw = {};
    var result = {
      id: raw.id || generateId(),
      ref: safeString(raw.ref || ''),
      type: safeString(raw.type || ''),
      variantType: safeString(raw.variant_type || raw.variantType || ''),
      order: raw.order || 0,
      // Preserve direct-variant fields (form is a {lang: text} dict)
      form: safeObject(raw.form),
      traits: safeObject(raw.traits),
      grammatical_info: safeString(raw.grammatical_info || raw.grammaticalInfo || ''),
      grammatical_traits: safeObject(raw.grammatical_traits || raw.grammaticalTraits)
    };
    return result;
  }

  /**
   * Normalize a relation entry.
   */
  function normalizeRelation(raw) {
    if (!raw) raw = {};
    return {
      id: raw.id || generateId(),
      ref: safeString(raw.ref || ''),
      type: safeString(raw.type || ''),
      order: raw.order || 0
    };
  }

  /**
   * Normalize a note entry.
   */
  /**
   * Normalize notes from server shape to Alpine array.
   * Server sends {note_type: {lang: text}} dict.
   */
  function normalizeNotes(raw) {
    if (!raw) return [];
    if (Array.isArray(raw)) return raw.map(normalizeNote);
    // Dict shape: {type: content_dict}
    if (typeof raw === 'object') {
      return Object.entries(raw).map(function (entry) {
        return {
          id: generateId(),
          type: safeString(entry[0]),
          content: dictToForms(entry[1])
        };
      });
    }
    return [];
  }

  function normalizeNote(raw) {
    if (!raw) raw = {};
    return {
      id: raw.id || generateId(),
      type: safeString(raw.type || ''),
      content: safeString(raw.content || '')
    };
  }

  /**
   * Normalize an annotation entry.
   */
  function normalizeAnnotation(raw) {
    if (!raw) raw = {};
    return {
      id: raw.id || generateId(),
      name: safeString(raw.name || ''),
      value: safeString(raw.value || ''),
      who: safeString(raw.who || ''),
      when: safeString(raw.when || ''),
      content: safeObject(raw.content),
      contentForms: dictToForms(raw.content)
    };
  }

  /**
   * Main entry point: convert server `entry.to_dict()` → Alpine reactive state.
   *
   * @param {Object} raw - The raw entry dict from the server (JSON.parse of #entry-data)
   * @returns {Object} Alpine-friendly state with arrays-of-objects and stable ids.
   */
  function normalizeEntry(raw) {
    if (!raw) raw = {};

    return {
      id: raw.id || '',
      guid: raw.guid || '',
      dateCreated: raw.date_created || raw.dateCreated || null,
      dateModified: raw.date_modified || raw.dateModified || null,
      order: raw.order || 0,

      // Lexical unit: lang→text dict → array of {id, lang, text}
      lexicalUnitForms: dictToForms(raw.lexical_unit || raw.lexicalUnit),

      // Grammatical info at entry level
      grammaticalInfo: safeString(raw.grammatical_info || raw.grammaticalInfo || ''),
      morphType: safeString(raw.morph_type || raw.morphType || ''),

      // Citation (single source-language text) + status (entry-level `status` trait)
      citation: firstCitationText(raw),
      status: safeString((raw.traits && raw.traits.status) || raw.status || ''),

      // Senses — the core tree
      senses: safeArray(raw.senses).map(normalizeSense),

      // Independent top-level sections
      // pronunciations may be a dict {ws_id: value} or an array of objects
      pronunciations: normalizePronunciations(raw.pronunciations),
      etymologies: safeArray(raw.etymologies).map(normalizeEtymology),
      variants: safeArray(raw.variants).map(normalizeVariant),
      // Entry-level semantic relations ONLY. The model (entry.py) folds variant_relations
      // and components INTO `relations` (as relations carrying a 'variant-type' /
      // 'complex-form-type' trait), and ALSO emits them separately as `variant_relations`.
      // Without this filter they render twice — once here (as an "undefined" relation, since
      // their type is `_component-lexeme`, not a lexical-relation) and once in the variant
      // component. Exclude trait-marked relations; they belong to entryVariantRelations/components.
      relations: safeArray(raw.relations).filter(function (r) {
        var t = r && r.traits;
        return !(t && (t['variant-type'] || t['complex-form-type']));
      }).map(normalizeRelation),
      variantRelations: safeArray(raw.variant_relations || raw.variantRelations).map(function (vr) {
        if (!vr) vr = {};
        return {
          id: vr.id || generateId(),
          ref: safeString(vr.ref || ''),
          variant_type: vr.variant_type || vr.variantType || '',
          type: safeString(vr.type || ''),
          order: vr.order || 0,
          traits: vr.traits || {}
        };
      }),
      notes: normalizeNotes(raw.notes),
      annotations: safeArray(raw.annotations).map(normalizeAnnotation),

      // Custom fields: preserve {field_type: {lang: text}} shape as-is
      customFields: safeObject(raw.custom_fields),

      // LIFT header info
      headerInfo: raw.header_info || raw.headerInfo || null
    };
  }

  // Export
  if (typeof module !== 'undefined' && module.exports) {
    module.exports = { normalizeEntry, dictToForms, normalizeSense, normalizeExample, generateId };
  } else if (typeof window !== 'undefined') {
    window.AlpineNormalize = { normalizeEntry: normalizeEntry, dictToForms: dictToForms, normalizeSense: normalizeSense, normalizeExample: normalizeExample, generateId: generateId };
  }
})();
