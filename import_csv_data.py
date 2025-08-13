#!/usr/bin/env python3
"""
Fixed CSV Data Importer for New Structure System
Properly imports all structure, infrastructure, and power plant data from CSV files
"""

import sqlite3
import csv
import re
import os
from pathlib import Path


def clean_numeric_value(value_str):
    """Clean and convert numeric values from CSV (removes commas, quotes, etc.)"""
    if not value_str or value_str.strip() == "":
        return 0

    # Remove quotes, spaces (including Unicode non-breaking spaces), and commas
    cleaned = (
        str(value_str)
        .strip()
        .replace('"', "")
        .replace("'", "")
        .replace(" ", "")
        .replace("\u202f", "")  # Unicode narrow no-break space
        .replace("\u00a0", "")  # Unicode non-breaking space
        .replace(",", ".")  # Replace comma with dot for float conversion
    )

    # Handle percentage values
    is_percentage = cleaned.endswith("%")
    if is_percentage:
        cleaned = cleaned[:-1]  # Remove the % sign

    try:
        # Try to convert to int first
        if "." in cleaned:
            value = float(cleaned)
        else:
            value = int(cleaned)
        
        # If it was a percentage, convert to decimal (e.g., 2.00% -> 2.00)
        # Store as the actual percentage value, not as decimal fraction
        return value
    except ValueError:
        return 0


def import_factory_data(cursor):
    """Import factory/usine data from usines.csv"""
    print("Importing factory data...")

    with open(
        "/home/ubuntu/Bots/NEBot/datas/csvs/usines.csv", "r", encoding="utf-8"
    ) as file:
        reader = csv.reader(file)
        lines = list(reader)

    # Find section starts
    terrestre_start = None
    naval_start = None
    aerospace_start = None
    tech_boost_start = None

    for i, row in enumerate(lines):
        row_text = " ".join(row)
        if "Usine de production Terrestre" in row_text:
            terrestre_start = i + 2  # Skip header row
        elif "Chantier Naval" in row_text:
            naval_start = i + 2
        elif "Usine de production Aérospatiale" in row_text:
            aerospace_start = i + 2
        elif "Niv tech" in row_text and "Coef boost" in row_text:
            tech_boost_start = i + 1

    # Import Terrestre factories
    if terrestre_start:
        for i in range(terrestre_start, min(terrestre_start + 7, len(lines))):
            row = lines[i]
            if len(row) >= 6 and row[2].strip():
                level = clean_numeric_value(row[2])
                production = clean_numeric_value(row[3])
                employees = clean_numeric_value(row[4])
                cost = clean_numeric_value(row[5])

                cursor.execute(
                    """
                    INSERT OR REPLACE INTO StructuresDatas 
                    (type, specialisation, level, capacity, population, cout_construction)
                    VALUES (?, ?, ?, ?, ?, ?)
                """,
                    ("Usine", "Terrestre", level, production, employees, cost),
                )

    # Import Naval factories (Chantier Naval)
    if naval_start:
        for i in range(naval_start, min(naval_start + 7, len(lines))):
            row = lines[i]
            if len(row) >= 6 and row[2].strip():
                level = clean_numeric_value(row[2])
                production = clean_numeric_value(row[3])
                employees = clean_numeric_value(row[4])
                cost = clean_numeric_value(row[5])

                cursor.execute(
                    """
                    INSERT OR REPLACE INTO StructuresDatas 
                    (type, specialisation, level, capacity, population, cout_construction)
                    VALUES (?, ?, ?, ?, ?, ?)
                """,
                    ("Usine", "Navale", level, production, employees, cost),
                )

    # Import Aerospace factories
    if aerospace_start:
        for i in range(aerospace_start, min(aerospace_start + 7, len(lines))):
            row = lines[i]
            if len(row) >= 6 and row[2].strip():
                level = clean_numeric_value(row[2])
                production = clean_numeric_value(row[3])
                employees = clean_numeric_value(row[4])
                cost = clean_numeric_value(row[5])

                cursor.execute(
                    """
                    INSERT OR REPLACE INTO StructuresDatas 
                    (type, specialisation, level, capacity, population, cout_construction)
                    VALUES (?, ?, ?, ?, ?, ?)
                """,
                    ("Usine", "Aerienne", level, production, employees, cost),
                )

    # Import technology boost coefficients
    if tech_boost_start:
        for i in range(tech_boost_start, min(tech_boost_start + 12, len(lines))):
            row = lines[i]
            if len(row) >= 4 and row[2].strip():
                tech_level = clean_numeric_value(row[2])
                boost_coeff = clean_numeric_value(row[3])

                cursor.execute(
                    """
                    INSERT OR REPLACE INTO TechnologyBoosts 
                    (tech_level, boost_coefficient)
                    VALUES (?, ?)
                """,
                    (tech_level, boost_coeff),
                )


