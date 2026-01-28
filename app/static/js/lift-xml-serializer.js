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
     * Normalize relation collections that may arrive as keyed objects.
     */
    normalizeRelationArray(relations) {
        if (!relations) return [];
        if (Array.isArray(relations)) {
            return relations.filter(item => item !== undefined && item !== null);
        }
        if (typeof relations === 'object') {
            return Object.keys(relations)
                .filter(key => !Number.isNaN(Number(key)))
                .sort((a, b) => Number(a) - Number(b))
                .map(key => relations[key])
                .filter(item => item !== undefined && item !== null);
        }
        return [];
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
        let entryId = formData.id;

        if (!entryId) {
            // IDs are required for serialization in this serializer.
            // Throw an error so callers must provide an id (server or client-side assignment).
            throw new Error('Entry must have an id');
        }
        
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
        const entryRelations = this.normalizeRelationArray(formData.relations);
        
        // Handle variant_relations: convert to relations with variant-type traits
        const variantRelations = this.normalizeRelationArray(formData.variant_relations);
        if (variantRelations.length > 0) {
            variantRelations.forEach(variantData => {
                // Convert variant relation to regular relation with variant-type trait
                const relationData = {
                    type: variantData.type || '_component-lexeme',
                    ref: variantData.ref,
                    order: variantData.order,
                    traits: {
                        'variant-type': variantData.variant_type || 'Unspecified Variant'
                    }
                };
                const relation = this.createRelation(doc, relationData);
                entry.appendChild(relation);
            });
        }
        
        // Handle components: convert to relations with complex-form-type traits
        const components = this.normalizeRelationArray(formData.components);
        if (components.length > 0) {
            components.forEach(componentData => {
                // Convert component to _component-lexeme relation with complex-form-type trait
                const relationData = {
                    type: componentData.type || '_component-lexeme',
                    ref: componentData.ref,
                    order: componentData.order,
                    traits: {
                        'complex-form-type': componentData.type || 'Compound'
                    }
                };
                const relation = this.createRelation(doc, relationData);
                entry.appendChild(relation);
            });
        }
        
        // Add regular relations
        if (entryRelations.length > 0) {
            entryRelations.forEach(relData => {
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
            formData.senses.forEach((senseData, index) => {
                const sense = this.serializeSense(doc, senseData, index);
                entry.appendChild(sense);
            });
        }

        // LIFT 0.13: Add annotations (editorial workflow) - Day 26-27
        if (formData.annotations && formData.annotations.length > 0) {
            formData.annotations.forEach(annotationData => {
                const annotation = this.serializeAnnotation(doc, annotationData);
                entry.appendChild(annotation);
            });
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

        // Add domain-type traits (supports multiple values)
        if (senseData.domainType || senseData.domain_type) {
            const domainType = senseData.domainType || senseData.domain_type;
            const domainTraits = this.createTraitsFromValue(doc, 'domain-type', domainType);
            domainTraits.forEach(trait => sense.appendChild(trait));
        }

        // Add semantic domain traits (supports multiple values)
        if (senseData.semanticDomain || senseData.semantic_domain) {
            const semDomain = senseData.semanticDomain || senseData.semantic_domain;
            const semDomainTraits = this.createTraitsFromValue(doc, 'semantic-domain-ddp4', semDomain);
            semDomainTraits.forEach(trait => sense.appendChild(trait));
        }

        // Add usage type traits (supports multiple values)
        if (senseData.usageType || senseData.usage_type) {
            const usageType = senseData.usageType || senseData.usage_type;
            const usageTraits = this.createTraitsFromValue(doc, 'usage-type', usageType);
            usageTraits.forEach(trait => sense.appendChild(trait));
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
        const senseRelations = this.normalizeRelationArray(senseData.relations);
        if (senseRelations.length > 0) {
            senseRelations.forEach(relData => {
                const relation = this.createRelation(doc, relData);
                sense.appendChild(relation);
            });
        }

        // Add subsenses (recursive structure)
        if (senseData.subsenses && senseData.subsenses.length > 0) {
            senseData.subsenses.forEach((subsenseData, index) => {
                const subsense = this.serializeSubsense(doc, subsenseData, index);
                sense.appendChild(subsense);
            });
        }

        // LIFT 0.13: Add reversals (bilingual dictionary support) - Day 24-25
        if (senseData.reversals && senseData.reversals.length > 0) {
            senseData.reversals.forEach(reversalData => {
                const reversal = this.serializeReversal(doc, reversalData);
                sense.appendChild(reversal);
            });
        }

        // LIFT 0.13: Add annotations (editorial workflow) - Day 26-27
        if (senseData.annotations && senseData.annotations.length > 0) {
            senseData.annotations.forEach(annotationData => {
                const annotation = this.serializeAnnotation(doc, annotationData);
                sense.appendChild(annotation);
            });
        }

        // LIFT 0.13: Add illustrations (images/graphics) - Day 33-34
        if (senseData.illustrations && senseData.illustrations.length > 0) {
            senseData.illustrations.forEach(illustrationData => {
                const illustration = this.serializeIllustration(doc, illustrationData);
                sense.appendChild(illustration);
            });
        }

        return sense;
    }

    /**
     * Serialize subsense data to LIFT XML subsense element (recursive)
     * 
     * @param {Document} doc - XML document
     * @param {Object} subsenseData - Subsense data object
     * @param {number} order - Order attribute value
     * @returns {Element} Subsense element
     */
    serializeSubsense(doc, subsenseData, order = 0) {
        // Create subsense element (has same structure as sense)
        const subsense = doc.createElementNS(this.LIFT_NS, 'subsense');
        
        subsense.setAttribute('id', subsenseData.id || this.generateId());
        
        if (order !== undefined) {
            subsense.setAttribute('order', order.toString());
        }

        // Add grammatical info
        const grammaticalInfo = subsenseData.grammaticalInfo || subsenseData.grammatical_info;
        if (grammaticalInfo) {
            const gramInfo = this.createGrammaticalInfo(doc, grammaticalInfo);
            subsense.appendChild(gramInfo);
        }

        // Add glosses
        if (subsenseData.glosses && Object.keys(subsenseData.glosses).length > 0) {
            Object.entries(subsenseData.glosses).forEach(([lang, glossData]) => {
                if (glossData && (glossData.text || glossData.value)) {
                    const gloss = this.createGloss(doc, lang, glossData.text || glossData.value);
                    subsense.appendChild(gloss);
                }
            });
        }

        // Add definitions
        if (subsenseData.definitions && Object.keys(subsenseData.definitions).length > 0) {
            const definition = this.createDefinition(doc, subsenseData.definitions);
            subsense.appendChild(definition);
        } else if (subsenseData.definition && Object.keys(subsenseData.definition).length > 0) {
            const definition = this.createDefinition(doc, subsenseData.definition);
            subsense.appendChild(definition);
        }

        // Add traits (domain-type, semantic-domain, usage-type) - supports multiple values
        if (subsenseData.domainType || subsenseData.domain_type) {
            const domainType = subsenseData.domainType || subsenseData.domain_type;
            const domainTraits = this.createTraitsFromValue(doc, 'domain-type', domainType);
            domainTraits.forEach(trait => subsense.appendChild(trait));
        }

        if (subsenseData.semanticDomain || subsenseData.semantic_domain) {
            const semDomain = subsenseData.semanticDomain || subsenseData.semantic_domain;
            const semDomainTraits = this.createTraitsFromValue(doc, 'semantic-domain-ddp4', semDomain);
            semDomainTraits.forEach(trait => subsense.appendChild(trait));
        }

        if (subsenseData.usageType || subsenseData.usage_type) {
            const usageType = subsenseData.usageType || subsenseData.usage_type;
            const usageTraits = this.createTraitsFromValue(doc, 'usage-type', usageType);
            usageTraits.forEach(trait => subsense.appendChild(trait));
        }

        // Add examples
        if (subsenseData.examples && subsenseData.examples.length > 0) {
            subsenseData.examples.forEach(exData => {
                const example = this.serializeExample(doc, exData);
                subsense.appendChild(example);
            });
        }

        // Add notes
        if (subsenseData.notes && Object.keys(subsenseData.notes).length > 0) {
            Object.entries(subsenseData.notes).forEach(([type, noteData]) => {
                const note = this.createNote(doc, type, noteData);
                subsense.appendChild(note);
            });
        }

        // Add relations
        const subsenseRelations = this.normalizeRelationArray(subsenseData.relations);
        if (subsenseRelations.length > 0) {
            subsenseRelations.forEach(relData => {
                const relation = this.createRelation(doc, relData);
                subsense.appendChild(relation);
            });
        }

        // RECURSIVE: Add nested subsenses
        if (subsenseData.subsenses && subsenseData.subsenses.length > 0) {
            subsenseData.subsenses.forEach((nestedSubsense, index) => {
                const nested = this.serializeSubsense(doc, nestedSubsense, index);
                subsense.appendChild(nested);
            });
        }

        return subsense;
    }

    /**
     * LIFT 0.13: Serialize reversal data to LIFT XML reversal element - Day 24-25
     * Reversals support bilingual dictionaries (L2→L1 translations)
     * 
     * @param {Document} doc - XML document
     * @param {Object} reversalData - Reversal data object
     * @returns {Element} Reversal element
     */
    serializeReversal(doc, reversalData) {
        const reversal = doc.createElementNS(this.LIFT_NS, 'reversal');

        // Optional type attribute (language code)
        if (reversalData.type) {
            reversal.setAttribute('type', reversalData.type);
        }

        // Add forms (multitext)
        if (reversalData.forms && Object.keys(reversalData.forms).length > 0) {
            Object.entries(reversalData.forms).forEach(([lang, text]) => {
                if (text) {
                    const form = this.createForm(doc, lang, text);
                    reversal.appendChild(form);
                }
            });
        }

        // Add grammatical-info at reversal level
        if (reversalData.grammaticalInfo || reversalData.grammatical_info) {
            const gramInfo = reversalData.grammaticalInfo || reversalData.grammatical_info;
            const grammaticalInfoElement = this.createGrammaticalInfo(doc, gramInfo);
            reversal.appendChild(grammaticalInfoElement);
        }

        // Add main sub-element (can be recursive)
        if (reversalData.main) {
            const mainElement = this.serializeReversalMain(doc, reversalData.main);
            reversal.appendChild(mainElement);
        }

        return reversal;
    }

    /**
     * LIFT 0.13: Serialize reversal main element (recursive structure) - Day 24-25
     * 
     * @param {Document} doc - XML document
     * @param {Object} mainData - Main element data object
     * @returns {Element} Main element
     */
    serializeReversalMain(doc, mainData) {
        const main = doc.createElementNS(this.LIFT_NS, 'main');

        // Add forms (multitext)
        if (mainData.forms && Object.keys(mainData.forms).length > 0) {
            Object.entries(mainData.forms).forEach(([lang, text]) => {
                if (text) {
                    const form = this.createForm(doc, lang, text);
                    main.appendChild(form);
                }
            });
        }

        // Add grammatical-info at main level
        if (mainData.grammaticalInfo || mainData.grammatical_info) {
            const gramInfo = mainData.grammaticalInfo || mainData.grammatical_info;
            const grammaticalInfoElement = this.createGrammaticalInfo(doc, gramInfo);
            main.appendChild(grammaticalInfoElement);
        }

        // RECURSIVE: Add nested main elements
        if (mainData.main) {
            const nestedMain = this.serializeReversalMain(doc, mainData.main);
            main.appendChild(nestedMain);
        }

        return main;
    }

    /**
     * LIFT 0.13: Serialize annotation data to LIFT XML annotation element - Day 26-27
     * Annotations support editorial workflow (review status, comments)
     * 
     * @param {Document} doc - XML document
     * @param {Object} annotationData - Annotation data object
     * @returns {Element} Annotation element
     */
    serializeAnnotation(doc, annotationData) {
        const annotation = doc.createElementNS(this.LIFT_NS, 'annotation');

        // Required: name attribute
        if (annotationData.name) {
            annotation.setAttribute('name', annotationData.name);
        }

        // Optional: value attribute
        if (annotationData.value) {
            annotation.setAttribute('value', annotationData.value);
        }

        // Optional: who attribute (person/email)
        if (annotationData.who) {
            annotation.setAttribute('who', annotationData.who);
        }

        // Optional: when attribute (datetime)
        if (annotationData.when) {
            annotation.setAttribute('when', annotationData.when);
        }

        // Add multitext content (forms)
        if (annotationData.content && typeof annotationData.content === 'object') {
            Object.entries(annotationData.content).forEach(([lang, text]) => {
                if (text) {
                    const form = this.createForm(doc, lang, text);
                    annotation.appendChild(form);
                }
            });
        }

        return annotation;
    }

    /**
     * Serialize illustration data to LIFT XML illustration element (Day 33-34)
     * 
     * @param {Document} doc - XML document
     * @param {Object} illustrationData - Illustration data object
     * @returns {Element} Illustration element
     */
    serializeIllustration(doc, illustrationData) {
        const illustration = doc.createElementNS(this.LIFT_NS, 'illustration');

        // Required: href attribute (path or URL to image)
        if (illustrationData.href) {
            illustration.setAttribute('href', illustrationData.href);
        }

        // Optional: multilingual label/caption
        if (illustrationData.label && typeof illustrationData.label === 'object') {
            const label = doc.createElementNS(this.LIFT_NS, 'label');
            
            Object.entries(illustrationData.label).forEach(([lang, text]) => {
                if (text) {
                    const form = this.createForm(doc, lang, text);
                    label.appendChild(form);
                }
            });
            
            // Only append label if it has forms
            if (label.childNodes.length > 0) {
                illustration.appendChild(label);
            }
        }

        return illustration;
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

        // Add example form (the actual example sentence)
        // Support multiple field naming conventions:
        // - 'form' (singular, from Example model/LIFT format): {en: "text"}
        // - 'forms' (legacy): {en: "text"}
        // - 'sentence' (from HTML form): "text" or {en: "text"}
        let exampleForm = exampleData.form || exampleData.forms;

        // Handle 'sentence' field from HTML form - could be string or dict
        if (!exampleForm && exampleData.sentence) {
            if (typeof exampleData.sentence === 'string') {
                exampleForm = { en: exampleData.sentence };
            } else if (typeof exampleData.sentence === 'object') {
                exampleForm = exampleData.sentence;
            }
        }

        if (exampleForm && Object.keys(exampleForm).length > 0) {
            Object.entries(exampleForm).forEach(([lang, text]) => {
                if (text) {
                    const form = this.createForm(doc, lang, text);
                    example.appendChild(form);
                }
            });
        }

        // Add translations
        // Support 'translations' (standard) and 'translation' (from HTML form)
        let exampleTranslations = exampleData.translations;
        if (!exampleTranslations && exampleData.translation) {
            if (typeof exampleData.translation === 'string') {
                exampleTranslations = { en: exampleData.translation };
            } else if (typeof exampleData.translation === 'object') {
                exampleTranslations = exampleData.translation;
            }
        }

        if (exampleTranslations && Object.keys(exampleTranslations).length > 0) {
            const translation = doc.createElementNS(this.LIFT_NS, 'translation');
            Object.entries(exampleTranslations).forEach(([lang, text]) => {
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
        
        // Extract string value from object if necessary
        let stringValue = value;
        if (typeof value === 'object' && value !== null) {
            // If it's an object, try to extract a string value
            stringValue = value.value || value.part_of_speech || value.partOfSpeech || 
                         Object.values(value)[0] || '';
        }
        
        gramInfo.setAttribute('value', String(stringValue));
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
     * Create trait elements for a value that may be a single string or an array.
     * Returns an array of trait elements (one per value in the array, or one for a single value).
     * This is used for fields like usage-type and domain-type that support multiple selections.
     * 
     * @param {Document} doc - XML document
     * @param {string} name - Trait name
     * @param {string|Array} value - Single value or array of values
     * @returns {Array<Element>} Array of trait elements
     */
    createTraitsFromValue(doc, name, value) {
        const traits = [];
        
        if (Array.isArray(value)) {
            // Create a separate trait element for each value in the array
            value.forEach(v => {
                if (v && String(v).trim()) {
                    traits.push(this.createTrait(doc, name, String(v).trim()));
                }
            });
        } else if (value && String(value).trim()) {
            // Handle semicolon-separated strings (legacy LIFT format)
            const stringValue = String(value).trim();
            if (stringValue.includes(';')) {
                const values = stringValue.split(';').map(v => v.trim()).filter(v => v);
                values.forEach(v => {
                    traits.push(this.createTrait(doc, name, v));
                });
            } else {
                traits.push(this.createTrait(doc, name, stringValue));
            }
        }
        
        return traits;
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
        
        // LIFT 0.13: Add cv-pattern custom field (Day 40)
        if (pronData.cv_pattern && Object.keys(pronData.cv_pattern).length > 0) {
            const cvPatternField = doc.createElementNS(this.LIFT_NS, 'field');
            cvPatternField.setAttribute('type', 'cv-pattern');
            Object.entries(pronData.cv_pattern).forEach(([lang, text]) => {
                if (text) {
                    const form = this.createForm(doc, lang, text);
                    cvPatternField.appendChild(form);
                }
            });
            pronunciation.appendChild(cvPatternField);
        }
        
        // LIFT 0.13: Add tone custom field (Day 40)
        if (pronData.tone && Object.keys(pronData.tone).length > 0) {
            const toneField = doc.createElementNS(this.LIFT_NS, 'field');
            toneField.setAttribute('type', 'tone');
            Object.entries(pronData.tone).forEach(([lang, text]) => {
                if (text) {
                    const form = this.createForm(doc, lang, text);
                    toneField.appendChild(form);
                }
            });
            pronunciation.appendChild(toneField);
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

        // Support both 'form' (singular from Python templates) and 'forms' (plural)
        const forms = variantData.form || variantData.forms || {};

        // Add variant forms
        if (forms && Object.keys(forms).length > 0) {
            Object.entries(forms).forEach(([lang, text]) => {
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

        // Add grammatical info if present
        if (variantData.grammatical_info) {
            const gramInfo = doc.createElementNS(this.LIFT_NS, 'grammatical-info');
            gramInfo.setAttribute('value', variantData.grammatical_info);
            variant.appendChild(gramInfo);
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
