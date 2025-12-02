/**
 * LIFT XML Serializer
 * 
 * Client-side library for generating LIFT 0.13 compliant XML from form data.
 * 
 * @see https://github.com/sillsdev/lift-standard
 * @version 1.0.1-namespace-fix
 */

class LIFTXMLSerializer {
    constructor() {
        this.LIFT_NS = 'http://fieldworks.sil.org/schemas/lift/0.13';
        this.LIFT_VERSION = '0.13';
    }

    /**
     * Serialize form data to LIFT XML entry element
     * 
     * @param {Object} formData - Form data object
     * @param {string} formData.id - Entry ID
     * @param {Object} formData.lexicalUnit - Lexical unit with language forms
     * @param {Array} formData.senses - Array of sense objects
     * @param {Array} formData.pronunciations - Array of pronunciation objects
     * @param {Array} formData.variants - Array of variant objects
     * @param {Array} formData.relations - Array of relation objects
     * @param {Array} formData.etymologies - Array of etymology objects
     * @param {string} formData.morphType - Morph type trait value
     * @param {Object} formData.notes - Notes by type
     * @param {string} formData.dateCreated - ISO date string
     * @param {string} formData.dateModified - ISO date string
     * @returns {string} LIFT XML string
     */
    serializeEntry(formData) {
        // Support both camelCase (lexicalUnit) and snake_case (lexical_unit)
        const lexicalUnit = formData.lexicalUnit || formData.lexical_unit;
        const grammaticalInfo = formData.grammaticalInfo || formData.grammatical_info;
        const morphType = formData.morphType || formData.morph_type;
        const dateCreated = formData.dateCreated || formData.date_created;
        const dateModified = formData.dateModified || formData.date_modified;
        
        // Validate required fields
        // For new entries (no ID), generate a temporary ID
        const entryId = formData.id || this.generateEntryId();
        
        if (!lexicalUnit || Object.keys(lexicalUnit).length === 0) {
            throw new Error('Entry must have a lexicalUnit with at least one form');
        }

        // Create XML document
        const doc = document.implementation.createDocument(this.LIFT_NS, 'entry', null);
        const entry = doc.documentElement;

        // Set entry attributes
        entry.setAttribute('id', entryId);
        
        if (formData.guid) {
            entry.setAttribute('guid', formData.guid);
        }
        
        if (dateCreated) {
            entry.setAttribute('dateCreated', this.formatDate(dateCreated));
        }
        
        // Always set dateModified to current time
        entry.setAttribute('dateModified', this.formatDate(new Date()));

        // Add lexical unit
        if (lexicalUnit && Object.keys(lexicalUnit).length > 0) {
            const lexicalUnitEl = this.createLexicalUnit(doc, lexicalUnit);
            entry.appendChild(lexicalUnitEl);
        }

        // Add grammatical info (entry-level)
        if (grammaticalInfo) {
            const gramInfo = this.createGrammaticalInfo(doc, grammaticalInfo);
            entry.appendChild(gramInfo);
        }

        // Add morph type trait
        if (morphType) {
            const morphTrait = this.createTrait(doc, 'morph-type', morphType);
            entry.appendChild(morphTrait);
        }

        // Add pronunciations
        if (formData.pronunciations && formData.pronunciations.length > 0) {
            formData.pronunciations.forEach(pronData => {
                const pron = this.createPronunciation(doc, pronData);
                entry.appendChild(pron);
            });
        }

        // Add variants
        if (formData.variants && formData.variants.length > 0) {
            formData.variants.forEach(variantData => {
                const variant = this.createVariant(doc, variantData);
                entry.appendChild(variant);
            });
        }

        // Add relations
        if (formData.relations && formData.relations.length > 0) {
            formData.relations.forEach(relData => {
                const relation = this.createRelation(doc, relData);
                entry.appendChild(relation);
            });
        }

        // Add etymologies
        if (formData.etymologies && formData.etymologies.length > 0) {
            formData.etymologies.forEach(etymData => {
                const etym = this.createEtymology(doc, etymData);
                entry.appendChild(etym);
            });
        }

        // Add notes
        if (formData.notes && Object.keys(formData.notes).length > 0) {
            Object.entries(formData.notes).forEach(([type, noteData]) => {
                const note = this.createNote(doc, type, noteData);
                entry.appendChild(note);
            });
        }

        // Add senses
        if (formData.senses && formData.senses.length > 0) {
            console.log(`[FORM SUBMIT] Serialized senses: ${formData.senses.length}`);
            formData.senses.forEach((senseData, index) => {
                const sense = this.serializeSense(doc, senseData, index);
                entry.appendChild(sense);
            });
        } else {
            console.log('[FORM SUBMIT] Serialized senses: 0');
        }

        // Serialize to string
        const serializer = new XMLSerializer();
        let xmlString = serializer.serializeToString(doc);

        // Remove XML declaration if present (we'll add it later if needed)
        xmlString = xmlString.replace(/<\?xml[^>]*\?>\s*/, '');

        return xmlString;
    }

