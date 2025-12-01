(:~
 : LIFT Entry CRUD Operations
 : 
 : XQuery module for BaseX operations on LIFT entries
 : LIFT 0.13 Namespace: http://fieldworks.sil.org/schemas/lift/0.13
 : 
 : @version 1.0
 : @author Dictionary App Team
 :)

module namespace entry = "http://dictionaryapp.local/xquery/entry";

declare namespace lift = "http://fieldworks.sil.org/schemas/lift/0.13";

(:~
 : CREATE - Insert a new LIFT entry into the database
 : 
 : @param $db-name Database name
 : @param $entry-xml LIFT entry XML as string
 : @return Success/error message
 :)
declare function entry:create(
    $db-name as xs:string,
    $entry-xml as xs:string
) as element(result) {
    try {
        let $entry := parse-xml($entry-xml)//lift:entry
        let $entry-id := $entry/@id/string()
        
        (: Validate entry has required fields :)
        let $validation := entry:validate-entry($entry)
        
        return if ($validation/@valid = 'false') then
            <result status="error">
                <message>Validation failed</message>
                {$validation/errors}
            </result>
        else
            (: Check if entry already exists :)
            let $exists := db:open($db-name)//lift:entry[@id = $entry-id]
            
            return if ($exists) then
                <result status="error">
                    <message>Entry with ID {$entry-id} already exists</message>
                    <entry-id>{$entry-id}</entry-id>
                </result>
            else
                (: Insert entry into database :)
                let $insert := db:add($db-name, $entry, concat($entry-id, '.xml'))
                return
                    <result status="success">
                        <message>Entry created successfully</message>
                        <entry-id>{$entry-id}</entry-id>
                        <timestamp>{current-dateTime()}</timestamp>
                    </result>
    } catch * {
        <result status="error">
            <message>Error creating entry: {$err:description}</message>
            <code>{$err:code}</code>
        </result>
    }
};

(:~
 : READ - Retrieve a LIFT entry by ID
 : 
 : @param $db-name Database name
 : @param $entry-id Entry ID to retrieve
 : @return LIFT entry XML or error
 :)
declare function entry:read(
    $db-name as xs:string,
    $entry-id as xs:string
) as element() {
    try {
        let $entry := db:open($db-name)//lift:entry[@id = $entry-id]
        
        return if ($entry) then
            <result status="success">
                <entry>{$entry}</entry>
            </result>
        else
            <result status="error">
                <message>Entry not found</message>
                <entry-id>{$entry-id}</entry-id>
            </result>
    } catch * {
        <result status="error">
            <message>Error reading entry: {$err:description}</message>
            <code>{$err:code}</code>
        </result>
    }
};

(:~
 : READ ALL - Retrieve all LIFT entries with pagination
 : 
 : @param $db-name Database name
 : @param $offset Starting position (0-indexed)
 : @param $limit Maximum number of results
 : @return List of LIFT entries
 :)
declare function entry:read-all(
    $db-name as xs:string,
    $offset as xs:integer,
    $limit as xs:integer
) as element(result) {
    try {
        let $all-entries := db:open($db-name)//lift:entry
        let $total := count($all-entries)
        let $entries := subsequence($all-entries, $offset + 1, $limit)
        
        return
            <result status="success">
                <total>{$total}</total>
                <offset>{$offset}</offset>
                <limit>{$limit}</limit>
                <count>{count($entries)}</count>
                <entries>{$entries}</entries>
            </result>
    } catch * {
        <result status="error">
            <message>Error reading entries: {$err:description}</message>
            <code>{$err:code}</code>
        </result>
    }
};

(:~
 : UPDATE - Replace an existing LIFT entry
 : 
 : @param $db-name Database name
 : @param $entry-id Entry ID to update
 : @param $entry-xml New LIFT entry XML as string
 : @return Success/error message
 :)
declare function entry:update(
    $db-name as xs:string,
    $entry-id as xs:string,
    $entry-xml as xs:string
) as element(result) {
    try {
        let $new-entry := parse-xml($entry-xml)//lift:entry
        let $new-entry-id := $new-entry/@id/string()
        
        (: Validate IDs match :)
        return if ($entry-id != $new-entry-id) then
            <result status="error">
                <message>Entry ID mismatch: {$entry-id} != {$new-entry-id}</message>
            </result>
        else
            (: Validate entry structure :)
            let $validation := entry:validate-entry($new-entry)
            
            return if ($validation/@valid = 'false') then
                <result status="error">
                    <message>Validation failed</message>
                    {$validation/errors}
                </result>
            else
                (: Find existing entry :)
                let $existing := db:open($db-name)//lift:entry[@id = $entry-id]
                
                return if (not($existing)) then
                    <result status="error">
                        <message>Entry not found</message>
                        <entry-id>{$entry-id}</entry-id>
                    </result>
                else
                    (: Update dateModified :)
                    let $updated-entry := copy $e := $new-entry
                                          modify replace value of node $e/@dateModified
                                          with current-dateTime()
                                          return $e
                    
                    (: Replace entry in database :)
                    let $replace := db:replace($db-name, concat($entry-id, '.xml'), $updated-entry)
                    
                    return
                        <result status="success">
                            <message>Entry updated successfully</message>
                            <entry-id>{$entry-id}</entry-id>
                            <timestamp>{current-dateTime()}</timestamp>
                        </result>
    } catch * {
        <result status="error">
            <message>Error updating entry: {$err:description}</message>
            <code>{$err:code}</code>
        </result>
    }
};

