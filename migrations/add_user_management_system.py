"""
Database migration script for user management tables.

This migration adds:
- Enhanced users table with authentication fields
- project_roles table for user-project membership with roles
- messages table for entry discussions
- activity_logs table for audit trail
- notifications table for user notifications
- User tracking fields to worksets and workset_entries tables

Run this migration with: python migrations/add_user_management_system.py
"""

from app import create_app
from app.models.workset_models import db
from sqlalchemy import text


def run_migration():
    """Run the user management migration."""
    app = create_app()

    with app.app_context():
        print("Starting user management migration...")

        # Get database connection
        conn = db.engine.connect()
        trans = conn.begin()

        try:
            # 1. Add columns to users table
            print("Enhancing users table...")
            queries = [
                # Check if columns exist before adding
                """
                DO $$ 
                BEGIN 
                    IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                                  WHERE table_name='users' AND column_name='username') THEN
                        ALTER TABLE users ADD COLUMN username VARCHAR(80) UNIQUE NOT NULL DEFAULT 'user';
                        ALTER TABLE users ALTER COLUMN username DROP DEFAULT;
                    END IF;
                END $$;
                """,
                """
                DO $$ 
                BEGIN 
                    IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                                  WHERE table_name='users' AND column_name='email') THEN
                        ALTER TABLE users ADD COLUMN email VARCHAR(120) UNIQUE NOT NULL DEFAULT 'user@example.com';
                        ALTER TABLE users ALTER COLUMN email DROP DEFAULT;
                    END IF;
                END $$;
                """,
                """
                DO $$ 
                BEGIN 
                    IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                                  WHERE table_name='users' AND column_name='password_hash') THEN
                        ALTER TABLE users ADD COLUMN password_hash VARCHAR(255) NOT NULL DEFAULT '';
                        ALTER TABLE users ALTER COLUMN password_hash DROP DEFAULT;
                    END IF;
                END $$;
                """,
                """
                DO $$ 
                BEGIN 
                    IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                                  WHERE table_name='users' AND column_name='first_name') THEN
                        ALTER TABLE users ADD COLUMN first_name VARCHAR(100);
                    END IF;
                END $$;
                """,
                """
                DO $$ 
                BEGIN 
                    IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                                  WHERE table_name='users' AND column_name='last_name') THEN
                        ALTER TABLE users ADD COLUMN last_name VARCHAR(100);
                    END IF;
                END $$;
                """,
                """
                DO $$ 
                BEGIN 
                    IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                                  WHERE table_name='users' AND column_name='is_active') THEN
                        ALTER TABLE users ADD COLUMN is_active BOOLEAN NOT NULL DEFAULT TRUE;
                    END IF;
                END $$;
                """,
                """
                DO $$ 
                BEGIN 
                    IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                                  WHERE table_name='users' AND column_name='is_admin') THEN
                        ALTER TABLE users ADD COLUMN is_admin BOOLEAN NOT NULL DEFAULT FALSE;
                    END IF;
                END $$;
                """,
                """
                DO $$ 
                BEGIN 
                    IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                                  WHERE table_name='users' AND column_name='created_at') THEN
                        ALTER TABLE users ADD COLUMN created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP;
                    END IF;
                END $$;
                """,
                """
                DO $$ 
                BEGIN 
                    IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                                  WHERE table_name='users' AND column_name='last_login') THEN
                        ALTER TABLE users ADD COLUMN last_login TIMESTAMP WITH TIME ZONE;
                    END IF;
                END $$;
                """,
                """
                DO $$ 
                BEGIN 
                    IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                                  WHERE table_name='users' AND column_name='avatar_url') THEN
                        ALTER TABLE users ADD COLUMN avatar_url VARCHAR(500);
                    END IF;
                END $$;
                """,
                """
                DO $$ 
                BEGIN 
                    IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                                  WHERE table_name='users' AND column_name='bio') THEN
                        ALTER TABLE users ADD COLUMN bio TEXT;
                    END IF;
                END $$;
                """,
                """
                DO $$ 
                BEGIN 
                    IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                                  WHERE table_name='users' AND column_name='preferences') THEN
                        ALTER TABLE users ADD COLUMN preferences JSONB;
                    END IF;
                END $$;
                """,
            ]

            for query in queries:
                conn.execute(text(query))

            # 2. Create indexes for users table
            print("Creating indexes for users table...")
            conn.execute(
                text("""
                CREATE INDEX IF NOT EXISTS idx_users_username ON users(username);
            """)
            )
            conn.execute(
                text("""
                CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);
            """)
            )

            # 3. Create project_roles table
            print("Creating project_roles table...")
            conn.execute(
                text("""
                CREATE TABLE IF NOT EXISTS project_roles (
                    id SERIAL PRIMARY KEY,
                    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                    project_id INTEGER NOT NULL REFERENCES project_settings(id) ON DELETE CASCADE,
                    role VARCHAR(20) NOT NULL,
                    granted_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                    granted_by_user_id INTEGER REFERENCES users(id) ON DELETE SET NULL,
                    UNIQUE(user_id, project_id)
                );
            """)
            )

            # 4. Create messages table
            print("Creating messages table...")
            conn.execute(
                text("""
                CREATE TABLE IF NOT EXISTS messages (
                    id SERIAL PRIMARY KEY,
                    entry_id VARCHAR(255) NOT NULL,
                    workset_id INTEGER REFERENCES worksets(id) ON DELETE CASCADE,
                    sender_user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                    recipient_user_id INTEGER REFERENCES users(id) ON DELETE SET NULL,
                    parent_message_id INTEGER REFERENCES messages(id) ON DELETE CASCADE,
                    message_text TEXT NOT NULL,
                    is_read BOOLEAN NOT NULL DEFAULT FALSE,
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP WITH TIME ZONE
                );
            """)
            )

            # Create indexes for messages
            conn.execute(
                text("""
                CREATE INDEX IF NOT EXISTS idx_messages_entry_id ON messages(entry_id);
            """)
            )
            conn.execute(
                text("""
                CREATE INDEX IF NOT EXISTS idx_messages_sender ON messages(sender_user_id);
            """)
            )
            conn.execute(
                text("""
                CREATE INDEX IF NOT EXISTS idx_messages_recipient ON messages(recipient_user_id);
            """)
            )
            conn.execute(
                text("""
                CREATE INDEX IF NOT EXISTS idx_messages_created_at ON messages(created_at);
            """)
            )

            # 5. Create activity_logs table
            print("Creating activity_logs table...")
            conn.execute(
                text("""
                CREATE TABLE IF NOT EXISTS activity_logs (
                    id SERIAL PRIMARY KEY,
                    user_id INTEGER REFERENCES users(id) ON DELETE SET NULL,
                    action VARCHAR(50) NOT NULL,
                    entity_type VARCHAR(50) NOT NULL,
                    entity_id VARCHAR(255) NOT NULL,
                    project_id INTEGER REFERENCES project_settings(id) ON DELETE CASCADE,
                    changes JSONB,
                    description TEXT,
                    timestamp TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                    ip_address VARCHAR(45),
                    user_agent VARCHAR(500)
                );
            """)
            )

            # Create indexes for activity_logs
            conn.execute(
                text("""
                CREATE INDEX IF NOT EXISTS idx_activity_logs_user ON activity_logs(user_id);
            """)
            )
            conn.execute(
                text("""
                CREATE INDEX IF NOT EXISTS idx_activity_logs_action ON activity_logs(action);
            """)
            )
            conn.execute(
                text("""
                CREATE INDEX IF NOT EXISTS idx_activity_logs_entity ON activity_logs(entity_type, entity_id);
            """)
            )
            conn.execute(
                text("""
                CREATE INDEX IF NOT EXISTS idx_activity_logs_timestamp ON activity_logs(timestamp);
            """)
            )

            # 6. Create notifications table
            print("Creating notifications table...")
            conn.execute(
                text("""
                CREATE TABLE IF NOT EXISTS notifications (
                    id SERIAL PRIMARY KEY,
                    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                    notification_type VARCHAR(50) NOT NULL,
                    title VARCHAR(255) NOT NULL,
                    message TEXT NOT NULL,
                    link_url VARCHAR(500),
                    is_read BOOLEAN NOT NULL DEFAULT FALSE,
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                    read_at TIMESTAMP WITH TIME ZONE,
                    related_message_id INTEGER REFERENCES messages(id) ON DELETE CASCADE,
                    related_entry_id VARCHAR(255)
                );
            """)
            )

            # Create indexes for notifications
            conn.execute(
                text("""
                CREATE INDEX IF NOT EXISTS idx_notifications_user ON notifications(user_id);
            """)
            )
            conn.execute(
                text("""
                CREATE INDEX IF NOT EXISTS idx_notifications_created_at ON notifications(created_at);
            """)
            )
            conn.execute(
                text("""
                CREATE INDEX IF NOT EXISTS idx_notifications_is_read ON notifications(user_id, is_read);
            """)
            )

            # 7. Add user tracking fields to worksets
            print("Adding user tracking to worksets...")
            conn.execute(
                text("""
                DO $$ 
                BEGIN 
                    IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                                  WHERE table_name='worksets' AND column_name='created_by_user_id') THEN
                        ALTER TABLE worksets ADD COLUMN created_by_user_id INTEGER REFERENCES users(id) ON DELETE SET NULL;
                    END IF;
                END $$;
            """)
            )

            # 8. Add user tracking fields to workset_entries
            print("Adding user tracking to workset_entries...")
            conn.execute(
                text("""
                DO $$ 
                BEGIN 
                    IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                                  WHERE table_name='workset_entries' AND column_name='modified_by_user_id') THEN
                        ALTER TABLE workset_entries ADD COLUMN modified_by_user_id INTEGER REFERENCES users(id) ON DELETE SET NULL;
                    END IF;
                END $$;
            """)
            )
            conn.execute(
                text("""
                DO $$ 
                BEGIN 
                    IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                                  WHERE table_name='workset_entries' AND column_name='notes_author_user_id') THEN
                        ALTER TABLE workset_entries ADD COLUMN notes_author_user_id INTEGER REFERENCES users(id) ON DELETE SET NULL;
                    END IF;
                END $$;
            """)
            )

            trans.commit()
            print("✓ User management migration completed successfully!")

        except Exception as e:
            trans.rollback()
            print(f"✗ Migration failed: {e}")
            raise
        finally:
            conn.close()


if __name__ == "__main__":
    run_migration()
