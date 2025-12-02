/**
 * Unit test for grammatical_info serialization fix
 * 
 * Verifies that the LIFTXMLSerializer correctly handles both
 * camelCase (grammaticalInfo) and snake_case (grammatical_info)
 * naming conventions for sense-level grammatical info.
 */

const { LIFTXMLSerializer } = require('../../../app/static/js/lift-xml-serializer');

describe('LIFTXMLSerializer - grammatical_info snake_case support', () => {
    let serializer;

    beforeEach(() => {
        serializer = new LIFTXMLSerializer();
    });

    test('should serialize sense with grammatical_info (snake_case)', () => {
        const formData = {
            id: 'test_entry_1',
            lexical_unit: {
                pl: 'testowe słowo'
            },
            senses: [
                {
                    id: 's1',
                    grammatical_info: 'Countable Noun',  // snake_case
                    definitions: {
                        pl: 'definicja testowa'
                    }
                }
            ]
        };

        const xml = serializer.serializeEntry(formData);
        
        expect(xml).toContain('<grammatical-info value="Countable Noun"');
        expect(xml).toContain('<sense id="s1"');
    });

    test('should serialize sense with grammaticalInfo (camelCase)', () => {
        const formData = {
            id: 'test_entry_2',
            lexical_unit: {
                en: 'test word'
            },
            senses: [
                {
                    id: 's1',
                    grammaticalInfo: 'Verb',  // camelCase
                    definitions: {
                        en: 'test definition'
                    }
                }
            ]
        };

        const xml = serializer.serializeEntry(formData);
        
        expect(xml).toContain('<grammatical-info value="Verb"');
    });

    test('should handle both naming conventions in same entry', () => {
        const formData = {
            id: 'test_entry_3',
            lexical_unit: {
                pl: 'słowo'
            },
            senses: [
                {
                    id: 's1',
                    grammatical_info: 'Noun',  // snake_case
                    definitions: { pl: 'def1' }
                },
                {
                    id: 's2',
                    grammaticalInfo: 'Verb',  // camelCase
                    definitions: { pl: 'def2' }
                }
            ]
        };

        const xml = serializer.serializeEntry(formData);
        
        expect(xml).toContain('value="Noun"');
        expect(xml).toContain('value="Verb"');
    });

    test('should not create grammatical-info element when value is missing', () => {
        const formData = {
            id: 'test_entry_4',
            lexical_unit: {
                pl: 'słowo'
            },
            senses: [
                {
                    id: 's1',
                    definitions: { pl: 'definicja' }
                    // No grammatical_info
                }
            ]
        };

        const xml = serializer.serializeEntry(formData);
        
        expect(xml).not.toContain('<grammatical-info');
    });

    test('should not create grammatical-info element when value is empty string', () => {
        const formData = {
            id: 'test_entry_5',
            lexical_unit: {
                pl: 'słowo'
            },
            senses: [
                {
                    id: 's1',
                    grammatical_info: '',  // Empty string
                    definitions: { pl: 'definicja' }
                }
            ]
        };

        const xml = serializer.serializeEntry(formData);
        
        expect(xml).not.toContain('<grammatical-info');
    });
});
