#!/usr/bin/env python3
"""
Test script to verify bot cog loading without running the full bot.
"""

import sys
import os
import asyncio
import discord
from discord.ext import commands

# Add src directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))


async def test_bot_cog_loading():
    """Test if the bot can load cogs successfully."""
    try:
        # Create a minimal bot for testing
        intents = discord.Intents.default()
        intents.message_content = True

        bot = commands.Bot(command_prefix=".", intents=intents)

        # Try to load the cog
        await bot.load_extension("cogs.economy")
        print("✅ Economy cog loaded successfully into bot")

        # Check if commands are registered
        economy_commands = [cmd for cmd in bot.commands if cmd.cog_name == "Economy"]
        print(
            f"✅ Found {len(economy_commands)} economy commands: {[cmd.name for cmd in economy_commands]}"
        )

        # Clean up
        await bot.close()

        return True
    except Exception as e:
        print(f"❌ Failed to load cog into bot: {e}")
        import traceback

        traceback.print_exc()
        return False


if __name__ == "__main__":
    print("🧪 Testing NEBot cog loading into bot...")
    success = asyncio.run(test_bot_cog_loading())
    if success:
        print("🎉 All tests passed! Bot can load cogs correctly.")
    else:
        print("💥 Tests failed. Please check the bot and cog implementation.")
