from notion_client import Client
import discord
import json


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
            print("✅ NotionHandler initialized successfully")
        except Exception as e:
            print(f"❌ Failed to initialize NotionHandler: {e}")
            # Set fallback values to prevent crashes
            self.notion_client = None
            self.discord_client = discord_client
            self.notion_db_ids = []
            self.discord_channel_id = None
            self.cache_file = "notion_cache.json"

    async def send_update_embed(self, action, task_info):
        discord_channel = self.discord_client.get_channel(self.discord_channel_id)
        colors = {
            "update": 0xFFA500,
            "new": 0x57F287,
            "delete": 0xED4245,
        }

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

        embed = discord.Embed(title=title, color=color)
        embed.add_field(name="Titre", value=task_title, inline=False)
        embed.add_field(name="Statut", value=status, inline=True)
        embed.add_field(name="Tags", value=tags, inline=True)

        await discord_channel.send(embed=embed)

    async def get_tasks(self, ctx, req_type="all"):
        all_tasks = []
        for notion_db in self.notion_db_ids:
            all_tasks += self.notion_client.databases.query(database_id=notion_db)[
                "results"
            ]

        tasks = {
            "Non commencées": [],
            "En cours": [],
            "Terminées": [],
        }

        for page in all_tasks:
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

            tasks[status].append({"title": title, "tags": tags})

        embed = discord.Embed(
            title="📋 Tâches Notion",
            description=(
                f"**Filtrées par tag** : `{req_type}`"
                if req_type != "all"
                else "Toutes les tâches"
            ),
            color=0x5865F2,
        )

        status_emojis = {"Non commencées": "🕒", "En cours": "🔧", "Terminées": "✅"}

        for status, task_list in tasks.items():
            if not task_list:
                embed.add_field(
                    name=f"{status_emojis.get(status, '')} {status}",
                    value="*Aucune tâche*",
                    inline=False,
                )
                continue

            lines = []
            for task in task_list:
                tags = (
                    ", ".join([f"`{t}`" for t in task["tags"]])
                    if task["tags"]
                    else "`aucun tag`"
                )
                lines.append(f"• **{task['title']}** — {tags}")

            embed.add_field(
                name=f"{status_emojis.get(status, '')} {status}",
                value="\n".join(lines),
                inline=False,
            )

        return embed

    def load_cache(self):
        try:
            with open(self.cache_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            return {}

    def save_cache(self, data):
        with open(self.cache_file, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def extract_task_info(self, page):
        page_id = page["id"]
        props = page["properties"]
        title_prop = props.get("Name", {}).get("title", [])
        status_prop = props.get("Status", {}).get("status", {})
        tags_prop = props.get("Tags", {}).get("multi_select", [])

        title = title_prop[0]["plain_text"] if title_prop else "Sans titre"
        status = status_prop.get("name", "Inconnu")
        tags = [tag["name"] for tag in tags_prop]

        return {
            "id": page_id,
            "title": title,
            "status": status,
            "tags": tags,
        }

    def tasks_differ(self, old_task, new_task):
        # Compare titre, status, tags
        return (
            old_task.get("title") != new_task.get("title")
            or old_task.get("status") != new_task.get("status")
            or set(old_task.get("tags", [])) != set(new_task.get("tags", []))
        )

    async def send_update(self, channel, message):
        discord_channel = self.discord_client.get_channel(self.discord_channel_id)
        await discord_channel.send(message)

    async def check_for_updates(self):
        cache = self.load_cache()
        all_tasks = []
        for notion_db in self.notion_db_ids:
            all_tasks += self.notion_client.databases.query(database_id=notion_db)[
                "results"
            ]

        current_ids = set()
        for page in all_tasks:
            task_info = self.extract_task_info(page)
            task_id = task_info["id"]
            current_ids.add(task_id)

            if task_id in cache:
                if self.tasks_differ(cache[task_id], task_info):
                    await self.send_update_embed("update", task_info)
                    cache[task_id] = task_info
            else:
                await self.send_update_embed("new", task_info)
                cache[task_id] = task_info

        # Détection des suppressions (facultatif)
        deleted_ids = set(cache.keys()) - current_ids
        for task_id in deleted_ids:
            deleted_task = cache[task_id]
            await self.send_update_embed("delete", deleted_task)
            del cache[task_id]

        self.save_cache(cache)
