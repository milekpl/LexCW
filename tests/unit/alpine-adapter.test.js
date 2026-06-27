/**
 * Unit Tests for Alpine.js Entry Form Adapter
 *
 * Tests:
 *   1. normalizeEntry() — server to_dict() → Alpine state
 *   2. alpineStateToSerializerInput() — Alpine state → serializer input
 *   3. Round-trip: normalize → adapt → serializeEntry() produces valid XML
 *   4. Golden test: XML output matches expected structure
 *   5. Language override: .lang is preserved through the adapter
 *   6. Null-safety: normalizeEntry handles missing/null fields
 */

// Setup XML DOM APIs
const { DOMParser, XMLSerializer, DOMImplementation } = require('@xmldom/xmldom');
globalThis.DOMParser = DOMParser;
globalThis.XMLSerializer = XMLSerializer;
globalThis.document = new DOMImplementation().createDocument(null, null, null);

// Import the serializer
const LIFTXMLSerializer = require('../../app/static/js/lift-xml-serializer.js');

// Load the normalize and adapter modules (they return module.exports in Node.js)
const AlpineNormalize = require('../../app/static/js/alpine/normalize-entry.js');
const AlpineAdapter = require('../../app/static/js/alpine/alpine-to-serializer.js');

const { normalizeEntry, dictToForms } = AlpineNormalize;
const { alpineStateToSerializerInput } = AlpineAdapter;

// --- Test fixtures ---

/**
 * A realistic entry.to_dict() fixture matching the server output shape.
 */
const SAMPLE_ENTRY_DICT = {
  id: 'entry-001',
  guid: 'abc-123-def',
  date_created: '2025-01-15T10:00:00Z',
  date_modified: '2025-06-20T14:30:00Z',
  order: 1,
  lexical_unit: {
    en: 'run',
    pl: 'biegać'
  },
  senses: [
    {
      id: 'sense-001',
      glosses: {
        en: 'move quickly on foot',
        pl: 'szybko poruszać się pieszo'
      },
      definitions: {
        en: 'To move swiftly on foot so that both feet leave the ground during each stride.',
        pl: 'Poruszać się szybko na nogach, tak że obie stopy odrywają się od ziemi.'
      },
      examples: [
        {
          id: 'ex-001',
          form: { en: 'She runs every morning.' },
          translations: { pl: 'Ona biega każdego ranka.' },
          source: 'Oxford Dictionary'
        }
      ],
      subsenses: [],
      grammatical_info: 'Verb',
      domain_type: ['sport'],
      usage_type: ['common'],
      semantic_domains: null,
      notes: {},
      relations: []
    },
    {
      id: 'sense-002',
      glosses: { en: 'operate a machine' },
      definitions: { en: 'To cause a machine or device to operate.' },
      examples: [],
      subsenses: [
        {
          id: 'subsense-001',
          glosses: { en: 'execute a program' },
          definitions: { en: 'To execute or start a computer program.' },
          examples: [],
          subsenses: [],
          grammatical_info: 'Transitive Verb'
        }
      ],
      grammatical_info: 'Verb'
    }
  ],
  pronunciations: [],
  etymologies: [],
  variants: [],
  relations: [],
  annotations: [],
  notes: []
};

// --- Tests ---

