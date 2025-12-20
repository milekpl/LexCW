# **Analysis and Optimization of Lexicographic Type Ranges and Grammatical Categories for Modern Dictionary Writing Systems**

The contemporary landscape of lexicography has evolved from the production of static, printed word lists into the development of sophisticated, interoperable lexical databases. This shift is driven by the necessity for data to be machine-readable, interchangeable across diverse software platforms, and capable of supporting complex computational tasks such as natural language processing (NLP) and the semantic web. Central to this evolution is the configuration of Dictionary Writing Systems (DWS), which must provide lexicographers with predefined yet flexible type ranges for grammatical, semantic, and morphological information.1 The challenge for modern developers and linguists lies in determining a minimal set of values that ensures structural integrity without imposing the prohibitive overhead of exhaustive but often redundant classification systems. By juxtaposing the minimal requirements of the Lexicon Interchange FormaT (LIFT) standard with the extensive catalogs utilized by SIL FieldWorks Language Explorer (FLEx), an optimized framework can be established that meets the rigorous demands of modern lexicographic practitioners.2

## **Evolution of Lexicographic Standards and Interoperability**

Lexicography is fundamentally the study of words and the principles used to describe them within a structured repository. Traditionally, this process involved the manual collection and refinement of data, often targeted toward a specific printed output. However, modern systems recognize that a dictionary entry is a complex mental and linguistic structure that requires multidimensional description: phonological, grammatical, and semantic.1 The emergence of interchange standards like LIFT represents a significant milestone in ensuring that lexical data remains accessible and usable over long durations, regardless of the specific software tool used for its creation.5 LIFT, as an XML-based format, prioritizes the movement of data between programs such as WeSay, FLEx, and Lexique Pro, acting as a bridge that prevents data silos.7

Despite the utility of LIFT, the global lexicographic community—represented by initiatives such as the European Lexicographic Infrastructure (ELEXIS)—is increasingly moving toward even more streamlined and standardized models like TEI Lex-0 and OntoLex-Lemon.2 TEI Lex-0, a subset of the Text Encoding Initiative (TEI) guidelines, aims to establish a baseline encoding that facilitates the interoperability of heterogeneously encoded resources.9 It reduces the permissive nature of traditional TEI, enforcing stricter structural rules to ensure that entries can be univocally transformed, queried, and visualized.2 This transition from tree-structured XML hierarchies to graph-based data models highlights the need for a DWS to adopt type ranges that are not only descriptively accurate but also conceptually linked to global linguistic ontologies.2

## **Grammatical Categories and Part of Speech Taxonomy**

The part of speech (POS) classification remains the most critical grammatical descriptor in any dictionary. It dictates the syntactic behavior of a word and informs the user of its role within a sentence.15 Most traditional grammars identify a core set of eight categories, yet modern linguistic documentation often requires a more granular approach to capture the idiosyncrasies of diverse languages.17

### **Evaluation of the Minimal LIFT POS Set**

The minimal LIFT set identified in current implementations includes Adverb, Noun, Pro-form, Verb, Preposition, Adjective, Interjection, and Determiner.20 While this set covers the "major" and "minor" classes essential for general-purpose dictionaries, its reliance on the "Pro-form" category as a catch-all for Acronyms, Abbreviations, and Pronouns is increasingly viewed as an architectural weakness in digital systems.20

In modern practice, practitioners distinguish between open classes (Nouns, Verbs, Adjectives, Adverbs) that easily accept new members through lexicalization, and closed classes (Pronouns, Prepositions, Conjunctions) that provide functional support.21 The exclusion of "Conjunction" as a top-level category in the minimal set represents a significant departure from both traditional and modern standards.15 Furthermore, the lack of a "Proper Noun" distinction limits the system's utility for named entity recognition, a core requirement for contemporary digital dictionaries.13

| Minimal LIFT Range | Universal Dependencies (UD) | SIL FLEx Catalog (GOLD-based) | Recommendation for DWS |
| :---- | :---- | :---- | :---- |
| Noun | NOUN | Noun | Split into Common and Proper Noun.25 |
| Verb | VERB | Verb | Include subcategories for Auxiliary (AUX).22 |
| Adjective | ADJ | Adjective | Essential for dimension, value, and color.1 |
| Adverb | ADV | Adverb | Differentiate narrow (verb-modifying) and broad.20 |
| Pro-form | PRON | Pro-form | Move Pronoun to top-level; treat Acronym as Entry Type.26 |
| Preposition | ADP | Adposition | Adopt "Adposition" to cover Pre- and Post-positions.14 |
| Determiner | DET | Determiner | Include Article as a sub-type.14 |
| Interjection | INTJ | Interjection | Essential for emotive, syntactically isolated forms.18 |
| \- | CCONJ / SCONJ | Conjunction | Add separate coordinating and subordinating types.16 |
| \- | NUM | Numeral | Necessary for count distinctions and cardinals.26 |
| \- | PART | Particle | Critical for phrasal verbs and focus markers.16 |

