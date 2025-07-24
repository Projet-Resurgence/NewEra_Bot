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
    CountryConverter,
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
        valid_types = ["usine", "base", "ecole", "logement", "centrale", "technocentre"]
        if structure_type.lower() not in valid_types:
            embed = discord.Embed(
                title="❌ Type invalide",
                description=f"Types valides: {', '.join(valid_types)}",
                color=self.error_color_int,
            )
            await ctx.send(embed=embed)
            return

        # Validate specialisation
        valid_specs = ["terrestre", "aerienne", "navale", "na"]
        if specialisation.lower() not in valid_specs:
            embed = discord.Embed(
                title="❌ Spécialisation invalide",
                description=f"Spécialisations valides: {', '.join(valid_specs)}",
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
        unit_cost = self.db.get_construction_cost(structure_type, level)
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
            country.get("id"), structure_type, specialisation, level, region_id, amount
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
    async def structures(
        self,
        ctx,
        structure_type: str = commands.parameter(
            default="all",
            description="Type de structure à afficher (Usine, Base, Ecole, Logement, Centrale, Technocentre, ou 'all')",
        ),
        user: discord.Member = commands.parameter(
            default=None,
            description="Utilisateur dont afficher les structures (optionnel, vous par défaut)",
        ),
    ):
        if user is None:
            user = ctx.author

        country = CountryEntity(user, ctx.guild).to_dict()
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
                description=f"{user.display_name} n'a aucune structure.",
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
            title=f"🏗️ Structures de {user.display_name}",
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
                value=f"**Utilisés**: {slot_info['used_capacity']:.1f}\n**Disponibles**: {slot_info['remaining_capacity']:.1f}\n**Total**: {slot_info['effective_capacity']}",
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

        country_entity = CountryEntity(target_country, ctx.guild)
        country = country_entity.to_dict()

        if not country or not country.get("id"):
            embed = discord.Embed(
                title="❌ Erreur",
                description="Le pays spécifié est invalide.",
                color=self.error_color_int,
            )
            await ctx.send(embed=embed)
            return

        # Validate parameters (same validation as construct_structure)
        valid_types = ["Usine", "Base", "Ecole", "Logement", "Centrale", "Technocentre"]
        if structure_type not in valid_types:
            embed = discord.Embed(
                title="❌ Type invalide",
                description=f"Types valides: {', '.join(valid_types)}",
                color=self.error_color_int,
            )
            await ctx.send(embed=embed)
            return

        valid_specs = ["Terrestre", "Aerienne", "Navale", "NA"]
        if specialisation not in valid_specs:
            embed = discord.Embed(
                title="❌ Spécialisation invalide",
                description=f"Spécialisations valides: {', '.join(valid_specs)}",
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
            country.get("id"), structure_type, specialisation, level, region_id, amount
        ):
            embed = discord.Embed(
                title="✅ Structures ajoutées",
                description=f"{amount} {structure_type}(s) {specialisation} niveau {level} ajoutée(s) à {country['name']}.",
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


async def setup(bot):
    """Setup function for the cog"""
    await bot.add_cog(Structures(bot))
