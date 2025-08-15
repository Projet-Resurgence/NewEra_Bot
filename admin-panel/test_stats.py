#!/usr/bin/env python3
"""
Test script to debug Stats model issue
"""
import sys
import os

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app import app, db, Stats

with app.app_context():
    try:
        # Try to get the Stats table metadata
        stats_table = Stats.__table__
        print(f"Stats table columns: {[col.name for col in stats_table.columns]}")

        # Try to query Stats
        stats_count = Stats.query.count()
        print(f"Stats count: {stats_count}")

    except Exception as e:
        print(f"Error: {e}")
        import traceback

        traceback.print_exc()
