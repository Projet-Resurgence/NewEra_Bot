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
        self.dUtils = get_discord_utils(bot)

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

    @commands.command()
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

    @commands.command()
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

    @commands.command()
    async def execute_cmd(self, ctx, *, code: str):
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

    @commands.command()
    async def del_betw(
        self, ctx, base_message: discord.Message, reach_message: discord.Message
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

    @commands.command()
    async def del_til(self, ctx, reach_message: discord.Message):
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

    @commands.command()
    async def sync_channels(
        self,
        ctx,
        chan_to_sync: Union[
            discord.TextChannel,
            discord.VoiceChannel,
            discord.ForumChannel,
            discord.StageChannel,
        ],
        model_chan: Union[
            discord.TextChannel,
            discord.VoiceChannel,
            discord.ForumChannel,
            discord.StageChannel,
        ],
    ):
        """Sync permissions between two channels."""
        if ctx.author.id not in self.bi_admins_id:
            return await ctx.send("Non.")
        new_permissions = model_chan.overwrites
        await chan_to_sync.edit(overwrites=new_permissions)
        await ctx.send("Fait")

    @commands.command()
    async def sync_cats(
        self,
        ctx,
        cat_to_sync: discord.CategoryChannel,
        model_cat: discord.CategoryChannel,
    ):
        """Sync permissions between two categories."""
        if ctx.author.id not in self.bi_admins_id:
            return await ctx.send("Non.")
        await cat_to_sync.edit(overwrites=model_cat.overwrites)
        await self.cat_syncer(ctx, cat_to_sync)
        await ctx.send("Fait")

    @commands.command()
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

    @commands.command()
    async def send_rules(self, ctx, webhook_url: str):
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

    @commands.command()
    async def groq_chat(self, ctx, *, message):
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

    @commands.command(name="leak_inventory")
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
