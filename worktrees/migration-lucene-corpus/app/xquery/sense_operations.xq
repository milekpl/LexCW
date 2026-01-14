(:~
 : LIFT Sense CRUD Operations
 : 
 : XQuery module for sense-level operations within LIFT entries
 : LIFT 0.13 Namespace: http://fieldworks.sil.org/schemas/lift/0.13
 : 
 : @version 1.0
 : @author Dictionary App Team
 :)

module namespace sense = "http://dictionaryapp.local/xquery/sense";

declare namespace lift = "http://fieldworks.sil.org/schemas/lift/0.13";

(:~
 : ADD SENSE - Add a new sense to an existing entry
 : 
 : @param $db-name Database name
 : @param $entry-id Entry ID to add sense to
 : @param $sense-xml Sense XML as string
 : @return Success/error message
 :)
declare function sense:add(
    $db-name as xs:string,
    $entry-id as xs:string,
    $sense-xml as xs:string
) as element(result) {
    try {
        let $new-sense := parse-xml($sense-xml)//lift:sense
        let $sense-id := $new-sense/@id/string()
        
        (: Find the entry :)
        let $entry := db:open($db-name)//lift:entry[@id = $entry-id]
        
        return if (not($entry)) then
            <result status="error">
                <message>Entry not found</message>
                <entry-id>{$entry-id}</entry-id>
            </result>
        else
            (: Check if sense ID already exists :)
            let $existing-sense := $entry/lift:sense[@id = $sense-id]
            
            return if ($existing-sense) then
                <result status="error">
                    <message>Sense with ID {$sense-id} already exists in entry</message>
                    <sense-id>{$sense-id}</sense-id>
                </result>
            else
                (: Calculate new order value :)
                let $max-order := max($entry/lift:sense/@order/number())
                let $new-order := if ($max-order) then $max-order + 1 else 0
                
                (: Set order attribute :)
                let $ordered-sense := copy $s := $new-sense
                                      modify replace value of node $s/@order
                                      with $new-order
                                      return $s
                
                (: Insert sense into entry :)
                let $updated-entry := copy $e := $entry
                                      modify insert node $ordered-sense into $e
                                      return $e
                
                (: Update dateModified :)
                let $final-entry := copy $e := $updated-entry
                                    modify replace value of node $e/@dateModified
                                    with current-dateTime()
                                    return $e
                
                (: Save to database :)
                let $replace := db:replace($db-name, concat($entry-id, '.xml'), $final-entry)
                
                return
                    <result status="success">
                        <message>Sense added successfully</message>
                        <entry-id>{$entry-id}</entry-id>
                        <sense-id>{$sense-id}</sense-id>
                        <order>{$new-order}</order>
                        <timestamp>{current-dateTime()}</timestamp>
                    </result>
    } catch * {
        <result status="error">
            <message>Error adding sense: {$err:description}</message>
            <code>{$err:code}</code>
        </result>
    }
};

(:~
 : UPDATE SENSE - Update an existing sense
 : 
 : @param $db-name Database name
 : @param $entry-id Entry ID containing the sense
 : @param $sense-id Sense ID to update
 : @param $sense-xml New sense XML as string
 : @return Success/error message
 :)