    /**
     * Serialize sense data to LIFT XML sense element
     * 
     * @param {Document} doc - XML document
     * @param {Object} senseData - Sense data object
     * @param {number} order - Sense order
     * @returns {Element} Sense element
     */
    serializeSense(doc, senseData, order = 0) {
        const sense = doc.createElementNS(this.LIFT_NS, 'sense');
        
        sense.setAttribute('id', senseData.id || this.generateId());
        
        if (order !== undefined) {
            sense.setAttribute('order', order.toString());
        }

        // Add grammatical info (support both camelCase and snake_case)
        const grammaticalInfo = senseData.grammaticalInfo || senseData.grammatical_info;
        if (grammaticalInfo) {
            const gramInfo = this.createGrammaticalInfo(doc, grammaticalInfo);
            sense.appendChild(gramInfo);
        }

        // Add glosses
        if (senseData.glosses && Object.keys(senseData.glosses).length > 0) {
            Object.entries(senseData.glosses).forEach(([lang, glossData]) => {
                if (glossData && (glossData.text || glossData.value)) {
                    const gloss = this.createGloss(doc, lang, glossData.text || glossData.value);
                    sense.appendChild(gloss);
                }
            });
        }

        // Add definitions
        if (senseData.definitions && Object.keys(senseData.definitions).length > 0) {
            const definition = this.createDefinition(doc, senseData.definitions);
            sense.appendChild(definition);
        } else if (senseData.definition && Object.keys(senseData.definition).length > 0) {
            // Handle both 'definition' and 'definitions'
            const definition = this.createDefinition(doc, senseData.definition);
            sense.appendChild(definition);
        }

        // Add domain-type trait
        if (senseData.domainType || senseData.domain_type) {
            const domainType = senseData.domainType || senseData.domain_type;
            const domainTrait = this.createTrait(doc, 'domain-type', domainType);
            sense.appendChild(domainTrait);
        }

        // Add semantic domain trait
        if (senseData.semanticDomain || senseData.semantic_domain) {
            const semDomain = senseData.semanticDomain || senseData.semantic_domain;
            const semDomainTrait = this.createTrait(doc, 'semantic-domain-ddp4', semDomain);
            sense.appendChild(semDomainTrait);
        }

        // Add usage type trait
        if (senseData.usageType || senseData.usage_type) {
            const usageType = senseData.usageType || senseData.usage_type;
            const usageTrait = this.createTrait(doc, 'usage-type', usageType);
            sense.appendChild(usageTrait);
        }

        // Add examples
        if (senseData.examples && senseData.examples.length > 0) {
            senseData.examples.forEach(exData => {
                const example = this.serializeExample(doc, exData);
                sense.appendChild(example);
            });
        }

        // Add notes
        if (senseData.notes && Object.keys(senseData.notes).length > 0) {
            Object.entries(senseData.notes).forEach(([type, noteData]) => {
                const note = this.createNote(doc, type, noteData);
                sense.appendChild(note);
            });
        }

        // Add relations
        if (senseData.relations && senseData.relations.length > 0) {
            senseData.relations.forEach(relData => {
                const relation = this.createRelation(doc, relData);
                sense.appendChild(relation);
            });
        }

        return sense;
    }

    /**
     * Serialize example data to LIFT XML example element
     * 
     * @param {Document} doc - XML document
     * @param {Object} exampleData - Example data object
     * @returns {Element} Example element
     */
    serializeExample(doc, exampleData) {
        const example = doc.createElementNS(this.LIFT_NS, 'example');

        if (exampleData.source) {
            example.setAttribute('source', exampleData.source);
        }

        // Add example forms (the actual example sentences)
        if (exampleData.forms && Object.keys(exampleData.forms).length > 0) {
            Object.entries(exampleData.forms).forEach(([lang, text]) => {
                if (text) {
                    const form = this.createForm(doc, lang, text);
                    example.appendChild(form);
                }
            });
        }

        // Add translations
        if (exampleData.translations && Object.keys(exampleData.translations).length > 0) {
            const translation = doc.createElementNS(this.LIFT_NS, 'translation');
            Object.entries(exampleData.translations).forEach(([lang, text]) => {
                if (text) {
                    const form = this.createForm(doc, lang, text);
                    translation.appendChild(form);
                }
            });
            example.appendChild(translation);
        }

        // Add notes
        if (exampleData.notes && Object.keys(exampleData.notes).length > 0) {
            Object.entries(exampleData.notes).forEach(([type, noteData]) => {
                const note = this.createNote(doc, type, noteData);
                example.appendChild(note);
            });
        }

        return example;
    }

