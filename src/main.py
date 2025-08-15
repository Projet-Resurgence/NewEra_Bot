import discord
from discord import app_commands
from pyutil import filereplace
from discord.ext import commands
from datetime import datetime, timedelta, timezone
import asyncio
import discord.utils
from time import sleep
import json
from discord.ext.commands import has_role, Context, Converter, BadArgument
from discord.ext import tasks
import urllib.request
import random
import aiohttp
import os
import sqlite3
import events
from construction import *
from currency import *
from db import *
from notion_handler import *
from discord_utils import *
from text_formatting import *
from typing import Union
from PIL import Image
import pytz
import string
import locale
import traceback

# Import centralized utilities
from shared_utils import (
    initialize_utilities,
    get_db,
    get_discord_utils,
    CountryEntity,
    CountryConverter,
    country_autocomplete,
    ERROR_COLOR_INT as error_color_int,
    MONEY_COLOR_INT as money_color_int,
    P_POINTS_COLOR_INT as p_points_color_int,
    D_POINTS_COLOR_INT as d_points_color_int,
    ALL_COLOR_INT as all_color_int,
    FACTORY_COLOR_INT as factory_color_int,
    structure_type_autocomplete,
    specialisation_autocomplete,
    structure_autocomplete,
    region_autocomplete,
    STRUCTURE_TYPES,
    SPECIALISATIONS,
    convert,
    amount_converter,
)

import requests
from dotenv import dotenv_values
import math
import contextlib
from discord.ui import Button, View, Modal, TextInput
from discord import message, emoji, Webhook, SyncWebhook
from removebg import RemoveBg
from context import *
from groq import Groq

Erreurs = {}
continents = []

token = dotenv_values(".env")["TOKEN"]
removebg_apikey = dotenv_values(".env")["REMOVEBG_API_KEY"]
groq_api_key = dotenv_values(".env")["GROQ_API_KEY"]
notion_token = dotenv_values(".env")["NOTION_TOKEN"]

_orig_print = print


def print(*args, **kwargs):
    _orig_print(*args, flush=True, **kwargs)


intents = discord.Intents().all()
bot = commands.Bot(
    intents=intents,
    activity=discord.Game(name="Aider le staff!"),
    command_prefix=["."],
)
groq_client = Groq(api_key=groq_api_key)
last_groq_query_time = datetime.now(timezone.utc)


async def load_cogs():
    """Load all cogs for the bot."""
    try:
        print("🔄 Loading economy cog...")
        await bot.load_extension("cogs.economy")
        print("✅ Economy cog loaded successfully")

        print("🔄 Loading points cog...")
        await bot.load_extension("cogs.points")
        print("✅ Points cog loaded successfully")

        print("🔄 Loading structures cog...")
        await bot.load_extension("cogs.structures")
        print("✅ Structures cog loaded successfully")

        print("🔄 Loading technology cog...")
        await bot.load_extension("cogs.technology")
        print("✅ Technology cog loaded successfully")

        print("🔄 Loading admin utilities cog...")
        await bot.load_extension("cogs.admin_utilities")
        print("✅ AdminUtilities cog loaded successfully")

        # List loaded commands for debugging
        economy_commands = [cmd for cmd in bot.commands if cmd.cog_name == "Economy"]
        points_commands = [cmd for cmd in bot.commands if cmd.cog_name == "Points"]
        structures_commands = [
            cmd for cmd in bot.commands if cmd.cog_name == "Structures"
        ]
        technology_commands = [
            cmd for cmd in bot.commands if cmd.cog_name == "Technology"
        ]
        admin_commands = [
            cmd for cmd in bot.commands if cmd.cog_name == "AdminUtilities"
        ]
        print(f"📋 Loaded economy commands: {[cmd.name for cmd in economy_commands]}")
        print(f"📋 Loaded points commands: {[cmd.name for cmd in points_commands]}")
        print(
            f"📋 Loaded structures commands: {[cmd.name for cmd in structures_commands]}"
        )
        print(
            f"📋 Loaded technology commands: {[cmd.name for cmd in technology_commands]}"
        )
        print(
            f"📋 Loaded structures commands: {[cmd.name for cmd in structures_commands]}"
        )
        print(f"📋 Loaded admin commands: {[cmd.name for cmd in admin_commands]}")
    except Exception as e:
        print(f"❌ Failed to load cogs: {e}")

        traceback.print_exc()


@bot.event
async def on_ready():
    """Event triggered when the bot is ready."""
    print(f"✅ Bot is ready! Logged in as {bot.user}")
    print("🔧 Utilities already initialized")

    await load_cogs()
    await bot.tree.sync()
    polling_notion.start()
    update_rp_date.start()


rmbg = RemoveBg(removebg_apikey, "error.log")

duration_in_seconds = 0
groq_chat_history = []

code_list = []
POLLING_INTERVAL = 300  # en secondes (ici toutes les 5 minutes)

# Usine = 0
# Terrestre = 1
# Aerienne = 2
# Maritime = 3
# Ecole = 4

production_data, base_data = {}, {}
with open("datas/main.json") as f:
    json_data = json.load(f)
    bat_types = json_data["bat_types"]
    query_types = json_data["query_types"]
    bi_admins_id = json_data["bi_admins_id"]
    code_list = json_data["code_list"]
    buildQuality = json_data["buildQuality"]
    bat_buffs = json_data["bat_buffs"]
    unit_types = json_data["unit_types"]

usefulDatas = UsefulDatas(bat_types, bat_buffs, unit_types)

# Initialize utilities early for debug_init
initialize_utilities(bot, bat_types, bat_buffs, unit_types)
db = get_db()
dUtils = get_discord_utils(bot, db)
notion_handler = NotionHandler(notion_token, bot)

# --- All global variables

debug = db.get_setting("debug")
continents = ["Europe", "Amerique", "Asie", "Afrique", "Moyen-Orient", "Oceanie"]
continents_dict = {
    "europe": db.get_setting("europe_category_id"),
    "amerique": db.get_setting("america_category_id"),
    "asie": db.get_setting("asia_category_id"),
    "afrique": db.get_setting("africa_category_id"),
    "moyen-orient": db.get_setting("middle_east_category_id"),
    "oceanie": db.get_setting("oceania_category_id"),
}
starting_amounts = {
    "money": db.get_setting("starting_amount_money"),
    "pol_points": db.get_setting("starting_amount_pol_points"),
    "diplo_points": db.get_setting("starting_amount_diplo_points"),
}
usefull_role_ids_dic = {
    "staff": db.get_setting("staff_role_id"),
    "admin": db.get_setting("admin_role_id"),
    "military_admin": 874869709223383091,
}

Erreurs = {
    "Erreur 1": "Le salon dans lequel vous effectuez la commande n'est pas le bon\n",
    "Erreur 2": "Aucun champ de recherche n'a été donné\n",
    "Erreur 3": "Le champ de recherche donné est invalide\n",
    "Erreur 3.2": "Le champ de recherche donné est invalide - Le pays n'est pas dans les fichiers\n",
    "Erreur 4": "La pause est déjà en cours\n",
    "Erreur 5": "Vous n'avez pas la permission de faire la commande.\n",
}
error_color_int = int(db.get_setting("error_color_hex"), 16)
money_color_int = int(db.get_setting("money_color_hex"), 16)
p_points_color_int = int(db.get_setting("p_points_color_hex"), 16)
d_points_color_int = int(db.get_setting("d_points_color_hex"), 16)
factory_color_int = int(db.get_setting("factory_color_hex"), 16)
all_color_int = int(db.get_setting("all_color_hex"), 16)

tech_channel_id = db.get_setting("tech_channel_id")

# --- Task de polling ---


@tasks.loop(seconds=POLLING_INTERVAL)
async def polling_notion():
    try:
        await notion_handler.check_for_updates()
    except Exception as e:
        print(f"Erreur lors du polling Notion: {e}")

async def update_map():
    return

@tasks.loop(hours=1)
async def daily_update():
    current_hour = datetime.now(pytz.timezone("Europe/Paris")).hour
    if current_hour != 6:
        return
    if db.get_setting("is_paused"):
        return
    await db.update_production()
    await db.update_development()
    await update_map()

@tasks.loop(seconds=5)
async def update_rp_date():
    now = datetime.now(pytz.timezone("Europe/Paris"))  # ou "UTC"
    # if now.hour == 7 and now.minute == 0:
    if True:
        # Advance the playday
        await db.advance_playday(bot)

        # Process production cycle
        completed_productions = db.process_production_cycle()


        if db.is_paused() or db.get_current_date().get('playday') != 1:
            return
        # Notify countries of completed productions
        for production in completed_productions:
            print(f"Production completed for country {production['country_id']}: {production['quantity']}x {production['tech_name']}")
            try:
                country_data = db.get_country_datas(production["country_id"])
                if country_data and country_data.get("secret_channel_id"):
                    channel = bot.get_channel(int(country_data["secret_channel_id"]))
                    if channel:
                        embed = discord.Embed(
                            title="🏭 Production Completed!",
                            description=f"**{production['quantity']}x {production['tech_name']}** has been completed and added to your inventory.",
                            color=factory_color_int,
                        )
                        embed.add_field(
                            name="Technology Type",
                            value=production["tech_type"],
                            inline=True,
                        )
                        embed.add_field(
                            name="Structure ID",
                            value=production["structure_id"],
                            inline=True,
                        )
                        embed.add_field(
                            name="Quantity",
                            value=f"{production['quantity']:,}",
                            inline=True,
                        )
                        await channel.send(embed=embed)
            except Exception as e:
                print(
                    f"Error notifying country {production['country_id']} of completed production: {e}"
                )


@update_rp_date.before_loop
async def before():
    await bot.wait_until_ready()


###


@bot.hybrid_command(
    name="resume_rp",
    brief="Relance le temps RP après une pause (Admin uniquement).",
    usage="resume_rp",
    description="Relance le compteur de temps du roleplay après une pause administrative.",
    help="""Relance le système de temps du roleplay après une pause.

    FONCTIONNALITÉ :
    - Réactive le compteur de temps RP
    - Met fin à l'état de pause du jeu
    - Permet la reprise des activités temporelles
    - Confirme la réactivation via un message

    UTILISATION :
    - Reprise après maintenance
    - Fin d'une pause administrative
    - Résolution de problèmes techniques

    RESTRICTIONS :
    - Réservé aux administrateurs uniquement
    - Ne fonctionne que si le jeu est en pause

    ARGUMENTS :
    - Aucun argument requis

    EXEMPLE :
    - `resume_rp` : Relance le temps RP
    """,
    hidden=False,
    enabled=True,
    case_insensitive=True,
)
@commands.has_permissions(administrator=True)
async def resume_rp(ctx):
    db.set_paused(False)
    await ctx.send("✅ Le temps RP a été relancé !")


@bot.hybrid_command(
    name="date",
    brief="Affiche la date actuelle du jeu RP.",
    usage="date",
    description="Consulte la date et le temps actuel dans l'univers du roleplay.",
    help="""Affiche la date actuelle du roleplay avec les informations temporelles complètes.

    FONCTIONNALITÉ :
    - Affiche l'année, le mois et le jour RP actuels
    - Indique l'état du système de temps (actif/en pause)
    - Utilise le calendrier français pour l'affichage
    - Montre la progression dans le mois actuel

    INFORMATIONS AFFICHÉES :
    - Année en cours du RP
    - Mois en français (avec accentuation)
    - Jour du mois (playday)
    - État du système temporel

    UTILISATION :
    - Vérification du timing pour les actions
    - Planification d'événements RP
    - Synchronisation des joueurs

    ARGUMENTS :
    - Aucun argument requis

    EXEMPLE :
    - `date` : Affiche "Nous sommes le 15 Mars 2045"
    """,
    hidden=False,
    enabled=True,
    case_insensitive=True,
)
async def date(ctx):
    """Affiche la date actuelle du jeu."""
    if db.is_paused():
        await ctx.send("Le temps RP est actuellement en pause.")
        return

    date_dict = db.get_current_date()
    year, month, playday = (
        date_dict.get("year", 1),
        date_dict.get("month", 1),
        date_dict.get("playday", 1),
    )

    try:
        locale.setlocale(locale.LC_TIME, "fr_FR.UTF-8")  # Système Unix/Linux
    except locale.Error:
        try:
            locale.setlocale(locale.LC_TIME, "fr_FR")  # Windows
        except locale.Error as e:
            await ctx.send(f"⚠️ Impossible de définir la locale française. {e}")
            return

    month_name = datetime(year, month, 1).strftime("%B")
    max_playdays = db.get_playdays_in_month(month)

    await ctx.send(
        f"📅 Date actuelle : {month_name.capitalize()} {year} - {playday}/{max_playdays}"
    )


