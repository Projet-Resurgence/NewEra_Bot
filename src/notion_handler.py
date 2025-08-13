from notion_client import Client
import discord
import json
import asyncio
from concurrent.futures import ThreadPoolExecutor


class NotionHandler:

    def __init__(self, notion_secret, discord_client):
        try:
            self.notion_client = Client(auth=notion_secret)
            self.discord_client = discord_client
            self.notion_db_ids = [
                "2367e0731d2d80d78352d02edcb5499d",
                "2367e0731d2d802c84b0f1c0d1b24a67",
            ]
            self.discord_channel_id = 1291471564973281280
            self.cache_file = "notion_cache.json"
            # Thread pool for blocking Notion API calls
            self.executor = ThreadPoolExecutor(max_workers=3)
            # Rate limiting for updates
            self.last_update_time = {}
            self.update_cooldown = (
                300  # 5 minutes cooldown between updates for the same task
            )
            print("✅ NotionHandler initialized successfully")
        except Exception as e:
            print(f"❌ Failed to initialize NotionHandler: {e}")
            # Set fallback values to prevent crashes
            self.notion_client = None
            self.discord_client = discord_client
            self.notion_db_ids = []
            self.discord_channel_id = None
            self.cache_file = "notion_cache.json"
            self.executor = None
            self.last_update_time = {}
            self.update_cooldown = 300

    def extract_text_from_blocks(self, blocks):
        texts = []
        for block in blocks:
            if block["type"] == "paragraph":
                paragraph = block["paragraph"]
                text_items = paragraph.get("rich_text", [])
                for item in text_items:
                    texts.append(item.get("plain_text", ""))
            elif block["type"] == "heading_1":
                text_items = block["heading_1"].get("rich_text", [])
                texts.append(
                    "🟦 " + "".join(item.get("plain_text", "") for item in text_items)
                )
            elif block["type"] == "heading_2":
                text_items = block["heading_2"].get("rich_text", [])
                texts.append(
                    "🟩 " + "".join(item.get("plain_text", "") for item in text_items)
                )
            elif block["type"] == "bulleted_list_item":
                text_items = block["bulleted_list_item"].get("rich_text", [])
                texts.append(
                    "• " + "".join(item.get("plain_text", "") for item in text_items)
                )
            elif block["type"] == "numbered_list_item":
                text_items = block["numbered_list_item"].get("rich_text", [])
                texts.append(
                    "1. " + "".join(item.get("plain_text", "") for item in text_items)
                )
            elif block["type"] == "to_do":
                text_items = block["to_do"].get("rich_text", [])
                checked = "☑️" if block["to_do"].get("checked", False) else "☐"
                texts.append(
                    f"{checked} "
                    + "".join(item.get("plain_text", "") for item in text_items)
                )
        return "\n".join(texts).strip()

    def _get_notion_blocks_sync(self, page_id):
        """Synchronous method to get blocks - runs in thread pool."""
        try:
            return self.notion_client.blocks.children.list(block_id=page_id)["results"]
        except Exception as e:
            print(
                f"❌ Erreur lors de la récupération du contenu de la page {page_id}: {e}",
                flush=True,
            )
            return []

    def _query_database_sync(self, database_id):
        """Synchronous method to query database - runs in thread pool."""
        try:
            return self.notion_client.databases.query(database_id=database_id)[
                "results"
            ]
        except Exception as e:
            print(
                f"❌ Erreur lors de la récupération de la base de données {database_id}: {e}",
                flush=True,
            )
            return []

    async def send_update_embed(self, action, task_info):
        # Rate limiting check
        import time

        task_id = task_info.get("id", "unknown")
        current_time = time.time()

        if action == "update":
            last_update = self.last_update_time.get(task_id, 0)
            if current_time - last_update < self.update_cooldown:
                print(
                    f"⏰ Skipping update for task {task_info.get('title', 'Unknown')} - cooldown active"
                )
                return
            self.last_update_time[task_id] = current_time

        discord_channel = self.discord_client.get_channel(self.discord_channel_id)
        if not discord_channel:
            print(f"❌ Discord channel {self.discord_channel_id} not found")
            return

        colors = {
            "update": 0xFFA500,
            "new": 0x57F287,
            "delete": 0xED4245,
        }

        print(
            f"Sending {action} embed for task: {task_info.get('title', 'Sans titre')} description: {task_info.get('description', 'Pas de description')}",
            flush=True,
        )

        titles = {
            "update": "🔄 Mise à jour de tâche",
            "new": "🆕 Nouvelle tâche ajoutée",
            "delete": "❌ Tâche supprimée",
        }

        color = colors.get(action, 0x2F3136)
        title = titles.get(action, "📋 Tâche")

        tags = (
            ", ".join(task_info.get("tags", [])) if task_info.get("tags") else "Aucun"
        )
        status = task_info.get("status", "Inconnu")
        task_title = task_info.get("title", "Sans titre")
        description = task_info.get("description", "Pas de description")

        embed = discord.Embed(title=title, color=color)
        embed.add_field(name="Titre", value=task_title, inline=False)
        embed.add_field(name="Statut", value=status, inline=True)
        embed.add_field(name="Tags", value=tags, inline=True)
        embed.add_field(name="Description", value=description, inline=False)

        try:
            await discord_channel.send(embed=embed)
        except Exception as e:
            print(f"❌ Failed to send Discord embed: {e}")

    async def get_tasks(self, ctx, req_type="all"):
        # Use executor to avoid blocking the event loop
        all_tasks = []
        if self.executor and self.notion_client:
            # Run database queries in thread pool to avoid blocking
            tasks_futures = []
            for notion_db in self.notion_db_ids:
                future = asyncio.get_event_loop().run_in_executor(
                    self.executor, self._query_database_sync, notion_db
                )
                tasks_futures.append(future)

            # Wait for all database queries to complete
            db_results = await asyncio.gather(*tasks_futures)
            for results in db_results:
                all_tasks.extend(results)
        else:
            # Fallback to synchronous calls if executor is not available
            for notion_db in self.notion_db_ids:
                all_tasks += self.notion_client.databases.query(database_id=notion_db)[
                    "results"
                ]

        tasks = {
            "Non commencées": [],
            "En cours": [],
            "Terminées": [],
        }

        # Process all pages and get their content asynchronously
        page_futures = []
        page_info = []

        for page in all_tasks:
            page_id = page["id"]
            title_prop = page["properties"].get("Name", {}).get("title", [])
            status_prop = page["properties"].get("Status", {}).get("status", {})
            tags_prop = page["properties"].get("Tags", {}).get("multi_select", [])

            title = title_prop[0]["plain_text"] if title_prop else "Sans titre"
            status = status_prop.get("name", "Inconnu")
            tags = [tag["name"] for tag in tags_prop]

            if status not in tasks:
                continue
            if req_type != "all" and req_type not in [tag.lower() for tag in tags]:
                continue

            page_info.append(
                {"id": page_id, "title": title, "status": status, "tags": tags}
            )

            # Schedule async block retrieval
            if self.executor and self.notion_client:
                future = asyncio.get_event_loop().run_in_executor(
                    self.executor, self._get_notion_blocks_sync, page_id
                )
                page_futures.append(future)

        # Get all block contents asynchronously
        if page_futures:
            blocks_results = await asyncio.gather(*page_futures)
            for i, blocks in enumerate(blocks_results):
                description = self.extract_text_from_blocks(blocks)
                # Limit description length - account for Discord field limits and formatting
                max_length = 800
                description = (
                    description[:max_length] if description else "Pas de description"
                )

                page_data = page_info[i]
                tasks[page_data["status"]].append(
                    {
                        "title": page_data["title"],
                        "tags": page_data["tags"],
                        "description": description,
                    }
                )
        else:
            # Fallback for pages without descriptions
            for page_data in page_info:
                tasks[page_data["status"]].append(
                    {
                        "title": page_data["title"],
                        "tags": page_data["tags"],
                        "description": "Pas de description",
                    }
                )

        # Create separate embeds for each status
        embeds = []
        status_emojis = {"Non commencées": "🕒", "En cours": "🔧", "Terminées": "✅"}
        status_colors = {
            "Non commencées": 0xFFA500,
            "En cours": 0x5865F2,
            "Terminées": 0x57F287,
        }

        for status, task_list in tasks.items():
            if not task_list:
                continue  # Skip empty categories

            embed = discord.Embed(
                title=f"{status_emojis.get(status, '')} {status}",
                description=(
                    f"**Filtrées par tag** : `{req_type}`"
                    if req_type != "all"
                    else "Toutes les tâches"
                ),
                color=status_colors.get(status, 0x5865F2),
            )

            for task in task_list:
                tags = (
                    ", ".join([f"`{t}`" for t in task["tags"]])
                    if task["tags"]
                    else "`aucun tag`"
                )
                description = task["description"] or "Pas de description"

                # Construct field value and ensure it fits Discord's 1024 character limit
                field_value = f"**Tags:** {tags}\n**Description:**\n{description}"
                if len(field_value) > 1024:
                    # Calculate available space for description after tags
                    tags_part = f"**Tags:** {tags}\n**Description:**\n"
                    available_space = 1024 - len(tags_part) - 3  # -3 for "..."
                    truncated_description = description[:available_space] + "..."
                    field_value = (
                        f"**Tags:** {tags}\n**Description:**\n{truncated_description}"
                    )

                # Each task gets its own field with more space
                embed.add_field(
                    name=f"**{task['title']}**",
                    value=field_value,
                    inline=False,
                )
            embeds.append(embed)

        return embeds

    def load_cache(self):
        try:
            with open(self.cache_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                # Migrate old cache format to new format if needed
                if data and not any(db_id in data for db_id in self.notion_db_ids):
                    # Old format detected, migrate to new format
                    print("🔄 Migrating cache to new format...")
                    migrated_data = {}
                    for db_id in self.notion_db_ids:
                        migrated_data[db_id] = {}
                    # Save migrated structure
                    self.save_cache(migrated_data)
                    return migrated_data
                return data
        except Exception as e:
            print(f"⚠️ Error loading cache, creating new one: {e}")
            # Initialize cache structure for each database
            new_cache = {}
            for db_id in self.notion_db_ids:
                new_cache[db_id] = {}
            return new_cache

    def save_cache(self, data):
        with open(self.cache_file, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    async def extract_task_info(self, page):
        page_id = page["id"]
        props = page["properties"]
        title_prop = props.get("Name", {}).get("title", [])
        status_prop = props.get("Status", {}).get("status", {})
        tags_prop = props.get("Tags", {}).get("multi_select", [])

        title = title_prop[0]["plain_text"] if title_prop else "Sans titre"
        status = status_prop.get("name", "Inconnu")
        tags = [tag["name"] for tag in tags_prop]

        # Récupérer le contenu des blocs Notion de la page asynchronously
        if self.executor and self.notion_client:
            try:
                blocks = await asyncio.get_event_loop().run_in_executor(
                    self.executor, self._get_notion_blocks_sync, page_id
                )
                description = self.extract_text_from_blocks(blocks)
            except Exception as e:
                print(
                    f"❌ Erreur lors de la récupération du contenu de la page {page_id}: {e}",
                    flush=True,
                )
                description = "Pas de description"
        else:
            # Fallback to synchronous call
            try:
                blocks = self.notion_client.blocks.children.list(block_id=page_id)[
                    "results"
                ]
                description = self.extract_text_from_blocks(blocks)
            except Exception as e:
                print(
                    f"❌ Erreur lors de la récupération du contenu de la page {page_id}: {e}",
                    flush=True,
                )
                description = "Pas de description"

        return {
            "id": page_id,
            "title": title,
            "status": status,
            "tags": tags,
            "description": description,
        }

    def tasks_differ(self, old_task, new_task):
        # Compare title, status, tags, and description
        title_changed = (
            old_task.get("title", "").strip() != new_task.get("title", "").strip()
        )
        status_changed = old_task.get("status", "") != new_task.get("status", "")
        tags_changed = set(old_task.get("tags", [])) != set(new_task.get("tags", []))

        # For description, normalize whitespace to avoid false positives
        old_desc = " ".join(old_task.get("description", "").split())
        new_desc = " ".join(new_task.get("description", "").split())
        description_changed = old_desc != new_desc

        if title_changed or status_changed or tags_changed or description_changed:
            print(f"🔍 Task differences detected:")
            if title_changed:
                print(
                    f"  📝 Title: '{old_task.get('title')}' → '{new_task.get('title')}'"
                )
            if status_changed:
                print(
                    f"  📊 Status: '{old_task.get('status')}' → '{new_task.get('status')}'"
                )
            if tags_changed:
                print(f"  🏷️ Tags: {old_task.get('tags')} → {new_task.get('tags')}")
            if description_changed:
                print(f"  📄 Description changed")
            return True

        return False

    async def send_update(self, channel, message):
        discord_channel = self.discord_client.get_channel(self.discord_channel_id)
        await discord_channel.send(message)

    async def initialize_cache_silently(self):
        """Initialize cache without sending notifications - useful for first run."""
        print("🔄 Initializing cache silently...")
        cache = self.load_cache()

        # Ensure cache structure exists for each database
        for db_id in self.notion_db_ids:
            if db_id not in cache:
                cache[db_id] = {}

        # Process each database separately
        for db_id in self.notion_db_ids:
            print(f"📚 Loading tasks from database {db_id}...")

            # Get tasks from this specific database
            if self.executor and self.notion_client:
                try:
                    tasks = await asyncio.get_event_loop().run_in_executor(
                        self.executor, self._query_database_sync, db_id
                    )
                except Exception as e:
                    print(f"❌ Error querying database {db_id}: {e}")
                    continue
            else:
                try:
                    tasks = self.notion_client.databases.query(database_id=db_id)[
                        "results"
                    ]
                except Exception as e:
                    print(f"❌ Error querying database {db_id}: {e}")
                    continue

            db_cache = cache[db_id]

            # Add all tasks to cache without notifications
            for page in tasks:
                try:
                    task_info = await self.extract_task_info(page)
                    task_id = task_info["id"]
                    db_cache[task_id] = task_info
                    print(f"  ✅ Cached task: {task_info['title']}")
                except Exception as e:
                    print(f"❌ Error processing task in DB {db_id}: {e}")
                    continue

            print(f"✅ Loaded {len(db_cache)} tasks from database {db_id}")

        # Save the initialized cache
        self.save_cache(cache)
        print("💾 Cache initialization complete")

    async def check_for_updates(self):
        cache = self.load_cache()
        to_save = False

        # Ensure cache structure exists for each database
        for db_id in self.notion_db_ids:
            if db_id not in cache:
                cache[db_id] = {}

        # Process each database separately to avoid cross-contamination
        for db_id in self.notion_db_ids:
            print(f"🔍 Checking database {db_id} for updates...")

            # Get tasks from this specific database
            if self.executor and self.notion_client:
                try:
                    tasks = await asyncio.get_event_loop().run_in_executor(
                        self.executor, self._query_database_sync, db_id
                    )
                except Exception as e:
                    print(f"❌ Error querying database {db_id}: {e}")
                    continue
            else:
                try:
                    tasks = self.notion_client.databases.query(database_id=db_id)[
                        "results"
                    ]
                except Exception as e:
                    print(f"❌ Error querying database {db_id}: {e}")
                    continue

            db_cache = cache[db_id]
            current_ids = set()

            # Process each task in this database
            for page in tasks:
                try:
                    task_info = await self.extract_task_info(page)
                    task_id = task_info["id"]
                    current_ids.add(task_id)

                    if task_id in db_cache:
                        # Check if task has been updated
                        if self.tasks_differ(db_cache[task_id], task_info):
                            print(
                                f"📝 Task updated in DB {db_id}: {task_info['title']}"
                            )
                            await self.send_update_embed("update", task_info)
                            to_save = True
                            db_cache[task_id] = task_info
                        # else: no changes, do nothing
                    else:
                        # New task found
                        print(f"🆕 New task in DB {db_id}: {task_info['title']}")
                        await self.send_update_embed("new", task_info)
                        to_save = True
                        db_cache[task_id] = task_info

                except Exception as e:
                    print(f"❌ Error processing task in DB {db_id}: {e}")
                    continue

            # Check for deleted tasks in this database
            deleted_ids = set(db_cache.keys()) - current_ids
            for task_id in deleted_ids:
                deleted_task = db_cache[task_id]
                print(
                    f"🗑️ Task deleted from DB {db_id}: {deleted_task.get('title', 'Unknown')}"
                )
                await self.send_update_embed("delete", deleted_task)
                to_save = True
                del db_cache[task_id]

            print(f"✅ Finished checking database {db_id}")

        if not to_save:
            print("🔒 No changes detected, skipping cache save.", flush=True)
            return
        # Save the updated cache
        self.save_cache(cache)
        print("💾 Cache saved successfully", flush=True)