    /**
     * Create lexical-unit element
     */
    createLexicalUnit(doc, lexicalUnitData) {
        const lexUnit = doc.createElementNS(this.LIFT_NS, 'lexical-unit');
        
        Object.entries(lexicalUnitData).forEach(([lang, text]) => {
            if (text) {
                const form = this.createForm(doc, lang, text);
                lexUnit.appendChild(form);
            }
        });

        return lexUnit;
    }

    /**
     * Create form element with text
     */
    createForm(doc, lang, text) {
        const form = doc.createElementNS(this.LIFT_NS, 'form');
        form.setAttribute('lang', lang);

        const textElem = doc.createElementNS(this.LIFT_NS, 'text');
        textElem.textContent = text;
        form.appendChild(textElem);

        return form;
    }

    /**
     * Create grammatical-info element
     */
    createGrammaticalInfo(doc, value) {
        const gramInfo = doc.createElementNS(this.LIFT_NS, 'grammatical-info');
        gramInfo.setAttribute('value', value);
        return gramInfo;
    }

    /**
     * Create trait element
     */
    createTrait(doc, name, value) {
        const trait = doc.createElementNS(this.LIFT_NS, 'trait');
        trait.setAttribute('name', name);
        trait.setAttribute('value', value);
        return trait;
    }

    /**
     * Create gloss element
     */
    createGloss(doc, lang, text) {
        const gloss = doc.createElementNS(this.LIFT_NS, 'gloss');
        gloss.setAttribute('lang', lang);

        const textElem = doc.createElementNS(this.LIFT_NS, 'text');
        textElem.textContent = text;
        gloss.appendChild(textElem);

        return gloss;
    }

    /**
     * Create definition element
     */
    createDefinition(doc, definitionData) {
        const definition = doc.createElementNS(this.LIFT_NS, 'definition');

        Object.entries(definitionData).forEach(([lang, defData]) => {
            if (defData && (defData.text || defData.value)) {
                const form = this.createForm(doc, lang, defData.text || defData.value);
                definition.appendChild(form);
            }
        });

        return definition;
    }

    /**
     * Create pronunciation element
     */
    createPronunciation(doc, pronData) {
        const pronunciation = doc.createElementNS(this.LIFT_NS, 'pronunciation');

        if (pronData.forms && Object.keys(pronData.forms).length > 0) {
            Object.entries(pronData.forms).forEach(([lang, text]) => {
                if (text) {
                    const form = this.createForm(doc, lang, text);
                    pronunciation.appendChild(form);
                }
            });
        }

        // Add media references if present
        if (pronData.media && pronData.media.length > 0) {
            pronData.media.forEach(mediaData => {
                const media = doc.createElementNS(this.LIFT_NS, 'media');
                media.setAttribute('href', mediaData.href);
                pronunciation.appendChild(media);
            });
        }

        return pronunciation;
    }

    /**
     * Create variant element
     */
    createVariant(doc, variantData) {
        const variant = doc.createElementNS(this.LIFT_NS, 'variant');

        if (variantData.ref) {
            variant.setAttribute('ref', variantData.ref);
        }

        // Add variant forms
        if (variantData.forms && Object.keys(variantData.forms).length > 0) {
            Object.entries(variantData.forms).forEach(([lang, text]) => {
                if (text) {
                    const form = this.createForm(doc, lang, text);
                    variant.appendChild(form);
                }
            });
        }

        // Add traits
        if (variantData.traits && Object.keys(variantData.traits).length > 0) {
            Object.entries(variantData.traits).forEach(([name, value]) => {
                const trait = this.createTrait(doc, name, value);
                variant.appendChild(trait);
            });
        }

        return variant;
    }

    /**
     * Create relation element
     */
    createRelation(doc, relData) {
        const relation = doc.createElementNS(this.LIFT_NS, 'relation');

        relation.setAttribute('type', relData.type);
        relation.setAttribute('ref', relData.ref);

        if (relData.order !== undefined) {
            relation.setAttribute('order', relData.order.toString());
        }

        // Add traits
        if (relData.traits && Object.keys(relData.traits).length > 0) {
            Object.entries(relData.traits).forEach(([name, value]) => {
                const trait = this.createTrait(doc, name, value);
                relation.appendChild(trait);
            });
        }

        return relation;
    }

