"""
Economy commands cog for NEBot.
Contains balance and other economic-related commands.
"""

import discord
from discord.ext import commands
from discord import app_commands

# Import centralized utilities
from shared_utils import (
    get_db,
    get_discord_utils,
    CountryEntity,
    CountryConverter,
    country_autocomplete,
    convert,
    amount_converter,
    ERROR_COLOR_INT,
    MONEY_COLOR_INT,
)


class Economy(commands.Cog):
    """Economy-related commands for managing currencies and balances."""

    def __init__(self, bot):
        self.bot = bot
        self.error_color_int = ERROR_COLOR_INT
        self.money_color_int = MONEY_COLOR_INT
        self.p_points_color_int = int("006AFF", 16)
        self.d_points_color_int = int("8b1bd1", 16)

        # Get utilities instances
        self.db = get_db()
        self.dUtils = get_discord_utils(bot, self.db)

        # We'll get code_list from main.json when needed
        self.code_list = []

    async def load_code_list(self):
        """Load code_list from main.json if not already loaded."""
        if not self.code_list:
            try:
                import json

                with open("datas/main.json") as f:
                    json_data = json.load(f)
                    self.code_list = json_data["code_list"]
            except Exception as e:
                print(f"Failed to load code_list: {e}")
                self.code_list = ["M1", "M2", "M3", "M4", "M5", "MR", "MRR"]  # Fallback

    async def eco_logger(self, code, amount, user1, user2=None, type=1):
        """Log economic events to the designated channel."""
        await self.load_code_list()
        log_channel_id = self.db.get_setting("eco_log_channel_id")
        log_channel_id = int(log_channel_id) if log_channel_id else None
        log_channel = self.bot.get_channel(log_channel_id) if log_channel_id else None
        event = EcoLogEvent(
            code,
            amount,
            user1,
            user2,
            type,
            self.money_color_int,
            self.p_points_color_int,
            self.d_points_color_int,
            self.code_list,
        )

        if not event.is_valid_code():
            print("Erreur de code : Le code donné n'est pas bon.")
            return

        embed = event.get_embed()
        if embed:
            await log_channel.send(embed=embed)
        else:
            print("Code non reconnu dans les mappings.")

    @commands.hybrid_command(
        name="bal",
        brief="Affiche le solde d'un pays ou utilisateur.",
        usage="bal [pays]",
        description="Consulte le solde monétaire d'un pays spécifique ou de votre propre pays.",
        help="""Affiche le solde monétaire d'un pays avec son classement.

        FONCTIONNALITÉ :
        - Affiche le solde d'argent du pays spécifié
        - Montre le classement du pays dans le leaderboard économique
        - Si aucun pays n'est spécifié, affiche votre propre solde

        ARGUMENTS :
        - `[pays]` : Optionnel. Pays dont afficher le solde (mention, nom ou ID)

        EXEMPLE :
        - `bal` : Affiche votre propre solde
        - `bal @France` : Affiche le solde de la France
        - `bal 123456789` : Affiche le solde du pays avec cet ID
        """,
        hidden=False,
        enabled=True,
        case_insensitive=True,
    )
    @app_commands.autocomplete(country=country_autocomplete)
    async def balance(
        self,
        ctx,
        country: CountryConverter = commands.parameter(
            default=None,
            description="Pays dont afficher le solde (optionnel, votre pays par défaut)",
        ),
    ):
        """Check the balance of a country or user."""
        if not country:
            country = CountryEntity(ctx.author, ctx.guild).to_dict()
        if not country or not country.get("id"):
            embed = discord.Embed(
                title="Erreur de balance",
                description=":moneybag: L'utilisateur ou le pays spécifié est invalide.",
                color=self.error_color_int,
            )
            await ctx.send(embed=embed)
            return

        balance = self.db.get_balance(country.get("id"))
        if balance == 0:
            embed = discord.Embed(
                title=":moneybag: Cet utilisateur n'a pas d'argent",
                color=self.money_color_int,
            )
        else:
            embed = discord.Embed(
                title=f"Balance de {country.get('name')}",
                description=f":moneybag: L'utilisateur {country.get('name')} a **{convert(str(balance))} d'argent**.",
                color=self.money_color_int,
            )
            embed.set_footer(
                text=f"Classement: {self.db.get_leads(1, country.get('id'))}"
            )
        await ctx.send(embed=embed)

    @commands.hybrid_command(
        name="money",
        brief="Alias pour la commande bal - affiche le solde.",
        usage="money [pays]",
        description="Consulte le solde monétaire d'un pays (même fonctionnalité que 'bal').",
        help="""Alias de la commande 'bal' pour afficher le solde monétaire.

        FONCTIONNALITÉ :
        - Identique à la commande 'bal'
        - Affiche le solde d'argent du pays spécifié
        - Montre le classement du pays dans le leaderboard économique

        ARGUMENTS :
        - `[pays]` : Optionnel. Pays dont afficher le solde (mention, nom ou ID)

        EXEMPLE :
        - `money` : Affiche votre propre solde
        - `money @France` : Affiche le solde de la France
        """,
        hidden=False,
        enabled=True,
        case_insensitive=True,
    )
    async def money_alias(
        self,
        ctx,
        country: CountryConverter = commands.parameter(
            default=None,
            description="Pays dont afficher le solde (optionnel, votre pays par défaut)",
        ),
    ):
        """Alias for the balance command."""
        await self.balance(ctx, country)

    @commands.hybrid_command(
        name="give",
        brief="Transfère de l'argent à un autre pays.",
        usage="give <pays_destinataire> <montant>",
        description="Effectue un transfert d'argent de votre pays vers un autre pays.",
        help="""Transfère de l'argent de votre pays vers un autre pays.

        FONCTIONNALITÉ :
        - Vérifie que vous avez suffisamment d'argent
        - Transfère le montant spécifié au pays destinataire
        - Enregistre la transaction dans les logs économiques
        - Supporte les montants relatifs (%, all, half)

        MONTANTS SUPPORTÉS :
        - Nombre exact : `1000`, `50000`
        - Pourcentage : `50%` (50% de votre solde)
        - Mots-clés : `all` (tout), `half` (moitié)

        RESTRICTIONS :
        - Vous devez avoir suffisamment d'argent
        - Le pays destinataire doit être valide

        ARGUMENTS :
        - `<pays_destinataire>` : Pays qui recevra l'argent (mention, nom ou ID)
        - `<montant>` : Montant à transférer (nombre, pourcentage, ou mot-clé)

        EXEMPLE :
        - `give @France 1000` : Donne 1000 d'argent à la France
        - `give Allemagne 50%` : Donne 50% de votre solde à l'Allemagne
        - `give 123456789 all` : Donne tout votre argent au pays avec cet ID
        """,
        hidden=False,
        enabled=True,
        case_insensitive=True,
    )
    @app_commands.autocomplete(country=country_autocomplete)
    async def give_money(
        self,
        ctx,
        country: CountryConverter = commands.parameter(
            description="Pays qui recevra l'argent (mention, nom ou ID)"
        ),
        amount: str = commands.parameter(
            description="Montant à transférer (nombre, pourcentage comme '50%', ou 'all'/'half')"
        ),
    ):
        """Give money to another country."""
        author = CountryEntity(ctx.author, ctx.guild).to_dict()
        if not author or not country or not country.get("id"):
            embed = discord.Embed(
                title="Erreur de donation",
                description=":moneybag: L'utilisateur ou le pays spécifié est invalide.",
                color=self.error_color_int,
            )
            await ctx.send(embed=embed)
            return
        sender_balance = self.db.get_balance(author.get("id"))
        if sender_balance is None:
            sender_balance = 0
        payment_amount = amount_converter(amount, sender_balance)
        if not payment_amount:
            embed = discord.Embed(
                title="Erreur de donation",
                description=":moneybag: Le montant spécifié est invalide.",
                color=self.error_color_int,
            )
            await ctx.send(embed=embed)
            return
        if not self.db.has_enough_balance(author.get("id"), payment_amount):
            print(sender_balance, payment_amount)
            embed = discord.Embed(
                title="Erreur de donation",
                description=f":moneybag: L'utilisateur {author.get('role').mention} n'a pas assez d'argent.",
                color=self.error_color_int,
            )
            await ctx.send(embed=embed)
            return
        self.db.give_balance(country.get("id"), payment_amount)
        self.db.take_balance(author.get("id"), payment_amount)
        transa_embed = discord.Embed(
            title="Opération réussie",
            description=f":moneybag: **{convert(str(payment_amount))}** ont été donnés à {country.get('role').mention}.",
            color=self.money_color_int,
        )
        await self.eco_logger(
            "M1", payment_amount, author.get("role"), country.get("role")
        )
        await ctx.send(embed=transa_embed)

    @commands.hybrid_command(
        name="add_money",
        brief="Ajoute de l'argent à un pays (Staff uniquement).",
        usage="add_money <pays> <montant>",
        description="Ajoute un montant d'argent spécifié au solde d'un pays.",
        help="""Ajoute de l'argent au solde d'un pays spécifié.

        FONCTIONNALITÉ :
        - Ajoute le montant spécifié au solde existant du pays
        - Enregistre l'opération dans les logs économiques avec alerte
        - Vérifie les autorisations staff avant exécution

        RESTRICTIONS :
        - Réservé aux membres du staff uniquement
        - Le pays cible doit être valide

        ARGUMENTS :
        - `<pays>` : Pays qui recevra l'argent (mention, nom ou ID)
        - `<montant>` : Montant d'argent à ajouter (nombre positif)

        EXEMPLE :
        - `add_money @France 50000` : Ajoute 50000 d'argent à la France
        - `add_money Allemagne 100000` : Ajoute 100000 d'argent à l'Allemagne
        """,
        hidden=False,
        enabled=True,
        case_insensitive=True,
    )
    async def add_money(
        self,
        ctx,
        country: CountryConverter = commands.parameter(
            description="Pays qui recevra l'argent (mention, nom ou ID)"
        ),
        amount: int = commands.parameter(
            description="Montant d'argent à ajouter (nombre positif)"
        ),
    ):
        """Add money to a country (Staff only)."""
        if not country:
            embed = discord.Embed(
                title="Erreur d'ajout d'argent",
                description=":moneybag: L'utilisateur ou le pays spécifié est invalide.",
                color=self.error_color_int,
            )
            await ctx.send(embed=embed)
            return
        if not country.get("id"):
            embed = discord.Embed(
                title="Erreur d'ajout d'argent",
                description=":moneybag: L'utilisateur ou le pays spécifié est invalide.",
                color=self.error_color_int,
            )
            await ctx.send(embed=embed)
            return
        if not self.dUtils.is_authorized(ctx):
            embed = discord.Embed(
                title="Vous n'êtes pas autorisé à effectuer cette commande.",
                description="Il vous faut être staff",
                color=self.error_color_int,
            )
            await ctx.send(embed=embed)
            return

        self.db.give_balance(country.get("id"), amount)
        embed = discord.Embed(
            title="Opération réussie",
            description=f":moneybag: **{convert(str(amount))}** ont été ajoutés à l'utilisateur {country.get('name')}.",
            color=self.money_color_int,
        )

        await self.eco_logger("M2", amount, country.get("role"), ctx.author)
        await ctx.send(embed=embed)

    @commands.hybrid_command(
        name="remove_money",
        brief="Retire de l'argent d'un pays (Staff uniquement).",
        usage="remove_money <pays> <montant>",
        description="Retire un montant d'argent spécifié du solde d'un pays.",
        help="""Retire de l'argent du solde d'un pays spécifié.

        FONCTIONNALITÉ :
        - Retire le montant spécifié du solde du pays
        - Vérifie que le pays a suffisamment d'argent
        - Enregistre l'opération dans les logs économiques avec double alerte
        - Supporte les montants relatifs (%, all, half)

        MONTANTS SUPPORTÉS :
        - Nombre exact : `1000`, `50000`
        - Pourcentage : `50%` (50% du solde du pays)
        - Mots-clés : `all` (tout), `half` (moitié)

        RESTRICTIONS :
        - Réservé aux membres du staff uniquement
        - Le pays doit avoir suffisamment d'argent
        - Le pays cible doit être valide

        ARGUMENTS :
        - `<pays>` : Pays dont retirer l'argent (mention, nom ou ID)
        - `<montant>` : Montant à retirer (nombre, pourcentage, ou mot-clé)

        EXEMPLE :
        - `remove_money @France 10000` : Retire 10000 d'argent à la France
        - `remove_money Allemagne 25%` : Retire 25% du solde de l'Allemagne
        - `remove_money 123456789 all` : Retire tout l'argent du pays avec cet ID
        """,
        hidden=False,
        enabled=True,
        case_insensitive=True,
    )
    async def remove_money(
        self,
        ctx,
        country: CountryConverter = commands.parameter(
            description="Pays dont retirer l'argent (mention, nom ou ID)"
        ),
        amount: str = commands.parameter(
            description="Montant à retirer (nombre, pourcentage comme '25%', ou 'all'/'half')"
        ),
    ):
        """Remove money from a country (Staff only)."""
        if not self.dUtils.is_authorized(ctx):
            embed = discord.Embed(
                title="Vous n'êtes pas autorisé à effectuer cette commande.",
                description="Il vous faut être staff",
                color=self.error_color_int,
            )
            await ctx.send(embed=embed)
            return

        if not country or not country.get("id"):
            embed = discord.Embed(
                title="Erreur",
                description=":moneybag: Le pays spécifié est invalide.",
                color=self.error_color_int,
            )
            await ctx.send(embed=embed)
            return

        balance = self.db.get_balance(country.get("id")) or 0
        payment_amount = amount_converter(amount, balance)

        if not payment_amount:
            embed = discord.Embed(
                title="Erreur de retrait",
                description=":moneybag: Le montant spécifié est invalide.",
                color=self.error_color_int,
            )
            await ctx.send(embed=embed)
            return

        if not self.db.has_enough_balance(country.get("id"), payment_amount):
            embed = discord.Embed(
                title="Erreur de retrait",
                description=f":moneybag: Le pays {country.get('role').mention} n'a pas assez d'argent.",
                color=self.error_color_int,
            )
            await ctx.send(embed=embed)
            return

        self.db.take_balance(country.get("id"), payment_amount)

        embed = discord.Embed(
            title="Opération réussie",
            description=f":moneybag: **{convert(str(payment_amount))}** ont été retirés du pays {country.get('role').mention}.",
            color=self.money_color_int,
        )
        await self.eco_logger("M5", payment_amount, country.get("role"), ctx.author)
        await ctx.send(embed=embed)

    @commands.hybrid_command(
        name="set_money",
        brief="Définit le solde d'un pays à un montant exact (Staff uniquement).",
        usage="set_money <pays> <montant>",
        description="Définit le solde d'un pays à un montant exact, remplaçant le solde actuel.",
        help="""Définit le solde d'un pays à un montant exact.

        FONCTIONNALITÉ :
        - Remplace complètement le solde actuel du pays
        - Définit le nouveau solde au montant spécifié
        - Enregistre l'opération dans les logs économiques avec alerte
        - Vérifie les autorisations staff avant exécution

        RESTRICTIONS :
        - Réservé aux membres du staff uniquement
        - Le pays cible doit être valide
        - Le montant doit être un nombre positif

        ARGUMENTS :
        - `<pays>` : Pays dont définir le solde (mention, nom ou ID)
        - `<montant>` : Nouveau solde à définir (nombre positif)

        EXEMPLE :
        - `set_money @France 75000` : Définit le solde de la France à 75000
        - `set_money Allemagne 100000` : Définit le solde de l'Allemagne à 100000
        """,
        hidden=False,
        enabled=True,
        case_insensitive=True,
    )
    async def set_money(
        self,
        ctx,
        country: CountryConverter = commands.parameter(
            description="Pays dont définir le solde (mention, nom ou ID)"
        ),
        amount: int = commands.parameter(
            description="Nouveau solde à définir (nombre positif)"
        ),
    ):
        """Set money for a country (Staff only)."""
        if not self.dUtils.is_authorized(ctx):
            embed = discord.Embed(
                title="Vous n'êtes pas autorisé à effectuer cette commande.",
                description="Il vous faut être staff",
                color=self.error_color_int,
            )
            await ctx.send(embed=embed)
            return

        if not country or not country.get("id"):
            embed = discord.Embed(
                title="Erreur",
                description=":moneybag: Le pays spécifié est invalide.",
                color=self.error_color_int,
            )
            await ctx.send(embed=embed)
            return

        self.db.set_balance(country.get("id"), amount)

        embed = discord.Embed(
            title="Opération réussie",
            description=f":moneybag: **{convert(str(amount))}** ont été définis pour {country.get('role').mention}.",
            color=self.money_color_int,
        )
        await self.eco_logger("M3", amount, country.get("role"), ctx.author)
        await ctx.send(embed=embed)

    @commands.hybrid_command(
        name="pay",
        brief="Paye de l'argent au bot (retire de l'argent de votre solde).",
        usage="pay <montant>",
        description="Effectue un paiement au bot, retirant l'argent de votre solde.",
        help="""Paye de l'argent au bot, retirant le montant de votre solde.

        FONCTIONNALITÉ :
        - Retire le montant spécifié de votre solde
        - Vérifie que vous avez suffisamment d'argent
        - Enregistre la transaction dans les logs économiques
        - Supporte les montants relatifs (%, all, half)
        - Utile pour les achats, taxes, ou pénalités

        MONTANTS SUPPORTÉS :
        - Nombre exact : `1000`, `5000`
        - Pourcentage : `10%` (10% de votre solde)
        - Mots-clés : `all` (tout), `half` (moitié)

        RESTRICTIONS :
        - Vous devez avoir suffisamment d'argent
        - Vous devez appartenir à un pays valide

        ARGUMENTS :
        - `<montant>` : Montant à payer (nombre, pourcentage, ou mot-clé)

        EXEMPLE :
        - `pay 2000` : Paye 2000 d'argent au bot
        - `pay 15%` : Paye 15% de votre solde au bot
        - `pay half` : Paye la moitié de votre solde au bot
        """,
        hidden=False,
        enabled=True,
        case_insensitive=True,
    )
    async def pay(
        self,
        ctx,
        amount: str = commands.parameter(
            description="Montant à payer au bot (nombre, pourcentage comme '15%', ou 'all'/'half')"
        ),
    ):
        """Pay money to the bot."""
        country = CountryEntity(ctx.author, ctx.guild).to_dict()
        balance = self.db.get_balance(country.get("id"))

        payment_amount = amount_converter(amount, balance)
        if not payment_amount:
            embed = discord.Embed(
                title="Erreur de retrait d'argent",
                description=":moneybag: Le montant spécifié est invalide.",
                color=self.error_color_int,
            )
            await ctx.send(embed=embed)
            return

        if not self.db.has_enough_balance(country.get("id"), payment_amount):
            embed = discord.Embed(
                title="Erreur de paiement",
                description=f":moneybag: Vous n'avez pas assez d'argent pour effectuer cette transaction.",
                color=self.error_color_int,
            )
            await ctx.send(embed=embed)
            return

        self.db.take_balance(country.get("id"), payment_amount)
        embed = discord.Embed(
            title="Opération réussie",
            description=f":moneybag: **{convert(str(payment_amount))}** ont été payés au bot.",
            color=self.money_color_int,
        )
        await self.eco_logger("M4", payment_amount, country.get("role"), ctx.author)
        await ctx.send(embed=embed)


