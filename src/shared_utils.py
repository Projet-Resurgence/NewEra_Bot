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

import re

# Global instances (will be initialized when bot is ready)
db = None
dUtils = None


def initialize_utilities(bot, bat_types, bat_buffs, unit_types):
    """Initialize all utility instances with the bot instance."""
    global db, dUtils
    uDatas = UsefulDatas(bat_types, bat_buffs, unit_types)
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

    def __init__(self, entity: Union[discord.User, discord.Member, discord.Role, discord.TextChannel], guild: discord.Guild):
        self.entity = entity
        self.guild = guild

    @property
    def is_user(self) -> bool:
        return isinstance(self.entity, (discord.User, discord.Member))

    @property
    def is_role(self) -> bool:
        return isinstance(self.entity, discord.Role)
    
    @property
    def is_channel(self) -> bool:
        return isinstance(self.entity, discord.TextChannel)

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
                "channel": None,
            }

        datas = db_instance.get_country_datas(country_id)
        if not datas:
            return {
                "name": getattr(self.entity, "name", "Inconnu"),
                "id": country_id,
                "channel": None,
                "role": None,
            }
        role = self.guild.get_role(int(datas.get("role_id")))
        channel = self.guild.get_channel(int(datas.get("public_channel_id")))
        return {"name": datas.get("name"), "id": country_id, "role": role, "channel": channel}

class CountryConverter(commands.Converter):
    """Centralized CountryConverter class used across all cogs."""

    async def convert(self, ctx, argument):
        entity = await self._convert_member(ctx, argument)
        if entity:
            return entity.to_dict()

        entity = await self._convert_role(ctx, argument)
        if entity:
            return entity.to_dict()

        entity = await self._convert_channel(ctx, argument)
        if entity:
            return entity.to_dict()

        entity = await self._convert_country_id(ctx, argument)
        if entity:
            return entity.to_dict()

        entity = await self._convert_country_name(ctx, argument)
        if entity:
            return entity.to_dict()

        raise commands.BadArgument(f"Entité inconnue : {argument}")

    async def _convert_member(self, ctx, argument):
        try:
            member = await commands.MemberConverter().convert(ctx, argument)
            return CountryEntity(member, ctx.guild)
        except commands.BadArgument:
            return None

    async def _convert_role(self, ctx, argument):
        try:
            role = await commands.RoleConverter().convert(ctx, argument)
            return CountryEntity(role, ctx.guild)
        except commands.BadArgument:
            return None

    async def _convert_channel(self, ctx, argument):
        try:
            channel = await commands.TextChannelConverter().convert(ctx, argument)
            return CountryEntity(channel, ctx.guild)
        except commands.BadArgument:
            return None

    async def _convert_country_id(self, ctx, argument):
        try:
            country_id = int(argument)
            db_instance = get_db()
            country_role_id = int(db_instance.get_country_role_with_id(country_id))
            if not country_role_id:
                return None
            role = ctx.guild.get_role(country_role_id)
            if not role:
                return None
            return CountryEntity(role, ctx.guild)
        except (ValueError, TypeError):
            return None

    async def _convert_country_name(self, ctx, argument):
        try:
            country_name = argument.strip().lower()
            db_instance = get_db()
            country_id = db_instance.get_country_by_name(country_name.capitalize())
            if not country_id:
                return None
            role = ctx.guild.get_role(int(db_instance.get_country_role_with_id(country_id)))
            if not role:
                return None
            return CountryEntity(role, ctx.guild)
        except Exception:
            return None

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
    current_lower = re.sub(r"[^\w\s]", "", current_lower)
    current_lower = current_lower.strip()
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

# Combined types for unified handling
ALL_BUILDABLE_TYPES = STRUCTURE_TYPES + ["Centrale électrique", "Infrastructure"]