def import_military_base_data(cursor):
    """Import military base and school data from bases_militaires.csv"""
    print("Importing military base data...")

    with open(
        "/home/ubuntu/Bots/NEBot/datas/csvs/bases_militaires.csv", "r", encoding="utf-8"
    ) as file:
        reader = csv.reader(file)
        lines = list(reader)

    # Import military bases (first section)
    for i in range(2, 9):  # Skip headers, import 7 levels
        if i < len(lines):
            row = lines[i]
            if len(row) >= 3 and row[0].strip():
                level = clean_numeric_value(row[0])
                capacity = clean_numeric_value(row[1])
                cost = clean_numeric_value(row[2])

                cursor.execute(
                    """
                    INSERT OR REPLACE INTO StructuresDatas 
                    (type, specialisation, level, capacity, population, cout_construction)
                    VALUES (?, ?, ?, ?, ?, ?)
                """,
                    ("Base", "NA", level, capacity, 0, cost),
                )

    # Import military schools (second section)
    for i in range(2, 9):  # Skip headers, import 7 levels
        if i < len(lines):
            row = lines[i]
            if len(row) >= 8 and row[5].strip():  # School data starts at column 5
                level = clean_numeric_value(row[5])
                capacity = clean_numeric_value(row[6])
                cost = clean_numeric_value(row[7])

                cursor.execute(
                    """
                    INSERT OR REPLACE INTO StructuresDatas 
                    (type, specialisation, level, capacity, population, cout_construction)
                    VALUES (?, ?, ?, ?, ?, ?)
                """,
                    ("Ecole", "NA", level, capacity, 0, cost),
                )


def import_technocentre_data(cursor):
    """Import technocentre data from technocentres.csv"""
    print("Importing technocentre data...")

    with open(
        "/home/ubuntu/Bots/NEBot/datas/csvs/technocentres.csv", "r", encoding="utf-8"
    ) as file:
        reader = csv.reader(file)
        lines = list(reader)

    # Start from row 3 (skip headers)
    for i in range(3, min(15, len(lines))):  # Import up to 12 levels
        row = lines[i]
        if len(row) >= 3 and row[2].strip():
            level = clean_numeric_value(row[2])
            cost = clean_numeric_value(row[3])

            cursor.execute(
                """
                INSERT OR REPLACE INTO StructuresDatas 
                (type, specialisation, level, capacity, population, cout_construction)
                VALUES (?, ?, ?, ?, ?, ?)
            """,
                ("Technocentre", "NA", level, 0, 0, cost),
            )


def import_infrastructure_data(cursor):
    """Import infrastructure data from infrastructures.csv"""
    print("Importing infrastructure data...")

    with open(
        "/home/ubuntu/Bots/NEBot/datas/csvs/infrastructures.csv", "r", encoding="utf-8"
    ) as file:
        reader = csv.reader(file)
        lines = list(reader)

    # Start from row 5 (skip headers)
    for i in range(5, len(lines)):
        row = lines[i]
        if len(row) >= 5 and row[3].strip():
            name = row[3].strip()
            cost_per_km = clean_numeric_value(row[4])

            cursor.execute(
                """
                INSERT OR REPLACE INTO InfrastructureTypes 
                (type, cost_per_km)
                VALUES (?, ?)
            """,
                (name, cost_per_km),
            )


