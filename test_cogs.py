#!/usr/bin/env python3
"""
Test script to verify cog loading functionality.
"""

import sys
import os
import asyncio
import importlib.util

# Add src directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))


async def test_cog_import():
    """Test if the economy cog can be imported successfully."""
    try:
        # Test import of the cog module
        spec = importlib.util.spec_from_file_location(
            "economy",
            os.path.join(os.path.dirname(__file__), "src", "cogs", "economy.py"),
        )
        economy_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(economy_module)

        print("✅ Economy cog imported successfully")
        print(f"✅ Economy class found: {hasattr(economy_module, 'Economy')}")
        print(f"✅ Setup function found: {hasattr(economy_module, 'setup')}")

        return True
    except Exception as e:
        print(f"❌ Failed to import economy cog: {e}")
        return False


if __name__ == "__main__":
    print("🧪 Testing NEBot cog structure...")
    success = asyncio.run(test_cog_import())
    if success:
        print("🎉 All tests passed! Cog structure is working correctly.")
    else:
        print("💥 Tests failed. Please check the cog implementation.")
