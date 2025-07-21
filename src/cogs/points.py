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
    amount_converter,
    ERROR_COLOR_INT,
    P_POINTS_COLOR_INT,
    D_POINTS_COLOR_INT
)


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
        from text_formatting import convert

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


class Points(commands.Cog):
    """Points-related commands for managing political and diplomatic points."""

    def __init__(self, bot):
        self.bot = bot
        self.error_color_int = ERROR_COLOR_INT
        self.money_color_int = int("FFF005", 16)
        self.p_points_color_int = P_POINTS_COLOR_INT
        self.d_points_color_int = D_POINTS_COLOR_INT

        # Get utilities instances
        self.db = get_db()
        self.dUtils = get_discord_utils(bot)

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
                self.code_list = ["P1", "P2", "P3", "P4", "PR", "PRR"]  # Fallback

    async def eco_logger(self, code, amount, user1, user2=None, type=1):
        """Log economic events to the designated channel."""
        await self.load_code_list()
        log_channel = self.bot.get_channel(1261064715480862866)
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

    async def _remove_points_generic(
        self,
        ctx,
        cible,
        amount: Union[int, str],
        point_type: int,
        emoji: str,
        color: int,
    ):
        if not self.dUtils.is_authorized(ctx):
            embed = discord.Embed(
                title="Vous n'êtes pas autorisé à effectuer cette commande.",
                description="Il vous faut être staff",
                color=self.error_color_int,
            )
            await ctx.send(embed=embed)
            return

        if not cible or not cible.get("id"):
            embed = discord.Embed(
                title="Erreur",
                description=f"{emoji} Utilisateur ou pays invalide.",
                color=self.error_color_int,
            )
            await ctx.send(embed=embed)
            return

        cible_id = str(cible["id"])
        cible_nom = cible["name"]
        cible_obj = cible["role"]

        current_points = self.db.get_points(cible_id, point_type) or 0

        if not amount_converter(amount, current_points):
            embed = discord.Embed(
                title="Erreur de retrait de points",
                description=f"{emoji} Le montant spécifié est invalide.",
                color=self.error_color_int,
            )
            await ctx.send(embed=embed)
            return

        payment_amount = amount_converter(amount, current_points)

        if not self.db.has_enough_points(cible_id, payment_amount, point_type):
            embed = discord.Embed(
                title="Erreur de retrait de points",
                description=f"{emoji} {cible_nom} n'a pas assez de points.",
                color=self.error_color_int,
            )
            await ctx.send(embed=embed)
            return

        self.db.take_points(cible_id, payment_amount, point_type)

        embed = discord.Embed(
            title="Opération réussie",
            description=f"{emoji} **{payment_amount}** ont été retirés des points de {cible_nom}.",
            color=color,
        )
        await self.eco_logger("P4", payment_amount, cible_obj, ctx.author, point_type)
        await ctx.send(embed=embed)

    async def _show_points_generic(
        self, ctx, cible, point_type: int, emoji: str, color: int, lead_type: int
    ):
        if not cible or not cible.get("id"):
            embed = discord.Embed(
                title=f"{emoji} Utilisateur ou pays invalide.",
                color=self.error_color_int,
            )
            await ctx.send(embed=embed)
            return

        cible_id = str(cible["id"])
        cible_nom = cible["name"]
        cible_obj = cible["role"]

        balance = self.db.get_points(cible_id, point_type) or 0

        if balance == 0:
            embed = discord.Embed(
                title=f"{emoji} {cible_nom} n'a pas de points de ce type.",
                color=color,
            )
        else:
            embed = discord.Embed(
                title=f"Nombre de points de {cible_nom}",
                description=f"{emoji} {cible_nom} a **{balance} points**.",
                color=color,
            )
            embed.set_footer(text=f"Classement: {self.db.get_leads(lead_type, cible_id)}")

        await ctx.send(embed=embed)

    async def _set_points_generic(
        self, ctx, cible, amount: int, point_type: int, emoji: str, color: int
    ):
        if not self.dUtils.is_authorized(ctx):
            embed = discord.Embed(
                title="Vous n'êtes pas autorisé à effectuer cette commande.",
                description="Il vous faut être staff",
                color=self.error_color_int,
            )
            await ctx.send(embed=embed)
            return

        # Extraction des données du CountryConverter
        cible_id = str(cible["id"])
        cible_nom = cible["name"]
        cible_obj = cible["role"]

        # Définition des points
        self.db.set_points(cible_id, amount, point_type)

        # Création de l'embed de confirmation
        embed = discord.Embed(
            title="Opération réussie",
            description=f"{emoji} **{amount}** points ont été définis pour {cible_nom}.",
            color=color,
        )

        # Journalisation de l'opération
        await self.eco_logger("P2", amount, cible_obj, ctx.author, point_type)

        await ctx.send(embed=embed)

    async def _add_points_generic(
        self, ctx, cible, amount: int, point_type: int, emoji: str, color: int
    ):
        if not self.dUtils.is_authorized(ctx):
            embed = discord.Embed(
                title="Vous n'êtes pas autorisé à effectuer cette commande.",
                description="Il vous faut être staff",
                color=self.error_color_int,
            )
            await ctx.send(embed=embed)
            return

        # Extraction des données depuis le CountryConverter
        cible_id = str(cible["id"])
        cible_nom = cible["name"]
        cible_obj = cible["role"]

        # On donne les points
        self.db.give_points(cible_id, amount, point_type)

        # Embed de confirmation
        embed = discord.Embed(
            title="Opération réussie",
            description=f"{emoji} **{amount}** ont été ajoutés à l'utilisateur {cible_nom}.",
            color=color,
        )
        await self.eco_logger("P1", amount, cible_obj, ctx.author, point_type)
        await ctx.send(embed=embed)

    @commands.command(name="remove_pp")
    async def remove_pp(self, ctx, cible: CountryConverter, amount: Union[int, str]):
        """Remove political points from a country (Staff only)."""
        await self._remove_points_generic(
            ctx, cible, amount, 1, ":blue_circle:", self.p_points_color_int
        )

    @commands.command(name="remove_pd")
    async def remove_pd(self, ctx, cible: CountryConverter, amount: Union[int, str]):
        """Remove diplomatic points from a country (Staff only)."""
        await self._remove_points_generic(
            ctx, cible, amount, 2, ":purple_circle:", self.d_points_color_int
        )

    @commands.command(name="points_p")
    async def points_p(self, ctx, cible: CountryConverter = None):
        """Check political points of a country or user."""
        if cible is None:
            cible = CountryEntity(ctx.author, ctx.guild).to_dict()
        await self._show_points_generic(
            ctx, cible, 1, ":blue_circle:", self.p_points_color_int, 2
        )

    @commands.command(name="points_d")
    async def points_d(self, ctx, cible: CountryConverter = None):
        """Check diplomatic points of a country or user."""
        if cible is None:
            cible = CountryEntity(ctx.author, ctx.guild).to_dict()
        await self._show_points_generic(
            ctx, cible, 2, ":purple_circle:", self.d_points_color_int, 3
        )

    @commands.command(name="set_pp")
    async def set_pp(self, ctx, cible: CountryConverter, amount: int):
        """Set political points for a country (Staff only)."""
        await self._set_points_generic(
            ctx, cible, amount, 1, ":blue_circle:", self.p_points_color_int
        )

    @commands.command(name="set_pd")
    async def set_pd(self, ctx, cible: CountryConverter, amount: int):
        """Set diplomatic points for a country (Staff only)."""
        await self._set_points_generic(
            ctx, cible, amount, 2, ":purple_circle:", self.d_points_color_int
        )

    @commands.command(name="add_pp")
    async def add_pp(self, ctx, cible: CountryConverter, amount: int):
        """Add political points to a country (Staff only)."""
        await self._add_points_generic(
            ctx, cible, amount, 1, ":blue_circle:", self.p_points_color_int
        )

    @commands.command(name="add_pd")
    async def add_pd(self, ctx, cible: CountryConverter, amount: int):
        """Add diplomatic points to a country (Staff only)."""
        await self._add_points_generic(
            ctx, cible, amount, 2, ":purple_circle:", self.d_points_color_int
        )

    @commands.command(name="use_pp")
    async def use_pp(self, ctx, amount: int = 1):
        """Use political points."""
        country = CountryEntity(ctx.author, ctx.guild).to_dict()

        if not country or not country.get("id"):
            embed = discord.Embed(
                title="Erreur d'utilisation des points",
                description=":blue_circle: Impossible d'identifier votre pays.",
                color=self.error_color_int,
            )
            await ctx.send(embed=embed)
            return

        current_points = self.db.get_points(country["id"], 1) or 0

        if not amount_converter(amount, current_points):
            embed = discord.Embed(
                title="Erreur d'utilisation des points",
                description=":blue_circle: Le montant spécifié est invalide.",
                color=self.error_color_int,
            )
            await ctx.send(embed=embed)
            return

        payment_amount = amount_converter(amount, current_points)

        if not self.db.has_enough_points(country["id"], payment_amount, 1):
            embed = discord.Embed(
                title="Erreur d'utilisation des points",
                description=f":blue_circle: Le pays {country['name']} n'a pas assez de points politiques.",
                color=self.error_color_int,
            )
            await ctx.send(embed=embed)
            return

        self.db.take_points(country["id"], payment_amount, 1)

        embed = discord.Embed(
            title="Opération réussie",
            description=f":blue_circle: **{payment_amount}** points politiques ont été utilisés par {country['role'].mention}.",
            color=self.p_points_color_int,
        )

        await self.eco_logger("P3", payment_amount, country["role"], None, 1)
        await ctx.send(embed=embed)

    @commands.command(name="use_pd")
    async def use_pd(self, ctx, amount: int = 1):
        """Use diplomatic points."""
        country = CountryEntity(ctx.author, ctx.guild).to_dict()

        if not country or not country.get("id"):
            embed = discord.Embed(
                title="Erreur d'utilisation des points",
                description=":purple_circle: Impossible d'identifier votre pays.",
                color=self.error_color_int,
            )
            await ctx.send(embed=embed)
            return

        current_points = self.db.get_points(country["id"], 2) or 0

        if not amount_converter(amount, current_points):
            embed = discord.Embed(
                title="Erreur d'utilisation des points",
                description=":purple_circle: Le montant spécifié est invalide.",
                color=self.error_color_int,
            )
            await ctx.send(embed=embed)
            return

        payment_amount = amount_converter(amount, current_points)

        if not self.db.has_enough_points(country["id"], payment_amount, 2):
            embed = discord.Embed(
                title="Erreur d'utilisation des points",
                description=f":purple_circle: Le pays {country['name']} n'a pas assez de points diplomatiques.",
                color=self.error_color_int,
            )
            await ctx.send(embed=embed)
            return

        self.db.take_points(country["id"], payment_amount, 2)

        embed = discord.Embed(
            title="Opération réussie",
            description=f":purple_circle: **{payment_amount}** points diplomatiques ont été utilisés par {country['role'].mention}.",
            color=self.d_points_color_int,
        )

        await self.eco_logger("P3", payment_amount, country["role"], None, 2)
        await ctx.send(embed=embed)


async def setup(bot):
    await bot.add_cog(Points(bot))