async def log_to_intel(bot, message, image = None):
    chan = bot.get_channel(int(db.get_setting("intelligence_channel_id")))
    if chan:
        await chan.send(message, file=image)


@bot.event
async def on_user_update(before: discord.User, after: discord.User):
    gravite = db.get_gravite_for_member_id(after.id)
    if gravite and gravite >= 1:
        if before.name != after.name:
            await log_to_intel(
                bot,
                f"📝 **Pseudo modifié** : `{before.name}` → `{after.name}` ({after.id})",
            )
        if before.avatar != after.avatar:
            await log_to_intel(bot, f"🖼️ **Avatar modifié** : {after.name} ({after.id})", image=after.avatar)


# 2️⃣ Log messages supprimés (gravité ≥ 2)
@bot.event
async def on_message_delete(message: discord.Message):
    gravite = db.get_gravite_for_member_id(message.author.id)
    if gravite and gravite >= 2:
        await log_to_intel(
            bot,
            f"🗑️ **Message supprimé** de {message.author} ({message.author.id})\n```{message.content}```",
        )

# 3️⃣ Log messages modifiés (gravité ≥ 2)
@bot.event
async def on_message_edit(before: discord.Message, after: discord.Message):
    if before.author.bot:
        return
    gravite = db.get_gravite_for_member_id(before.author.id)
    if gravite and gravite >= 2:
        await log_to_intel(
            bot,
            f"✏️ **Message modifié** de {before.author} ({before.author.id})\n"
            f"Avant:\n```{before.content}```\nAprès:\n```{after.content}```",
        )


# 5️⃣ Log sanctions (mute / ban)
@bot.event
async def on_member_ban(guild, user):
    gravite = db.get_gravite_for_member_id(user.id)
    if gravite:
        await log_to_intel(bot, f"⛔ **BAN** : {user} ({user.id})")


@bot.event
async def on_member_update(before: discord.Member, after: discord.Member):
    # Check si un mute vocal ou timeout a été appliqué
    gravite = db.get_gravite_for_member_id(after.id)
    if gravite and before.timed_out_until != after.timed_out_until:
        await log_to_intel(
            bot,
            f"🔇 **MUTE/TIMEOUT** : {after} ({after.id}) jusqu'à {after.timed_out_until}",
        )


# 4️⃣ Log tous les messages envoyés (gravité = 3)
@bot.event
async def on_message(message: discord.Message):
    if message.author.bot:
        return
    gravite = db.get_gravite_for_member_id(message.author.id)
    if gravite == 3:
        await log_to_intel(
            bot,
            f"📨 **Message** de {message.author} ({message.author.id}) :\n```{message.content}```",
        )
    if (
        isinstance(message.channel, discord.DMChannel)
        and message.author.id == 293869524091142144
        and message.content.startswith("!")
    ):
        await bot.get_channel(int(db.get_setting("tchat_channel_id"))).send(
            message.content[1:]
        )
    if (message.author == bot.user) or (not message.content):
        return
    if message.author.id == 292953664492929025:
        for embed in message.embeds:
            if embed.description.startswith("<:xmark:773218895150448640> "):
                sleep(10)
                await message.delete()
    if message.content == len(message.content) * message.content[0]:
        return
    if "soup" in message.content.lower():
        await message.add_reaction("🥣")
    await bot.process_commands(message)


@bot.hybrid_command(name="info_intel", hidden=True)
@commands.has_permissions(administrator=True)
async def info_intel(ctx: commands.Context, user: discord.User):
    # Vérifie que la commande est exécutée dans le bon salon
    if ctx.channel.id != int(db.get_setting("intelligence_channel_id")):
        return await ctx.send(
            "❌ Cette commande ne peut être utilisée que dans le salon d'intelligence.",
            delete_after=5,
        )

    # Récupère la personne
    personne_data = db.get_personne_from_account_id(user.id)
    if not personne_data:
        return await ctx.send(
            f"ℹ️ L'utilisateur {user} ({user.id}) n'est pas dans la fiche S."
        )

    personne_id = personne_data[0]  # id_personne
    gravite = db.get_gravite_for_member_id(user.id)

    # Comptes associés
    accounts = [
        acc[2] for acc in db.get_accounts_from_personne(personne_id)
    ]  # colonne pseudo
    comptes_str = ", ".join(accounts) if accounts else "Aucun"

    # Sanctions
    sanctions_data = db.get_sanctions_for_personne(personne_id)
    sanctions_str = (
        ", ".join(str(s[2]) for s in sanctions_data) if sanctions_data else "Aucune"
    )

    # Construction du message
    message = (
        f"📄 **Informations sur** {user.mention}\n"
        f"🆔 **ID Personne** : `{personne_id}`\n"
        f"👥 **Comptes associés** : {comptes_str}\n"
        f"⚠️ **Gravité** : **{gravite if gravite is not None else 'Inconnue'}**\n"
        f"🚫 **Sanctions** : {sanctions_str}"
    )

    colors = [discord.Color.yellow(), discord.Color.orange(), discord.Color.red()]
    color = (
        colors[gravite]
        if gravite is not None and gravite < len(colors)
        else discord.Color.yellow()
    )

    embed = discord.Embed(
        title=f"Informations sur {user.name}", description=message, color=color
    )
    await ctx.send(embed=embed)


async def insert_mention(
    message: discord.Message, user: discord.User, mentions: dict = None
):
    """
    Inserts a mention into the embed description of a Discord message.

    Args:
        message (discord.Message): The Discord message object containing the embed.
        user (discord.User): The Discord user to mention.
        mentions (dict, optional): A dictionary to store mentions with user mentions as keys and user IDs as values. Defaults to None.

    Returns:
        None
    """
    embed = message.embeds[0]
    message_content = embed.description
    mentions[user.mention] = user.id
    mention_str = " | ".join([f"{key} ({value})" for key, value in mentions.items()])
    message_content += mention_str + "\n"
    embed = discord.Embed(
        title=message.embeds[0].title, description=message_content, color=all_color_int
    )
    await message.edit(embed=embed)


async def handle_treaty(reaction: discord.Reaction, user: discord.User):
    async def handle_treaty(reaction: discord.Reaction, user: discord.User):
        """
        Handles the treaty reaction event.

        This function is triggered when a user reacts to a message with a specific emoji.
        It checks if the reaction emoji is either "🖋️" or "🖊️". If the emoji is valid,
        it parses the mentions from the message's embed description and inserts the user's
        mention if it is not already present.

        Args:
            reaction (discord.Reaction): The reaction object containing the emoji and the message.
            user (discord.User): The user who reacted to the message.

        Returns:
            None
        """

    if reaction.emoji not in ["🖋️", "🖊️"]:
        return
    message = reaction.message
    mentions = parse_mentions(message.embeds[0].description)
    if user.mention in mentions.keys():
        return
    await insert_mention(message, user, mentions)


async def create_treaty(reaction, user):
    """
    Asynchronously creates a treaty message when a specific reaction is added to a message.

    Args:
        reaction (discord.Reaction): The reaction that triggered the function.
        user (discord.User): The user who added the reaction.

    Returns:
        None

    Behavior:
        - If the reaction emoji is not "✅", the function returns immediately.
        - Retrieves the content of the message that received the reaction.
        - Fetches a list of users who reacted with specific emojis ("🖋️" and "🖊️") to the message.
        - Constructs a message content string that includes the original message content and mentions of the users.
        - Creates and sends an embedded message to the same channel with the constructed content.
    """
    message = reaction.message
    if reaction.emoji != "✅":
        return
    message_content = f"Traité crée, officialisé et signé par les membres précisés dans la section ``Mention``.\n\nContenu du traité : \n\n{message.content}"
    user_list = await dUtils.get_users_by_reaction(["🖋️", "🖊️"], message)
    mentions = {user.mention: user.id for user in user_list}
    mention_str = " | ".join([f"{key} ({value})" for key, value in mentions.items()])
    message_content += f"\n\n Mention : {mention_str}"
    embed = discord.Embed(
        title="Traité", description=message_content, color=all_color_int
    )
    new_message = await message.channel.send(embed=embed)


@bot.event
async def on_reaction_add(reaction: discord.Reaction, user: discord.User):
    if user == bot.user:
        return
    message = reaction.message
    if (
        message.channel.id != 1396922371121610792
        and message.channel.category.id != 1269295981183369279
    ):
        return
    if (
        message.author == bot.user
        and reaction.emoji in ["🖋️", "🖊️"]
        and message.channel.id == 1396922371121610792
    ):
        await handle_treaty(reaction, user)
    elif reaction.emoji == "✅":
        await create_treaty(reaction, user)


@bot.hybrid_command()
async def notion(ctx, req_type: str = "all"):
    await ctx.defer()
    req_type = req_type.lower()
    try:
        embeds = await notion_handler.get_tasks(ctx, req_type)
        if not embeds:
            await ctx.send(
                "❌ Aucune tâche trouvée ou erreur lors de la récupération des données Notion."
            )
            return

        # Send each embed separately for better space management
        for embed in embeds:
            await ctx.send(embed=embed)
    except Exception as e:
        await ctx.send(f"❌ Erreur lors de la récupération des données Notion : {e}")


@bot.hybrid_command()
async def notion_init_cache(ctx):
    """Admin command to initialize Notion cache without sending notifications."""
    if ctx.author.id not in bi_admins_id:
        await ctx.send("❌ Cette commande est réservée aux administrateurs.")
        return

    await ctx.defer()
    try:
        await ctx.send("🔄 Initialisation du cache Notion en cours...")
        await notion_handler.initialize_cache_silently()
        await ctx.send(
            "✅ Cache Notion initialisé avec succès. Les prochaines vérifications ne signaleront que les vraies mises à jour."
        )
    except Exception as e:
        await ctx.send(f"❌ Erreur lors de l'initialisation du cache Notion : {e}")


@bot.hybrid_command(
    name="sign_user_to_treaty",
    brief="Propose la signature d'un traité à un utilisateur.",
    usage="sign_user_to_treaty <message> <user>",
    description="Permet à un utilisateur de signer un traité et, si besoin, d'envoyer le traité dans un salon secret.",
    help="""Propose à un utilisateur de signer un traité dont les détails sont contenus dans un message donné.

    ARGUMENTS :
    - `<message>` : Message contenant le traité (de préférence, un message du bot lui-même).
    - `<user>` : Utilisateur Discord invité à signer le traité.

    EXEMPLE :
    - `sign_user_to_treaty 123456789012345678 @utilisateur` : Invite l'utilisateur mentionné à signer le traité contenu dans le message avec l'ID spécifié.
    """,
    hidden=False,
    enabled=True,
    case_insensitive=True,
)
async def sign_user_to_treaty(
    ctx,
    message: discord.Message = commands.parameter(
        description="Message contenant le traité à signer."
    ),
    user: discord.User = commands.parameter(
        description="Utilisateur invité à signer le traité."
    ),
) -> None:
    if message.author != bot.user:
        return
    try:
        waiting_message = await user.send(
            f"Voulez-vous signer le traité dont les détails sont ci-dessous?\n\n{message.content} (Oui/Non)"
        )
        response = await bot.wait_for(
            "message",
            check=lambda m: m.author == user and m.channel == waiting_message.channel,
            timeout=120,
        )
        if response.content.lower() == "oui":
            await insert_mention(
                ctx.message, user, parse_mentions(ctx.message.embeds[0].description)
            )
            if message.channel.category.id == 1269295981183369279:
                waiting_message = await user.send(
                    "Veuillez indiquer l'ID / Lien / Mention de votre salon secret."
                )
                response = await bot.wait_for(
                    "message",
                    check=lambda m: m.author == user
                    and m.channel == waiting_message.channel,
                    timeout=120,
                )
                response = message.guild.get_channel(response.content.strip())
                await response.send(embed=message.embeds[0])
            await user.send("Vous avez signé le traité.")
    except discord.Forbidden:
        await ctx.send("Impossible d'obtenir l'utilisateur.")
        return


