import sqlite3
from config import debug
import math
import os

class Database:
    """Database class to handle database operations."""

    def __init__(self, path="datas/rts.db"):
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
                    if debug:
                        print(f"{filename}:\n{content}\n")
                        dbs_content[filename] = content
                    cur.executescript(content)
        conn.commit()
        if debug:
            with open("dbs_log.txt", "w", encoding="utf-8") as f:
                for name, sql in dbs_content.items():
                    f.write(f"\n=== {name} ===\n")
                    f.write(sql)
                    f.write("\n\n")
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

    # Building-related database functions
    def get_bats(self, country_id, level, bat_type: int, specialization: str = None):
        """Retourne le nombre de bâtiments d’un type et niveau donnés pour un pays."""
        from config import bat_types

        type_name = bat_types[bat_type][0]

        if not specialization:
            self.cur.execute(
                """
                SELECT COUNT(*) FROM CountryStructuresView
                WHERE country_id = ? AND type = ? AND level = ?
                """,
                (country_id, type_name, level),
            )
        else:
            self.cur.execute(
                """
                SELECT COUNT(*) FROM CountryStructuresView
                WHERE country_id = ? AND type = ? AND specialization = ? AND level = ?
                """,
                (country_id, type_name, specialization, level),
            )

        result = self.cur.fetchone()
        return result[0] if result else 0

    def list_bats(self, country_id, bat_type: str = "all"):
        """Retourne la liste des bâtiments d’un type donné pour un pays."""
        from config import bat_types

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
        self, country_id, level: int, bat_type: int, specialization: str, region_id: str
    ):
        """Ajoute un bâtiment dans une région donnée."""
        from config import bat_types, bat_buffs

        if region_id is None:
            raise ValueError("region_id est requis.")

        type_name, properties = bat_types[bat_type]
        ref_capacity = properties["capacity"]
        buff_percent = bat_buffs.get(level, 1)
        capacity = int((ref_capacity * buff_percent) / 100)

        self.cur.execute(
            """
            INSERT INTO Structures (region_id, type, specialization, level, capacity, population)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (region_id, type_name, specialization, level, capacity, 0),
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

    def edit_bat(self, bat_id: int, level: int = None, specialization: str = None):
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

        if specialization is not None:
            updates.append("specialization = ?")
            params.append(specialization)

        if updates:
            query = f"UPDATE Structures SET {', '.join(updates)} WHERE id = ?"
            params.append(bat_id)
            self.cur.execute(query, tuple(params))
            self.conn.commit()

    def upgrade_bat(self, country_id, bat_id: int):
        """Améliore un bâtiment donné d’un pays."""
        from config import bat_types, bat_buffs

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
            self.cur.execute("SELECT country_id FROM Inventory ORDER BY pol_points DESC")
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
        self.cur.execute("""
            SELECT Countries.role_id, Inventory.balance, Inventory.pol_points, Inventory.diplo_points
            FROM Inventory
            JOIN Countries ON Inventory.country_id = Countries.country_id
            ORDER BY (Inventory.balance * (Inventory.pol_points + Inventory.diplo_points)) DESC
            LIMIT ? OFFSET ?
        """, (limit, offset))
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

    def drop_all_except_inventory(db_path="datas/rts_clean.db"):
        conn = sqlite3.connect(db_path)
        cur = conn.cursor()
        cur.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = [row[0] for row in cur.fetchall()]
        tables_to_drop = [
            t for t in tables if t != "inventory" and not t.startswith("sqlite_")
        ]
        cur.execute("PRAGMA foreign_keys = OFF;")
        for table in tables_to_drop:
            print(f"Suppression de la table: {table}")
            cur.execute(f"DROP TABLE IF EXISTS {table};")
        cur.execute("PRAGMA foreign_keys = ON;")
        conn.commit()
        conn.close()
        print("Suppression terminée.")

    def has_permission(country_id: str, player_id: str, permission: str) -> bool:
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

    async def get_player_role(ctx):
        return ctx.guild.get_role(873955562734362625)

    async def get_non_player_role(ctx):
        return ctx.guild.get_role(873955513921048646)

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
    
    def get_country_datas(self, country_id: str) -> dict:
        """Récupère les données d'un pays."""
        self.cur.execute(
            "SELECT * FROM Countries WHERE country_id = ?", (country_id,)
        )
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

    def execute_script(self, script: str):
        """Execute a SQL script."""
        try:
            self.cur.executescript(script)
            self.conn.commit()
        except sqlite3.Error as e:
            print(f"Erreur lors de l'exécution du script : {e}")
            self.conn.rollback()
            
    def debug_init(self):
        test_data = [
            {
                "name": "Testland",
                "role_id": "873645550820556831",
                "public_channel_id": "9876543210",
                "secret_channel_id": None,
                "region": "Testopolis",
                "region_map": "testopolis_map",
                "user_id": "293869524091142144",
            },
            {
                "name": "Debuglia",
                "role_id": "873645549826486323",
                "public_channel_id": "9876543211",
                "secret_channel_id": None,
                "region": "Debugton",
                "region_map": "debugton_map",
                "user_id": "868399385149579274",
            }
        ]

        for country in test_data:
            # 1. Vérifier l'existence
            self.cur.execute("SELECT country_id FROM Countries WHERE name = ?", (country["name"],))
            existing = self.cur.fetchone()
            if existing:
                print(f"Pays de test '{country['name']}' déjà existant.")
                continue

            # 2. Créer le pays
            self.cur.execute("""
                INSERT INTO Countries (name, role_id, public_channel_id, secret_channel_id)
                VALUES (?, ?, ?, ?)
            """, (
                country["name"],
                country["role_id"],
                country["public_channel_id"],
                country["secret_channel_id"]
            ))
            self.conn.commit()

            # 3. Récupérer l’ID
            self.cur.execute("SELECT country_id FROM Countries WHERE name = ?", (country["name"],))
            country_id = self.cur.fetchone()[0]

            # 4. Région fictive
            self.cur.execute("""
                INSERT INTO Regions (country_id, name, mapchart_name, population)
                VALUES (?, ?, ?, ?)
            """, (country_id, country["region"], country["region_map"], 100000))
            self.conn.commit()

            # 5. Gouvernement
            self.cur.execute("""
                INSERT INTO Governments (
                    country_id, slot, player_id,
                    can_spend_money, can_spend_points, can_sign_treaties,
                    can_build, can_recruit, can_produce, can_declare_war
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                country_id, 1, country["user_id"],
                True, True, True,
                True, True, True, True
            ))
            self.conn.commit()

            # 6. Inventaire
            self.cur.execute("""
                INSERT INTO Inventory (
                    country_id, balance, pol_points, diplo_points,
                    soldiers, reserves
                ) VALUES (?, ?, ?, ?, ?, ?)
            """, (country_id, 100000, 50, 50, 1000, 500))
            self.conn.commit()

            # 7. Stats
            self.cur.execute("""
                INSERT INTO Stats (country_id, tech_level, gdp)
                VALUES (?, ?, ?)
            """, (country_id, 2, 1500000))
            self.conn.commit()

            print(f"Pays de test '{country['name']}' créé avec l'ID {country_id} et l'utilisateur {country['user_id']} au gouvernement.")