async def structure_type_autocomplete(
    interaction: discord.Interaction,
    current: str,
) -> List[app_commands.Choice[str]]:
    """
    Autocomplete function for structure type parameters in slash commands.
    Returns a list of available structure types including power plants and infrastructures.
    """
    choices = []
    current_lower = current.lower()
    current_lower = re.sub(r"[^\w\s]", "", current_lower)
    current_lower = current_lower.strip()

    # Add traditional structure types
    for structure_type in STRUCTURE_TYPES:
        if current_lower in structure_type.lower():
            choices.append(
                app_commands.Choice(name=f"🏭 {structure_type}", value=structure_type)
            )

    # Add power plants
    if (
        current_lower in "centrale électrique"
        or current_lower in "centrale"
        or current_lower in "électrique"
    ):
        choices.append(
            app_commands.Choice(
                name="⚡ Centrale électrique", value="Centrale électrique"
            )
        )

    # Add infrastructures
    if (
        current_lower in "infrastructure"
        or current_lower in "route"
        or current_lower in "chemin"
    ):
        choices.append(
            app_commands.Choice(name="🛣️ Infrastructure", value="Infrastructure")
        )

    return choices


async def power_plant_type_autocomplete(
    interaction: discord.Interaction,
    current: str,
) -> List[app_commands.Choice[str]]:
    """
    Autocomplete function for power plant types.
    Dynamically loads available types from the database.
    """
    choices = []
    current_lower = current.lower()
    current_lower = re.sub(r"[^\w\s]", "", current_lower)
    current_lower = current_lower.strip()

    # Get database instance
    db_instance = get_db()
    if not db_instance:
        return choices

    try:
        # Get all distinct power plant types from the database
        cursor = db_instance.cur
        cursor.execute("SELECT DISTINCT type FROM PowerPlantsDatas ORDER BY type")
        power_plant_types = [row[0] for row in cursor.fetchall()]

        power_plant_emojis = {
            "éolien onshore": "🌬️",
            "éolien offshore": "🌊",
            "Solaire": "☀️",
            "Centrale solaire": "☀️",
            "Nucléaire": "☢️",
            "Nucléaire OCC": "☢️",
            "Nucléaire ORT": "☢️",
            "Hydroélectrique": "💧",
            "Charbon": "⛏️",
            "Pétrole": "🛢️",
            "Gaz": "🔥",
            "Géothermie": "🌋",
            "Biomasse": "🌿",
        }

        for plant_type in power_plant_types:
            if current_lower in plant_type.lower():
                emoji = power_plant_emojis.get(plant_type, "⚡")
                choices.append(
                    app_commands.Choice(name=f"{emoji} {plant_type}", value=plant_type)
                )

        return choices

    except Exception as e:
        print(f"Error in power_plant_type_autocomplete: {e}")
        return choices


async def infrastructure_type_autocomplete(
    interaction: discord.Interaction,
    current: str,
) -> List[app_commands.Choice[str]]:
    """
    Autocomplete function for infrastructure types.
    Dynamically loads available types from the database.
    """
    choices = []
    current_lower = current.lower()
    current_lower = re.sub(r"[^\w\s]", "", current_lower)
    current_lower = current_lower.strip()

    # Get database instance
    db_instance = get_db()
    if not db_instance:
        return choices

    try:
        # Get all infrastructure types from the database
        cursor = db_instance.cur
        cursor.execute("SELECT DISTINCT type FROM InfrastructureTypes ORDER BY type")
        infrastructure_types = [row[0] for row in cursor.fetchall()]

        infrastructure_emojis = {
            "Route sommaire": "🛤️",
            "Route": "🛣️",
            "Autoroute": "🛣️",
            "Tunnel route sommaire": "🚇",
            "Tunnel route": "🚇",
            "Tunnel autoroute": "🚇",
            "Chemin de fer": "🚂",
            "Chemin de fer électrifié": "🚄",
            "Tunnel chemin de fer": "🚇",
            "Tunnel chemin de fer électrifié": "🚇",
        }

        for infra_type in infrastructure_types:
            if current_lower in infra_type.lower():
                emoji = infrastructure_emojis.get(infra_type, "🛣️")
                choices.append(
                    app_commands.Choice(name=f"{emoji} {infra_type}", value=infra_type)
                )

        return choices

    except Exception as e:
        print(f"Error in infrastructure_type_autocomplete: {e}")
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
    current_lower = re.sub(r"[^\w\s]", "", current_lower)
    current_lower = current_lower.strip()

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
) -> List[app_commands.Choice[int]]:
    """
    Autocomplete function for structure IDs in slash commands.
    Returns only traditional structures (Usine, Base, Ecole, etc.) that belong to the user's country.
    Returns integer IDs for direct use in commands.
    """
    choices = []
    current_lower = current.lower()
    current_lower = re.sub(r"[^\w\s]", "", current_lower)
    current_lower = current_lower.strip()

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

        # Get only traditional structures for this country
        cursor = db_instance.cur
        cursor.execute(
            """
            SELECT s.id, s.type, s.specialisation, s.level, r.name as region_name
            FROM Structures s
            JOIN Regions r ON s.region_id = r.region_id
            WHERE r.country_id = ?
            ORDER BY s.type, s.level DESC
            LIMIT 25
        """,
            (country_id,),
        )
        structures = cursor.fetchall()

        # Process traditional structures
        for structure in structures:
            structure_id, struct_type, specialisation, level, region_name = structure
            search_text = f"{struct_type} {specialisation} {region_name}".lower()

            if not current_lower or current_lower in search_text:
                choices.append(
                    app_commands.Choice(
                        name=f"🏭 {struct_type} {specialisation} Niv.{level} ({region_name})",
                        value=structure_id,  # Return integer ID directly
                    )
                )

    except Exception as e:
        print(f"Error in structure_autocomplete: {e}")

    return choices[:25]  # Discord limit