@bot.event
async def on_command_error(ctx, error):
    tb = "".join(traceback.format_exception(type(error), error, error.__traceback__))
    # Only show first line and line number for users, full traceback for admins
    error_msg = f"**Error:** {error}\n"
    if error.__traceback__:
        tb_lines = tb.splitlines()
        # Find the most recent call line
        for line in reversed(tb_lines):
            error_msg += f"`{line.strip()}`\n"
    embed = discord.Embed(
        title="Une erreur s'est produite en exécutant la commande",
        description="**Message d'erreur:** " + str(error),
        color=discord.Color.red(),
    )
    await ctx.send(embed=embed)
    print(f"❌ Error in command {ctx.command}: {error}")
    print(f"Full traceback:\n{tb}")


class ConstructionForm(discord.ui.Modal, title="Données de construction"):
    def __init__(self, goal: str):
        super().__init__()

        self.objectif = discord.ui.TextInput(
            label=(
                "Objectif d'habitants"
                if goal == "habitants"
                else "Budget de construction"
            ),
            placeholder="Ex: 200",
            required=True,
        )
        self.max_etages = discord.ui.TextInput(
            label="Nombre max d'étages", default="10", required=False
        )
        self.max_apartments = discord.ui.TextInput(
            label="Nombre max de logements/étage", default="30", required=False
        )
        self.appt_lvl = discord.ui.TextInput(
            label="Niveau de qualité des logements", default="1", required=False
        )
        self.taille_appt = discord.ui.TextInput(
            label="Taille moyenne des logements (en m²)", default="40", required=False
        )

        # Ajout explicite des champs dans le Modal
        self.add_item(self.objectif)
        self.add_item(self.max_etages)
        self.add_item(self.max_apartments)
        self.add_item(self.appt_lvl)
        self.add_item(self.taille_appt)

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer(thinking=True)
        appt_lvl_int = int(self.appt_lvl.value or 1)
        datas = {
            "objectif": int(self.objectif.value),
            "max_etages": int(self.max_etages.value or 10),
            "max_apartments": int(self.max_apartments.value or 30),
            "appt_lvl": appt_lvl_int,
            "taille_moyenne": int(self.taille_appt.value or 40),
            "type_murs": buildQuality["walls"][str(appt_lvl_int)],
            "prix_moyen": buildQuality["price"][str(appt_lvl_int)],
            "people_per_apartment": get_people_per_apartment(
                int(self.taille_appt.value or 40)
            ),
            "objectif_type": (
                "habitants" if "habitants" in self.objectif.label.lower() else "cout"
            ),
            "prix_fondations": 50,
        }

        if datas["objectif_type"] == "habitants":
            buildings, datas = await calculate_by_population_from_datas(
                interaction, datas
            )
        else:
            buildings, datas = await calculate_by_budget_from_datas(interaction, datas)
        await send_building_summary(interaction, buildings, datas)


@bot.hybrid_command(
    name="construction_immeuble",
    brief="Construit un immeuble basé sur le nombre d'habitants ou un budget.",
    usage="construction_immeuble",
    description="Construit un immeuble selon un objectif d'habitants ou un budget donné.",
    help="""Interagit avec l'utilisateur pour établir un projet de construction d'immeubles selon ses choix et contraintes.

    DESCRIPTION DU PROCESSUS :
    - Cette commande guide l'utilisateur pour calculer les coûts et surfaces de plusieurs bâtiments selon une estimation du nombre d'habitants ou un budget maximum.
    - Elle génère ensuite un bilan détaillé pour chaque bâtiment, ainsi qu'un récapitulatif final qui présente les coûts et surfaces totales.
    - Si le nombre de bâtiments est élevé, un fichier texte est envoyé à la place pour éviter le dépassement de la limite de caractères.

    ARGUMENTS :
    - Aucun argument n'est requis pour exécuter cette commande, car elle prend des informations via des interactions avec l'utilisateur.

    EXEMPLE :
    - `construction_immeuble` : Lance le programme de construction d'immeubles et invite l'utilisateur à choisir entre un objectif d'habitants ou un budget de construction.
    """,
    hidden=False,
    enabled=True,
    case_insensitive=True,
)
async def construction_immeuble(ctx, goal: str = None) -> None:
    """Commande classique qui initie un bouton vers un formulaire modal"""
    if not goal:
        goal = await dUtils.discord_input(
            ctx,
            "Bienvenue dans le programme de construction d'immeubles!\nVoulez-vous construire un immeuble par nombre d'habitants ou par coût de construction? (habitants/coût)",
        )
    goal = goal.lower()
    if goal not in ["habitants", "habitant", "coût", "cout"]:
        await ctx.send("Veuillez répondre par 'habitants' ou 'coût'.")
        return
    if goal == "coût":
        goal = "cout"
    if goal == "habitant":
        goal = "habitants"

    class ModalTriggerView(discord.ui.View):
        @discord.ui.button(
            label="📋 Remplir le formulaire", style=discord.ButtonStyle.green
        )
        async def launch_modal(
            self, interaction: discord.Interaction, button: discord.ui.Button
        ):
            await interaction.response.send_modal(ConstructionForm(goal))

    await ctx.send(
        "📋 Cliquez sur le bouton ci-dessous pour ouvrir le formulaire :",
        view=ModalTriggerView(),
    )


@bot.hybrid_command()
async def lead(ctx):
    async def create_lead_embed(leaderboard, offset):
        embed = discord.Embed(
            title=f"Classement des pays (de {offset + 1} à {offset + len(leaderboard)})",
            color=0x00FF00,
        )
        for i, (role_id, balance, pp, pd) in enumerate(leaderboard, offset + 1):
            role = ctx.guild.get_role(int(role_id))
            if role:
                rolename = role.name + f" - {str(role_id)}"
            else:
                rolename = str(role_id) + " - Non identifié"
            embed.add_field(
                name=f"{i}. {rolename}",
                value=f":moneybag: **{convert(str(balance))}** argent -- :blue_circle: **{pp}** points politiques -- :green_circle: **{pd}** points diplos",
                inline=False,
            )
        return embed

    leaderboard = await db.get_leaderboard()

    if len(leaderboard) == 0:
        return await ctx.send("Le classement est vide.")

    view = View()
    max_entries = 100  # Limite maximum du nombre d'utilisateurs à afficher

    async def next_callback(interaction):
        nonlocal offset
        offset += 10
        leaderboard = await db.get_leaderboard(offset)
        if len(leaderboard) > 0:
            embed = await create_lead_embed(leaderboard, offset)
            await interaction.response.edit_message(embed=embed, view=view)
        else:
            offset -= 10

    async def prev_callback(interaction):
        nonlocal offset
        if offset > 0:
            offset -= 10
            leaderboard = await db.get_leaderboard(offset)
            embed = await create_lead_embed(leaderboard, offset)
            await interaction.response.edit_message(embed=embed, view=view)

    offset = 0
    embed = await create_lead_embed(leaderboard, offset)

    prev_button = Button(label="◀️ Précédent", style=discord.ButtonStyle.primary)
    prev_button.callback = prev_callback
    next_button = Button(label="▶️ Suivant", style=discord.ButtonStyle.primary)
    next_button.callback = next_callback

    view.add_item(prev_button)
    view.add_item(next_button)

    await ctx.send(embed=embed, view=view)


def is_valid_lvl(type: int, lvl: int):
    if lvl < 0:
        return False
    if type == 0 and lvl <= 7:
        return True
    elif type == 1 and lvl <= 7:
        return True
    elif type == 2 and lvl <= 4:
        return True
    elif type == 3 and lvl <= 4:
        return True
    elif type == 4 and lvl <= 4:
        return True
    else:
        return False


@bot.hybrid_command(
    name="create_country",
    brief="Crée un pays, en lui attribuant ses ressources, son rôle, et son salon.",
    usage="create_country <membre> <emoji_drapeau> <nom_sans_espace> <continent>",
    description="create_country <membre> <emoji_drapeau> <nom_sans_espace> <continent>",
    help="""Crée un pays, en lui attribuant ses ressources, son rôle, et son salon.
    ARGUMENTS :
    - `<membre>` : Le membre Discord auquel attribuer le pays (mention ou ID).
    - `<emoji_drapeau>` : Emoji représentant le drapeau du pays.
    - `<nom_sans_espace>` : Nom du pays, sans espaces (utilisez des underscores `_` si besoin).
    - `<continent>` : Le nom ou ID du continent (Europe, Amérique, Asie, Afrique, Océanie, Moyen-Orient).
    EXEMPLE :
    - `create_country @membre :flag_fr: France Europe` : Crée le pays France sur le continent Europe pour membre.
    """,
    hidden=False,
    enabled=True,
    case_insensitive=True,
)
async def create_country(
    ctx,
    user: discord.Member = commands.parameter(
        description="ID ou mention du membre auquel attribuer le pays"
    ),
    country_flag=commands.parameter(
        description="Emoji représentant le drapeau du pays"
    ),
    country_name=commands.parameter(
        description="Nom du pays sans espaces. Remplacez les espaces par des underscores `_`."
    ),
    continent: discord.CategoryChannel = commands.parameter(
        description="ID ou nom du continent (Europe, Amérique, Asie, etc.). Accents et majuscules autorisés."
    ),
) -> None:
    continents = {
        "europe": 955479237001891870,
        "amerique": 952314456870907934,
        "asie": 1243672298381381816,
        "afrique": 961678827933794314,
        "oceanie": 992368253580087377,
        "moyen-orient": 951163668102520833,
    }
    player_role = await dUtils.get_player_role(ctx)
    non_player_role = await dUtils.get_non_player_role(ctx)
    if not dUtils.is_authorized(ctx):
        return await ctx.send(embed=dUtils.get_auth_embed())

    # Initialize country resources directly
    country_entity = CountryEntity(user, ctx.guild).to_dict()
    if country_entity and country_entity.get("id"):
        country_id = country_entity["id"]
        db.set_balance(country_id, starting_amounts["money"])
        db.set_points(country_id, starting_amounts["pp"], 1)  # Political points
        db.set_points(country_id, starting_amounts["pd"], 2)  # Diplomatic points

    country_name = country_name.replace("_", " ")
    role_name = f"《{country_flag}》{country_name}"
    country_name = convert_country_name(country_name)
    channel_name = f"「{country_flag}」{country_name}"
    channel = await continent.create_text_channel(channel_name)
    role = await ctx.guild.create_role(name=role_name)
    await channel.set_permissions(
        ctx.guild.default_role,
        manage_webhooks=False,
        view_channel=True,
        read_messages=True,
        send_messages=False,
    )
    await channel.set_permissions(
        role,
        manage_webhooks=True,
        view_channel=True,
        read_messages=True,
        send_messages=True,
        manage_messages=True,
    )
    await channel.send(f"Bienvenue dans le pays de {country_name} !")
    await user.add_roles(role, reason=f"Création du pays {country_name}")
    await user.add_roles(player_role, reason=f"Création du pays {country_name}")
    await user.remove_roles(non_player_role, reason=f"Création du pays {country_name}")
    await ctx.send(f"Le pays {country_name} a été créé avec succès.")


