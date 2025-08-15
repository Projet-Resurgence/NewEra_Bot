#!/usr/bin/env python3
"""
Comprehensive test script to debug admin panel backend issues
"""
import sys
import os

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app import (
    app,
    db,
    Country,
    Government,
    Doctrine,
    Inventory,
    Region,
    Structure,
    Stats,
    Technology,
    CountryTechnology,
    User,
    StructureData,
    StructureProduction,
    TechnologyAttribute,
    TechnologyLicense,
    CountryTechnologyInventory,
    CountryTechnologyProduction,
    CountryDoctrine,
    GameDate,
    PlaydaysPerMonth,
    ServerSettings,
)


def test_model_counts():
    """Test each model's count to identify which ones are problematic"""
    with app.app_context():
        models_to_test = [
            ("Countries", Country),
            ("Governments", Government),
            ("Doctrines", Doctrine),
            ("Inventory", Inventory),
            ("Regions", Region),
            ("Structures", Structure),
            ("Stats", Stats),
            ("Technologies", Technology),
            ("CountryTechnologies", CountryTechnology),
            ("Users", User),
            ("StructureData", StructureData),
            ("Productions", StructureProduction),
            ("TechnologyAttributes", TechnologyAttribute),
            ("TechnologyLicenses", TechnologyLicense),
            ("CountryTechInventory", CountryTechnologyInventory),
            ("CountryTechProduction", CountryTechnologyProduction),
            ("CountryDoctrines", CountryDoctrine),
            ("GameDate", GameDate),
            ("PlaydaysPerMonth", PlaydaysPerMonth),
        ]

        results = {}

        for name, model in models_to_test:
            try:
                count = model.query.count()
                results[name] = count
                print(f"✓ {name}: {count}")
            except Exception as e:
                results[name] = f"ERROR: {e}"
                print(f"✗ {name}: ERROR - {e}")

        return results


def test_complex_queries():
    """Test the more complex queries from the index route"""
    with app.app_context():
        try:
            # Test total playdays calculation
            total_playdays = (
                db.session.query(db.func.sum(PlaydaysPerMonth.playdays)).scalar() or 0
            )
            print(f"✓ Total playdays: {total_playdays}")
        except Exception as e:
            print(f"✗ Total playdays: ERROR - {e}")

        try:
            # Test current game date
            current_date = GameDate.query.order_by(GameDate.real_date.desc()).first()
            print(f"✓ Current date: {current_date}")
        except Exception as e:
            print(f"✗ Current date: ERROR - {e}")

        try:
            # Test server settings
            is_paused_setting = ServerSettings.query.filter_by(key="is_paused").first()
            print(f"✓ Server settings: {is_paused_setting}")
        except Exception as e:
            print(f"✗ Server settings: ERROR - {e}")


def check_database_tables():
    """Check which tables actually exist in each database"""
    import sqlite3

    print("\n=== Admin Database Tables ===")
    try:
        admin_conn = sqlite3.connect("admin.db")
        admin_cursor = admin_conn.cursor()
        admin_cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        admin_tables = admin_cursor.fetchall()
        for table in admin_tables:
            print(f"  {table[0]}")
        admin_conn.close()
    except Exception as e:
        print(f"Error checking admin database: {e}")

    print("\n=== Game Database Tables ===")
    try:
        game_conn = sqlite3.connect("../datas/rts.db")
        game_cursor = game_conn.cursor()
        game_cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        game_tables = game_cursor.fetchall()
        for table in game_tables:
            print(f"  {table[0]}")
        game_conn.close()
    except Exception as e:
        print(f"Error checking game database: {e}")


if __name__ == "__main__":
    print("=== Checking Database Tables ===")
    check_database_tables()

    print("\n=== Testing Model Counts ===")
    results = test_model_counts()

    print("\n=== Testing Complex Queries ===")
    test_complex_queries()

    print("\n=== Summary ===")
    success_count = sum(1 for v in results.values() if isinstance(v, int))
    error_count = sum(
        1 for v in results.values() if isinstance(v, str) and "ERROR" in v
    )
    print(f"Successful queries: {success_count}")
    print(f"Failed queries: {error_count}")
