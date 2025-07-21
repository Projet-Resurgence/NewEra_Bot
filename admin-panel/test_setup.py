#!/usr/bin/env python3
"""
Test script to verify the application setup
"""

import os
import sys

# Add the current directory to Python path
sys.path.append(os.path.dirname(__file__))


def test_application():
    print("🧪 Testing application setup...")

    try:
        # Test imports
        print("📦 Testing imports...")
        from app import app, db, User, Country, Doctrine

        print("✅ All imports successful")

        # Test database connection
        print("🗄️  Testing database connections...")
        with app.app_context():
            # Test admin database
            user_count = User.query.count()
            print(f"✅ Admin DB connected - {user_count} users found")

            # Test game database
            country_count = Country.query.count()
            print(f"✅ Game DB connected - {country_count} countries found")

            doctrine_count = Doctrine.query.count()
            print(f"✅ Doctrines table accessible - {doctrine_count} doctrines found")

        print("🎉 All tests passed!")
        return True

    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback

        traceback.print_exc()
        return False


if __name__ == "__main__":
    print("=" * 50)
    print("Application Test Script")
    print("=" * 50)

    success = test_application()

    if success:
        print("\n✅ Application is ready to run!")
        print("🚀 You can now start the application with: python3 app.py")
        print("🌐 Or visit the login page in your browser")
    else:
        print("\n❌ Application has issues that need to be fixed!")