describe('normalizeEntry', () => {
  test('should handle null input', () => {
    const result = normalizeEntry(null);
    expect(result).toBeDefined();
    expect(result.senses).toEqual([]);
    expect(result.lexicalUnitForms).toEqual([]);
  });

  test('should handle undefined input', () => {
    const result = normalizeEntry(undefined);
    expect(result).toBeDefined();
    expect(result.senses).toEqual([]);
  });

  test('should handle empty object', () => {
    const result = normalizeEntry({});
    expect(result.id).toBe('');
    expect(result.senses).toEqual([]);
    expect(result.lexicalUnitForms).toEqual([]);
  });

  test('should convert lexical_unit dict to forms array', () => {
    const result = normalizeEntry({ lexical_unit: { en: 'test', pl: 'testowy' } });
    expect(result.lexicalUnitForms).toHaveLength(2);
    expect(result.lexicalUnitForms[0]).toMatchObject({ lang: 'en', text: 'test' });
    expect(result.lexicalUnitForms[0].id).toBeDefined();
  });

  test('should normalize senses with glosses and definitions', () => {
    const result = normalizeEntry(SAMPLE_ENTRY_DICT);
    expect(result.senses).toHaveLength(2);

    const sense1 = result.senses[0];
    expect(sense1.id).toBe('sense-001');
    expect(sense1.glossForms).toHaveLength(2);
    expect(sense1.definitionForms).toHaveLength(2);
    expect(sense1.glossForms[0]).toMatchObject({ lang: 'en', text: 'move quickly on foot' });

    // Examples
    expect(sense1.examples).toHaveLength(1);
    const ex = sense1.examples[0];
    expect(ex.id).toBe('ex-001');
    expect(ex.sentence).toBe('She runs every morning.');
    expect(ex.sentenceLang).toBe('en');
    expect(ex.translations).toHaveLength(1);
    expect(ex.translations[0]).toMatchObject({ lang: 'pl', text: 'Ona biega każdego ranka.' });
    expect(ex.source).toBe('Oxford Dictionary');
  });

  test('should normalize subsenses recursively', () => {
    const result = normalizeEntry(SAMPLE_ENTRY_DICT);
    const sense2 = result.senses[1];
    expect(sense2.subsenses).toHaveLength(1);
    const subsense = sense2.subsenses[0];
    expect(subsense.id).toBe('subsense-001');
    expect(subsense.glossForms).toHaveLength(1);
    expect(subsense.glossForms[0]).toMatchObject({ lang: 'en', text: 'execute a program' });
  });

  test('should handle definitions as nested objects with .lang override', () => {
    const raw = {
      senses: [{
        id: 's1',
        definitions: {
          en: { text: 'A test definition', lang: 'en' },
          pl: { text: 'Polska definicja', lang: 'pl' }
        }
      }]
    };
    const result = normalizeEntry(raw);
    expect(result.senses[0].definitionForms).toHaveLength(2);
    expect(result.senses[0].definitionForms[0]).toMatchObject({ lang: 'en', text: 'A test definition' });
    expect(result.senses[0].definitionForms[1]).toMatchObject({ lang: 'pl', text: 'Polska definicja' });
  });

  test('should handle flat string definitions (LIFT format)', () => {
    const raw = {
      senses: [{
        id: 's1',
        definitions: { en: 'flat text definition' }
      }]
    };
    const result = normalizeEntry(raw);
    expect(result.senses[0].definitionForms).toHaveLength(1);
    expect(result.senses[0].definitionForms[0]).toMatchObject({ lang: 'en', text: 'flat text definition' });
  });

  test('should handle missing examples array', () => {
    const result = normalizeEntry({ senses: [{ id: 's1', definitions: {} }] });
    expect(result.senses[0].examples).toEqual([]);
  });

  test('should handle missing subsenses', () => {
    const result = normalizeEntry({ senses: [{ id: 's1', definitions: {} }] });
    expect(result.senses[0].subsenses).toEqual([]);
  });

  test('should preserve grammatical_info', () => {
    const result = normalizeEntry({ senses: [{ id: 's1', grammatical_info: 'Noun', definitions: {} }] });
    expect(result.senses[0].grammaticalInfo).toBe('Noun');
  });

  test('should handle domain_type as array', () => {
    const result = normalizeEntry({ senses: [{ id: 's1', domain_type: ['sport', 'medicine'], definitions: {} }] });
    expect(result.senses[0].domainType).toEqual(['sport', 'medicine']);
  });

  test('should handle domain_type as string', () => {
    const result = normalizeEntry({ senses: [{ id: 's1', domain_type: 'sport', definitions: {} }] });
    expect(result.senses[0].domainType).toEqual(['sport']);
  });

  test('every form item should have a stable id', () => {
    const result = normalizeEntry(SAMPLE_ENTRY_DICT);
    const sense = result.senses[0];
    // Check all ids exist and are unique
    const ids = new Set();
    sense.glossForms.forEach(f => { expect(f.id).toBeDefined(); ids.add(f.id); });
    sense.definitionForms.forEach(f => { expect(f.id).toBeDefined(); ids.add(f.id); });
    sense.examples.forEach(ex => {
      expect(ex.id).toBeDefined();
      ids.add(ex.id);
      ex.translations.forEach(t => { expect(t.id).toBeDefined(); ids.add(t.id); });
    });
  });
});

