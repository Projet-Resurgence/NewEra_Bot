"""
Discord utilities for NEBot.
Contains helper functions for discord commands.
"""

import asyncio
import discord

# The bot instance must be set at runtime (e.g. by main.py)

class discordUtils:
    """
    A utility class for Discord-related functions.
    This class provides methods to check user authorization, send messages, and handle reactions.
    """

    def __init__(self, bot, db):
        self.bot = bot
        self.db = db

    def is_authorized(self, ctx) -> bool:
        authorized_role_id = 1124057695276773426
        return authorized_role_id in [role.id for role in ctx.author.roles]

    async def discord_input(self, ctx, message: str) -> str:
        await ctx.send(message)
        try:
            response = await self.bot.wait_for(
                "message",
                check=lambda m: m.author == ctx.author and m.channel == ctx.channel,
                timeout=90,
            )
        except asyncio.TimeoutError:
            return ""
        return response.content

    async def send_long_message(self, ctx, message: str):
        messages = []
        while len(message) > 2000:
            index = message.rfind("\n", 0, 2000)
            messages.append(message[:index])
            message = message[index:]
        messages.append(message)
        for msg in messages:
            await ctx.send(msg)

    def get_auth_embed(self) -> discord.Embed:
        """
        Creates a Discord embed message indicating lack of authorization.

        This function generates an embed message that informs the user they are not authorized to execute a command and that they need to be a staff member.

        Returns:
            discord.Embed: The embed message with the authorization error.
        """
        embed = discord.Embed(
            title="Vous n'êtes pas autorisé à effectuer cette commande.",
            description="Il vous faut être staff",
            color=error_color_int,
        )
        return embed

    async def get_users_by_reaction(self, emoji: list, message: discord.Message):
        """
        Retrieve a list of users who reacted to a message with specific emojis.

        Args:
            emoji (list): A list of emojis to check for reactions.
            message (discord.Message): The Discord message to check reactions on.

        Returns:
            list: A list of users who reacted with the specified emojis.
        """
        users = []
        for reaction in message.reactions:
            if reaction.emoji in emoji:
                async for user in reaction.users():
                    users.append(user)
        return users

    def parse_embed_json(json_file):
        embeds_json = json.loads(json_file)["embeds"]

        for embed_json in embeds_json:
            embed = discord.Embed().from_dict(embed_json)
            yield embed

    async def get_channel_context(
        self, channel: discord.TextChannel, messageLimit: discord.Message
    ) -> str:
        """Récupère le contexte du salon pour la synthèse, y compris les messages webhook et embeds complexes."""
        context_lines = []

        async for message in channel.history(limit=100, oldest_first=False):
            if message.author.id == self.bot.user.id:
                continue

            # Inclure le message limite, puis couper juste après
            context_included = message.id == messageLimit.id

            # Détermination du nom d’auteur
            author_name = (
                message.author.name if message.webhook_id else message.author.display_name
            )
            
            if (message.content.startswith("[") or message.content.startswith("(")) and (message.content.endswith(")") or message.content.endswith("]")):
                continue  # Ignore messages that are wrapped in brackets or parentheses

            # Contenu brut
            if message.content.strip():
                context_lines.append(f"{author_name}: {message.content.strip()}")

            # Contenu embed
            for embed in message.embeds:
                lines = [f"{author_name} (embed):"]
                if embed.title:
                    lines.append(f"  Titre : {embed.title}")
                if embed.description:
                    lines.append(f"  Description : {embed.description}")
                for field in embed.fields:
                    lines.append(f"  {field.name}: {field.value}")
                if embed.footer and embed.footer.text:
                    lines.append(f"  [Footer] {embed.footer.text}")
                if embed.author and embed.author.name:
                    lines.append(f"  [Auteur] {embed.author.name}")
                context_lines.append("\n".join(lines))

            if context_included:
                break
            
            if len("\n".join(context_lines)) > 8000:
                break

        return "\n".join(reversed(context_lines))

    async def ask_confirmation(self, ctx, prompted_country: str, question):
        """
        Asks the user for confirmation with a yes/no question,
        Waiting for a whitecheck reaction under the question message.

        Args:
            ctx (commands.Context): The context of the command.
            question (str): The question to ask the user.

        Returns:
            bool: True if the user confirms, False otherwise.
        """
        embed = discord.Embed(
            title="Confirmation",
            description=question,
            color=0x00FF00,  # Green color for confirmation
        )
        message = await ctx.send(embed=embed)
        await message.add_reaction("✅")
        await message.add_reaction("❌")

        def check(reaction, user):
            return (
                self.db.has_permission(prompted_country, user.id, "can_recruit")
                and str(reaction.emoji) in ["✅", "❌"]
                and reaction.message.id == message.id
            )

        try:
            reaction, user = await self.bot.wait_for(
                "reaction_add", timeout=60.0, check=check
            )
            return str(reaction.emoji) == "✅"
        except asyncio.TimeoutError:
            await ctx.send("⏰ Temps écoulé pour la confirmation.")
            return False