declare function sense:update(
    $db-name as xs:string,
    $entry-id as xs:string,
    $sense-id as xs:string,
    $sense-xml as xs:string
) as element(result) {
    try {
        let $new-sense := parse-xml($sense-xml)//lift:sense
        let $new-sense-id := $new-sense/@id/string()
        
        (: Validate IDs match :)
        return if ($sense-id != $new-sense-id) then
            <result status="error">
                <message>Sense ID mismatch: {$sense-id} != {$new-sense-id}</message>
            </result>
        else
            (: Find the entry :)
            let $entry := db:open($db-name)//lift:entry[@id = $entry-id]
            
            return if (not($entry)) then
                <result status="error">
                    <message>Entry not found</message>
                    <entry-id>{$entry-id}</entry-id>
                </result>
            else
                (: Find the sense :)
                let $existing-sense := $entry/lift:sense[@id = $sense-id]
                
                return if (not($existing-sense)) then
                    <result status="error">
                        <message>Sense not found</message>
                        <sense-id>{$sense-id}</sense-id>
                    </result>
                else
                    (: Preserve order attribute :)
                    let $order := $existing-sense/@order
                    let $ordered-sense := copy $s := $new-sense
                                          modify (
                                              if ($s/@order) then
                                                  replace value of node $s/@order with $order
                                              else
                                                  insert node attribute order {$order} into $s
                                          )
                                          return $s
                    
                    (: Replace sense in entry :)
                    let $updated-entry := copy $e := $entry
                                          modify replace node $e/lift:sense[@id = $sense-id]
                                          with $ordered-sense
                                          return $e
                    
                    (: Update dateModified :)
                    let $final-entry := copy $e := $updated-entry
                                        modify replace value of node $e/@dateModified
                                        with current-dateTime()
                                        return $e
                    
                    (: Save to database :)
                    let $replace := db:replace($db-name, concat($entry-id, '.xml'), $final-entry)
                    
                    return
                        <result status="success">
                            <message>Sense updated successfully</message>
                            <entry-id>{$entry-id}</entry-id>
                            <sense-id>{$sense-id}</sense-id>
                            <timestamp>{current-dateTime()}</timestamp>
                        </result>
    } catch * {
        <result status="error">
            <message>Error updating sense: {$err:description}</message>
            <code>{$err:code}</code>
        </result>
    }
};

(:~
 : DELETE SENSE - Remove a sense from an entry
 : 
 : @param $db-name Database name
 : @param $entry-id Entry ID containing the sense
 : @param $sense-id Sense ID to delete
 : @return Success/error message
 :)
declare function sense:delete(
    $db-name as xs:string,
    $entry-id as xs:string,
    $sense-id as xs:string
) as element(result) {
    try {
        (: Find the entry :)
        let $entry := db:open($db-name)//lift:entry[@id = $entry-id]
        
        return if (not($entry)) then
            <result status="error">
                <message>Entry not found</message>
                <entry-id>{$entry-id}</entry-id>
            </result>
        else
            (: Find the sense :)
            let $sense := $entry/lift:sense[@id = $sense-id]
            
            return if (not($sense)) then
                <result status="error">
                    <message>Sense not found</message>
                    <sense-id>{$sense-id}</sense-id>
                </result>
            else
                (: Delete sense from entry :)
                let $updated-entry := copy $e := $entry
                                      modify delete node $e/lift:sense[@id = $sense-id]
                                      return $e
                
                (: Reorder remaining senses :)
                let $reordered-entry := sense:reorder-senses($updated-entry)
                
                (: Update dateModified :)
                let $final-entry := copy $e := $reordered-entry
                                    modify replace value of node $e/@dateModified
                                    with current-dateTime()
                                    return $e
                
                (: Save to database :)
                let $replace := db:replace($db-name, concat($entry-id, '.xml'), $final-entry)
                
                return
                    <result status="success">
                        <message>Sense deleted successfully</message>
                        <entry-id>{$entry-id}</entry-id>
                        <sense-id>{$sense-id}</sense-id>
                        <timestamp>{current-dateTime()}</timestamp>
                    </result>
    } catch * {
        <result status="error">
            <message>Error deleting sense: {$err:description}</message>
            <code>{$err:code}</code>
        </result>
    }
};

(:~
 : REORDER SENSE - Change sense order within an entry
 : 
 : @param $db-name Database name
 : @param $entry-id Entry ID containing the sense
 : @param $sense-id Sense ID to reorder
 : @param $new-order New order position (0-indexed)
 : @return Success/error message
 :)