async def power_plant_autocomplete(
    interaction: discord.Interaction,
    current: str,
) -> List[app_commands.Choice[int]]:
    """
    Autocomplete function for power plant IDs in slash commands.
    Returns only power plants that belong to the user's country.
    Returns integer IDs for direct use in commands.
    """
    choices = []
    current_lower = current.lower()
    current_lower = re.sub(r"[^\w\s]", "", current_lower)
    current_lower = current_lower.strip()

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

        # Get power plants for this country
        cursor = db_instance.cur
        cursor.execute(
            """
            SELECT p.id, p.type, p.level, r.name as region_name
            FROM PowerPlants p
            JOIN Regions r ON p.region_id = r.region_id
            WHERE r.country_id = ?
            ORDER BY p.type, p.level DESC
            LIMIT 25
        """,
            (country_id,),
        )

        try:
            power_plants = cursor.fetchall()
        except:
            power_plants = []  # Table might not exist yet

        # Process power plants
        for plant in power_plants:
            plant_id, plant_type, level, region_name = plant
            search_text = f"{plant_type} centrale {region_name}".lower()

            if not current_lower or current_lower in search_text:
                choices.append(
                    app_commands.Choice(
                        name=f"⚡ {plant_type} Niv.{level} ({region_name})",
                        value=plant_id,  # Return integer ID directly
                    )
                )

    except Exception as e:
        print(f"Error in power_plant_autocomplete: {e}")

    return choices[:25]  # Discord limit


async def infrastructure_autocomplete(
    interaction: discord.Interaction,
    current: str,
) -> List[app_commands.Choice[int]]:
    """
    Autocomplete function for infrastructure IDs in slash commands.
    Returns only infrastructures that belong to the user's country.
    Returns integer IDs for direct use in commands.
    """
    choices = []
    current_lower = current.lower()
    current_lower = re.sub(r"[^\w\s]", "", current_lower)
    current_lower = current_lower.strip()

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

        # Get infrastructures for this country
        cursor = db_instance.cur
        cursor.execute(
            """
            SELECT i.id, i.type, i.length_km, r.name as region_name
            FROM Infrastructure i
            JOIN Regions r ON i.region_id = r.region_id
            WHERE r.country_id = ?
            ORDER BY i.type
            LIMIT 25
        """,
            (country_id,),
        )

        try:
            infrastructures = cursor.fetchall()
        except:
            infrastructures = []  # Table might not exist yet

        # Process infrastructures
        for infra in infrastructures:
            infra_id, infra_type, length_km, region_name = infra
            search_text = f"{infra_type} {region_name}".lower()

            if not current_lower or current_lower in search_text:
                choices.append(
                    app_commands.Choice(
                        name=f"🛣️ {infra_type} {length_km}km ({region_name})",
                        value=infra_id,  # Return integer ID directly
                    )
                )

    except Exception as e:
        print(f"Error in infrastructure_autocomplete: {e}")

    return choices[:25]  # Discord limit


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
    current_lower = re.sub(r"[^\w\s]", "", current_lower)
    current_lower = current_lower.strip()

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


