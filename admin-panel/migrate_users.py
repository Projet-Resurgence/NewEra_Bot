#!/usr/bin/env python3
"""
Migration script to move AdminUsers table from game database to admin database
"""

import sqlite3
import os
from datetime import datetime
from werkzeug.security import generate_password_hash


def migrate_admin_users():
    admin_db_path = os.path.join(os.path.dirname(__file__), "admin.db")
    game_db_path = os.path.join(os.path.dirname(__file__), "../datas/rts.db")

    print("🔄 Starting AdminUsers migration...")

    # Check if game database exists
    if not os.path.exists(game_db_path):
        print("❌ Game database not found at:", game_db_path)
        return False

    try:
        # Connect to both databases
        game_conn = sqlite3.connect(game_db_path)
        admin_conn = sqlite3.connect(admin_db_path)

        game_cursor = game_conn.cursor()
        admin_cursor = admin_conn.cursor()

        # Create AdminUsers table in admin database
        admin_cursor.execute(
            """
        CREATE TABLE IF NOT EXISTS AdminUsers (
            user_id INTEGER PRIMARY KEY AUTOINCREMENT,
            username VARCHAR(80) UNIQUE NOT NULL,
            email VARCHAR(120) UNIQUE NOT NULL,
            password_hash VARCHAR(200) NOT NULL,
            is_admin BOOLEAN DEFAULT 0 NOT NULL,
            can_manage_users BOOLEAN DEFAULT 0 NOT NULL,
            created_at TEXT,
            last_login TEXT,
            is_active BOOLEAN DEFAULT 1 NOT NULL
        )
        """
        )

        # Check if AdminUsers table exists in game database
        game_cursor.execute(
            """
        SELECT name FROM sqlite_master 
        WHERE type='table' AND name='AdminUsers'
        """
        )

        if game_cursor.fetchone():
            print("📋 Found existing AdminUsers table in game database")

            # Get all existing admin users
            game_cursor.execute("SELECT * FROM AdminUsers")
            existing_users = game_cursor.fetchall()

            # Get column names
            game_cursor.execute("PRAGMA table_info(AdminUsers)")
            columns = [col[1] for col in game_cursor.fetchall()]

            print(f"📊 Found {len(existing_users)} existing users")

            # Migrate each user
            migrated = 0
            for user in existing_users:
                user_dict = dict(zip(columns, user))

                try:
                    admin_cursor.execute(
                        """
                    INSERT OR IGNORE INTO AdminUsers 
                    (username, email, password_hash, is_admin, can_manage_users, created_at, last_login, is_active)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                        (
                            user_dict.get("username"),
                            user_dict.get("email"),
                            user_dict.get("password_hash"),
                            user_dict.get("is_admin", 0),
                            user_dict.get("can_manage_users", 0),
                            user_dict.get("created_at"),
                            user_dict.get("last_login"),
                            user_dict.get("is_active", 1),
                        ),
                    )
                    migrated += 1
                    print(f"✅ Migrated user: {user_dict.get('username')}")

                except Exception as e:
                    print(f"⚠️  Failed to migrate user {user_dict.get('username')}: {e}")

            print(f"✅ Successfully migrated {migrated} users")

        else:
            print("ℹ️  No existing AdminUsers table found in game database")

        # Create a default admin user if none exist
        admin_cursor.execute("SELECT COUNT(*) FROM AdminUsers")
        user_count = admin_cursor.fetchone()[0]

        if user_count == 0:
            print("👤 Creating default admin user...")
            admin_password = generate_password_hash("admin123")
            created_at = str(datetime.now())

            admin_cursor.execute(
                """
            INSERT INTO AdminUsers 
            (username, email, password_hash, is_admin, can_manage_users, created_at, is_active)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
                ("admin", "admin@example.com", admin_password, 1, 1, created_at, 1),
            )

            print("✅ Default admin user created:")
            print("   Username: admin")
            print("   Password: admin123")
            print("   ⚠️  CHANGE THIS PASSWORD IMMEDIATELY!")

        # Commit changes
        admin_conn.commit()

        # Close connections
        game_conn.close()
        admin_conn.close()

        print("🎉 Migration completed successfully!")
        print(f"📁 Admin database: {admin_db_path}")

        return True

    except Exception as e:
        print(f"❌ Migration failed: {e}")
        import traceback

        traceback.print_exc()
        return False


def cleanup_game_database():
    """Optional: Remove AdminUsers table from game database after successful migration"""
    game_db_path = os.path.join(os.path.dirname(__file__), "../datas/rts.db")

    answer = input("\n🗑️  Remove AdminUsers table from game database? (y/N): ")
    if answer.lower() == "y":
        try:
            conn = sqlite3.connect(game_db_path)
            cursor = conn.cursor()
            cursor.execute("DROP TABLE IF EXISTS AdminUsers")
            conn.commit()
            conn.close()
            print("✅ AdminUsers table removed from game database")
        except Exception as e:
            print(f"❌ Failed to remove table: {e}")


if __name__ == "__main__":
    print("=" * 50)
    print("AdminUsers Migration Script")
    print("=" * 50)

    success = migrate_admin_users()

    if success:
        cleanup_game_database()

    print("\n✨ Migration script completed!")
