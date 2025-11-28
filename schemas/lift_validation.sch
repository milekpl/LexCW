<?xml version="1.0" encoding="UTF-8"?>
<schema xmlns="http://purl.oclc.org/dsdl/schematron"
        xmlns:lift="http://code.google.com/p/lift-standard"
        queryBinding="xslt2">
    
    <title>LIFT Dictionary Validation Rules</title>
    <ns prefix="lift" uri="http://code.google.com/p/lift-standard"/>
    
    <!-- R1: Entry Level Validation -->
    
    <pattern id="entry-required-fields">
        <title>R1.1: Entry Required Fields</title>
        
        <rule context="lift:entry">
            <!-- R1.1.1: Entry ID is required and must be non-empty -->
            <assert test="@id and string-length(@id) > 0">
                R1.1.1 Violation: Entry ID is required and must be non-empty
            </assert>
            
            <!-- R1.1.2: Lexical unit is required -->
            <assert test="lift:lexical-unit">
                R1.1.2 Violation: Lexical unit is required
            </assert>
            
            <!-- R1.1.3: At least one sense is required -->
            <assert test="lift:sense">
                R1.1.3 Violation: At least one sense is required per entry
            </assert>
        </rule>
        
        <rule context="lift:lexical-unit">
            <!-- R1.1.2: Lexical unit must contain at least one language form -->
            <assert test="lift:form">
                R1.1.2 Violation: Lexical unit must contain at least one language entry
            </assert>
        </rule>
    </pattern>
    
    <pattern id="entry-format-validation">
        <title>R1.2: Entry Format Validation</title>
        
        <rule context="lift:entry/@id">
            <!-- R1.2.1: Entry ID format validation (allows spaces per LIFT standard) -->
            <assert test="matches(., '^[a-zA-Z0-9_\- ]+$')">
                R1.2.1 Violation: Invalid entry ID format '<value-of select="."/>'. Use only letters, numbers, underscores, hyphens, and spaces
            </assert>
        </rule>
    </pattern>
    
    <!-- R2: Sense Level Validation -->
    
    <pattern id="sense-required-fields">
        <title>R2.1: Sense Required Fields</title>
        
        <rule context="lift:sense">
            <!-- R2.1.1: Sense ID is required -->
            <assert test="@id and string-length(@id) > 0">
                R2.1.1 Violation: Sense ID is required and must be non-empty
            </assert>
            
            <!-- R2.1.2: Sense definition OR gloss is required (except for variants) -->
            <assert test="lift:definition or lift:gloss or @ref">
                R2.1.2 Violation: Sense must have definition, gloss, or be a variant reference
            </assert>
        </rule>
    </pattern>
    
    <pattern id="sense-content-validation">
        <title>R2.2: Sense Content Validation</title>
        
        <rule context="lift:sense/lift:definition/lift:form/lift:text">
            <!-- R2.2.1: Sense definitions must be non-empty -->
            <assert test="string-length(normalize-space(.)) > 0">
                R2.2.1 Violation: Sense definition cannot be empty
            </assert>
        </rule>
        
        <rule context="lift:sense/lift:gloss/lift:text">
            <!-- R2.2.2: Sense glosses must be non-empty -->
            <assert test="string-length(normalize-space(.)) > 0">
                R2.2.2 Violation: Sense gloss cannot be empty
            </assert>
        </rule>
        
        <rule context="lift:example/lift:form/lift:text">
            <!-- R2.2.3: Example texts must be non-empty -->
            <assert test="string-length(normalize-space(.)) > 0">
                R2.2.3 Violation: Example text cannot be empty
            </assert>
        </rule>
    </pattern>
    
    <!-- R3: Note and Multilingual Content Validation -->
    
    <pattern id="note-validation">
        <title>R3.1: Note Structure Validation</title>
        
        <rule context="lift:entry | lift:sense">
            <!-- R3.1.1: Note types must be unique per element -->
            <assert test="count(lift:note[@type]) = count(distinct-values(lift:note/@type))">
                R3.1.1 Violation: Note types must be unique per entry/sense
            </assert>
        </rule>
        
        <rule context="lift:note/lift:form/lift:text">
            <!-- R3.1.2: Note content must be non-empty -->
            <assert test="string-length(normalize-space(.)) > 0">
                R3.1.2 Violation: Note content cannot be empty
            </assert>
        </rule>
    </pattern>
    
    <!-- R4: Pronunciation Validation -->
    
    <pattern id="pronunciation-validation">
        <title>R4.1: Pronunciation Format Validation</title>
        
        <rule context="lift:pronunciation/lift:form">
            <!-- R4.1.1: Pronunciation language restricted to seh-fonipa -->
            <assert test="@lang = 'seh-fonipa'">
                R4.1.1 Violation: Pronunciation language must be 'seh-fonipa', found: '<value-of select="@lang"/>'
            </assert>
        </rule>
        
        <rule context="lift:pronunciation/lift:form[@lang='seh-fonipa']/lift:text">
            <!-- R4.1.2: IPA character validation -->
            <assert test="matches(., '^[ɑæɒəɜɪiʊuʌeɛoɔbdfghjklmnprstwvzðθŋʃʒːˈˌᵻ \.]*$')">
                R4.1.2 Violation: Invalid IPA characters in pronunciation
            </assert>
            
            <!-- R4.2.1: No double stress markers -->
            <assert test="not(matches(., 'ˈˈ|ˌˌ|ˈˌ|ˌˈ'))">
                R4.2.1 Violation: Double stress markers not allowed
            </assert>
            
            <!-- R4.2.2: No double length markers -->
            <assert test="not(contains(., 'ːː'))">
                R4.2.2 Violation: Double length markers not allowed
            </assert>
        </rule>
    </pattern>
    
    <!-- R5: Relation and Reference Validation -->
    
    <pattern id="relation-validation">
        <title>R5: Relation Validation</title>
        
        <rule context="lift:relation">
            <!-- R5.1.1 & R5.1.2: Reference integrity (requires external validation) -->
            <assert test="@ref">
                R5.1.1 Violation: Relation must have a reference
            </assert>
            
            <!-- R5.2.1: Relation type validation (requires LIFT ranges) -->
            <assert test="@type">
                R5.2.1 Violation: Relation must have a type
            </assert>
        </rule>
    </pattern>
    
    <!-- R8: LIFT Schema Advanced Validation -->
    
    <pattern id="multitext-language-uniqueness">
        <title>R8.2.2: Unique language codes per multitext</title>
        
        <rule context="lift:form/parent::*">
            <assert test="count(lift:form[@lang]) = count(distinct-values(lift:form/@lang))">
                R8.2.2 Violation: Duplicate language code in multitext content
            </assert>
        </rule>
    </pattern>
    
    <pattern id="date-validation">
        <title>R8.3: Date and DateTime Validation</title>
        
        <rule context="*[@dateCreated]">
            <!-- R8.3.1: Date format validation -->
            <assert test="matches(@dateCreated, '^\d{4}-\d{2}-\d{2}(T\d{2}:\d{2}:\d{2}(\.\d+)?(Z|[+-]\d{2}:\d{2})?)?$')">
                R8.3.1 Violation: Invalid date format in dateCreated. Use ISO 8601 format
            </assert>
        </rule>
        
        <rule context="*[@dateModified]">
            <!-- R8.3.1: Date format validation -->
            <assert test="matches(@dateModified, '^\d{4}-\d{2}-\d{2}(T\d{2}:\d{2}:\d{2}(\.\d+)?(Z|[+-]\d{2}:\d{2})?)?$')">
                R8.3.1 Violation: Invalid date format in dateModified. Use ISO 8601 format
            </assert>
        </rule>
        
        <rule context="*[@dateDeleted]">
            <!-- R8.3.1: Date format validation -->
            <assert test="matches(@dateDeleted, '^\d{4}-\d{2}-\d{2}(T\d{2}:\d{2}:\d{2}(\.\d+)?(Z|[+-]\d{2}:\d{2})?)?$')">
                R8.3.1 Violation: Invalid date format in dateDeleted. Use ISO 8601 format
            </assert>
        </rule>
    </pattern>
    
    <pattern id="media-validation">
        <title>R8.1: Media and Resource Validation</title>
        
        <rule context="lift:media">
            <!-- R8.1.1: Media references must have href -->
            <assert test="@href">
                R8.1.1 Violation: Media element must have href attribute
            </assert>
        </rule>
        
        <rule context="lift:illustration">
            <!-- R8.1.2: Illustration references must have href -->
            <assert test="@href">
                R8.1.2 Violation: Illustration element must have href attribute
            </assert>
        </rule>
    </pattern>
    
    <pattern id="field-uniqueness">
        <title>R8.6.1: Field type uniqueness</title>
        
        <rule context="*[lift:field]">
            <assert test="count(lift:field[@type]) = count(distinct-values(lift:field/@type))">
                R8.6.1 Violation: Field types must be unique within parent element
            </assert>
        </rule>
    </pattern>
    
    <pattern id="translation-uniqueness">
        <title>R8.9.1: Translation type uniqueness</title>
        
        <rule context="*[lift:translation]">
            <assert test="count(lift:translation[@type]) = count(distinct-values(lift:translation/@type))">
                R8.9.1 Violation: Translation types must be unique within parent element
            </assert>
        </rule>
    </pattern>
    
    <pattern id="subsense-depth">
        <title>R8.7.1: Subsense depth limits</title>
        
        <rule context="lift:sense/lift:subsense/lift:subsense/lift:subsense">
            <assert test="false()">
                R8.7.1 Violation: Subsense nesting exceeds maximum depth of 3 levels
            </assert>
        </rule>
    </pattern>
    
</schema>