async def free_region_autocomplete(
    interaction: discord.Interaction,
    current: str,
) -> List[app_commands.Choice[str]]:
    """
    Autocomplete function for regions in slash commands.
    Returns a list of unowned regions.
    """
    choices = []
    current_lower = current.lower()
    current_lower = re.sub(r"[^\w\s]", "", current_lower)
    current_lower = current_lower.strip()

    # Get database instance
    db_instance = get_db()
    if not db_instance or not interaction.guild:
        return choices

    try:
        cursor = db_instance.cur
        if current_lower:
            cursor.execute(
                """
            SELECT r.region_id, r.name, r.population, r.geographical_area_id
            FROM Regions r
            JOIN GeographicalAreas g ON r.geographical_area_id = g.geographical_area_id
            WHERE (r.country_id = 0 OR r.country_id IS NULL)
              AND (LOWER(g.name) LIKE ? OR LOWER(r.name) LIKE ?)
            ORDER BY r.name
            LIMIT 25
            """,
                (f"{current_lower}%", f"{current_lower}%"),
            )
        else:
            cursor.execute(
                """
            SELECT r.region_id, r.name, r.population, r.geographical_area_id
            FROM Regions r
            WHERE (r.country_id = 0 OR r.country_id IS NULL)
            ORDER BY r.name
            LIMIT 25
            """
            )
        regions = cursor.fetchall()

        for region in regions:
            region_id, region_name, population, geographical_area_id = region
            geographical_area = db_instance.get_geographical_area(geographical_area_id)

            if (
                current_lower in region_name.lower()
                or current_lower in geographical_area["name"].lower()
            ):
                choices.append(
                    app_commands.Choice(
                        name=f"🌍 {geographical_area['name']}: {region_name} (Pop: {population:,})",
                        value=str(region_id),
                    )
                )

    except Exception as e:
        print(f"Error in region_autocomplete: {e}")

    return choices


async def factory_autocomplete(
    interaction: discord.Interaction,
    current: str,
) -> List[app_commands.Choice[int]]:
    """
    Autocomplete function for factory structures in production commands.
    Returns only factories (Usine) that belong to the user's country.
    Returns integer IDs for direct use in commands.
    """
    choices = []
    current_lower = current.lower()
    current_lower = re.sub(r"[^\w\s]", "", current_lower)
    current_lower = current_lower.strip()

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

        # Get only factories (Usine) for this country
        cursor = db_instance.cur
        cursor.execute(
            """
            SELECT s.id, s.specialisation, s.level, r.name as region_name
            FROM Structures s
            JOIN Regions r ON s.region_id = r.region_id
            WHERE r.country_id = ? AND s.type = 'Usine'
            ORDER BY s.specialisation, s.level DESC
            LIMIT 25
        """,
            (country_id,),
        )
        factories = cursor.fetchall()

        # Process factories
        for factory in factories:
            factory_id, specialisation, level, region_name = factory
            search_text = f"usine {specialisation} {region_name}".lower()

            if not current_lower or current_lower in search_text:
                choices.append(
                    app_commands.Choice(
                        name=f"🏭 Usine {specialisation} Niv.{level} ({region_name})",
                        value=factory_id,  # Return integer ID directly
                    )
                )

    except Exception as e:
        print(f"Error in factory_autocomplete: {e}")

    return choices[:25]  # Discord limit