@bot.hybrid_command(
    name="create_secret",
    brief="Crée un service secret, en attribuant les permissions correctes pour le pays à qui il appartient.",
    usage="create_secret <country_role> <service_icon> <nom_sans_espace>",
    description="create_secret <country_role> <service_icon> <nom_sans_espace>",
    help="""Crée un service secret, en attribuant les permissions correctes pour le pays à qui il appartient
    ARGUMENTS :
    - `<country_role>` : Role du pays à qui appartient le service secret.
    - `<service_icon>` : Emoji de l'emoji à côté du service secret.
    - `<nom_sans_espace>` : Nom du service secret sans espace - les espaces sont à remplacer par des underscores.
    - `create_secret @role :flag_fr: DGSI` : Crée le service secret 'DGSI' du pays @role avec l'emoji du drapeau français.
    """,
    hidden=False,
    enabled=True,
    case_insensitive=True,
)
async def create_secret(
    ctx,
    country_role: discord.Role = commands.parameter(
        description="ID ou @ du rôle du pays"
    ),
    service_icon=commands.parameter(description="l'Emoji du drapeau du pays"),
    secret_name=commands.parameter(description="Nom du service secret sans espace."),
) -> None:
    secret_category = discord.utils.get(ctx.guild.categories, id=1269295981183369279)
    staff_role = ctx.guild.get_role(usefull_role_ids_dic["staff"])
    if not dUtils.is_authorized(ctx):
        return await ctx.send(embed=dUtils.get_auth_embed())
    secret_name = secret_name.replace("_", " ")
    secret_name = convert_country_name(secret_name)
    channel_name = f"「{service_icon}」{secret_name}"
    channel = await secret_category.create_text_channel(channel_name)
    await channel.set_permissions(
        ctx.guild.default_role,
        manage_webhooks=False,
        view_channel=False,
        read_messages=False,
        send_messages=False,
    )
    await channel.set_permissions(
        country_role,
        manage_webhooks=True,
        view_channel=True,
        read_messages=True,
        send_messages=True,
        manage_messages=True,
    )
    await channel.set_permissions(
        staff_role,
        manage_webhooks=True,
        view_channel=True,
        read_messages=True,
        send_messages=True,
        manage_messages=True,
    )
    await channel.send(
        f"Bienvenue dans les services {secret_name} du pays {country_role.name} !"
    )
    await ctx.send(f"Le service secret {secret_name} a été créé avec succès.")


def get_query_level(user_id):
    if user_id in bi_admins_id:
        return "admin"
    return "user"


@bot.hybrid_command(
    name="brief_chat_til",
    brief="Résume la situation RP actuelle d'un salon (Staff uniquement).",
    usage="brief_chat_til <message>",
    description="Génère un résumé IA de la situation géopolitique dans un salon Discord.",
    help="""Utilise l'IA pour résumer la situation géopolitique actuelle dans un salon.

    FONCTIONNALITÉ :
    - Analyse les messages récents du salon spécifié
    - Génère un résumé intelligent avec l'IA Groq
    - Se concentre sur les aspects géopolitiques et RP
    - Fournit un contexte synthétique de la situation

    UTILISATION :
    - Mise à jour rapide sur une situation
    - Briefing pour nouveaux participants
    - Synthèse d'événements complexes
    - Support administratif pour le suivi RP

    RESTRICTIONS :
    - Réservé aux membres du staff uniquement
    - Nécessite l'accès aux API externes
    - Limité par la disponibilité de l'IA

    ARGUMENTS :
    - `<message>` : Message du salon à analyser pour le contexte

    EXEMPLE :
    - `brief_chat_til <ID_message>` : Résume la situation à partir de ce message
    """,
    hidden=False,
    enabled=True,
    case_insensitive=True,
)
async def brief_chat_til(
    ctx,
    user_message: discord.Message = commands.parameter(
        description="Message du salon à analyser pour générer le résumé"
    ),
):
    """Résumer la situation actuelle du RP dans un salon."""
    if not dUtils.is_authorized(ctx):
        return await ctx.send(embed=dUtils.get_auth_embed())

    # Récupérer le contexte du salon
    channel_context = await dUtils.get_channel_context(
        user_message.channel, user_message
    )

    # Construire le message pour Groq
    system_prompt = (
        "Tu es une IA spécialisée dans la synthèse d'informations géopolitiques. "
        "Tu dois résumer la situation actuelle du RP dans un salon Discord, en te basant sur les messages récents."
    )
    messages = [{"role": "system", "content": system_prompt}]
    messages.append({"role": "user", "content": channel_context})

    try:
        chat_completion = groq_client.chat.completions.create(
            messages=messages, model="llama-3.3-70b-versatile"
        )
        response = chat_completion.choices[0].message.content
        await dUtils.send_long_message(ctx, f"Résumé de la situation : {response}")
    except Exception as e:
        await user_message.channel.send(f"Erreur lors de la synthèse : {e}")


@bot.hybrid_command(
    name="ask_rp_questions",
    brief="Pose une question IA sur la situation RP d'un salon (Staff uniquement).",
    usage="ask_rp_questions <question> <message>",
    description="Utilise l'IA pour répondre à une question spécifique sur la situation géopolitique.",
    help="""Pose une question spécifique à l'IA sur la situation géopolitique d'un salon.

    FONCTIONNALITÉ :
    - Analyse le contexte du salon spécifié
    - Répond à votre question avec l'IA Groq
    - Se base sur les messages récents pour le contexte
    - Fournit des réponses ciblées et pertinentes

    TYPES DE QUESTIONS POSSIBLES :
    - "Quels sont les principaux enjeux actuels ?"
    - "Qui sont les acteurs clés dans cette situation ?"
    - "Quelle est la position de [pays] ?"
    - "Y a-t-il des tensions diplomatiques ?"

    RESTRICTIONS :
    - Réservé aux membres du staff uniquement
    - Nécessite l'accès aux API externes
    - Qualité dépendante du contexte disponible

    ARGUMENTS :
    - `<question>` : Votre question sur la situation RP
    - `<message>` : Message du salon pour le contexte

    EXEMPLE :
    - `ask_rp_questions "Quelle est la situation militaire ?" <ID_message>`
    """,
    hidden=False,
    enabled=True,
    case_insensitive=True,
)
async def ask_rp_questions(
    ctx,
    question: str = commands.parameter(
        description="Question à poser sur la situation RP"
    ),
    user_message: discord.Message = commands.parameter(
        description="Message du salon pour fournir le contexte"
    ),
):
    """Résumer la situation actuelle du RP dans un salon."""
    if not dUtils.is_authorized(ctx):
        return await ctx.send(embed=dUtils.get_auth_embed())

    # Récupérer le contexte du salon
    channel_context = await dUtils.get_channel_context(
        user_message.channel, user_message
    )

    # Construire le message pour Groq
    system_prompt = (
        "Tu es une IA spécialisée dans la synthèse d'informations géopolitiques. "
        "Tu dois répondre à la question de l'utilisateur en te basant sur les messages qui te seront donnés."
    )
    messages = [{"role": "system", "content": system_prompt}]
    messages.append({"role": "user", "content": channel_context})
    messages.append({"role": "user", "content": question})

    print(f"Question posée : {question}")
    print(f"Contexte du salon : {channel_context}")

    try:
        chat_completion = groq_client.chat.completions.create(
            messages=messages, model="llama-3.3-70b-versatile"
        )
        response = chat_completion.choices[0].message.content
        await dUtils.send_long_message(
            ctx, f"Réponse à la question {question} : {response}"
        )
    except Exception as e:
        await user_message.channel.send(f"Erreur lors de la synthèse : {e}")


@bot.hybrid_command(
    name="check_for_role_overwrites",
    brief="Vérifie les permissions spécifiques d'un rôle (Staff uniquement).",
    usage="check_for_role_overwrites <role>",
    description="Analyse les permissions spécifiques d'un rôle dans tous les salons du serveur.",
    help="""Vérifie où un rôle a des permissions spécifiquement définies dans le serveur.

    FONCTIONNALITÉ :
    - Scanne tous les salons du serveur
    - Identifie les permissions explicitement définies pour le rôle
    - Liste les salons avec des overrides de permissions
    - Aide au diagnostic des problèmes de permissions

    UTILISATION :
    - Audit de sécurité des permissions
    - Diagnostic de problèmes d'accès
    - Vérification de la configuration des rôles
    - Maintenance administrative

    INFORMATIONS AFFICHÉES :
    - Liste des salons avec permissions spécifiques
    - Indication des overrides existants
    - Récapitulatif des permissions personnalisées

    RESTRICTIONS :
    - Réservé aux membres du staff uniquement
    - Nécessite les permissions d'administration

    ARGUMENTS :
    - `<role>` : Rôle à analyser (mention ou nom)

    EXEMPLE :
    - `check_for_role_overwrites @Moderateur`
    """,
    hidden=False,
    enabled=True,
    case_insensitive=True,
)
async def check_for_role_overwrites(
    ctx,
    role: discord.Role = commands.parameter(
        description="Rôle dont vérifier les permissions spécifiques"
    ),
):
    """Vérifie si le rôle a des permissions définies dans des salons spécifiques."""
    if not dUtils.is_authorized(ctx):
        return await ctx.send(embed=dUtils.get_auth_embed())

    exclusive_overwrites = []

    for channel in ctx.guild.channels:
        overwrites = channel.overwrites_for(role)

        # Vérifie si au moins une permission est explicitement définie
        for perm_name in dir(overwrites):
            if perm_name.startswith("_"):
                continue  # ignore les attributs internes

            value = getattr(overwrites, perm_name)
            if isinstance(value, bool):  # Permission explicitement définie
                exclusive_overwrites.append(f"#{channel.name}")
                break  # On passe au canal suivant dès qu'une permission est définie

    if exclusive_overwrites:
        embed = discord.Embed(
            title=f"🔍 Permissions spécifiques pour le rôle {role.name}",
            description="\n".join(exclusive_overwrites),
            color=discord.Color.gold(),
        )
        print(
            f"Permissions spécifiques trouvées pour le rôle {role.name} dans les salons suivants : {', '.join(exclusive_overwrites)}"
        )
        await ctx.send(embed=embed)
    else:
        await ctx.send(
            f"✅ Aucune permission spécifique définie pour le rôle {role.name}."
        )


@bot.hybrid_command()
async def archive_rp_channels(ctx, archive_category: discord.CategoryChannel):
    """Archive les salons de RP en les déplaçant dans une catégorie d'archive."""
    if not dUtils.is_authorized(ctx):
        return await ctx.send(embed=dUtils.get_auth_embed())

    continents_dict["services"] = (
        1269295981183369279  # ID de la catégorie des services secrets
    )

    # Liste pour stocker tous les salons de RP à archiver
    rp_channels = []

    for category_id in continents_dict.values():
        category = bot.get_channel(category_id)
        if isinstance(category, discord.CategoryChannel):
            rp_channels.extend(category.text_channels)

    if not rp_channels:
        return await ctx.send(
            "Aucun salon de RP trouvé dans les catégories spécifiées."
        )

    for channel in rp_channels:
        try:
            await channel.edit(category=archive_category)
            print(f"Salon {channel.name} archivé dans {archive_category.name}.")
        except discord.Forbidden:
            print(f"Permission refusée pour archiver le salon {channel.name}.")
            await ctx.send(
                f"❌ Permission refusée pour archiver le salon {channel.name}."
            )
        except Exception as e:
            print(f"Erreur lors de l'archivage du salon {channel.name}: {e}")
            await ctx.send(
                f"❌ Erreur lors de l'archivage du salon {channel.name}: {e}"
            )

    await ctx.send("✅ Tous les salons de RP ont été archivés avec succès.")


async def transfer_messages_from_channel_to_channel(source_channel, target_channel):
    """Copie les messages d'un salon vers un autre en utilisant des embeds."""
    async for message in source_channel.history(limit=None, oldest_first=True):
        if message.author.bot:
            continue
        if (
            message.content.startswith(".")
            or message.content.startswith("!")
            or message.content.startswith("/")
        ):
            continue

        try:
            # Embed personnalisé pour le message
            embed = discord.Embed(
                description=message.clean_content,
                timestamp=message.created_at,
                color=discord.Color.blue(),
            )
            embed.set_author(
                name=f"{message.author.display_name}",
                icon_url=(
                    message.author.display_avatar.url
                    if message.author.display_avatar
                    else discord.Embed.Empty
                ),
            )
            embed.set_footer(text=f"Envoyé dans #{source_channel.name}")

            files = [await a.to_file() for a in message.attachments]

            # Si le message a déjà des embeds (envoyés par des bots par exemple), les copier aussi
            embeds_to_send = [embed]
            if message.embeds:
                for original_embed in message.embeds:
                    try:
                        # Discord ne permet pas de cloner exactement tous les embeds
                        # mais on peut les inclure tels quels s’ils sont simples
                        embeds_to_send.append(original_embed)
                    except Exception as e:
                        print(f"Erreur lors de la copie d’un embed existant : {e}")

            await target_channel.send(embeds=embeds_to_send, files=files)

        except discord.HTTPException as e:
            print(f"Erreur HTTP : {e}")
        except discord.Forbidden:
            print(f"Permission refusée dans {target_channel.name}")
            return False
    return True


