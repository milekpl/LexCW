(:~
 : LIFT Validation Queries
 : 
 : XQuery module for data integrity checks and validation
 : LIFT 0.13 Namespace: http://fieldworks.sil.org/schemas/lift/0.13
 : 
 : @version 1.0
 : @author Dictionary App Team
 :)

module namespace validate = "http://dictionaryapp.local/xquery/validate";

declare namespace lift = "http://fieldworks.sil.org/schemas/lift/0.13";

(:~
 : CHECK DATABASE INTEGRITY - Comprehensive validation
 : 
 : @param $db-name Database name
 : @return Validation report
 :)
declare function validate:check-database(
    $db-name as xs:string
) as element(report) {
    try {
        let $entries := db:open($db-name)//lift:entry
        let $total-entries := count($entries)
        
        let $checks := (
            validate:check-duplicate-ids($db-name),
            validate:check-missing-lexical-units($db-name),
            validate:check-sense-order($db-name),
            validate:check-namespaces($db-name),
            validate:check-orphaned-relations($db-name)
        )
        
        let $errors := $checks[errors/error]
        let $has-errors := count($errors) > 0
        
        return
            <report>
                <status>{if ($has-errors) then 'FAILED' else 'PASSED'}</status>
                <database>{$db-name}</database>
                <total-entries>{$total-entries}</total-entries>
                <timestamp>{current-dateTime()}</timestamp>
                <checks>{$checks}</checks>
                <summary>
                    <total-checks>{count($checks)}</total-checks>
                    <passed>{count($checks[status = 'PASSED'])}</passed>
                    <failed>{count($checks[status = 'FAILED'])}</failed>
                    <warnings>{count($checks[status = 'WARNING'])}</warnings>
                </summary>
            </report>
    } catch * {
        <report>
            <status>ERROR</status>
            <message>Error running validation: {$err:description}</message>
            <code>{$err:code}</code>
        </report>
    }
};

(:~
 : CHECK DUPLICATE IDS - Find entries with duplicate IDs
 : 
 : @param $db-name Database name
 : @return Check result
 :)
declare function validate:check-duplicate-ids(
    $db-name as xs:string
) as element(check) {
    let $entries := db:open($db-name)//lift:entry
    let $duplicates :=
        for $id in distinct-values($entries/@id)
        let $count := count($entries[@id = $id])
        where $count > 1
        return
            <duplicate>
                <id>{$id}</id>
                <count>{$count}</count>
            </duplicate>
    
    return
        <check name="duplicate-ids">
            <status>{if (count($duplicates) = 0) then 'PASSED' else 'FAILED'}</status>
            <message>{
                if (count($duplicates) = 0) then
                    'No duplicate entry IDs found'
                else
                    concat('Found ', count($duplicates), ' duplicate entry ID(s)')
            }</message>
            {if (count($duplicates) > 0) then
                <errors>{$duplicates}</errors>
            else ()}
        </check>
};

(:~
 : CHECK MISSING LEXICAL UNITS - Find entries without lexical-unit
 : 
 : @param $db-name Database name
 : @return Check result
 :)
declare function validate:check-missing-lexical-units(
    $db-name as xs:string
) as element(check) {
    let $entries := db:open($db-name)//lift:entry
    let $missing :=
        for $entry in $entries
        where not($entry/lift:lexical-unit) or not($entry/lift:lexical-unit/lift:form)
        return
            <error>
                <entry-id>{$entry/@id/string()}</entry-id>
                <issue>{
                    if (not($entry/lift:lexical-unit)) then
                        'Missing lexical-unit element'
                    else
                        'Lexical-unit has no form elements'
                }</issue>
            </error>
    
    return
        <check name="missing-lexical-units">
            <status>{if (count($missing) = 0) then 'PASSED' else 'FAILED'}</status>
            <message>{
                if (count($missing) = 0) then
                    'All entries have valid lexical-units'
                else
                    concat('Found ', count($missing), ' entry(ies) with missing/invalid lexical-units')
            }</message>
            {if (count($missing) > 0) then
                <errors>{$missing}</errors>
            else ()}
        </check>
};

(:~
 : CHECK SENSE ORDER - Validate sense order attributes
 : 
 : @param $db-name Database name
 : @return Check result
 :)
