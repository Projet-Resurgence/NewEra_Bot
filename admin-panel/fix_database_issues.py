#!/usr/bin/env python3
"""
Fix database permission and schema issues
"""

import os
import sqlite3
import subprocess
from datetime import datetime
from werkzeug.security import generate_password_hash


def fix_database_permissions():
    """Fix database file and directory permissions"""
    admin_db_path = os.path.join(os.path.dirname(__file__), "admin.db")

    print("🔧 Fixing database permissions...")

    # Remove existing admin.db to start fresh
    if os.path.exists(admin_db_path):
        print("🗑️  Removing existing admin.db...")
        os.remove(admin_db_path)

    # Set directory permissions
    current_dir = os.path.dirname(__file__)
    os.chmod(current_dir, 0o775)

    # Create new admin database with proper permissions
    print("📁 Creating fresh admin database...")
    conn = sqlite3.connect(admin_db_path)
    cursor = conn.cursor()

    # Create AdminUsers table
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

    # Create admin users
    admin_password = generate_password_hash("admin123")
    created_at = str(datetime.now())

    users = [
        ("admin", "admin@newerabot.local", admin_password, 1, 1, created_at, 1),
        (
            "annonywolfroda",
            "annonywolfroda@gmail.com",
            admin_password,
            1,
            1,
            created_at,
            1,
        ),
    ]

    for user_data in users:
        cursor.execute(
            """
            INSERT INTO AdminUsers 
            (username, email, password_hash, is_admin, can_manage_users, created_at, is_active)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
            user_data,
        )

    conn.commit()
    conn.close()

    # Set proper file permissions
    os.chmod(admin_db_path, 0o666)

    print("✅ Admin database created successfully!")
    return True


def fix_technology_model():
    """Remove original_name references from cached SQLAlchemy models"""
    print("🔧 Clearing SQLAlchemy cache...")

    # Find and remove __pycache__ directories
    for root, dirs, files in os.walk("."):
        for dir_name in dirs:
            if dir_name == "__pycache__":
                pycache_path = os.path.join(root, dir_name)
                print(f"🗑️  Removing: {pycache_path}")
                subprocess.run(["rm", "-rf", pycache_path])

    # Also remove any .pyc files
    subprocess.run(["find", ".", "-name", "*.pyc", "-delete"])

    print("✅ Cache cleared!")
    return True


def test_database_connections():
    """Test that both databases work correctly"""
    print("🧪 Testing database connections...")

    try:
        # Test admin database
        admin_db_path = os.path.join(os.path.dirname(__file__), "admin.db")
        admin_conn = sqlite3.connect(admin_db_path)
        admin_cursor = admin_conn.cursor()

        admin_cursor.execute("SELECT COUNT(*) FROM AdminUsers")
        user_count = admin_cursor.fetchone()[0]
        print(f"✅ Admin database: {user_count} users")

        # Try a write operation
        admin_cursor.execute(
            "UPDATE AdminUsers SET last_login = ? WHERE user_id = 1",
            (str(datetime.now()),),
        )
        admin_conn.commit()
        admin_conn.close()
        print("✅ Admin database: Write test successful")

        # Test game database
        game_db_path = os.path.join(os.path.dirname(__file__), "../datas/rts.db")
        if os.path.exists(game_db_path):
            game_conn = sqlite3.connect(game_db_path)
            game_cursor = game_conn.cursor()

            game_cursor.execute("SELECT COUNT(*) FROM Countries")
            country_count = game_cursor.fetchone()[0]
            print(f"✅ Game database: {country_count} countries")

            # Test Technologies table structure
            game_cursor.execute("PRAGMA table_info(Technologies)")
            tech_columns = [col[1] for col in game_cursor.fetchall()]
            print(f"✅ Technologies columns: {', '.join(tech_columns)}")

            if "original_name" in tech_columns:
                print("⚠️  WARNING: original_name column still exists in Technologies")
            else:
                print("✅ Technologies table structure is correct")

            game_conn.close()

        return True

    except Exception as e:
        print(f"❌ Database test failed: {e}")
        return False


def main():
    print("=" * 60)
    print("Database Issues Fix Script")
    print("=" * 60)

    success = True

    # Fix permissions and recreate admin database
    if not fix_database_permissions():
        success = False

    # Clear Python cache to remove old model definitions
    if not fix_technology_model():
        success = False

    # Test everything works
    if not test_database_connections():
        success = False

    if success:
        print("\n🎉 All database issues fixed!")
        print("👤 Login credentials:")
        print("   Username: admin or annonywolfroda")
        print("   Password: admin123")
        print("\n🚀 You can now restart the Flask application")
    else:
        print("\n❌ Some issues remain - check the errors above")

    return success


if __name__ == "__main__":
    main()
