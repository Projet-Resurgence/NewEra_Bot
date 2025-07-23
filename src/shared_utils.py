"""
Centralized utilities module for NEBot.
Contains all shared utility class instances and common classes.
"""

import discord
from discord.ext import commands
from typing import Union

# Import the base classes
from db import Database, UsefulDatas
from discord_utils import discordUtils
from currency import convert, amount_converter

# Global instances (will be initialized when bot is ready)
db = None
dUtils = None

def initialize_utilities(bot, bat_types, bat_buffs):
    """Initialize all utility instances with the bot instance."""
    global db, dUtils
    uDatas = UsefulDatas(bat_types, bat_buffs)
    db = Database("datas/rts.db", uDatas)
    dUtils = discordUtils(bot, db)

def get_db():
    """Get the global database instance."""
    global db
    if db is None:
        db = Database()
    return db

def get_discord_utils(bot=None, db=None):
    """Get the global discord utils instance."""
    global dUtils
    if dUtils is None and bot is not None:
        dUtils = discordUtils(bot, db)
    return dUtils

class CountryEntity:
    """Centralized CountryEntity class used across all cogs."""

    def __init__(self, entity: Union[discord.User, discord.Role], guild: discord.Guild):
        self.entity = entity
        self.guild = guild

    @property
    def is_user(self) -> bool:
        return isinstance(self.entity, (discord.User, discord.Member))

    @property
    def is_role(self) -> bool:
        return isinstance(self.entity, discord.Role)

    def get_country_id(self) -> int:
        db_instance = get_db()
        if not self.is_user:
            return db_instance.get_country_by_role(self.entity.id)

        member = self.guild.get_member(self.entity.id)
        if not member:
            return None
        return db_instance.get_players_government(member.id)

    def to_dict(self) -> dict:
        db_instance = get_db()
        country_id = self.get_country_id()
        if not country_id:
            return {
                "name": getattr(self.entity, "name", "Inconnu"),
                "id": None,
                "role": None,
            }

        datas = db_instance.get_country_datas(country_id)
        if not datas:
            return {
                "name": getattr(self.entity, "name", "Inconnu"),
                "id": country_id,
                "role": None,
            }
        role = self.guild.get_role(int(datas.get("role_id")))
        return {"name": datas.get("name"), "id": country_id, "role": role}


class CountryConverter(commands.Converter):
    """Centralized CountryConverter class used across all cogs."""

    async def convert(self, ctx, argument):
        try:
            member = await commands.MemberConverter().convert(ctx, argument)
            entity = CountryEntity(member, ctx.guild)
        except commands.BadArgument:
            try:
                role = await commands.RoleConverter().convert(ctx, argument)
                entity = CountryEntity(role, ctx.guild)
            except commands.BadArgument:
                raise commands.BadArgument("Entité inconnue.")

        return entity.to_dict()


# Color constants used across cogs
ERROR_COLOR_INT = int("FF5733", 16)
MONEY_COLOR_INT = int("FFF005", 16)
P_POINTS_COLOR_INT = int("006AFF", 16)
D_POINTS_COLOR_INT = int("8b1bd1", 16)
ALL_COLOR_INT = int("00FF44", 16)
FACTORY_COLOR_INT = int("6E472E", 16)

# Export commonly used functions
__all__ = [
    "initialize_utilities",
    "get_db",
    "get_discord_utils",
    "CountryEntity",
    "CountryConverter",
    "convert",
    "amount_converter",
    "ERROR_COLOR_INT",
    "MONEY_COLOR_INT",
    "P_POINTS_COLOR_INT",
    "D_POINTS_COLOR_INT",
    "ALL_COLOR_INT",
    "FACTORY_COLOR_INT",
]
