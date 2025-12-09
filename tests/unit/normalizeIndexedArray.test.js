const { normalizeIndexedArray } = require('../../app/static/js/normalize-indexed-array');

describe('normalizeIndexedArray', () => {
    test('returns empty array for null or undefined', () => {
        expect(normalizeIndexedArray(null)).toEqual([]);
        expect(normalizeIndexedArray(undefined)).toEqual([]);
    });

    test('returns the same array instance when an array is provided', () => {
        const arr = [{ id: 1 }];
        expect(normalizeIndexedArray(arr)).toBe(arr);
    });

    test('converts numeric-keyed objects to arrays sorted by numeric index', () => {
        const input = { '2': { id: 2 }, '0': { id: 0 }, '1': { id: 1 } };
        expect(normalizeIndexedArray(input)).toEqual([{ id: 0 }, { id: 1 }, { id: 2 }]);
    });

    test('ignores non-numeric keys when normalizing', () => {
        const input = { '0': { id: 0 }, extra: { id: 99 }, '3': { id: 3 } };
        expect(normalizeIndexedArray(input)).toEqual([{ id: 0 }, { id: 3 }]);
    });

    test('returns empty array for non-object inputs', () => {
        expect(normalizeIndexedArray('not-an-object')).toEqual([]);
        expect(normalizeIndexedArray(42)).toEqual([]);
    });
});
