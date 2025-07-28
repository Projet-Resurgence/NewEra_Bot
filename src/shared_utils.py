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


# Global lists for autocompletion and validation
STRUCTURE_TYPES = ["Usine", "Base", "Ecole", "Logement", "Centrale", "Technocentre"]
SPECIALISATIONS = ["Terrestre", "Aerienne", "Navale", "NA"]


async def structure_type_autocomplete(
    interaction: discord.Interaction,
    current: str,
) -> List[app_commands.Choice[str]]:
    """
    Autocomplete function for structure type parameters in slash commands.
    Returns a list of available structure types.
    """
    choices = []
    current_lower = current.lower()

    for structure_type in STRUCTURE_TYPES:
        if current_lower in structure_type.lower():
            choices.append(
                app_commands.Choice(name=structure_type, value=structure_type)
            )

    return choices


async def specialisation_autocomplete(
    interaction: discord.Interaction,
    current: str,
) -> List[app_commands.Choice[str]]:
    """
    Autocomplete function for specialisation parameters in slash commands.
    Returns a list of available specialisations.
    """
    choices = []
    current_lower = current.lower()

    specialisation_emojis = {
        "Terrestre": "🚗",
        "Aerienne": "✈️",
        "Navale": "🚢",
        "NA": "⚙️",
    }

    for specialisation in SPECIALISATIONS:
        if current_lower in specialisation.lower():
            emoji = specialisation_emojis.get(specialisation, "")
            choices.append(
                app_commands.Choice(
                    name=f"{emoji} {specialisation}", value=specialisation
                )
            )

    return choices


async def structure_autocomplete(
    interaction: discord.Interaction,
    current: str,
) -> List[app_commands.Choice[str]]:
    """
    Autocomplete function for built structures in slash commands.
    Returns a list of structures owned by the user's country.
    """
    choices = []
    current_lower = current.lower()

    # Get database instance
    db_instance = get_db()
    if not db_instance or not interaction.guild:
        return choices

    try:
        # Get the user's country
        country_entity = CountryEntity(interaction.user, interaction.guild)
        country_id = country_entity.get_country_id()

        if not country_id:
            return choices

        # Get structures for this country
        cursor = db_instance.cur
        cursor.execute(
            """
            SELECT s.id, s.type, s.specialization, s.level, r.name as region_name
            FROM Structures s
            JOIN Regions r ON s.region_id = r.region_id
            WHERE r.country_id = ?
            ORDER BY s.type, s.level DESC
            LIMIT 25
        """,
            (country_id,),
        )

        structures = cursor.fetchall()

        for structure in structures:
            structure_id, struct_type, specialization, level, region_name = structure

            # Create search text
            search_text = f"{struct_type} {specialization} {region_name}".lower()

            if current_lower in search_text:
                choices.append(
                    app_commands.Choice(
                        name=f"{struct_type} {specialization} Niv.{level} ({region_name})",
                        value=str(structure_id),
                    )
                )

    except Exception as e:
        print(f"Error in structure_autocomplete: {e}")

    return choices


async def region_autocomplete(
    interaction: discord.Interaction,
    current: str,
) -> List[app_commands.Choice[str]]:
    """
    Autocomplete function for regions in slash commands.
    Returns a list of regions owned by the user's country.
    """
    choices = []
    current_lower = current.lower()

    # Get database instance
    db_instance = get_db()
    if not db_instance or not interaction.guild:
        return choices

    try:
        # Get the user's country
        country_entity = CountryEntity(interaction.user, interaction.guild)
        country_id = country_entity.get_country_id()

        if not country_id:
            return choices

        # Get regions for this country
        cursor = db_instance.cur
        cursor.execute(
            """
            SELECT region_id, name, population
            FROM Regions
            WHERE country_id = ?
            ORDER BY name
            LIMIT 25
        """,
            (country_id,),
        )

        regions = cursor.fetchall()

        for region in regions:
            region_id, region_name, population = region

            if current_lower in region_name.lower():
                choices.append(
                    app_commands.Choice(
                        name=f"🌍 {region_name} (Pop: {population:,})",
                        value=str(region_id),
                    )
                )

    except Exception as e:
        print(f"Error in region_autocomplete: {e}")

    return choices


