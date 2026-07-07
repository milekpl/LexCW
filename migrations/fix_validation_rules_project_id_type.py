"""
Migration: Fix project_validation_rules.project_id column type.

The column was VARCHAR(255) but every other project_id in the app (and the
JSON payloads + URL parameters) is an INTEGER referencing project_settings.id.
This type mismatch caused:

    psycopg2.errors.UndefinedFunction: operator does not exist: character varying = integer

whenever ValidationEngine.load_project_rules_from_db() queried the table,
silently dropping all project-specific validation rules.

This migration:
  1. Casts existing rows ('1' -> 1) and alters the column to INTEGER.
  2. Adds a foreign key to project_settings(id).
  3. Rebuilds the unique constraint and index.

Run:  python3 migrations/fix_validation_rules_project_id_type.py
"""

import sys
import os
from dotenv import load_dotenv

load_dotenv()
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app
from app.models.workset_models import db


def migrate():
    app = create_app('development')
    with app.app_context():
        conn = db.session.connection().connection
        cur = conn.cursor()

        print("== project_validation_rules.project_id type fix ==")

        # 1. Sanitize existing data: drop empty/non-numeric rows so the cast can't fail.
        print("  - removing rows with non-numeric project_id (if any)...")
        cur.execute("""
            DELETE FROM project_validation_rules
            WHERE project_id IS NULL
               OR project_id = ''
               OR project_id !~ '^[0-9]+\$'
        """)
        print(f"    deleted {cur.rowcount} uncastable row(s)")

        # 2. Drop constraints/indexes that depend on project_id.
        print("  - dropping unique constraint uq_project_rule_id...")
        cur.execute("ALTER TABLE project_validation_rules DROP CONSTRAINT IF EXISTS uq_project_rule_id")
        print("  - dropping index ix_project_validation_rules_project_id...")
        cur.execute("DROP INDEX IF EXISTS ix_project_validation_rules_project_id")

        # 3. Alter column type VARCHAR -> INTEGER.
        print("  - altering column project_id VARCHAR(255) -> INTEGER ...")
        cur.execute("""
            ALTER TABLE project_validation_rules
                ALTER COLUMN project_id TYPE INTEGER
                USING project_id::integer
        """)
        cur.execute("ALTER TABLE project_validation_rules ALTER COLUMN project_id SET NOT NULL")

        # 4. Add foreign key to project_settings(id).
        print("  - adding FK -> project_settings(id) ...")
        cur.execute("""
            ALTER TABLE project_validation_rules
                DROP CONSTRAINT IF EXISTS project_validation_rules_project_id_fkey
        """)
        cur.execute("""
            ALTER TABLE project_validation_rules
                ADD CONSTRAINT project_validation_rules_project_id_fkey
                FOREIGN KEY (project_id) REFERENCES project_settings(id)
                ON DELETE CASCADE
        """)

        # 5. Recreate index and unique constraint.
        print("  - recreating index + unique constraint ...")
        cur.execute("""
            CREATE INDEX IF NOT EXISTS ix_project_validation_rules_project_id
            ON project_validation_rules (project_id)
        """)
        cur.execute("""
            ALTER TABLE project_validation_rules
                ADD CONSTRAINT uq_project_rule_id
                UNIQUE (project_id, rule_id)
        """)

        conn.commit()
        print("  done.")

        # Verify.
        cur.execute(
            "SELECT data_type FROM information_schema.columns "
            "WHERE table_name='project_validation_rules' AND column_name='project_id'"
        )
        row = cur.fetchone()
        print(f"== verification: project_id is now {row[0] if row else '??'} ==")


if __name__ == '__main__':
    migrate()