14

### **The Necessity of Functional and Sub-categorical Labels**

A DWS must support more than just primary labels; it must capture the features that dictate how a word combines with others.32 For verbs, this primarily concerns transitivity and valency. Minimal systems often overlook the distinction between transitive, intransitive, and ditransitive verbs, yet this information is vital for learners and for automated parsing.27 SIL FLEx addresses this by associating categories with inflectional templates and features such as person, number, and gender.33

Modern practitioners also emphasize "countability" for nouns, distinguishing between count nouns (pluralizable) and mass nouns (invariant).30 A DWS should include a range for "Inflectional Classes" to handle these distinctions structurally, rather than relying on prose definitions.14

## **Complex Morphological Forms and Phrasal Structures**

Linguistic units often occupy a spectrum between a single morpheme and a full syntactic phrase. SIL FLEx provides a robust list of "Complex Form Types" (EntTyp) that are frequently missing from minimal LIFT implementations.20

### **Juxtaposition of Complex Form Ranges**

The user's minimal system currently treats morphology through a simple "morpheme type" range (root, stem, affix, phrase).20 However, modern lexicography requires more nuanced labels to identify how these components interact to form a single semantic unit.13

| Category | SIL Definition and Practitioner View | Lexicographic Implication |
| :---- | :---- | :---- |
| **Compound** | A stem made of more than one root.20 | Crucial for languages like German or Dutch where compounding is highly productive.4 |
| **Derivative** | Root plus non-inflectional affix; often changes POS.20 | Essential for mapping lexical families and productivity.12 |
| **Idiom** | Multi-word expression as a single semantic unit; resists reordering.20 | Requires special handling in search; meaning is often opaque/non-compositional.18 |
| **Phrasal Verb** | Lexical verb \+ verbal particle.20 | Vital for Germanic languages; needs to be linked to the base verb.15 |
| **Contraction** | Phonologically reduced combinations.20 | Different from clitics (grammatically independent) and portmanteaus (indivisible).20 |
| **Saying** | Pithy phrasal expression of wisdom (proverb/maxim).20 | Often treated as distinct lexical items in community-based dictionaries.18 |

15

The exclusion of these categories from a minimal DWS leads to "flat" data where idioms are indistinguishable from regular phrases, and derived forms lose their connection to their roots.13 Practitioners now consider the identification of Multi-Word Expressions (MWEs) a baseline requirement for high-quality dictionaries.4

### **Distinguishing Roots, Stems, and Affixes**

The minimal LIFT range for morpheme types includes specific interfix types (infixing, prefixing, suffixing).20 Modern documentation projects, particularly those focused on endangered or low-resource languages, prioritize the distinction between roots (morphologically simple, carrying the principle meaning) and stems (roots plus derivational affixes ready for inflection).1 A DWS should maintain SIL's recommended distinction between "Inflectional Affixes" (associated with grammatical slots) and "Derivational Affixes" (mapping from one POS category to another).34

## **Lexical Relations and Semantic Networks**

Lexical relations describe how words occupy and divide semantic space.38 The move toward "linked data" in lexicography makes these relations the "backbone" of modern meaning representation.2

### **Comparative Analysis of Relations**

The user's minimal set identifies six primary relations: Part (pt), Specific (spec), Synonym (syn), Antonym (ant), Abbreviation (abbr), and Calendar (cal).20 While functional, this set lacks several relations that are now standard in the field.

| Relation Type | Standard Terminology | Practitioner Importance |
| :---- | :---- | :---- |
| Specific / Przypadek | **Hyponymy** | Horizontal navigation; "A is a type of B".38 |
| Generic / Typ | **Hypernymy** | Enables inheritance; "B is a broader category than A".37 |
| Part | **Meronymy** | Crucial for technical domains (body parts, engine parts).38 |
| Whole | **Holonymy** | Inverse of meronymy; "B is composed of A".38 |
| Synonyms | **Synonymy** | Essential for "active" dictionaries (thesauruses).18 |
| Antonyms | **Antonymy** | Powerful for adjectives; includes gradable (hot/cold) and complementary (dead/alive).38 |
| \- | **Troponymy** | Manner specification for verbs (e.g., to sprint is to run fast).38 |
| Calendar | \- | Highly project-specific; recommended for trimming in general systems.20 |

38

