"""
Technology commands cog for NEBot.
Contains all technology development and management commands.
"""

import discord
from discord.ext import commands
from discord import app_commands
from typing import Union
import json
import os
import asyncio
import aiohttp
from datetime import datetime
from io import BytesIO

# Import centralized utilities
from shared_utils import (
    get_db,
    get_discord_utils,
    CountryEntity,
    CountryConverter,
    country_autocomplete,
    structure_autocomplete,
    technocentre_autocomplete,
    factory_autocomplete,
    technology_autocomplete,
    ERROR_COLOR_INT,
    MONEY_COLOR_INT,
    FACTORY_COLOR_INT,
    convert,
    amount_converter,
)


class TechFormData:
    """Configuration data for different technology forms loaded from JSON"""

    @staticmethod
    def load_tech_configs():
        """Load tech configurations from JSON file."""
        import json

        try:
            with open("datas/tech_form_datas.json", "r", encoding="utf-8") as f:
                raw_configs = json.load(f)

            # Convert color strings to discord.Color objects
            configs = {}
            for tech_type, config in raw_configs.items():
                configs[tech_type] = {
                    "title": config["title"],
                    "color": getattr(discord.Color, config["color"])(),
                    "color_completed": getattr(
                        discord.Color, config["color_completed"]
                    )(),
                    "emoji": config["emoji"],
                    "forms": config["forms"],
                    "accepted_types": config.get("accepted_types", []),
                }
            return configs
        except FileNotFoundError:
            print("⚠️ tech_form_datas.json not found, using empty config")
            return {}
        except Exception as e:
            print(f"⚠️ Error loading tech_form_datas.json: {e}")
            return {}

    # Load configurations on class initialization
    TECH_CONFIGS = load_tech_configs()


class TechTypeSelectView(discord.ui.View):
    """View with a SelectMenu for choosing technology type."""

    def __init__(
        self,
        accepted_types: list,
        tech_type: str,
        form_index: int,
        form_data: dict,
        parent_view=None,
        callback=None,
    ):
        super().__init__(timeout=300)
        self.tech_type = tech_type
        self.form_index = form_index
        self.form_data = form_data
        self.parent_view = parent_view
        self.callback = callback

        # Create options from accepted_types
        options = []
        for tech_type_option in accepted_types:
            # Convert snake_case to human readable
            display_name = tech_type_option.replace("_", " ").title()
            options.append(
                discord.SelectOption(
                    label=display_name,
                    value=tech_type_option,
                    description=f"Choisir {display_name}",
                )
            )

        self.type_select = discord.ui.Select(
            placeholder="Choisissez le type de technologie...", options=options
        )
        self.type_select.callback = self.on_type_select
        self.add_item(self.type_select)

    async def on_type_select(self, interaction: discord.Interaction):
        """Handle type selection and continue with the form."""
        selected_type = self.type_select.values[0]

        # Convert back to display name for storage
        display_name = selected_type.replace("_", " ").title()
        self.form_data["type_technologie"] = display_name

        if self.callback:
            await self.callback(interaction, selected_type)


class UniversalTechForm(discord.ui.Modal):
    """Universal modal form that adapts based on configuration."""

    def __init__(
        self, tech_type: str, form_index: int, form_data: dict, parent_view=None
    ):
        config = TechFormData.TECH_CONFIGS[tech_type]
        common_config = TechFormData.TECH_CONFIGS.get("common", {"forms": []})

        # Combine common fields first, then tech-specific fields
        all_forms = common_config["forms"] + config["forms"]

        # Auto-split forms into groups of 5
        forms_per_page = 5
        start_idx = form_index * forms_per_page
        end_idx = start_idx + forms_per_page
        current_forms = all_forms[start_idx:end_idx]

        title = f"{config['title']} - Partie {form_index + 1}"
        super().__init__(title=title, timeout=None)

        self.tech_type = tech_type
        self.form_index = form_index
        self.form_data = form_data
        self.parent_view = parent_view

        # Create TextInput fields following ConstructionForm pattern
        self.fields = []
        self.has_type_field = False
        self.type_field_config = None

        for field_config in current_forms:
            # Skip type_technologie field as it will be handled by SelectMenu
            if field_config["key"] == "type_technologie":
                self.has_type_field = True
                self.type_field_config = field_config
                continue

            field = discord.ui.TextInput(
                label=field_config["label"],
                placeholder=field_config["placeholder"],
                max_length=300,
                style=discord.TextStyle.short,
                required=False,
            )
            setattr(self, f"field_{field_config['key']}", field)
            self.fields.append((field_config["key"], field))
            self.add_item(field)

    async def on_submit(self, interaction: discord.Interaction):
        """Handle form submission and update parent view."""
        # Collect field values
        for key, field in self.fields:
            self.form_data[key] = field.value

        # Mark this form as completed in parent view
        if self.parent_view:
            self.parent_view.mark_form_completed(self.form_index)

        embed = interaction.message.embeds[0] if interaction.message.embeds else None
        if not embed:
            embed = discord.Embed(
                title=f"✅ Formulaire {self.form_index + 1} complété",
                description="Données sauvegardées avec succès !",
                color=TechFormData.TECH_CONFIGS[self.tech_type]["color_completed"],
            )

        await interaction.response.edit_message(embed=embed, view=self.parent_view)


