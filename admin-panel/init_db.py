#!/usr/bin/env python3
"""
Database initialization script for the admin panel
"""

import os
import sys
from datetime import datetime
from werkzeug.security import generate_password_hash

# Add the current directory to Python path
sys.path.append(os.path.dirname(__file__))

from app import app, db, User


def init_databases():
    """Initialize both admin and game databases"""
    print("🔄 Initializing databases...")

    with app.app_context():
        try:
            # Create admin database tables (User model)
            print("📁 Creating admin database tables...")
            db.create_all()

            # Create game database tables (all game models)
            print("📁 Creating game database tables...")
            db.create_all(bind_key="game")

            print("✅ Database tables created successfully")

            # Check if any admin users exist
            user_count = User.query.count()
            print(f"👤 Found {user_count} admin users")

            if user_count == 0:
                print("👤 Creating default admin user...")

                # Create default admin user
                admin_user = User(
                    username="annonywolfroda",
                    email="admin@newerabot.local",
                    is_admin=True,
                    can_manage_users=True,
                    is_active=True,
                )
                admin_user.set_password("admin123")

                db.session.add(admin_user)
                db.session.commit()

                print("✅ Default admin user created:")
                print("   Username: annonywolfroda")
                print("   Email: admin@newerabot.local")
                print("   Password: admin123")
                print("   ⚠️  CHANGE THIS PASSWORD IMMEDIATELY!")

            return True

        except Exception as e:
            print(f"❌ Database initialization failed: {e}")
            import traceback

            traceback.print_exc()
            return False


if __name__ == "__main__":
    print("=" * 50)
    print("Database Initialization Script")
    print("=" * 50)

    success = init_databases()

    if success:
        print("\n🎉 Database initialization completed successfully!")
    else:
        print("\n❌ Database initialization failed!")
        sys.exit(1)