async def technology_autocomplete(
    interaction: discord.Interaction,
    current: str,
) -> List[app_commands.Choice[str]]:
    """
    Autocomplete function for technologies in slash commands.
    Returns technologies based on user role and context:
    - Military admin: All technologies
    - Non-player: Nothing
    - Player in any channel: Country's public techs only
    - Player in secret channel: All country's techs (public + secret)
    """
    choices = []
    current_lower = current.lower()

    # Get database instance
    db_instance = get_db()
    if not db_instance or not interaction.guild:
        print(f"technology_autocomplete: No db_instance or guild")
        return choices

    try:
        print(
            f"technology_autocomplete: User {interaction.user.display_name} (ID: {interaction.user.id}) searching for '{current}'"
        )

        # Check if user is military admin first
        military_admin_role_id = 874869709223383091  # Hardcoded for testing
        # User is a player, get their country
        country_entity = CountryEntity(interaction.user, interaction.guild).to_dict()
        country_id = country_entity.get("id")
        if military_admin_role_id:
            military_admin_role_id = int(military_admin_role_id)
            is_military_admin = any(
                role.id == military_admin_role_id for role in interaction.user.roles
            )
            print(f"technology_autocomplete: Is military admin: {is_military_admin}")

            if is_military_admin:
                # Military admin sees ALL technologies
                cursor = db_instance.cur
                cursor.execute(
                    """
                    SELECT name FROM Countries
                    WHERE secret_channel_id = ?
                """,
                    (interaction.channel_id,),
                )
                secret_channel_techs = cursor.fetchall()
                print(
                    f"technology_autocomplete: Military admin found {len(secret_channel_techs)} secret channel technologies"
                )
                cursor.execute(
                    """
                    SELECT tech_id, name, developed_by, specialisation, technology_level, type, is_secret
                    FROM Technologies
                    WHERE name LIKE ?
                    AND (is_secret = 0 OR ? = 1)
                    ORDER BY name
                    LIMIT 25
                """,
                    (f"%{current}%", 1 if len(secret_channel_techs) > 0 else 0),
                )
                technologies = cursor.fetchall()
                print(
                    f"technology_autocomplete: Military admin found {len(technologies)} technologies"
                )

                specialisation_emojis = {
                    "Terrestre": "🚗",
                    "Aerienne": "✈️",
                    "Navale": "🚢",
                    "NA": "⚙️",
                }

                for tech in technologies:
                    tech_id, tech_name, tech_country_id, specialisation, tech_level, tech_type, is_secret = tech

                    if current_lower in tech_name.lower():
                        emoji = specialisation_emojis.get(specialisation, "🔧")
                        secret_indicator = " 🔒 " if is_secret and tech_country_id == country_id else " 🔒 (ADMIN)" if is_secret and tech_country_id != country_id else ""
                        choices.append(
                            app_commands.Choice(
                                name=f"{emoji} {tech_name} (Niv.{tech_level}) {secret_indicator}",
                                value=str(tech_id),
                            )
                        )
                print(
                    f"technology_autocomplete: Military admin returning {len(choices)} choices"
                )
                return choices

        # Check if user is a player (this was missing!)
        # For now, let's assume everyone who isn't military admin is a player
        # You can add proper player role check here later
        f = open("test.txt", "w")
        f.write(f"technology_autocomplete: Player country_id: {country_id}")

        if not country_id:
            # Player but no country, return nothing
            f.write(f"technology_autocomplete: No country found for player")
            return choices

        # Check if user is in their secret channel
        is_secret_channel = False
        country_data = db_instance.get_country_datas(country_id)
        if country_data:
            secret_channel_id = country_data.get("secret_channel_id")
            if secret_channel_id and str(interaction.channel_id) == str(
                secret_channel_id
            ):
                is_secret_channel = True
        f.write(
            f"technology_autocomplete: Is secret channel: {is_secret_channel}, Channel ID: {interaction.channel_id}"
        )

        # Get technologies based on context
        cursor = db_instance.cur

        # Debug: First check if there are ANY technologies in the database
        cursor.execute("SELECT COUNT(*) FROM Technologies")
        total_techs = cursor.fetchone()[0]
        f.write(f"technology_autocomplete: Total technologies in database: {total_techs}")

        # Debug: Check if there are exported technologies
        cursor.execute("SELECT COUNT(*) FROM Technologies WHERE exported = 1")
        exported_techs = cursor.fetchone()[0]
        f.write(f"technology_autocomplete: Exported technologies: {exported_techs}")

        # Debug: Check if there are technologies developed by this country
        cursor.execute(
            "SELECT COUNT(*) FROM Technologies WHERE developed_by = ?", (country_id,)
        )
        country_techs = cursor.fetchone()[0]
        f.write(
            f"technology_autocomplete: Technologies developed by country {country_id}: {country_techs}"
        )

        if is_secret_channel:
            # In secret channel: show all country's technologies (public + secret)
            query = """
                SELECT tech_id, name, specialisation, technology_level, type, is_secret
                FROM Technologies
                WHERE (developed_by = ? OR tech_id IN (
                    SELECT tech_id FROM TechnologyLicenses WHERE country_id = ?
                )) OR is_secret = 0
                ORDER BY name
                LIMIT 25
            """
            params = (country_id, country_id)
        else:
            # In any other channel: only public technologies
            query = """
                SELECT tech_id, name, specialisation, technology_level, type, is_secret
                FROM Technologies
                WHERE is_secret = 0
                ORDER BY name
                LIMIT 25
            """
            params = ()

        f.write(f"technology_autocomplete: Executing query with params: {params}")
        cursor.execute(query, params)
        technologies = cursor.fetchall()
        f.write(f"technology_autocomplete: Player found {len(technologies)} technologies")

        # Debug: If no results, try simpler query
        if not technologies:
            f.write(f"technology_autocomplete: No results, trying simpler query...")
            cursor.execute(
                """
                SELECT tech_id, name, specialisation, technology_level, type, 
                       COALESCE(is_secret, 0) as is_secret
                FROM Technologies
                WHERE name LIKE ?
                ORDER BY name
                LIMIT 10
            """,
                (f"%{current}%",),
            )
            all_matching = cursor.fetchall()
            f.write(
                f"technology_autocomplete: All matching technologies (debug): {len(all_matching)}"
            )
            for tech in all_matching:
                f.write(f"  - Tech: {tech}")

        specialisation_emojis = {
            "Terrestre": "🚗",
            "Aerienne": "✈️",
            "Navale": "🚢",
            "NA": "⚙️",
        }

        for tech in technologies:
            tech_id, tech_name, specialisation, tech_level, tech_type, is_secret = tech

            if current_lower in tech_name.lower():
                emoji = specialisation_emojis.get(specialisation, "🔧")
                secret_indicator = " 🔒" if is_secret and is_secret_channel else ""
                choices.append(
                    app_commands.Choice(
                        name=f"{emoji} {tech_name} (Niv.{tech_level}){secret_indicator}",
                        value=str(tech_id),
                    )
                )

        f.write(f"technology_autocomplete: Player returning {len(choices)} choices")
        f.close()

    except Exception as e:
        f = open("error_log.txt", "a")
        f.write(f"Error in technology_autocomplete: {e}")
        f.close()
        import traceback

        traceback.print_exc()

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
    "structure_type_autocomplete",
    "specialisation_autocomplete",
    "structure_autocomplete",
    "region_autocomplete",
    "technology_autocomplete",
    "STRUCTURE_TYPES",
    "SPECIALISATIONS",
    "convert",
    "amount_converter",
    "ERROR_COLOR_INT",
    "MONEY_COLOR_INT",
    "P_POINTS_COLOR_INT",
    "D_POINTS_COLOR_INT",
    "ALL_COLOR_INT",
    "FACTORY_COLOR_INT",
]