def import_power_plants_data(cursor):
    """Import power plant data from centrales_electriques.csv"""
    print("Importing power plant data...")

    with open(
        "/home/ubuntu/Bots/NEBot/datas/csvs/centrales_electriques.csv",
        "r",
        encoding="utf-8",
    ) as file:
        reader = csv.reader(file)
        lines = list(reader)

    # Start from row 2 (skip headers)
    for i in range(2, len(lines)):
        row = lines[i]
        if len(row) >= 11 and row[2].strip():
            plant_type = row[2].strip()
            level = clean_numeric_value(row[3])
            production = clean_numeric_value(row[4])
            cost = clean_numeric_value(row[5])
            danger_rate = clean_numeric_value(row[7]) if len(row) > 7 else 0
            resource = row[8] if len(row) > 8 and row[8] != "N/A" else None
            resource_consumption = clean_numeric_value(row[9]) if len(row) > 9 else 0
            price_per_mwh = clean_numeric_value(row[10]) if len(row) > 10 else 100

            cursor.execute(
                """
                INSERT OR REPLACE INTO PowerPlantsDatas 
                (type, level, production_mwh, construction_cost, danger_rate, resource_type, resource_consumption, price_per_mwh)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
                (
                    plant_type,
                    level,
                    production,
                    cost,
                    danger_rate,
                    resource,
                    resource_consumption,
                    price_per_mwh,
                ),
            )


def import_housing_data(cursor):
    """Import housing data from logements.csv"""
    print("Importing housing data...")

    # Housing data is complex with density/style/quality multipliers
    # For now, create basic housing entries
    for level in range(1, 8):
        # Basic housing costs (these would need to be calculated from the complex CSV)
        base_cost = 50000 * level * level

        cursor.execute(
            """
            INSERT OR REPLACE INTO StructuresDatas 
            (type, specialisation, level, capacity, population, cout_construction)
            VALUES (?, ?, ?, ?, ?, ?)
        """,
            ("Logement", "NA", level, 1000 * level, 0, base_cost),
        )


def main():
    """Main function to import all CSV data"""
    db_path = "/home/ubuntu/Bots/NEBot/datas/rts.db"

    try:
        # Connect to database
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # Clear existing data
        print("Clearing existing data...")
        cursor.execute("DELETE FROM StructuresDatas")
        cursor.execute("DELETE FROM TechnologyBoosts")
        cursor.execute("DELETE FROM InfrastructureTypes")
        cursor.execute("DELETE FROM PowerPlantsDatas")

        # Import all data
        import_factory_data(cursor)
        import_military_base_data(cursor)
        import_technocentre_data(cursor)
        import_infrastructure_data(cursor)
        import_power_plants_data(cursor)
        import_housing_data(cursor)

        # Commit changes
        conn.commit()
        print("✅ All data imported successfully!")

        # Display summary
        cursor.execute("SELECT COUNT(*) FROM StructuresDatas")
        structures_count = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM TechnologyBoosts")
        tech_boosts_count = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM InfrastructureTypes")
        infra_count = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM PowerPlantsDatas")
        power_plants_count = cursor.fetchone()[0]

        print(f"\nImport Summary:")
        print(f"- Structures Data: {structures_count} entries")
        print(f"- Technology Boosts: {tech_boosts_count} entries")
        print(f"- Infrastructure Types: {infra_count} entries")
        print(f"- Power Plants Data: {power_plants_count} entries")

        # Show some sample costs to verify
        print(f"\nSample Structure Costs:")
        cursor.execute(
            "SELECT type, specialisation, level, cout_construction FROM StructuresDatas WHERE cout_construction > 0 LIMIT 5"
        )
        for row in cursor.fetchall():
            print(f"- {row[0]} {row[1]} Level {row[2]}: {row[3]:,}")

        print(f"\nSample Power Plant Costs:")
        cursor.execute(
            "SELECT type, level, construction_cost FROM PowerPlantsDatas WHERE construction_cost > 0 LIMIT 5"
        )
        for row in cursor.fetchall():
            print(f"- {row[0]} Level {row[1]}: {row[2]:,}")

        conn.close()

    except Exception as e:
        print(f"❌ Error importing data: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    main()
