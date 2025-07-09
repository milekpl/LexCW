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

    it('should throw on non-numeric array index', () => {
        const badField = 'senses[1].gloss[en].lang';
        expect(() => parseFieldPath(badField)).toThrow(/array index/i);
    });
});