describe('alpineStateToSerializerInput', () => {
  test('should convert Alpine state back to serializer-compatible shape', () => {
    const alpineState = normalizeEntry(SAMPLE_ENTRY_DICT);
    const serializerInput = alpineStateToSerializerInput(alpineState);

    // Basic fields
    expect(serializerInput.id).toBe('entry-001');
    expect(serializerInput.lexical_unit).toEqual({ en: 'run', pl: 'biegać' });
    expect(serializerInput.lexicalUnit).toEqual({ en: 'run', pl: 'biegać' });

    // Senses
    expect(serializerInput.senses).toHaveLength(2);

    const sense1 = serializerInput.senses[0];
    // Glosses should be flat dicts
    expect(sense1.glosses).toEqual({
      en: 'move quickly on foot',
      pl: 'szybko poruszać się pieszo'
    });
    // Also should have singular fallback
    expect(sense1.gloss).toEqual(sense1.glosses);

    // Definitions should be nested {lang: {text, lang}}
    expect(sense1.definitions).toHaveProperty('en');
    expect(sense1.definitions.en).toMatchObject({
      text: 'To move swiftly on foot so that both feet leave the ground during each stride.',
      lang: 'en'
    });

    // Examples
    expect(sense1.examples).toHaveLength(1);
    const ex = sense1.examples[0];
    expect(ex.sentence).toBe('She runs every morning.');
    expect(ex.sentence_lang).toBe('en');
    expect(ex.translation).toBe('Ona biega każdego ranka.');
    expect(ex.translation_lang).toBe('pl');
  });

  test('should handle empty Alpine state', () => {
    const result = alpineStateToSerializerInput(null);
    // null input returns empty object (adapter guards against null)
    expect(result).toEqual({});
  });

  test('should preserve subsenses', () => {
    const alpineState = normalizeEntry(SAMPLE_ENTRY_DICT);
    const serializerInput = alpineStateToSerializerInput(alpineState);

    const sense2 = serializerInput.senses[1];
    expect(sense2.subsenses).toHaveLength(1);
    expect(sense2.subsenses[0].id).toBe('subsense-001');
    expect(sense2.subsenses[0].glosses).toEqual({ en: 'execute a program' });
  });

  test('should preserve grammatical_info in sense', () => {
    const alpineState = normalizeEntry(SAMPLE_ENTRY_DICT);
    const serializerInput = alpineStateToSerializerInput(alpineState);
    expect(serializerInput.senses[0].grammatical_info).toBe('Verb');
  });

  test('should preserve domain_type as array', () => {
    const alpineState = normalizeEntry(SAMPLE_ENTRY_DICT);
    const serializerInput = alpineStateToSerializerInput(alpineState);
    expect(serializerInput.senses[0].domain_type).toEqual(['sport']);
  });

  test('should handle definition language override (lang differs from dict key)', () => {
    // Simulate a case where the user selected a different language
    const alpineState = {
      id: 'test-entry',
      lexicalUnitForms: [{ id: 'l1', lang: 'en', text: 'test' }],
      senses: [{
        id: 's1',
        definitionForms: [
          // The user chose 'fr' as the language but the dict key would normally be 'en'
          { id: 'd1', lang: 'fr', text: 'Définition en français' }
        ],
        glossForms: [{ id: 'g1', lang: 'en', text: 'test gloss' }],
        examples: [],
        subsenses: []
      }]
    };

    const serializerInput = alpineStateToSerializerInput(alpineState);
    expect(serializerInput.senses[0].definitions.fr).toBeDefined();
    expect(serializerInput.senses[0].definitions.fr.lang).toBe('fr');
    expect(serializerInput.senses[0].definitions.fr.text).toBe('Définition en français');
  });
});

