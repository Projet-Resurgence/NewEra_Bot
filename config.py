import discord

# Debug flag
debug = False

# Discord setup
intents = discord.Intents().all()

# Important IDs
bi_admins_id = [
    293869524091142144,
    557638191231008768,
    1225576816958242877,
    868399385149579274,
]
usefull_role_ids_dic = {"staff": 1230046019262087198}

# Error messages
Erreurs = {
    "Erreur 1": "Le salon dans lequel vous effectuez la commande n'est pas le bon\n",
    "Erreur 2": "Aucun champ de recherche n'a été donné\n",
    "Erreur 3": "Le champ de recherche donné est invalide\n",
    "Erreur 3.2": "Le champ de recherche donné est invalide - Le pays n'est pas dans les fichiers\n",
    "Erreur 4": "La pause est déjà en cours\n",
    "Erreur 5": "Vous n'avez pas la permission de faire la commande.\n",
}

# Continents
continents = ["Europe", "Amerique", "Asie", "Afrique", "Moyen-Orient", "Oceanie"]
continents_dict = {
    "oceanie": 992368253580087377,
    "asie": 1243672298381381816,
    "moyen-orient": 951163668102520833,
    "afrique": 961678827933794314,
    "amerique": 952314456870907934,
    "europe": 955479237001891870,
}

# Starting resources
starting_amounts = {"money": 500000000, "pd": 4, "pp": 2}

# Colors for embeds
error_color_int = int("FF5733", 16)
money_color_int = int("FFF005", 16)
p_points_color_int = int("006AFF", 16)
d_points_color_int = int("8b1bd1", 16)
all_color_int = int("00FF44", 16)
factory_color_int = int("6E472E", 16)

# Code list for logging
code_list = [
    "M1",
    "M2",
    "M3",
    "M4",
    "M5",
    "MR",
    "MRR",
    "P1",
    "P2",
    "P3",
    "P4",
    "PR",
    "PRR",
]

# Building types configuration
# ID: ["Name", {"capacity:" capacity, "cost": cost}]
bat_types = {
    0: ["Usine", {"capacity": 1000, "cost": 100000}],
    1: ["Base", {"capacity": 800, "cost": 90000}],
    2: ["Ecole", {"capacity": 500, "cost": 60000}],
    3: ["Logement", {"capacity": 1500, "cost": 50000}],
}

bat_buffs = {
    1: 10, 2: 25, 3: 30, 4: 50,
    5: 75, 6: 85, 7: 100
}


# Construction costs
wall_prices = {
    "béton": (60, 150),  # prix par m³
    "ossature métallique": (1000, 1000),  # prix par m²
}

# Global variables
groq_chat_history = []
embed_p = ""
duration_in_seconds = 0
