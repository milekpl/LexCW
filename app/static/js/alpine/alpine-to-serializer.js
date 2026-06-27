/**
 * alpineStateToSerializerInput — the SINGLE adapter that converts Alpine internal state
 * into the shape `LIFTXMLSerializer.serializeEntry()` expects.
 *
 * This is the ONLY place data-shape knowledge lives (§5.0, §8 item 2).
 * The serializer's XML-generation logic is UNCHANGED.
 *
 * The adapter must produce a shape compatible with the serializer's input contract:
 *   - serializeEntry() accepts: lexicalUnit (or lexical_unit), senses, pronunciations, etc.
 *   - serializeSense() reads: senseData.glosses || senseData.gloss (plural or singular)
 *   - createDefinition() reads: definitionData as {lang: {text, lang}} and honors .lang override
 *   - serializeExample() reads: sentence/sentence_lang, translation/translation_lang
 *
 * The adapter converts Alpine arrays-of-objects back to the lang-keyed dicts + nested
 * structures the serializer expects, preserving the .lang override semantics.
 */

(function () {
  'use strict';

  /**
   * Convert array of {id, lang, text} back to a lang-keyed dict of flat strings.
   * Used for glosses (which the serializer reads as {en: "text"}).
   *
   * @param {Array<{id: string, lang: string, text: string}>} forms
   * @returns {Object} {lang: text}
   */
  function formsToFlatDict(forms) {
    if (!Array.isArray(forms)) return {};
    var dict = {};
    forms.forEach(function (f) {
      if (f && f.lang && f.text) {
        dict[f.lang] = f.text;
      }
    });
    return dict;
  }

  /**
   * Convert array of {id, lang, text} to a lang-keyed dict of nested {text, lang} objects.
   * Used for definitions (where the serializer honors .lang override in createDefinition).
   *
   * @param {Array<{id: string, lang: string, text: string}>} forms
   * @returns {Object} {lang: {text: string, lang: string}}
   */
  function formsToNestedDict(forms) {
    if (!Array.isArray(forms)) return {};
    var dict = {};
    forms.forEach(function (f) {
      if (f && f.lang && f.text) {
        dict[f.lang] = { text: f.text, lang: f.lang };
      }
    });
    return dict;
  }

  /**
   * Convert Alpine example → serializer example shape.
   *
   * Alpine: {id, sentence, sentenceLang, translations: [{id, lang, text}], translationType, reference, source, note}
   * Serializer expects: {sentence, sentence_lang, translation, translation_lang, ...} (flat),
   *                    OR {form: {lang: text}, translations: {lang: text}} (model shape)
   *
   * We emit the flat sentence/sentence_lang + translation/translation_lang shape
   * which serializeExample() handles explicitly.
   */
  function adaptExample(ex) {
    if (!ex) return {};
    var result = {
      sentence: ex.sentence || '',
      sentence_lang: ex.sentenceLang || '',
      translation_type: ex.translationType || '',
      reference: ex.reference || '',
      source: ex.source || ''
    };

    // If there are translations, use the first one as the flat translation field
    if (ex.translations && ex.translations.length > 0) {
      result.translation = ex.translations[0].text || '';
      result.translation_lang = ex.translations[0].lang || '';
    } else {
      result.translation = '';
      result.translation_lang = '';
    }

    // Also provide the model-compatible shape for broader compatibility
    if (ex.sentence && ex.sentenceLang) {
      result.form = {};
      result.form[ex.sentenceLang] = ex.sentence;
    }
    if (ex.translations && ex.translations.length > 0) {
      result.translations = {};
      ex.translations.forEach(function (t) {
        if (t.lang && t.text) {
          result.translations[t.lang] = t.text;
        }
      });
    }

    if (ex.id) result.id = ex.id;
    if (ex.note) result.note = ex.note;

    return result;
  }

  /**
   * Adapt a single Alpine etymology → serializer etymology shape.
   *
   * Alpine: {id, type, source, formForms: [{id,lang,text}], glossForms: [{id,lang,text}], ...}
   * Serializer expects: {type, source, form: {lang: text}, gloss: {lang: text}}
   */
  function adaptEtymology(e) {
    var out = { type: e.type || '', source: e.source || '' };
    out.form  = {};
    (e.formForms  || []).forEach(function (f) { if (f.lang && f.text) out.form[f.lang]  = f.text; });
    out.gloss = {};
    (e.glossForms || []).forEach(function (g) { if (g.lang && g.text) out.gloss[g.lang] = g.text; });
    if (e.protoform) out.protoform = e.protoform;
    if (e.comment)   out.comment   = e.comment;
    return out;
  }

  /**
   * Adapt a single Alpine sense → serializer sense shape.
   *
   * Alpine: {id, glossForms, definitionForms, examples, subsenses, grammaticalInfo, ...}
   * Serializer expects: {id, glosses: {lang: text}, definitions: {lang: {text, lang}}, examples: [...], subsenses: [...], ...}
   */
  function adaptSense(sense) {
    if (!sense) return {};

    var result = {
      id: sense.id || '',
      glosses: formsToFlatDict(sense.glossForms),
      definitions: formsToNestedDict(sense.definitionForms),
      examples: (sense.examples || []).map(adaptExample),
      subsenses: (sense.subsenses || []).map(adaptSense)
    };

    // Also provide singular 'gloss' and 'definition' as fallbacks the serializer also checks
    result.gloss = result.glosses;
    result.definition = result.definitions;

    // Pass through other fields the serializer reads
    if (sense.grammaticalInfo) result.grammatical_info = sense.grammaticalInfo;
    if (sense.domainType && sense.domainType.length > 0) result.domain_type = sense.domainType;
    if (sense.usageType && sense.usageType.length > 0) result.usage_type = sense.usageType;
    if (sense.semanticDomains && sense.semanticDomains.length > 0) result.semantic_domain = sense.semanticDomains;
    if (sense.notes && Object.keys(sense.notes).length > 0) result.notes = sense.notes;
    if (sense.relations && sense.relations.length > 0) result.relations = sense.relations;
    if (sense.variantRelations && sense.variantRelations.length > 0) result.variant_relations = sense.variantRelations;
    if (sense.annotations && sense.annotations.length > 0) result.annotations = sense.annotations;
    if (sense.reversals && sense.reversals.length > 0) result.reversals = sense.reversals;
    if (sense.exemplar) result.exemplar = sense.exemplar;
    if (sense.scientificName) result.scientific_name = sense.scientificName;
    if (sense.literalMeaning) result.literal_meaning = sense.literalMeaning;
    if (sense.illustrations && sense.illustrations.length > 0) result.illustrations = sense.illustrations;

    // Convert multilingual form arrays back to lang→text dicts
    if (sense.noteForms && sense.noteForms.length > 0) {
      result.notes = {};
      sense.noteForms.forEach(function (f) { if (f.lang && f.text) result.notes[f.lang] = f.text; });
    }
    if (sense.literalMeaningForms && sense.literalMeaningForms.length > 0) {
      result.literal_meaning = {};
      sense.literalMeaningForms.forEach(function (f) { if (f.lang && f.text) result.literal_meaning[f.lang] = f.text; });
    }
    if (sense.exemplarForms && sense.exemplarForms.length > 0) {
      result.exemplar = {};
      sense.exemplarForms.forEach(function (f) { if (f.lang && f.text) result.exemplar[f.lang] = f.text; });
    }
    if (sense.scientificNameForms && sense.scientificNameForms.length > 0) {
      result.scientific_name = {};
      sense.scientificNameForms.forEach(function (f) { if (f.lang && f.text) result.scientific_name[f.lang] = f.text; });
    }

    return result;
  }

  /**
   * Main adapter: Alpine state → serializer input.
   *
   * @param {Object} state - Alpine reactive state (after Alpine.raw() + structuredClone)
   * @returns {Object} Shape that LIFTXMLSerializer.serializeEntry() accepts
   */
  function alpineStateToSerializerInput(state) {
    if (!state) return {};

    var result = {
      id: state.id || '',
      lexical_unit: formsToFlatDict(state.lexicalUnitForms || [])
    };

    // Also provide camelCase variant
    result.lexicalUnit = result.lexical_unit;

    if (state.guid) result.guid = state.guid;
    if (state.dateCreated) result.date_created = state.dateCreated;
    if (state.dateModified) result.date_modified = state.dateModified;
    if (state.order !== undefined) result.order = state.order;
    if (state.grammaticalInfo) result.grammatical_info = state.grammaticalInfo;
    if (state.morphType) result.morph_type = state.morphType;

    // Senses
    result.senses = (state.senses || []).map(adaptSense);

    // Top-level sections (adapt to serializer shape)
    result.pronunciations = (state.pronunciations || []).map(function (p) {
      var out = {
        id: p.id,
        type: p.type || 'seh-fonipa',
        is_default: p.isDefault
      };
      // Convert IPA value to forms dict keyed by the writing system (NOT hardcoded 'en')
      if (p.value) {
        out.forms = {};
        out.forms[p.type || 'seh-fonipa'] = p.value;
      }
      // Convert cvPattern array back to lang→text dict
      if (p.cvPattern && p.cvPattern.length > 0) {
        out.cv_pattern = {};
        p.cvPattern.forEach(function (cv) {
          if (cv.lang && cv.text) out.cv_pattern[cv.lang] = cv.text;
        });
      }
      // Convert tone array back to lang→text dict
      if (p.tone && p.tone.length > 0) {
        out.tone = {};
        p.tone.forEach(function (t) {
          if (t.lang && t.text) out.tone[t.lang] = t.text;
        });
      }
      if (p.audioPath) out.audio_path = p.audioPath;
      return out;
    });
    result.etymologies = (state.etymologies || []).map(adaptEtymology);
    result.variants = state.variants || [];
    result.relations = state.relations || [];
    result.variant_relations = state.variantRelations || [];
    // Notes: convert to {type: {lang: text}} dict (serializer expects dict keyed by note type)
    result.notes = {};
    (state.notes || []).forEach(function (n) {
      if (!n.type) return;
      var out = {};
      if (n.content && n.content.length > 0) {
        n.content.forEach(function (c) {
          if (c.lang && c.text) out[c.lang] = c.text;
        });
      }
      result.notes[n.type] = out;
    });
    result.annotations = state.annotations || [];
    if (state.headerInfo) result.header_info = state.headerInfo;

    return result;
  }

  // Export
  if (typeof module !== 'undefined' && module.exports) {
    module.exports = { alpineStateToSerializerInput, formsToFlatDict, formsToNestedDict, adaptSense, adaptExample };
  } else if (typeof window !== 'undefined') {
    window.AlpineAdapter = { alpineStateToSerializerInput: alpineStateToSerializerInput, formsToFlatDict: formsToFlatDict, formsToNestedDict: formsToNestedDict, adaptSense: adaptSense, adaptExample: adaptExample };
  }
})();