Modern practitioners emphasize that lexical relations should be bidirectional.40 For example, a DWS should automatically generate the "Whole" relation when the "Part" relation is assigned.20 Furthermore, the inclusion of "Compare" (cf.) is vital for relations that are not purely hierarchical, such as minimal contrasts or associative links.40

### **Semantic Domains and the Moe System**

Semantic domains provide a conceptual organization of the lexicon, moving beyond the arbitrary alphabetical order.44 The SIL FieldWorks system utilizes a hierarchical list of semantic domains (the "Ron Moe" list) which serves as an elicitation tool during "Rapid Word Collection" workshops.1 These domains range from the physical universe (Sky, Sun, Stars) to social interactions and grammar.20

While extensive, the value of semantic domains in a modern DWS is twofold:

1. **Term Identification:** They help lexicographers identify gaps in the lexicon and ensure consistent definitions within technical fields like "Earth Sciences".48  
2. **Cross-Linguistic Linking:** The ELEXIS Dictionary Matrix relies on semantic domains to link senses across different languages, providing a conceptual "pivot".4

## **Variant Types and Form Variation**

Lexical variation—differences in spelling, pronunciation, or regional usage—complicates information retrieval in digital systems.50 A modern DWS must distinguish between format variants and relational variants.50

### **Standardizing the Variant Range**

SIL FLEx provides a controlled list of "Variant Types" that should be considered for any robust DWS.20 The minimal LIFT set currently lacks a structured way to handle these, which often leads to the proliferation of duplicate or disconnected entries.13

* **Dialectal Variant:** Characteristically used by a specific demographic or geographic subset.20  
* **Free Variant:** Interchangeable forms used by the same speaker without discernible conditioning.20  
* **Irregularly Inflected Form:** Forms that deviate from standard rules, such as "men" for the plural of "man".20  
* **Spelling Variant:** Purely orthographic differences (e.g., color vs. colour).20

Modern practitioners recommend that these variants be linked to a single "lemma" or "canonical form" through structured metadata, allowing search engines to direct users from a variant to the main entry.4 This is particularly essential for the "lemma dilemma" in morphologically rich languages like Slovene or Nahuatl.13

## **Lexicographical Labels and Pragmatic Data**

Labels contextualize lexical units, providing guidance on marked language usage—informal language, jargon, or regional variation.57 They are indispensable instruments of description that promote communicative success for the user.57

### **Taxonomic Classes of Labels**

Practitioners identify several classes of labels that should be included in a DWS as controlled value ranges:

1. **Domain Labels:** Mark terms belonging to specialized fields (Anatomy, Computer Science).20  
2. **Regional Labels:** Indicate spatial distribution (e.g., British English vs. Australian slang).46  
3. **Register Labels:** Indicate stylistic level (formal, informal, colloquial, poetic).13  
4. **Usage/Sociolinguistic Labels:** Mark words that are offensive, taboo, or limited to specific text types.20  
5. **Temporal Labels:** Identify archaic, obsolete, or new (neologism) words.11

The minimal system's reliance on free-text "restrictions" and "usage" notes prevents the automated generation of targeted dictionary views (e.g., a "school dictionary" that filters out offensive terms).57 Adopting a controlled label range enables "tickbox lexicography," where lexicographers can quickly assign attributes that the software then uses to format entries for different audiences.3

## **Recommendation for Enlarging or Trimming the Minimal Set**

Based on the juxtaposition of the minimal LIFT ranges with the extensive SIL FLEx recommended values and modern practitioner trends, several modifications are proposed to optimize the dictionary writing system.

### **Recommended Trimmings**

Trimming is directed toward project-specific values that hinder broader interoperability or cause data redundancy.

* **Lexical Relations \- Remove "Calendar":** This is a highly specific semantic relation. In a general-purpose DWS, such relationships should be handled within the "Semantic Domain" hierarchy rather than as a primary lexical relation type. It does not provide the general ontological utility required for interchange.20  
* **POS \- Consolidate "Pro-form":** The minimal set categorizes Acronyms and Abbreviations as sub-types of Pro-form. In modern digital linguistics (e.g., TEI Lex-0), "Pronoun" should be a primary POS, while "Acronym" and "Abbreviation" are structural form types better managed under entry-level attributes or variant types.12  
* **Notes \- Merge "General," "Comment," and "Questions":** These three types frequently overlap in practitioner usage. Consolidating them into an "Editorial Note" vs. "Public Note" framework aligns with the best practices for neology tracking and collaborative editing.59

### **Recommended Enlargements**

Enlarging the set is essential to ensure the database can support the advanced features expected by modern users and automated systems.