class EcoLogEvent:
    """Event logging class for economic transactions."""

    def __init__(
        self,
        code,
        amount,
        user1,
        user2=None,
        type=1,
        money_color_int=None,
        p_points_color_int=None,
        d_points_color_int=None,
        code_list=None,
    ):
        self.code = code
        self.amount = convert(str(amount)) if len(str(amount)) > 3 else amount
        self.user1 = user1
        self.user2 = user2
        self.type = type
        self.money_color_int = money_color_int or int("FFF005", 16)
        self.p_points_color_int = p_points_color_int or int("006AFF", 16)
        self.d_points_color_int = d_points_color_int or int("8b1bd1", 16)
        self.code_list = code_list or []

    def is_valid_code(self):
        return self.code in self.code_list

    def get_embed(self):
        if self.code.startswith("M"):
            return self._money_embed()
        elif self.code.startswith("P"):
            return self._points_embed()
        return None

    def _money_embed(self):
        templates = {
            "M1": (
                "Nouvelle transaction entre joueurs",
                ":moneybag: L'utilisateur {u1} a donné {amt} à {u2}.",
            ),
            "M2": (
                "<a:NE_Alert:1261090848024690709> Ajout d'argent",
                ":moneybag: {u1} s'est fait ajouter {amt} par {u2}.",
            ),
            "M3": (
                "<a:NE_Alert:1261090848024690709> Argent défini",
                ":moneybag: {u1} s'est fait définir son argent à {amt} par {u2}.",
            ),
            "M4": ("Argent payé", ":moneybag: {u1} a payé {amt} à la banque."),
            "M5": (
                "<a:NE_Alert:1261090848024690709> <a:NE_Alert:1261090848024690709> Retrait d'argent",
                ":moneybag: {u1} s'est fait retirer {amt} par {u2}.",
            ),
            "MR": (
                "<a:NE_Alert:1261090848024690709> <a:NE_Alert:1261090848024690709> <a:NE_Alert:1261090848024690709> Reset de l'économie",
                ":moneybag: {u1} a réinitialisé l'économie.",
            ),
            "MRR": (
                "<a:NE_Alert:1261090848024690709> <a:NE_Alert:1261090848024690709> <a:NE_Alert:1261090848024690709> <a:NE_Alert:1261090848024690709> Tentative de reset",
                ":moneybag: {u1} a tenté de réinitialiser l'économie.",
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
        return discord.Embed(title=title, description=desc, color=self.money_color_int)

    def _points_embed(self):
        p_type = "Points politiques" if self.type == 1 else "Points diplomatiques"
        color = self.p_points_color_int if self.type == 1 else self.d_points_color_int

        templates = {
            "P1": (
                f"<a:NE_Alert:1261090848024690709> {p_type} ajoutés",
                ":blue_circle: {u1} s'est fait ajouter {amt} {p_type} par {u2}.",
            ),
            "P2": (
                f"<a:NE_Alert:1261090848024690709> {p_type} définis",
                ":blue_circle: {u1} s'est fait définir ses {p_type} à {amt} par {u2}.",
            ),
            "P3": (f"{p_type} utilisé", ":blue_circle: {u1} a utilisé {amt} {p_type}."),
            "P4": (
                f"<a:NE_Alert:1261090848024690709> <a:NE_Alert:1261090848024690709> {p_type} retirés",
                ":blue_circle: {u1} s'est fait retirer {amt} {p_type} par {u2}.",
            ),
            "PR": (
                f"<a:NE_Alert:1261090848024690709> <a:NE_Alert:1261090848024690709> <a:NE_Alert:1261090848024690709> Reset des {p_type}",
                ":blue_circle: {u1} a réinitialisé les {p_type}.",
            ),
            "PRR": (
                f"<a:NE_Alert:1261090848024690709> <a:NE_Alert:1261090848024690709> <a:NE_Alert:1261090848024690709> <a:NE_Alert:1261090848024690709> Tentative de reset",
                ":blue_circle: {u1} a tenté de réinitialiser les {p_type}.",
            ),
        }

        title, desc_template = templates.get(self.code, (None, None))
        if not title:
            return None

        desc = desc_template.format(
            u1=f"{self.user1.name} ({self.user1.id})",
            u2=f"{self.user2.name} ({self.user2.id})" if self.user2 else "❓",
            amt=self.amount,
            p_type=p_type,
        )
        return discord.Embed(title=title, description=desc, color=color)


async def setup(bot):
    """Setup function to add the cog to the bot."""
    await bot.add_cog(Economy(bot))