async def technocentre_autocomplete(
    interaction: discord.Interaction,
    current: str,
) -> List[app_commands.Choice[int]]:
    """
    Autocomplete function for technocentre structures in technology development commands.
    Returns only technocentres that belong to the user's country.
    Returns integer IDs for direct use in commands.
    """
    choices = []
    current_lower = current.lower()
    current_lower = re.sub(r"[^\w\s]", "", current_lower)
    current_lower = current_lower.strip()

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

        # Get only technocentres for this country
        cursor = db_instance.cur
        cursor.execute(
            """
            SELECT s.id, s.specialisation, s.level, r.name as region_name
            FROM Structures s
            JOIN Regions r ON s.region_id = r.region_id
            WHERE r.country_id = ? AND s.type = 'Technocentre'
            ORDER BY s.specialisation, s.level DESC
            LIMIT 25
        """,
            (country_id,),
        )
        technocentres = cursor.fetchall()

        # Process technocentres
        for technocentre in technocentres:
            technocentre_id, specialisation, level, region_name = technocentre
            search_text = f"technocentre {specialisation} {region_name}".lower()

            if not current_lower or current_lower in search_text:
                choices.append(
                    app_commands.Choice(
                        name=f"🔬 Technocentre {specialisation} Niv.{level} ({region_name})",
                        value=technocentre_id,  # Return integer ID directly
                    )
                )

    except Exception as e:
        print(f"Error in technocentre_autocomplete: {e}")

    return choices[:25]  # Discord limit


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
    current_lower = re.sub(r"[^\w\s]", "", current_lower)
    current_lower = current_lower.strip()

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
                    (
                        tech_id,
                        tech_name,
                        tech_country_id,
                        specialisation,
                        tech_level,
                        tech_type,
                        is_secret,
                    ) = tech

                    if current_lower in tech_name.lower():
                        emoji = specialisation_emojis.get(specialisation, "🔧")
                        secret_indicator = (
                            " 🔒 "
                            if is_secret and tech_country_id == country_id
                            else (
                                " 🔒 (ADMIN)"
                                if is_secret and tech_country_id != country_id
                                else ""
                            )
                        )
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
        f.write(
            f"technology_autocomplete: Total technologies in database: {total_techs}"
        )

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
        f.write(
            f"technology_autocomplete: Player found {len(technologies)} technologies"
        )

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


async def loan_years_autocomplete(
    interaction: discord.Interaction,
    current: str,
) -> List[app_commands.Choice[int]]:
    """Autocomplete for loan years (1-10 years only)."""
    valid_years = [i for i in range(1, 11)]

    if current:
        try:
            current_int = int(current)
            filtered_years = [
                year for year in valid_years if str(year).startswith(str(current_int))
            ]
        except ValueError:
            filtered_years = valid_years
    else:
        filtered_years = valid_years

    return [
        app_commands.Choice(name=f"{year} ans", value=year) for year in filtered_years
    ]


async def loan_reference_autocomplete(
    interaction: discord.Interaction,
    current: str,
) -> List[app_commands.Choice[str]]:
    """
    Autocomplete function for loan references in repay commands.
    Returns a list of active loan references for the user's country.
    """
    choices = []
    current_lower = current.lower()
    current_lower = re.sub(r"[^\w\s]", "", current_lower)
    current_lower = current_lower.strip()

    # Get database instance
    db_instance = get_db()
    if not db_instance or not interaction.guild:
        return choices

    try:
        # Get user's country
        country_entity = CountryEntity(interaction.user, interaction.guild)
        country_id = country_entity.get_country_id()

        if not country_id:
            return choices

        # Get active debts for the user's country
        debts = db_instance.get_debts_by_country(country_id)

        for debt in debts:
            ref = debt["debt_reference"]
            remaining = debt["remaining_amount"]

            # Filter based on current input
            if current_lower in ref.lower():
                choices.append(
                    app_commands.Choice(
                        name=f"{ref} (Restant: {remaining:,})", value=ref
                    )
                )

    except Exception as e:
        print(f"Error in loan_reference_autocomplete: {e}")

    return choices[:25]  # Discord limit


# ============================================================================
# ECO LOGGER SYSTEM - Unified economic event logging
# ============================================================================