class MultiFormView(discord.ui.View):
    """Universal view that handles tech types with auto-splitting forms."""

    def __init__(
        self,
        specialisation: str,
        ctx: commands.Context,
        image_url: str,
        technocentre_id: int = None,
    ):
        super().__init__(timeout=300)
        self.specialisation = specialisation
        self.config = TechFormData.TECH_CONFIGS[specialisation]
        self.common_config = TechFormData.TECH_CONFIGS.get("common", {"forms": []})
        self.form_data = {}
        self.ctx = ctx
        self.image_url = image_url
        self.technocentre_id = (
            technocentre_id  # NEW: Store the technocentre for development
        )

        # Calculate number of forms needed (auto-split by 5)
        # Include common fields + tech-specific fields
        total_fields = len(self.common_config["forms"]) + len(self.config["forms"])
        self.num_forms = (total_fields + 4) // 5  # Ceiling division
        self.completed_forms = set()

        # Create buttons in a single row
        for i in range(self.num_forms):
            button = discord.ui.Button(
                label=f"Partie {i + 1} / {self.num_forms}",
                style=discord.ButtonStyle.green,
                custom_id=f"form_{i}",
                row=0,
            )

            # Create callback using closure
            def create_callback(form_index):
                async def button_callback(interaction):
                    # Check if this form contains the type_technologie field
                    config = TechFormData.TECH_CONFIGS[self.specialisation]
                    common_config = TechFormData.TECH_CONFIGS.get(
                        "common", {"forms": []}
                    )
                    all_forms = common_config["forms"] + config["forms"]

                    forms_per_page = 5
                    start_idx = form_index * forms_per_page
                    end_idx = start_idx + forms_per_page
                    current_forms = all_forms[start_idx:end_idx]

                    # Check if any form in this page has type_technologie
                    has_type_field = any(
                        field["key"] == "type_technologie" for field in current_forms
                    )

                    if has_type_field and "type_technologie" not in self.form_data:
                        # Show SelectMenu first for type selection
                        accepted_types = config.get("accepted_types", [])
                        if accepted_types:

                            async def continue_with_form(
                                select_interaction, selected_type
                            ):
                                # After type selection, show the modal
                                await select_interaction.response.send_modal(
                                    UniversalTechForm(
                                        self.specialisation,
                                        form_index,
                                        self.form_data,
                                        self,
                                    )
                                )

                            embed = discord.Embed(
                                title=f"🔧 Sélection du type - {config['title']}",
                                description="Veuillez d'abord choisir le type de technologie :",
                                color=config["color"],
                            )

                            view = TechTypeSelectView(
                                accepted_types,
                                self.specialisation,
                                form_index,
                                self.form_data,
                                self,
                                continue_with_form,
                            )

                            await interaction.response.send_message(
                                embed=embed, view=view, ephemeral=True
                            )
                            return

                    # Normal flow - show modal directly
                    await interaction.response.send_modal(
                        UniversalTechForm(
                            self.specialisation, form_index, self.form_data, self
                        )
                    )

                return button_callback

            button.callback = create_callback(i)
            self.add_item(button)

    def mark_form_completed(self, form_index: int):
        """Mark a form as completed and update button appearance."""
        self.completed_forms.add(form_index)

        # Update button to dark green and make unclickable
        for item in self.children:
            if hasattr(item, "custom_id") and item.custom_id == f"form_{form_index}":
                item.style = discord.ButtonStyle.secondary
                item.label = f"✅ Formulaire {form_index + 1}"
                item.disabled = True
                break

        if self.all_forms_completed():
            asyncio.create_task(
                self.send_summary()
            )  # Use create_task because we're not in async

    def all_forms_completed(self) -> bool:
        """Check if all forms have been completed."""
        return len(self.completed_forms) == self.num_forms

    async def send_summary(self):
        summary_lines = [
            f"📦 **Résumé de la technologie `{self.config['title']}` :**\n"
        ]

        print(f"Form data collected: {self.form_data}")
        print(f"Sending to ctx: {self.ctx.message.channel.id}")

        try:
            # Get the database instance
            db = get_db()
            dUtils = get_discord_utils()

            # Combine common and tech-specific fields for summary
            all_fields = self.common_config["forms"] + self.config["forms"]
            country_entity = CountryEntity(self.ctx.author, self.ctx.guild)
            country_id = country_entity.get_country_id()

            # Get tech type and level from form data
            tech_type = self.form_data.get("type_technologie")
            tech_level_str = self.form_data.get("niveau_technologique", "1")

            # Ensure tech_level is an integer
            try:
                tech_level = int(tech_level_str)
            except (ValueError, TypeError):
                tech_level = 1
                print(
                    f"Warning: Invalid tech_level '{tech_level_str}', defaulting to 1"
                )

            print(f"Getting tech data for type: {tech_type}, level: {tech_level}")

            # Get costs with error handling
            try:
                dev_cost = await db.get_tech_datas(tech_type, tech_level, "dev_cost")
                dev_time = await db.get_tech_datas(tech_type, tech_level, "dev_time")
                prod_cost = await db.get_tech_datas(tech_type, tech_level, "prod_cost")
                slots_taken = await db.get_tech_datas(
                    tech_type, tech_level, "slots_taken"
                )
            except Exception as e:
                print(f"Error getting tech data from database: {e}")
                # Fallback values
                dev_cost = [10000, 50000]
                dev_time = [30, 90]
                prod_cost = [1000, 5000]
                slots_taken = 1

            print(
                f"dev_cost: {dev_cost}, dev_time: {dev_time}, prod_cost: {prod_cost}, slots_taken: {slots_taken}"
            )

            # Add form data to summary
            for key, value in self.form_data.items():
                label = next((f["label"] for f in all_fields if f["key"] == key), key)
                summary_lines.append(f"• **{label}** : {value or '*Non renseigné*'}")

            # Add cost information with safe formatting
            try:
                if isinstance(dev_cost, (list, tuple)) and len(dev_cost) >= 2:
                    summary_lines.append(
                        f"**Coût de développement** : entre {dev_cost[0]:,} et {dev_cost[1]:,}"
                    )
                else:
                    summary_lines.append(f"**Coût de développement** : {dev_cost}")

                if isinstance(dev_time, (list, tuple)) and len(dev_time) >= 2:
                    summary_lines.append(
                        f"**Temps de développement** : entre {dev_time[0]} et {dev_time[1]} jours"
                    )
                else:
                    summary_lines.append(
                        f"**Temps de développement** : {dev_time} jours"
                    )

                if isinstance(prod_cost, (list, tuple)) and len(prod_cost) >= 2:
                    summary_lines.append(
                        f"**Coût de production** : entre {prod_cost[0]:,} et {prod_cost[1]:,}"
                    )
                else:
                    summary_lines.append(f"**Coût de production** : {prod_cost}")

                summary_lines.append(f"**Slots occupés** : {slots_taken}")

                # NEW: Add technocentre information if provided
                if self.technocentre_id:
                    summary_lines.append(
                        f"**Technocentre pour développement** : #{self.technocentre_id}"
                    )
            except Exception as e:
                print(f"Error formatting cost data: {e}")
                summary_lines.append("**Coûts** : Données non disponibles")

            print(f"Summary lines: {summary_lines}")

            embed = discord.Embed(
                title="🧪 Résumé de votre nouvelle technologie",
                description="\n".join(summary_lines),
                color=discord.Color.green(),
            )

            if hasattr(self, "image_url") and self.image_url:
                embed.set_image(url=self.image_url)

            print(f"Sending summary to channel {self.ctx.message.channel.id}")

            await self.ctx.send(embed=embed)

            confirmed = await dUtils.ask_confirmation(
                self.ctx, country_id, "Souhaitez-vous créer cette technologie ?"
            )
            print(f"User confirmed: {confirmed}")
            if confirmed:
                # Pass the technocentre_id to handle_new_tech
                await handle_new_tech(
                    self.ctx,
                    self.specialisation,
                    self.form_data,
                    self.image_url,
                    self.technocentre_id,
                )
        except Exception as e:
            print(f"Error in send_summary: {e}")
            # Send a basic error message to the user
            await self.ctx.send(f"❌ Erreur lors de la génération du résumé: {e}")
            import traceback

            traceback.print_exc()

    async def on_timeout(self):
        """Disable all buttons when view times out."""
        for item in self.children:
            item.disabled = True


