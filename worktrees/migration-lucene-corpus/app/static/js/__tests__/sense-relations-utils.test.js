/** @jest-environment jsdom */

const { applySenseRelationsFromDom } = require('../sense-relations-utils');
const { normalizeIndexedArray } = require('../normalize-indexed-array');

describe('applySenseRelationsFromDom', () => {
    test('overwrites relations with current DOM values and clears missing ones', () => {
        document.body.innerHTML = `
            <form id="entry-form">
                <div id="senses-container">
                    <div class="sense-item" data-sense-index="0">
                        <div class="sense-relation-item">
                            <select class="sense-lexical-relation-select">
                                <option value="synonym" selected>Synonym</option>
                            </select>
                            <input class="sense-relation-ref-hidden" value="new_ref" />
                        </div>
                    </div>
                    <div class="sense-item" data-sense-index="1">
                        <!-- no relations -->
                    </div>
                </div>
            </form>
        `;

        const form = document.getElementById('entry-form');
        const formData = {
            senses: [
                { relations: [{ type: 'antonym', ref: 'stale_ref', order: 0 }] },
                { relations: [{ type: 'synonym', ref: 'should_clear', order: 0 }] }
            ]
        };

        const result = applySenseRelationsFromDom(form, formData, normalizeIndexedArray);

        expect(result.senses[0].relations).toEqual([{ type: 'synonym', ref: 'new_ref', order: 0 }]);
        expect(result.senses[1].relations).toEqual([]);
    });
});
