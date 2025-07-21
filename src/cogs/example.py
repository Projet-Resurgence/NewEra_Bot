"""
Example of how to create additional cogs for NEBot.
This template can be used to create new command categories.
"""

import discord
from discord.ext import commands
from typing import Union


class ExampleCog(commands.Cog):
    """Example cog showing the basic structure for NEBot cogs."""

    def __init__(self, bot):
        self.bot = bot
        self.error_color_int = int("FF5733", 16)
        self.success_color_int = int("00FF44", 16)

    @commands.command(name="hello")
    async def hello_command(self, ctx):
        """Example command - says hello to the user."""
        embed = discord.Embed(
            title="Hello!",
            description=f"Hello {ctx.author.mention}! This is an example command from a cog.",
            color=self.success_color_int,
        )
        await ctx.send(embed=embed)

    @commands.command(name="ping")
    async def ping_command(self, ctx):
        """Example command - shows bot latency."""
        latency = round(self.bot.latency * 1000)
        embed = discord.Embed(
            title="Pong! 🏓",
            description=f"Bot latency: {latency}ms",
            color=self.success_color_int,
        )
        await ctx.send(embed=embed)

    @commands.Cog.listener()
    async def on_message(self, message):
        """Example event listener - responds to specific messages."""
        if message.author.bot:
            return

        # Example: React to messages containing "test"
        if "test" in message.content.lower():
            await message.add_reaction("✅")


async def setup(bot):
    """Setup function to add the cog to the bot."""
    await bot.add_cog(ExampleCog(bot))
