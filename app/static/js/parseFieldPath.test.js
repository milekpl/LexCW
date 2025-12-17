// Unit test for parseFieldPath to catch malformed or deeply nested field names
// Run with: node parseFieldPath.test.js

const { parseFieldPath } = require('./form-serializer');

describe('parseFieldPath', () => {
    it('should throw on too many parse steps (malformed field)', () => {
        // Simulate a field name that would cause too many parse steps
        const badField = 'a' + '[0]'.repeat(60);
        expect(() => parseFieldPath(badField)).toThrow(/too many parse steps/i);
    });

    it('should parse normal field names', () => {
        expect(parseFieldPath('foo[0].bar')).toEqual([
            { key: 'foo', isArrayIndex: false },
            { key: '0', isArrayIndex: true },
            { key: 'bar', isArrayIndex: false }
        ]);
    });

    it('should parse field names with non-numeric bracket access', () => {
        expect(parseFieldPath('senses[1].gloss[en].lang')).toEqual([
            { key: 'senses', isArrayIndex: false },
            { key: '1', isArrayIndex: true },
            { key: 'gloss', isArrayIndex: false },
            { key: 'en', isArrayIndex: false },
            { key: 'lang', isArrayIndex: false }
        ]);
    });

    it('should parse standalone bracket access', () => {
        expect(parseFieldPath('variant_relations[0][ref]')).toEqual([
            { key: 'variant_relations', isArrayIndex: false },
            { key: '0', isArrayIndex: true },
            { key: 'ref', isArrayIndex: false }
        ]);
    });
});