class EcoLogEvent:
    """Unified event logging class for all economic transactions."""

    def __init__(
        self,
        code: str,
        amount: int,
        user1: discord.User,
        user2: discord.User = None,
        point_type: int = 1,
        extra_data: dict = None,
    ):
        from currency import convert

        self.code = code
        self.amount = convert(str(amount)) if len(str(amount)) > 3 else amount
        self.user1 = user1
        self.user2 = user2
        self.point_type = point_type  # 1=political, 2=diplomatic
        self.extra_data = extra_data or {}

        # Color constants
        self.money_color_int = MONEY_COLOR_INT
        self.p_points_color_int = P_POINTS_COLOR_INT
        self.d_points_color_int = D_POINTS_COLOR_INT
        self.error_color_int = ERROR_COLOR_INT

    def get_embed(self):
        """Generate the appropriate embed based on the code."""
        # Money-related transactions
        if self.code in [
            "TRANSFER",
            "ADD_MONEY",
            "SET_MONEY",
            "PAYMENT",
            "REMOVE_MONEY",
            "LOAN_TAKEN",
            "LOAN_REPAID",
            "ECONOMY_RESET",
            "ECONOMY_RESET_ATTEMPT",
        ]:
            return self._money_embed()

        # Points-related transactions
        elif self.code in [
            "ADD_POINTS",
            "SET_POINTS",
            "USE_POINTS",
            "REMOVE_POINTS",
            "POINTS_RESET",
            "POINTS_RESET_ATTEMPT",
        ]:
            return self._points_embed()

        return None

    def _money_embed(self):
        """Generate embed for money-related transactions."""
        alert = "<a:NE_Alert:1261090848024690709>"

        templates = {
            "TRANSFER": (
                "💰 Transfert entre pays",
                ":moneybag: **{u1}** a transféré **{amt}** à **{u2}**.",
            ),
            "ADD_MONEY": (
                "{} Ajout d'argent administratif".format(alert),
                ":moneybag: **{u1}** s'est fait ajouter **{amt}** par **{u2}**.",
            ),
            "SET_MONEY": (
                "{} Solde défini administrativement".format(alert),
                ":moneybag: **{u1}** s'est fait définir son solde à **{amt}** par **{u2}**.",
            ),
            "PAYMENT": (
                "💸 Paiement effectué",
                ":moneybag: **{u1}** a payé **{amt}** à la banque.",
            ),
            "REMOVE_MONEY": (
                "{} {} Retrait d'argent administratif".format(alert, alert),
                ":moneybag: **{u1}** s'est fait retirer **{amt}** par **{u2}**.",
            ),
            "LOAN_TAKEN": (
                "🏦 Emprunt contracté",
                ":bank: **{u1}** a contracté un emprunt de **{amt}** auprès de la banque.",
            ),
            "LOAN_REPAID": (
                "💳 Remboursement d'emprunt",
                ":bank: **{u1}** a remboursé **{amt}** d'emprunt à la banque.",
            ),
            "ECONOMY_RESET": (
                "{} {} {} RESET ÉCONOMIQUE COMPLET".format(alert, alert, alert),
                ":moneybag: **{u1}** a réinitialisé l'économie entière.",
            ),
            "ECONOMY_RESET_ATTEMPT": (
                "{} {} {} {} TENTATIVE DE RESET ÉCONOMIQUE".format(
                    alert, alert, alert, alert
                ),
                ":moneybag: **{u1}** a tenté de réinitialiser l'économie.",
            ),
        }

        title, desc_template = templates.get(self.code, (None, None))
        if not title:
            return None

        desc = desc_template.format(
            u1=f"{self.user1.name} ({self.user1.id})",
            u2=f"{self.user2.name} ({self.user2.id})" if self.user2 else "❓",
            amt=self.amount,
        )

        embed = discord.Embed(title=title, description=desc, color=self.money_color_int)

        # Add extra data if available
        if self.extra_data:
            if "reference" in self.extra_data:
                embed.add_field(
                    name="Référence", value=self.extra_data["reference"], inline=True
                )
            if "interest_rate" in self.extra_data:
                embed.add_field(
                    name="Taux d'intérêt",
                    value=f"{self.extra_data['interest_rate']:.2f}%",
                    inline=True,
                )
            if "duration" in self.extra_data:
                embed.add_field(
                    name="Durée",
                    value=f"{self.extra_data['duration']} ans",
                    inline=True,
                )

        return embed

    def _points_embed(self):
        """Generate embed for points-related transactions."""
        alert = "<a:NE_Alert:1261090848024690709>"
        p_type = "points politiques" if self.point_type == 1 else "points diplomatiques"
        emoji = ":blue_circle:" if self.point_type == 1 else ":purple_circle:"
        color = (
            self.p_points_color_int if self.point_type == 1 else self.d_points_color_int
        )

        templates = {
            "ADD_POINTS": (
                "{} Ajout de {}".format(alert, p_type),
                "{} **{{u1}}** s'est fait ajouter **{{amt}} {}** par **{{u2}}**.".format(
                    emoji, p_type
                ),
            ),
            "SET_POINTS": (
                "{} {} définis".format(alert, p_type.capitalize()),
                "{} **{{u1}}** s'est fait définir ses **{}** à **{{amt}}** par **{{u2}}**.".format(
                    emoji, p_type
                ),
            ),
            "USE_POINTS": (
                "Utilisation de {}".format(p_type),
                "{} **{{u1}}** a utilisé **{{amt}} {}**.".format(emoji, p_type),
            ),
            "REMOVE_POINTS": (
                "{} {} Retrait de {}".format(alert, alert, p_type),
                "{} **{{u1}}** s'est fait retirer **{{amt}} {}** par **{{u2}}**.".format(
                    emoji, p_type
                ),
            ),
            "POINTS_RESET": (
                "{} {} {} RESET des {}".format(alert, alert, alert, p_type),
                "{} **{{u1}}** a réinitialisé les {}.".format(emoji, p_type),
            ),
            "POINTS_RESET_ATTEMPT": (
                "{} {} {} {} TENTATIVE DE RESET".format(alert, alert, alert, alert),
                "{} **{{u1}}** a tenté de réinitialiser les {}.".format(emoji, p_type),
            ),
        }

        title, desc_template = templates.get(self.code, (None, None))
        if not title:
            return None

        desc = desc_template.format(
            u1=f"{self.user1.name} ({self.user1.id})",
            u2=f"{self.user2.name} ({self.user2.id})" if self.user2 else "❓",
            amt=self.amount,
        )

        return discord.Embed(title=title, description=desc, color=color)


