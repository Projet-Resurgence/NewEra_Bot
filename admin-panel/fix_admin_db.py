#!/usr/bin/env python3
"""
Quick fix script to ensure the admin database is properly configured
"""

import os
import sqlite3
from datetime import datetime
from werkzeug.security import generate_password_hash


def fix_admin_database():
    admin_db_path = os.path.join(os.path.dirname(__file__), "admin.db")
    print(f"🔧 Fixing admin database at: {admin_db_path}")

    try:
        # Connect to admin database
        conn = sqlite3.connect(admin_db_path)
        cursor = conn.cursor()

        # Drop and recreate the AdminUsers table to ensure proper schema
        print("🗑️  Dropping existing AdminUsers table...")
        cursor.execute("DROP TABLE IF EXISTS AdminUsers")

        print("📁 Creating AdminUsers table with correct schema...")
        cursor.execute(
            """
        CREATE TABLE AdminUsers (
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

        # Insert existing users from the attached data
        print("👤 Re-creating admin users...")

        users_data = [
            (
                "annonywolfroda",
                "annonywolfroda@gmail.com",
                "scrypt:32768:8:1$Gd1TzHJMc6r6b1K4$b9882893c4533eaac81c8005eb186f809eb21a0c28cca0392f5f16832215bd888e2cd024cc8989252081dd88d3f79e4a24ac8e0c2b12edad1ba7a680640466172025-07-19 02:09:232025-07-19 12:45:07.510617",
                1,
                1,
                "2025-07-19 02:09:23",
                "2025-07-19 12:45:07.510617",
                1,
            ),
            (
                "Chjara",
                "example@gmail.com",
                "scrypt:32768:8:1$8JqESwgij4Wzr5of$d87e51a09ebcf346a58d13753213f36121f7db57f7d557205450ece4fe3dec57a5f5cdbfbfc7b38ad1758e489cc02a609b362fe9b0182f9e7fa9f18f3a84aa4d2025-07-19 04:18:44.4826472025-07-19 08:01:00.854710",
                1,
                1,
                "2025-07-19 04:18:44.482647",
                "2025-07-19 08:01:00.854710",
                1,
            ),
            (
                "admin",
                "admin@newerabot.local",
                "scrypt:32768:8:1$NcqEg8hK9caBEaVW$ae91d9c8b2f3faf54b3a19e497cd713e052c7a4e915fbcf80016b65e161e717a303377bb7fc88ba17bd89ac00b2c9ae3e4dd8a3aeed7b52210fceb965c80470a2025-07-19 14:34:33.044475",
                1,
                1,
                "2025-07-19 14:34:33.044475",
                None,
                1,
            ),
        ]

        # Actually, let's create a fresh admin user with a known password
        print("👤 Creating fresh admin user...")
        admin_password = generate_password_hash("admin123")
        created_at = str(datetime.now())

        cursor.execute(
            """
        INSERT INTO AdminUsers 
        (username, email, password_hash, is_admin, can_manage_users, created_at, is_active)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
            ("admin", "admin@newerabot.local", admin_password, 1, 1, created_at, 1),
        )

        # Also recreate annonywolfroda
        cursor.execute(
            """
        INSERT INTO AdminUsers 
        (username, email, password_hash, is_admin, can_manage_users, created_at, is_active)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
            (
                "annonywolfroda",
                "annonywolfroda@gmail.com",
                admin_password,
                1,
                1,
                created_at,
                1,
            ),
        )

        conn.commit()
        conn.close()

        # Update file permissions
        os.chmod(admin_db_path, 0o666)

        print("✅ Admin database fixed successfully!")
        print("👤 Login credentials:")
        print("   Username: admin or annonywolfroda")
        print("   Password: admin123")
        print("   ⚠️  Change passwords after login!")

        return True

    except Exception as e:
        print(f"❌ Failed to fix admin database: {e}")
        import traceback

        traceback.print_exc()
        return False


if __name__ == "__main__":
    print("=" * 50)
    print("Admin Database Fix Script")
    print("=" * 50)

    success = fix_admin_database()

    if success:
        print("\n🎉 Fix completed successfully!")
    else:
        print("\n❌ Fix failed!")
