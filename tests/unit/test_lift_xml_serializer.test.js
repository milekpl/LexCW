/**
 * Unit Tests for LIFT XML Serializer
 * Tests the LIFTXMLSerializer class for generating valid LIFT 0.13 XML
 * 
 * Test Coverage:
 * - Basic entry serialization
 * - Multi-lingual lexical units
 * - Senses with glosses and definitions
 * - Examples with translations
 * - Grammatical info
 * - Academic domains, semantic domains, usage types
 * - Relations (component-lexeme, derivations, synonyms)
 * - Notes (general, usage, etymology)
 * - Pronunciations and variants
 * - Etymology structures
 * - XML validation
 * - Edge cases (empty fields, special characters)
 */

// Setup XML DOM APIs using @xmldom/xmldom
const { DOMParser, XMLSerializer, DOMImplementation } = require('@xmldom/xmldom');

// Inject XML DOM globals for the serializer to use
global.DOMParser = DOMParser;
global.XMLSerializer = XMLSerializer;
global.document = new DOMImplementation().createDocument(null, null, null);

// Import the serializer (now that globals are set)
const LIFTXMLSerializer = require('../../app/static/js/lift-xml-serializer.js');

describe('LIFTXMLSerializer', () => {
    let serializer;

    beforeEach(() => {
        serializer = new LIFTXMLSerializer();
    });

    describe('Basic Entry Serialization', () => {
        test('should serialize a minimal entry', () => {
            const formData = {
                id: 'test_entry_001',
                lexicalUnit: {
                    'en': 'test'
                }
            };

            const xml = serializer.serializeEntry(formData);
            
            expect(xml).toContain('<entry id="test_entry_001"');
            expect(xml).toContain('<lexical-unit>');
            expect(xml).toContain('<form lang="en">');
            expect(xml).toContain('<text>test</text>');
        });

        test('should include GUID when provided', () => {
            const formData = {
                id: 'test_entry_002',
                guid: 'test-guid-12345',
                lexicalUnit: { 'en': 'test' }
            };

            const xml = serializer.serializeEntry(formData);
            
            expect(xml).toContain('guid="test-guid-12345"');
        });

        test('should include dateCreated when provided', () => {
            const formData = {
                id: 'test_entry_003',
                dateCreated: '2024-11-30T10:00:00Z',
                lexicalUnit: { 'en': 'test' }
            };

            const xml = serializer.serializeEntry(formData);
            
            expect(xml).toContain('dateCreated="2024-11-30T10:00:00Z"');
        });

        test('should handle multi-lingual lexical units', () => {
            const formData = {
                id: 'multilang_entry',
                lexicalUnit: {
                    'en': 'test',
                    'pl': 'test',
                    'de': 'Test',
                    'fr': 'test'
                }
            };

            const xml = serializer.serializeEntry(formData);
            
            expect(xml).toContain('lang="en"');
            expect(xml).toContain('lang="pl"');
            expect(xml).toContain('lang="de"');
            expect(xml).toContain('lang="fr"');
        });
    });

    describe('Morphological Type', () => {
        test('should serialize morph-type trait', () => {
            const formData = {
                id: 'morph_test',
                lexicalUnit: { 'en': 'test' },
                morphType: 'phrase'
            };

            const xml = serializer.serializeEntry(formData);
            
            expect(xml).toContain('<trait name="morph-type" value="phrase"');
        });

        test('should handle root morph-type', () => {
            const formData = {
                id: 'root_test',
                lexicalUnit: { 'en': 'test' },
                morphType: 'root'
            };

            const xml = serializer.serializeEntry(formData);
            
            expect(xml).toContain('value="root"');
        });
    });

    describe('Grammatical Info', () => {
        test('should serialize grammatical-info on entry level', () => {
            const formData = {
                id: 'gram_test',
                lexicalUnit: { 'en': 'test' },
                grammaticalInfo: 'Noun'
            };

            const xml = serializer.serializeEntry(formData);
            
            expect(xml).toContain('<grammatical-info value="Noun"');
        });

        test('should serialize grammatical-info on sense level', () => {
            const formData = {
                id: 'sense_gram_test',
                lexicalUnit: { 'en': 'test' },
                senses: [
                    {
                        id: 'sense_001',
                        grammaticalInfo: 'Verb'
                    }
                ]
            };

            const xml = serializer.serializeEntry(formData);
            
            expect(xml).toContain('<sense id="sense_001"');
            expect(xml).toContain('<grammatical-info value="Verb"');
        });
    });

    describe('Senses', () => {
        test('should serialize sense with gloss', () => {
            const formData = {
                id: 'sense_test',
                lexicalUnit: { 'en': 'test' },
                senses: [
                    {
                        id: 'sense_001',
                        glosses: {
                            'en': { text: 'examination' }
                        }
                    }
                ]
            };

            const xml = serializer.serializeEntry(formData);
            
            expect(xml).toContain('<sense id="sense_001"');
            expect(xml).toContain('<gloss lang="en">');
            expect(xml).toContain('<text>examination</text>');
        });

        test('should serialize sense with definition', () => {
            const formData = {
                id: 'def_test',
                lexicalUnit: { 'en': 'test' },
                senses: [
                    {
                        id: 'sense_001',
                        definitions: {
                            'en': { text: 'A procedure to assess knowledge.' }
                        }
                    }
                ]
            };

            const xml = serializer.serializeEntry(formData);
            
            expect(xml).toContain('<definition>');
            expect(xml).toContain('<form lang="en">');
            expect(xml).toContain('<text>A procedure to assess knowledge.</text>');
        });

        test('should serialize multiple senses with order', () => {
            const formData = {
                id: 'multi_sense_test',
                lexicalUnit: { 'en': 'test' },
                senses: [
                    {
                        id: 'sense_001',
                        glosses: { 'en': { text: 'first meaning' } }
                    },
                    {
                        id: 'sense_002',
                        glosses: { 'en': { text: 'second meaning' } }
                    }
                ]
            };

            const xml = serializer.serializeEntry(formData);
            
            expect(xml).toContain('<sense id="sense_001" order="0"');
            expect(xml).toContain('<sense id="sense_002" order="1"');
        });
    });

    describe('Domain Types', () => {
        test('should serialize domain-type trait from domainType field', () => {
            const formData = {
                id: 'domain_type_test',
                lexicalUnit: { 'en': 'test' },
                senses: [
                    {
                        id: 'sense_001',
                        domainType: 'education'
                    }
                ]
            };

            const xml = serializer.serializeEntry(formData);
            
            expect(xml).toContain('<trait name="domain-type" value="education"');
        });

        test('should serialize domain-type trait', () => {
            const formData = {
                id: 'domain_test',
                lexicalUnit: { 'en': 'test' },
                senses: [
                    {
                        id: 'sense_001',
                        domainType: 'psychology'
                    }
                ]
            };

            const xml = serializer.serializeEntry(formData);
            
            expect(xml).toContain('<trait name="domain-type" value="psychology"');
        });

        test('should serialize semantic-domain-ddp4 trait', () => {
            const formData = {
                id: 'semantic_test',
                lexicalUnit: { 'en': 'test' },
                senses: [
                    {
                        id: 'sense_001',
                        semanticDomain: '3.6.2.1'
                    }
                ]
            };

            const xml = serializer.serializeEntry(formData);
            
            expect(xml).toContain('<trait name="semantic-domain-ddp4" value="3.6.2.1"');
        });

        test('should serialize usage-type trait', () => {
            const formData = {
                id: 'usage_test',
                lexicalUnit: { 'en': 'test' },
                senses: [
                    {
                        id: 'sense_001',
                        usageType: 'technical'
                    }
                ]
            };

            const xml = serializer.serializeEntry(formData);
            
            expect(xml).toContain('<trait name="usage-type" value="technical"');
        });
    });

    describe('Examples', () => {
        test('should serialize example with translation', () => {
            const formData = {
                id: 'example_test',
                lexicalUnit: { 'en': 'test' },
                senses: [
                    {
                        id: 'sense_001',
                        examples: [
                            {
                                forms: {
                                    'en': 'I have a test tomorrow.'
                                },
                                translations: {
                                    'pl': 'Jutro mam test.'
                                }
                            }
                        ]
                    }
                ]
            };

            const xml = serializer.serializeEntry(formData);
            
            expect(xml).toContain('<example>');
            expect(xml).toContain('<form lang="en">');
            expect(xml).toContain('<text>I have a test tomorrow.</text>');
            expect(xml).toContain('<translation>');
            expect(xml).toContain('<form lang="pl">');
            expect(xml).toContain('<text>Jutro mam test.</text>');
        });

        test('should serialize example source attribute', () => {
            const formData = {
                id: 'source_test',
                lexicalUnit: { 'en': 'test' },
                senses: [
                    {
                        id: 'sense_001',
                        examples: [
                            {
                                forms: { 'en': 'Test example.' },
                                source: 'corpus'
                            }
                        ]
                    }
                ]
            };

            const xml = serializer.serializeEntry(formData);
            
            expect(xml).toContain('<example source="corpus">');
        });

        test('should serialize multiple examples', () => {
            const formData = {
                id: 'multi_example_test',
                lexicalUnit: { 'en': 'test' },
                senses: [
                    {
                        id: 'sense_001',
                        examples: [
                            { forms: { 'en': 'First example.' } },
                            { forms: { 'en': 'Second example.' } },
                            { forms: { 'en': 'Third example.' } }
                        ]
                    }
                ]
            };

            const xml = serializer.serializeEntry(formData);
            
            const exampleCount = (xml.match(/<example>/g) || []).length;
            expect(exampleCount).toBe(3);
        });
    });

    describe('Pronunciations', () => {
        test('should serialize pronunciation with IPA', () => {
            const formData = {
                id: 'pronunciation_test',
                lexicalUnit: { 'en': 'test' },
                pronunciations: [
                    {
                        forms: {
                            'seh-fonipa': 'test'
                        }
                    }
                ]
            };

            const xml = serializer.serializeEntry(formData);
            
            expect(xml).toContain('<pronunciation>');
            expect(xml).toContain('<form lang="seh-fonipa">');
            expect(xml).toContain('<text>test</text>');
        });

        test('should serialize multiple pronunciation forms', () => {
            const formData = {
                id: 'multi_pron_test',
                lexicalUnit: { 'en': 'test' },
                pronunciations: [
                    {
                        forms: {
                            'seh-fonipa': 'test',
                            'seh-x-ipa': 'tɛst'
                        }
                    }
                ]
            };

            const xml = serializer.serializeEntry(formData);
            
            expect(xml).toContain('lang="seh-fonipa"');
            expect(xml).toContain('lang="seh-x-ipa"');
        });
    });

    describe('Variants', () => {
        test('should serialize variant with trait', () => {
            const formData = {
                id: 'variant_test',
                lexicalUnit: { 'en': 'test' },
                variants: [
                    {
                        forms: {
                            'en': 'tests'
                        },
                        traits: {
                            'variant-type': 'plural'
                        }
                    }
                ]
            };

            const xml = serializer.serializeEntry(formData);
            
            expect(xml).toContain('<variant>');
            expect(xml).toContain('<form lang="en">');
            expect(xml).toContain('<text>tests</text>');
            expect(xml).toContain('<trait name="variant-type" value="plural"');
        });
    });

    describe('Relations', () => {
        test('should serialize component-lexeme relation', () => {
            const formData = {
                id: 'relation_test',
                lexicalUnit: { 'en': 'test' },
                relations: [
                    {
                        type: '_component-lexeme',
                        ref: 'base_entry',
                        order: 0
                    }
                ]
            };

            const xml = serializer.serializeEntry(formData);
            
            expect(xml).toContain('<relation type="_component-lexeme"');
            expect(xml).toContain('ref="base_entry"');
            expect(xml).toContain('order="0"');
        });

        test('should serialize relation with traits', () => {
            const formData = {
                id: 'relation_trait_test',
                lexicalUnit: { 'en': 'test' },
                relations: [
                    {
                        type: '_component-lexeme',
                        ref: 'base_entry',
                        traits: {
                            'is-primary': 'true',
                            'complex-form-type': 'Compound'
                        }
                    }
                ]
            };

            const xml = serializer.serializeEntry(formData);
            
            expect(xml).toContain('<trait name="is-primary" value="true"');
            expect(xml).toContain('<trait name="complex-form-type" value="Compound"');
        });

        test('should serialize sense-level relations', () => {
            const formData = {
                id: 'sense_relation_test',
                lexicalUnit: { 'en': 'test' },
                senses: [
                    {
                        id: 'sense_001',
                        relations: [
                            {
                                type: 'synonym',
                                ref: 'exam_entry'
                            }
                        ]
                    }
                ]
            };

            const xml = serializer.serializeEntry(formData);
            
            expect(xml).toContain('<relation type="synonym"');
            expect(xml).toContain('ref="exam_entry"');
        });
    });

    describe('Notes', () => {
        test('should serialize general note', () => {
            const formData = {
                id: 'note_test',
                lexicalUnit: { 'en': 'test' },
                notes: {
                    'general': {
                        'en': 'This is a general note.'
                    }
                }
            };

            const xml = serializer.serializeEntry(formData);
            
            expect(xml).toContain('<note type="general">');
            expect(xml).toContain('<form lang="en">');
            expect(xml).toContain('<text>This is a general note.</text>');
        });

        test('should serialize multiple note types', () => {
            const formData = {
                id: 'multi_note_test',
                lexicalUnit: { 'en': 'test' },
                notes: {
                    'general': { 'en': 'General note.' },
                    'usage': { 'en': 'Usage note.' },
                    'etymology': { 'en': 'Etymology note.' }
                }
            };

            const xml = serializer.serializeEntry(formData);
            
            expect(xml).toContain('type="general"');
            expect(xml).toContain('type="usage"');
            expect(xml).toContain('type="etymology"');
        });

        test('should serialize sense-level notes', () => {
            const formData = {
                id: 'sense_note_test',
                lexicalUnit: { 'en': 'test' },
                senses: [
                    {
                        id: 'sense_001',
                        notes: {
                            'usage': { 'en': 'Common in formal contexts.' }
                        }
                    }
                ]
            };

            const xml = serializer.serializeEntry(formData);
            
            expect(xml).toContain('<note type="usage">');
        });
    });

    describe('Etymology', () => {
        test('should serialize etymology structure', () => {
            const formData = {
                id: 'etymology_test',
                lexicalUnit: { 'en': 'test' },
                etymologies: [
                    {
                        type: 'borrowed',
                        source: 'Latin',
                        form: { 'la': 'testum' },
                        gloss: { 'en': 'earthen pot' }
                    }
                ]
            };

            const xml = serializer.serializeEntry(formData);
            
            expect(xml).toContain('<etymology type="borrowed" source="Latin"');
            expect(xml).toContain('<form lang="la">');
            expect(xml).toContain('<text>testum</text>');
            expect(xml).toContain('<gloss lang="en">');
            expect(xml).toContain('<text>earthen pot</text>');
        });
    });

    describe('XML Validation', () => {
        test('should validate well-formed XML', () => {
            const formData = {
                id: 'valid_test',
                lexicalUnit: { 'en': 'test' }
            };

            const xml = serializer.serializeEntry(formData);
            const result = serializer.validate(xml);
            
            expect(result.valid).toBe(true);
            expect(result.errors).toHaveLength(0);
        });

        test('should detect missing required id attribute', () => {
            // Manually create bad XML without id
            const badXML = `<?xml version="1.0" encoding="utf-8"?>
                <entry xmlns="http://fieldworks.sil.org/schemas/lift/0.13">
                    <lexical-unit><form lang="en"><text>test</text></form></lexical-unit>
                </entry>`;
            const result = serializer.validate(badXML);
            
            expect(result.valid).toBe(false);
            expect(result.errors.some(e => e.type === 'MISSING_ATTRIBUTE')).toBe(true);
        });

        test('should detect parse errors', () => {
            const badXML = '<entry id="test"><unclosed>';
            const result = serializer.validate(badXML);
            
            expect(result.valid).toBe(false);
            expect(result.errors.length).toBeGreaterThan(0);
        });
    });

    describe('Edge Cases', () => {
        test('should handle empty senses array', () => {
            const formData = {
                id: 'empty_senses',
                lexicalUnit: { 'en': 'test' },
                senses: []
            };

            const xml = serializer.serializeEntry(formData);
            
            expect(xml).toContain('<entry id="empty_senses"');
            expect(xml).not.toContain('<sense');
        });

        test('should handle special characters in text', () => {
            const formData = {
                id: 'special_chars',
                lexicalUnit: {
                    'en': 'test & <special> "characters"'
                }
            };

            const xml = serializer.serializeEntry(formData);
            
            // XML should escape special characters
            expect(xml).toContain('&amp;');
            expect(xml).toContain('&lt;');
            expect(xml).toContain('&gt;');
        });

        test('should handle Unicode characters', () => {
            const formData = {
                id: 'unicode_test',
                lexicalUnit: {
                    'pl': 'zażółć gęślą jaźń',
                    'ar': 'اختبار',
                    'zh': '测试'
                }
            };

            const xml = serializer.serializeEntry(formData);
            
            expect(xml).toContain('zażółć gęślą jaźń');
            expect(xml).toContain('اختبار');
            expect(xml).toContain('测试');
        });

        test('should handle missing optional fields gracefully', () => {
            const formData = {
                id: 'minimal_entry',
                lexicalUnit: { 'en': 'test' }
                // No senses, no grammatical info, etc.
            };

            const xml = serializer.serializeEntry(formData);
            const result = serializer.validate(xml);
            
            expect(result.valid).toBe(true);
            expect(xml).toContain('<entry id="minimal_entry"');
        });

        test('should throw error for missing required lexicalUnit', () => {
            const formData = {
                id: 'no_lexical_unit'
                // Missing lexicalUnit
            };

            expect(() => {
                serializer.serializeEntry(formData);
            }).toThrow();
        });

        test('should throw error for missing required id', () => {
            const formData = {
                lexicalUnit: { 'en': 'test' }
                // Missing id
            };

            expect(() => {
                serializer.serializeEntry(formData);
            }).toThrow();
        });
    });

    describe('Complex Integration', () => {
        test('should serialize complete complex entry', () => {
            const complexData = {
                id: 'achievement_test',
                guid: 'complex-guid-001',
                dateCreated: '2024-11-30T12:00:00Z',
                lexicalUnit: {
                    'en': 'achievement test',
                    'pl': 'test osiągnięć'
                },
                morphType: 'phrase',
                grammaticalInfo: 'Countable Noun',
                pronunciations: [
                    {
                        forms: {
                            'seh-fonipa': 'əˈtʃiːvmənt test'
                        }
                    }
                ],
                senses: [
                    {
                        id: 'sense_001',
                        grammaticalInfo: 'Noun',
                        glosses: {
                            'en': { text: 'test measuring achievement' },
                            'pl': { text: 'sprawdzian wiadomości' }
                        },
                        definitions: {
                            'en': { text: 'A standardized test designed to measure knowledge.' }
                        },
                        domainType: 'education',
                        semanticDomain: '3.6.2.1',
                        examples: [
                            {
                                forms: {
                                    'en': 'Students took an achievement test.'
                                },
                                translations: {
                                    'pl': 'Studenci przystąpili do testu.'
                                }
                            }
                        ]
                    }
                ],
                relations: [
                    {
                        type: '_component-lexeme',
                        ref: 'achievement_base',
                        order: 0,
                        traits: {
                            'is-primary': 'true'
                        }
                    }
                ],
                notes: {
                    'general': {
                        'en': 'Common in educational contexts.'
                    }
                }
            };

            const xml = serializer.serializeEntry(complexData);
            const result = serializer.validate(xml);
            
            // Should be valid
            expect(result.valid).toBe(true);
            
            // Verify all components present
            expect(xml).toContain('id="achievement_test"');
            expect(xml).toContain('guid="complex-guid-001"');
            expect(xml).toContain('<lexical-unit>');
            expect(xml).toContain('<pronunciation>');
            expect(xml).toContain('<sense id="sense_001"');
            expect(xml).toContain('<gloss');
            expect(xml).toContain('<definition>');
            expect(xml).toContain('<example>');
            expect(xml).toContain('<relation');
            expect(xml).toContain('<note');
            expect(xml).toContain('domain-type');
            expect(xml).toContain('semantic-domain-ddp4');
        });
    });
});