@bot.hybrid_command(
    name="transfer_archives",
    brief="Copie les salons d'archives vers une autre catégorie.",
    usage="transfer_archives",
    description="Copie les salons d'archives vers une autre catégorie.",
)
async def transfer_archives(ctx):
    """Copie les salons d'archives vers une autre catégorie (dans le même serveur ou un autre où le bot est)."""
    if not dUtils.is_authorized(ctx):
        return await ctx.send(embed=dUtils.get_auth_embed())
    archive_guild = bot.get_guild(1396923284498415807)

    archive_categories_id = [1231253371902623764, 1396920393939419156]

    archive_categories = [
        bot.get_channel(cat_id)
        for cat_id in archive_categories_id
        if isinstance(bot.get_channel(cat_id), discord.CategoryChannel)
    ]

    if not archive_categories:
        return await ctx.send("Aucune catégorie d'archives trouvée.")

    for category in archive_categories:
        new_category = await archive_guild.create_category(
            name=f"Archives de {category.name}",
            reason="Transfert des salons d'archives",
        )
        for channel in category.text_channels:
            try:
                new_channel = await archive_guild.create_text_channel(
                    name=channel.name,
                    category=new_category,
                    topic=f"Copie depuis {category.name}",
                )
                await ctx.send(f"📤 Transfert de #{channel.name} en cours...")
                await transfer_messages_from_channel_to_channel(channel, new_channel)
                await new_channel.send(f"✅ Fin du transfert depuis #{channel.name}")
                await asyncio.sleep(2)
            except discord.Forbidden:
                await ctx.send(
                    f"❌ Permission refusée pour copier le salon {channel.name}"
                )
            except Exception as e:
                await ctx.send(f"❌ Erreur pour le salon {channel.name}: {e}")


@bot.hybrid_command()
@app_commands.autocomplete(country=country_autocomplete)
@app_commands.choices(
    unit_type=[
        app_commands.Choice(name="Tous", value="all"),
        app_commands.Choice(name="Soldat", value="soldat"),
        app_commands.Choice(name="Réserve", value="reserve"),
        app_commands.Choice(name="Policier", value="policier"),
        app_commands.Choice(name="Secret", value="secret"),
        app_commands.Choice(name="Ingénieur", value="ingenieur"),
    ]
)
async def get_units(ctx, country: CountryConverter = None, unit_type: str = "all"):
    """
    Commande pour obtenir le nombre d'unités d'un pays.

    Args:
        ctx (commands.Context): Le contexte de la commande.
        country (CountryConverter): Le pays dont on veut connaître le nombre d'unités.
        unit_type (str): Le type d'unité à vérifier (par défaut "soldier").

    Returns:
        None
    """

    if not country:
        country = CountryEntity(ctx.author, ctx.guild).to_dict()
    if unit_type.lower() not in unit_types.keys() and unit_type.lower() != "all":
        return await ctx.send(
            "Type d'unité invalide. Utilisez une de ces valeurs : "
            + ", ".join(unit_types.keys())
            + " ou 'all'."
        )

    is_country = db.get_players_country(ctx.author.id) == country.get("id")
    is_channel_secret = ctx.channel.id == int(
        db.get_country_secret_channel(country.get("id"))
    )

    title_str = f"Récupération des unités {'privées & publiques' if is_country and is_channel_secret else 'publiques'} pour {country.get('name')}"

    units = {}
    if unit_type.lower() == "all":
        for utype in unit_types.keys():
            if is_country and is_channel_secret:
                units[utype] = db.get_units(country.get("id"), unit_types.get(utype))
            units[f"public_{utype}"] = db.get_units(
                country.get("id"), f"public_{unit_types.get(utype)}"
            )
    else:
        if is_country and is_channel_secret:
            units[f"public_{unit_type.lower()}"] = db.get_units(
                country.get("id"), f"public_{unit_types.get(unit_type.lower())}"
            )
        units[unit_type.lower()] = db.get_units(
            country.get("id"), unit_types.get(unit_type.lower())
        )
    if not units:
        return await ctx.send("Aucune unité trouvée pour ce pays.")
    result_text = ""
    for utype, count in units.items():
        if count is not None:
            result_text += f"{utype.replace('public_', '(chiffre public) ')}: {count}\n"
    embed = discord.Embed(
        title=title_str, color=discord.Color.blue(), description=result_text
    )
    await ctx.send(embed=embed)