declare function validate:check-sense-order(
    $db-name as xs:string
) as element(check) {
    let $entries := db:open($db-name)//lift:entry
    let $errors :=
        for $entry in $entries[lift:sense]
        let $senses := $entry/lift:sense
        let $orders := $senses/@order/number()
        let $expected := (0 to count($senses) - 1)
        let $sorted-orders := 
            for $o in $orders
            order by $o
            return $o
        where $sorted-orders != $expected
        return
            <error>
                <entry-id>{$entry/@id/string()}</entry-id>
                <expected>{string-join($expected, ', ')}</expected>
                <actual>{string-join($sorted-orders, ', ')}</actual>
            </error>
    
    return
        <check name="sense-order">
            <status>{if (count($errors) = 0) then 'PASSED' else 'FAILED'}</status>
            <message>{
                if (count($errors) = 0) then
                    'All sense orders are correct'
                else
                    concat('Found ', count($errors), ' entry(ies) with incorrect sense order')
            }</message>
            {if (count($errors) > 0) then
                <errors>{$errors}</errors>
            else ()}
        </check>
};

(:~
 : CHECK NAMESPACES - Verify LIFT 0.13 namespace usage
 : 
 : @param $db-name Database name
 : @return Check result
 :)
declare function validate:check-namespaces(
    $db-name as xs:string
) as element(check) {
    let $entries := db:open($db-name)//lift:entry
    let $errors :=
        for $entry in $entries
        let $ns := namespace-uri($entry)
        where $ns != 'http://fieldworks.sil.org/schemas/lift/0.13'
        return
            <error>
                <entry-id>{$entry/@id/string()}</entry-id>
                <namespace>{$ns}</namespace>
            </error>
    
    return
        <check name="namespaces">
            <status>{if (count($errors) = 0) then 'PASSED' else 'FAILED'}</status>
            <message>{
                if (count($errors) = 0) then
                    'All entries use correct LIFT 0.13 namespace'
                else
                    concat('Found ', count($errors), ' entry(ies) with incorrect namespace')
            }</message>
            {if (count($errors) > 0) then
                <errors>{$errors}</errors>
            else ()}
        </check>
};

(:~
 : CHECK ORPHANED RELATIONS - Find relations pointing to non-existent entries
 : 
 : @param $db-name Database name
 : @return Check result
 :)
declare function validate:check-orphaned-relations(
    $db-name as xs:string
) as element(check) {
    let $entries := db:open($db-name)//lift:entry
    let $all-entry-ids := $entries/@id/string()
    
    let $errors :=
        for $entry in $entries
        for $relation in $entry//lift:relation[@ref]
        let $ref := $relation/@ref/string()
        where not($ref = $all-entry-ids)
        return
            <error>
                <entry-id>{$entry/@id/string()}</entry-id>
                <relation-type>{$relation/@type/string()}</relation-type>
                <ref>{$ref}</ref>
                <issue>Referenced entry not found</issue>
            </error>
    
    return
        <check name="orphaned-relations">
            <status>{if (count($errors) = 0) then 'PASSED' else 'WARNING'}</status>
            <message>{
                if (count($errors) = 0) then
                    'No orphaned relations found'
                else
                    concat('Found ', count($errors), ' orphaned relation(s)')
            }</message>
            {if (count($errors) > 0) then
                <errors>{$errors}</errors>
            else ()}
        </check>
};

(:~
 : CHECK ENTRY - Validate a single entry
 : 
 : @param $db-name Database name
 : @param $entry-id Entry ID to validate
 : @return Validation result
 :)
