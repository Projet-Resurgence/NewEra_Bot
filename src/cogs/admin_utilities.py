"""
AdminUtilities cog for NEBot.
Contains all administrative utility commands.
"""

import discord
from discord.ext import commands
import asyncio
import aiohttp
import contextlib
import io
import json
from typing import Union
from datetime import datetime, timedelta, timezone

from shared_utils import (
    get_db,
    get_discord_utils,
    ERROR_COLOR_INT as error_color_int,
)
from text_formatting import convert_country_name_channel
from removebg import RemoveBg
from dotenv import dotenv_values
from groq import Groq

# Initialize removebg
removebg_apikey = dotenv_values(".env")["REMOVEBG_API_KEY"]
rmbg = RemoveBg(removebg_apikey, "error.log")

# Global variables that need to be accessible
groq_chat_history = []
last_groq_query_time = datetime.now(timezone.utc)


class AdminUtilities(commands.Cog):
    """Administrative utility commands for bot management and moderation."""

    def __init__(self, bot):
        self.bot = bot
        self.db = get_db()
        self.dUtils = get_discord_utils(bot, self.db)

        # Access global variables from main
        self.bi_admins_id = []
        self.Erreurs = {}
        self.continents_dict = {}
        self.usefull_role_ids_dic = {}
        self.groq_client = None

        # Load these from main.py when the cog is ready
        self._load_global_data()
        self._init_groq_client()

    def _init_groq_client(self):
        """Initialize Groq client."""
        try:
            from groq import Groq

            groq_api_key = dotenv_values(".env").get("GROQ_API_KEY")
            if groq_api_key:
                self.groq_client = Groq(api_key=groq_api_key)
        except Exception as e:
            print(f"Failed to initialize Groq client: {e}")
            self.groq_client = None

    def _load_global_data(self):
        """Load global data from JSON file instead of importing main."""
        try:
            import json

            with open("datas/main.json", "r") as f:
                json_data = json.load(f)
                self.bi_admins_id = json_data.get("bi_admins_id", [])
                self.Erreurs = json_data.get("Erreurs", {})
                self.continents_dict = json_data.get("continents_dict", {})
                self.usefull_role_ids_dic = json_data.get("usefull_role_ids_dic", {})
        except Exception as e:
            print(f"Failed to load global data from JSON: {e}")
            # Use default empty values if loading fails
            pass

    def get_query_level(self, user_id):
        """Get the query level for a user."""
        if user_id in self.bi_admins_id:
            return "admin"
        return "user"

    async def ask_groq(self, user_message: str, level: str = "user") -> str:
        """Ask Groq AI a question."""
        from context import get_server_context

        max_tokens = {"user": 400, "trusted": 800, "mod": 2000, "admin": 8000}.get(
            level, 400
        )

        system_prompt = (
            "Tu es une IA destinée à assister un jeu de rôle géopolitique post-apocalyptique se déroulant en 2045, appelé Nouvelle Ère V4. "
            "Tu ne poses jamais de questions. Tu ne dis jamais 'je suis prêt à vous aider'. "
            "Tu ne fais jamais de compliments ou d'intros inutiles. "
            "Tu dois répondre uniquement aux questions ou suggestions posées, de manière concise, précise, et thématiquement cohérente avec l'univers. "
            "Utilise toujours un ton professionnel, froid et informatif. Évite les expressions comme 'bien sûr', 'nous pouvons', 'je suppose que'."
        )
        system_prompt += "\n" + get_server_context()
        messages = [{"role": "system", "content": system_prompt}]

        # Ajout de l'historique
        global groq_chat_history
        for user_msg, bot_reply in groq_chat_history[
            -5:
        ]:  # Ne pas envoyer trop de contexte
            messages.append({"role": "user", "content": user_msg})
            messages.append({"role": "assistant", "content": bot_reply})

        # Ajoute la nouvelle requête
        messages.append({"role": "user", "content": user_message})

        chat_completion = self.groq_client.chat.completions.create(
            messages=messages, model="llama-3.3-70b-versatile", max_tokens=max_tokens
        )

        content = chat_completion.choices[0].message.content
        groq_chat_history.append((user_message, content))
        return content

    @commands.command(
        name="reload_cogs",
        brief="Recharge tous les cogs du bot.",
        usage="reload_cogs",
        description="Recharge ou charge tous les cogs principaux du bot (Economy, Points, Structures, AdminUtilities).",
        help="""Recharge tous les cogs du bot pour appliquer les modifications sans redémarrer le bot.

        FONCTIONNALITÉ :
        - Tente de recharger les cogs s'ils sont déjà chargés
        - Les charge s'ils ne sont pas encore chargés
        - Affiche un message de confirmation ou d'erreur

        RESTRICTIONS :
        - Réservé aux administrateurs uniquement

        EXEMPLE :
        - `reload_cogs` : Recharge tous les cogs principaux du bot
        """,
        hidden=False,
        enabled=True,
        case_insensitive=True,
    )
    @commands.has_permissions(administrator=True)
    async def reload_cogs(self, ctx):
        """Reload all cogs (Admin only)."""
        try:
            # Try to reload, if not loaded then load it
            try:
                await self.bot.reload_extension("cogs.economy")
                await self.bot.reload_extension("cogs.points")
                await self.bot.reload_extension("cogs.structures")
                await self.bot.reload_extension("cogs.admin_utilities")
                await ctx.send(
                    "✅ Economy, Points, Structures and AdminUtilities cogs reloaded successfully!"
                )
            except commands.ExtensionNotLoaded:
                await self.bot.load_extension("cogs.economy")
                await self.bot.load_extension("cogs.points")
                await self.bot.load_extension("cogs.structures")
                await self.bot.load_extension("cogs.admin_utilities")
                await ctx.send(
                    "✅ Economy, Points, Structures and AdminUtilities cogs loaded successfully!"
                )
        except Exception as e:
            await ctx.send(f"❌ Failed to reload/load cogs: {e}")

    @commands.command(
        name="list_cogs",
        brief="Affiche tous les cogs chargés et leurs commandes.",
        usage="list_cogs",
        description="Liste toutes les extensions chargées du bot et leurs commandes associées.",
        help="""Affiche un récapitulatif complet des cogs et commandes du bot.

        INFORMATIONS AFFICHÉES :
        - Liste des extensions chargées
        - Commandes groupées par cog
        - Statut de chargement de chaque extension

        RESTRICTIONS :
        - Réservé aux administrateurs uniquement

        EXEMPLE :
        - `list_cogs` : Affiche tous les cogs et leurs commandes
        """,
        hidden=False,
        enabled=True,
        case_insensitive=True,
    )
    @commands.has_permissions(administrator=True)
    async def list_cogs(self, ctx):
        """List all loaded cogs and their commands (Admin only)."""
        loaded_extensions = list(self.bot.extensions.keys())

        embed = discord.Embed(title="🔧 Loaded Extensions & Commands", color=0x00FF00)

        if loaded_extensions:
            embed.add_field(
                name="📦 Loaded Extensions",
                value="\n".join(loaded_extensions) or "None",
                inline=False,
            )

        # Group commands by cog
        cog_commands = {}
        for command in self.bot.commands:
            cog_name = command.cog_name or "No Cog"
            if cog_name not in cog_commands:
                cog_commands[cog_name] = []
            cog_commands[cog_name].append(command.name)

        for cog_name, commands in cog_commands.items():
            embed.add_field(
                name=f"⚙️ {cog_name}",
                value=", ".join(commands) or "No commands",
                inline=False,
            )

        await ctx.send(embed=embed)

    @commands.command(
        name="execute_cmd",
        brief="Exécute du code Python.",
        usage="execute_cmd <code>",
        description="Exécute du code Python directement depuis Discord.",
        help="""Exécute du code Python et affiche le résultat.

        FONCTIONNALITÉ :
        - Exécute le code fourni en paramètre
        - Capture et affiche la sortie
        - Envoie un fichier si le résultat est trop long

        RESTRICTIONS :
        - Réservé au propriétaire du bot uniquement
        - Utilisation dangereuse - à manipuler avec précaution

        ARGUMENTS :
        - `<code>` : Le code Python à exécuter

        EXEMPLE :
        - `execute_cmd print("Hello World")` : Exécute et affiche "Hello World"
        """,
        hidden=False,
        enabled=True,
        case_insensitive=True,
    )
    async def execute_cmd(
        self, 
        ctx, 
        *, 
        code: str = commands.parameter(
            description="Le code Python à exécuter"
        )
    ):
        """Execute Python code (Owner only)."""
        if ctx.author.id != 293869524091142144:
            await ctx.reply("You do not have the required role to use this command.")
            return
        try:
            # Créer un tampon pour capturer la sortie
            buffer = io.StringIO()
            with contextlib.redirect_stdout(buffer):
                # Exécuter le code fourni
                exec(code)
            output = buffer.getvalue()

            if not output:
                output = "L'exécution s'est terminée sans produire de sortie."

            if len(output) > 2000:
                await ctx.send(
                    "Le résultat est trop long, voici le fichier contenant l'output :",
                    file=discord.File(io.StringIO(output), filename="output.txt"),
                )
            else:
                await ctx.send(
                    f"**Résultat de l'exécution :**\n```python\n{output}\n```"
                )

        except Exception as e:
            await ctx.send(
                f"**Une erreur est survenue lors de l'exécution du code :**\n```python\n{e}\n```"
            )

    @commands.command(
        name="del_betw",
        brief="Supprime les messages entre deux messages spécifiés.",
        usage="del_betw <message_base> <message_cible>",
        description="Supprime tous les messages situés entre deux messages donnés.",
        help="""Supprime tous les messages entre deux messages spécifiés.

        FONCTIONNALITÉ :
        - Supprime jusqu'à 1000 messages entre les deux points
        - Affiche le nombre de messages supprimés
        - Vérifie que les messages sont dans le même salon

        RESTRICTIONS :
        - Réservé aux super-administrateurs uniquement
        - Les messages doivent être dans le salon actuel

        ARGUMENTS :
        - `<message_base>` : Message de début (non inclus)
        - `<message_cible>` : Message de fin (non inclus)

        EXEMPLE :
        - `del_betw 123456789 987654321` : Supprime les messages entre ces deux IDs
        """,
        hidden=False,
        enabled=True,
        case_insensitive=True,
    )
    async def del_betw(
        self, 
        ctx, 
        base_message: discord.Message = commands.parameter(
            description="Message de début (les messages après celui-ci seront supprimés)"
        ), 
        reach_message: discord.Message = commands.parameter(
            description="Message de fin (les messages avant celui-ci seront supprimés)"
        )
    ):
        """Delete messages between two specified messages."""
        if not ctx.author.id in self.bi_admins_id:
            embed = discord.Embed(
                title="Vous n'êtes pas autorisé à effectuer cette commande.",
                description=f"{self.Erreurs.get('Erreur ', '')}",
                color=error_color_int,
            )
            await ctx.send(embed=embed)
            return
        if (
            not reach_message.channel.id == ctx.channel.id
            or not base_message.channel.id == ctx.channel.id
        ):
            await ctx.send(
                "Erreur : Vous n'êtes pas dans le salon des messages à supprimer"
            )
        deleted = await ctx.channel.purge(
            limit=1000, before=base_message, after=reach_message
        )
        await ctx.channel.send(f"J'ai supprimé {len(deleted)} message(s)")

    @commands.command(
        name="del_til",
        brief="Supprime tous les messages depuis un message spécifié jusqu'au plus récent.",
        usage="del_til <message_cible>",
        description="Supprime tous les messages postés après le message spécifié.",
        help="""Supprime tous les messages postés après un message donné.

        FONCTIONNALITÉ :
        - Supprime jusqu'à 1000 messages après le message spécifié
        - Affiche le nombre de messages supprimés
        - Vérifie que le message est dans le salon actuel

        RESTRICTIONS :
        - Réservé aux super-administrateurs uniquement
        - Le message doit être dans le salon actuel

        ARGUMENTS :
        - `<message_cible>` : Message à partir duquel supprimer (non inclus)

        EXEMPLE :
        - `del_til 123456789` : Supprime tous les messages postés après ce message
        """,
        hidden=False,
        enabled=True,
        case_insensitive=True,
    )
    async def del_til(
        self, 
        ctx, 
        reach_message: discord.Message = commands.parameter(
            description="Message à partir duquel supprimer tous les messages suivants"
        )
    ):
        """Delete messages from a specified message to the most recent."""
        if not ctx.author.id in self.bi_admins_id:
            embed = discord.Embed(
                title="Vous n'êtes pas autorisé à effectuer cette commande.",
                description=f"{self.Erreurs.get('Erreur ', '')}",
                color=error_color_int,
            )
            await ctx.send(embed=embed)
            return
        if not reach_message.channel.id == ctx.channel.id:
            await ctx.send(
                "Erreur : Vous n'êtes pas dans le salon des messages à supprimer"
            )
        deleted = await ctx.channel.purge(limit=1000, after=reach_message)
        await ctx.channel.send(f"J'ai supprimé {len(deleted)} message(s)")

    @commands.command(
        name="reformat_emoji",
        brief="Reformate un emoji en lui assignant un nouveau nom, et optionnellement, enlève son arrière-plan.",
        usage="reformat_emoji <emoji> <nouveau_nom> [del_bg]",
        description="Reformate l'emoji spécifié avec un nouveau nom. Peut également supprimer l'arrière-plan si `del_bg` est activé.",
        help="""Reformate un emoji en changeant son nom et en enlevant, si demandé, l'arrière-plan.

        ARGUMENTS :
        - `<emoji>` : L'emoji à reformater (mention ou ID).
        - `<new_name>` : Nouveau nom de l'emoji. S'il ne commence pas par "NE_", ce préfixe sera ajouté automatiquement.
        - `[del_bg]` : Optionnel. Indique si l'arrière-plan de l'emoji doit être supprimé (True/False). Si activé, utilise une API pour reformater l'image sans fond.

        EXEMPLE :
        - `reformat_emoji :smile: smile_new` : Change le nom de l'emoji `:smile:` en `NE_smile_new`.
        - `reformat_emoji :smile: smile_no_bg True` : Change le nom de l'emoji `:smile:` en `NE_smile_no_bg` et enlève l'arrière-plan.
        """,
        hidden=False,
        enabled=True,
        case_insensitive=True,
    )
    async def reformat_emoji(
        self,
        ctx,
        emoji: discord.Emoji = commands.parameter(
            description="L'emoji à reformater (mention ou ID)"
        ),
        new_name: str = commands.parameter(
            description="Nouveau nom de l'emoji. Ajoute automatiquement le préfixe `NE_` si absent."
        ),
        del_bg: bool = commands.parameter(
            description="Optionnel. Si True, enlève l'arrière-plan de l'emoji."
        ),
    ) -> None:
        """Reformat an emoji with a new name and optionally remove background."""
        image_url = emoji.url
        if not new_name.startswith("NE_"):
            new_name = "NE_" + new_name
        new_file_name = new_name + ".png"

        if del_bg:
            rmbg.remove_background_from_img_url(image_url, new_file_name=new_file_name)
            await emoji.delete(reason=f"Reformatage de l'emoji {emoji.name}")
            with open(new_file_name, "rb") as image:
                image_data = image.read()
                emoji = await ctx.guild.create_custom_emoji(
                    image=image_data,
                    name=new_name,
                    reason=f"Reformatage de l'emoji {emoji.name}",
                )
        else:
            await emoji.edit(
                name=new_name, reason=f"Reformatage de l'emoji {emoji.name}"
            )

        await ctx.send(
            f"{ctx.message.author.mention} J'ai reformatté l'emoji en <:{new_name}:{emoji.id}> pour le serveur."
        )

    async def cat_syncer(self, ctx, cat: discord.CategoryChannel):
        """Helper function to sync category permissions."""
        if ctx.author.id not in self.bi_admins_id:
            return await ctx.send("Non.")
        for i in cat.channels:
            if i.overwrites == cat.overwrites:
                continue
            await i.edit(sync_permissions=True)
            await asyncio.sleep(2)
        await ctx.send("Fait")

    @commands.command(
        name="sync_channels",
        brief="Synchronise les permissions entre deux salons.",
        usage="sync_channels <salon_à_synchroniser> <salon_modèle>",
        description="Copie les permissions d'un salon modèle vers un salon cible.",
        help="""Synchronise les permissions entre deux salons.

        FONCTIONNALITÉ :
        - Copie toutes les permissions du salon modèle
        - Applique ces permissions au salon cible
        - Fonctionne avec tous types de salons (texte, vocal, forum, scène)

        RESTRICTIONS :
        - Réservé aux super-administrateurs uniquement

        ARGUMENTS :
        - `<salon_à_synchroniser>` : Salon qui recevra les nouvelles permissions
        - `<salon_modèle>` : Salon dont les permissions seront copiées

        EXEMPLE :
        - `sync_channels #salon-cible #salon-modele` : Copie les permissions du salon-modèle vers salon-cible
        """,
        hidden=False,
        enabled=True,
        case_insensitive=True,
    )
    async def sync_channels(
        self,
        ctx,
        chan_to_sync: Union[
            discord.TextChannel,
            discord.VoiceChannel,
            discord.ForumChannel,
            discord.StageChannel,
        ] = commands.parameter(
            description="Salon qui recevra les nouvelles permissions"
        ),
        model_chan: Union[
            discord.TextChannel,
            discord.VoiceChannel,
            discord.ForumChannel,
            discord.StageChannel,
        ] = commands.parameter(
            description="Salon modèle dont les permissions seront copiées"
        ),
    ):
        """Sync permissions between two channels."""
        if ctx.author.id not in self.bi_admins_id:
            return await ctx.send("Non.")
        new_permissions = model_chan.overwrites
        await chan_to_sync.edit(overwrites=new_permissions)
        await ctx.send("Fait")

    @commands.command(
        name="sync_cats",
        brief="Synchronise les permissions entre deux catégories et leurs salons.",
        usage="sync_cats <catégorie_à_synchroniser> <catégorie_modèle>",
        description="Copie les permissions d'une catégorie modèle vers une catégorie cible et synchronise tous ses salons.",
        help="""Synchronise les permissions entre deux catégories et leurs salons.

        FONCTIONNALITÉ :
        - Copie les permissions de la catégorie modèle
        - Applique ces permissions à la catégorie cible
        - Synchronise automatiquement tous les salons de la catégorie cible
        - Ajoute un délai de 2 secondes entre chaque salon pour éviter la limite de taux

        RESTRICTIONS :
        - Réservé aux super-administrateurs uniquement

        ARGUMENTS :
        - `<catégorie_à_synchroniser>` : Catégorie qui recevra les nouvelles permissions
        - `<catégorie_modèle>` : Catégorie dont les permissions seront copiées

        EXEMPLE :
        - `sync_cats "Catégorie Cible" "Catégorie Modèle"` : Synchronise les permissions entre les catégories
        """,
        hidden=False,
        enabled=True,
        case_insensitive=True,
    )
    async def sync_cats(
        self,
        ctx,
        cat_to_sync: discord.CategoryChannel = commands.parameter(
            description="Catégorie qui recevra les nouvelles permissions"
        ),
        model_cat: discord.CategoryChannel = commands.parameter(
            description="Catégorie modèle dont les permissions seront copiées"
        ),
    ):
        """Sync permissions between two categories."""
        if ctx.author.id not in self.bi_admins_id:
            return await ctx.send("Non.")
        await cat_to_sync.edit(overwrites=model_cat.overwrites)
        await self.cat_syncer(ctx, cat_to_sync)
        await ctx.send("Fait")

    @commands.command(
        name="reformat_rp_channels",
        brief="Reformate les noms des salons RP selon les conventions.",
        usage="reformat_rp_channels",
        description="Applique le formatage standard aux noms des salons RP dans toutes les catégories de continents.",
        help="""Reformate automatiquement les noms des salons RP.

        FONCTIONNALITÉ :
        - Parcourt tous les salons des catégories de continents
        - Applique le formatage standard aux noms de salons
        - Affiche un aperçu des changements avant application
        - Respecte les conventions de nommage du serveur

        RESTRICTIONS :
        - Réservé aux super-administrateurs uniquement
        - Actuellement en mode aperçu (ne renomme pas réellement)

        EXEMPLE :
        - `reformat_rp_channels` : Formate tous les salons RP selon les conventions
        """,
        hidden=False,
        enabled=True,
        case_insensitive=True,
    )
    async def reformat_rp_channels(self, ctx):
        """Reformat RP channel names."""
        if ctx.author.id not in self.bi_admins_id:
            return await ctx.send("Non.")
        for continent_cat in self.continents_dict.values():
            continent_cat = discord.utils.get(
                ctx.guild.categories, id=int(continent_cat)
            )
            for channel in continent_cat.channels:
                new_name = convert_country_name_channel(channel.name)
                if new_name == channel.name:
                    continue
                await ctx.send(f"{channel.name} => {new_name}")
                # await channel.edit(name=new_name)
        await ctx.send("Fait")

    @commands.command(
        name="send_rules",
        brief="Envoie les règles du serveur via un webhook.",
        usage="send_rules <url_webhook>",
        description="Publie toutes les règles du serveur (HRP, RP, militaires, territoriales) via un webhook et annonce leur publication.",
        help="""Envoie un ensemble complet de règles via webhook.

        FONCTIONNALITÉ :
        - Lit les fichiers de règles depuis le dossier rules/
        - Envoie les règles HRP, RP, militaires et territoriales
        - Crée un résumé avec des liens vers chaque section
        - Publie une annonce dans le salon d'annonces
        - Supprime automatiquement le message de commande

        FICHIERS UTILISÉS :
        - rules/hrp.json : Règles hors-roleplay
        - rules/rp.json : Règles de roleplay
        - rules/military.json : Règles militaires
        - rules/territorial.json : Règles territoriales
        - rules/summary.json : Résumé des règles
        - rules/announcing.json : Message d'annonce

        RESTRICTIONS :
        - Réservé aux super-administrateurs uniquement

        ARGUMENTS :
        - `<url_webhook>` : URL du webhook Discord où publier les règles

        EXEMPLE :
        - `send_rules https://discord.com/api/webhooks/...` : Publie les règles via le webhook
        """,
        hidden=False,
        enabled=True,
        case_insensitive=True,
    )
    async def send_rules(
        self, 
        ctx, 
        webhook_url: str = commands.parameter(
            description="URL du webhook Discord où publier les règles"
        )
    ):
        """Send rules to a webhook URL."""
        if ctx.author.id not in self.bi_admins_id:
            return await ctx.send("Non.")

        rules = {
            "hrp": "hrp.json",
            "rp": "rp.json",
            "military": "military.json",
            "territorial": "territorial.json",
        }

        rules_webhooks = {}
        summary_links = []
        summary_embeds = []
        rules_titles = {}

        # Lire et parser chaque fichier de règles
        for rule in rules.values():
            with open(f"rules/{rule}", "r") as file:
                r_file = file.read()
                rules_webhooks[rule] = list(
                    self.dUtils.parse_embed_json(r_file)
                )  # Convertir en liste d'embeds
                rules_titles[rule] = json.loads(r_file)["content"]

        # Lire les embeds pour le résumé
        with open("rules/summary.json", "r") as file:
            summary_embeds = list(self.dUtils.parse_embed_json(file.read()))

        # Utiliser la session aiohttp pour envoyer les webhooks
        async with aiohttp.ClientSession() as session:
            webhook = discord.Webhook.from_url(webhook_url, session=session)

            # Envoyer les règles et récupérer les liens d'embed
            for rule_title, rule_embeds in zip(
                rules_titles.values(), rules_webhooks.values()
            ):
                await webhook.send(
                    content=rule_title,
                    username=self.bot.user.name,
                    avatar_url=self.bot.user.avatar.url,
                    wait=True,
                )
                embeds_to_send = []
                for embed in rule_embeds:
                    embeds_to_send.append(
                        await webhook.send(
                            embed=embed,
                            username=self.bot.user.name,
                            avatar_url=self.bot.user.avatar.url,
                            wait=True,
                        )
                    )
                    # await asyncio.sleep(1)  # Si tu veux vraiment un délai
                summary_links.append(embeds_to_send[0].jump_url)
                await webhook.send(
                    content="``` ```",
                    username=self.bot.user.name,
                    avatar_url=self.bot.user.avatar.url,
                )

            # Envoyer les embeds du résumé avec les URLs ajoutées

            await webhook.send(
                embed=summary_embeds[0],
                username=self.bot.user.name,
                avatar_url=self.bot.user.avatar.url,
            )
            for i, sum_embed in enumerate(summary_embeds[1:]):
                if i < len(summary_links):
                    sum_embed.url = summary_links[
                        i
                    ]  # Ajouter les URLs récupérées précédemment

                await webhook.send(
                    embed=sum_embed,
                    username=self.bot.user.name,
                    avatar_url=self.bot.user.avatar.url,
                )
                await asyncio.sleep(1)  # Si nécessaire
        announce_channel = discord.utils.get(ctx.guild.channels, id=873645600183287859)
        with open("rules/announcing.json", "r") as file:
            announce_embed = discord.Embed().from_dict(json.loads(file.read()))
        await announce_channel.send(embed=announce_embed)
        await announce_channel.send("@everyone")
        await ctx.message.delete()

    @commands.command(
        name="groq_chat",
        brief="Discute avec l'IA Groq spécialisée dans le RP géopolitique.",
        usage="groq_chat <message>",
        description="Pose une question ou discute avec l'IA Groq configurée pour le contexte du serveur RP.",
        help="""Interface de chat avec l'IA Groq spécialisée.

        FONCTIONNALITÉ :
        - IA configurée pour le contexte géopolitique post-apocalyptique 2045
        - Mémorise les 5 dernières interactions pour le contexte
        - Différents niveaux de tokens selon le rang utilisateur
        - Anti-flood de 3 minutes entre les requêtes (sauf admin)

        NIVEAUX DE TOKENS :
        - Utilisateur : 400 tokens
        - Admin : 8000 tokens

        RESTRICTIONS :
        - Nécessite une autorisation staff
        - Délai de 3 minutes entre les requêtes pour les non-admins

        ARGUMENTS :
        - `<message>` : Votre question ou message pour l'IA

        EXEMPLE :
        - `groq_chat Quelle est la situation géopolitique actuelle ?` : Pose une question à l'IA
        """,
        hidden=False,
        enabled=True,
        case_insensitive=True,
    )
    async def groq_chat(
        self, 
        ctx, 
        *, 
        message: str = commands.parameter(
            description="Votre question ou message pour l'IA Groq"
        )
    ):
        """Chat with Groq AI."""
        global last_groq_query_time

        if not self.dUtils.is_authorized(ctx):
            return await ctx.send(embed=self.dUtils.get_auth_embed())

        # Anti-flood simple par user
        if last_groq_query_time:
            delta = datetime.now(timezone.utc) - last_groq_query_time
            if (
                delta < timedelta(seconds=180)
                and ctx.author.id not in self.bi_admins_id
            ):
                return await ctx.send(
                    "⏳ Veuillez patienter 3 minutes entre chaque requête."
                )
        level = self.get_query_level(ctx.author.id)
        try:
            response = await self.ask_groq(message, level)
            last_groq_query_time = datetime.now(timezone.utc)
            await self.dUtils.send_long_message(ctx, response)
        except Exception as e:
            await ctx.send(f"❌ Erreur lors de la requête : {e}")

    @commands.command(
        name="leak_inventory",
        brief="Affiche le contenu de la base de données d'inventaire.",
        usage="leak_inventory",
        description="Exporte et affiche toutes les données d'inventaire des joueurs (argent, points politiques/diplomatiques, capacité de population).",
        help="""Affiche le contenu complet de la base de données d'inventaire.

        INFORMATIONS AFFICHÉES :
        - ID/Nom des joueurs
        - Solde d'argent
        - Points politiques
        - Points diplomatiques
        - Capacité de population

        FONCTIONNALITÉ :
        - Affichage par chunks de 20 joueurs pour éviter les limites Discord
        - Conversion des IDs utilisateurs en noms d'affichage
        - Export du fichier de base de données complet
        - Lien vers un visualisateur SQLite en ligne

        RESTRICTIONS :
        - Réservé aux administrateurs uniquement
        - Commande sensible - contient toutes les données économiques

        EXEMPLE :
        - `leak_inventory` : Affiche toutes les données d'inventaire des joueurs
        """,
        hidden=False,
        enabled=True,
        case_insensitive=True,
    )
    @commands.has_permissions(administrator=True)
    async def leak_inventory(self, ctx):
        """Leak the inventory database (Admin only)."""
        columns, rows = self.db.leak_db()

        if not rows:
            await ctx.send("La table `inventory` est vide.")
            return

        columns_to_show = [
            "player_id",
            "balance",
            "pol_points",
            "diplo_points",
            "population_capacity",
        ]
        header = " | ".join(columns_to_show)
        chunk_size = 20
        for i in range(0, len(rows), chunk_size):
            embed = discord.Embed(
                title=f"=== INVENTORY DATABASE LEAK (partie {i // chunk_size + 1}/{(len(rows) - 1) // chunk_size + 1}) ===",
                color=discord.Color.red(),
            )
            for row in rows[i : i + chunk_size]:
                vals = []
                for col in columns_to_show:
                    idx = columns.index(col)
                    val = str(row[idx])
                    vals.append(val)

                user_id = vals[0]
                if user_id.isdigit():
                    user = ctx.guild.get_member(int(user_id))
                    vals[0] = (
                        user.display_name
                        if user
                        else f"Utilisateur inconnu ({user_id})"
                    )

                value = " | ".join(
                    f"{col}: {vals[idx + 1]}"
                    for idx, col in enumerate(columns_to_show[1:])
                )
                embed.add_field(name=vals[0], value=value, inline=False)

            embed.set_footer(
                text=f"Affichage des joueurs {i + 1} à {min(i + chunk_size, len(rows))} / {len(rows)}"
            )
            await ctx.send(embed=embed)
        embed = discord.Embed(
            title="=== INVENTORY DATABASE LEAK (fin) ===",
            description="Fin de l'affichage de la base de données `inventory`. Possible de lire le fichier complet et de le visualiser ici : https://inloop.github.io/sqlite-viewer/",
            color=discord.Color.red(),
        )
        embed.set_footer(text="Fin de l'affichage de la base de données `inventory`.")
        await ctx.send(
            embed=embed, file=discord.File("datas/rts_clean.db", filename="rts.db")
        )


async def setup(bot):
    """Setup function for the cog."""
    await bot.add_cog(AdminUtilities(bot))