(:~
 : DELETE - Remove a LIFT entry from the database
 : 
 : @param $db-name Database name
 : @param $entry-id Entry ID to delete
 : @return Success/error message
 :)
declare function entry:delete(
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
        else
            (: Delete entry from database :)
            let $delete := db:delete($db-name, concat($entry-id, '.xml'))
            
            return
                <result status="success">
                    <message>Entry deleted successfully</message>
                    <entry-id>{$entry-id}</entry-id>
                    <timestamp>{current-dateTime()}</timestamp>
                </result>
    } catch * {
        <result status="error">
            <message>Error deleting entry: {$err:description}</message>
            <code>{$err:code}</code>
        </result>
    }
};

(:~
 : SEARCH - Find entries by lexical unit text
 : 
 : @param $db-name Database name
 : @param $search-term Search term (case-insensitive)
 : @param $lang Language code (optional, searches all if empty)
 : @param $limit Maximum results
 : @return Matching entries
 :)
declare function entry:search(
    $db-name as xs:string,
    $search-term as xs:string,
    $lang as xs:string,
    $limit as xs:integer
) as element(result) {
    try {
        let $entries := 
            if ($lang != '') then
                db:open($db-name)//lift:entry[
                    .//lift:lexical-unit/lift:form[@lang = $lang]/lift:text
                    [contains(lower-case(.), lower-case($search-term))]
                ]
            else
                db:open($db-name)//lift:entry[
                    .//lift:lexical-unit/lift:form/lift:text
                    [contains(lower-case(.), lower-case($search-term))]
                ]
        
        let $limited := subsequence($entries, 1, $limit)
        
        return
            <result status="success">
                <total>{count($entries)}</total>
                <count>{count($limited)}</count>
                <limit>{$limit}</limit>
                <search-term>{$search-term}</search-term>
                <lang>{$lang}</lang>
                <entries>{$limited}</entries>
            </result>
    } catch * {
        <result status="error">
            <message>Error searching entries: {$err:description}</message>
            <code>{$err:code}</code>
        </result>
    }
};

(:~
 : VALIDATE ENTRY - Check LIFT entry structure
 : 
 : @param $entry LIFT entry element
 : @return Validation result
 :)
declare function entry:validate-entry(
    $entry as element(lift:entry)
) as element(validation) {
    let $errors := (
        (: Check required @id attribute :)
        if (not($entry/@id) or $entry/@id = '') then
            <error type="missing-attribute">Entry must have an id attribute</error>
        else (),
        
        (: Check required lexical-unit :)
        if (not($entry/lift:lexical-unit)) then
            <error type="missing-element">Entry must have a lexical-unit element</error>
        else (),
        
        (: Check lexical-unit has at least one form :)
        if ($entry/lift:lexical-unit and not($entry/lift:lexical-unit/lift:form)) then
            <error type="missing-element">Lexical-unit must have at least one form element</error>
        else (),
        
        (: Check namespace :)
        if (not(namespace-uri($entry) = 'http://fieldworks.sil.org/schemas/lift/0.13')) then
            <error type="invalid-namespace">Entry must use LIFT 0.13 namespace</error>
        else ()
    )
    
    return
        <validation valid="{if (count($errors) = 0) then 'true' else 'false'}">
            {if (count($errors) > 0) then
                <errors count="{count($errors)}">{$errors}</errors>
            else ()}
        </validation>
};

(:~
 : GET ENTRY COUNT - Count total entries in database
 : 
 : @param $db-name Database name
 : @return Count result
 :)
declare function entry:count(
    $db-name as xs:string
) as element(result) {
    try {
        let $count := count(db:open($db-name)//lift:entry)
        
        return
            <result status="success">
                <count>{$count}</count>
                <database>{$db-name}</database>
            </result>
    } catch * {
        <result status="error">
            <message>Error counting entries: {$err:description}</message>
            <code>{$err:code}</code>
        </result>
    }
};