async def eco_logger(
    code: str,
    amount: int,
    user1: discord.User,
    user2: discord.User = None,
    point_type: int = 1,
    extra_data: dict = None,
):
    """
    Unified economic event logger function.

    Args:
        code: Event code (TRANSFER, ADD_MONEY, USE_POINTS, etc.)
        amount: Amount involved in the transaction
        user1: Primary user (the one affected by the transaction)
        user2: Secondary user (the one performing the action, if different)
        point_type: Type of points for point transactions (1=political, 2=diplomatic)
        extra_data: Additional data to include in the log (dict)
    """
    try:
        # Get database and bot instances
        db_instance = get_db()
        if not db_instance:
            print("Error in eco_logger: Database instance not available")
            return

        # Get the eco log channel
        log_channel_id = db_instance.get_setting("eco_log_channel_id")
        if not log_channel_id:
            print("Error in eco_logger: No eco_log_channel_id setting found")
            return

        # We need to get the bot instance to get the channel
        # This will be set during bot initialization
        if not hasattr(eco_logger, "_bot_instance"):
            print("Error in eco_logger: Bot instance not set")
            return

        bot = eco_logger._bot_instance
        log_channel = bot.get_channel(int(log_channel_id))

        if not log_channel:
            print(f"Error in eco_logger: Channel {log_channel_id} not found")
            return

        # Create and send the log event
        event = EcoLogEvent(code, amount, user1, user2, point_type, extra_data)
        embed = event.get_embed()

        if embed:
            await log_channel.send(embed=embed)
        else:
            print(f"Error in eco_logger: Unknown code '{code}'")

    except Exception as e:
        print(f"Error in eco_logger: {e}")


def set_eco_logger_bot(bot):
    """Set the bot instance for the eco_logger function."""
    eco_logger._bot_instance = bot


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
    "power_plant_type_autocomplete",
    "infrastructure_type_autocomplete",
    "specialisation_autocomplete",
    "structure_autocomplete",
    "power_plant_autocomplete",
    "infrastructure_autocomplete",
    "factory_autocomplete",
    "technocentre_autocomplete",
    "region_autocomplete",
    "technology_autocomplete",
    "loan_years_autocomplete",
    "loan_reference_autocomplete",
    "EcoLogEvent",
    "eco_logger",
    "set_eco_logger_bot",
    "STRUCTURE_TYPES",
    "ALL_BUILDABLE_TYPES",
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