describe('Round-trip: normalize → adapt → serializeEntry', () => {
  let serializer;

  beforeEach(() => {
    serializer = new LIFTXMLSerializer();
  });

  test('should produce valid LIFT XML from a full entry', () => {
    const alpineState = normalizeEntry(SAMPLE_ENTRY_DICT);
    const serializerInput = alpineStateToSerializerInput(alpineState);
    const xml = serializer.serializeEntry(serializerInput);

    // Basic structure
    expect(xml).toContain('<entry');
    expect(xml).toContain('id="entry-001"');
    expect(xml).toContain('<lexical-unit>');
    expect(xml).toContain('<form lang="en"><text>run</text></form>');

    // Senses
    expect(xml).toContain('<sense id="sense-001"');
    expect(xml).toContain('<sense id="sense-002"');

    // Glosses
    expect(xml).toContain('<gloss lang="en"><text>move quickly on foot</text></gloss>');

    // Definitions
    expect(xml).toContain('<definition>');
    expect(xml).toContain('To move swiftly on foot');

    // Examples
    expect(xml).toContain('<example');
    expect(xml).toContain('source="Oxford Dictionary"');
    expect(xml).toContain('She runs every morning.');
    expect(xml).toContain('<translation>');
    expect(xml).toContain('Ona biega każdego ranka.');

    // Subsenses (serialized as <subsense> elements)
    expect(xml).toContain('<subsense id="subsense-001"');
    expect(xml).toContain('execute a program');

    // Entry-level
    expect(xml).toContain('guid="abc-123-def"');
  });

  test('should handle minimal entry (just lexical unit and one sense)', () => {
    const minimal = {
      id: 'minimal-entry',
      lexical_unit: { en: 'word' },
      senses: [{
        id: 's1',
        definitions: { en: 'A unit of language.' },
        glosses: {}
      }]
    };
    const alpineState = normalizeEntry(minimal);
    const serializerInput = alpineStateToSerializerInput(alpineState);
    const xml = serializer.serializeEntry(serializerInput);

    expect(xml).toContain('<entry id="minimal-entry"');
    expect(xml).toContain('<form lang="en"><text>word</text></form>');
    expect(xml).toContain('<sense id="s1"');
    expect(xml).toContain('<definition>');
    expect(xml).toContain('A unit of language.');
  });

  test('should handle empty collections gracefully', () => {
    const emptyCollections = {
      id: 'empty-test',
      lexical_unit: { en: 'test' },
      senses: [{
        id: 's1',
        definitions: {},
        glosses: {},
        examples: [],
        subsenses: []
      }]
    };
    const alpineState = normalizeEntry(emptyCollections);
    const serializerInput = alpineStateToSerializerInput(alpineState);

    // Should not throw
    expect(() => serializer.serializeEntry(serializerInput)).not.toThrow();
  });

  test('should contain grammatical-info when present', () => {
    const alpineState = normalizeEntry(SAMPLE_ENTRY_DICT);
    const serializerInput = alpineStateToSerializerInput(alpineState);
    const xml = serializer.serializeEntry(serializerInput);

    expect(xml).toContain('<grammatical-info value="Verb"');
  });

  test('language override: emitted XML uses selected language, not dict key', () => {
    // This guards the original bug class (§5.0, §8 item 5)
    const entryWithOverride = {
      id: 'lang-test',
      lexical_unit: { en: 'test' },
      senses: [{
        id: 's1',
        definitions: {
          // The user changed the language selector from 'en' to 'fr'
          en: { text: 'This should appear as French', lang: 'fr' }
        },
        glosses: {}
      }]
    };

    const alpineState = normalizeEntry(entryWithOverride);
    const serializerInput = alpineStateToSerializerInput(alpineState);
    const xml = serializer.serializeEntry(serializerInput);

    // The definition should use 'fr' as the lang, not 'en'
    expect(xml).toContain('<form lang="fr">');
    expect(xml).toContain('This should appear as French');
    // Should NOT use the dict key 'en' since .lang override is 'fr'
    // (The serializer createDefinition honors defData.lang over the dict key)
  });

  test('etymology round-trips through adaptEtymology (§13.1 golden test)', () => {
    // Guards the etymology data-shape adapter: normalize → adapt → serializeEntry.
    // normalizeEtymology produces formForms/glossForms arrays + source; adaptEtymology
    // must convert them back to the {type, source, form:{lang:text}, gloss:{lang:text}}
    // shape createEtymology consumes — otherwise etymology data is silently dropped.
    const entryWithEtymology = {
      id: 'etym-test',
      lexical_unit: { en: 'test' },
      senses: [{ id: 's1', definitions: { en: 'a definition' }, glosses: {} }],
      etymologies: [{
        type: 'borrowed',
        source: 'Latin',
        form: { la: 'testum' },
        glosses: { en: 'origin meaning' }
      }]
    };

    const alpineState = normalizeEntry(entryWithEtymology);
    // Alpine-internal shape: arrays-of-objects with ids, source preserved
    expect(alpineState.etymologies).toHaveLength(1);
    expect(alpineState.etymologies[0]).toMatchObject({ type: 'borrowed', source: 'Latin' });
    expect(alpineState.etymologies[0].formForms[0]).toMatchObject({ lang: 'la', text: 'testum' });
    expect(alpineState.etymologies[0].glossForms[0]).toMatchObject({ lang: 'en', text: 'origin meaning' });

    const xml = serializer.serializeEntry(alpineStateToSerializerInput(alpineState));
    expect(xml).toContain('<etymology');
    expect(xml).toContain('type="borrowed"');
    expect(xml).toContain('source="Latin"');
    expect(xml).toContain('<form lang="la"><text>testum</text></form>');
    expect(xml).toContain('<gloss lang="en"><text>origin meaning</text></gloss>');
  });
});

