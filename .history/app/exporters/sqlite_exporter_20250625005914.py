"""
SQLite exporter for the Dictionary Writing System.

This module provides functionality for exporting dictionary entries to SQLite format
for use with Flutter mobile applications.
"""

import os
import logging
import sqlite3
from typing import List, Optional
import json

from app.models.entry import Entry
from app.services.dictionary_service import DictionaryService
from app.exporters.base_exporter import BaseExporter
from app.utils.exceptions import ExportError


class SQLiteExporter(BaseExporter):
    """
    Exporter for SQLite database format.
    
    This class handles exporting dictionary entries to a SQLite database
    optimized for mobile applications.
    """
    
    # SQLite table definitions
    TABLES = {
        "entries": """
            CREATE TABLE IF NOT EXISTS entries (
                id TEXT PRIMARY KEY,
                headword TEXT NOT NULL,
                pronunciation TEXT,
                grammatical_info TEXT,
                date_created TEXT,
                date_modified TEXT,
                custom_fields TEXT
            )
        """,
        "senses": """
            CREATE TABLE IF NOT EXISTS senses (
                id TEXT PRIMARY KEY,
                entry_id TEXT NOT NULL,
                definition TEXT,
                grammatical_info TEXT,
                custom_fields TEXT,
                sort_order INTEGER,
                FOREIGN KEY (entry_id) REFERENCES entries (id) ON DELETE CASCADE
            )
        """,
        "examples": """
            CREATE TABLE IF NOT EXISTS examples (
                id TEXT PRIMARY KEY,
                sense_id TEXT NOT NULL,
                text TEXT NOT NULL,
                translation TEXT,
                custom_fields TEXT,
                sort_order INTEGER,
                FOREIGN KEY (sense_id) REFERENCES senses (id) ON DELETE CASCADE
            )
        """,
        "variant_forms": """
            CREATE TABLE IF NOT EXISTS variant_forms (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                entry_id TEXT NOT NULL,
                form TEXT NOT NULL,
                FOREIGN KEY (entry_id) REFERENCES entries (id) ON DELETE CASCADE
            )
        """,
        "relations": """
            CREATE TABLE IF NOT EXISTS relations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                source_id TEXT NOT NULL,
                target_id TEXT NOT NULL,
                relation_type TEXT NOT NULL,
                is_sense_relation BOOLEAN DEFAULT 0,
                FOREIGN KEY (source_id) REFERENCES entries (id) ON DELETE CASCADE
            )
        """,
        "search_index": """
            CREATE VIRTUAL TABLE IF NOT EXISTS search_index USING fts5(
                headword, 
                definition, 
                example_text,
                entry_id UNINDEXED,
                sense_id UNINDEXED,
                content='',
                tokenize='unicode61'
            )
        """
    }
    
    # Indexes for performance
    INDEXES = [
        "CREATE INDEX IF NOT EXISTS idx_senses_entry_id ON senses(entry_id)",
        "CREATE INDEX IF NOT EXISTS idx_examples_sense_id ON examples(sense_id)",
        "CREATE INDEX IF NOT EXISTS idx_variant_forms_entry_id ON variant_forms(entry_id)",
        "CREATE INDEX IF NOT EXISTS idx_relations_source_id ON relations(source_id)",
        "CREATE INDEX IF NOT EXISTS idx_relations_target_id ON relations(target_id)",
    ]
    
    def __init__(self, dictionary_service: DictionaryService):
        """
        Initialize a SQLite exporter.
        
        Args:
            dictionary_service: The dictionary service to use.
        """
        super().__init__(dictionary_service)
        self.logger = logging.getLogger(__name__)
    
    def export(self, output_path: str, entries: Optional[List[Entry]] = None, 
               source_lang: str = "en", target_lang: str = "pl", batch_size: int = 500, **kwargs) -> str:
        """
        Export entries to a SQLite database.
        
        Args:
            output_path: Path to save the SQLite database.
            entries: List of entries to export. If None, all entries will be exported.
            source_lang: Source language code.
            target_lang: Target language code.
            batch_size: Number of entries to process in each batch (default: 500).
            **kwargs: Additional export options.
            
        Returns:
            Path to the exported SQLite database.
            
        Raises:
            ExportError: If the export fails.
        """
        try:
            # Create export directory if it doesn't exist
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            
            # If no entries provided, get all entries
            if entries is None:
                entries, _ = self.dictionary_service.list_entries(limit=100000)
            
            if not entries:
                raise ExportError("No entries to export")
            
            # Create and setup the SQLite database
            conn = sqlite3.connect(output_path)
            conn.execute("PRAGMA foreign_keys = ON")
            
            # Create tables
            self._create_tables(conn)
            
            # Create indexes
            self._create_indexes(conn)
            
            # Begin transaction
            conn.execute("BEGIN TRANSACTION")
            
            try:
                # Process entries in batches
                total_entries = len(entries)
                for i in range(0, total_entries, batch_size):
                    batch = entries[i:i+batch_size]
                    self._process_entries_batch(conn, batch, source_lang, target_lang)
                    self.logger.info("Processed %d/%d entries", min(i+batch_size, total_entries), total_entries)
                
                # Create metadata table
                self._create_metadata(conn, source_lang, target_lang)
                
                # Commit transaction
                conn.commit()
                
            except Exception as e:
                conn.rollback()
                raise e
            finally:
                conn.close()
            
            self.logger.info("SQLite database exported to %s", output_path)
            return output_path
            
        except Exception as e:
            self.logger.error("Error exporting to SQLite format: %s", e, exc_info=True)
            raise ExportError(f"Failed to export to SQLite format: {e}") from e
    
    def _create_tables(self, conn: sqlite3.Connection) -> None:
        """
        Create the necessary tables in the SQLite database.
        
        Args:
            conn: SQLite connection.
        """
        cursor = conn.cursor()
        for _, table_sql in self.TABLES.items():
            cursor.execute(table_sql)
        
        # Create metadata table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS metadata (
                key TEXT PRIMARY KEY,
                value TEXT
            )
        """)
        
        conn.commit()
    
    def _create_indexes(self, conn: sqlite3.Connection) -> None:
        """
        Create indexes for better performance.
        
        Args:
            conn: SQLite connection.
        """
        cursor = conn.cursor()
        for index_sql in self.INDEXES:
            cursor.execute(index_sql)
        conn.commit()
    
    def _create_metadata(self, conn: sqlite3.Connection, source_lang: str, target_lang: str) -> None:
        """
        Create metadata entries.
        
        Args:
            conn: SQLite connection.
            source_lang: Source language code.
            target_lang: Target language code.
        """
        cursor = conn.cursor()
        metadata: Dict[str, Any] = {
            "source_language": source_lang,
            "target_language": target_lang,
            "version": "1.0",
            "created": self._get_timestamp(),
            "entry_count": self._count_rows(conn, "entries"),
            "sense_count": self._count_rows(conn, "senses"),
            "example_count": self._count_rows(conn, "examples")
        }
        
        for key, value in metadata.items():
            cursor.execute("INSERT OR REPLACE INTO metadata (key, value) VALUES (?, ?)", 
                          (key, str(value)))
    
    def _count_rows(self, conn: sqlite3.Connection, table: str) -> int:
        """
        Count rows in a table.
        
        Args:
            conn: SQLite connection.
            table: Table name.
            
        Returns:
            Number of rows.
        """
        cursor = conn.cursor()
        cursor.execute(f"SELECT COUNT(*) FROM {table}")
        return cursor.fetchone()[0]
    
    def _get_timestamp(self) -> str:
        """
        Get the current timestamp.
        
        Returns:
            ISO format timestamp.
        """
        from datetime import datetime
        return datetime.now().isoformat()
    
    def _process_entries_batch(self, conn: sqlite3.Connection, entries: List[Entry], 
                             source_lang: str, target_lang: str) -> None:
        """
        Process a batch of entries.
        
        Args:
            conn: SQLite connection.
            entries: List of entries to process.
            source_lang: Source language code.
            target_lang: Target language code.
        """
        cursor = conn.cursor()
        
        for entry in entries:
            # Insert entry
            headword = entry.lexical_unit.get(source_lang, "")
            if not headword:
                continue
            
            # Prepare pronunciation (join if multiple)
            pronunciation = entry.pronunciations.get('seh-fonipa', '')
            
            # Process custom fields
            custom_fields = json.dumps(entry.custom_fields) if entry.custom_fields else None
            
            # Insert entry
            cursor.execute(
                """
                INSERT OR REPLACE INTO entries 
                (id, headword, pronunciation, grammatical_info, date_created, date_modified, custom_fields)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    entry.id,
                    headword,
                    pronunciation,
                    entry.grammatical_info,
                    None,  # date_created
                    None,  # date_modified
                    custom_fields
                )
            )
            
            # Insert variant forms
            for variant in entry.variant_forms:
                if source_lang in variant.get('form', {}):
                    variant_form = variant['form'][source_lang]
                    cursor.execute(
                        "INSERT INTO variant_forms (entry_id, form) VALUES (?, ?)",
                        (entry.id, variant_form)
                    )
            
            # Process senses
            for i, sense in enumerate(entry.senses):
                sense_id = sense.get('id')
                if not sense_id:
                    continue
                
                definition = sense.get('definitions', {}).get(target_lang, '')
                
                # Insert sense
                cursor.execute(
                    """
                    INSERT OR REPLACE INTO senses 
                    (id, entry_id, definition, grammatical_info, custom_fields, sort_order)
                    VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (
                        sense_id,
                        entry.id,
                        definition,
                        sense.get('grammatical_info'),
                        json.dumps(sense.get('custom_fields', {})) if sense.get('custom_fields') else None,
                        i
                    )
                )
                
                # Process examples
                for j, example in enumerate(sense.get('examples', [])):
                    example_id = example.get('id', f"{sense_id}_ex_{j}")
                    
                    example_text = example.get('form', {}).get(source_lang, '')
                    translation = example.get('translation', {}).get(target_lang, '')
                    
                    if not example_text:
                        continue
                    
                    # Insert example
                    cursor.execute(
                        """
                        INSERT OR REPLACE INTO examples 
                        (id, sense_id, text, translation, custom_fields, sort_order)
                        VALUES (?, ?, ?, ?, ?, ?)
                        """,
                        (
                            example_id,
                            sense_id,
                            example_text,
                            translation,
                            json.dumps(example.get('custom_fields', {})) if example.get('custom_fields') else None,
                            j
                        )
                    )
                    
                    # Add to search index
                    cursor.execute(
                        """
                        INSERT INTO search_index (headword, definition, example_text, entry_id, sense_id)
                        VALUES (?, ?, ?, ?, ?)
                        """,
                        (
                            headword,
                            definition,
                            example_text,
                            entry.id,
                            sense_id
                        )
                    )
            
            # Process relations
            for relation in entry.relations:
                relation_type = relation.get('type', '')
                target_id = relation.get('ref', '')
                
                if not target_id:
                    continue
                
                # Insert relation
                cursor.execute(
                    """
                    INSERT OR REPLACE INTO relations 
                    (source_id, target_id, relation_type, is_sense_relation)
                    VALUES (?, ?, ?, 0)
                    """,
                    (
                        entry.id,
                        target_id,
                        relation_type
                    )
                )
