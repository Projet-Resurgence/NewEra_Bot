import discord
from discord.ext import commands
from discord import app_commands
import json

# Import centralized utilities
from shared_utils import (
    get_db,
    get_discord_utils,
    CountryEntity,
    CountryConverter,
    country_autocomplete,
    eco_logger,
    amount_converter,
    ERROR_COLOR_INT,
    P_POINTS_COLOR_INT,
    D_POINTS_COLOR_INT,
)


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
        self.dUtils = get_discord_utils(bot, self.db)

    async def _remove_points_generic(
        self,
        ctx,
        target,
        amount: str,
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

        if not target or not target.get("id"):
            embed = discord.Embed(
                title="Erreur",
                description=f"{emoji} Utilisateur ou pays invalide.",
                color=self.error_color_int,
            )
            await ctx.send(embed=embed)
            return

        target_id = str(target["id"])
        target_name = target["name"]
        target_obj = target["role"]

        current_points = self.db.get_points(target_id, point_type) or 0

        if not amount_converter(amount, current_points):
            embed = discord.Embed(
                title="Erreur de retrait de points",
                description=f"{emoji} Le montant spécifié est invalide.",
                color=self.error_color_int,
            )
            await ctx.send(embed=embed)
            return

        payment_amount = amount_converter(amount, current_points)

        if not self.db.has_enough_points(target_id, payment_amount, point_type):
            embed = discord.Embed(
                title="Erreur de retrait de points",
                description=f"{emoji} {target_name} n'a pas assez de points.",
                color=self.error_color_int,
            )
            await ctx.send(embed=embed)
            return

        self.db.take_points(target_id, payment_amount, point_type)

        embed = discord.Embed(
            title="Opération réussie",
            description=f"{emoji} **{payment_amount}** ont été retirés des points de {target_name}.",
            color=color,
        )
        await eco_logger(
            "REMOVE_POINTS", payment_amount, target_obj, ctx.author, point_type
        )
        await ctx.send(embed=embed)

    async def _show_points_generic(
        self, ctx, target, point_type: int, emoji: str, color: int, lead_type: int
    ):
        if not target or not target.get("id"):
            embed = discord.Embed(
                title=f"{emoji} Utilisateur ou pays invalide.",
                color=self.error_color_int,
            )
            await ctx.send(embed=embed)
            return

        target_id = str(target["id"])
        target_name = target["name"]
        target_obj = target["role"]

        balance = self.db.get_points(target_id, point_type) or 0

        if balance == 0:
            embed = discord.Embed(
                title=f"{emoji} {target_name} n'a pas de points de ce type.",
                color=color,
            )
        else:
            embed = discord.Embed(
                title=f"Nombre de points de {target_name}",
                description=f"{emoji} {target_name} a **{balance} points**.",
                color=color,
            )
            embed.set_footer(
                text=f"Classement: {self.db.get_leads(lead_type, target_id)}"
            )

        await ctx.send(embed=embed)

    async def _set_points_generic(
        self, ctx, target, amount: int, point_type: int, emoji: str, color: int
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
        target_id = str(target["id"])
        target_name = target["name"]
        target_obj = target["role"]

        # Définition des points
        self.db.set_points(target_id, amount, point_type)

        # Création de l'embed de confirmation
        embed = discord.Embed(
            title="Opération réussie",
            description=f"{emoji} **{amount}** points ont été définis pour {target_name}.",
            color=color,
        )

        # Journalisation de l'opération
        await eco_logger("SET_POINTS", amount, target_obj, ctx.author, point_type)

        await ctx.send(embed=embed)

    async def _add_points_generic(
        self, ctx, target, amount: int, point_type: int, emoji: str, color: int
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
        target_id = str(target["id"])
        target_name = target["name"]
        target_obj = target["role"]

        # On donne les points
        self.db.give_points(target_id, amount, point_type)

        # Embed de confirmation
        embed = discord.Embed(
            title="Opération réussie",
            description=f"{emoji} **{amount}** ont été ajoutés à l'utilisateur {target_name}.",
            color=color,
        )
        await eco_logger("ADD_POINTS", amount, target_obj, ctx.author, point_type)
        await ctx.send(embed=embed)

    @commands.hybrid_command(
        name="remove_pp",
        brief="Retire des points politiques d'un pays (Staff uniquement).",
        usage="remove_pp <pays> <montant>",
        description="Retire un montant de points politiques spécifié d'un pays.",
        help="""Retire des points politiques du solde d'un pays spécifié.

        FONCTIONNALITÉ :
        - Retire le montant spécifié des points politiques du pays
        - Vérifie que le pays a suffisamment de points politiques
        - Enregistre l'opération dans les logs économiques avec double alerte
        - Supporte les montants relatifs (%, all, half)

        MONTANTS SUPPORTÉS :
        - Nombre exact : `10`, `50`
        - Pourcentage : `50%` (50% des points du pays)
        - Mots-clés : `all` (tous), `half` (moitié)

        RESTRICTIONS :
        - Réservé aux membres du staff uniquement
        - Le pays doit avoir suffisamment de points politiques
        - Le pays cible doit être valide

        ARGUMENTS :
        - `<pays>` : Pays dont retirer les points politiques (mention, nom ou ID)
        - `<montant>` : Montant à retirer (nombre, pourcentage, ou mot-clé)

        EXEMPLE :
        - `remove_pp @France 5` : Retire 5 points politiques à la France
        - `remove_pp Allemagne 25%` : Retire 25% des points politiques de l'Allemagne
        - `remove_pp 123456789 all` : Retire tous les points politiques du pays
        """,
        hidden=False,
        enabled=True,
        case_insensitive=True,
    )
    @app_commands.autocomplete(target=country_autocomplete)
    async def remove_pp(
        self,
        ctx,
        target: CountryConverter = commands.parameter(
            description="Pays dont retirer les points politiques (mention, nom ou ID)"
        ),
        amount: str = commands.parameter(
            description="Montant à retirer (nombre, pourcentage comme '25%', ou 'all'/'half')"
        ),
    ):
        """Remove political points from a country (Staff only)."""
        await self._remove_points_generic(
            ctx, target, amount, 1, ":blue_circle:", self.p_points_color_int
        )

    @commands.hybrid_command(
        name="remove_pd",
        brief="Retire des points diplomatiques d'un pays (Staff uniquement).",
        usage="remove_pd <pays> <montant>",
        description="Retire un montant de points diplomatiques spécifié d'un pays.",
        help="""Retire des points diplomatiques du solde d'un pays spécifié.

        FONCTIONNALITÉ :
        - Retire le montant spécifié des points diplomatiques du pays
        - Vérifie que le pays a suffisamment de points diplomatiques
        - Enregistre l'opération dans les logs économiques avec double alerte
        - Supporte les montants relatifs (%, all, half)

        MONTANTS SUPPORTÉS :
        - Nombre exact : `10`, `50`
        - Pourcentage : `50%` (50% des points du pays)
        - Mots-clés : `all` (tous), `half` (moitié)

        RESTRICTIONS :
        - Réservé aux membres du staff uniquement
        - Le pays doit avoir suffisamment de points diplomatiques
        - Le pays cible doit être valide

        ARGUMENTS :
        - `<pays>` : Pays dont retirer les points diplomatiques (mention, nom ou ID)
        - `<montant>` : Montant à retirer (nombre, pourcentage, ou mot-clé)

        EXEMPLE :
        - `remove_pd @France 3` : Retire 3 points diplomatiques à la France
        - `remove_pd Allemagne 30%` : Retire 30% des points diplomatiques de l'Allemagne
        - `remove_pd 123456789 all` : Retire tous les points diplomatiques du pays
        """,
        hidden=False,
        enabled=True,
        case_insensitive=True,
    )
    @app_commands.autocomplete(target=country_autocomplete)
    async def remove_pd(
        self,
        ctx,
        target: CountryConverter = commands.parameter(
            description="Pays dont retirer les points diplomatiques (mention, nom ou ID)"
        ),
        amount: str = commands.parameter(
            description="Montant à retirer (nombre, pourcentage comme '30%', ou 'all'/'half')"
        ),
    ):
        """Remove diplomatic points from a country (Staff only)."""
        await self._remove_points_generic(
            ctx, target, amount, 2, ":purple_circle:", self.d_points_color_int
        )

    @commands.hybrid_command(
        name="points_p",
        brief="Affiche les points politiques d'un pays ou utilisateur.",
        usage="points_p [pays]",
        description="Consulte les points politiques d'un pays spécifique ou de votre propre pays.",
        help="""Affiche les points politiques d'un pays avec son classement.

        FONCTIONNALITÉ :
        - Affiche le nombre de points politiques du pays spécifié
        - Montre le classement du pays dans le leaderboard des points politiques
        - Si aucun pays n'est spécifié, affiche vos propres points politiques

        UTILITÉ DES POINTS POLITIQUES :
        - Actions internes au pays (réformes, lois, etc.)
        - Gestion gouvernementale
        - Influence politique interne

        ARGUMENTS :
        - `[pays]` : Optionnel. Pays dont afficher les points politiques (mention, nom ou ID)

        EXEMPLE :
        - `points_p` : Affiche vos propres points politiques
        - `points_p @France` : Affiche les points politiques de la France
        - `points_p 123456789` : Affiche les points politiques du pays avec cet ID
        """,
        hidden=False,
        enabled=True,
        case_insensitive=True,
    )
    @app_commands.autocomplete(target=country_autocomplete)
    async def points_p(
        self,
        ctx,
        target: CountryConverter = commands.parameter(
            default=None,
            description="Pays dont afficher les points politiques (optionnel, votre pays par défaut)",
        ),
    ):
        """Check political points of a country or user."""
        if target is None:
            target = CountryEntity(ctx.author, ctx.guild).to_dict()
        await self._show_points_generic(
            ctx, target, 1, ":blue_circle:", self.p_points_color_int, 2
        )

    @commands.hybrid_command(
        name="points_d",
        brief="Affiche les points diplomatiques d'un pays ou utilisateur.",
        usage="points_d [pays]",
        description="Consulte les points diplomatiques d'un pays spécifique ou de votre propre pays.",
        help="""Affiche les points diplomatiques d'un pays avec son classement.

        FONCTIONNALITÉ :
        - Affiche le nombre de points diplomatiques du pays spécifié
        - Montre le classement du pays dans le leaderboard des points diplomatiques
        - Si aucun pays n'est spécifié, affiche vos propres points diplomatiques

        UTILITÉ DES POINTS DIPLOMATIQUES :
        - Relations internationales
        - Négociations diplomatiques
        - Traités et accords
        - Influence diplomatique

        ARGUMENTS :
        - `[pays]` : Optionnel. Pays dont afficher les points diplomatiques (mention, nom ou ID)

        EXEMPLE :
        - `points_d` : Affiche vos propres points diplomatiques
        - `points_d @France` : Affiche les points diplomatiques de la France
        - `points_d 123456789` : Affiche les points diplomatiques du pays avec cet ID
        """,
        hidden=False,
        enabled=True,
        case_insensitive=True,
    )
    @app_commands.autocomplete(target=country_autocomplete)
    async def points_d(
        self,
        ctx,
        target: CountryConverter = commands.parameter(
            default=None,
            description="Pays dont afficher les points diplomatiques (optionnel, votre pays par défaut)",
        ),
    ):
        """Check diplomatic points of a country or user."""
        if target is None:
            target = CountryEntity(ctx.author, ctx.guild).to_dict()
        await self._show_points_generic(
            ctx, target, 2, ":purple_circle:", self.d_points_color_int, 3
        )

    @commands.hybrid_command(
        name="set_pp",
        brief="Définit les points politiques d'un pays à un montant exact (Staff uniquement).",
        usage="set_pp <pays> <montant>",
        description="Définit les points politiques d'un pays à un montant exact, remplaçant le total actuel.",
        help="""Définit les points politiques d'un pays à un montant exact.

        FONCTIONNALITÉ :
        - Remplace complètement les points politiques actuels du pays
        - Définit les nouveaux points politiques au montant spécifié
        - Enregistre l'opération dans les logs économiques avec alerte
        - Vérifie les autorisations staff avant exécution

        RESTRICTIONS :
        - Réservé aux membres du staff uniquement
        - Le pays cible doit être valide
        - Le montant doit être un nombre positif ou zéro

        ARGUMENTS :
        - `<pays>` : Pays dont définir les points politiques (mention, nom ou ID)
        - `<montant>` : Nouveaux points politiques à définir (nombre positif)

        EXEMPLE :
        - `set_pp @France 15` : Définit les points politiques de la France à 15
        - `set_pp Allemagne 20` : Définit les points politiques de l'Allemagne à 20
        """,
        hidden=False,
        enabled=True,
        case_insensitive=True,
    )
    @app_commands.autocomplete(target=country_autocomplete)
    async def set_pp(
        self,
        ctx,
        target: CountryConverter = commands.parameter(
            description="Pays dont définir les points politiques (mention, nom ou ID)"
        ),
        amount: int = commands.parameter(
            description="Nouveaux points politiques à définir (nombre positif)"
        ),
    ):
        """Set political points for a country (Staff only)."""
        await self._set_points_generic(
            ctx, target, amount, 1, ":blue_circle:", self.p_points_color_int
        )

    @commands.hybrid_command(
        name="set_pd",
        brief="Définit les points diplomatiques d'un pays à un montant exact (Staff uniquement).",
        usage="set_pd <pays> <montant>",
        description="Définit les points diplomatiques d'un pays à un montant exact, remplaçant le total actuel.",
        help="""Définit les points diplomatiques d'un pays à un montant exact.

        FONCTIONNALITÉ :
        - Remplace complètement les points diplomatiques actuels du pays
        - Définit les nouveaux points diplomatiques au montant spécifié
        - Enregistre l'opération dans les logs économiques avec alerte
        - Vérifie les autorisations staff avant exécution

        RESTRICTIONS :
        - Réservé aux membres du staff uniquement
        - Le pays cible doit être valide
        - Le montant doit être un nombre positif ou zéro

        ARGUMENTS :
        - `<pays>` : Pays dont définir les points diplomatiques (mention, nom ou ID)
        - `<montant>` : Nouveaux points diplomatiques à définir (nombre positif)

        EXEMPLE :
        - `set_pd @France 8` : Définit les points diplomatiques de la France à 8
        - `set_pd Allemagne 12` : Définit les points diplomatiques de l'Allemagne à 12
        """,
        hidden=False,
        enabled=True,
        case_insensitive=True,
    )
    @app_commands.autocomplete(target=country_autocomplete)
    async def set_pd(
        self,
        ctx,
        target: CountryConverter = commands.parameter(
            description="Pays dont définir les points diplomatiques (mention, nom ou ID)"
        ),
        amount: int = commands.parameter(
            description="Nouveaux points diplomatiques à définir (nombre positif)"
        ),
    ):
        """Set diplomatic points for a country (Staff only)."""
        await self._set_points_generic(
            ctx, target, amount, 2, ":purple_circle:", self.d_points_color_int
        )

    @commands.hybrid_command(
        name="add_pp",
        brief="Ajoute des points politiques à un pays (Staff uniquement).",
        usage="add_pp <pays> <montant>",
        description="Ajoute un montant de points politiques spécifié au total d'un pays.",
        help="""Ajoute des points politiques au total d'un pays spécifié.

        FONCTIONNALITÉ :
        - Ajoute le montant spécifié aux points politiques existants du pays
        - Enregistre l'opération dans les logs économiques avec alerte
        - Vérifie les autorisations staff avant exécution

        UTILITÉ DES POINTS POLITIQUES :
        - Récompense pour bonnes actions internes
        - Compensation pour événements politiques
        - Ajustements d'équilibrage du jeu

        RESTRICTIONS :
        - Réservé aux membres du staff uniquement
        - Le pays cible doit être valide

        ARGUMENTS :
        - `<pays>` : Pays qui recevra les points politiques (mention, nom ou ID)
        - `<montant>` : Montant de points politiques à ajouter (nombre positif)

        EXEMPLE :
        - `add_pp @France 5` : Ajoute 5 points politiques à la France
        - `add_pp Allemagne 10` : Ajoute 10 points politiques à l'Allemagne
        """,
        hidden=False,
        enabled=True,
        case_insensitive=True,
    )
    @app_commands.autocomplete(target=country_autocomplete)
    async def add_pp(
        self,
        ctx,
        target: CountryConverter = commands.parameter(
            description="Pays qui recevra les points politiques (mention, nom ou ID)"
        ),
        amount: int = commands.parameter(
            description="Montant de points politiques à ajouter (nombre positif)"
        ),
    ):
        """Add political points to a country (Staff only)."""
        await self._add_points_generic(
            ctx, target, amount, 1, ":blue_circle:", self.p_points_color_int
        )

    @commands.hybrid_command(
        name="add_pd",
        brief="Ajoute des points diplomatiques à un pays (Staff uniquement).",
        usage="add_pd <pays> <montant>",
        description="Ajoute un montant de points diplomatiques spécifié au total d'un pays.",
        help="""Ajoute des points diplomatiques au total d'un pays spécifié.

        FONCTIONNALITÉ :
        - Ajoute le montant spécifié aux points diplomatiques existants du pays
        - Enregistre l'opération dans les logs économiques avec alerte
        - Vérifie les autorisations staff avant exécution

        UTILITÉ DES POINTS DIPLOMATIQUES :
        - Récompense pour bonnes relations internationales
        - Compensation pour événements diplomatiques
        - Ajustements d'équilibrage du jeu

        RESTRICTIONS :
        - Réservé aux membres du staff uniquement
        - Le pays cible doit être valide

        ARGUMENTS :
        - `<pays>` : Pays qui recevra les points diplomatiques (mention, nom ou ID)
        - `<montant>` : Montant de points diplomatiques à ajouter (nombre positif)

        EXEMPLE :
        - `add_pd @France 3` : Ajoute 3 points diplomatiques à la France
        - `add_pd Allemagne 7` : Ajoute 7 points diplomatiques à l'Allemagne
        """,
        hidden=False,
        enabled=True,
        case_insensitive=True,
    )
    @app_commands.autocomplete(target=country_autocomplete)
    async def add_pd(
        self,
        ctx,
        target: CountryConverter = commands.parameter(
            description="Pays qui recevra les points diplomatiques (mention, nom ou ID)"
        ),
        amount: int = commands.parameter(
            description="Montant de points diplomatiques à ajouter (nombre positif)"
        ),
    ):
        """Add diplomatic points to a country (Staff only)."""
        await self._add_points_generic(
            ctx, target, amount, 2, ":purple_circle:", self.d_points_color_int
        )

    @commands.hybrid_command(
        name="use_pp",
        brief="Utilise des points politiques de votre pays.",
        usage="use_pp [montant]",
        description="Dépense des points politiques de votre pays pour des actions internes.",
        help="""Utilise des points politiques de votre pays pour des actions internes.

        FONCTIONNALITÉ :
        - Retire le montant spécifié de vos points politiques
        - Vérifie que votre pays a suffisamment de points politiques
        - Enregistre l'utilisation dans les logs économiques
        - Montant par défaut : 1 point politique

        UTILISATIONS TYPIQUES :
        - Réformes internes
        - Changements de lois
        - Actions gouvernementales
        - Gestion politique interne

        RESTRICTIONS :
        - Vous devez appartenir à un pays valide
        - Votre pays doit avoir suffisamment de points politiques

        ARGUMENTS :
        - `[montant]` : Optionnel. Nombre de points politiques à utiliser (défaut : 1)

        EXEMPLE :
        - `use_pp` : Utilise 1 point politique
        - `use_pp 3` : Utilise 3 points politiques
        - `use_pp 5` : Utilise 5 points politiques
        """,
        hidden=False,
        enabled=True,
        case_insensitive=True,
    )
    async def use_pp(
        self,
        ctx,
        amount: int = commands.parameter(
            default=1, description="Nombre de points politiques à utiliser (défaut : 1)"
        ),
    ):
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

        await eco_logger("USE_POINTS", payment_amount, country["role"], point_type=1)
        await ctx.send(embed=embed)

    @commands.hybrid_command(
        name="use_pd",
        brief="Utilise des points diplomatiques de votre pays.",
        usage="use_pd [montant]",
        description="Dépense des points diplomatiques de votre pays pour des actions diplomatiques.",
        help="""Utilise des points diplomatiques de votre pays pour des actions diplomatiques.

        FONCTIONNALITÉ :
        - Retire le montant spécifié de vos points diplomatiques
        - Vérifie que votre pays a suffisamment de points diplomatiques
        - Enregistre l'utilisation dans les logs économiques
        - Montant par défaut : 1 point diplomatique

        UTILISATIONS TYPIQUES :
        - Négociations internationales
        - Signature de traités
        - Actions diplomatiques
        - Relations internationales

        RESTRICTIONS :
        - Vous devez appartenir à un pays valide
        - Votre pays doit avoir suffisamment de points diplomatiques

        ARGUMENTS :
        - `[montant]` : Optionnel. Nombre de points diplomatiques à utiliser (défaut : 1)

        EXEMPLE :
        - `use_pd` : Utilise 1 point diplomatique
        - `use_pd 2` : Utilise 2 points diplomatiques
        - `use_pd 4` : Utilise 4 points diplomatiques
        """,
        hidden=False,
        enabled=True,
        case_insensitive=True,
    )
    async def use_pd(
        self,
        ctx,
        amount: int = commands.parameter(
            default=1,
            description="Nombre de points diplomatiques à utiliser (défaut : 1)",
        ),
    ):
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

        await eco_logger("USE_POINTS", payment_amount, country["role"], point_type=2)
        await ctx.send(embed=embed)


async def setup(bot):
    await bot.add_cog(Points(bot))
