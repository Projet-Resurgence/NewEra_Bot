#!/usr/bin/env python3
"""
Test script to initialize structure data in the database.
"""

import sys
import os

# Add src directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

from db import Database


def main():
    print("Testing structure data initialization...")

    # Initialize database
    db = Database()

    # Initialize structure test data
    db._init_structure_test_data()

    # Test queries
    print("\n=== Testing Structure Data ===")

    # Test base structure data
    db.cur.execute("SELECT * FROM StructuresDatas ORDER BY type")
    structures = db.cur.fetchall()

    print("Base Structure Data:")
    for struct in structures:
        print(
            f"  {struct['type']}: Capacity={struct['capacity']}, Population={struct['population']}, Cost={struct['cout_construction']}"
        )

    # Test ratio data
    print("\nRatio Data:")
    db.cur.execute("SELECT * FROM StructuresRatios ORDER BY type, level")
    ratios = db.cur.fetchall()

    current_type = None
    for ratio in ratios:
        if current_type != ratio["type"]:
            current_type = ratio["type"]
            print(f"\n  {current_type}:")
        print(
            f"    Level {ratio['level']}: Production={ratio['ratio_production']}%, Population={ratio['ratio_population']}%, Capacity={ratio['ratio_capacity']}%"
        )

    # Test cost calculations
    print("\n=== Testing Cost Calculations ===")
    for struct_type in [
        "Usine",
        "Base",
        "Ecole",
        "Logement",
        "Centrale",
        "Technocentre",
    ]:
        print(f"\n{struct_type} Construction Costs:")
        for level in range(1, 8):
            cost = db.get_construction_cost(struct_type, level)
            print(f"  Level {level}: {cost:,}")

    print("\nTest completed successfully!")


if __name__ == "__main__":
    main()
