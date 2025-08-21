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
    loan_years_autocomplete,
    loan_reference_autocomplete,
    eco_logger,
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
    @app_commands.autocomplete(country=country_autocomplete)
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
        await eco_logger(
            "TRANSFER", payment_amount, author.get("role"), country.get("role")
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
    @app_commands.autocomplete(country=country_autocomplete)
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

        await eco_logger("ADD_MONEY", amount, country.get("role"), ctx.author)
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
    @app_commands.autocomplete(country=country_autocomplete)
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
        await eco_logger(
            "REMOVE_MONEY", payment_amount, country.get("role"), ctx.author
        )
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
    @app_commands.autocomplete(country=country_autocomplete)
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
        await eco_logger("SET_MONEY", amount, country.get("role"), ctx.author)
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
        await eco_logger("PAYMENT", payment_amount, country.get("role"))
        await ctx.send(embed=embed)

    # --- Debt Management Commands ---

    @commands.hybrid_command(
        name="loan",
        brief="Demande un emprunt bancaire selon votre statut géopolitique.",
        usage="loan <amount> <years>",
        description="Contracte un emprunt avec taux d'intérêt basé sur le statut du pays.",
        help="""Demande un emprunt bancaire avec conditions selon votre statut géopolitique.

        FONCTIONNALITÉ :
        - Calcul automatique du taux d'intérêt selon le statut géopolitique
        - Validation de l'éligibilité basée sur le PIB et la stabilité
        - Génération automatique d'une référence unique pour le prêt
        - Ajout immédiat des fonds au trésor national

        TAUX D'INTÉRÊT PAR STATUT :
        - Superpuissance : 0.0% - 1.0%
        - Grande Puissance : 1.0% - 2.0%
        - Puissance majeure : 2.0% - 4.0%
        - Puissance mineure : 4.0% - 6.0%
        - Non Puissance : 6.0% - 10.0%

        CONDITIONS D'ÉLIGIBILITÉ :
        - Le montant total des dettes ne peut excéder 50% du PIB
        - La stabilité du pays doit être supérieure à 20
        - Durée : entre 2 et 5 ans

        ARGUMENTS :
        - `<amount>` : Montant de l'emprunt (entier positif)
        - `<years>` : Durée du prêt en années (2-5 ans)

        EXEMPLES :
        - `loan 1000000 3` : Emprunter 1M sur 3 ans
        - `loan 500000 5` : Emprunter 500K sur 5 ans
        """,
        hidden=False,
        enabled=True,
        case_insensitive=True,
    )
    @app_commands.autocomplete(years=loan_years_autocomplete)
    async def loan(self, ctx, amount: int, years: int):
        """Request a bank loan based on geopolitical status."""
        try:
            # Get country information
            country_entity = CountryEntity(ctx.author, ctx.guild)
            country_id = country_entity.get_country_id()

            if not country_id:
                embed = discord.Embed(
                    title="❌ Erreur",
                    description="Vous devez appartenir à un pays pour demander un emprunt.",
                    color=self.error_color_int,
                )
                return await ctx.send(embed=embed)

            # Validation des paramètres
            if amount <= 0:
                embed = discord.Embed(
                    title="❌ Erreur",
                    description="Le montant de l'emprunt doit être positif.",
                    color=self.error_color_int,
                )
                return await ctx.send(embed=embed)

            if years < 1 or years > 10:
                embed = discord.Embed(
                    title="❌ Erreur",
                    description="La durée de l'emprunt doit être entre 1 et 10 ans.",
                    color=self.error_color_int,
                )
                return await ctx.send(embed=embed)

            # Get country data for eligibility check
            country_dict = country_entity.to_dict()
            country_name = country_dict["name"]

            # Check current debt
            debt_stats = self.db.get_total_debt_by_country(country_id)
            current_debt = debt_stats["total_remaining"]

            # Get GDP for debt capacity check
            gdp = self.db.get_country_gdp(country_id)

            # Check stability
            stability = self.db.get_country_stability(country_id)

            # Eligibility checks
            total_debt_after = current_debt + amount
            if total_debt_after > gdp * 0.5:  # 50% of GDP limit
                embed = discord.Embed(
                    title="❌ Emprunt refusé",
                    description=f"Désolé **{country_name}**, nous ne pouvons vous accorder ce prêt.\n\n"
                    f"**Raison :** Le montant excède votre capacité de 50% de votre PIB.\n"
                    f"**PIB actuel :** {convert(str(gdp))}\n"
                    f"**Dette actuelle :** {convert(str(current_debt))}\n"
                    f"**Limite d'endettement :** {convert(str(int(gdp * 0.5)))}",
                    color=self.error_color_int,
                )
                embed.set_thumbnail(
                    url="https://cdn.discordapp.com/emojis/1163227223109668935.png"
                )
                return await ctx.send(embed=embed)

            if stability < 20:
                embed = discord.Embed(
                    title="❌ Emprunt refusé",
                    description=f"Désolé **{country_name}**, nous ne pouvons vous accorder ce prêt.\n\n"
                    f"**Raison :** Votre stabilité ne permet pas des prêts sans risquer la faillite.\n"
                    f"**Stabilité requise :** 20 minimum\n"
                    f"**Stabilité actuelle :** {stability}",
                    color=self.error_color_int,
                )
                embed.set_thumbnail(
                    url="https://cdn.discordapp.com/emojis/1163227223109668935.png"
                )
                return await ctx.send(embed=embed)

            # Calculate interest rate based on geopolitical status
            power_status = self.db.get_country_power_status(country_id)

            import random

            interest_rates = {
                "Superpuissance": random.uniform(0.0, 1.0),
                "Grande Puissance": random.uniform(1.0, 2.0),
                "Puissance majeure": random.uniform(2.0, 4.0),
                "Puissance mineure": random.uniform(4.0, 6.0),
                "Non Puissance": random.uniform(6.0, 10.0),
            }

            interest_rate = round(interest_rates.get(power_status, 5.0), 2)

            # Calculate total amount to repay
            total_repayment = amount + (amount * interest_rate / 100)
            total_repayment = int(total_repayment)

            # Generate unique reference
            debt_reference = self.db.generate_debt_reference(country_id)

            # Create debt record
            success = self.db.create_debt(
                debt_reference,
                country_id,
                amount,
                total_repayment,
                interest_rate,
                years,
            )

            if not success:
                embed = discord.Embed(
                    title="❌ Erreur",
                    description="Impossible de créer l'enregistrement de dette.",
                    color=self.error_color_int,
                )
                return await ctx.send(embed=embed)

            # Add money to country balance
            self.db.give_balance(country_id, amount)

            # Log the transaction
            await eco_logger(
                "LOAN_TAKEN",
                amount,
                ctx.author,
                extra_data={
                    "reference": debt_reference,
                    "interest_rate": interest_rate,
                    "duration": years,
                },
            )

            # Success response
            embed = discord.Embed(
                title="✅ Emprunt accordé",
                description=f"Votre demande d'emprunt de **{convert(str(amount))}** est acceptée sous ces conditions :",
                color=self.money_color_int,
            )
            embed.add_field(
                name="💰 Montant emprunté", value=convert(str(amount)), inline=True
            )
            embed.add_field(
                name="📈 Taux d'intérêt", value=f"{interest_rate}%", inline=True
            )
            embed.add_field(name="⏰ Durée", value=f"{years} ans", inline=True)
            embed.add_field(
                name="💸 Somme à rembourser",
                value=convert(str(total_repayment)),
                inline=True,
            )
            embed.add_field(
                name="🏷️ Référence du prêt", value=f"`{debt_reference}`", inline=True
            )
            embed.add_field(
                name="🏛️ Statut géopolitique", value=power_status, inline=True
            )
            embed.set_footer(text="Fonds versés immédiatement au trésor national")
            embed.set_thumbnail(
                url="https://cdn.discordapp.com/emojis/1163227223109668935.png"
            )

            await ctx.send(embed=embed)

        except Exception as e:
            embed = discord.Embed(
                title="❌ Erreur",
                description=f"Une erreur s'est produite lors de la demande d'emprunt : {str(e)}",
                color=self.error_color_int,
            )
            await ctx.send(embed=embed)

    @commands.hybrid_command(
        name="check_debt",
        brief="Vérifie les informations d'un emprunt spécifique ou vos emprunts totaux.",
        usage="check_debt [reference]",
        description="Affiche les détails d'un emprunt ou un résumé de tous vos emprunts.",
        help="""Consulte les informations détaillées sur vos emprunts.

        FONCTIONNALITÉ :
        - Sans référence : affiche un résumé de tous vos emprunts
        - Avec référence : affiche les détails complets d'un emprunt spécifique
        - Informations sur les montants, taux et échéances

        ARGUMENTS :
        - `[reference]` : Optionnel. Référence du prêt à consulter

        EXEMPLES :
        - `check_debt` : Résumé de tous vos emprunts
        - `check_debt 123_4567AB` : Détails de l'emprunt spécifique
        """,
        hidden=False,
        enabled=True,
        case_insensitive=True,
    )
    async def check_debt(self, ctx, reference: str = None):
        """Check debt information by reference or show debt summary."""
        try:
            if reference:
                # Show specific debt details
                debt = self.db.get_debt_by_reference(reference)

                if not debt:
                    embed = discord.Embed(
                        title="❌ Emprunt introuvable",
                        description=f"L'emprunt avec la référence `{reference}` n'a pas été trouvé.",
                        color=self.error_color_int,
                    )
                    return await ctx.send(embed=embed)

                embed = discord.Embed(
                    title="📋 Détails de l'emprunt",
                    description=f"Informations pour l'emprunt `{reference}`",
                    color=self.money_color_int,
                )
                embed.add_field(
                    name="🏛️ Pays contracteur", value=debt["country_name"], inline=True
                )
                embed.add_field(
                    name="💰 Somme empruntée",
                    value=convert(str(debt["original_amount"])),
                    inline=True,
                )
                embed.add_field(
                    name="📈 Taux d'intérêt",
                    value=f"{debt['interest_rate']}%",
                    inline=True,
                )
                embed.add_field(
                    name="⏰ Durée", value=f"{debt['max_years']} ans", inline=True
                )
                embed.add_field(
                    name="💸 Somme à rembourser",
                    value=convert(str(debt["remaining_amount"])),
                    inline=True,
                )
                embed.add_field(
                    name="📅 Date de création",
                    value=debt["created_at"][:10],
                    inline=True,
                )
                embed.set_thumbnail(
                    url="https://cdn.discordapp.com/emojis/1163227223109668935.png"
                )

            else:
                # Show debt summary for the user's country
                country_entity = CountryEntity(ctx.author, ctx.guild)
                country_id = country_entity.get_country_id()

                if not country_id:
                    embed = discord.Embed(
                        title="❌ Erreur",
                        description="Vous devez appartenir à un pays pour consulter les emprunts.",
                        color=self.error_color_int,
                    )
                    return await ctx.send(embed=embed)

                debt_stats = self.db.get_total_debt_by_country(country_id)
                country_dict = country_entity.to_dict()

                embed = discord.Embed(
                    title="📊 Résumé des emprunts",
                    description=f"État des emprunts pour **{country_dict['name']}**",
                    color=self.money_color_int,
                )
                embed.add_field(
                    name="📈 Nombre d'emprunts",
                    value=str(debt_stats["debt_count"]),
                    inline=True,
                )
                embed.add_field(
                    name="💰 Total emprunté",
                    value=convert(str(debt_stats["total_borrowed"])),
                    inline=True,
                )
                embed.add_field(
                    name="💸 Total à rembourser",
                    value=convert(str(debt_stats["total_remaining"])),
                    inline=True,
                )
                embed.set_thumbnail(
                    url="https://cdn.discordapp.com/emojis/1163227223109668935.png"
                )

            await ctx.send(embed=embed)

        except Exception as e:
            embed = discord.Embed(
                title="❌ Erreur",
                description=f"Une erreur s'est produite : {str(e)}",
                color=self.error_color_int,
            )
            await ctx.send(embed=embed)

    @commands.hybrid_command(
        name="repay_debt",
        brief="Rembourse tout ou partie d'un emprunt.",
        usage="repay_debt <reference> [amount]",
        description="Effectue un remboursement total ou partiel d'un emprunt existant.",
        help="""Rembourse un emprunt existant de manière totale ou partielle.

        FONCTIONNALITÉ :
        - Remboursement partiel ou total d'un emprunt
        - Suppression automatique de l'emprunt si entièrement remboursé
        - Vérification automatique des fonds disponibles
        - Mise à jour instantanée du solde

        ARGUMENTS :
        - `<reference>` : Référence du prêt à rembourser
        - `[amount]` : Optionnel. Montant à rembourser (défaut : totalité)

        EXEMPLES :
        - `repay_debt 123_4567AB` : Remboursement total
        - `repay_debt 123_4567AB 500000` : Remboursement partiel de 500K
        """,
        hidden=False,
        enabled=True,
        case_insensitive=True,
    )
    @app_commands.autocomplete(reference=loan_reference_autocomplete)
    async def repay_debt(self, ctx, reference: str, amount: int = 0):
        """Repay a debt partially or fully."""
        try:
            # Get country information
            country_entity = CountryEntity(ctx.author, ctx.guild)
            country_id = country_entity.get_country_id()

            if not country_id:
                embed = discord.Embed(
                    title="❌ Erreur",
                    description="Vous devez appartenir à un pays pour rembourser un emprunt.",
                    color=self.error_color_int,
                )
                return await ctx.send(embed=embed)

            # Check if debt exists
            debt = self.db.get_debt_by_reference(reference)

            if not debt:
                embed = discord.Embed(
                    title="❌ Emprunt introuvable",
                    description=f"L'emprunt avec la référence `{reference}` n'a pas été trouvé.",
                    color=self.error_color_int,
                )
                return await ctx.send(embed=embed)

            # Verify the debt belongs to the user's country
            if debt["country_id"] != country_id:
                embed = discord.Embed(
                    title="❌ Accès refusé",
                    description="Vous ne pouvez rembourser que les emprunts de votre propre pays.",
                    color=self.error_color_int,
                )
                return await ctx.send(embed=embed)

            # Determine repayment amount
            remaining_debt = debt["remaining_amount"]
            repayment_amount = (
                remaining_debt if amount == 0 or amount >= remaining_debt else amount
            )

            if repayment_amount <= 0:
                embed = discord.Embed(
                    title="❌ Erreur",
                    description="Le montant de remboursement doit être positif.",
                    color=self.error_color_int,
                )
                return await ctx.send(embed=embed)

            # Check if country has enough money
            if not self.db.has_enough_balance(country_id, repayment_amount):
                current_balance = self.db.get_balance(country_id)
                embed = discord.Embed(
                    title="❌ Fonds insuffisants",
                    description=f"Impossible de rembourser {convert(str(repayment_amount))}.\n\n"
                    f"**Solde actuel :** {convert(str(current_balance))}\n"
                    f"**Montant requis :** {convert(str(repayment_amount))}",
                    color=self.error_color_int,
                )
                return await ctx.send(embed=embed)

            # Process repayment
            self.db.take_balance(country_id, repayment_amount)
            success = self.db.update_debt_amount(reference, repayment_amount)

            if not success:
                # Refund the money if debt update failed
                self.db.give_balance(country_id, repayment_amount)
                embed = discord.Embed(
                    title="❌ Erreur",
                    description="Impossible de traiter le remboursement.",
                    color=self.error_color_int,
                )
                return await ctx.send(embed=embed)

            # Log the transaction
            await eco_logger(
                "LOAN_REPAID",
                repayment_amount,
                ctx.author,
                extra_data={"reference": reference},
            )

            # Success response
            is_full_repayment = repayment_amount >= remaining_debt
            remaining_after = max(0, remaining_debt - repayment_amount)

            embed = discord.Embed(
                title="✅ Remboursement effectué",
                description=f"Remboursement de **{convert(str(repayment_amount))}** effectué avec succès.",
                color=self.money_color_int,
            )
            embed.add_field(name="🏷️ Référence", value=f"`{reference}`", inline=True)
            embed.add_field(
                name="💸 Montant remboursé",
                value=convert(str(repayment_amount)),
                inline=True,
            )
            embed.add_field(
                name="📊 Statut",
                value=(
                    "Entièrement remboursé"
                    if is_full_repayment
                    else f"Reste : {convert(str(remaining_after))}"
                ),
                inline=True,
            )
            embed.set_thumbnail(
                url="https://cdn.discordapp.com/emojis/1163227223109668935.png"
            )

            await ctx.send(embed=embed)

        except Exception as e:
            embed = discord.Embed(
                title="❌ Erreur",
                description=f"Une erreur s'est produite lors du remboursement : {str(e)}",
                color=self.error_color_int,
            )
            await ctx.send(embed=embed)

    @commands.hybrid_command(
        name="list_debts",
        brief="Affiche la liste détaillée des emprunts d'un pays.",
        usage="list_debts [country]",
        description="Liste tous les emprunts actifs d'un pays avec leurs détails.",
        help="""Affiche la liste complète des emprunts d'un pays.

        FONCTIONNALITÉ :
        - Liste tous les emprunts actifs d'un pays
        - Affiche les références, montants et échéances
        - Triés par montant restant décroissant
        - Informations détaillées pour chaque emprunt

        ARGUMENTS :
        - `[country]` : Optionnel. Pays à consulter (défaut : votre pays)

        EXEMPLES :
        - `list_debts` : Vos emprunts
        - `list_debts @France` : Emprunts de la France
        """,
        hidden=False,
        enabled=True,
        case_insensitive=True,
    )
    @app_commands.autocomplete(country=country_autocomplete)
    async def list_debts(self, ctx, country: CountryConverter = None):
        """List all debts for a country."""
        try:
            if country is None:
                # Use the author's country
                country_entity = CountryEntity(ctx.author, ctx.guild)
                country_id = country_entity.get_country_id()

                if not country_id:
                    embed = discord.Embed(
                        title="❌ Erreur",
                        description="Vous devez appartenir à un pays ou spécifier un pays à consulter.",
                        color=self.error_color_int,
                    )
                    return await ctx.send(embed=embed)

                country_dict = country_entity.to_dict()
            else:
                # Use the specified country
                country_entity = CountryEntity(country, ctx.guild)
                country_id = country_entity.get_country_id()
                country_dict = country_entity.to_dict()

            # Get all debts for the country
            debts = self.db.get_debts_by_country(country_id)

            if not debts:
                embed = discord.Embed(
                    title="📊 Liste des emprunts",
                    description=f"**{country_dict['name']}** n'a aucun emprunt actif.",
                    color=self.money_color_int,
                )
                embed.set_thumbnail(
                    url="https://cdn.discordapp.com/emojis/1163227223109668935.png"
                )
                return await ctx.send(embed=embed)

            # Create the embed with debt list
            embed = discord.Embed(
                title="📊 Liste des emprunts",
                description=f"Emprunts actifs de **{country_dict['name']}**",
                color=self.money_color_int,
            )

            debt_list = []
            for debt in debts:
                debt_info = (
                    f"**🏷️ Référence :** `{debt['debt_reference']}`\n"
                    f"**💸 Montant à rembourser :** {convert(str(debt['remaining_amount']))}\n"
                    f"**📈 Taux :** {debt['interest_rate']}% | **⏰ Durée :** {debt['max_years']} ans\n"
                )
                debt_list.append(debt_info)

            # Split into multiple embeds if too long
            debt_text = "\n".join(debt_list)

            if len(debt_text) > 2000:
                # Split the list for multiple embeds
                embed.add_field(
                    name=f"📋 {len(debts)} emprunt(s) trouvé(s)",
                    value="Liste trop longue, utilisez `check_debt <référence>` pour les détails.",
                    inline=False,
                )
            else:
                embed.add_field(
                    name=f"📋 {len(debts)} emprunt(s) trouvé(s)",
                    value=debt_text,
                    inline=False,
                )

            # Add summary
            debt_stats = self.db.get_total_debt_by_country(country_id)
            embed.add_field(
                name="📊 Résumé",
                value=f"**Total à rembourser :** {convert(str(debt_stats['total_remaining']))}",
                inline=False,
            )
            embed.set_thumbnail(
                url="https://cdn.discordapp.com/emojis/1163227223109668935.png"
            )

            await ctx.send(embed=embed)

        except Exception as e:
            embed = discord.Embed(
                title="❌ Erreur",
                description=f"Une erreur s'est produite : {str(e)}",
                color=self.error_color_int,
            )
            await ctx.send(embed=embed)


async def setup(bot):
    """Setup function to add the cog to the bot."""
    await bot.add_cog(Economy(bot))
