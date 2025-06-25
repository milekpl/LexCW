def search_entries(self, 
                      query: str, 
                      fields: Optional[List[str]] = None,
                      limit: Optional[int] = None,
                      offset: Optional[int] = None) -> Tuple[List[Entry], int]:
        """
        Search for entries.
        
        Args:
            query: Search query.
            fields: Fields to search in (default: lexical_unit, glosses, definitions).
            limit: Maximum number of entries to return.
            offset: Offset for pagination.
            
        Returns:
            Tuple of (list of Entry objects, total count).
            
        Raises:
            DatabaseError: If there is an error searching entries.
        """
        if not fields:
            fields = ["lexical_unit", "glosses", "definitions"]
        
        try:
            db_name = self.db_connector.database
            if not db_name:
                raise DatabaseError(DB_NAME_NOT_CONFIGURED)

            # Using modern XQuery 4.0 syntax with map expressions
            # This is more robust and handles escaping better
            search_query = f"""
            xquery 
            declare option output:method "xml";
            let $db := '{db_name}'
            let $query := "{query.replace('"', '\\"')}"
            let $query_lower := lower-case($query)
            let $entries := collection($db)/*[local-name()='lift']/*[local-name()='entry']
            
            let $matches := (
              for $entry in $entries
              let $match := {{
                "lexical_unit": {"contains(lower-case(string-join($entry/lexical-unit/form/text/text(), '')), $query_lower)" if "lexical_unit" in fields else "false()"},
                "glosses": {"some $gloss in $entry/sense/gloss/text satisfies contains(lower-case($gloss), $query_lower)" if "glosses" in fields else "false()"},
                "definitions": {"some $def in $entry/sense/definition/form/text satisfies contains(lower-case($def), $query_lower)" if "definitions" in fields else "false()"}
              }}
              where $match?lexical_unit or $match?glosses or $match?definitions
              order by $entry/lexical-unit/form/text/text()
              return $entry
            )
            
            let $total_count := count($matches)
            let $start := {offset + 1 if offset is not None else 1}
            let $count := {limit if limit is not None else 'count($matches)'}
            let $paginated_matches := 
              if ({limit is not None and offset is not None})
              then subsequence($matches, $start, $count)
              else $matches
            
            return
              <r>
                <count>{{$total_count}}</count>
                <entries>{{$paginated_matches}}</entries>
              </r>
            """
            
            result = self.db_connector.execute_query(search_query)
            
            # The result should be in XML format now
            if not result:
                return [], 0
            
            # Try to parse the entries from the result
            try:
                # Add explicit import for XML parsing
                import xml.etree.ElementTree as ET
                
                # Parse the XML result
                root = ET.fromstring(result)
                
                # Extract the count
                count_elem = root.find('./count')
                total_count = int(count_elem.text) if count_elem is not None and count_elem.text else 0
                
                # Extract and parse the entries
                entries_elem = root.find('./entries')
                if entries_elem is not None and len(entries_elem) > 0:
                    # Convert entries_elem to string
                    entries_xml = ''.join(ET.tostring(entry, encoding='unicode') for entry in entries_elem)
                    entries = self.lift_parser.parse_string(f"<lift>{entries_xml}</lift>")
                    
                    # Debug to check what we're getting back
                    self.logger.debug(f"Got {len(entries)} entries with limit={limit}, offset={offset}")
                    
                    return entries, total_count
                else:
                    return [], total_count
                    
            except Exception as xml_err:
                self.logger.warning(f"Error parsing XML result: {xml_err}. Falling back to traditional approach.")
            
            # If we get here, either the XML parsing failed or we need to use the fallback
            # Use a simpler query as fallback
            conditions = []
            q_lower = query.lower()
            if "lexical_unit" in fields:
                conditions.append(f'contains(lower-case($entry/lexical-unit/form/text), "{q_lower}")')
            if "glosses" in fields:
                conditions.append(f'some $gloss in $entry/sense/gloss/text satisfies contains(lower-case($gloss), "{q_lower}")')
            if "definitions" in fields:
                conditions.append(f'some $def in $entry/sense/definition/form/text satisfies contains(lower-case($def), "{q_lower}")')
            
            search_condition = " or ".join(conditions)
            
            count_query = f"""
            xquery count(for $entry in collection('{db_name}')/*[local-name()='lift']/*[local-name()='entry']
            where {search_condition}
            return $entry)
            """
            
            count_result = self.db_connector.execute_query(count_query)
            total_count = int(count_result) if count_result else 0
            
            # Use a different approach for pagination in the fallback
            if limit is not None and offset is not None:
                query_str = f"""
                xquery (for $entry at $pos in collection('{db_name}')/*[local-name()='lift']/*[local-name()='entry']
                where {search_condition}
                order by $entry/lexical-unit/form/text/text()
                return $entry)[position() > {offset} and position() <= {offset + limit}]
                """
            else:
                query_str = f"""
                xquery for $entry in collection('{db_name}')/*[local-name()='lift']/*[local-name()='entry']
                where {search_condition}
                order by $entry/lexical-unit/form/text/text()
                return $entry
                """
            
            result = self.db_connector.execute_query(query_str)
            
            if not result:
                return [], total_count
            
            entries = self.lift_parser.parse_string(f"<lift>{result}</lift>")
            
            return entries, total_count
            
        except Exception as e:
            self.logger.error("Error searching entries: %s", str(e))
            raise DatabaseError(f"Failed to search entries: {str(e)}") from e