@bot.hybrid_command()
@app_commands.autocomplete(country=country_autocomplete)
@app_commands.choices(
    unit_type=[
        app_commands.Choice(name="Soldat", value="soldat"),
        app_commands.Choice(name="Réserve", value="reserve"),
        app_commands.Choice(name="Policier", value="policier"),
        app_commands.Choice(name="Secret", value="secret"),
        app_commands.Choice(name="Ingénieur", value="ingenieur"),
    ]
)
async def recruit(
    ctx, country: CountryConverter, note: int, goal: int, unit_type: str = "None"
):
    """
    Commande pour recruter des membres dans le pays.

    Args:
        ctx (commands.Context): Le contexte de la commande.
        note (int): La note de recrutement.
        goal (int): L'objectif de recrutement.
        unit_type (str): Le type d'unité à recruter (par défaut "None").

    Returns:
        None
    """

    if not country.get("id"):
        return await ctx.send("Pays non trouvé.")
    if not dUtils.is_authorized(ctx):
        return await ctx.send(embed=dUtils.get_auth_embed())
    if unit_type.lower() not in unit_types.keys():
        return await ctx.send(
            "Type de recrutement invalide. Utilisez une de ces valeurs : "
            + ", ".join(unit_types.keys())
        )
    if note < 1 or note > 10:
        return await ctx.send("La note doit être entre 1 et 10.")
    if goal < 1:
        return await ctx.send("L'objectif doit être supérieur à 0.")
    recruited = int(goal * (note / 10) + random.randint(-goal // 4, goal // 10))
    if recruited < 0:
        recruited = 0
    if recruited > goal:
        recruited = goal
    if recruited > 1000:
        recruited = math.ceil(recruited / 10) * 10
    cost = db.get_pricings(unit_types.get(unit_type.lower())).get("price") * recruited
    await ctx.send(
        f"Vous avez recruté {recruited} {unit_type} pour votre pays avec une note de {note}/10 et un objectif de {goal}. \n\
Le coût total est de {convert(str(cost))}.\n\n"
    )
    confirmed = await dUtils.ask_confirmation(
        ctx,
        country.get("id"),
        f"Voulez-vous confirmer le recrutement de {recruited} {unit_type} pour {convert(str(cost))} ?",
    )
    if not confirmed:
        return
    if not db.has_enough_balance(country.get("id"), cost):
        return await ctx.send("Fonds insuffisants.")
    db.take_balance(country.get("id"), cost)
    confirmed = await dUtils.ask_confirmation(
        ctx,
        country.get("id"),
        f"Voulez-vous ajouter ces recrutements aux chiffres publics de votre pays ?",
    )
    db.add_units(country.get("id"), unit_types.get(unit_type.lower()), recruited)
    if confirmed:
        db.add_units(
            country.get("id"), f"public_{unit_types.get(unit_type.lower())}", recruited
        )
    return await ctx.send(
        f"Recrutement de {recruited} {unit_type} confirmé pour {convert(str(cost))}.\n"
    )


@bot.hybrid_command()
@app_commands.autocomplete(country=country_autocomplete)
@app_commands.choices(
    unit_type=[
        app_commands.Choice(name="Soldat", value="soldat"),
        app_commands.Choice(name="Réserve", value="reserve"),
        app_commands.Choice(name="Policier", value="policier"),
        app_commands.Choice(name="Secret", value="secret"),
        app_commands.Choice(name="Ingénieur", value="ingenieur"),
    ]
)
async def set_public_units(ctx, country: CountryConverter, unit_type: str, qty: int):
    """
    Commande pour définir le nombre d'unités publiques d'un pays.

    Args:
        ctx (commands.Context): Le contexte de la commande.
        country (CountryConverter): Le pays dont on veut définir les unités publiques.
        unit_type (str): Le type d'unité à définir.
        qty (int): La quantité d'unités à définir.

    Returns:
        None
    """

    if not country.get("id"):
        return await ctx.send("Pays non trouvé.")
    if not dUtils.is_authorized(ctx):
        return await ctx.send(embed=dUtils.get_auth_embed())
    if unit_type.lower() not in unit_types.keys():
        return await ctx.send(
            "Type d'unité invalide. Utilisez une de ces valeurs : "
            + ", ".join(unit_types.keys())
        )
    if qty < 0:
        return await ctx.send("La quantité doit être supérieure ou égale à 0.")

    db.set_units(country.get("id"), f"public_{unit_types.get(unit_type.lower())}", qty)
    return await ctx.send(
        f"Les unités publiques de {country.get('name')} pour {unit_type} ont été définies à {qty}."
    )


@bot.hybrid_command()
async def program_ghostping(
    ctx, target: Union[discord.Member, discord.Role], waiting: int = 5
):
    """
    Programme un ghost ping sur un membre ou un rôle.

    Args:
        ctx (commands.Context): Le contexte de la commande.
        target (Union[discord.Member, discord.Role]): Le membre ou le rôle à ghost pinger.
        waiting (int): Temps d'attente en secondes avant le ghost ping (par défaut 5).

    Returns:
        None
    """
    if not dUtils.is_authorized(ctx):
        return await ctx.send(embed=dUtils.get_auth_embed())

    await ctx.message.delete()  # Supprimer la commande pour éviter le spam
    message = await ctx.send(
        f"Ghost ping programmé pour {target.name} dans {waiting} secondes."
    )
    await asyncio.sleep(2)  # Laisser le temps à l'utilisateur de lire le message
    await message.delete()  # Supprimer le message de confirmation
    await asyncio.sleep(waiting)
    message = await ctx.send(f"{target.mention}")
    await asyncio.sleep(2)
    await message.delete()  # Supprimer le message de ghost ping


@bot.hybrid_command()
@app_commands.autocomplete(country=country_autocomplete)
async def test_converter(ctx, country: CountryConverter):
    """
    Teste le convertisseur de pays.

    Args:
        ctx (commands.Context): Le contexte de la commande.
        country (CountryConverter): Le pays à tester.

    Returns:
        None
    """
    if not country.get("id"):
        return await ctx.send("Pays non trouvé.")
    await ctx.send(f"Pays trouvé : {country.get('name')} (ID: {country.get('id')})")


@bot.hybrid_command()
async def sync_tree(ctx):
    """Synchronize the command tree with Discord."""
    if not dUtils.is_authorized(ctx):
        return await ctx.send(embed=dUtils.get_auth_embed())

    await bot.tree.sync()
    await ctx.send("✅ Command tree synchronized successfully.")


@bot.hybrid_command()
async def easy_tech_test(ctx, image: str = None):
    """Test command to create a technology with a simple form."""
    if not dUtils.is_authorized(ctx):
        return await ctx.send(embed=dUtils.get_auth_embed())

    tech_datas = {
        "nom": "hello",
        "niveau_technologique": "2",
        "tech_inspiration": "30",
        "type_technologie": "Char",
        "constructeur": "39",
        "masse": "129",
        "dimensions": "55",
        "equipage": "55",
        "moteurs": "55",
        "poussee": "55",
        "vitesse": "55",
        "variantes": "424",
        "autre": "433",
        "plafond": "43",
        "rayon": "32",
        "armement": "43",
        "avionique": "54",
        "materiaux": "32",
    }
    specialisation = "terrestre"  # Example tech type, replace with actual logic

    image = "https://media.discordapp.net/attachments/1397862765028442183/1397982345310769189/tech_12.png?ex=6883b404&is=68826284&hm=b17254d5f35a4875dba953afe826bdbcf418fe0d65de1513154bd9fd2316cdda&=&format=webp&quality=lossless&width=352&height=234"

    confirmed = True
    if confirmed:
        await handle_new_tech(ctx, specialisation, tech_datas, image)


async def handle_new_tech(ctx, specialisation: str, tech_datas: dict, image_url: str):
    """Handle the creation of a new technology with the provided data."""

    # Validate tech type
    if specialisation not in TechFormData.TECH_CONFIGS:
        valid_types = ", ".join(
            [k for k in TechFormData.TECH_CONFIGS.keys() if k != "common"]
        )
        return await ctx.send(
            f"Type de technologie invalide. Choisissez parmi : {valid_types}"
        )

    tech_datas["specialisation"] = specialisation
    tech_datas["tech_type"] = tech_datas.get("type_technologie")
    tech_datas.pop("type_technologie", None)  # Remove if not needed

    country = CountryEntity(ctx.author, ctx.guild).to_dict()
    if not country.get("id"):
        return await ctx.send(
            "Vous devez être dans un pays pour créer une technologie."
        )

    # Check if command was issued from public or secret channel
    country_data = db.get_country_datas(country["id"])
    is_from_secret_channel = False

    if country_data:
        public_channel_id = country_data.get("public_channel_id")
        secret_channel_id = country_data.get("secret_channel_id")

        if str(ctx.channel.id) == str(secret_channel_id):
            is_from_secret_channel = True
        elif str(ctx.channel.id) != str(public_channel_id):
            return await ctx.send(
                "❌ Cette commande doit être utilisée dans le salon public ou secret de votre pays."
            )

    # 1. Send image to CDN channel and get new URL
    cdn_channel = ctx.guild.get_channel(int(db.get_setting("cdn_channel_id")))
    if not cdn_channel:
        return await ctx.send(
            "Salon CDN non trouvé. Veuillez contacter un administrateur."
        )

    # Download and re-upload image
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(image_url) as resp:
                if resp.status == 200:
                    image_data = await resp.read()
                    # Create a file-like object
                    from io import BytesIO

                    image_file = discord.File(
                        BytesIO(image_data),
                        filename=f"tech_{tech_datas.get('nom', 'unknown')}.png",
                    )
                    cdn_message = await cdn_channel.send(
                        f"📷 Image pour la technologie: **{tech_datas.get('nom')}**",
                        file=image_file,
                    )
                    new_image_url = cdn_message.attachments[0].url
                else:
                    return await ctx.send("Impossible de télécharger l'image fournie.")
    except Exception as e:
        return await ctx.send(f"Erreur lors du traitement de l'image: {e}")

    # 2. Save technology data to JSON file
    tech_data_complete = {
        "id": f"tech_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{country['id']}",
        "country_id": country["id"],
        "country_name": country["name"],
        "tech_type": tech_datas.get("tech_type"),
        "specialisation": specialisation,
        "image_url": new_image_url,
        "created_at": datetime.now().isoformat(),
        "status": "pending_staff_review",
        "submitted_by": ctx.author.id,
        "is_secret": is_from_secret_channel,  # Track if from secret channel
        "channel_type": "secret" if is_from_secret_channel else "public",
        **tech_datas,
    }

    # Ensure the directory exists
    os.makedirs("datas/pending_techs", exist_ok=True)
    tech_file_path = f"datas/pending_techs/{tech_data_complete['id']}.json"

    with open(tech_file_path, "w", encoding="utf-8") as f:
        json.dump(tech_data_complete, f, ensure_ascii=False, indent=2)

    # 3. Create staff confirmation embed and view
    embed = discord.Embed(
        title="🔬 Nouvelle technologie à valider",
        description=f"**Pays:** {country['name']}\n**Type:** {specialisation.title()}\n**Soumis par:** {ctx.author.mention}\n**Canal:** {'🔒 Secret' if is_from_secret_channel else '🌐 Public'}",
        color=discord.Color.orange(),
    )

    # Add all tech data to embed
    for key, value in tech_datas.items():
        if value:  # Only show non-empty fields
            embed.add_field(
                name=key.replace("_", " ").title(), value=value, inline=True
            )

    embed.set_image(url=new_image_url)
    embed.set_footer(text=f"ID: {tech_data_complete['id']}")

    # Create confirmation view
    view = StaffTechConfirmationView(tech_data_complete, ctx)

    # Send to military admin notification channel
    notification_channel = ctx.guild.get_channel(int(db.get_setting("tech_channel_id")))

    if notification_channel:
        # Ping military admin role
        military_admin_role_id = usefull_role_ids_dic.get("military_admin")
        military_admin_role = (
            ctx.guild.get_role(military_admin_role_id)
            if military_admin_role_id
            else None
        )

        ping_text = (
            f"<@&{military_admin_role_id}>"
            if military_admin_role
            else "@Military Admin"
        )
        # staff_message = await notification_channel.send(f"{ping_text} Nouvelle technologie à valider:", embed=embed, view=view)
        staff_message = await notification_channel.send(
            f"Nouvelle technologie à valider:", embed=embed, view=view
        )
    else:
        return await ctx.send(
            "Salon de notification non trouvé. Veuillez contacter un administrateur."
        )

    # Notify the submitter
    await ctx.send(
        f"✅ Votre technologie **{tech_datas.get('nom')}** a été soumise pour validation par le staff!"
    )


class StaffTechConfirmationView(discord.ui.View):
    """View for staff to confirm or reject technology submissions."""

    def __init__(self, tech_data: dict, original_ctx):
        super().__init__(timeout=86400)  # 24 hours timeout
        self.tech_data = tech_data
        self.original_ctx = original_ctx

    @discord.ui.button(
        label="✅ Valider", style=discord.ButtonStyle.green, custom_id="approve"
    )
    async def approve_tech(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        """Approve the technology and proceed to difficulty rating."""
        if not any(
            role.id == usefull_role_ids_dic.get("military_admin")
            for role in interaction.user.roles
        ):
            return await interaction.response.send_message(
                "❌ Vous n'avez pas les permissions nécessaires.", ephemeral=True
            )

        # Update status
        self.tech_data["status"] = "approved"
        self.tech_data["approved_by"] = interaction.user.id
        self.tech_data["approved_at"] = datetime.now().isoformat()

        # Save updated data
        tech_file_path = f"datas/pending_techs/{self.tech_data['id']}.json"
        with open(tech_file_path, "w", encoding="utf-8") as f:
            json.dump(self.tech_data, f, ensure_ascii=False, indent=2)

        # Disable buttons
        for item in self.children:
            item.disabled = True

        embed = interaction.message.embeds[0]
        embed.color = discord.Color.green()
        embed.title = "✅ Technologie validée par le staff"

        await interaction.response.edit_message(embed=embed, view=self)

        # Show difficulty rating form
        await self.show_difficulty_rating(interaction)

    @discord.ui.button(
        label="❌ Rejeter", style=discord.ButtonStyle.red, custom_id="reject"
    )
    async def reject_tech(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        """Reject the technology and ask for feedback."""
        if not any(
            role.id == usefull_role_ids_dic.get("military_admin")
            for role in interaction.user.roles
        ):
            return await interaction.response.send_message(
                "❌ Vous n'avez pas les permissions nécessaires.", ephemeral=True
            )

        # Show rejection reason form
        modal = TechRejectionModal(self.tech_data, self.original_ctx, self)
        await interaction.response.send_modal(modal)

    async def show_difficulty_rating(self, interaction):
        """Show the difficulty rating form to determine final costs."""
        # Get average difficulty for same inspiration tech
        inspiration_name = self.tech_data.get("tech_inspiration", "").lower()
        specialisation = self.tech_data.get("specialisation")
        tech_level = int(self.tech_data.get("niveau_technologique", 1))
        tech_type = self.tech_data.get(
            "tech_type"
        )  # Fixed: was overwriting specialisation

        # Get base costs from database (await if async)
        try:
            if hasattr(db, "get_tech_datas") and callable(
                getattr(db, "get_tech_datas")
            ):
                if asyncio.iscoroutinefunction(db.get_tech_datas):
                    base_dev_cost = await db.get_tech_datas(
                        tech_type, tech_level, "dev_cost"
                    )
                    base_dev_time = await db.get_tech_datas(
                        tech_type, tech_level, "dev_time"
                    )
                    base_prod_cost = await db.get_tech_datas(
                        tech_type, tech_level, "prod_cost"
                    )
                    base_slots_taken = await db.get_tech_datas(
                        tech_type, tech_level, "slots_taken"
                    )
                else:
                    base_dev_cost = db.get_tech_datas(tech_type, tech_level, "dev_cost")
                    base_dev_time = db.get_tech_datas(tech_type, tech_level, "dev_time")
                    base_prod_cost = db.get_tech_datas(
                        tech_type, tech_level, "prod_cost"
                    )
                    base_slots_taken = db.get_tech_datas(
                        tech_type, tech_level, "slots_taken"
                    )
            else:
                base_dev_cost = [10000, 50000]
                base_dev_time = [30, 90]
                base_prod_cost = [1000, 5000]
                base_slots_taken = 1
        except Exception as e:
            print(f"Error getting tech data: {e}")
            # Fallback values
            base_dev_cost = [10000, 50000]
            base_dev_time = [30, 90]
            base_prod_cost = [1000, 5000]
            base_slots_taken = 1
        # Calculate average difficulty for similar techs (placeholder for now)
        suggested_difficulty = 5  # Default middle value
        # Create a new button to trigger the modal
        # Since we can't send modal through followup, we'll create a temporary button
        embed = discord.Embed(
            title="🎯 Évaluation de la difficulté",
            description=f"Cliquez sur le bouton ci-dessous pour évaluer la difficulté de **{self.tech_data.get('nom')}**",
            color=discord.Color.blue(),
        )
        view = TempDifficultyButtonView(
            self.tech_data,
            self.original_ctx,
            base_dev_cost,
            base_dev_time,
            base_prod_cost,
            base_slots_taken,
            suggested_difficulty,
        )
        await interaction.followup.send(embed=embed, view=view, ephemeral=True)


class TempDifficultyButtonView(discord.ui.View):
    """Temporary view with a button to show the difficulty rating modal."""

    def __init__(
        self,
        tech_data: dict,
        original_ctx,
        base_dev_cost,
        base_dev_time,
        base_prod_cost,
        base_slots_taken,
        suggested_difficulty,
    ):
        super().__init__(timeout=300)
        self.tech_data = tech_data
        self.original_ctx = original_ctx
        self.base_dev_cost = base_dev_cost
        self.base_dev_time = base_dev_time
        self.base_prod_cost = base_prod_cost
        self.base_slots_taken = base_slots_taken
        self.suggested_difficulty = suggested_difficulty

    @discord.ui.button(
        label="🎯 Évaluer la difficulté", style=discord.ButtonStyle.primary
    )
    async def show_difficulty_modal(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        """Show the difficulty rating modal."""
        if not any(
            role.id == usefull_role_ids_dic.get("military_admin")
            for role in interaction.user.roles
        ):
            return await interaction.response.send_message(
                "❌ Vous n'avez pas les permissions nécessaires.", ephemeral=True
            )

        modal = DifficultyRatingModal(
            self.tech_data,
            self.original_ctx,
            self.base_dev_cost,
            self.base_dev_time,
            self.base_prod_cost,
            self.base_slots_taken,
            self.suggested_difficulty,
        )

        await interaction.response.send_modal(modal)


class TechRejectionModal(discord.ui.Modal, title="Rejeter la technologie"):
    """Modal for staff to provide rejection feedback."""

    def __init__(self, tech_data: dict, original_ctx, parent_view):
        super().__init__()
        self.tech_data = tech_data
        self.original_ctx = original_ctx
        self.parent_view = parent_view

        self.rejection_reason = discord.ui.TextInput(
            label="Raison du rejet",
            placeholder="Expliquez pourquoi cette technologie est rejetée et ce qui doit être modifié...",
            style=discord.TextStyle.paragraph,
            max_length=1000,
            required=True,
        )
        self.add_item(self.rejection_reason)

    async def on_submit(self, interaction: discord.Interaction):
        # Update tech data
        self.tech_data["status"] = "rejected"
        self.tech_data["rejected_by"] = interaction.user.id
        self.tech_data["rejected_at"] = datetime.now().isoformat()
        self.tech_data["rejection_reason"] = self.rejection_reason.value

        # Save updated data
        tech_file_path = f"datas/pending_techs/{self.tech_data['id']}.json"
        with open(tech_file_path, "w", encoding="utf-8") as f:
            json.dump(self.tech_data, f, ensure_ascii=False, indent=2)

        # Update the staff message
        embed = interaction.message.embeds[0]
        embed.color = discord.Color.red()
        embed.title = "❌ Technologie rejetée par le staff"
        embed.add_field(
            name="Raison du rejet", value=self.rejection_reason.value, inline=False
        )

        # Disable buttons
        for item in self.parent_view.children:
            item.disabled = True

        await interaction.response.edit_message(embed=embed, view=self.parent_view)

        # Send feedback to country channel
        country_id = self.tech_data["country_id"]
        try:
            country_channel_id = db.get_country_datas(country_id).get(
                "public_channel_id"
            )
        except:
            country_channel_id = None

        print(f"Sending rejection feedback to country channel ID: {country_channel_id}")
        if country_channel_id:
            country_channel = interaction.guild.get_channel(int(country_channel_id))
            if country_channel:
                feedback_embed = discord.Embed(
                    title="❌ Technologie rejetée",
                    description=f"Votre technologie **{self.tech_data.get('nom')}** a été rejetée par le staff.",
                    color=discord.Color.red(),
                )
                feedback_embed.add_field(
                    name="Raison", value=self.rejection_reason.value, inline=False
                )
                feedback_embed.add_field(
                    name="Action requise",
                    value="Veuillez modifier votre technologie selon les commentaires et la soumettre à nouveau.",
                    inline=False,
                )

                await country_channel.send(
                    f"<@{self.tech_data['submitted_by']}>", embed=feedback_embed
                )


class DifficultyRatingModal(discord.ui.Modal, title="Notation de difficulté"):
    """Modal for staff to rate technology difficulty."""

    def __init__(
        self,
        tech_data: dict,
        original_ctx,
        base_dev_cost,
        base_dev_time,
        base_prod_cost,
        base_slots_taken,
        suggested_difficulty,
    ):
        super().__init__()
        self.tech_data = tech_data
        self.original_ctx = original_ctx
        self.base_dev_cost = base_dev_cost
        self.base_dev_time = base_dev_time
        self.base_prod_cost = base_prod_cost
        self.base_slots_taken = base_slots_taken

        self.difficulty_rating = discord.ui.TextInput(
            label="Note de difficulté (1-10)",
            placeholder=f"Suggestion: {suggested_difficulty} (basé sur des techs similaires)",
            default=str(suggested_difficulty),
            max_length=2,
            required=True,
        )
        self.add_item(self.difficulty_rating)

    async def on_submit(self, interaction: discord.Interaction):
        try:
            difficulty = int(self.difficulty_rating.value)
            if difficulty < 1 or difficulty > 10:
                return await interaction.response.send_message(
                    "❌ La note doit être entre 1 et 10.", ephemeral=True
                )
        except ValueError:
            return await interaction.response.send_message(
                "❌ Veuillez entrer un nombre valide.", ephemeral=True
            )

        # Calculate final costs based on difficulty
        # Formula: final_cost = min_cost + (max_cost - min_cost) * (difficulty - 1) / 9
        def calculate_final_value(base_range, difficulty_rating, default_value):
            if isinstance(base_range, (list, tuple)) and len(base_range) == 2:
                min_val, max_val = base_range
                return int(min_val + (max_val - min_val) * (difficulty_rating - 1) / 9)
            elif isinstance(base_range, (int, float)) and base_range is not None:
                return int(base_range)
            else:
                return default_value

        final_dev_cost = calculate_final_value(self.base_dev_cost, difficulty, 25000)
        final_dev_time = calculate_final_value(self.base_dev_time, difficulty, 60)
        final_prod_cost = calculate_final_value(self.base_prod_cost, difficulty, 3000)
        final_slots_taken = (
            self.base_slots_taken if self.base_slots_taken is not None else 1
        )

        # Update tech data
        self.tech_data.update(
            {
                "difficulty_rating": difficulty,
                "final_dev_cost": final_dev_cost,
                "final_dev_time": final_dev_time,
                "final_prod_cost": final_prod_cost,
                "final_slots_taken": final_slots_taken,
                "status": "awaiting_final_confirmation",
            }
        )

        # Save updated data
        tech_file_path = f"datas/pending_techs/{self.tech_data['id']}.json"
        with open(tech_file_path, "w", encoding="utf-8") as f:
            json.dump(self.tech_data, f, ensure_ascii=False, indent=2)

        # Show final confirmation
        embed = discord.Embed(
            title="🎯 Confirmation finale de la technologie",
            description=f"**{self.tech_data.get('nom')}** - Note de difficulté: {difficulty}/10",
            color=discord.Color.blue(),
        )

        embed.add_field(
            name="💰 Coût de développement", value=f"{final_dev_cost:,}", inline=True
        )
        embed.add_field(
            name="⏱️ Temps de développement",
            value=f"{final_dev_time} jours",
            inline=True,
        )
        embed.add_field(
            name="🏭 Coût de production", value=f"{final_prod_cost:,}", inline=True
        )
        embed.add_field(
            name="🔧 Slots occupés", value=str(final_slots_taken), inline=True
        )

        embed.set_image(url=self.tech_data["image_url"])

        view = FinalTechConfirmationView(self.tech_data)

        await interaction.response.send_message(embed=embed, view=view)


class FinalTechConfirmationView(discord.ui.View):
    """Final confirmation view for technology creation."""

    def __init__(self, tech_data: dict):
        super().__init__(timeout=3600)  # 1 hour timeout
        self.tech_data = tech_data

    @discord.ui.button(label="✅ Créer la technologie", style=discord.ButtonStyle.green)
    async def create_technology(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        """Create the technology in the database."""
        if not any(
            role.id == usefull_role_ids_dic.get("military_admin")
            for role in interaction.user.roles
        ):
            return await interaction.response.send_message(
                "❌ Vous n'avez pas les permissions nécessaires.", ephemeral=True
            )

        # Add to database
        try:
            # Map specialisation to database-compatible values
            specialisation_mapping = {
                "terrestre": "Terrestre",
                "aerienne": "Aerienne",
                "navale": "Navale",
                "armes": "NA",  # Assuming "armes" maps to "NA" based on constraint
            }

            db_specialisation = specialisation_mapping.get(
                self.tech_data.get("specialisation", "").lower(),
                "NA",  # Default fallback
            )

            success = db.add_technology(
                name=self.tech_data.get("nom"),
                inspiration_name=self.tech_data.get("tech_inspiration"),
                specialisation=db_specialisation,  # Use mapped value
                tech_type=self.tech_data.get("tech_type"),
                tech_level=int(self.tech_data.get("niveau_technologique", 1)),
                country_id=self.tech_data.get("country_id"),
                dev_cost=self.tech_data.get("final_dev_cost"),
                dev_time=self.tech_data.get("final_dev_time"),
                prod_cost=self.tech_data.get("final_prod_cost"),
                slots_taken=self.tech_data.get("final_slots_taken"),
                image_url=self.tech_data.get("image_url"),
                tech_data=self.tech_data,  # Store all form data
            )

            print(f"Database add_technology result: {success}")  # Debug log

        except Exception as e:
            print(f"Error adding technology to database: {e}")
            success = False

        if success:
            # Update status
            self.tech_data["status"] = "created"
            self.tech_data["created_in_db_at"] = datetime.now().isoformat()

            old_path = f"datas/pending_techs/{self.tech_data['id']}.json"

            print(f"Removing old tech file: {old_path}")  # Debug log
            print(f"Tech data to be removed: {self.tech_data}")  # Debug log
            if os.path.exists(old_path):
                os.remove(old_path)

            # Disable button
            button.disabled = True
            await interaction.response.edit_message(view=self)

            # Notify success
            await interaction.followup.send(
                f"✅ Technologie **{self.tech_data.get('nom')}** créée avec succès dans la base de données!"
            )

            # Notify country - use appropriate channel based on where it was submitted
            country_id = self.tech_data["country_id"]
            is_secret = self.tech_data.get("is_secret", False)
            country_data = db.get_country_datas(country_id)

            if country_data:
                if is_secret:
                    # Use secret channel
                    country_channel_id = country_data.get("secret_channel_id")
                else:
                    # Use public channel
                    country_channel_id = country_data.get("public_channel_id")

                if country_channel_id:
                    country_channel = interaction.guild.get_channel(
                        int(country_channel_id)
                    )
                    if country_channel:
                        success_embed = discord.Embed(
                            title="🎉 Technologie approuvée!",
                            description=f"Votre technologie **{self.tech_data.get('nom')}** a été officiellement créée!",
                            color=discord.Color.green(),
                        )
                        success_embed.add_field(
                            name="💰 Coût de développement",
                            value=f"{self.tech_data.get('final_dev_cost'):,}",
                            inline=True,
                        )
                        success_embed.add_field(
                            name="⏱️ Temps de développement",
                            value=f"{self.tech_data.get('final_dev_time')} jours",
                            inline=True,
                        )
                        success_embed.set_image(url=self.tech_data.get("image_url"))
                        success_embed.set_footer(text=f"ID: {self.tech_data['id']}")

                        await country_channel.send(
                            f"<@{self.tech_data['submitted_by']}>", embed=success_embed
                        )
        else:
            await interaction.response.send_message(
                "❌ Erreur lors de la création de la technologie en base de données.",
                ephemeral=True,
            )

    @discord.ui.button(label="❌ Annuler", style=discord.ButtonStyle.red)
    async def cancel_creation(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        """Cancel the technology creation."""
        if not any(
            role.id == usefull_role_ids_dic.get("military_admin")
            for role in interaction.user.roles
        ):
            return await interaction.response.send_message(
                "❌ Vous n'avez pas les permissions nécessaires.", ephemeral=True
            )

        # Update status
        self.tech_data["status"] = "cancelled"
        self.tech_data["cancelled_at"] = datetime.now().isoformat()

        tech_file_path = f"datas/pending_techs/{self.tech_data['id']}.json"
        with open(tech_file_path, "w", encoding="utf-8") as f:
            json.dump(self.tech_data, f, ensure_ascii=False, indent=2)

        # Disable buttons
        for item in self.children:
            item.disabled = True

        await interaction.response.edit_message(view=self)
        await interaction.followup.send("❌ Création de la technologie annulée.")


@bot.hybrid_command()
async def annex(ctx, region_id):
    return


@bot.hybrid_command()
@app_commands.autocomplete(country=country_autocomplete)
async def add_player_to_country(ctx, user: discord.Member, country: CountryConverter):
    return


@bot.hybrid_command()
@app_commands.autocomplete(country=country_autocomplete)
async def remove_player_from_country(
    ctx, user: discord.Member, country: CountryConverter
):
    return


@bot.hybrid_command()
@app_commands.autocomplete(country=country_autocomplete)
async def add_region(
    ctx,
    region_name: str,
    map_name: str,
    population: int,
    country: CountryConverter = None,
):
    return


@bot.hybrid_command()
@app_commands.autocomplete(region_id=region_autocomplete)
async def remove_region(ctx, region_id: int):
    return


@bot.hybrid_command()
@app_commands.autocomplete(region_id=region_autocomplete)
async def set_region_data(ctx, region_id: int, key: str, value: str):
    return


# Add missing database methods if they don't exist
def ensure_db_methods():
    """Ensure required database methods exist."""
    if not hasattr(db, "execute_query"):

        def execute_query(query, params=None):
            """Execute a query and return results."""
            try:
                if params:
                    db.cur.execute(query, params)
                else:
                    db.cur.execute(query)

                # If it's a SELECT query, return results
                if query.strip().upper().startswith("SELECT"):
                    return db.cur.fetchall()
                else:
                    # For INSERT, UPDATE, DELETE, commit the transaction
                    db.conn.commit()
                    return db.cur.rowcount
            except Exception as e:
                print(f"Database query error: {e}")
                return None

        db.execute_query = execute_query

    if not hasattr(db, "get_country_channel"):

        def get_country_channel(country_id):
            """Get country channel ID from database."""
            try:
                result = db.execute_query(
                    "SELECT channel_id FROM Countries WHERE id = ?", (country_id,)
                )
                return result[0][0] if result else None
            except Exception as e:
                print(f"Error getting country channel: {e}")
                # Try alternative column names
                try:
                    result = db.execute_query(
                        "SELECT public_channel_id FROM Countries WHERE id = ?",
                        (country_id,),
                    )
                    return result[0][0] if result else None
                except:
                    return None

        db.get_country_channel = get_country_channel

    if not hasattr(db, "add_technology"):

        def add_technology(
            name,
            inspiration_name=None,
            specialisation=None,
            tech_type=None,
            tech_level=1,
            country_id=None,
            dev_cost=0,
            dev_time=0,
            prod_cost=0,
            slots_taken=1,
            image_url=None,
            tech_data=None,
        ):
            """Add technology to database."""
            try:
                # Check if Technologies table exists, if not create a basic one that matches the schema
                db.execute_query(
                    """
                    CREATE TABLE IF NOT EXISTS Technologies (
                        tech_id INTEGER PRIMARY KEY AUTOINCREMENT,
                        name TEXT NOT NULL,
                        cost INTEGER NOT NULL DEFAULT 0,
                        specialisation TEXT NOT NULL CHECK (specialisation IN ('Terrestre', 'Aerienne', 'Navale', 'NA')) DEFAULT 'NA',
                        development_time INTEGER NOT NULL DEFAULT 0,
                        development_cost INTEGER NOT NULL DEFAULT 0,
                        slots_taken FLOAT NOT NULL DEFAULT 1.0,
                        original_name TEXT NOT NULL,
                        technology_level INTEGER NOT NULL DEFAULT 1 CHECK (technology_level >= 1 AND technology_level <= 11),
                        image_url TEXT,
                        developed_by INTEGER,
                        exported BOOLEAN DEFAULT FALSE,
                        type TEXT NOT NULL,
                        description TEXT,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (developed_by) REFERENCES Countries(country_id) ON DELETE SET NULL
                    )
                """
                )

                # Insert technology with proper mapping to database schema
                query = """
                INSERT INTO Technologies (
                    name, cost, specialisation, development_time, 
                    development_cost, slots_taken, original_name, technology_level, 
                    image_url, developed_by, type, description
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """

                # Map the parameters to the database schema
                mapped_specialisation = (
                    specialisation
                    if specialisation in ["Terrestre", "Aerienne", "Navale", "NA"]
                    else "NA"
                )

                db.execute_query(
                    query,
                    (
                        name,  # name
                        prod_cost or 0,  # cost (production cost)
                        mapped_specialisation,  # specialisation
                        dev_time or 0,  # development_time
                        dev_cost or 0,  # development_cost
                        float(slots_taken) if slots_taken else 1.0,  # slots_taken
                        inspiration_name or name,  # original_name
                        tech_level or 1,  # technology_level
                        image_url,  # image_url
                        country_id,  # developed_by
                        tech_type or "unknown",  # type
                        (
                            json.dumps(tech_data) if tech_data else None
                        ),  # description (storing JSON data)
                    ),
                )
                print(f"Technology {name} added successfully to database")
                return True
            except Exception as e:
                print(f"Error adding technology: {e}")
                return False

        db.add_technology = add_technology

    if not hasattr(db, "get_tech_datas"):

        def get_tech_datas(tech_type, tech_level, data_type):
            """Get technology data ranges from database."""
            try:
                # This is a placeholder implementation
                # You should replace this with actual database queries
                base_costs = {
                    "dev_cost": {
                        1: [5000, 15000],
                        2: [10000, 30000],
                        3: [20000, 60000],
                        4: [40000, 120000],
                        5: [80000, 240000],
                    },
                    "dev_time": {
                        1: [15, 45],
                        2: [30, 90],
                        3: [60, 180],
                        4: [120, 360],
                        5: [240, 720],
                    },
                    "prod_cost": {
                        1: [500, 1500],
                        2: [1000, 3000],
                        3: [2000, 6000],
                        4: [4000, 12000],
                        5: [8000, 24000],
                    },
                    "slots_taken": {
                        1: 1,
                        2: 1,
                        3: 2,
                        4: 2,
                        5: 3,
                    },
                }

                # Ensure tech_level is within bounds and convert to int
                try:
                    tech_level = int(tech_level)
                except (ValueError, TypeError):
                    tech_level = 1
                tech_level = max(1, min(tech_level, 5))

                if data_type in base_costs and tech_level in base_costs[data_type]:
                    result = base_costs[data_type][tech_level]
                    print(
                        f"get_tech_datas({tech_type}, {tech_level}, {data_type}) = {result}"
                    )
                    return result
                else:
                    # Default fallback values
                    if data_type == "dev_cost":
                        return [10000, 50000]
                    elif data_type == "dev_time":
                        return [30, 90]
                    elif data_type == "prod_cost":
                        return [1000, 5000]
                    elif data_type == "slots_taken":
                        return 1

            except Exception as e:
                print(f"Error getting tech data: {e}")
                # Return safe defaults
                if data_type == "dev_cost":
                    return [10000, 50000]
                elif data_type == "dev_time":
                    return [30, 90]
                elif data_type == "prod_cost":
                    return [1000, 5000]
                elif data_type == "slots_taken":
                    return 1

        db.get_tech_datas = get_tech_datas


# Call the helper function to ensure methods exist
ensure_db_methods()


@bot.hybrid_command(
    name="exponential",
    brief="Génère une progression exponentielle de valeurs.",
    usage="exponential <start> <target> <steps>",
    description="Génère une liste de valeurs d'une exponentielle de X à Y.",
    help="""Génère une liste de valeurs suivant une progression exponentielle.

    FONCTIONNALITÉ :
    - Calcule des valeurs exponentielles entre un point de départ et un point cible
    - Utile pour des applications nécessitant des progressions exponentielles

    ARGUMENTS :
    - `<start>` : Point de départ (doit être différent de 0)
    - `<target>` : Point cible
    - `<steps>` : Nombre d'étapes à générer

    EXEMPLE :
    - `exponential 100 1000 5` : Génère 6 valeurs entre 100 et 1000
    """,
)
async def exponential(
    ctx,
    start: float = commands.parameter(
        description="Point de départ de la progression exponentielle"
    ),
    target: float = commands.parameter(
        description="Point cible de la progression exponentielle"
    ),
    steps: int = commands.parameter(
        description="Nombre d'étapes à générer (au moins 1)"
    ),
) -> None:
    if start == 0:
        raise ValueError(
            "Le point de départ ne peut pas être 0 pour une progression exponentielle."
        )
    if steps < 1:
        raise ValueError("Le nombre d'étapes doit être au moins 1.")

    r = (target / start) ** (1 / steps)
    values = [start * (r**i) for i in range(steps + 1)]
    values_str = ", ".join(f"{v:.2f}" for v in values)
    await ctx.send(f"Valeurs générées : {values_str}")


@bot.hybrid_command()
async def date_difference(ctx, date):
    """Calculer la différence en jours entre deux dates au format YYYY-MM."""
    date_dict = db.get_current_date()
    year, month = (
        date_dict.get("year", 1),
        date_dict.get("month", 1),
    )
    current_date = f"{year:04d}-{month:02d}"
    date1 = current_date
    date2 = date.strip()
    try:
        months_diff = get_date_difference(date1, date2)
        await ctx.send(
            f"La différence entre {date1} et {date2} est de {months_diff} mois."
        )
    except ValueError as e:
        await ctx.send(f"Erreur : {e}")


@bot.hybrid_command(
    name="get_old_date", description="Récupère la date du jeu à partir d'une date IRL."
)
async def get_old_date(ctx, date):
    date_dict = db.get_date_from_irl(date)
    if date_dict:
        year = date_dict.get("year", 1)
        month = date_dict.get("month", 1)
        playday = date_dict.get("playday", 1)
        await ctx.send(f"Date du jeu : {year:04d}-{month:02d}-{playday:02d}")
    else:
        await ctx.send("Date non trouvée.")


def get_date_difference(date1: str, date2: str) -> int:
    """Calculate the difference in months between two dates."""
    date_format = "%Y-%m"
    d1 = datetime.strptime(date1, date_format)
    d2 = datetime.strptime(date2, date_format)
    return (d2.year - d1.year) * 12 + (d2.month - d1.month)


async def counter_func():
    cur.execute(f"SELECT PIB FROM country")
    top_data = cur.fetchall()
    tt = 0
    embed = discord.Embed(title=f"Total PIBs cumulés :", description="")
    if top_data:
        for data in top_data:
            value = data[0]
            if isinstance(value, str):
                try:
                    tt += int(value)
                except:
                    pass
            else:
                tt += value
        embed.description = f"{tt}\n{convert(str(tt))}"
    else:
        embed.title = "Aucune donnée trouvée pour la colonne spécifiée."
    return embed


async def counter_func2():
    cur.execute("SELECT PIB FROM country")
    top_data = cur.fetchall()
    tt = 0
    if top_data:
        for data_tuple in top_data:
            data = data_tuple[0]  # Unpack the tuple to get the actual value
            if isinstance(data, str):
                try:
                    tt += int(data)
                except:
                    pass
            else:
                tt += data
        return tt
    else:
        return 0


@bot.hybrid_command()
async def counter(ctx):
    embed = await counter_func()  # Call the function to get the Embed object
    await ctx.send(embed=embed)  # Send the Embed object as a message


@bot.hybrid_command()
@app_commands.autocomplete(country=country_autocomplete)
async def power_checker(ctx, country: CountryConverter):
    if not country:
        return await ctx.send("Pays invalide.")
    country_gdp = await db.get_country_gdp(country.get("id"))
    state = "une Non Puissance"
    if country_gdp:
        total_value = await db.get_worlds_gdp()
        states = {
            int(0.15 * total_value): "une Superpuissance",
            int(0.065 * total_value): "une Grande Puissance",
            int(0.025 * total_value): "une Puissance majeure",
            int(0.002 * total_value): "une Puissance mineure",
        }
        for i in states.keys():
            if country_gdp > i:
                state = states[i]
                break
    else:
        state = "un Pays Invalide"
    return await ctx.send(f"Le pays {country.get('name')} est **{state}**")


@bot.hybrid_command()
@app_commands.autocomplete(country=country_autocomplete)
async def edit_country_stats(ctx, country: CountryConverter, stat: str, value: str):
    """Modifie les statistiques d'un pays."""
    if not country:
        return await ctx.send("Pays invalide.")

    # Validate stat
    valid_stats = ["population", "gdp", "military_strength"]
    if stat not in valid_stats:
        return await ctx.send(
            f"Statistique invalide. Choisissez parmi : {', '.join(valid_stats)}"
        )

    try:
        # Convert value to appropriate type
        if stat == "population":
            value = int(value)
        elif stat == "gdp":
            value = float(value)
        elif stat == "military_strength":
            value = int(value)

        # Update the country's stats in the database
        success = db.update_country_stat(country.get("id"), stat, value)
        if success:
            return await ctx.send(
                f"Statistique `{stat}` du pays {country.get('name')} mise à jour à {value}."
            )
        else:
            return await ctx.send(
                "Erreur lors de la mise à jour des statistiques du pays."
            )
    except ValueError:
        return await ctx.send("Valeur invalide pour la statistique spécifiée.")


bot.run(token)