    /**
     * Create etymology element
     */
    createEtymology(doc, etymData) {
        const etymology = doc.createElementNS(this.LIFT_NS, 'etymology');

        etymology.setAttribute('type', etymData.type);
        etymology.setAttribute('source', etymData.source);

        // Add form
        if (etymData.form && Object.keys(etymData.form).length > 0) {
            Object.entries(etymData.form).forEach(([lang, text]) => {
                if (text) {
                    const form = this.createForm(doc, lang, text);
                    etymology.appendChild(form);
                }
            });
        }

        // Add gloss
        if (etymData.gloss && Object.keys(etymData.gloss).length > 0) {
            Object.entries(etymData.gloss).forEach(([lang, text]) => {
                if (text) {
                    const glossElem = doc.createElementNS(this.LIFT_NS, 'gloss');
                    glossElem.setAttribute('lang', lang);
                    const textElem = doc.createElementNS(this.LIFT_NS, 'text');
                    textElem.textContent = text;
                    glossElem.appendChild(textElem);
                    etymology.appendChild(glossElem);
                }
            });
        }

        return etymology;
    }

    /**
     * Create note element
     */
    createNote(doc, type, noteData) {
        const note = doc.createElementNS(this.LIFT_NS, 'note');
        note.setAttribute('type', type);

        if (typeof noteData === 'string') {
            // Simple string note
            const form = this.createForm(doc, 'en', noteData);
            note.appendChild(form);
        } else if (noteData && Object.keys(noteData).length > 0) {
            // Multilingual note
            Object.entries(noteData).forEach(([lang, text]) => {
                if (text) {
                    const form = this.createForm(doc, lang, text);
                    note.appendChild(form);
                }
            });
        }

        return note;
    }

    /**
     * Generate unique ID for entries/senses
     */
    generateId() {
        return `entry_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
    }

    /**
     * Format date to ISO 8601 format
     */
    formatDate(date) {
        if (typeof date === 'string') {
            return date;
        }
        return date.toISOString();
    }

    /**
     * Validate generated XML against LIFT schema (client-side basic check)
     * 
     * @param {string} xmlString - XML string to validate
     * @returns {Object} Validation result {valid: boolean, errors: Array}
     */
    validate(xmlString) {
        const errors = [];

        try {
            // Parse XML
            const parser = new DOMParser();
            const doc = parser.parseFromString(xmlString, 'text/xml');

            // Check for parse errors (xmldom creates parsererror as documentElement)
            if (doc.documentElement.nodeName === 'parsererror') {
                errors.push({
                    type: 'PARSE_ERROR',
                    message: doc.documentElement.textContent
                });
                return { valid: false, errors };
            }

            // Check for required entry attributes
            const entry = doc.documentElement;
            if (entry.nodeName !== 'entry') {
                errors.push({
                    type: 'MISSING_ELEMENT',
                    message: 'No entry element found'
                });
                return { valid: false, errors };
            }

            if (!entry.getAttribute('id')) {
                errors.push({
                    type: 'MISSING_ATTRIBUTE',
                    message: 'Entry missing required id attribute'
                });
            }

            // Check for lexical-unit (manual search since querySelector not available)
            let hasLexicalUnit = false;
            for (let i = 0; i < entry.childNodes.length; i++) {
                if (entry.childNodes[i].nodeName === 'lexical-unit') {
                    hasLexicalUnit = true;
                    break;
                }
            }
            if (!hasLexicalUnit) {
                errors.push({
                    type: 'MISSING_ELEMENT',
                    message: 'Entry missing lexical-unit element'
                });
            }

            return {
                valid: errors.length === 0,
                errors
            };

        } catch (e) {
            return {
                valid: false,
                errors: [{
                    type: 'EXCEPTION',
                    message: e.message
                }]
            };
        }
    }

    /**
     * Generate a unique entry ID for new entries
     * Format: new_entry_TIMESTAMP_RANDOM
     * @returns {string} Generated entry ID
     */
    generateEntryId() {
        const timestamp = Date.now();
        const random = Math.random().toString(36).substring(2, 10);
        return `new_entry_${timestamp}_${random}`;
    }
}

// Export for use in Node.js/testing environments
if (typeof module !== 'undefined' && module.exports) {
    module.exports = LIFTXMLSerializer;
}