declare function sense:reorder(
    $db-name as xs:string,
    $entry-id as xs:string,
    $sense-id as xs:string,
    $new-order as xs:integer
) as element(result) {
    try {
        (: Find the entry :)
        let $entry := db:open($db-name)//lift:entry[@id = $entry-id]
        
        return if (not($entry)) then
            <result status="error">
                <message>Entry not found</message>
                <entry-id>{$entry-id}</entry-id>
            </result>
        else
            (: Find the sense :)
            let $sense := $entry/lift:sense[@id = $sense-id]
            
            return if (not($sense)) then
                <result status="error">
                    <message>Sense not found</message>
                    <sense-id>{$sense-id}</sense-id>
                </result>
            else
                let $current-order := $sense/@order/number()
                let $total-senses := count($entry/lift:sense)
                
                (: Validate new order :)
                return if ($new-order < 0 or $new-order >= $total-senses) then
                    <result status="error">
                        <message>Invalid order: must be between 0 and {$total-senses - 1}</message>
                        <new-order>{$new-order}</new-order>
                    </result>
                else if ($current-order = $new-order) then
                    <result status="success">
                        <message>Sense already at requested position</message>
                        <entry-id>{$entry-id}</entry-id>
                        <sense-id>{$sense-id}</sense-id>
                        <order>{$new-order}</order>
                    </result>
                else
                    (: Reorder senses :)
                    let $updated-entry := 
                        copy $e := $entry
                        modify (
                            (: Update all sense orders :)
                            for $s at $pos in $e/lift:sense
                            order by $s/@order
                            return
                                if ($s/@id = $sense-id) then
                                    replace value of node $s/@order with $new-order
                                else if ($current-order < $new-order) then
                                    (: Moving down - shift up senses in between :)
                                    if ($s/@order > $current-order and $s/@order <= $new-order) then
                                        replace value of node $s/@order with ($s/@order - 1)
                                    else ()
                                else
                                    (: Moving up - shift down senses in between :)
                                    if ($s/@order >= $new-order and $s/@order < $current-order) then
                                        replace value of node $s/@order with ($s/@order + 1)
                                    else ()
                        )
                        return $e
                    
                    (: Update dateModified :)
                    let $final-entry := copy $e := $updated-entry
                                        modify replace value of node $e/@dateModified
                                        with current-dateTime()
                                        return $e
                    
                    (: Save to database :)
                    let $replace := db:replace($db-name, concat($entry-id, '.xml'), $final-entry)
                    
                    return
                        <result status="success">
                            <message>Sense reordered successfully</message>
                            <entry-id>{$entry-id}</entry-id>
                            <sense-id>{$sense-id}</sense-id>
                            <old-order>{$current-order}</old-order>
                            <new-order>{$new-order}</new-order>
                            <timestamp>{current-dateTime()}</timestamp>
                        </result>
    } catch * {
        <result status="error">
            <message>Error reordering sense: {$err:description}</message>
            <code>{$err:code}</code>
        </result>
    }
};

(:~
 : REORDER SENSES - Normalize sense order attributes (0, 1, 2, ...)
 : 
 : @param $entry Entry element
 : @return Entry with reordered senses
 :)
declare function sense:reorder-senses(
    $entry as element(lift:entry)
) as element(lift:entry) {
    copy $e := $entry
    modify (
        for $s at $pos in $e/lift:sense
        order by $s/@order
        return replace value of node $s/@order with ($pos - 1)
    )
    return $e
};

(:~
 : GET SENSE - Retrieve a specific sense from an entry
 : 
 : @param $db-name Database name
 : @param $entry-id Entry ID containing the sense
 : @param $sense-id Sense ID to retrieve
 : @return Sense XML or error
 :)
declare function sense:get(
    $db-name as xs:string,
    $entry-id as xs:string,
    $sense-id as xs:string
) as element(result) {
    try {
        let $entry := db:open($db-name)//lift:entry[@id = $entry-id]
        
        return if (not($entry)) then
            <result status="error">
                <message>Entry not found</message>
                <entry-id>{$entry-id}</entry-id>
            </result>
        else
            let $sense := $entry/lift:sense[@id = $sense-id]
            
            return if (not($sense)) then
                <result status="error">
                    <message>Sense not found</message>
                    <sense-id>{$sense-id}</sense-id>
                </result>
            else
                <result status="success">
                    <sense>{$sense}</sense>
                </result>
    } catch * {
        <result status="error">
            <message>Error getting sense: {$err:description}</message>
            <code>{$err:code}</code>
        </result>
    }
};

(:~
 : LIST SENSES - Get all senses for an entry
 : 
 : @param $db-name Database name
 : @param $entry-id Entry ID
 : @return List of senses
 :)
declare function sense:list(
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
            let $senses := $entry/lift:sense
            
            return
                <result status="success">
                    <entry-id>{$entry-id}</entry-id>
                    <count>{count($senses)}</count>
                    <senses>{
                        for $s in $senses
                        order by $s/@order
                        return $s
                    }</senses>
                </result>
    } catch * {
        <result status="error">
            <message>Error listing senses: {$err:description}</message>
            <code>{$err:code}</code>
        </result>
    }
};
