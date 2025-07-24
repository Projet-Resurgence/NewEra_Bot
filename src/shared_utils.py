"""
Centralized utilities module for NEBot.
Contains all shared utility class instances and common classes.
"""

import discord
from discord import app_commands
from discord.ext import commands
from typing import Union, List

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
                try:
                    country_id = int(argument)
                    db_instance = get_db()
                    country_role_id = int(
                        db_instance.get_country_role_with_id(country_id)
                    )
                    if not country_role_id:
                        raise commands.BadArgument("Entité inconnue.")
                    role = ctx.guild.get_role(country_role_id)
                    if not role:
                        raise commands.BadArgument("Rôle introuvable.")
                    entity = CountryEntity(role, ctx.guild)
                except (commands.BadArgument, ValueError):
                    try:
                        country_name = argument.strip().lower()
                        db_instance = get_db()
                        country_id = db_instance.get_country_by_name(
                            country_name.capitalize()
                        )
                        if not country_id:
                            raise commands.BadArgument("Pays inconnu.")
                        role = ctx.guild.get_role(
                            int(db_instance.get_country_role_with_id(country_id))
                        )
                        if not role:
                            raise commands.BadArgument("Rôle introuvable.")
                        entity = CountryEntity(role, ctx.guild)
                    except commands.BadArgument:
                        raise commands.BadArgument("Entité inconnue.")
        return entity.to_dict()


async def country_autocomplete(
    interaction: discord.Interaction,
    current: str,
) -> List[app_commands.Choice[str]]:
    """
    Autocomplete function for country parameters in slash commands.
    Returns a list of Discord roles (countries) and users that match the current input.
    """
    choices = []
    current_lower = current.lower()

    # Get database instance
    db_instance = get_db()
    if not db_instance or not interaction.guild:
        return choices

    try:
        # Get all countries by querying the Countries table directly
        cursor = db_instance.cur
        cursor.execute("SELECT country_id, name, role_id FROM Countries ORDER BY name")
        countries = cursor.fetchall()

        # Add country roles first (prioritized)
        for country in countries:
            if len(choices) >= 20:  # Leave some space for users
                break

            country_id, country_name, role_id = country

            if current_lower in country_name.lower():
                # Get the role to verify it exists
                role = interaction.guild.get_role(int(role_id)) if role_id else None
                if role:
                    choices.append(
                        app_commands.Choice(
                            name=f"🏛️ {country_name}", value=str(role.id)
                        )
                    )

        # Add users/members if there's still space and current input looks like a user search
        if len(choices) < 20 and len(current) >= 2:
            # Get members who have government positions (are country players)
            cursor.execute("SELECT DISTINCT player_id FROM Governments")
            government_players = [row[0] for row in cursor.fetchall()]

            for player_id in government_players:
                if len(choices) >= 25:  # Discord limit
                    break

                try:
                    member = interaction.guild.get_member(int(player_id))
                    if member and (
                        current_lower in member.display_name.lower()
                        or current_lower in member.name.lower()
                    ):
                        # Get the country name for this member
                        member_country_id = db_instance.get_players_government(
                            member.id
                        )
                        if member_country_id:
                            country_data = db_instance.get_country_datas(
                                member_country_id
                            )
                            country_name = (
                                country_data.get("name", "Pays inconnu")
                                if country_data
                                else "Pays inconnu"
                            )

                            choices.append(
                                app_commands.Choice(
                                    name=f"👤 {member.display_name} ({country_name})",
                                    value=str(member.id),
                                )
                            )
                except (ValueError, AttributeError):
                    continue

    except Exception as e:
        # Fallback: show guild roles that might be countries
        for role in interaction.guild.roles:
            if len(choices) >= 25:
                break
            if current_lower in role.name.lower() and not role.is_default():
                choices.append(
                    app_commands.Choice(name=f"🏛️ {role.name}", value=str(role.id))
                )

    return choices


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
    "country_autocomplete",
    "convert",
    "amount_converter",
    "ERROR_COLOR_INT",
    "MONEY_COLOR_INT",
    "P_POINTS_COLOR_INT",
    "D_POINTS_COLOR_INT",
    "ALL_COLOR_INT",
    "FACTORY_COLOR_INT",
]