* **POS \- Adopt Universal Dependencies (UD) Standard:** The minimal set is missing crucial categories for syntactic parsing. Adding "Proper Noun" (PROPN), "Auxiliary Verb" (AUX), and "Numeral" (NUM) is mandatory for ELEXIS compliance and linked data integration.12 "Conjunction" should be expanded to include "Coordinating" and "Subordinating" types.15  
* **Complex Form Types \- Full Adoption of SIL List:** The current absence of "Compound," "Derivative," "Idiom," and "Phrasal Verb" ranges is a critical failure point. These must be included to allow the system to handle MWEs as structured, linked data.13  
* **Variant Types \- Full Adoption of SIL List:** Structured ranges for "Dialectal," "Free," "Irregular," and "Spelling" variants are essential for modern search and retrieval, ensuring that allomorphic variations are linked to their canonical forms.12  
* **Lexical Relations \- Add Hierarchy and Manner:** "Hypernymy" (the reverse of Specific) and "Troponymy" (for verb manner) should be added to provide a complete hierarchical framework compatible with WordNet and other semantic networks.38  
* **Usage Labels \- Adopt Controlled Typology:** Replace free-text notes with controlled ranges for "Register," "Region," and "Domain." This transition enables the system to support "individualization"—customizing the dictionary output based on the user's profile.57

## **Implementation of Traits and Metadata in Digital Frameworks**

Dictionary writing systems like FLEx and Lexonomy rely on technical "traits" or attributes to provide instructions to the software's parsing and display engines.20 A minimal DWS should incorporate several of these as baseline metadata fields within its XML structure.

### **Recommended Trait Integration**

| Trait Name | Functional Purpose | Recommendation |
| :---- | :---- | :---- |
| **Catalog-Source-ID** | Links a project-specific category to a global standard (e.g., GOLD or UD).20 | Mandatory for all POS categories to ensure ELEXIS compatibility.26 |
| **Inflectable-Feature** | Marks whether a POS can take inflectional affixes (e.g., "nagr" for noun agreement).20 | Mandatory for Verbs and Nouns in inflectional languages.13 |
| **Leading/Trailing Symbol** | Automates formatting for bound forms (e.g., adding a hyphen "-" for affixes).20 | Required for all morpheme types that are not free words.20 |
| **Reverse-Label** | Automatically defines the inverse of a lexical relation (e.g., Part → Whole).20 | Mandatory for all hierarchical and partitive relations to maintain database integrity.13 |

20

The inclusion of these traits allows a developer to automate the tedious aspects of dictionary production, such as the generation of cross-references and the application of morphological rules.1 In systems like Lexonomy, these traits act as "logic constraints," determining which elements (e.g., example sentences) can be added to which parts of the entry (e.g., a specific sense).62

## **Future Directions: Graph Models and Linguistic Knowledge Bases**

The shift from tree-structured XML to graph-based data models represents the "cutting edge" of modern lexicography.13 While XML is proficient at representing hierarchical structures, it struggles with non-hierarchical phenomena such as entry-to-entry cross-references and complex hierarchies of sub-senses.13 The recently standardized "Data Model for Lexicography" (DMLex) aims to bridge this gap, treating the dictionary as a network of linked nodes rather than a nested tree.13

For a DWS developer, this means that even if the underlying storage remains XML (like LIFT or TEI), the *conceptual model* should be relational. Every "Phrasal Verb" or "Compound" should not just be a label, but a pointer to the constituent roots or particles, each of which should have its own identity in the database.13 This approach transforms the dictionary from a "book in a box" into a true "Linguistic Knowledge Base" capable of feeding modern AI tools like Large Language Models, which increasingly rely on structured lexical data to prevent hallucinations and biases.13

## **Conclusion on Lexicographic Best Practices for Minimal Type Ranges**

The optimization of a dictionary writing system requires a strategic alignment with international standards for interoperability while providing enough granular metadata to satisfy the descriptive needs of linguists. The juxtaposition of minimal LIFT ranges with the extensive catalogs of SIL FLEx reveals that a strictly "minimal" approach is often counterproductive in the digital age, as it fails to provide the structural indices required for automated search, linking, and processing.

The recommended "standardized minimal" set—which enlarges the POS range to include proper nouns and conjunctions, adopts the SIL framework for complex forms and variants, and utilizes controlled labels for pragmatics—provides the most robust foundation for any new dictionary project. This configuration ensures that the resulting data is not only useful for the immediate project but is also ready to be integrated into the global "Dictionary Matrix" of linked lexical resources, serving human users and machine systems with equal precision.4

#### **Cytowane prace**

