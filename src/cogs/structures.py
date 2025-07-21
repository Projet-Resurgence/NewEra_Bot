"""
Structures commands cog for NEBot.
Contains all structure-related commands (previously usines/batiments).
"""

import discord
from discord.ext import commands
from typing import Union
import json

# Import centralized utilities
from shared_utils import (
    get_db,
    get_discord_utils,
    CountryEntity,
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
        self.dUtils = get_discord_utils(bot)

        # Load production data
        with open("datas/usines.json") as f:
            self.production_data = json.load(f)
        with open("datas/bases.json") as f:
            self.base_data = json.load(f)
        with open("datas/main.json") as f:
            json_data = json.load(f)
            self.bat_types = json_data["bat_types"]

        # Color constants
        self.error_color_int = ERROR_COLOR_INT
        self.money_color_int = MONEY_COLOR_INT
        self.factory_color_int = FACTORY_COLOR_INT

    @commands.command(
        name="construct_structure",
        brief="Construit un certain nombre de structures d'un niveau spécifié.",
        usage="construct_structure <amount> <lvl>",
        description="Construit plusieurs structures du niveau indiqué et débite le coût correspondant.",
        help="""Construit une ou plusieurs structures en fonction de la quantité et du niveau indiqués, tout en vérifiant le solde de l'utilisateur.

        ARGUMENTS :
        - `<amount>` : Nombre de structures à construire (entier).
        - `<lvl>` : Niveau des structures à construire (entier ou chaîne représentative du niveau).
        - `<region>` : Id de la région où les structures seront construites

        EXEMPLE :
        - `construct_structure 3 1` : Construit 3 structures de niveau 1 si l'utilisateur a suffisamment de fonds pour couvrir le coût.
        """,
        case_insensitive=True,
    )
    async def construct_structure(
        self,
        ctx,
        amount: int = commands.parameter(
            description="Nombre de structures à construire (doit être un entier positif)."
        ),
        lvl=commands.parameter(
            description="Niveau des structures à construire (indique le coût de construction par structure)."
        ),
        region: int = commands.parameter(
            description="ID de la région où les structures seront construites.",
        ),
        struct_type: str = commands.parameter(
            description="Type de structure à construire (par exemple, 'usine', 'base', etc.).",
        ),
    ) -> None:
        country = CountryEntity(ctx.author, ctx.guild).to_dict()
        struct_type = struct_type.lower()
        if not country or not country.get("id"):
            embed = discord.Embed(
                title="Erreur de donation",
                description=":moneybag: L'utilisateur ou le pays spécifié est invalide.",
                color=self.error_color_int,
            )
            await ctx.send(embed=embed)
            return

        balance = self.db.get_balance(country.get("id"))
        if not amount_converter(amount, balance):
            embed = discord.Embed(
                title="Erreur de paiement",
                description=":moneybag: Le montant spécifié est invalide.",
                color=self.error_color_int,
            )
            await ctx.send(embed=embed)
            return

        payment_amount = amount * int(
            self.production_data[str(lvl)]["cout_construction"]
        )

        if not self.db.has_enough_balance(country.get("id"), payment_amount):
            embed = discord.Embed(
                title="Erreur de paiement",
                description=f":moneybag: Vous n'avez pas assez d'argent pour effectuer cette transaction.\nMontant demandé : {payment_amount}. | Vous possédez : {balance}",
                color=self.error_color_int,
            )
            await ctx.send(embed=embed)
            return

        self.db.take_balance(country.get("id"), payment_amount)
        self.db.give_usine(country.get("id"), amount, lvl, region)
        embed = discord.Embed(
            title="Opération réussie",
            description=f":factory: Vos {amount} structures de niveau {lvl} auront coûtés **{convert(str(payment_amount))}** et ont été payés au bot.",
            color=self.money_color_int,
        )
        await ctx.send(embed=embed)

    @commands.command(
        name="sell_structure",
        brief="Vend des structures.",
        usage="sell_structure <struct_type> <amount> <lvl>",
        description="Vend des structures et récupère de l'argent.",
        hidden=False,
        enabled=True,
        case_insensitive=True,
    )
    async def sell_structure(self, ctx, struct_type, amount: int, lvl):
        user = ctx.author
        balance = self.db.get_usine(user.id, lvl, 0)
        if balance is None:
            balance = 0

        if not amount_converter(amount, balance):
            embed = discord.Embed(
                title="Erreur de retrait de structure",
                description=":factory: Le montant spécifié est invalide.",
                color=self.error_color_int,
            )
            await ctx.send(embed=embed)
            return
        payment_amount = amount * int(
            self.production_data[str(lvl)]["cout_construction"]
        )

        if not self.db.has_enough_bats(user.id, amount, lvl, 0):
            embed = discord.Embed(
                title="Erreur de paiement",
                description=f":factory: Vous n'avez pas assez de structures pour effectuer cette transaction.\nMontant demandé : {amount}. | Vous possédez : {balance}",
                color=self.error_color_int,
            )
            await ctx.send(embed=embed)
            return

        self.db.give_balance(user.id, payment_amount)
        self.db.remove_usine(user.id, amount, lvl, 0)
        embed = discord.Embed(
            title="Opération réussie",
            description=f":factory: Vos {amount} structures de niveau {lvl} vous ont rapporté **{convert(str(payment_amount))}** et ont été ajouté à votre solde.",
            color=self.money_color_int,
        )
        await ctx.send(embed=embed)

    @commands.command(
        name="structures",
        brief="Affiche les structures d'un utilisateur.",
        usage="structures <type> [user]",
        description="Affiche les structures d'un utilisateur par type.",
        hidden=False,
        enabled=True,
        case_insensitive=True,
    )
    async def structures(self, ctx, type, user: discord.Member = None):
        if user is None:
            user = ctx.author
        types = [1, 2, 3, 4, 5, 6, 7]
        if (type.lower() != "all") and (int(type) not in types):
            return await ctx.send("Type invalide")
        if type.lower() == "all":
            embed = discord.Embed(title=f"Structures de {user.name}", description="")
            for i in types:
                current_structures = self.db.get_usine(user.id, i, 0)
                embed.description += f"Type {i} : {current_structures}\n"
        else:
            type = int(type)
            embed = discord.Embed(
                title=f"Structures de type {type} de {user.name}",
                description=f"L'utilisateur a **{str(self.db.get_usine(user.id, type, 0))}** structures de type {type}.",
            )
        await ctx.send(embed=embed)
        
    @commands.command(
        name="add_structure",
        brief="Ajoute des structures à un utilisateur (Staff seulement).",

    @commands.command(
        name="remove_structure",
        brief="Retire des structures d'un utilisateur (Staff seulement).",
        usage="remove_structure <user> <amount> <lvl>",
        description="Retire des structures de l'inventaire d'un utilisateur.",
        hidden=False,
        enabled=True,
        case_insensitive=True,
    )
    async def remove_structure(
        self, ctx, user: discord.Member, amount: Union[int, str], lvl: int
    ):
        if not self.dUtils.is_authorized(ctx):
            embed = discord.Embed(
                title="Vous n'êtes pas autorisé à effectuer cette commande.",
                description="Il vous faut être staff",
                color=self.error_color_int,
            )
            await ctx.send(embed=embed)
            return

        balance = self.db.get_usine(user.id, lvl, 0)
        if balance is None:
            balance = 0

        if not amount_converter(amount, balance):
            embed = discord.Embed(
                title="Erreur de retrait de structure",
                description=":factory: Le montant spécifié est invalide.",
                color=self.error_color_int,
            )
            await ctx.send(embed=embed)
            return

        payment_amount = amount_converter(amount, balance)
        if not self.db.has_enough_balance(user.id, payment_amount):
            embed = discord.Embed(
                title="Erreur de retrait d'argent",
                description=f":factory: L'utilisateur {user.name} n'a pas assez de structures.",
                color=self.error_color_int,
            )
            await ctx.send(embed=embed)
            return
        self.db.remove_usine(user.id, amount, lvl, 0)
        embed = discord.Embed(
            title="Opération réussie",
            description=f":factory: **{convert(str(payment_amount))}** ont été retirés de l'inventaire de structures de niveau {lvl} de l'utilisateur {user.name}.",
            color=self.money_color_int,
        )
        await ctx.send(embed=embed)

async def setup(bot):
    """Setup function for the cog"""
    await bot.add_cog(Structures(bot))
