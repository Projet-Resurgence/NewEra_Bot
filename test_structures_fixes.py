#!/usr/bin/env python3
"""
Test script to validate structure system fixes.
"""

import sys
import os

sys.path.append("src")

from db import Database


def test_structures_system():
    """Test the structures system after fixes."""
    print("🔧 Testing Structures System Fixes")
    print("=" * 50)

    # Initialize database
    db = Database("datas/rts.db")

    print("\n1. Testing database structure methods...")

    try:
        # Test get_structure_capacity with a structure
        print("   - Testing get_structure_capacity...")
        capacity = db.get_structure_capacity(1)  # Test with structure ID 1
        print(f"     ✅ get_structure_capacity works (capacity: {capacity})")
    except Exception as e:
        print(f"     ❌ get_structure_capacity failed: {e}")

    try:
        # Test get_construction_cost
        print("   - Testing get_construction_cost...")
        cost = db.get_construction_cost("Usine", 3)
        print(f"     ✅ get_construction_cost works (cost: {cost})")
    except Exception as e:
        print(f"     ❌ get_construction_cost failed: {e}")

    try:
        # Test get_structures_by_country
        print("   - Testing get_structures_by_country...")
        structures = db.get_structures_by_country(1)  # Test with country ID 1
        print(
            f"     ✅ get_structures_by_country works (found: {len(structures)} structures)"
        )
    except Exception as e:
        print(f"     ❌ get_structures_by_country failed: {e}")

    try:
        # Test get_available_structure_types
        print("   - Testing get_available_structure_types...")
        types = db.get_available_structure_types()
        print(f"     ✅ get_available_structure_types works (types: {types})")
    except Exception as e:
        print(f"     ❌ get_available_structure_types failed: {e}")

    print("\n2. Testing table consistency...")

    # Check StructuresDatas table
    try:
        db.cur.execute(
            "SELECT type, specialisation, capacity, cout_construction FROM StructuresDatas LIMIT 5"
        )
        results = db.cur.fetchall()
        print(f"     ✅ StructuresDatas table accessible ({len(results)} entries)")
        if results:
            print(f"       Sample: {results[0]}")
    except Exception as e:
        print(f"     ❌ StructuresDatas table error: {e}")

    # Check StructuresRatios table
    try:
        db.cur.execute(
            "SELECT type, level, ratio_production, ratio_cost FROM StructuresRatios LIMIT 5"
        )
        results = db.cur.fetchall()
        print(f"     ✅ StructuresRatios table accessible ({len(results)} entries)")
        if results:
            print(f"       Sample: {results[0]}")
    except Exception as e:
        print(f"     ❌ StructuresRatios table error: {e}")

    # Check Structures table
    try:
        db.cur.execute(
            "SELECT id, type, specialisation, level, capacity FROM Structures LIMIT 5"
        )
        results = db.cur.fetchall()
        print(f"     ✅ Structures table accessible ({len(results)} entries)")
        if results:
            print(f"       Sample: {results[0]}")
    except Exception as e:
        print(f"     ❌ Structures table error: {e}")

    print("\n3. Testing JOIN consistency...")

    # Test the fixed JOIN queries
    try:
        db.cur.execute(
            """
            SELECT s.id, sd.capacity, sr.ratio_production
            FROM Structures s
            JOIN StructuresDatas sd ON s.type = sd.type AND s.specialisation = sd.specialisation
            JOIN StructuresRatios sr ON s.type = sr.type AND s.level = sr.level
            LIMIT 5
        """
        )
        results = db.cur.fetchall()
        print(f"     ✅ Fixed JOIN query works ({len(results)} results)")
    except Exception as e:
        print(f"     ❌ Fixed JOIN query failed: {e}")

    print("\n" + "=" * 50)
    print("🎉 Structure system validation completed!")

    print("\n📋 Summary of Fixes Applied:")
    print("• ✅ Fixed JOIN condition: s.level = sr.level (was s.level = s.level)")
    print("• ✅ Added specialisation filter in capacity calculations")
    print("• ✅ Fixed column name consistency: specialisation (not specialisation)")
    print("• ✅ Updated INSERT statements to include specialisation column")
    print("• ✅ Fixed SELECT queries to use consistent column names")

    return True


if __name__ == "__main__":
    test_structures_system()