async def handle_new_tech(
    ctx,
    specialisation: str,
    tech_datas: dict,
    image_url: str,
    technocentre_id: int = None,
):
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
    db = get_db()
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
        "technocentre_id": technocentre_id,  # NEW: Store the technocentre for development
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

    # NEW: Add technocentre information if provided
    if technocentre_id:
        embed.add_field(
            name="🔬 Technocentre", value=f"ID: {technocentre_id}", inline=True
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
        # Get the database and check permissions
        db = get_db()
        usefull_role_ids_dic = {
            "military_admin": 874869709223383091,  # You might need to adjust this
        }

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
        usefull_role_ids_dic = {
            "military_admin": 874869709223383091,  # You might need to adjust this
        }

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
        tech_type = self.tech_data.get("tech_type")

        # Get base costs from database
        db = get_db()
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
        usefull_role_ids_dic = {
            "military_admin": 874869709223383091,  # You might need to adjust this
        }

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
        db = get_db()
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
        usefull_role_ids_dic = {
            "military_admin": 874869709223383091,  # You might need to adjust this
        }

        if not any(
            role.id == usefull_role_ids_dic.get("military_admin")
            for role in interaction.user.roles
        ):
            return await interaction.response.send_message(
                "❌ Vous n'avez pas les permissions nécessaires.", ephemeral=True
            )

        # Add to database
        db = get_db()
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
            # NEW: Start development immediately if technocentre_id is provided
            technocentre_id = self.tech_data.get("technocentre_id")
            tech_id = success  # Assuming add_technology returns the tech_id

            if technocentre_id and tech_id:
                # Start technology development automatically
                country_id = self.tech_data.get("country_id")
                dev_time = self.tech_data.get("final_dev_time")
                dev_cost = self.tech_data.get("final_dev_cost")

                # Check if country has enough money for development
                if db.has_enough_balance(country_id, dev_cost):
                    dev_started = db.start_technology_development(
                        technocentre_id,
                        tech_id,
                        country_id,
                        dev_time,
                        dev_cost
                    )

                    if dev_started:
                        # Debit development cost
                        db.take_balance(country_id, dev_cost)
                        development_msg = f"\n🔬 **Développement automatiquement lancé** dans le technocentre {technocentre_id}!"
                    else:
                        development_msg = f"\n⚠️ Technologie créée mais impossible de lancer le développement dans le technocentre {technocentre_id}."
                else:
                    development_msg = f"\n⚠️ Technologie créée mais fonds insuffisants pour le développement ({convert(str(dev_cost))})."
            else:
                development_msg = ""

            # Update status
            self.tech_data["status"] = "created"
            self.tech_data["created_in_db_at"] = datetime.now().isoformat()

            old_path = f"datas/pending_techs/{self.tech_data['id']}.json"

            print(f"Removing old tech file: {old_path}")  # Debug log
            if os.path.exists(old_path):
                os.remove(old_path)

            # Disable button
            button.disabled = True
            await interaction.response.edit_message(view=self)

            # Notify success
            await interaction.followup.send(
                f"✅ Technologie **{self.tech_data.get('nom')}** créée avec succès dans la base de données!{development_msg}"
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
                        notification_embed = discord.Embed(
                            title="🎉 Technologie créée !",
                            description=f"Votre technologie **{self.tech_data.get('nom')}** a été approuvée et créée!{development_msg}",
                            color=discord.Color.green(),
                        )
                        await country_channel.send(
                            f"<@{self.tech_data['submitted_by']}>",
                            embed=notification_embed,
                        )
        else:
            await interaction.response.send_message(
                "❌ Erreur lors de la création de la technologie dans la base de données.",
                ephemeral=True,
            )


class Technology(commands.Cog):
    """Technology development and management cog"""

    def __init__(self, bot):
        self.bot = bot
        self.db = get_db()
        self.dUtils = get_discord_utils(bot, self.db)

        # Color constants
        self.error_color_int = ERROR_COLOR_INT
        self.money_color_int = MONEY_COLOR_INT
        self.factory_color_int = FACTORY_COLOR_INT

    @commands.hybrid_command(
        name="tech_dev_status",
        brief="Affiche l'état des développements technologiques.",
        usage="tech_dev_status [structure_id]",
        description="Affiche l'état des développements technologiques en cours.",
        help="""Affiche l'état des développements technologiques.

        ARGUMENTS :
        - `[structure_id]` : Optionnel. ID du technocentre spécifique à vérifier.

        FONCTIONNALITÉ :
        - Si aucun ID n'est fourni, affiche tous les développements du pays
        - Si un ID est fourni, affiche les détails du développement pour ce technocentre
        - Montre le temps restant et les coûts

        EXEMPLE :
        - `tech_dev_status` : Affiche tous les développements en cours
        - `tech_dev_status 123` : Affiche le développement du technocentre 123
        """,
        case_insensitive=True,
    )
    @app_commands.autocomplete(structure_id=technocentre_autocomplete)
    async def tech_dev_status(
        self,
        ctx,
        structure_id: int = commands.parameter(
            description="ID du technocentre à vérifier (optionnel).", default=None
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

        if structure_id:
            # Check specific technocentre
            dev = self.db.get_technocentre_development(structure_id)
            if not dev:
                embed = discord.Embed(
                    title="📊 État du technocentre",
                    description=f"Le technocentre {structure_id} n'a aucun développement en cours.",
                    color=self.factory_color_int,
                )
            else:
                if dev["country_id"] != country.get("id"):
                    embed = discord.Embed(
                        title="❌ Accès refusé",
                        description="Ce technocentre ne vous appartient pas.",
                        color=self.error_color_int,
                    )
                else:
                    progress = (
                        (dev["total_development_time"] - dev["months_remaining"])
                        / dev["total_development_time"]
                    ) * 100
                    embed = discord.Embed(
                        title="🔬 Développement en cours",
                        description=f"**{dev['tech_name']}** ({dev['tech_specialisation']})",
                        color=self.factory_color_int,
                    )
                    embed.add_field(
                        name="Progression",
                        value=f"{progress:.1f}% ({dev['months_remaining']} mois restants)",
                        inline=True,
                    )
                    embed.add_field(
                        name="Coût total",
                        value=convert(str(dev["development_cost"])),
                        inline=True,
                    )
        else:
            # Check all developments for the country
            developments = self.db.get_all_technocentre_developments(country.get("id"))

            if not developments:
                embed = discord.Embed(
                    title="📊 Développements technologiques",
                    description="Aucun développement technologique en cours.",
                    color=self.factory_color_int,
                )
            else:
                embed = discord.Embed(
                    title="🔬 Développements en cours",
                    description=f"{len(developments)} développement(s) actif(s)",
                    color=self.factory_color_int,
                )

                for dev in developments[:10]:  # Limit to 10 to avoid embed size issues
                    progress = (
                        (dev["total_development_time"] - dev["months_remaining"])
                        / dev["total_development_time"]
                    ) * 100
                    embed.add_field(
                        name=f"🏢 {dev['region_name']} (#{dev['structure_id']})",
                        value=f"**{dev['tech_name']}**\n{progress:.1f}% - {dev['months_remaining']} jours restants",
                        inline=True,
                    )

        await ctx.send(embed=embed)

    @commands.hybrid_command(
        name="cancel_tech_dev",
        brief="Annule le développement d'une technologie.",
        usage="cancel_tech_dev <structure_id>",
        description="Annule le développement en cours dans un technocentre.",
        help="""Annule un développement technologique en cours.

        ARGUMENTS :
        - `<structure_id>` : ID du technocentre dont annuler le développement.

        FONCTIONNALITÉ :
        - Annule le développement en cours
        - Libère le technocentre pour d'autres développements
        - Ne rembourse pas les coûts déjà engagés

        EXEMPLE :
        - `cancel_tech_dev 123` : Annule le développement du technocentre 123.
        """,
        case_insensitive=True,
    )
    @app_commands.autocomplete(structure_id=technocentre_autocomplete)
    async def cancel_tech_dev(
        self,
        ctx,
        structure_id: int = commands.parameter(
            description="ID du technocentre dont annuler le développement."
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

        # Check if there's development at this technocentre
        dev = self.db.get_technocentre_development(structure_id)
        if not dev:
            embed = discord.Embed(
                title="❌ Aucun développement",
                description="Aucun développement en cours dans ce technocentre.",
                color=self.error_color_int,
            )
            await ctx.send(embed=embed)
            return

        if dev["country_id"] != country.get("id"):
            embed = discord.Embed(
                title="❌ Accès refusé",
                description="Ce technocentre ne vous appartient pas.",
                color=self.error_color_int,
            )
            await ctx.send(embed=embed)
            return

        # Cancel development
        if self.db.cancel_technology_development(dev["development_id"]):
            embed = discord.Embed(
                title="❌ Développement annulé",
                description=f"Le développement de **{dev['tech_name']}** a été annulé.\nLe technocentre {structure_id} est maintenant disponible.",
                color=self.factory_color_int,
            )
        else:
            embed = discord.Embed(
                title="❌ Erreur",
                description="Impossible d'annuler le développement.",
                color=self.error_color_int,
            )

        await ctx.send(embed=embed)

    @commands.hybrid_command(
        name="available_technocentres",
        brief="Liste les technocentres disponibles pour le développement.",
        usage="available_technocentres [specialisation]",
        description="Affiche les technocentres disponibles pour le développement technologique.",
        help="""Liste les technocentres disponibles pour le développement.

        ARGUMENTS :
        - `[specialisation]` : Optionnel. Filtre par spécialisation ('Terrestre', 'Aerienne', 'Navale').

        FONCTIONNALITÉ :
        - Affiche tous les technocentres disponibles (non utilisés)
        - Peut filtrer par spécialisation si spécifiée
        - Montre le niveau et la localisation

        EXEMPLE :
        - `available_technocentres` : Affiche tous les technocentres disponibles
        - `available_technocentres Terrestre` : Affiche les technocentres terrestres disponibles
        """,
        case_insensitive=True,
    )
    @app_commands.choices(
        specialisation=[
            app_commands.Choice(name="Terrestre", value="Terrestre"),
            app_commands.Choice(name="Aerienne", value="Aerienne"),
            app_commands.Choice(name="Navale", value="Navale"),
        ]
    )
    async def available_technocentres(
        self,
        ctx,
        specialisation: str = commands.parameter(
            description="Spécialisation à filtrer (optionnel).", default=None
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

        # Get available technocentres
        technocentres = self.db.get_available_technocentres(
            country.get("id"), specialisation
        )

        if not technocentres:
            spec_text = f" de spécialisation {specialisation}" if specialisation else ""
            embed = discord.Embed(
                title="🏢 Technocentres disponibles",
                description=f"Aucun technocentre{spec_text} disponible pour le développement.",
                color=self.factory_color_int,
            )
        else:
            spec_text = f" ({specialisation})" if specialisation else ""
            embed = discord.Embed(
                title=f"🏢 Technocentres disponibles{spec_text}",
                description=f"{len(technocentres)} technocentre(s) disponible(s)",
                color=self.factory_color_int,
            )

            for tc in technocentres[:15]:  # Limit to avoid embed size issues
                embed.add_field(
                    name=f"#{tc['structure_id']} - Niveau {tc['level']}",
                    value=f"📍 {tc['region_name']}\n🔧 {tc['specialisation']}",
                    inline=True,
                )

        await ctx.send(embed=embed)

    @commands.hybrid_command(
        name="create_tech",
        brief="Crée une nouvelle technologie avec développement automatique.",
        usage="create_tech <specialisation> <technocentre_id> <image_url>",
        description="Lance la création d'une nouvelle technologie avec sélection du technocentre pour le développement.",
        help="""Crée une nouvelle technologie et lance automatiquement son développement.

        ARGUMENTS :
        - `<specialisation>` : Type de technologie (terrestre, aerienne, navale, armes)
        - `<technocentre_id>` : ID du technocentre où développer la technologie
        - `<image_url>` : URL de l'image de la technologie

        FONCTIONNALITÉ :
        - Guide l'utilisateur à travers les formulaires de création
        - Vérifie la disponibilité du technocentre sélectionné
        - Soumet la technologie pour validation par le staff
        - Lance automatiquement le développement après approbation
        - Débite automatiquement les coûts de développement

        PROCESSUS :
        1. Remplissage des formulaires de technologie
        2. Validation par le staff militaire
        3. Évaluation de la difficulté et calcul des coûts
        4. Création dans la base de données
        5. Lancement automatique du développement

        EXEMPLE :
        - `create_tech terrestre 123 https://example.com/image.png`
        """,
        case_insensitive=True,
    )
    @app_commands.choices(
        specialisation=[
            app_commands.Choice(name="🚗 Terrestre", value="terrestre"),
            app_commands.Choice(name="✈️ Aerienne", value="aerienne"),
            app_commands.Choice(name="🚢 Navale", value="navale"),
            app_commands.Choice(name="🔫 Armes", value="armes"),
        ]
    )
    @app_commands.autocomplete(technocentre_id=technocentre_autocomplete)
    async def create_tech(
        self,
        ctx,
        specialisation: str = commands.parameter(
            description="Type de technologie (terrestre, aerienne, navale, armes)"
        ),
        technocentre_id: int = commands.parameter(
            description="ID du technocentre pour le développement"
        ),
        image_url: str = commands.parameter(
            description="URL de l'image de la technologie"
        ),
    ):
        """Crée une nouvelle technologie avec développement automatique."""

        # Get user's country
        country = CountryEntity(ctx.author, ctx.guild).to_dict()
        if not country or not country.get("id"):
            embed = discord.Embed(
                title="❌ Erreur",
                description="L'utilisateur ou le pays spécifié est invalide.",
                color=self.error_color_int,
            )
            await ctx.send(embed=embed)
            return

        # Validate technocentre ownership and availability
        technocentre_dev = self.db.get_technocentre_development(technocentre_id)
        if technocentre_dev:
            embed = discord.Embed(
                title="❌ Technocentre occupé",
                description=f"Le technocentre {technocentre_id} est déjà utilisé pour le développement de **{technocentre_dev['tech_name']}**.",
                color=self.error_color_int,
            )
            await ctx.send(embed=embed)
            return

        # Check if technocentre belongs to the country
        technocentres = self.db.get_available_technocentres(country.get("id"))
        if not any(tc["structure_id"] == technocentre_id for tc in technocentres):
            embed = discord.Embed(
                title="❌ Technocentre invalide",
                description=f"Le technocentre {technocentre_id} ne vous appartient pas ou n'est pas disponible.",
                color=self.error_color_int,
            )
            await ctx.send(embed=embed)
            return

        # Validate technology type
        if specialisation not in TechFormData.TECH_CONFIGS:
            valid_types = ", ".join(
                [k for k in TechFormData.TECH_CONFIGS.keys() if k != "common"]
            )
            embed = discord.Embed(
                title="❌ Type invalide",
                description=f"Type de technologie invalide. Choisissez parmi : {valid_types}",
                color=self.error_color_int,
            )
            await ctx.send(embed=embed)
            return

        # Validate image URL
        try:
            async with aiohttp.ClientSession() as session:
                async with session.head(image_url) as resp:
                    if resp.status != 200:
                        embed = discord.Embed(
                            title="❌ Image invalide",
                            description="L'URL de l'image fournie n'est pas accessible.",
                            color=self.error_color_int,
                        )
                        await ctx.send(embed=embed)
                        return
        except Exception as e:
            embed = discord.Embed(
                title="❌ Erreur d'image",
                description=f"Impossible de vérifier l'image: {e}",
                color=self.error_color_int,
            )
            await ctx.send(embed=embed)
            return

        # Create the technology creation interface
        config = TechFormData.TECH_CONFIGS[specialisation]

        embed = discord.Embed(
            title=f"🔬 Création de technologie - {config['title']}",
            description=f"**Technocentre sélectionné:** #{technocentre_id}\n\nVeuillez remplir les formulaires ci-dessous pour créer votre nouvelle technologie.",
            color=config["color"],
        )
        embed.set_image(url=image_url)
        embed.add_field(
            name="ℹ️ Instructions",
            value="Cliquez sur les boutons pour remplir chaque partie du formulaire. Une fois tous les formulaires complétés, votre technologie sera soumise pour validation.",
            inline=False,
        )

        # Create the multi-form view with technocentre_id
        view = MultiFormView(specialisation, ctx, image_url, technocentre_id)

        await ctx.send(embed=embed, view=view)

    @commands.hybrid_command(
        name="get_infos",
        brief="Affiche les informations d'une technologie par son ID.",
        usage="get_infos <tech_id>",
        description="Récupère et affiche toutes les informations d'une technologie en utilisant son ID.",
        help="""Affiche les informations complètes d'une technologie.

        FONCTIONNALITÉ :
        - Récupère les données de la technologie depuis la base de données
        - Affiche les informations techniques et de développement
        - Montre les attributs spécifiques de la technologie
        - Inclut l'image et les coûts de production

        INFORMATIONS AFFICHÉES :
        - Nom et nom d'origine de la technologie
        - Niveau et spécialisation
        - Coûts de développement et production
        - Temps de développement et slots utilisés
        - Pays développeur
        - Attributs techniques détaillés

        RESTRICTIONS :
        - Nécessite un ID de technologie valide
        - Les technologies secrètes peuvent avoir des restrictions d'accès

        ARGUMENTS :
        - `<tech_id>` : ID numérique de la technologie

        EXEMPLE :
        - `get_infos 42` : Affiche les informations de la technologie avec l'ID 42
        """,
        hidden=False,
        enabled=True,
        case_insensitive=True,
    )
    @app_commands.autocomplete(tech_id=technology_autocomplete)
    async def get_infos(
        self,
        ctx,
        tech_id: int = commands.parameter(description="ID de la technologie"),
    ):
        """Affiche les informations complètes d'une technologie."""
        try:
            # Get technology information
            tech = self.db.get_tech(tech_id)

            if not tech:
                embed = discord.Embed(
                    title="❌ Technologie introuvable",
                    description=f"Aucune technologie trouvée avec l'ID {tech_id}.",
                    color=self.error_color_int,
                )
                await ctx.send(embed=embed)
                return

            # Get country entity for user
            country_entity = CountryEntity(ctx.author, ctx.guild)
            user_country_id = country_entity.get_country_id()

            # Check if technology is secret and user access
            is_secret = tech.get("is_secret", False)
            developed_by = tech.get("developed_by")

            # If secret tech and user is not from the developing country, hide details
            if is_secret and user_country_id != developed_by:
                embed = discord.Embed(
                    title="🔒 Technologie classifiée",
                    description="Cette technologie est classifiée et ses détails ne sont pas accessibles.",
                    color=self.error_color_int,
                )
                await ctx.send(embed=embed)
                return

            # Create information embed
            embed = discord.Embed(
                title=f"🔬 {tech.get('name', 'Technologie inconnue')}",
                description=f"**Nom d'origine:** {tech.get('original_name', 'N/A')}",
                color=self.factory_color_int,
            )

            # Basic information
            embed.add_field(
                name="📊 Informations générales",
                value=f"**Niveau:** {tech.get('technology_level', 'N/A')}\n"
                f"**Spécialisation:** {tech.get('specialisation', 'N/A')}\n"
                f"**Type:** {tech.get('type', 'N/A')}\n"
                f"**Difficulté:** {tech.get('difficulty_rating', 'N/A')}/10",
                inline=True,
            )

            # Development information
            embed.add_field(
                name="🔬 Développement",
                value=f"**Coût:** {tech.get('development_cost', 0):,}\n"
                f"**Temps:** {tech.get('development_time', 0)} jours\n"
                f"**Slots:** {tech.get('slots_taken', 1.0)}",
                inline=True,
            )

            # Production information
            embed.add_field(
                name="🏭 Production",
                value=f"**Coût:** {tech.get('cost', 0):,}\n"
                f"**Exporté:** {'✅' if tech.get('exported', False) else '❌'}\n"
                f"**Secret:** {'🔒' if is_secret else '🌐'}",
                inline=True,
            )

            # Developer information
            if developed_by:
                try:
                    dev_country = self.db.get_country_datas(developed_by)
                    dev_name = (
                        dev_country.get("name", "Pays inconnu")
                        if dev_country
                        else "Pays inconnu"
                    )
                    embed.add_field(
                        name="🏛️ Développeur",
                        value=dev_name,
                        inline=True,
                    )
                except:
                    pass

            # Add image if available
            image_url = tech.get("image_url")
            if image_url:
                embed.set_image(url=image_url)

            # Get and display attributes
            attributes = self.db.get_tech_attributes(tech_id)
            if attributes:
                attr_text = ""
                for attr in attributes[:10]:  # Limit to avoid embed size issues
                    attr_name = attr.get("attribute_name", "N/A")
                    attr_value = attr.get("attribute_value", "N/A")
                    attr_text += f"**{attr_name}:** {attr_value}\n"

                if attr_text:
                    embed.add_field(
                        name="⚙️ Attributs techniques",
                        value=attr_text,
                        inline=False,
                    )

            embed.set_footer(
                text=f"ID: {tech_id} | Créé le: {tech.get('created_at', 'Date inconnue')}"
            )

            await ctx.send(embed=embed)

        except Exception as e:
            print(f"Error in get_infos command: {e}")
            embed = discord.Embed(
                title="❌ Erreur",
                description="Une erreur s'est produite lors de la récupération des informations.",
                color=self.error_color_int,
            )
            await ctx.send(embed=embed)

    @commands.hybrid_command(
        name="start_production",
        brief="Démarre la production d'une technologie dans une usine.",
        usage="start_production <structure_id> <technology_id> <quantity>",
        description="Lance la production d'une technologie licenciée dans une usine.",
        help="""Démarre la production d'une technologie dans une usine.

        FONCTIONNALITÉ :
        - Lance la production d'une technologie licenciée dans une usine
        - Vérifie la capacité de l'usine, les ressources et les licences
        - Démarre automatiquement le processus de production

        ARGUMENTS :
        - `<structure_id>` : ID de l'usine (structure)
        - `<technology_id>` : ID de la technologie à produire
        - `<quantity>` : Quantité à produire

        EXEMPLE :
        - `start_production 5 12 10` : Produit 10 unités de la technologie 12 dans l'usine 5
        """,
        case_insensitive=True,
    )
    @app_commands.autocomplete(structure_id=factory_autocomplete)
    @app_commands.autocomplete(technology_id=technology_autocomplete)
    async def start_production(
        self,
        ctx,
        structure_id: int = commands.parameter(description="ID de l'usine"),
        technology_id: int = commands.parameter(description="ID de la technologie"),
        quantity: int = commands.parameter(description="Quantité à produire"),
    ):
        """Démarre la production d'une technologie dans une usine."""
        await ctx.defer()  # Acknowledge the command to prevent timeout
        try:
            # Get user's country using CountryEntity pattern
            country_entity = CountryEntity(ctx.author, ctx.guild)
            country_id = country_entity.get_country_id()
            if not country_id:
                embed = discord.Embed(
                    title="❌ Erreur",
                    description="Vous n'êtes membre d'aucun pays.",
                    color=self.error_color_int,
                )
                await ctx.send(embed=embed)
                return

            # Attempt to start production
            result = self.db.start_production(
                structure_id, technology_id, quantity, country_id
            )
            success, message = result.get("success", False), result.get("error", "")

            if success:
                embed = discord.Embed(
                    title="✅ Production démarrée",
                    description=message,
                    color=self.factory_color_int,
                )
            else:
                embed = discord.Embed(
                    title="❌ Erreur de production",
                    description=message,
                    color=self.error_color_int,
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
        name="sell_technology",
        brief="Vend des technologies de votre inventaire à un autre pays.",
        usage="sell_technology <buyer_country> <technology_id> <quantity> [price] [per_unit]",
        description="Transfère des technologies de votre inventaire vers un autre pays.",
        help="""Vend des technologies de votre inventaire à un autre pays.

        FONCTIONNALITÉ :
        - Transfère des technologies de votre inventaire vers un autre pays
        - Gère les paiements et les transactions sécurisées
        - Supporte les prix par unité ou totaux

        ARGUMENTS :
        - `<buyer_country>` : Nom ou ID du pays acheteur
        - `<technology_id>` : ID de la technologie à vendre
        - `<quantity>` : Quantité à vendre
        - `<price>` : Prix (optionnel)
        - `<per_unit>` : True pour prix par unité, False pour prix total (défaut: False)

        EXEMPLE :
        - `sell_technology "France" 12 5 1000` : Vend 5 unités de tech 12 pour 1000 au total
        - `sell_technology "France" 12 5 200 True` : Vend 5 unités à 200 par unité
        """,
        case_insensitive=True,
    )
    @app_commands.autocomplete(technology_id=technology_autocomplete)
    @app_commands.autocomplete(buyer_country=country_autocomplete)
    async def sell_technology(
        self,
        ctx,
        buyer_country: str = commands.parameter(description="Pays acheteur"),
        technology_id: int = commands.parameter(description="ID de la technologie"),
        quantity: int = commands.parameter(description="Quantité à vendre"),
        price: int = commands.parameter(description="Prix (optionnel)", default=0),
        per_unit: bool = commands.parameter(
            description="Prix par unité", default=False
        ),
    ):
        """Vend des technologies de votre inventaire à un autre pays."""
        try:
            # Get user's country
            country_entity = CountryEntity(ctx.author, ctx.guild)
            seller_country_id = country_entity.get_country_id()

            if not seller_country_id:
                embed = discord.Embed(
                    title="❌ Erreur",
                    description="Vous n'êtes membre d'aucun pays.",
                    color=self.error_color_int,
                )
                await ctx.send(embed=embed)
                return

            # Get buyer country
            buyer_entity = CountryEntity(buyer_country, ctx.guild)
            buyer_country_id = buyer_entity.get_country_id()

            if not buyer_country_id:
                embed = discord.Embed(
                    title="❌ Pays introuvable",
                    description=f"Le pays '{buyer_country}' n'a pas été trouvé.",
                    color=self.error_color_int,
                )
                await ctx.send(embed=embed)
                return

            # Attempt to sell technology
            success, message = self.db.sell_technology_inventory(
                seller_country_id,
                buyer_country_id,
                technology_id,
                quantity,
                price,
                per_unit,
            )

            if success:
                embed = discord.Embed(
                    title="✅ Vente réussie",
                    description=message,
                    color=self.factory_color_int,
                )
            else:
                embed = discord.Embed(
                    title="❌ Erreur de vente",
                    description=message,
                    color=self.error_color_int,
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
        name="view_productions",
        brief="Affiche les productions en cours pour votre pays.",
        usage="view_productions",
        description="Liste toutes les productions actuellement en cours.",
        help="""Affiche les productions en cours pour votre pays.

        FONCTIONNALITÉ :
        - Liste toutes les productions actuellement en cours
        - Affiche les détails : usine, technologie, quantité, date de fin
        - Montre le temps restant pour chaque production

        EXEMPLE :
        - `view_productions` : Affiche toutes vos productions en cours
        """,
        case_insensitive=True,
    )
    async def view_productions(self, ctx):
        """Affiche les productions en cours pour votre pays."""
        try:
            # Get user's country
            country_entity = CountryEntity(ctx.author, ctx.guild)
            country_id = country_entity.get_country_id()

            if not country_id:
                embed = discord.Embed(
                    title="❌ Erreur",
                    description="Vous n'êtes membre d'aucun pays.",
                    color=self.error_color_int,
                )
                await ctx.send(embed=embed)
                return

            # Get all productions for the country
            productions = self.db.get_country_productions(country_id)

            if not productions:
                embed = discord.Embed(
                    title="📊 Productions en cours",
                    description="Aucune production en cours pour votre pays.",
                    color=self.factory_color_int,
                )
                await ctx.send(embed=embed)
                return

            embed = discord.Embed(
                title="🏭 Productions en cours",
                description=f"{len(productions)} production(s) active(s)",
                color=self.factory_color_int,
            )

            for prod in productions[:10]:  # Limit to 10 to avoid embed size issues
                tech_name = prod.get("tech_name", "Technologie inconnue")
                quantity = prod.get("quantity", 0)
                months_remaining = prod.get("months_remaining", 0)
                structure_id = prod.get("structure_id", "N/A")

                embed.add_field(
                    name=f"🏢 Usine #{structure_id}",
                    value=f"**{tech_name}**\nQuantité: {quantity}\nTemps restant: {months_remaining} mois",
                    inline=True,
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
    await bot.add_cog(Technology(bot))
