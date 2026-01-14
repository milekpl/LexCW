const LIFTXMLSerializer = require('../../../app/static/js/lift-xml-serializer');

describe('LIFTXMLSerializer relation normalization', () => {
    it('serializes entry- and sense-level relations when provided as keyed objects', () => {
        const serializer = new LIFTXMLSerializer();

        const formData = {
            id: 'entry_normalize_relations',
            lexical_unit: { en: 'normalize' },
            relations: {
                0: { type: 'synonym', ref: 'entry_target_001' }
            },
            senses: [
                {
                    id: 'sense_normalize_001',
                    relations: {
                        0: { type: 'antonym', ref: 'sense_target_001' }
                    }
                }
            ]
        };

        const xmlString = serializer.serializeEntry(formData);

        expect(xmlString).toContain('relation type="synonym" ref="entry_target_001"');
        expect(xmlString).toContain('relation type="antonym" ref="sense_target_001"');
    });
});