declare function validate:check-entry(
    $db-name as xs:string,
    $entry-id as xs:string
) as element(report) {
    try {
        let $entry := db:open($db-name)//lift:entry[@id = $entry-id]
        
        return if (not($entry)) then
            <report>
                <status>ERROR</status>
                <entry-id>{$entry-id}</entry-id>
                <message>Entry not found</message>
            </report>
        else
            let $errors := (
                (: Check required @id :)
                if (not($entry/@id) or $entry/@id = '') then
                    <error type="missing-attribute">Entry must have an id attribute</error>
                else (),
                
                (: Check namespace :)
                if (namespace-uri($entry) != 'http://fieldworks.sil.org/schemas/lift/0.13') then
                    <error type="invalid-namespace">Entry must use LIFT 0.13 namespace</error>
                else (),
                
                (: Check lexical-unit :)
                if (not($entry/lift:lexical-unit)) then
                    <error type="missing-element">Entry must have a lexical-unit element</error>
                else if (not($entry/lift:lexical-unit/lift:form)) then
                    <error type="missing-element">Lexical-unit must have at least one form</error>
                else (),
                
                (: Check sense order :)
                if ($entry/lift:sense) then
                    let $senses := $entry/lift:sense
                    let $orders := $senses/@order/number()
                    let $expected := (0 to count($senses) - 1)
                    let $sorted-orders := 
                        for $o in $orders
                        order by $o
                        return $o
                    where $sorted-orders != $expected
                    return
                        <error type="invalid-order">
                            Sense orders must be consecutive starting from 0
                        </error>
                else (),
                
                (: Check for orphaned relations :)
                for $relation in $entry//lift:relation[@ref]
                let $ref := $relation/@ref/string()
                where not(db:open($db-name)//lift:entry[@id = $ref])
                return
                    <error type="orphaned-relation">
                        Relation references non-existent entry: {$ref}
                    </error>
            )
            
            return
                <report>
                    <status>{if (count($errors) = 0) then 'PASSED' else 'FAILED'}</status>
                    <entry-id>{$entry-id}</entry-id>
                    <timestamp>{current-dateTime()}</timestamp>
                    {if (count($errors) > 0) then
                        <errors count="{count($errors)}">{$errors}</errors>
                    else
                        <message>Entry is valid</message>
                    }
                </report>
    } catch * {
        <report>
            <status>ERROR</status>
            <entry-id>{$entry-id}</entry-id>
            <message>Error validating entry: {$err:description}</message>
            <code>{$err:code}</code>
        </report>
    }
};

(:~
 : FIX SENSE ORDER - Automatically fix sense order in an entry
 : 
 : @param $db-name Database name
 : @param $entry-id Entry ID to fix
 : @return Fix result
 :)
declare function validate:fix-sense-order(
    $db-name as xs:string,
    $entry-id as xs:string
) as element(result) {
    try {
        let $entry := db:open($db-name)//lift:entry[@id = $entry-id]
        
        return if (not($entry)) then
            <result status="error">
                <message>Entry not found</message>
                <entry-id>{$entry-id}</entry-id>
            </result>
        else if (not($entry/lift:sense)) then
            <result status="success">
                <message>Entry has no senses to fix</message>
                <entry-id>{$entry-id}</entry-id>
            </result>
        else
            (: Reorder senses :)
            let $fixed-entry := copy $e := $entry
                                modify (
                                    for $s at $pos in $e/lift:sense
                                    order by $s/@order
                                    return replace value of node $s/@order with ($pos - 1)
                                )
                                return $e
            
            (: Update dateModified :)
            let $final-entry := copy $e := $fixed-entry
                                modify replace value of node $e/@dateModified
                                with current-dateTime()
                                return $e
            
            (: Save to database :)
            let $replace := db:replace($db-name, concat($entry-id, '.xml'), $final-entry)
            
            return
                <result status="success">
                    <message>Sense order fixed successfully</message>
                    <entry-id>{$entry-id}</entry-id>
                    <sense-count>{count($final-entry/lift:sense)}</sense-count>
                    <timestamp>{current-dateTime()}</timestamp>
                </result>
    } catch * {
        <result status="error">
            <message>Error fixing sense order: {$err:description}</message>
            <code>{$err:code}</code>
        </result>
    }
};

(:~
 : DATABASE STATISTICS - Get comprehensive database stats
 : 
 : @param $db-name Database name
 : @return Statistics report
 :)
declare function validate:database-stats(
    $db-name as xs:string
) as element(stats) {
    try {
        let $entries := db:open($db-name)//lift:entry
        let $senses := $entries/lift:sense
        let $examples := $senses/lift:example
        
        return
            <stats>
                <database>{$db-name}</database>
                <timestamp>{current-dateTime()}</timestamp>
                <entries>
                    <total>{count($entries)}</total>
                    <with-senses>{count($entries[lift:sense])}</with-senses>
                    <without-senses>{count($entries[not(lift:sense)])}</without-senses>
                </entries>
                <senses>
                    <total>{count($senses)}</total>
                    <average-per-entry>{
                        if (count($entries) > 0) then
                            round-half-to-even(count($senses) div count($entries), 2)
                        else 0
                    }</average-per-entry>
                </senses>
                <examples>
                    <total>{count($examples)}</total>
                    <average-per-sense>{
                        if (count($senses) > 0) then
                            round-half-to-even(count($examples) div count($senses), 2)
                        else 0
                    }</average-per-sense>
                </examples>
                <relations>
                    <total>{count($entries//lift:relation)}</total>
                    <entry-level>{count($entries/lift:relation)}</entry-level>
                    <sense-level>{count($senses/lift:relation)}</sense-level>
                </relations>
            </stats>
    } catch * {
        <stats>
            <error>Error getting statistics: {$err:description}</error>
            <code>{$err:code}</code>
        </stats>
    }
};
