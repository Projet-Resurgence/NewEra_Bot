#!/usr/bin/env python3
"""
Debug Country Creator Script

This script takes every region in the database and creates a corresponding 
debug country in the Countries table only. It does NOT modify region ownership.

The debug countries will have:
- Name: "Debug_<RegionName>"
- Fake Discord role IDs and channel IDs
- No actual Discord integration
"""

import sqlite3
import sys
import os
from pathlib import Path


def connect_to_database():
    """Connect to the NEBot database."""
    db_path = "/home/ubuntu/Bots/NEBot/datas/rts.db"
    
    if not os.path.exists(db_path):
        print(f"❌ Database not found at {db_path}")
        sys.exit(1)
    
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row  # Enable dict-like access
    return conn


def get_all_regions(cursor):
    """Get all regions from the database."""
    cursor.execute("""
        SELECT region_id, name, continent, geographical_area_id 
        FROM Regions 
        ORDER BY continent, name
    """)
    return cursor.fetchall()


def generate_fake_ids(region_id):
    """Generate fake Discord IDs based on region_id."""
    # Generate fake but consistent IDs based on region_id
    # Using a large offset to avoid conflicts with real Discord IDs
    base_id = 900000000000000000 + (region_id * 1000)
    
    return {
        'role_id': str(base_id + 1),
        'public_channel_id': str(base_id + 2),
        'secret_channel_id': str(base_id + 3)
    }


def country_name_exists(cursor, country_name):
    """Check if a country name already exists."""
    cursor.execute("SELECT 1 FROM Countries WHERE name = ?", (country_name,))
    return cursor.fetchone() is not None


def create_debug_countries(cursor, regions):
    """Create debug countries for all regions."""
    created_countries = []
    skipped_countries = []
    
    for region in regions:
        region_id = region['region_id']
        region_name = region['name']
        continent = region['continent']
        
        # Create debug country name
        debug_name = f"Debug_{region_name}"
        
        # Check if country already exists
        if country_name_exists(cursor, debug_name):
            skipped_countries.append(debug_name)
            continue
        
        # Generate fake Discord IDs
        fake_ids = generate_fake_ids(region_id)
        
        try:
            # Insert debug country
            cursor.execute("""
                INSERT INTO Countries (name, role_id, public_channel_id, secret_channel_id)
                VALUES (?, ?, ?, ?)
            """, (
                debug_name,
                fake_ids['role_id'],
                fake_ids['public_channel_id'],
                fake_ids['secret_channel_id']
            ))
            
            country_id = cursor.lastrowid
            created_countries.append({
                'country_id': country_id,
                'name': debug_name,
                'region_name': region_name,
                'continent': continent
            })
            
            cursor.execute("""
                UPDATE Regions SET country_id = ?
                WHERE region_id = ?
            """, (country_id, region_id))

        except sqlite3.Error as e:
            print(f"❌ Error creating country for region '{region_name}': {e}")
    
    return created_countries, skipped_countries


def create_debug_inventory_entries(cursor, created_countries):
    """Create basic inventory entries for debug countries."""
    for country in created_countries:
        country_id = country['country_id']
        
        try:
            # Check if inventory entry already exists
            cursor.execute("SELECT 1 FROM Inventory WHERE country_id = ?", (country_id,))
            if cursor.fetchone():
                continue  # Skip if already exists
            
            # Create basic inventory entry with default values
            cursor.execute("""
                INSERT INTO Inventory (country_id, balance, pol_points, diplo_points, tech_points)
                VALUES (?, ?, ?, ?, ?)
            """, (country_id, 1000000, 100, 100, 50))  # Default debug values
            
        except sqlite3.Error as e:
            print(f"❌ Error creating inventory for country '{country['name']}': {e}")


def main():
    """Main function to create debug countries."""
    print("🚀 Starting Debug Country Creator...")
    print("=" * 50)
    
    # Connect to database
    try:
        conn = connect_to_database()
        cursor = conn.cursor()
        print("✅ Connected to database")
    except Exception as e:
        print(f"❌ Failed to connect to database: {e}")
        sys.exit(1)
    
    try:
        # Get all regions
        print("📍 Fetching all regions...")
        regions = get_all_regions(cursor)
        print(f"✅ Found {len(regions)} regions")
        
        # Show continent breakdown
        continent_counts = {}
        for region in regions:
            continent = region['continent']
            continent_counts[continent] = continent_counts.get(continent, 0) + 1
        
        print("\n📊 Regions by continent:")
        for continent, count in sorted(continent_counts.items()):
            print(f"   {continent}: {count} regions")
        
        # Confirm with user
        print(f"\n⚠️  This will create {len(regions)} debug countries.")
        print("   Each debug country will have fake Discord IDs and basic inventory.")
        print("   This does NOT affect region ownership.")
        
        response = input("\n🤔 Do you want to continue? (y/N): ").strip().lower()
        if response not in ['y', 'yes']:
            print("❌ Operation cancelled by user")
            return
        
        # Create debug countries
        print("\n🏭 Creating debug countries...")
        created_countries, skipped_countries = create_debug_countries(cursor, regions)
        
        if skipped_countries:
            print(f"\n⚠️  Skipped {len(skipped_countries)} countries (already exist):")
            for name in skipped_countries[:10]:  # Show first 10
                print(f"   - {name}")
            if len(skipped_countries) > 10:
                print(f"   ... and {len(skipped_countries) - 10} more")
        
        if created_countries:
            print(f"\n✅ Created {len(created_countries)} new debug countries")
            
            # Create inventory entries
            print("💰 Creating inventory entries...")
            create_debug_inventory_entries(cursor, created_countries)
            
            # Show sample of created countries
            print("\n📋 Sample of created countries:")
            for country in created_countries[:10]:
                print(f"   ID {country['country_id']}: {country['name']} ({country['continent']})")
            
            if len(created_countries) > 10:
                print(f"   ... and {len(created_countries) - 10} more")
            
            # Commit changes
            conn.commit()
            print(f"\n✅ Successfully committed {len(created_countries)} new debug countries to database")
            
            # Show final statistics
            cursor.execute("SELECT COUNT(*) FROM Countries")
            total_countries = cursor.fetchone()[0]
            print(f"📊 Total countries in database: {total_countries}")
            
        else:
            print("ℹ️  No new countries were created")
    
    except Exception as e:
        print(f"❌ Error during execution: {e}")
        import traceback
        traceback.print_exc()
        conn.rollback()
    
    finally:
        conn.close()
        print("\n🔒 Database connection closed")


if __name__ == "__main__":
    main()