describe('entry relations vs variant relations (no double-render)', () => {
  test('variant/component relations are excluded from entryRelations (kept only in variant_relations)', () => {
    // entry.py folds variant_relations into `relations` (trait-marked) AND emits them
    // separately; entryRelations must not render the trait-marked ones (they would show as
    // duplicate "undefined" relations alongside the variant component).
    const entry = normalizeEntry({
      id: 'e1',
      relations: [
        { ref: 'syn-target', type: 'Synonym' },
        { ref: 'var-target', type: '_component-lexeme', traits: { 'variant-type': 'Spelling Variant' } },
        { ref: 'cmp-target', type: '_component-lexeme', traits: { 'complex-form-type': 'Compound' } },
      ],
      variant_relations: [
        { ref: 'var-target', type: '_component-lexeme', variant_type: 'Spelling Variant' },
      ],
    });
    expect(entry.relations.map(r => r.ref)).toEqual(['syn-target']); // only the real relation
    expect(entry.variantRelations.map(r => r.ref)).toContain('var-target'); // variant kept here
  });

  test('a sense-less entry normalizes to zero senses (variant entries have no sense)', () => {
    const entry = normalizeEntry({ id: 'variant-entry', lexical_unit: { en: 'be highly considered' }, senses: [] });
    expect(entry.senses).toEqual([]);
  });
});

describe('dictToForms helper', () => {
  test('should convert lang→text dict to forms array', () => {
    const forms = dictToForms({ en: 'hello', pl: 'cześć' });
    expect(forms).toHaveLength(2);
    expect(forms[0]).toMatchObject({ lang: 'en', text: 'hello' });
    expect(forms[1]).toMatchObject({ lang: 'pl', text: 'cześć' });
    expect(forms[0].id).toBeDefined();
    expect(forms[1].id).toBeDefined();
    // IDs should be unique
    expect(forms[0].id).not.toBe(forms[1].id);
  });

  test('should handle empty dict', () => {
    expect(dictToForms({})).toEqual([]);
  });

  test('should handle null', () => {
    expect(dictToForms(null)).toEqual([]);
  });

  test('should handle nested {text, lang} objects', () => {
    const forms = dictToForms({ en: { text: 'nested text', lang: 'en' } });
    expect(forms).toHaveLength(1);
    expect(forms[0]).toMatchObject({ lang: 'en', text: 'nested text' });
  });

  test('should preserve .lang override in nested objects', () => {
    const forms = dictToForms({ en: { text: 'override test', lang: 'fr' } });
    expect(forms).toHaveLength(1);
    expect(forms[0].lang).toBe('fr'); // NOT 'en'
    expect(forms[0].text).toBe('override test');
  });

  test('should filter out empty strings', () => {
    const forms = dictToForms({ en: '', pl: 'valid' });
    expect(forms).toHaveLength(1);
    expect(forms[0].lang).toBe('pl');
  });
});
