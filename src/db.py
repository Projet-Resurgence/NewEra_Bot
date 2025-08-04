import sqlite3
import math
import os
from datetime import datetime, timezone

debug = False
bat_types = {}
bat_buffs = {}


class UsefulDatas:
    """Class to hold useful data for the bot."""

    def __init__(self, _bat_types, _bat_buffs):
        global bat_types, bat_buffs, debug
        bat_types = _bat_types
        bat_buffs = _bat_buffs


class Database:
    """Database class to handle database operations."""

    def __init__(self, path="datas/rts.db", useful_datas: UsefulDatas = None):
        self.conn, self.cur = self.initialize_database()

    def __del__(self):
        if hasattr(self, "conn"):
            self.conn.close()

    def initialize_database(self):
        """Initialize the database self.connection and create tables if they don't exist."""
        conn = sqlite3.connect("datas/rts.db", check_same_thread=False)
        conn.row_factory = sqlite3.Row  # Enable row factory for dict-like access
        cur = conn.cursor()
        dbs_content = {}
        for filename in sorted(os.listdir("datas/db_schemas")):
            if filename.endswith(".sql"):
                with open(f"datas/db_schemas/{filename}", "r", encoding="utf-8") as f:
                    content = f.read()
                    dbs_content[filename] = content
                    cur.executescript(content)
        conn.commit()
        with open("datas/init_data.sql", "r", encoding="utf-8") as f:
            init_data = f.read()
            cur.executescript(init_data)
        global debug
        cur.execute("SELECT value FROM ServerSettings WHERE key = 'debug'")
        res = cur.fetchone()
        if res is None:
            cur.execute("INSERT INTO ServerSettings (key, value) VALUES ('debug', 0)")
            conn.commit()
            debug = False
            print("Debug mode not set, defaulting to False.", flush=True)
        else:
            debug = True if res[0] else False
        print("Database initialized with debug mode:", debug, flush=True)
        if debug:
            with open("dbs_log.txt", "w", encoding="utf-8") as f:
                for name, sql in dbs_content.items():
                    f.write(f"\n=== {name} ===\n")
                    f.write(sql)
                    f.write("\n\n")
            for name, sql in dbs_content.items():
                print(f"{name}:\n{sql}\n")
        print("Database initialized.", flush=True)
        return conn, cur

    def get_balance(self, country_id):
        """Get the balance of a country from the database."""
        self.cur.execute(
            "SELECT balance FROM Inventory WHERE country_id = ?", (country_id,)
        )
        result = self.cur.fetchone()
        if result is not None:
            return str(result[0])
        return 0

    def get_points(self, country_id, type: int = 1):
        """Get the points of a player from the database."""
        column = "pol_points" if type == 1 else "diplo_points"
        self.cur.execute(
            f"SELECT {column} FROM Inventory WHERE country_id = ?", (country_id,)
        )
        result = self.cur.fetchone()
        if result is not None:
            return result[0]
        else:
            return 0

    def has_enough_balance(self, country_id, amount):
        """Check if a player has enough balance."""
        result = self.get_balance(country_id)
        if result is None:
            return False
        if amount <= 0:
            return False
        return int(result) >= int(amount)

    def has_enough_points(self, country_id, amount, type: int = 1):
        """Check if a player has enough points."""
        result = self.get_points(country_id, type)
        if result is None:
            return False
        if amount <= 0:
            return False
        return result >= amount

    def set_balance(self, country_id, amount):
        """Set the balance of a country."""
        result = self.get_balance(country_id)
        if result is not None:
            self.cur.execute(
                "UPDATE Inventory SET balance = ? WHERE country_id = ?",
                (amount, country_id),
            )
        else:
            self.cur.execute(
                "INSERT INTO Inventory (country_id, balance) VALUES (?, ?)",
                (country_id, amount),
            )
        self.conn.commit()

    def set_points(self, country_id, amount, type: int = 1):
        """Set the points of a player."""
        result = self.get_points(country_id, type)
        column = "pol_points" if type == 1 else "diplo_points"
        if result is not None:
            self.cur.execute(
                f"UPDATE Inventory SET {column} = ? WHERE country_id = ?",
                (amount, country_id),
            )
        else:
            self.cur.execute(
                f"INSERT INTO Inventory (country_id, {column}) VALUES (?, ?)",
                (country_id, amount),
            )
        self.conn.commit()

    def give_balance(self, country_id, amount):
        """Give money to a country."""
        try:
            self.cur.execute(
                "INSERT INTO Inventory (country_id, balance) VALUES (?, ?) "
                "ON CONFLICT(country_id) DO UPDATE SET balance = balance + ?",
                (country_id, amount, amount),
            )
            self.conn.commit()
        except sqlite3.IntegrityError:
            raise (f"ERREUR : Le pays {country_id} n'existe pas dans Countries.")

    def take_balance(self, country_id, amount):
        """Take money from a country."""
        result = self.get_balance(country_id)
        if result is not None:
            self.cur.execute(
                "UPDATE Inventory SET balance = balance - ? WHERE country_id = ?",
                (amount, country_id),
            )
        else:
            self.cur.execute(
                "INSERT INTO Inventory (country_id, balance) VALUES (?, ?)",
                (country_id, -amount),
            )
        self.conn.commit()

    def give_points(self, country_id: str, amount: int, type: int = 1):
        """Ajoute des points politiques (type=1) ou diplomatiques (type=2) à un pays."""
        column = "pol_points" if type == 1 else "diplo_points"

        result = self.get_points(country_id, type)

        if result is not None:
            self.cur.execute(
                f"UPDATE Inventory SET {column} = {column} + ? WHERE country_id = ?",
                (amount, country_id),
            )
        else:
            self.cur.execute(
                f"INSERT INTO Inventory (country_id, {column}) VALUES (?, ?)",
                (country_id, amount),
            )
        self.conn.commit()

    def take_points(self, country_id, amount, type: int = 1):
        """Take points from a country."""
        result = self.get_points(country_id, type)
        column = "pol_points" if type == 1 else "diplo_points"

        if result:
            self.cur.execute(
                f"UPDATE Inventory SET {column} = {column} - ? WHERE country_id = ?",
                (amount, country_id),
            )
        else:
            self.cur.execute(
                f"INSERT INTO Inventory (country_id, {column}) VALUES (?, ?)",
                (country_id, -amount),
            )
        self.conn.commit()

    # Structure-related database functions
    def get_structures_by_country(
        self, country_id: int = None, structure_type: str = None
    ) -> list:
        """Get all structures owned by a country, or all structures if country_id is None."""
        if country_id is None:
            # Get all structures (for admin commands)
            if structure_type:
                self.cur.execute(
                    """
                    SELECT s.id, s.type, s.specialisation, s.level, s.capacity, s.population,
                           s.region_id, r.name as region_name
                    FROM Structures s
                    LEFT JOIN Regions r ON s.region_id = r.region_id
                    WHERE s.type = ?
                    ORDER BY s.type, s.level DESC
                """,
                    (structure_type,),
                )
            else:
                self.cur.execute(
                    """
                    SELECT s.id, s.type, s.specialisation, s.level, s.capacity, s.population,
                           s.region_id, r.name as region_name
                    FROM Structures s
                    LEFT JOIN Regions r ON s.region_id = r.region_id
                    ORDER BY s.type, s.level DESC
                """
                )
        else:
            # Get structures for specific country
            if structure_type:
                self.cur.execute(
                    """
                    SELECT s.id, s.type, s.specialisation, s.level, s.capacity, s.population,
                           r.region_id, r.name as region_name
                    FROM Structures s
                    JOIN Regions r ON s.region_id = r.region_id
                    WHERE r.country_id = ? AND s.type = ?
                    ORDER BY s.type, s.level DESC
                """,
                    (country_id, structure_type),
                )
            else:
                self.cur.execute(
                    """
                    SELECT s.id, s.type, s.specialisation, s.level, s.capacity, s.population,
                           r.region_id, r.name as region_name
                    FROM Structures s
                    JOIN Regions r ON s.region_id = r.region_id
                    WHERE r.country_id = ?
                    ORDER BY s.type, s.level DESC
                """,
                    (country_id,),
                )
        return self.cur.fetchall()

    def get_structure_capacity(self, structure_id: int) -> int:
        """Get the effective capacity of a structure."""
        self.cur.execute(
            """
            SELECT sd.capacity * sr.ratio_production / 100.0 as effective_capacity
            FROM Structures s
            JOIN StructuresDatas sd ON s.type = sd.type AND s.specialisation = sd.specialisation
            JOIN StructuresRatios sr ON s.type = sr.type AND s.level = sr.level
            WHERE s.id = ?
        """,
            (structure_id,),
        )
        result = self.cur.fetchone()
        return int(result[0]) if result else 0

    def get_structure_used_capacity(self, structure_id: int) -> float:
        """Get the currently used capacity of a structure."""
        self.cur.execute(
            """
            SELECT SUM(t.slots_taken * (1 + t.technology_level / 10.0) * sp.quantity) as used_capacity
            FROM StructureProduction sp
            JOIN Technologies t ON sp.tech_id = t.tech_id
            WHERE sp.structure_id = ?
        """,
            (structure_id,),
        )
        result = self.cur.fetchone()
        return float(result[0]) if result and result[0] else 0.0

    def construct_structure(
        self,
        country_id: int,
        structure_type: str,
        specialisation: str,
        level: int,
        region_id: int,
        amount: int = 1,
    ) -> bool:
        """Construct structures in a region."""
        try:
            self.cur.execute(
                """
                SELECT region_id FROM Regions WHERE region_id = ? AND country_id = ?
            """,
                (region_id, country_id),
            )
            if not self.cur.fetchone():
                return False

            # Get base capacity from StructuresDatas and apply level ratio
            self.cur.execute(
                """
                SELECT sd.capacity * sr.ratio_production / 100.0
                FROM StructuresDatas sd
                JOIN StructuresRatios sr ON sd.type = sr.type
                WHERE sd.type = ? AND sd.specialisation = ? AND sr.level = ?
            """,
                (structure_type, specialisation, level),
            )
            capacity_result = self.cur.fetchone()
            capacity = int(capacity_result[0]) if capacity_result else 0

            # Insert structures
            for _ in range(amount):
                self.cur.execute(
                    """
                    INSERT INTO Structures (region_id, type, specialisation, level, capacity, population)
                    VALUES (?, ?, ?, ?, ?, 0)
                """,
                    (region_id, structure_type, specialisation, level, capacity),
                )

            self.conn.commit()
            return True
        except Exception as e:
            print(f"Error constructing structure: {e}")
            return False

    def get_construction_cost(self, structure_type: str, level: int) -> int:
        """Get construction cost for a structure type and level."""
        self.cur.execute(
            """
            SELECT sd.cout_construction * sr.ratio_cost / 100.0
            FROM StructuresDatas sd
            JOIN StructuresRatios sr ON sd.type = sr.type
            WHERE sd.type = ? AND sr.level = ?
        """,
            (structure_type, level),
        )
        result = self.cur.fetchone()
        return int(result[0]) if result else 0

    def remove_structure(self, structure_id: int) -> bool:
        """Remove a structure by ID."""
        try:
            self.cur.execute("DELETE FROM Structures WHERE id = ?", (structure_id,))
            self.conn.commit()
            return self.cur.rowcount > 0
        except Exception as e:
            print(f"Error removing structure: {e}")
            return False

    def get_available_structure_types(self) -> list:
        """Get all available structure types."""
        self.cur.execute("SELECT DISTINCT type FROM StructuresDatas")
        return [row[0] for row in self.cur.fetchall()]

    def get_structure_production_slots(self, structure_id: int) -> dict:
        """Get production slot information for a structure."""
        effective_cost = self.get_structure_capacity(structure_id)
        used_capacity = self.get_structure_used_capacity(structure_id)

        return {
            "effective_cost": effective_cost,
            "used_capacity": used_capacity,
            "remaining_capacity": effective_cost - used_capacity,
        }

    def list_bats(self, country_id, bat_type: str = "all"):
        """Retourne la liste des bâtiments d’un type donné pour un pays."""

        if bat_type.lower() == "all":
            self.cur.execute(
                """
                SELECT * FROM CountryStructuresView
                WHERE country_id = ?
                """,
                (country_id,),
            )
        else:
            matched = None
            for bt in bat_types.values():
                if bt[0].lower() == bat_type.lower():
                    matched = bt[0]
                    break
            if not matched:
                raise ValueError(f"Type de bâtiment inconnu : {bat_type}")
            self.cur.execute(
                """
                SELECT * FROM CountryStructuresView
                WHERE country_id = ? AND type = ?
                """,
                (country_id, matched),
            )
        return self.cur.fetchall()

    def give_bat(
        self, country_id, level: int, bat_type: int, specialisation: str, region_id: str
    ):
        """Ajoute un bâtiment dans une région donnée."""

        if region_id is None:
            raise ValueError("region_id est requis.")

        type_name, properties = bat_types[bat_type]
        ref_capacity = properties["capacity"]
        buff_percent = bat_buffs.get(level, 1)
        capacity = int((ref_capacity * buff_percent) / 100)

        self.cur.execute(
            """
            INSERT INTO Structures (region_id, type, specialisation, level, capacity, population)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (region_id, type_name, specialisation, level, capacity, 0),
        )
        self.conn.commit()

    def remove_bat(self, bat_id: int):
        """Remove buildings from a player."""
        self.cur.execute("SELECT * FROM Structures WHERE id = ?", (bat_id,))
        if self.cur.fetchone() is None:
            return

        self.cur.execute(
            """
            DELETE FROM Structures
            WHERE id = ?
            """,
            (bat_id,),
        )
        self.conn.commit()

    def edit_bat(self, bat_id: int, level: int = None, specialisation: str = None):
        """Modifie le niveau ou la spécialisation d’un bâtiment."""
        # On récupère l’ancien bâtiment
        self.cur.execute("SELECT type FROM Structures WHERE id = ?", (bat_id,))
        row = self.cur.fetchone()
        if not row:
            return

        bat_type = row[0]  # nom du type ("Usine", etc.)
        matched_type = next(
            (bt for bt in bat_types.values() if bt[0] == bat_type), None
        )
        if not matched_type:
            return

        updates = []
        params = []

        if level is not None:
            buff_percent = bat_buffs.get(level, 1)
            ref_capacity = matched_type[1]["capacity"]
            new_capacity = int((ref_capacity * buff_percent) / 100)

            updates += ["level = ?", "capacity = ?"]
            params += [level, new_capacity]

        if specialisation is not None:
            updates.append("specialisation = ?")
            params.append(specialisation)

        if updates:
            query = f"UPDATE Structures SET {', '.join(updates)} WHERE id = ?"
            params.append(bat_id)
            self.cur.execute(query, tuple(params))
            self.conn.commit()

    def get_pricings(self, item: str):
        """Get the pricing for a specific item."""
        self.cur.execute(
            "SELECT price, maintenance FROM InventoryPricings WHERE item = ?", (item,)
        )
        result = self.cur.fetchone()
        if result:
            return {"price": result[0], "maintenance": result[1]}
        return None

    def upgrade_bat(self, country_id, bat_id: int):
        """Améliore un bâtiment donné d’un pays."""

        self.cur.execute("SELECT type, level FROM Structures WHERE id = ?", (bat_id,))
        row = self.cur.fetchone()
        if not row:
            return "Bâtiment introuvable."

        bat_type_name, level = row
        matched_type = next(
            (bt for bt in bat_types.values() if bt[0] == bat_type_name), None
        )
        if not matched_type:
            return "Type de bâtiment invalide."

        if level >= 7:
            return "Niveau maximum atteint."

        new_level = level + 1
        cost = matched_type[1]["cost"]

        balance = self.get_balance(country_id)
        if balance is None or balance < cost:
            return "Solde insuffisant."

        # Paiement et mise à jour
        self.take_balance(country_id, cost)
        self.edit_bats(bat_id, level=new_level)
        return f"{bat_type_name} amélioré au niveau {new_level}."

    def get_leads(self, lead_type: int, user_id: str):
        if lead_type == 1:
            self.cur.execute("SELECT country_id FROM Inventory ORDER BY balance DESC")
        elif lead_type == 2:
            self.cur.execute(
                "SELECT country_id FROM Inventory ORDER BY pol_points DESC"
            )
        elif lead_type == 3:
            self.cur.execute(
                "SELECT country_id FROM Inventory ORDER BY diplo_points DESC"
            )
        elif lead_type == 4:
            self.cur.execute(
                "SELECT country_id FROM Inventory ORDER BY (balance * (pol_points + diplo_points)) DESC"
            )
        leaderboard = self.cur.fetchall()
        leaderboard = [
            str(row[0]) for row in leaderboard
        ]  # Extraire uniquement les `country_id` dans une liste
        return (
            leaderboard.index(str(user_id)) + 1 if str(user_id) in leaderboard else -1
        )

    def lead_economy(self, size: int = 10):
        """Get the leaderboard of players based on their balance."""
        if size <= 0:
            self.cur.execute(
                "SELECT country_id, balance FROM Inventory ORDER BY balance DESC"
            )
        else:
            self.cur.execute(
                "SELECT country_id, balance FROM Inventory ORDER BY balance DESC LIMIT ?",
                (size,),
            )
        leaderboard = self.cur.fetchall()
        leaderboard = [(str(row[0]), int(row[1])) for row in leaderboard]
        return leaderboard

    def lead_pol(self, size: int = 10):
        """Get the leaderboard of players based on their political points."""
        if size <= 0:
            self.cur.execute(
                "SELECT player_id, pol_points FROM inventory ORDER BY pol_points DESC"
            )
        else:
            self.cur.execute(
                "SELECT player_id, pol_points FROM inventory ORDER BY pol_points DESC LIMIT ?",
                (size,),
            )
        leaderboard = self.cur.fetchall()
        leaderboard = [(str(row[0]), int(row[1])) for row in leaderboard]
        return leaderboard

    def lead_diplo(self, size: int = 10):
        """Get the leaderboard of players based on their diplomatic points."""
        if size <= 0:
            self.cur.execute(
                "SELECT player_id, diplo_points FROM inventory ORDER BY diplo_points DESC"
            )
        else:
            self.cur.execute(
                "SELECT player_id, diplo_points FROM inventory ORDER BY diplo_points DESC LIMIT ?",
                (size,),
            )
        leaderboard = self.cur.fetchall()
        leaderboard = [(str(row[0]), int(row[1])) for row in leaderboard]
        return leaderboard

    def lead_all(self, size: int = 10):
        """Get the leaderboard of players based on their total points (balance + political points + diplomatic points)."""
        if size <= 0:
            self.cur.execute(
                "SELECT player_id, balance + pol_points + diplo_points FROM inventory ORDER BY balance + pol_points + diplo_points DESC"
            )
        else:
            self.cur.execute(
                "SELECT player_id, balance + pol_points + diplo_points FROM inventory ORDER BY balance + pol_points + diplo_points DESC LIMIT ?",
                (size,),
            )
        leaderboard = self.cur.fetchall()
        leaderboard = [(str(row[0]), int(row[1])) for row in leaderboard]
        return leaderboard

    async def get_leaderboard(self, offset=0, limit=10):
        """
        Récupère le classement des pays basé sur le total points :
        balance * (pol_points + diplo_points)
        Retourne aussi le rôle (role_id) pour affichage.
        """
        self.cur.execute(
            """
            SELECT Countries.role_id, Inventory.balance, Inventory.pol_points, Inventory.diplo_points
            FROM Inventory
            JOIN Countries ON Inventory.country_id = Countries.country_id
            ORDER BY (Inventory.balance * (Inventory.pol_points + Inventory.diplo_points)) DESC
            LIMIT ? OFFSET ?
        """,
            (limit, offset),
        )
        return self.cur.fetchall()

    # Fonction pour calculer le temps de production
    def calculer_temps_production(
        self, player_id, appareil, quantite: int, app_type=None, production_data={}
    ):
        # Connexion à la base de données
        self.cur.execute("SELECT * FROM inventory WHERE player_id = ?", (player_id,))
        player_data = self.cur.fetchone()

        if not player_data:
            return f"Player ID {player_id} not found."

        # Définir un mapping pour les colonnes de la base de données
        columns = [
            "player_id",
            "balance",
            "pol_points",
            "diplo_points",
        ]

        # Créer un dictionnaire des données du joueur
        player_inventory = dict(zip(columns, player_data))
        # Calculer la capacité de production totale par mois
        total_production_capacity = 0

        app_type = self.find_app_type(appareil, production_data)
        for i in range(1, 8):
            usine_lvl = f"usine_lvl{i}"
            usine_count = player_inventory[usine_lvl]
            if usine_count > 0:
                production_capacity = int(
                    production_data[str(i)]["production_mensuelle"][app_type][appareil]
                )
                total_production_capacity += production_capacity * usine_count

        if total_production_capacity == 0:
            return f"Player ID {player_id} has no production capacity for {appareil}."

        # Calculer le temps nécessaire pour produire la quantité demandée
        # return f"Quantite: {quantite}, total_production_capacity: {total_production_capacity}. Type appareil: {type(quantite)}, {type(total_production_capacity)}"
        time_needed_months = math.ceil(int(quantite) / int(total_production_capacity))

        return f"Pour produire {quantite} {appareil} (type {app_type}), il vous faudra {time_needed_months} mois. Vous avez une capacité de production totale de {total_production_capacity} par mois."

    def find_app_type(self, app_name, production_data={}):
        app_types = ["terrestre", "navale", "aerienne", "explosif"]

        for app_type in app_types:
            for apparel in production_data["7"]["production_mensuelle"][app_type]:
                if apparel.lower() == app_name.lower():
                    return app_type
        return None

    def leak_db(self):
        """Leak the database content, renvoie colonnes et lignes."""
        self.cur.execute("SELECT * FROM inventory")
        rows = self.cur.fetchall()
        columns = [desc[0] for desc in self.cur.description]
        return columns, rows

    def has_permission(self, country_id: str, player_id: str, permission: str) -> bool:
        self.cur.execute(
            f"""
            SELECT 1 FROM Governments
            WHERE country_id = ? AND player_id = ? AND {permission} = 1
        """,
            (country_id, player_id),
        )
        return self.cur.fetchone() is not None

    def add_region_to_country(
        self, country_id: str, region_name: str, population: int = 0
    ) -> int:
        """Ajoute une région à un pays, et met à jour automatiquement la population du pays."""
        # Vérifie si la région existe déjà
        self.cur.execute(
            "SELECT region_id, country_id FROM Regions WHERE name = ?", (region_name,)
        )
        region = self.cur.fetchone()

        if region:
            region_id, old_country_id = region
            # Mise à jour du rattachement
            self.cur.execute(
                "UPDATE Regions SET country_id = ? WHERE region_id = ?",
                (country_id, region_id),
            )
        else:
            # Nouvelle région → insertion
            self.cur.execute(
                "INSERT INTO Regions (country_id, name, mapchart_name, population) VALUES (?, ?, ?, ?)",
                (
                    country_id,
                    region_name,
                    region_name,
                    population,
                ),  # mapchart_name = name par défaut
            )
            region_id = self.cur.lastrowid
        self.conn.commit()
        return region_id

    async def get_tech_datas(self, tech_type: str, tech_level: int, key: str):
        """Récupère les données d'une technologie spécifique."""
        self.cur.execute(
            f"SELECT minimum_{key} FROM TechnologyDatas WHERE type = ? AND level = ?",
            (tech_type, tech_level),
        )
        minimum = self.cur.fetchone()
        self.cur.execute(
            f"SELECT maximum_{key} FROM TechnologyDatas WHERE type = ? AND level = ?",
            (tech_type, tech_level),
        )
        maximum = self.cur.fetchone()
        if minimum and maximum:
            return (minimum[0], maximum[0])
        return None

    def get_tech(self, tech_id: int):
        """Récupère les données d'une technologie par son ID."""
        self.cur.execute(
            """
            SELECT t.*, c.name as country_name 
            FROM Technologies t 
            LEFT JOIN Countries c ON t.developed_by = c.country_id 
            WHERE t.tech_id = ?
        """,
            (tech_id,),
        )
        result = self.cur.fetchone()
        if result:
            tech_data = {
                "tech_id": result["tech_id"],
                "name": result["name"],
                "original_name": result["original_name"],
                "type": result["type"],
                "technology_level": result["technology_level"],
                "developed_by": result["developed_by"],
                "country_name": result["country_name"],
                "development_cost": result["development_cost"],
                "development_time": result["development_time"],
                "cost": result["cost"],
                "slots_taken": result["slots_taken"],
                "image_url": result["image_url"],
                "specialisation": result["specialisation"],
            }
            return tech_data
        return None

    def get_attributes_by_tech(self, tech_id: int):
        """Récupère les attributs d'une technologie par son ID."""
        self.cur.execute(
            """
            SELECT attribute_name, attribute_value 
            FROM TechnologyAttributes 
            WHERE tech_id = ?
        """,
            (tech_id,),
        )
        attributes = self.cur.fetchall()
        # Return as list of dictionaries for compatibility with get_infos command
        return [
            {"attribute_name": attr[0], "attribute_value": attr[1]}
            for attr in attributes
        ]

    async def get_player_role(self, ctx):
        role_id = self.db.get_setting("player_role_id")
        return ctx.guild.get_role(role_id)

    async def get_non_player_role(self, ctx):
        role_id = self.db.get_setting("non_player_role_id")
        return ctx.guild.get_role(role_id)

    def get_players_government(self, player_id: int) -> str:
        """Récupère le gouvernement d'un joueur."""
        self.cur.execute(
            "SELECT country_id FROM Governments WHERE player_id = ?", (player_id,)
        )
        result = self.cur.fetchone()
        return result[0] if result else None

    def get_population_by_country(self, country_id: str) -> int:
        """Récupère la population totale d'un pays."""
        self.cur.execute(
            "SELECT * FROM PopulationView WHERE country_id = ?", (country_id,)
        )
        result = self.cur.fetchone()
        return result[0] if result and result[0] is not None else 0

    def get_population_capacity_by_country(self, country_id: str) -> int:
        """Récupère la capacité d'accueil totale d'un pays."""
        self.cur.execute(
            "SELECT * FROM PopulationCapacityView WHERE country_id = ?", (country_id,)
        )
        result = self.cur.fetchone()
        return result[0] if result and result[0] is not None else 0

    def set_paused(self, is_paused: bool):
        """Met à jour l'état de pause du temps RP."""
        paused_value = 1 if is_paused else 0
        self.cur.execute(
            "INSERT OR IGNORE INTO ServerSettings (key, value) VALUES ('is_paused', ?)",
            (paused_value,),
        )
        # Met à jour la valeur si elle existe déjà
        self.cur.execute(
            "UPDATE ServerSettings SET value = ? WHERE key = 'is_paused'",
            (paused_value,),
        )
        self.conn.commit()

    def get_setting(self, key: str) -> str:
        """Récupère une valeur de paramètre du serveur."""
        self.cur.execute("SELECT value FROM ServerSettings WHERE key = ?", (key,))
        result = self.cur.fetchone()
        if result:
            return result[0]
        return None

    def is_paused(self) -> bool:
        """Vérifie si le temps RP est en pause."""
        return self.get_setting("is_paused") == "1"

    def get_stats_by_country(self, country_id: str) -> dict:
        """Récupère les stats d'un pays."""
        self.cur.execute("SELECT * FROM StatsView WHERE country_id = ?", (country_id,))
        result = self.cur.fetchone()
        if result:
            return {
                "country_id": result["country_id"],
                "name": result["name"],
                "population": result["population"],
                "population_capacity": result["population_capacity"],
                "tech_level": result["tech_level"],
                "gdp": result["gdp"],
            }
        return {
            "country_id": country_id,
            "name": None,
            "population": 0,
            "population_capacity": 0,
            "tech_level": 1,
            "gdp": 0,
        }

    def add_technology(
        self,
        specialisation,
        name,
        inspiration_name,
        tech_type,
        tech_level,
        country_id,
        dev_cost,
        dev_time,
        prod_cost,
        slots_taken,
        image_url,
        tech_data,
    ):
        temp_datas = tech_data.copy()
        temp_datas.pop("nom", None)
        temp_datas.pop("tech_inspiration", None)
        temp_datas.pop("specialisation", None)
        temp_datas.pop("niveau_technologique", None)
        temp_datas.pop("country_id", None)
        temp_datas.pop("final_dev_cost", None)
        temp_datas.pop("final_dev_time", None)
        temp_datas.pop("final_prod_cost", None)
        temp_datas.pop("final_slots_taken", None)
        temp_datas.pop("image_url", None)
        secret = temp_datas.pop("is_secret", None)

        """Ajoute une technologie à la base de données."""
        self.cur.execute(
            """
            INSERT INTO Technologies (name, original_name, type, is_secret, technology_level, developed_by, development_cost, development_time, cost, slots_taken, image_url, specialisation)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
            (
                name,
                inspiration_name,
                tech_type,
                1 if secret else 0,  # is_secret
                tech_level,
                country_id,
                dev_cost,
                dev_time,
                prod_cost,
                slots_taken,
                image_url,
                specialisation,
            ),
        )
        for key, value in temp_datas.items():
            self.cur.execute(
                """
                INSERT INTO TechnologyAttributes (tech_id, attribute_name, attribute_value)
                VALUES ((SELECT tech_id FROM Technologies WHERE name = ? AND type = ? AND technology_level = ?), ?, ?)
            """,
                (name, tech_type, tech_level, key, value),
            )
        self.conn.commit()
        return self.cur.lastrowid

    def get_current_date(self) -> dict:
        """Récupère la date actuelle du jeu."""
        self.cur.execute(
            "SELECT year, month, playday FROM Dates ORDER BY real_date DESC LIMIT 1"
        )
        result = self.cur.fetchone()
        if result:
            return {
                "year": result["year"],
                "month": result["month"],
                "playday": result["playday"],
            }
        return {"year": 2023, "month": 1, "playday": 0}

    def get_date_from_irl(self, date_str: str) -> dict:
        """Récupère la date du jeu à partir d'une date IRL."""
        self.cur.execute(
            "SELECT year, month, playday FROM Dates WHERE real_date = ?", (date_str,)
        )
        result = self.cur.fetchone()
        if result:
            return {
                "year": result["year"],
                "month": result["month"],
                "playday": result["playday"],
            }
        return None

    def get_playdays_in_month(self, month: int) -> int:
        """Récupère le nombre de playdays dans un mois donné."""
        self.cur.execute(
            "SELECT playdays FROM PlaydaysPerMonth WHERE month_number = ?", (month,)
        )
        result = self.cur.fetchone()
        return result["playdays"] if result else 2

    async def advance_playday(self):
        # Récupère la dernière date enregistrée
        self.cur.execute("SELECT * FROM Dates ORDER BY real_date DESC LIMIT 1")
        row = self.cur.fetchone()

        today = datetime.now(timezone.utc)
        today_str = today.isoformat()  # Convert to ISO string format for comparison

        is_paused = self.is_paused()
        if is_paused:
            print("⏸️ Temps RP en pause. Rien à faire.")
            return

        if row:
            year, month, playday = row["year"], row["month"], row["playday"]
        else:
            year, month, playday = 2023, 1, 0

        # Récupérer le nombre de playdays max pour le mois
        self.cur.execute(
            "SELECT playdays FROM PlaydaysPerMonth WHERE month_number = ?", (month,)
        )
        playdays_result = self.cur.fetchone()
        if not playdays_result:
            print(
                f"⚠️ Aucune configuration trouvée pour le mois {month}, utilisation de 2 playdays par défaut"
            )
            playdays_in_month = 2
        else:
            playdays_in_month = playdays_result["playdays"]

        if playday < playdays_in_month:
            playday += 1
        else:
            playday = 1
            if month == 12:
                year += 1
                month = 1
                self.set_paused(True)  # Pause le temps RP à la fin de l'année
                is_paused = True
            else:
                month += 1

        # Vérifier si cette date existe déjà avant d'insérer
        self.cur.execute(
            """
            SELECT 1 FROM Dates 
            WHERE year = ? AND month = ? AND playday = ?
        """,
            (year, month, playday),
        )

        if self.cur.fetchone():
            print(f"⚠️ Date {year}-{month}-{playday} existe déjà, pas d'insertion")
            return

        # Insérer la nouvelle ligne
        self.cur.execute(
            """
            INSERT INTO Dates (year, month, playday, real_date)
            VALUES (?, ?, ?, ?)
        """,
            (year, month, playday, today_str),
        )

        self.conn.commit()
        print(f"📅 Avancé à {year}-{month}-{playday} (pause: {is_paused})")

    def get_country_by_name(self, country_name: str) -> str:
        """Récupère l'ID d'un pays par son nom."""
        self.cur.execute(
            "SELECT country_id FROM Countries WHERE name = ?", (country_name,)
        )
        result = self.cur.fetchone()
        return result[0] if result else None

    def get_country_secret_channel(self, country_id: str) -> str:
        """Récupère le canal secret d'un pays."""
        self.cur.execute(
            "SELECT secret_channel_id FROM Countries WHERE country_id = ?",
            (country_id,),
        )
        result = self.cur.fetchone()
        return result[0] if result else None

    def get_players_country(self, player_id: str) -> str:
        """Récupère le pays d'un joueur."""
        self.cur.execute(
            "SELECT country_id FROM Governments WHERE player_id = ?", (player_id,)
        )
        result = self.cur.fetchone()
        return result[0] if result else None

    def get_country_by_role(self, role_id: str) -> str:
        """Récupère le pays associé à un rôle Discord."""
        self.cur.execute(
            "SELECT country_id FROM Countries WHERE role_id = ?", (role_id,)
        )
        result = self.cur.fetchone()
        return result[0] if result else None

    def get_country_by_id(self, country_id: str) -> str:
        """Récupère le nom d'un pays par son ID."""
        self.cur.execute(
            "SELECT name FROM Countries WHERE country_id = ?", (country_id,)
        )
        result = self.cur.fetchone()
        return result[0] if result else None

    def get_country_role_with_id(self, country_id: str) -> str:
        """Récupère le rôle associé à un pays par son ID."""
        self.cur.execute(
            "SELECT role_id FROM Countries WHERE country_id = ?", (country_id,)
        )
        result = self.cur.fetchone()
        return result[0] if result else None

    def get_country_datas(self, country_id: str) -> dict:
        """Récupère les données d'un pays."""
        self.cur.execute("SELECT * FROM Countries WHERE country_id = ?", (country_id,))
        result = self.cur.fetchone()
        if result:
            return {
                "country_id": result["country_id"],
                "name": result["name"],
                "role_id": result["role_id"],
                "public_channel_id": result["public_channel_id"],
                "secret_channel_id": result["secret_channel_id"],
                "last_bilan": result["last_bilan"],
            }
        return None

    def add_units(self, country_id: str, unit_type: str, quantity: int):
        """Ajoute des unités à un pays."""
        if quantity <= 0:
            raise ValueError("La quantité doit être supérieure à zéro.")

        if self.get_units(country_id, unit_type) > 0:
            # Si des unités existent déjà, on met à jour la quantité
            self.cur.execute(
                """
                UPDATE InventoryUnits
                SET quantity = quantity + ?
                WHERE country_id = ? AND unit_type = ?
                """,
                (quantity, country_id, unit_type),
            )
        else:
            self.cur.execute(
                """
                INSERT INTO InventoryUnits (country_id, unit_type, quantity)
                VALUES (?, ?, ?)
                """,
                (country_id, unit_type, quantity),
            )
        self.conn.commit()

    def get_units(self, country_id: str, unit_type: str = None) -> int:
        """Récupère le nombre d'unités d'un type spécifique pour un pays."""
        if unit_type:
            self.cur.execute(
                "SELECT quantity FROM InventoryUnits WHERE country_id = ? AND unit_type = ?",
                (country_id, unit_type),
            )
            result = self.cur.fetchone()
            return result[0] if result else 0
        return 0

    def execute_script(self, script: str):
        """Execute a SQL script."""
        try:
            self.cur.executescript(script)
            self.conn.commit()
        except sqlite3.Error as e:
            print(f"Erreur lors de l'exécution du script : {e}")
            self.conn.rollback()

    def get_structure_informations(self, structure_id: int) -> dict:
        return self.cur.execute(
            """
            SELECT * FROM CountryStructuresView WHERE country_id = ?
            """,
            (structure_id,),
        ).fetchone()

    def start_production(
        self, structure_id: int, tech_id: int, quantity: int, country_id: int
    ) -> dict:
        """Start production of a technology in a structure."""
        try:
            # Get technology details
            tech = self.get_tech(tech_id)
            if not tech:
                return {"success": False, "error": "Technology not found"}

            # Check if country has license or developed the technology
            if not self.has_technology_access(country_id, tech_id):
                return {
                    "success": False,
                    "error": "No license or ownership for this technology",
                }

            # Get structure information
            structure_info = self.get_structure_informations(structure_id)
            if not structure_info:
                return {"success": False, "error": "Structure not found"}

            # Check if structure belongs to country
            if structure_info["country_id"] != country_id:
                return {
                    "success": False,
                    "error": "Structure does not belong to your country",
                }

            # Check if structure is a factory (Usine)
            if structure_info["type"] != "Usine":
                return {
                    "success": False,
                    "error": "Production can only be done in factories (Usine)",
                }

            # Calculate slot requirements
            slots_needed = (
                tech["slots_taken"] * (1 + (tech["technology_level"] / 10.0)) * quantity
            )

            # Get structure capacity
            capacity_info = self.get_structure_production_slots(structure_id)
            if slots_needed > capacity_info["remaining_capacity"]:
                return {
                    "success": False,
                    "error": f"Not enough free slots. Need: {slots_needed:.1f}, Available: {capacity_info['remaining_capacity']:.1f}",
                }

            # Calculate total cost
            total_cost = tech["cost"] * quantity
            if not self.has_enough_balance(country_id, total_cost):
                return {
                    "success": False,
                    "error": f"Insufficient balance. Need: {total_cost:,}",
                }

            # Calculate production time with special delays
            production_delays = {
                "frigate": 2,  # 2 months
                "aircraft_carrier": 12,  # 12 months
                "nuclear_submarine": 12,  # 12 months
            }

            base_time = 1  # Default 1 month
            tech_type_lower = tech["type"].lower()
            production_time = production_delays.get(tech_type_lower, base_time)

            # Start production
            self.take_balance(country_id, total_cost)

            # Add to StructureProduction table (replacing if exists)
            self.cur.execute(
                """
                INSERT OR REPLACE INTO StructureProduction 
                (structure_id, tech_id, quantity, days_remaining, started_at)
                VALUES (?, ?, ?, ?, ?)
            """,
                (
                    structure_id,
                    tech_id,
                    quantity,
                    production_time * 30,
                    datetime.now().isoformat(),
                ),
            )

            self.conn.commit()

            return {
                "success": True,
                "cost": total_cost,
                "production_time": production_time,
                "slots_used": slots_needed,
            }

        except Exception as e:
            return {"success": False, "error": f"Database error: {str(e)}"}

    def has_technology_access(self, country_id: int, tech_id: int) -> bool:
        """Check if country has access to technology (owns it or has license)."""
        # Check if country developed it
        self.cur.execute(
            """
            SELECT 1 FROM Technologies 
            WHERE tech_id = ? AND developed_by = ?
        """,
            (tech_id, country_id),
        )

        if self.cur.fetchone():
            return True

        # Check if country has license
        self.cur.execute(
            """
            SELECT 1 FROM TechnologyLicenses 
            WHERE tech_id = ? AND country_id = ?
        """,
            (tech_id, country_id),
        )

        return self.cur.fetchone() is not None

    def sell_technology_inventory(
        self,
        seller_country_id: int,
        buyer_country_id: int,
        tech_id: int,
        quantity: int,
        price_per_unit: int = None,
        total_price: int = None,
    ) -> dict:
        """Sell technology from inventory to another country."""
        try:
            # Validate inputs
            if price_per_unit is None and total_price is None:
                return {
                    "success": False,
                    "error": "Must specify either price_per_unit or total_price",
                }

            if price_per_unit is not None and total_price is not None:
                return {
                    "success": False,
                    "error": "Cannot specify both price_per_unit and total_price",
                }

            # Check if seller has enough inventory
            self.cur.execute(
                """
                SELECT quantity FROM CountryTechnologyInventory 
                WHERE country_id = ? AND tech_id = ?
            """,
                (seller_country_id, tech_id),
            )

            result = self.cur.fetchone()
            if not result or result["quantity"] < quantity:
                available = result["quantity"] if result else 0
                return {
                    "success": False,
                    "error": f"Insufficient inventory. Have: {available}, Need: {quantity}",
                }

            # Calculate price
            if price_per_unit is not None:
                final_price = price_per_unit * quantity
            else:
                final_price = total_price

            # Check buyer balance
            if not self.has_enough_balance(buyer_country_id, final_price):
                return {"success": False, "error": "Buyer has insufficient balance"}

            # Execute transfer
            # Remove from seller inventory
            self.cur.execute(
                """
                UPDATE CountryTechnologyInventory 
                SET quantity = quantity - ? 
                WHERE country_id = ? AND tech_id = ?
            """,
                (quantity, seller_country_id, tech_id),
            )

            # Add to buyer inventory
            self.cur.execute(
                """
                INSERT OR REPLACE INTO CountryTechnologyInventory 
                (country_id, tech_id, quantity)
                VALUES (?, ?, 
                    COALESCE((SELECT quantity FROM CountryTechnologyInventory 
                             WHERE country_id = ? AND tech_id = ?), 0) + ?)
            """,
                (buyer_country_id, tech_id, buyer_country_id, tech_id, quantity),
            )

            # Transfer money
            self.take_balance(buyer_country_id, final_price)
            self.give_balance(seller_country_id, final_price)

            self.conn.commit()

            return {
                "success": True,
                "quantity": quantity,
                "total_price": final_price,
                "price_per_unit": final_price / quantity,
            }

        except Exception as e:
            return {"success": False, "error": f"Database error: {str(e)}"}

    def process_production_cycle(self) -> list:
        """Process all ongoing productions and complete those that are ready."""
        completed_productions = []

        try:
            # Get all ongoing productions
            self.cur.execute(
                """
                SELECT sp.*, t.name as tech_name, t.type as tech_type
                FROM StructureProduction sp
                JOIN Technologies t ON sp.tech_id = t.tech_id
                WHERE sp.days_remaining > 0
            """
            )

            productions = self.cur.fetchall()

            for production in productions:
                # Decrease remaining time
                new_days_remaining = production["days_remaining"] - 1

                if new_days_remaining <= 0:
                    # Production complete - add to inventory
                    structure_info = self.get_structure_informations(
                        production["structure_id"]
                    )
                    country_id = structure_info["country_id"]

                    # Add to country inventory
                    self.cur.execute(
                        """
                        INSERT OR REPLACE INTO CountryTechnologyInventory 
                        (country_id, tech_id, quantity)
                        VALUES (?, ?, 
                            COALESCE((SELECT quantity FROM CountryTechnologyInventory 
                                     WHERE country_id = ? AND tech_id = ?), 0) + ?)
                    """,
                        (
                            country_id,
                            production["tech_id"],
                            country_id,
                            production["tech_id"],
                            production["quantity"],
                        ),
                    )

                    # Remove from production queue
                    self.cur.execute(
                        """
                        DELETE FROM StructureProduction 
                        WHERE structure_id = ? AND tech_id = ?
                    """,
                        (production["structure_id"], production["tech_id"]),
                    )

                    completed_productions.append(
                        {
                            "country_id": country_id,
                            "tech_name": production["tech_name"],
                            "tech_type": production["tech_type"],
                            "quantity": production["quantity"],
                            "structure_id": production["structure_id"],
                        }
                    )
                else:
                    # Update remaining time
                    self.cur.execute(
                        """
                        UPDATE StructureProduction 
                        SET days_remaining = ? 
                        WHERE structure_id = ? AND tech_id = ?
                    """,
                        (
                            new_days_remaining,
                            production["structure_id"],
                            production["tech_id"],
                        ),
                    )

            self.conn.commit()
            return completed_productions

        except Exception as e:
            print(f"Error processing production cycle: {e}")
            return []

    def get_country_productions(self, country_id: int) -> list:
        """Get all ongoing productions for a country."""
        try:
            self.cur.execute(
                """
                SELECT sp.*, t.name as tech_name, t.type as tech_type, 
                       s.type as structure_type, r.name as region_name
                FROM StructureProduction sp
                JOIN Technologies t ON sp.tech_id = t.tech_id
                JOIN Structures s ON sp.structure_id = s.id
                JOIN Regions r ON s.region_id = r.region_id
                WHERE r.country_id = ?
                ORDER BY sp.days_remaining ASC
            """,
                (country_id,),
            )

            return [dict(row) for row in self.cur.fetchall()]

        except Exception as e:
            print(f"Error getting country productions: {e}")
            return []
