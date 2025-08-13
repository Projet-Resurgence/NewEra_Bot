"""
Structures commands cog for NEBot.
Contains all structure-related commands (previously usines/batiments).
"""

import discord
from discord.ext import commands
from discord import app_commands
from typing import Union
import json

# Import centralized utilities
from shared_utils import (
    get_db,
    get_discord_utils,
    CountryEntity,
    CountryConverter,
    country_autocomplete,
    structure_type_autocomplete,
    power_plant_type_autocomplete,
    infrastructure_type_autocomplete,
    specialisation_autocomplete,
    structure_autocomplete,
    power_plant_autocomplete,
    infrastructure_autocomplete,
    region_autocomplete,
    technology_autocomplete,
    STRUCTURE_TYPES,
    ALL_BUILDABLE_TYPES,
    SPECIALISATIONS,
    convert,
    amount_converter,
    ERROR_COLOR_INT,
    MONEY_COLOR_INT,
    FACTORY_COLOR_INT,
)


class Structures(commands.Cog):
    """Structures management cog"""

    def __init__(self, bot):
        self.bot = bot
        self.db = get_db()
        self.dUtils = get_discord_utils(bot, self.db)

        # Color constants
        self.error_color_int = ERROR_COLOR_INT
        self.money_color_int = MONEY_COLOR_INT
        self.factory_color_int = FACTORY_COLOR_INT

    @commands.hybrid_command(
        name="construct_structure",
        brief="Construit un certain nombre de structures d'un niveau spécifié.",
        usage="construct_structure <type> <specialisation> <level> <amount> <region_id>",
        description="Construit plusieurs structures du niveau indiqué et débite le coût correspondant.",
        help="""Construit une ou plusieurs structures en fonction des paramètres indiqués, tout en vérifiant le solde de l'utilisateur.

        ARGUMENTS :
        - `<type>` : Type de structure ('Usine', 'Base', 'Ecole', 'Logement', 'Centrale', 'Technocentre').
        - `<specialisation>` : Spécialisation ('Terrestre', 'Aerienne', 'Navale', 'NA').
        - `<level>` : Niveau des structures à construire (1-7).
        - `<amount>` : Nombre de structures à construire (entier positif).
        - `<region_id>` : ID de la région où les structures seront construites.

        EXEMPLE :
        - `construct_structure Usine Terrestre 3 2 15` : Construit 2 usines terrestres de niveau 3 dans la région 15.
        """,
        case_insensitive=True,
    )
    @app_commands.choices(
        structure_type=[
            app_commands.Choice(name=struct_type, value=struct_type)
            for struct_type in STRUCTURE_TYPES
        ]
    )
    @app_commands.choices(
        specialisation=[
            app_commands.Choice(name=spec, value=spec) for spec in SPECIALISATIONS
        ]
    )
    @app_commands.autocomplete(region_id=region_autocomplete)
    async def construct_structure(
        self,
        ctx,
        structure_type: str = commands.parameter(
            description="Type de structure à construire."
        ),
        specialisation: str = commands.parameter(
            description="Spécialisation de la structure."
        ),
        level: int = commands.parameter(
            description="Niveau des structures à construire (1-7)."
        ),
        amount: int = commands.parameter(
            description="Nombre de structures à construire."
        ),
        region_id: int = commands.parameter(
            description="ID de la région où construire."
        ),
    ) -> None:
        country = CountryEntity(ctx.author, ctx.guild).to_dict()

        if not country or not country.get("id"):
            embed = discord.Embed(
                title="❌ Erreur",
                description="L'utilisateur ou le pays spécifié est invalide.",
                color=self.error_color_int,
            )
            await ctx.send(embed=embed)
            return

        # Validate structure type
        if structure_type not in STRUCTURE_TYPES:
            embed = discord.Embed(
                title="❌ Type invalide",
                description=f"Types valides: {', '.join(STRUCTURE_TYPES)}",
                color=self.error_color_int,
            )
            await ctx.send(embed=embed)
            return

        # Validate specialisation
        if specialisation not in SPECIALISATIONS:
            embed = discord.Embed(
                title="❌ Spécialisation invalide",
                description=f"Spécialisations valides: {', '.join(SPECIALISATIONS)}",
                color=self.error_color_int,
            )
            await ctx.send(embed=embed)
            return

        # Validate level
        if not (1 <= level <= 7):
            embed = discord.Embed(
                title="❌ Niveau invalide",
                description="Le niveau doit être entre 1 et 7.",
                color=self.error_color_int,
            )
            await ctx.send(embed=embed)
            return

        # Validate amount
        if amount <= 0:
            embed = discord.Embed(
                title="❌ Quantité invalide",
                description="La quantité doit être un nombre positif.",
                color=self.error_color_int,
            )
            await ctx.send(embed=embed)
            return

        # Check if region belongs to country
        # This check should be implemented in the database
        # For now, we'll assume the region ownership is valid

        # Calculate cost
        unit_cost = self.db.get_construction_cost(structure_type, level, specialisation)
        total_cost = unit_cost * amount

        if total_cost == 0:
            embed = discord.Embed(
                title="❌ Erreur de coût",
                description="Impossible de calculer le coût de construction.",
                color=self.error_color_int,
            )
            await ctx.send(embed=embed)
            return

        # Check balance
        if not self.db.has_enough_balance(country.get("id"), total_cost):
            balance = self.db.get_balance(country.get("id"))
            embed = discord.Embed(
                title="❌ Fonds insuffisants",
                description=f"Coût: {convert(str(total_cost))} | Solde: {convert(str(balance))}",
                color=self.error_color_int,
            )
            await ctx.send(embed=embed)
            return

        # Perform construction
        if self.db.construct_structure(
            country.get("id"),
            structure_type,
            specialisation,
            level,
            region_id,
            amount,
        ):
            self.db.take_balance(country.get("id"), total_cost)
            embed = discord.Embed(
                title="🏗️ Construction réussie",
                description=f"{amount} {structure_type}(s) {specialisation} niveau {level} construite(s) pour {convert(str(total_cost))}.",
                color=self.money_color_int,
            )
        else:
            embed = discord.Embed(
                title="❌ Erreur de construction",
                description="La construction a échoué. Vérifiez que la région vous appartient.",
                color=self.error_color_int,
            )

        await ctx.send(embed=embed)

    @commands.hybrid_command(
        name="sell_structure",
        brief="Vend une structure spécifique.",
        usage="sell_structure <structure_id>",
        description="Vend une structure par son ID et récupère de l'argent.",
        help="""Vend une structure appartenant à votre pays et récupère 50% de sa valeur de construction.

        FONCTIONNALITÉ :
        - Vend une structure spécifique par son ID
        - Récupère 50% du coût de construction original
        - Supprime définitivement la structure de votre inventaire
        - Libère l'espace dans la région

        RESTRICTIONS :
        - La structure doit vous appartenir
        - Vous devez connaître l'ID exact de la structure
        - Les structures en production pourraient être affectées

        ARGUMENTS :
        - `<structure_id>` : ID numérique de la structure à vendre

        EXEMPLE :
        - `sell_structure 1234` : Vend la structure avec l'ID 1234
        
        CONSEIL :
        - Utilisez `structure_info <id>` pour vérifier les détails avant la vente
        - Utilisez `structures` pour voir toutes vos structures et leurs IDs
        """,
        hidden=False,
        enabled=True,
        case_insensitive=True,
    )
    @app_commands.autocomplete(structure_id=structure_autocomplete)
    async def sell_structure(
        self,
        ctx,
        structure_id: int = commands.parameter(
            description="ID de la structure à vendre"
        ),
    ):
        country = CountryEntity(ctx.author, ctx.guild).to_dict()

        if not country or not country.get("id"):
            embed = discord.Embed(
                title="❌ Erreur",
                description="L'utilisateur ou le pays spécifié est invalide.",
                color=self.error_color_int,
            )
            await ctx.send(embed=embed)
            return

        # Check if structure belongs to the country
        structures = self.db.get_structures_by_country(country.get("id"))
        structure = next((s for s in structures if s[0] == structure_id), None)

        if not structure:
            embed = discord.Embed(
                title="❌ Structure introuvable",
                description="Cette structure n'existe pas ou ne vous appartient pas.",
                color=self.error_color_int,
            )
            await ctx.send(embed=embed)
            return

        structure_type, level = structure[1], structure[3]

        # Calculate sell price (usually 50% of construction cost)
        construction_cost = self.db.get_construction_cost(structure_type, level)
        sell_price = construction_cost // 2

        # Remove structure and give money
        if self.db.remove_structure(structure_id):
            self.db.give_balance(country.get("id"), sell_price)
            embed = discord.Embed(
                title="💰 Vente réussie",
                description=f"{structure_type} niveau {level} vendue pour {convert(str(sell_price))}.",
                color=self.money_color_int,
            )
        else:
            embed = discord.Embed(
                title="❌ Erreur de vente",
                description="La vente a échoué.",
                color=self.error_color_int,
            )

        await ctx.send(embed=embed)

    @commands.hybrid_command(
        name="sell_power_plant",
        brief="Vend une centrale électrique spécifique.",
        usage="sell_power_plant <plant_id>",
        description="Vend une centrale électrique par son ID et récupère de l'argent.",
        help="""Vend une centrale électrique appartenant à votre pays et récupère 50% de sa valeur de construction.

        FONCTIONNALITÉ :
        - Vend une centrale électrique spécifique par son ID
        - Récupère 50% du coût de construction original
        - Supprime définitivement la centrale de votre inventaire
        - Libère l'espace dans la région

        RESTRICTIONS :
        - La centrale doit vous appartenir
        - Vous devez connaître l'ID exact de la centrale

        ARGUMENTS :
        - `<plant_id>` : ID numérique de la centrale à vendre

        EXEMPLE :
        - `sell_power_plant 1234` : Vend la centrale avec l'ID 1234
        
        CONSEIL :
        - Utilisez `power_plants` pour voir toutes vos centrales et leurs IDs
        """,
        hidden=False,
        enabled=True,
        case_insensitive=True,
    )
    @app_commands.autocomplete(plant_id=power_plant_autocomplete)
    async def sell_power_plant(
        self,
        ctx,
        plant_id: int = commands.parameter(
            description="ID de la centrale électrique à vendre"
        ),
    ):
        country = CountryEntity(ctx.author, ctx.guild).to_dict()

        if not country or not country.get("id"):
            embed = discord.Embed(
                title="❌ Erreur",
                description="L'utilisateur ou le pays spécifié est invalide.",
                color=self.error_color_int,
            )
            await ctx.send(embed=embed)
            return

        # Check if power plant belongs to the country
        power_plants = self.db.get_power_plants_by_country(country.get("id"))
        plant = next((p for p in power_plants if p.get("id") == plant_id), None)

        if not plant:
            embed = discord.Embed(
                title="❌ Centrale introuvable",
                description="Cette centrale n'existe pas ou ne vous appartient pas.",
                color=self.error_color_int,
            )
            await ctx.send(embed=embed)
            return

        plant_type, level = plant["type"], plant["level"]

        # Calculate sell price (usually 50% of construction cost)
        construction_cost = self.db.get_power_plant_cost(plant_type, level)
        sell_price = construction_cost // 2

        # Remove power plant and give money
        if self.db.remove_power_plant(plant_id):
            self.db.give_balance(country.get("id"), sell_price)
            embed = discord.Embed(
                title="⚡ Vente réussie",
                description=f"Centrale {plant_type} niveau {level} vendue pour {convert(str(sell_price))}.",
                color=self.money_color_int,
            )
        else:
            embed = discord.Embed(
                title="❌ Erreur de vente",
                description="La vente a échoué.",
                color=self.error_color_int,
            )

        await ctx.send(embed=embed)

    @commands.hybrid_command(
        name="sell_infrastructure",
        brief="Vend une infrastructure spécifique.",
        usage="sell_infrastructure <infra_id>",
        description="Vend une infrastructure par son ID et récupère de l'argent.",
        help="""Vend une infrastructure appartenant à votre pays et récupère 50% de sa valeur de construction.

        FONCTIONNALITÉ :
        - Vend une infrastructure spécifique par son ID
        - Récupère 50% du coût de construction original
        - Supprime définitivement l'infrastructure de votre inventaire
        - Libère l'espace dans la région

        RESTRICTIONS :
        - L'infrastructure doit vous appartenir
        - Vous devez connaître l'ID exact de l'infrastructure

        ARGUMENTS :
        - `<infra_id>` : ID numérique de l'infrastructure à vendre

        EXEMPLE :
        - `sell_infrastructure 1234` : Vend l'infrastructure avec l'ID 1234
        
        CONSEIL :
        - Utilisez `infrastructures` pour voir toutes vos infrastructures et leurs IDs
        """,
        hidden=False,
        enabled=True,
        case_insensitive=True,
    )
    @app_commands.autocomplete(infra_id=infrastructure_autocomplete)
    async def sell_infrastructure(
        self,
        ctx,
        infra_id: int = commands.parameter(
            description="ID de l'infrastructure à vendre"
        ),
    ):
        country = CountryEntity(ctx.author, ctx.guild).to_dict()

        if not country or not country.get("id"):
            embed = discord.Embed(
                title="❌ Erreur",
                description="L'utilisateur ou le pays spécifié est invalide.",
                color=self.error_color_int,
            )
            await ctx.send(embed=embed)
            return

        # Check if infrastructure belongs to the country
        infrastructures = self.db.get_infrastructures_by_country(country.get("id"))
        infrastructure = next(
            (i for i in infrastructures if i.get("id") == infra_id), None
        )

        if not infrastructure:
            embed = discord.Embed(
                title="❌ Infrastructure introuvable",
                description="Cette infrastructure n'existe pas ou ne vous appartient pas.",
                color=self.error_color_int,
            )
            await ctx.send(embed=embed)
            return

        infra_type, length_km = infrastructure["type"], infrastructure["length_km"]

        # Calculate sell price (usually 50% of construction cost)
        cost_per_km = self.db.get_infrastructure_cost_per_km(infra_type)
        construction_cost = int(cost_per_km * length_km)
        sell_price = construction_cost // 2

        # Remove infrastructure and give money
        if self.db.remove_infrastructure(infra_id):
            self.db.give_balance(country.get("id"), sell_price)
            embed = discord.Embed(
                title="🛣️ Vente réussie",
                description=f"{infra_type} ({length_km}km) vendue pour {convert(str(sell_price))}.",
                color=self.money_color_int,
            )
        else:
            embed = discord.Embed(
                title="❌ Erreur de vente",
                description="La vente a échoué.",
                color=self.error_color_int,
            )

        await ctx.send(embed=embed)

    @commands.hybrid_command(
        name="structures",
        brief="Affiche les structures d'un utilisateur.",
        usage="structures [type] [user]",
        description="Affiche les structures d'un utilisateur par type.",
        help="""Affiche un résumé détaillé de toutes les structures ou d'un type spécifique.

        FONCTIONNALITÉ :
        - Affiche toutes les structures ou filtré par type
        - Groupe par type, spécialisation et niveau
        - Montre les quantités, capacités totales et régions
        - Permet de consulter les structures d'autres utilisateurs

        TYPES DE STRUCTURES :
        - `Usine` : Production industrielle
        - `Base` : Infrastructure militaire
        - `Ecole` : Formation et éducation
        - `Logement` : Capacité de population
        - `Centrale` : Production d'énergie
        - `Technocentre` : Recherche et développement

        ARGUMENTS :
        - `[type]` : Optionnel. Type de structure spécifique ou 'all' (par défaut)
        - `[user]` : Optionnel. Utilisateur dont voir les structures (vous par défaut)

        EXEMPLE :
        - `structures` : Affiche toutes vos structures
        - `structures Usine` : Affiche seulement vos usines
        - `structures all @utilisateur` : Affiche toutes les structures de l'utilisateur
        """,
        hidden=False,
        enabled=True,
        case_insensitive=True,
    )
    @app_commands.choices(
        structure_type=[
            app_commands.Choice(name=struct_type, value=struct_type)
            for struct_type in (STRUCTURE_TYPES + ["all"])
        ]
    )
    async def structures(
        self,
        ctx,
        structure_type: str = commands.parameter(
            default="all",
            description="Type de structure à afficher (Usine, Base, Ecole, Logement, Centrale, Technocentre, ou 'all')",
        ),
        country: CountryConverter = commands.parameter(
            default=None,
            description="Pays dont afficher les structures (optionnel, vous par défaut)",
        ),
    ):
        if country is None:
            country = CountryEntity(ctx.author, ctx.guild).to_dict()

        if not country or not country.get("id"):
            embed = discord.Embed(
                title="❌ Erreur",
                description="L'utilisateur spécifié n'a pas de pays.",
                color=self.error_color_int,
            )
            await ctx.send(embed=embed)
            return

        # Get structures
        if structure_type.lower() == "all":
            structures = self.db.get_structures_by_country(country.get("id"))
        else:
            valid_types = [
                "Usine",
                "Base",
                "Ecole",
                "Logement",
                "Centrale",
                "Technocentre",
            ]
            if structure_type not in valid_types:
                embed = discord.Embed(
                    title="❌ Type invalide",
                    description=f"Types valides: {', '.join(valid_types)} ou 'all'",
                    color=self.error_color_int,
                )
                await ctx.send(embed=embed)
                return
            structures = self.db.get_structures_by_country(
                country.get("id"), structure_type
            )

        if not structures:
            embed = discord.Embed(
                title="🏗️ Structures",
                description=f"{country.get('name')} n'a aucune structure.",
                color=self.factory_color_int,
            )
            await ctx.send(embed=embed)
            return

        # Group structures by type, specialisation, level
        structure_groups = {}
        for structure in structures:
            (
                struct_id,
                struct_type,
                specialisation,
                level,
                capacity,
                population,
                region_id,
                region_name,
            ) = structure
            key = f"{struct_type} {specialisation} Niv.{level}"

            if key not in structure_groups:
                structure_groups[key] = {
                    "count": 0,
                    "total_capacity": 0,
                    "total_population": 0,
                    "regions": set(),
                }

            structure_groups[key]["count"] += 1
            structure_groups[key]["total_capacity"] += capacity
            structure_groups[key]["total_population"] += population
            structure_groups[key]["regions"].add(region_name)

        # Create embed
        embed = discord.Embed(
            title=f"🏗️ Structures de {country.get('name')}",
            color=self.factory_color_int,
        )

        for struct_key, data in structure_groups.items():
            regions_text = (
                ", ".join(list(data["regions"]))[:50] + "..."
                if len(", ".join(data["regions"])) > 50
                else ", ".join(data["regions"])
            )

            value = f"**Quantité**: {data['count']}\n"
            value += f"**Capacité totale**: {data['total_capacity']}\n"
            value += f"**Population**: {data['total_population']}\n"
            value += f"**Régions**: {regions_text}"

            embed.add_field(name=struct_key, value=value, inline=False)

        if len(embed.fields) == 0:
            embed.description = "Aucune structure trouvée."

        await ctx.send(embed=embed)

    @commands.hybrid_command(
        name="structure_info",
        brief="Affiche les détails d'une structure spécifique.",
        usage="structure_info <structure_id>",
        description="Affiche les informations détaillées d'une structure incluant la capacité de production.",
        help="""Affiche les informations complètes d'une structure spécifique.

        FONCTIONNALITÉ :
        - Montre tous les détails de la structure (type, spécialisation, niveau)
        - Affiche l'emplacement (région) de la structure
        - Indique la capacité et la population actuelle
        - Pour les usines : détails des slots de production utilisés/disponibles

        INFORMATIONS AFFICHÉES :
        - Type et spécialisation de la structure
        - Niveau de la structure (1-7)
        - Région d'implantation
        - Capacité maximale et population actuelle
        - Slots de production (pour les usines uniquement)

        RESTRICTIONS :
        - La structure doit vous appartenir
        - Vous devez fournir l'ID exact de la structure

        ARGUMENTS :
        - `<structure_id>` : ID numérique de la structure à examiner

        EXEMPLE :
        - `structure_info 1234` : Affiche les détails de la structure ID 1234
        
        CONSEIL :
        - Utilisez `structures` pour obtenir les IDs de vos structures
        """,
        case_insensitive=True,
    )
    @app_commands.autocomplete(structure_id=structure_autocomplete)
    async def structure_info(
        self,
        ctx,
        structure_id: int = commands.parameter(
            description="ID de la structure dont afficher les informations"
        ),
    ):
        country = CountryEntity(ctx.author, ctx.guild).to_dict()

        if not country or not country.get("id"):
            embed = discord.Embed(
                title="❌ Erreur",
                description="L'utilisateur ou le pays spécifié est invalide.",
                color=self.error_color_int,
            )
            await ctx.send(embed=embed)
            return

        # Check if structure belongs to the country
        structures = self.db.get_structures_by_country(country.get("id"))
        structure = next((s for s in structures if s[0] == structure_id), None)

        if not structure:
            embed = discord.Embed(
                title="❌ Structure introuvable",
                description="Cette structure n'existe pas ou ne vous appartient pas.",
                color=self.error_color_int,
            )
            await ctx.send(embed=embed)
            return

        (
            struct_id,
            struct_type,
            specialisation,
            level,
            capacity,
            population,
            region_id,
            region_name,
        ) = structure

        # Get production slot information
        slot_info = self.db.get_structure_production_slots(structure_id)

        embed = discord.Embed(
            title=f"🏗️ {struct_type} #{struct_id}",
            color=self.factory_color_int,
        )

        embed.add_field(name="Type", value=struct_type, inline=True)
        embed.add_field(name="Spécialisation", value=specialisation, inline=True)
        embed.add_field(name="Niveau", value=level, inline=True)
        embed.add_field(
            name="Région", value=f"{region_name} (#{region_id})", inline=False
        )
        embed.add_field(name="Capacité", value=capacity, inline=True)
        embed.add_field(name="Population", value=population, inline=True)

        if struct_type == "Usine":
            embed.add_field(
                name="Slots de production",
                value=f"**Utilisés**: {slot_info['used_capacity']:.1f}\n**Disponibles**: {slot_info['remaining_capacity']:.1f}\n**Total**: {slot_info['effective_cost']}",
                inline=False,
            )

        await ctx.send(embed=embed)

    @commands.hybrid_command(
        name="add_structure",
        brief="Ajoute des structures à un pays (Staff seulement).",
        usage="add_structure <country> <type> <specialisation> <level> <amount> <region_id>",
        description="Ajoute des structures à l'inventaire d'un pays.",
        help="""Ajoute des structures à un pays sans frais de construction (commande staff).

        FONCTIONNALITÉ :
        - Ajoute instantanément des structures à un pays
        - Aucun coût de construction appliqué
        - Validations automatiques des paramètres
        - Enregistrement automatique dans la base de données

        TYPES DISPONIBLES :
        - `Usine` : Production industrielle
        - `Base` : Infrastructure militaire  
        - `Ecole` : Formation et éducation
        - `Logement` : Capacité de population
        - `Centrale` : Production d'énergie
        - `Technocentre` : Recherche et développement

        SPÉCIALISATIONS :
        - `Terrestre` : Opérations terrestres
        - `Aerienne` : Opérations aériennes
        - `Navale` : Opérations navales
        - `NA` : Non applicable / générique

        RESTRICTIONS :
        - Réservé aux membres du staff uniquement
        - Niveau doit être entre 1 et 7
        - Quantité doit être positive
        - La région doit exister

        ARGUMENTS :
        - `<country>` : Pays destinataire (mention, nom ou ID)
        - `<type>` : Type de structure
        - `<specialisation>` : Spécialisation de la structure
        - `<level>` : Niveau des structures (1-7)
        - `<amount>` : Nombre de structures à ajouter
        - `<region_id>` : ID de la région où placer les structures

        EXEMPLE :
        - `add_structure @France Usine Terrestre 5 3 42` : Ajoute 3 usines terrestres niveau 5 à la France dans la région 42
        """,
        hidden=False,
        enabled=True,
        case_insensitive=True,
    )
    @app_commands.autocomplete(target_country=country_autocomplete)
    @app_commands.choices(
        structure_type=[
            app_commands.Choice(name=struct_type, value=struct_type)
            for struct_type in STRUCTURE_TYPES
        ]
    )
    @app_commands.choices(
        specialisation=[
            app_commands.Choice(name=spec, value=spec) for spec in SPECIALISATIONS
        ]
    )
    @app_commands.autocomplete(region_id=region_autocomplete)
    async def add_structure(
        self,
        ctx,
        target_country: CountryConverter = commands.parameter(
            description="Pays destinataire des structures"
        ),
        structure_type: str = commands.parameter(
            description="Type de structure (Usine, Base, Ecole, Logement, Centrale, Technocentre)"
        ),
        specialisation: str = commands.parameter(
            description="Spécialisation (Terrestre, Aerienne, Navale, NA)"
        ),
        level: int = commands.parameter(description="Niveau des structures (1-7)"),
        amount: int = commands.parameter(description="Nombre de structures à ajouter"),
        region_id: int = commands.parameter(
            description="ID de la région où placer les structures"
        ),
    ):
        if not self.dUtils.is_authorized(ctx):
            embed = discord.Embed(
                title="❌ Non autorisé",
                description="Il vous faut être staff.",
                color=self.error_color_int,
            )
            await ctx.send(embed=embed)
            return

        if not target_country or not target_country.get("id"):
            embed = discord.Embed(
                title="❌ Erreur",
                description="Le pays spécifié est invalide.",
                color=self.error_color_int,
            )
            await ctx.send(embed=embed)
            return

        # Validate parameters (same validation as construct_structure)
        if structure_type not in STRUCTURE_TYPES:
            embed = discord.Embed(
                title="❌ Type invalide",
                description=f"Types valides: {', '.join(STRUCTURE_TYPES)}",
                color=self.error_color_int,
            )
            await ctx.send(embed=embed)
            return

        if specialisation not in SPECIALISATIONS:
            embed = discord.Embed(
                title="❌ Spécialisation invalide",
                description=f"Spécialisations valides: {', '.join(SPECIALISATIONS)}",
                color=self.error_color_int,
            )
            await ctx.send(embed=embed)
            return

        if not (1 <= level <= 7) or amount <= 0:
            embed = discord.Embed(
                title="❌ Paramètres invalides",
                description="Niveau: 1-7, Quantité: > 0",
                color=self.error_color_int,
            )
            await ctx.send(embed=embed)
            return

        # Add structures without cost
        if self.db.construct_structure(
            target_country.get("id"),
            structure_type,
            specialisation,
            level,
            region_id,
            amount,
        ):
            embed = discord.Embed(
                title="✅ Structures ajoutées",
                description=f"{amount} {structure_type}(s) {specialisation} niveau {level} ajoutée(s) à {target_country['name']}.",
                color=self.money_color_int,
            )
        else:
            embed = discord.Embed(
                title="❌ Erreur",
                description="L'ajout a échoué. Vérifiez les paramètres.",
                color=self.error_color_int,
            )

        await ctx.send(embed=embed)

    @commands.hybrid_command(
        name="remove_structure",
        brief="Retire une structure par son ID (Staff seulement).",
        usage="remove_structure <structure_id>",
        description="Retire une structure spécifique par son ID.",
        help="""Supprime définitivement une structure par son ID (commande staff).

        FONCTIONNALITÉ :
        - Supprime instantanément une structure du jeu
        - Suppression permanente et irréversible
        - Recherche automatique de la structure dans toutes les régions
        - Confirmation des détails avant suppression

        UTILISATION :
        - Correction d'erreurs de construction
        - Équilibrage du jeu
        - Maintenance administrative
        - Résolution de problèmes techniques

        RESTRICTIONS :
        - Réservé aux membres du staff uniquement
        - Suppression définitive (aucun remboursement)
        - L'ID doit correspondre à une structure existante

        ARGUMENTS :
        - `<structure_id>` : ID numérique de la structure à supprimer

        EXEMPLE :
        - `remove_structure 1234` : Supprime la structure avec l'ID 1234
        
        ATTENTION :
        - Cette action est irréversible
        - Vérifiez l'ID avant d'exécuter la commande
        - Les productions en cours peuvent être affectées
        """,
        hidden=False,
        enabled=True,
        case_insensitive=True,
    )
    @app_commands.autocomplete(structure_id=structure_autocomplete)
    async def remove_structure(
        self,
        ctx,
        structure_id: int = commands.parameter(
            description="ID de la structure à supprimer"
        ),
    ):
        if not self.dUtils.is_authorized(ctx):
            embed = discord.Embed(
                title="❌ Non autorisé",
                description="Il vous faut être staff.",
                color=self.error_color_int,
            )
            await ctx.send(embed=embed)
            return

        # Get structure info before removing
        try:
            structures = self.db.get_structures_by_country(
                None
            )  # Get all structures to find this one
            structure = None
            for s in structures:
                if s[0] == structure_id:
                    structure = s
                    break

            if not structure:
                embed = discord.Embed(
                    title="❌ Structure introuvable",
                    description=f"Aucune structure avec l'ID {structure_id}.",
                    color=self.error_color_int,
                )
                await ctx.send(embed=embed)
                return

            (
                struct_id,
                struct_type,
                specialisation,
                level,
                capacity,
                population,
                region_id,
                region_name,
            ) = structure

            if self.db.remove_structure(structure_id):
                embed = discord.Embed(
                    title="✅ Structure supprimée",
                    description=f"{struct_type} {specialisation} niveau {level} (ID: {structure_id}) supprimée de la région {region_name}.",
                    color=self.money_color_int,
                )
            else:
                embed = discord.Embed(
                    title="❌ Erreur de suppression",
                    description="La suppression a échoué.",
                    color=self.error_color_int,
                )
        except Exception as e:
            embed = discord.Embed(
                title="❌ Erreur",
                description=f"Erreur lors de la suppression: {str(e)}",
                color=self.error_color_int,
            )

        await ctx.send(embed=embed)

    @commands.hybrid_command(
        name="structure_costs",
        brief="Affiche les coûts de construction des structures.",
        usage="structure_costs [type]",
        description="Affiche les coûts de construction pour tous les types de structures ou un type spécifique.",
        help="""Affiche un tableau détaillé des coûts de construction pour les structures.

        FONCTIONNALITÉ :
        - Affiche les coûts par niveau pour chaque type de structure
        - Permet de consulter tous les types ou un type spécifique
        - Aide à planifier les budgets de construction
        - Référence complète des prix du jeu

        INFORMATIONS AFFICHÉES :
        - Coût par niveau (1-7) pour chaque type
        - Progression des prix selon le niveau
        - Formatage monétaire pour faciliter la lecture

        TYPES DISPONIBLES :
        - `Usine` : Structures de production industrielle
        - `Base` : Infrastructure militaire
        - `Ecole` : Établissements d'éducation
        - `Logement` : Structures résidentielles
        - `Centrale` : Centrales électriques
        - `Technocentre` : Centres de recherche

        ARGUMENTS :
        - `[type]` : Optionnel. Type spécifique ou 'all' pour tous les types

        EXEMPLE :
        - `structure_costs` : Affiche tous les coûts de construction
        - `structure_costs Usine` : Affiche uniquement les coûts des usines
        - `structure_costs Base` : Affiche uniquement les coûts des bases
        """,
        case_insensitive=True,
    )
    @app_commands.choices(
        structure_type=[
            app_commands.Choice(name=struct_type, value=struct_type)
            for struct_type in STRUCTURE_TYPES + ["all"]
        ]
    )
    async def structure_costs(
        self,
        ctx,
        structure_type: str = commands.parameter(
            default="all",
            description="Type de structure dont afficher les coûts (ou 'all' pour tous)",
        ),
    ):
        valid_types = ["Usine", "Base", "Ecole", "Logement", "Centrale", "Technocentre"]

        if structure_type != "all" and structure_type not in valid_types:
            embed = discord.Embed(
                title="❌ Type invalide",
                description=f"Types valides: {', '.join(valid_types)} ou 'all'",
                color=self.error_color_int,
            )
            await ctx.send(embed=embed)
            return

        embed = discord.Embed(
            title="💰 Coûts de construction",
            color=self.money_color_int,
        )

        types_to_show = [structure_type] if structure_type != "all" else valid_types

        for struct_type in types_to_show:
            cost_info = ""
            for level in range(1, 8):  # Levels 1-7
                cost = self.db.get_construction_cost(struct_type, level)
                if cost > 0:
                    cost_info += f"**Niveau {level}**: {convert(str(cost))}\n"

            if cost_info:
                embed.add_field(name=struct_type, value=cost_info, inline=True)

        if len(embed.fields) == 0:
            embed.description = "Aucun coût de construction disponible."

        await ctx.send(embed=embed)

    @commands.hybrid_command(
        name="construct_power_plant",
        brief="Construit une centrale électrique.",
        usage="construct_power_plant <plant_type> <level> <region_id>",
        description="Construit une centrale électrique du type et niveau spécifiés.",
        help="""Construit une centrale électrique dans une région spécifiée.

        ARGUMENTS :
        - `<plant_type>` : Type de centrale ('éolien onshore', 'éolien offshore', 'Solaire', 'Nucléaire', etc.).
        - `<level>` : Niveau de la centrale à construire.
        - `<region_id>` : ID de la région où la centrale sera construite.

        EXEMPLE :
        - `construct_power_plant Solaire 3 15` : Construit une centrale solaire de niveau 3 dans la région 15.
        """,
        case_insensitive=True,
    )
    @app_commands.autocomplete(plant_type=power_plant_type_autocomplete)
    @app_commands.autocomplete(region_id=region_autocomplete)
    async def construct_power_plant(
        self,
        ctx,
        plant_type: str = commands.parameter(
            description="Type de centrale électrique à construire."
        ),
        level: int = commands.parameter(
            description="Niveau de la centrale à construire."
        ),
        amount: int = commands.parameter(
            description="Nombre de centrales à construire."
        ),
        region_id: int = commands.parameter(
            description="ID de la région où construire."
        ),
    ):
        country = CountryEntity(ctx.author, ctx.guild).to_dict()

        if not country or not country.get("id"):
            embed = discord.Embed(
                title="❌ Erreur",
                description="L'utilisateur ou le pays spécifié est invalide.",
                color=self.error_color_int,
            )
            await ctx.send(embed=embed)
            return

        # Validate plant type by checking available types from database
        available_types = self.db.get_available_power_plant_types()
        if plant_type not in available_types:
            embed = discord.Embed(
                title="❌ Type invalide",
                description=f"Types valides: {', '.join(available_types)}",
                color=self.error_color_int,
            )
            await ctx.send(embed=embed)
            return

        # Calculate cost
        base_cost = self.db.get_power_plant_cost(plant_type, level)
        cost = base_cost * amount

        if cost == 0:
            # Check if this power plant type exists and what levels are available
            available_levels = self.db.get_power_plant_available_levels(plant_type)
            if available_levels["min_level"] is None:
                embed = discord.Embed(
                    title="❌ Type de centrale invalide",
                    description=f"Le type de centrale '{plant_type}' n'existe pas.",
                    color=self.error_color_int,
                )
            else:
                embed = discord.Embed(
                    title="❌ Niveau non disponible",
                    description=f"Le niveau {level} n'est pas disponible pour {plant_type}.\nNiveaux disponibles: {available_levels['min_level']} - {available_levels['max_level']}",
                    color=self.error_color_int,
                )
            await ctx.send(embed=embed)
            return

        # Check balance
        if not self.db.has_enough_balance(country.get("id"), cost):
            balance = self.db.get_balance(country.get("id"))
            embed = discord.Embed(
                title="❌ Fonds insuffisants",
                description=f"Coût: {convert(str(cost))} | Solde: {convert(str(balance))}",
                color=self.error_color_int,
            )
            await ctx.send(embed=embed)
            return

        # Perform construction
        if self.db.construct_power_plant(
            country.get("id"), plant_type, amount, level, region_id
        ):
            embed = discord.Embed(
                title="⚡ Centrale construite",
                description=f"{amount} centrale(s) {plant_type} niveau {level} construite(s) pour {convert(str(cost))}.",
                color=self.money_color_int,
            )
        else:
            embed = discord.Embed(
                title="❌ Erreur de construction",
                description="La construction a échoué. Vérifiez que la région vous appartient.",
                color=self.error_color_int,
            )

        await ctx.send(embed=embed)

    @commands.hybrid_command(
        name="construct_infrastructure",
        brief="Construit une infrastructure.",
        usage="construct_infrastructure <infra_type> <length_km> <region_id>",
        description="Construit une infrastructure du type spécifié sur une longueur donnée.",
        help="""Construit une infrastructure dans une région spécifiée.

        ARGUMENTS :
        - `<infra_type>` : Type d'infrastructure ('Route', 'Autoroute', 'Chemin de fer', etc.).
        - `<length_km>` : Longueur en kilomètres à construire.
        - `<region_id>` : ID de la région où l'infrastructure sera construite.

        EXEMPLE :
        - `construct_infrastructure Route 25.5 15` : Construit 25,5 km de route dans la région 15.
        """,
        case_insensitive=True,
    )
    @app_commands.autocomplete(infra_type=infrastructure_type_autocomplete)
    @app_commands.autocomplete(region_id=region_autocomplete)
    async def construct_infrastructure(
        self,
        ctx,
        infra_type: str = commands.parameter(
            description="Type d'infrastructure à construire."
        ),
        length_km: float = commands.parameter(
            description="Longueur en kilomètres à construire."
        ),
        region_id: int = commands.parameter(
            description="ID de la région où construire."
        ),
    ):
        country = CountryEntity(ctx.author, ctx.guild).to_dict()

        if not country or not country.get("id"):
            embed = discord.Embed(
                title="❌ Erreur",
                description="L'utilisateur ou le pays spécifié est invalide.",
                color=self.error_color_int,
            )
            await ctx.send(embed=embed)
            return

        # Validate infrastructure type by checking available types from database
        available_types = self.db.get_available_infrastructure_types()
        if infra_type not in available_types:
            embed = discord.Embed(
                title="❌ Type invalide",
                description=f"Types valides: {', '.join(available_types)}",
                color=self.error_color_int,
            )
            await ctx.send(embed=embed)
            return

        # Validate length
        if length_km <= 0:
            embed = discord.Embed(
                title="❌ Longueur invalide",
                description="La longueur doit être positive.",
                color=self.error_color_int,
            )
            await ctx.send(embed=embed)
            return

        # Calculate cost
        cost_per_km = self.db.get_infrastructure_cost_per_km(infra_type)
        total_cost = int(cost_per_km * length_km)

        if cost_per_km == 0:
            embed = discord.Embed(
                title="❌ Erreur de coût",
                description="Type d'infrastructure invalide.",
                color=self.error_color_int,
            )
            await ctx.send(embed=embed)
            return

        # Check balance
        if not self.db.has_enough_balance(country.get("id"), total_cost):
            balance = self.db.get_balance(country.get("id"))
            embed = discord.Embed(
                title="❌ Fonds insuffisants",
                description=f"Coût: {convert(str(total_cost))} | Solde: {convert(str(balance))}",
                color=self.error_color_int,
            )
            await ctx.send(embed=embed)
            return

        # Perform construction
        if self.db.construct_infrastructure(
            country.get("id"), infra_type, length_km, region_id
        ):
            embed = discord.Embed(
                title="🛣️ Infrastructure construite",
                description=f"{length_km}km de {infra_type} construits pour {convert(str(total_cost))}.",
                color=self.money_color_int,
            )
        else:
            embed = discord.Embed(
                title="❌ Erreur de construction",
                description="La construction a échoué. Vérifiez que la région vous appartient.",
                color=self.error_color_int,
            )

        await ctx.send(embed=embed)

    @commands.hybrid_command(
        name="power_plants",
        brief="Liste toutes les centrales électriques du pays.",
        usage="power_plants [country]",
        description="Affiche la liste des centrales électriques appartenant au pays.",
        help="""Affiche toutes les centrales électriques d'un pays avec leurs détails.

        FONCTIONNALITÉ :
        - Liste toutes les centrales par région
        - Affiche le type, niveau, production et danger
        - Calcule la production totale d'énergie
        - Montre l'efficacité énergétique globale

        ARGUMENTS :
        - `[country]` : Pays ciblé (optionnel, par défaut votre pays)

        EXEMPLE :
        - `power_plants` : Vos centrales électriques
        - `power_plants @France` : Centrales de la France
        """,
        hidden=False,
        enabled=True,
        case_insensitive=True,
    )
    @app_commands.autocomplete(country=country_autocomplete)
    async def power_plants(
        self,
        ctx,
        country: CountryConverter = None,
    ):
        if country is None:
            country = CountryEntity(ctx.author, ctx.guild).to_dict()

        if not country or not country.get("id"):
            embed = discord.Embed(
                title="❌ Erreur",
                description="L'utilisateur ou le pays spécifié est invalide.",
                color=self.error_color_int,
            )
            await ctx.send(embed=embed)
            return

        power_plants = self.db.get_power_plants_by_country(country.get("id"))

        embed = discord.Embed(
            title=f"⚡ Centrales électriques - {country.get('name')}",
            color=self.factory_color_int,
        )

        if not power_plants:
            embed.description = "Aucune centrale électrique trouvée."
        else:
            total_production = 0
            current_region = None
            region_text = ""

            for plant in power_plants:
                if current_region != plant["region_name"]:
                    if region_text:
                        embed.add_field(
                            name=f"🌍 {current_region}", value=region_text, inline=False
                        )
                    current_region = plant["region_name"]
                    region_text = ""

                total_production += plant["production_mwh"]
                danger_text = (
                    f" ⚠️ {plant['danger_rate']}%" if plant["danger_rate"] > 0 else ""
                )
                region_text += f"• {plant['type']} Niv.{plant['level']} - {plant['production_mwh']:,} MW/h{danger_text}\n"

            # Add the last region
            if region_text:
                embed.add_field(
                    name=f"🌍 {current_region}", value=region_text, inline=False
                )

            embed.add_field(
                name="📊 Production totale",
                value=f"{total_production:,} MW/h",
                inline=True,
            )
            embed.add_field(
                name="🏭 Nombre de centrales", value=str(len(power_plants)), inline=True
            )

        await ctx.send(embed=embed)

    @commands.hybrid_command(
        name="infrastructures",
        brief="Liste toutes les infrastructures du pays.",
        usage="infrastructures [country]",
        description="Affiche la liste des infrastructures appartenant au pays.",
        help="""Affiche toutes les infrastructures d'un pays avec leurs détails.

        FONCTIONNALITÉ :
        - Liste toutes les infrastructures par région
        - Affiche le type, longueur et coût total
        - Calcule la longueur totale par type
        - Montre l'investissement total en infrastructures

        ARGUMENTS :
        - `[country]` : Pays ciblé (optionnel, par défaut votre pays)

        EXEMPLE :
        - `infrastructures` : Vos infrastructures
        - `infrastructures @France` : Infrastructures de la France
        """,
        hidden=False,
        enabled=True,
        case_insensitive=True,
    )
    @app_commands.autocomplete(country=country_autocomplete)
    async def infrastructures(
        self,
        ctx,
        country: CountryConverter = None,
    ):
        if country is None:
            country = CountryEntity(ctx.author, ctx.guild).to_dict()

        if not country or not country.get("id"):
            embed = discord.Embed(
                title="❌ Erreur",
                description="L'utilisateur ou le pays spécifié est invalide.",
                color=self.error_color_int,
            )
            await ctx.send(embed=embed)
            return

        infrastructures = self.db.get_infrastructures_by_country(country.get("id"))

        embed = discord.Embed(
            title=f"🛣️ Infrastructures - {country.get('name')}",
            color=self.factory_color_int,
        )

        if not infrastructures:
            embed.description = "Aucune infrastructure trouvée."
        else:
            total_cost = 0
            total_length = 0
            current_region = None
            region_text = ""

            for infra in infrastructures:
                if current_region != infra["region_name"]:
                    if region_text:
                        embed.add_field(
                            name=f"🌍 {current_region}", value=region_text, inline=False
                        )
                    current_region = infra["region_name"]
                    region_text = ""

                total_cost += infra["total_cost"]
                total_length += infra["length_km"]
                region_text += f"• {infra['type']} - {infra['length_km']}km ({convert(str(infra['total_cost']))})\n"

            # Add the last region
            if region_text:
                embed.add_field(
                    name=f"🌍 {current_region}", value=region_text, inline=False
                )

            embed.add_field(
                name="📏 Longueur totale", value=f"{total_length:,.1f} km", inline=True
            )
            embed.add_field(
                name="💰 Coût total", value=convert(str(total_cost)), inline=True
            )

        await ctx.send(embed=embed)

    @commands.hybrid_command(
        name="remove_power_plant",
        brief="Supprime une centrale électrique.",
        usage="remove_power_plant <plant_id>",
        description="Supprime une centrale électrique par son ID.",
        help="""Supprime définitivement une centrale électrique.

        ARGUMENTS :
        - `<plant_id>` : ID de la centrale à supprimer

        EXEMPLE :
        - `remove_power_plant 123` : Supprime la centrale avec l'ID 123
        """,
        case_insensitive=True,
    )
    async def remove_power_plant(
        self,
        ctx,
        plant_id: int = commands.parameter(description="ID de la centrale à supprimer"),
    ):
        country = CountryEntity(ctx.author, ctx.guild).to_dict()

        if not country or not country.get("id"):
            embed = discord.Embed(
                title="❌ Erreur",
                description="L'utilisateur ou le pays spécifié est invalide.",
                color=self.error_color_int,
            )
            await ctx.send(embed=embed)
            return

        if self.db.remove_power_plant(plant_id):
            embed = discord.Embed(
                title="⚡ Centrale supprimée",
                description=f"La centrale électrique ID {plant_id} a été supprimée.",
                color=self.factory_color_int,
            )
        else:
            embed = discord.Embed(
                title="❌ Erreur",
                description="Impossible de supprimer la centrale. Vérifiez l'ID et que la centrale vous appartient.",
                color=self.error_color_int,
            )

        await ctx.send(embed=embed)

    @commands.hybrid_command(
        name="remove_infrastructure",
        brief="Supprime une infrastructure.",
        usage="remove_infrastructure <infra_id>",
        description="Supprime une infrastructure par son ID.",
        help="""Supprime définitivement une infrastructure.

        ARGUMENTS :
        - `<infra_id>` : ID de l'infrastructure à supprimer

        EXEMPLE :
        - `remove_infrastructure 456` : Supprime l'infrastructure avec l'ID 456
        """,
        case_insensitive=True,
    )
    async def remove_infrastructure(
        self,
        ctx,
        infra_id: int = commands.parameter(
            description="ID de l'infrastructure à supprimer"
        ),
    ):
        country = CountryEntity(ctx.author, ctx.guild).to_dict()

        if not country or not country.get("id"):
            embed = discord.Embed(
                title="❌ Erreur",
                description="L'utilisateur ou le pays spécifié est invalide.",
                color=self.error_color_int,
            )
            await ctx.send(embed=embed)
            return

        if self.db.remove_infrastructure(infra_id):
            embed = discord.Embed(
                title="🛣️ Infrastructure supprimée",
                description=f"L'infrastructure ID {infra_id} a été supprimée.",
                color=self.factory_color_int,
            )
        else:
            embed = discord.Embed(
                title="❌ Erreur",
                description="Impossible de supprimer l'infrastructure. Vérifiez l'ID et que l'infrastructure vous appartient.",
                color=self.error_color_int,
            )

        await ctx.send(embed=embed)

    @commands.hybrid_command(
        name="power_plant_info",
        brief="Affiche les informations sur les types de centrales électriques.",
        usage="power_plant_info [plant_type]",
        description="Affiche les types de centrales disponibles et leurs niveaux.",
        help="""Affiche des informations sur les centrales électriques disponibles.

        ARGUMENTS :
        - `[plant_type]` : Optionnel. Type spécifique de centrale à consulter.

        FONCTIONNALITÉ :
        - Sans argument : affiche tous les types disponibles avec leurs niveaux
        - Avec argument : affiche les détails d'un type spécifique
        - Montre les niveaux minimum et maximum disponibles
        - Indique les coûts par niveau

        EXEMPLE :
        - `power_plant_info` : Affiche tous les types de centrales
        - `power_plant_info éolien onshore` : Affiche les détails des éoliennes onshore
        """,
        case_insensitive=True,
    )
    @app_commands.autocomplete(plant_type=power_plant_type_autocomplete)
    async def power_plant_info(
        self,
        ctx,
        plant_type: str = commands.parameter(
            description="Type de centrale à consulter (optionnel).", default=None
        ),
    ):
        if plant_type:
            # Show specific power plant type info
            available_levels = self.db.get_power_plant_available_levels(plant_type)
            if available_levels["min_level"] is None:
                embed = discord.Embed(
                    title="❌ Type inconnu",
                    description=f"Le type de centrale '{plant_type}' n'existe pas.",
                    color=self.error_color_int,
                )
            else:
                embed = discord.Embed(
                    title=f"⚡ {plant_type}",
                    description=f"Niveaux disponibles: {available_levels['min_level']} - {available_levels['max_level']}",
                    color=self.factory_color_int,
                )

                # Get costs for first few levels
                for level in range(
                    available_levels["min_level"],
                    min(
                        available_levels["min_level"] + 5,
                        available_levels["max_level"] + 1,
                    ),
                ):
                    cost = self.db.get_power_plant_cost(plant_type, level)
                    if cost > 0:
                        embed.add_field(
                            name=f"Niveau {level}",
                            value=convert(str(cost)),
                            inline=True,
                        )
        else:
            # Show all power plant types
            try:
                cursor = self.db.cur
                cursor.execute(
                    """
                    SELECT type, MIN(level) as min_level, MAX(level) as max_level 
                    FROM PowerPlantsDatas 
                    WHERE construction_cost > 0 
                    GROUP BY type 
                    ORDER BY type
                """
                )
                power_plants = cursor.fetchall()

                embed = discord.Embed(
                    title="⚡ Types de centrales électriques",
                    description=f"{len(power_plants)} types de centrales disponibles",
                    color=self.factory_color_int,
                )

                for plant_type, min_level, max_level in power_plants:
                    embed.add_field(
                        name=plant_type,
                        value=f"Niveaux {min_level}-{max_level}",
                        inline=True,
                    )

            except Exception as e:
                embed = discord.Embed(
                    title="❌ Erreur",
                    description="Impossible de récupérer les informations sur les centrales.",
                    color=self.error_color_int,
                )

        await ctx.send(embed=embed)

    @commands.hybrid_command(
        name="check_infrastructure",
        brief="Affiche toutes les infrastructures du pays.",
        usage="check_infrastructure",
        description="Affiche un récapitulatif de toutes les infrastructures construites par le pays.",
        help="""Affiche toutes les infrastructures de votre pays avec leurs détails.

        FONCTIONNALITÉ :
        - Liste toutes les infrastructures par région
        - Affiche le type et la longueur de chaque infrastructure
        - Montre le coût total investi
        - Calcule les statistiques globales

        INFORMATIONS AFFICHÉES :
        - Type d'infrastructure (Route, Autoroute, etc.)
        - Longueur en kilomètres
        - Coût total de construction
        - Région de construction

        EXEMPLE :
        - `check_infrastructure` : Affiche toutes vos infrastructures
        """,
        case_insensitive=True,
    )
    async def check_infrastructure(self, ctx):
        """Affiche toutes les infrastructures du pays."""
        try:
            country_entity = CountryEntity(ctx.author, ctx.guild)
            country_id = country_entity.get_country_id()

            if not country_id:
                embed = discord.Embed(
                    title="❌ Erreur",
                    description="Vous n'êtes membre d'aucun pays.",
                    color=self.error_color_int,
                )
                return await ctx.send(embed=embed)

            infrastructures = self.db.get_infrastructures_by_country(country_id)
            country_name = country_entity.to_dict()["name"]

            if not infrastructures:
                embed = discord.Embed(
                    title="🛣️ Infrastructures",
                    description=f"**{country_name}** ne possède aucune infrastructure.",
                    color=self.factory_color_int,
                )
                return await ctx.send(embed=embed)

            # Group by type and calculate totals
            infra_by_type = {}
            total_cost = 0
            total_length = 0

            for infra in infrastructures:
                infra_type = infra.get("type", "Inconnu")
                length = infra.get("length_km", 0)
                cost = infra.get("total_cost", 0)
                region_name = infra.get(
                    "region_name", f"Région {infra.get('region_id', 'N/A')}"
                )

                if infra_type not in infra_by_type:
                    infra_by_type[infra_type] = {
                        "count": 0,
                        "total_length": 0,
                        "total_cost": 0,
                        "regions": [],
                    }

                infra_by_type[infra_type]["count"] += 1
                infra_by_type[infra_type]["total_length"] += length
                infra_by_type[infra_type]["total_cost"] += cost
                infra_by_type[infra_type]["regions"].append(
                    f"{region_name} ({length}km)"
                )

                total_cost += cost
                total_length += length

            embed = discord.Embed(
                title="🛣️ Infrastructures du pays",
                description=f"**{country_name}**",
                color=self.factory_color_int,
            )

            # Add summary
            embed.add_field(
                name="📊 Résumé global",
                value=f"**Total longueur:** {total_length:,.1f} km\n"
                f"**Coût total investi:** {convert(total_cost)}\n"
                f"**Nombre de projets:** {len(infrastructures)}",
                inline=False,
            )

            # Add details by type
            for infra_type, data in infra_by_type.items():
                regions_text = "\n".join(data["regions"][:5])  # Show first 5 regions
                if len(data["regions"]) > 5:
                    regions_text += f"\n... et {len(data['regions']) - 5} autres"

                embed.add_field(
                    name=f"🛤️ {infra_type}",
                    value=f"**Nombre:** {data['count']}\n"
                    f"**Longueur totale:** {data['total_length']:,.1f} km\n"
                    f"**Coût total:** {convert(data['total_cost'])}\n"
                    f"**Régions:**\n{regions_text}",
                    inline=True,
                )

        except Exception as e:
            embed = discord.Embed(
                title="❌ Erreur",
                description="Impossible de récupérer les informations sur les infrastructures.",
                color=self.error_color_int,
            )

        await ctx.send(embed=embed)

    @commands.hybrid_command(
        name="check_electricity",
        brief="Affiche la production électrique du pays.",
        usage="check_electricity",
        description="Affiche un récapitulatif de toute la production électrique du pays.",
        help="""Affiche toutes les informations sur la production électrique de votre pays.

        FONCTIONNALITÉ :
        - Liste toutes les centrales électriques par type
        - Calcule la production totale en MWh
        - Affiche les coûts d'exploitation
        - Montre la répartition par source d'énergie

        INFORMATIONS AFFICHÉES :
        - Type de centrale (Nucléaire, Thermique, etc.)
        - Niveau et production MWh
        - Coût de construction et d'exploitation
        - Taux de danger et consommation de ressources
        - Région d'implantation

        CALCULS :
        - Production totale en MWh
        - Coût moyen par MWh
        - Répartition des sources d'énergie
        - Investissement total

        EXEMPLE :
        - `check_electricity` : Affiche votre production électrique
        """,
        case_insensitive=True,
    )
    @app_commands.autocomplete(country=country_autocomplete)
    async def check_electricity(self, ctx, country: CountryConverter = None):
        """Affiche la production électrique du pays."""
        try:
            if not country:
                country_entity = CountryEntity(ctx.author, ctx.guild)
                country_id = country_entity.get_country_id()
                country_name = country_entity.to_dict()["name"]
            else:
                # country is already a CountryConverter (dict)
                country_name = country.get("name", "Pays inconnu")
                country_id = country.get("id")

            if not country_id:
                embed = discord.Embed(
                    title="❌ Erreur",
                    description="Vous n'êtes membre d'aucun pays.",
                    color=self.error_color_int,
                )
                return await ctx.send(embed=embed)

            power_plants = self.db.get_power_plants_by_country(country_id)

            if not power_plants:
                embed = discord.Embed(
                    title="⚡ Production électrique",
                    description=f"**{country_name}** ne possède aucune centrale électrique.",
                    color=self.factory_color_int,
                )
                return await ctx.send(embed=embed)

            # Group by type and calculate totals
            plants_by_type = {}
            total_production = 0
            total_cost = 0
            total_danger = 0
            total_resource_consumption = 0

            for plant in power_plants:
                plant_type = plant.get("type", "Inconnu")
                production = plant.get("production_mwh", 0)
                cost = plant.get("construction_cost", 0)
                danger = plant.get("danger_rate", 0)
                resource_consumption = plant.get("resource_consumption", 0)
                level = plant.get("level", 1)
                region_name = plant.get(
                    "region_name", f"Région {plant.get('region_id', 'N/A')}"
                )

                if plant_type not in plants_by_type:
                    plants_by_type[plant_type] = {
                        "count": 0,
                        "total_production": 0,
                        "total_cost": 0,
                        "avg_danger": 0,
                        "total_resource_consumption": 0,
                        "plants": [],
                    }

                plants_by_type[plant_type]["count"] += 1
                plants_by_type[plant_type]["total_production"] += production
                plants_by_type[plant_type]["total_cost"] += cost
                plants_by_type[plant_type]["avg_danger"] += danger
                plants_by_type[plant_type][
                    "total_resource_consumption"
                ] += resource_consumption
                plants_by_type[plant_type]["plants"].append(
                    f"{region_name} (Niv.{level}, {production} MWh)"
                )

                total_production += production
                total_cost += cost
                total_danger += danger
                total_resource_consumption += resource_consumption

            # Calculate averages
            for plant_type in plants_by_type:
                if plants_by_type[plant_type]["count"] > 0:
                    plants_by_type[plant_type]["avg_danger"] /= plants_by_type[
                        plant_type
                    ]["count"]

            embed = discord.Embed(
                title="⚡ Production électrique du pays",
                description=f"**{country_name}**",
                color=self.factory_color_int,
            )

            # Add summary
            avg_cost_per_mwh = (
                (total_cost / total_production) if total_production > 0 else 0
            )
            avg_danger = (total_danger / len(power_plants)) if power_plants else 0

            embed.add_field(
                name="📊 Résumé global",
                value=f"**Production totale:** {total_production:,} MWh\n"
                f"**Coût total investi:** {convert(total_cost)}\n"
                f"**Coût moyen par MWh:** {avg_cost_per_mwh:,.2f}\n"
                f"**Nombre de centrales:** {len(power_plants)}\n"
                f"**Danger moyen:** {avg_danger:.2f}%\n"
                f"**Consommation ressources:** {total_resource_consumption:,.2f}",
                inline=False,
            )

            # Add details by type
            for plant_type, data in plants_by_type.items():
                plants_text = "\n".join(data["plants"][:3])  # Show first 3 plants
                if len(data["plants"]) > 3:
                    plants_text += f"\n... et {len(data['plants']) - 3} autres"

                percentage = (
                    (data["total_production"] / total_production * 100)
                    if total_production > 0
                    else 0
                )

                embed.add_field(
                    name=f"🔌 {plant_type}",
                    value=f"**Nombre:** {data['count']}\n"
                    f"**Production:** {data['total_production']:,} MWh ({percentage:.1f}%)\n"
                    f"**Coût total:** {convert(data['total_cost'])}\n"
                    f"**Danger moyen:** {data['avg_danger']:.2f}%\n"
                    f"**Centrales:**\n{plants_text}",
                    inline=True,
                )

        except Exception as e:
            embed = discord.Embed(
                title="❌ Erreur",
                description="Impossible de récupérer les informations sur la production électrique.",
                color=self.error_color_int,
            )
            print("Erreur lors de la récupération des informations sur la production électrique :", e, flush=True)

        await ctx.send(embed=embed)

    @commands.hybrid_command(
        name="check_all_structures",
        brief="Affiche toutes les structures, infrastructures et centrales du pays.",
        usage="check_all_structures",
        description="Affiche un récapitulatif complet de toutes les constructions du pays.",
        help="""Affiche un aperçu complet de toutes les constructions de votre pays.

        FONCTIONNALITÉ :
        - Résumé de toutes les structures (usines, bases, etc.)
        - Récapitulatif des infrastructures de transport
        - Vue d'ensemble de la production électrique
        - Statistiques globales et coûts totaux

        INFORMATIONS AFFICHÉES :
        - Nombre total de structures par type
        - Longueur totale d'infrastructures
        - Production électrique totale
        - Investissement total en construction
        - Répartition par région

        CALCULS :
        - Capacité de production totale
        - Capacité de logement disponible
        - Coût total investi
        - Efficacité énergétique

        EXEMPLE :
        - `check_all_structures` : Affiche toutes vos constructions
        """,
        case_insensitive=True,
    )
    async def check_all_structures(self, ctx):
        """Affiche toutes les structures, infrastructures et centrales du pays."""
        try:
            country_entity = CountryEntity(ctx.author, ctx.guild)
            country_id = country_entity.get_country_id()

            if not country_id:
                embed = discord.Embed(
                    title="❌ Erreur",
                    description="Vous n'êtes membre d'aucun pays.",
                    color=self.error_color_int,
                )
                return await ctx.send(embed=embed)

            # Get all data
            structures = self.db.get_structures_by_country(country_id)
            infrastructures = self.db.get_infrastructures_by_country(country_id)
            power_plants = self.db.get_power_plants_by_country(country_id)
            country_name = country_entity.to_dict()["name"]

            embed = discord.Embed(
                title="🏗️ Récapitulatif complet des constructions",
                description=f"**{country_name}**",
                color=self.factory_color_int,
            )

            # Structures summary
            if structures:
                structure_summary = {}
                total_structure_cost = 0
                total_capacity = 0

                for structure in structures:
                    struct_type = structure.get("type", "Inconnu")
                    level = structure.get("level", 1)
                    capacity = structure.get("capacity", 0)
                    cost = self.db.get_construction_cost(
                        struct_type, level, structure.get("specialisation", "NA")
                    )

                    if struct_type not in structure_summary:
                        structure_summary[struct_type] = {
                            "count": 0,
                            "total_capacity": 0,
                            "total_cost": 0,
                        }

                    structure_summary[struct_type]["count"] += 1
                    structure_summary[struct_type]["total_capacity"] += capacity
                    structure_summary[struct_type]["total_cost"] += cost
                    total_structure_cost += cost
                    total_capacity += capacity

                structure_text = "\n".join(
                    [
                        f"**{stype}:** {data['count']} unités ({data['total_capacity']} capacité)"
                        for stype, data in structure_summary.items()
                    ]
                )

                embed.add_field(
                    name="🏢 Structures",
                    value=f"{structure_text}\n**Coût total:** {convert(total_structure_cost)}\n**Capacité totale:** {total_capacity:,}",
                    inline=False,
                )

            # Infrastructure summary
            if infrastructures:
                total_infra_length = sum(
                    infra.get("length_km", 0) for infra in infrastructures
                )
                total_infra_cost = sum(
                    infra.get("total_cost", 0) for infra in infrastructures
                )
                infra_types = {}
                for infra in infrastructures:
                    itype = infra.get("type", "Inconnu")
                    infra_types[itype] = infra_types.get(itype, 0) + 1

                infra_text = ", ".join(
                    [f"{itype}: {count}" for itype, count in infra_types.items()]
                )

                embed.add_field(
                    name="🛣️ Infrastructures",
                    value=f"**Types:** {infra_text}\n**Longueur totale:** {total_infra_length:,.1f} km\n**Coût total:** {convert(total_infra_cost)}",
                    inline=False,
                )

            # Power plants summary
            if power_plants:
                total_production = sum(
                    plant.get("production_mwh", 0) for plant in power_plants
                )
                total_power_cost = sum(
                    plant.get("construction_cost", 0) for plant in power_plants
                )
                plant_types = {}
                for plant in power_plants:
                    ptype = plant.get("type", "Inconnu")
                    plant_types[ptype] = plant_types.get(ptype, 0) + 1

                plant_text = ", ".join(
                    [f"{ptype}: {count}" for ptype, count in plant_types.items()]
                )

                embed.add_field(
                    name="⚡ Production électrique",
                    value=f"**Types:** {plant_text}\n**Production totale:** {total_production:,} MWh\n**Coût total:** {convert(total_power_cost)}",
                    inline=False,
                )

            # Global summary
            total_investment = 0
            if structures:
                total_investment += total_structure_cost
            if infrastructures:
                total_investment += total_infra_cost
            if power_plants:
                total_investment += total_power_cost

            total_constructions = (
                len(structures) + len(infrastructures) + len(power_plants)
            )

            embed.add_field(
                name="💰 Récapitulatif financier",
                value=f"**Investissement total:** {convert(total_investment)}\n**Nombre total de constructions:** {total_constructions:,}",
                inline=False,
            )

            if total_constructions == 0:
                embed.description = (
                    f"**{country_name}** ne possède aucune construction."
                )

        except Exception as e:
            embed = discord.Embed(
                title="❌ Erreur",
                description="Impossible de récupérer les informations sur les constructions.",
                color=self.error_color_int,
            )

        await ctx.send(embed=embed)


async def setup(bot):
    """Setup function for the cog"""
    await bot.add_cog(Structures(bot))