1. Introduction to Lexicography for FieldWorks Language Explorer \- LanguageTechnology.org, otwierano: grudnia 19, 2025, [https://downloads.languagetechnology.org/fieldworks/Documentation/Intro%20to%20Lexicography/Introduction%20to%20Lexicography.htm](https://downloads.languagetechnology.org/fieldworks/Documentation/Intro%20to%20Lexicography/Introduction%20to%20Lexicography.htm)  
2. Standards for Representing Lexicographic Data: An Overview \- DARIAH-Campus, otwierano: grudnia 19, 2025, [https://campus.dariah.eu/resources/hosted/standards-for-representing-lexicographic-data-an-overview](https://campus.dariah.eu/resources/hosted/standards-for-representing-lexicographic-data-an-overview)  
3. ELEXIS Pathfinder to Computational Lexicography for Developers and Computational Linguists | DARIAH-Campus, otwierano: grudnia 19, 2025, [https://campus.dariah.eu/resources/pathfinders/elexis-pathfinder-to-computional-lexicography-for-developers-and-computational-linguists](https://campus.dariah.eu/resources/pathfinders/elexis-pathfinder-to-computional-lexicography-for-developers-and-computational-linguists)  
4. ELEXIS Data Model, otwierano: grudnia 19, 2025, [https://project.elex.is/wp-content/uploads/2019/04/ELEXIS\_Carole\_Tiberius\_DataModel\_ObserverEvent.pdf](https://project.elex.is/wp-content/uploads/2019/04/ELEXIS_Carole_Tiberius_DataModel_ObserverEvent.pdf)  
5. sillsdev/lift-standard: Automatically exported from code.google.com/p/lift-standard \- GitHub, otwierano: grudnia 19, 2025, [https://github.com/sillsdev/lift-standard](https://github.com/sillsdev/lift-standard)  
6. LIFT (Lexicon Interchange FormaT) \- Google Code, otwierano: grudnia 19, 2025, [https://code.google.com/archive/p/lift-standard](https://code.google.com/archive/p/lift-standard)  
7. Standards | SIL Global, otwierano: grudnia 19, 2025, [https://www.sil.org/language-technology/standards](https://www.sil.org/language-technology/standards)  
8. Technical Notes on LIFT used in FLEx \- LanguageTechnology.org, otwierano: grudnia 19, 2025, [https://downloads.languagetechnology.org/fieldworks/Documentation/Technical%20Notes%20on%20LIFT%20used%20in%20FLEx.pdf](https://downloads.languagetechnology.org/fieldworks/Documentation/Technical%20Notes%20on%20LIFT%20used%20in%20FLEx.pdf)  
9. TEI Lex-0: A baseline encoding for lexicographic data \- Universidade NOVA de Lisboa, otwierano: grudnia 19, 2025, [https://novaresearch.unl.pt/en/publications/tei-lex-0-a-baseline-encoding-for-lexicographic-data/](https://novaresearch.unl.pt/en/publications/tei-lex-0-a-baseline-encoding-for-lexicographic-data/)  
10. TEI Lex0 (dictionary encoding), otwierano: grudnia 19, 2025, [https://standards.clarin.eu/sis/views/view-format.xq?id=fLex0](https://standards.clarin.eu/sis/views/view-format.xq?id=fLex0)  
11. TEI Lex-0 Etym: Toward Terse Recommendations for the Encoding of Etymological Information \- OpenEdition Journals, otwierano: grudnia 19, 2025, [https://journals.openedition.org/jtei/4300](https://journals.openedition.org/jtei/4300)  
12. TEI Lex-0 In Action: Improving the Encoding of the Dictionary of the Academia das Ciências de Lisboa \- ResearchGate, otwierano: grudnia 19, 2025, [https://www.researchgate.net/publication/339209684\_TEI\_Lex-0\_In\_Action\_Improving\_the\_Encoding\_of\_the\_Dictionary\_of\_the\_Academia\_das\_Ciencias\_de\_Lisboa](https://www.researchgate.net/publication/339209684_TEI_Lex-0_In_Action_Improving_the_Encoding_of_the_Dictionary_of_the_Academia_das_Ciencias_de_Lisboa)  
13. Electronic lexicography in the 21st century (eLex 2025\) Book of abstracts, otwierano: grudnia 19, 2025, [https://elex.link/elex2025/wp-content/uploads/elex2025\_book\_of\_abstracts.pdf](https://elex.link/elex2025/wp-content/uploads/elex2025_book_of_abstracts.pdf)  
14. Genderal Ontology for Linguistic Description \- CLARIAH-NL, otwierano: grudnia 19, 2025, [https://static.vocabs.clariah.nl/docs/gold/2010.html](https://static.vocabs.clariah.nl/docs/gold/2010.html)  
15. The 8 Parts of Speech | Chart, Definition & Examples \- Scribbr, otwierano: grudnia 19, 2025, [https://www.scribbr.com/category/parts-of-speech/](https://www.scribbr.com/category/parts-of-speech/)  
16. Part of speech | Meaning, Examples, & English Grammar \- Britannica, otwierano: grudnia 19, 2025, [https://www.britannica.com/topic/part-of-speech](https://www.britannica.com/topic/part-of-speech)  
17. The 8 Parts of Speech: Rules and Examples | Grammarly, otwierano: grudnia 19, 2025, [https://www.grammarly.com/blog/parts-of-speech/the-8-parts-of-speech/](https://www.grammarly.com/blog/parts-of-speech/the-8-parts-of-speech/)  
18. Lexis in Linguistics | Definition & Examples \- Study.com, otwierano: grudnia 19, 2025, [https://study.com/academy/lesson/lexis-linguistics-definition-examples.html](https://study.com/academy/lesson/lexis-linguistics-definition-examples.html)  
19. Leveraging Dictionaries and Grammar Rules for the Creation of Educational Materials for Indigenous Languages \- ACL Anthology, otwierano: grudnia 19, 2025, [https://aclanthology.org/2025.americasnlp-1.13.pdf](https://aclanthology.org/2025.americasnlp-1.13.pdf)  
20. empty\_project\_list.xml.txt  
21. Language Basics – Academic Writing Skills, otwierano: grudnia 19, 2025, [https://uq.pressbooks.pub/academicwritingskills/chapter/language-and-grammar-basics/](https://uq.pressbooks.pub/academicwritingskills/chapter/language-and-grammar-basics/)  
22. 6.5 Functional categories – Essentials of Linguistics, 2nd edition \- eCampusOntario Pressbooks, otwierano: grudnia 19, 2025, [https://ecampusontario.pressbooks.pub/essentialsoflinguistics2/chapter/functional-categories/](https://ecampusontario.pressbooks.pub/essentialsoflinguistics2/chapter/functional-categories/)  
23. Lexical Words and Language Learning \- Text Inspector, otwierano: grudnia 19, 2025, [https://textinspector.com/lexical-words-and-language-learning/](https://textinspector.com/lexical-words-and-language-learning/)  
24. Parts of Speech Handout 2025, otwierano: grudnia 19, 2025, [https://www.apsu.edu/writingcenter/writing-resources/Parts-of-Speech-Handout-2025.pdf](https://www.apsu.edu/writingcenter/writing-resources/Parts-of-Speech-Handout-2025.pdf)  
25. 6 The Major Parts of Speech \- The WAC Clearinghouse, otwierano: grudnia 19, 2025, [https://wacclearinghouse.org/docs/books/sound/chapter6.pdf](https://wacclearinghouse.org/docs/books/sound/chapter6.pdf)  
26. ELEXIS Protocol for accessing dictionaries (1.2), otwierano: grudnia 19, 2025, [https://elexis-eu.github.io/elexis-rest/](https://elexis-eu.github.io/elexis-rest/)  
27. 8.6 Subcategories – Essential of Linguistics \- Maricopa Open Digital Press, otwierano: grudnia 19, 2025, [https://open.maricopa.edu/essentialsoflinguistics/chapter/8-7-subcategories/](https://open.maricopa.edu/essentialsoflinguistics/chapter/8-7-subcategories/)  
28. 10 Dictionaries \- The TEI Guidelines \- Text Encoding Initiative, otwierano: grudnia 19, 2025, [https://www.tei-c.org/release/doc/tei-p5-doc/en/html/DI.html](https://www.tei-c.org/release/doc/tei-p5-doc/en/html/DI.html)  
29. Grammatical Terms/Word Classes/Features of Sentences, otwierano: grudnia 19, 2025, [https://www.thrive-stw.com/documents/parents/homework/grammatical-terminology.pdf](https://www.thrive-stw.com/documents/parents/homework/grammatical-terminology.pdf)  
30. Grammatical number \- Wikipedia, otwierano: grudnia 19, 2025, [https://en.wikipedia.org/wiki/Grammatical\_number](https://en.wikipedia.org/wiki/Grammatical_number)  
31. The ELEXIS Interface for Interoperable Lexical Resources \- eLex Conferences, otwierano: grudnia 19, 2025, [https://elex.link/elex2019/wp-content/uploads/2019/09/eLex\_2019\_37.pdf](https://elex.link/elex2019/wp-content/uploads/2019/09/eLex_2019_37.pdf)  
32. 57\. Syntax and Lexicography, otwierano: grudnia 19, 2025, [https://user.phil.hhu.de/\~osswald/publications/osswald-HSK\_syntax\_lexicography.pdf](https://user.phil.hhu.de/~osswald/publications/osswald-HSK_syntax_lexicography.pdf)  
33. Categories \- FieldWorks \- SIL Language Technology, otwierano: grudnia 19, 2025, [https://software.sil.org/fieldworks/features/orientation-to-fieldworks/grammar/categories/](https://software.sil.org/fieldworks/features/orientation-to-fieldworks/grammar/categories/)  
34. The SIL FieldWorks Language Explorer Approach to Morphological Parsing \- Stanford University, otwierano: grudnia 19, 2025, [https://web.stanford.edu/group/cslipublications/cslipublications/TLS/TLS10-2006/TLS10\_Black\_Simons.pdf](https://web.stanford.edu/group/cslipublications/cslipublications/TLS/TLS10-2006/TLS10_Black_Simons.pdf)  
35. What Is a Noun? Definition, Types, and Examples \- Grammarly, otwierano: grudnia 19, 2025, [https://www.grammarly.com/blog/parts-of-speech/nouns/](https://www.grammarly.com/blog/parts-of-speech/nouns/)  
36. Lexical Approach 1 \- What does the lexical approach look like? \- British Council, otwierano: grudnia 19, 2025, [https://www.teachingenglish.org.uk/professional-development/teachers/knowing-subject/lexical-approach-1-what-does-lexical-approach](https://www.teachingenglish.org.uk/professional-development/teachers/knowing-subject/lexical-approach-1-what-does-lexical-approach)  
37. Lexical semantics \- Wikipedia, otwierano: grudnia 19, 2025, [https://en.wikipedia.org/wiki/Lexical\_semantics](https://en.wikipedia.org/wiki/Lexical_semantics)  
38. Lexical Relations to Know for Intro to Semantics and Pragmatics \- Fiveable, otwierano: grudnia 19, 2025, [https://fiveable.me/lists/lexical-relations](https://fiveable.me/lists/lexical-relations)  
39. LINGUISTICS, LEXICOGRAPHY, AND THE REVITALIZATION OF ENDANGERED LANGUAGES | Dictionary Lab, otwierano: grudnia 19, 2025, [https://dictionarylab.web.ox.ac.uk/files/endangeredlanguagespdf](https://dictionarylab.web.ox.ac.uk/files/endangeredlanguagespdf)  
40. Lexical relations in lexicography \- Christian Lehmann, otwierano: grudnia 19, 2025, [https://www.christianlehmann.eu/ling/ling\_meth/ling\_description/lexicography/relations\_in\_lexicography.html](https://www.christianlehmann.eu/ling/ling_meth/ling_description/lexicography/relations_in_lexicography.html)  
41. "Lexical Relations" in the English language | LanGeek, otwierano: grudnia 19, 2025, [https://langeek.co/en/grammar/course/1633/lexical-relations](https://langeek.co/en/grammar/course/1633/lexical-relations)  
42. TEI Lex-0 — A baseline encoding for lexicographic data \- GitHub Pages, otwierano: grudnia 19, 2025, [https://dariah-eric.github.io/lexicalresources/pages/TEILex0/TEILex0.html](https://dariah-eric.github.io/lexicalresources/pages/TEILex0/TEILex0.html)  
43. Lexical Semantics \- Study.com, otwierano: grudnia 19, 2025, [https://study.com/academy/lesson/lexical-semantics.html](https://study.com/academy/lesson/lexical-semantics.html)  
44. Dictionary & Lexicography Services \- Glossary, otwierano: grudnia 19, 2025, [https://sites.google.com/sil.org/dls-course/glossary](https://sites.google.com/sil.org/dls-course/glossary)  
45. The Lexical Perspective – The Discipline of Organizing: 4th Professional Edition, otwierano: grudnia 19, 2025, [https://berkeley.pressbooks.pub/tdo4p/chapter/the-lexical-perspective/](https://berkeley.pressbooks.pub/tdo4p/chapter/the-lexical-perspective/)  
46. March 2024 \- Oxford English Dictionary, otwierano: grudnia 19, 2025, [https://www.oed.com/information/updates/march-2024/](https://www.oed.com/information/updates/march-2024/)  
47. SIL FieldWorks Language Explorer (FLEx): Digitization of Field Data, otwierano: grudnia 19, 2025, [https://www.tezu.ernet.in/wmcfel/pdf/Cog/lexico/04.pdf](https://www.tezu.ernet.in/wmcfel/pdf/Cog/lexico/04.pdf)  
48. APPLYING TERMINOLOGICAL METHODS TO LEXICOGRAPHIC WORK: TERMS AND THEIR DOMAINS, otwierano: grudnia 19, 2025, [https://d-nb.info/1277050627/34](https://d-nb.info/1277050627/34)  
49. ELEXIS survey on licensing lexicographic data and software \- Euralex, otwierano: grudnia 19, 2025, [https://euralex.org/wp-content/themes/euralex/proceedings/Euralex%202020-2021/EURALEX2020-2021\_Vol2-p705-712.pdf](https://euralex.org/wp-content/themes/euralex/proceedings/Euralex%202020-2021/EURALEX2020-2021_Vol2-p705-712.pdf)  
50. Variant Terminology \- ASTM Digital Library, otwierano: grudnia 19, 2025, [https://dl.astm.org/books/book/585/chapter/103665/Variant-Terminology](https://dl.astm.org/books/book/585/chapter/103665/Variant-Terminology)  
51. The Role of Variation in Lexicography \- ResearchGate, otwierano: grudnia 19, 2025, [https://www.researchgate.net/publication/236803888\_The\_Role\_of\_Variation\_in\_Lexicography](https://www.researchgate.net/publication/236803888_The_Role_of_Variation_in_Lexicography)  
52. Lexical variation and the lexeme-lection-lect triangle \- Oxford Academic, otwierano: grudnia 19, 2025, [https://academic.oup.com/book/55109/chapter/423919495](https://academic.oup.com/book/55109/chapter/423919495)  
53. TEI Lex-0 In Action: Improving the Encoding of the Dictionary of the Academia das Ciências de Lisboa \- UNL, otwierano: grudnia 19, 2025, [https://research.unl.pt/ws/portalfiles/portal/16379084/eLex\_2019\_23.pdf](https://research.unl.pt/ws/portalfiles/portal/16379084/eLex_2019_23.pdf)  
54. Fieldworks Language Explorer (FLEx) \- PARADISEC, otwierano: grudnia 19, 2025, [https://www.paradisec.org.au/FLEx\_Workshop\_March\_2020.pdf](https://www.paradisec.org.au/FLEx_Workshop_March_2020.pdf)  
55. Glossary of grammatical terms \- Oxford English Dictionary, otwierano: grudnia 19, 2025, [https://www.oed.com/information/understanding-entries/glossary-grammatical-terms/](https://www.oed.com/information/understanding-entries/glossary-grammatical-terms/)  
56. LEX3: Transforming Legacy Dictionaries using Elexifier \- DARIAH-Campus, otwierano: grudnia 19, 2025, [https://campus.dariah.eu/resources/hosted/lex3-transforming-legacy-dictionaries-using-elexifier](https://campus.dariah.eu/resources/hosted/lex3-transforming-legacy-dictionaries-using-elexifier)  
57. A general typology of lexicographical labels, otwierano: grudnia 19, 2025, [https://scielo.org.za/scielo.php?script=sci\_abstract\&pid=S0041-47512011000300010\&lng=es\&nrm=iso\&tlng=en](https://scielo.org.za/scielo.php?script=sci_abstract&pid=S0041-47512011000300010&lng=es&nrm=iso&tlng=en)  
58. The role of subjectivity in lexicography: Experiments towards data-driven labeling of informality \- eLex Conferences, otwierano: grudnia 19, 2025, [https://elex.link/elex2025/wp-content/uploads/eLex2025-22-Risberg\_etal.pdf](https://elex.link/elex2025/wp-content/uploads/eLex2025-22-Risberg_etal.pdf)  
59. Structuring a Collection of Lexicographic Data for Different User and Usage Situations, otwierano: grudnia 19, 2025, [https://scielo.org.za/scielo.php?script=sci\_arttext\&pid=S2224-00392023000200002](https://scielo.org.za/scielo.php?script=sci_arttext&pid=S2224-00392023000200002)  
60. Best practices for labels | Resource Manager \- Google Cloud Documentation, otwierano: grudnia 19, 2025, [https://docs.cloud.google.com/resource-manager/docs/best-practices-labels](https://docs.cloud.google.com/resource-manager/docs/best-practices-labels)  
61. FieldWorks Lite (Beta) \- SIL Language Technology, otwierano: grudnia 19, 2025, [https://software.sil.org/fieldworks/download/fieldworks-lite/](https://software.sil.org/fieldworks/download/fieldworks-lite/)  
62. Lexonomy: Mastering the ELEXIS Dictionary Writing System \- DARIAH-Campus, otwierano: grudnia 19, 2025, [https://campus.dariah.eu/resources/hosted/lexonomy-mastering-the-elexis-dictionary-writing-system](https://campus.dariah.eu/resources/hosted/lexonomy-mastering-the-elexis-dictionary-writing-system)