(function(global) {
    const localNormalize = function(value) {
        if (value === undefined || value === null) return [];
        if (Array.isArray(value)) return value;
        if (typeof value === 'object') {
            return Object.entries(value)
                .filter(([key]) => key !== '__proto__' && key !== 'constructor' && key !== 'prototype' && !Number.isNaN(Number(key)))
                .sort((a, b) => Number(a[0]) - Number(b[0]))
                .map(([, val]) => val);
        }
        return [];
    };

    function applySenseRelationsFromDom(form, formData = {}, normalizeFn) {
        const normalize = typeof normalizeFn === 'function'
            ? normalizeFn
            : (typeof global.normalizeIndexedArray === 'function' ? global.normalizeIndexedArray : localNormalize);

        const result = formData;
        result.senses = normalize(result.senses);

        const senseItems = form ? form.querySelectorAll('#senses-container .sense-item') : [];
        senseItems.forEach((senseEl, fallbackIndex) => {
            const senseIndex = senseEl.dataset.senseIndex;
            const idx = Number.isNaN(Number(senseIndex)) ? fallbackIndex : Number(senseIndex);

            if (!result.senses[idx]) {
                result.senses[idx] = {};
            }

            const relations = [];
            senseEl.querySelectorAll('.sense-relation-item').forEach((relEl, relIdx) => {
                const typeEl = relEl.querySelector('.sense-lexical-relation-select');
                const refEl = relEl.querySelector('.sense-relation-ref-hidden');
                const type = typeEl ? (typeEl.value || '').trim() : '';
                const ref = refEl ? (refEl.value || '').trim() : '';
                if (type || ref) {
                    relations.push({ type, ref, order: relIdx });
                }
            });

            // Always set relations to current DOM-derived values to avoid stale data
            result.senses[idx].relations = relations;
        });

        return result;
    }

    const exported = { applySenseRelationsFromDom };

    if (typeof module !== 'undefined' && module.exports) {
        module.exports = exported;
    } else {
        global.applySenseRelationsFromDom = applySenseRelationsFromDom;
    }
})(typeof window !== 'undefined' ? window : globalThis);
