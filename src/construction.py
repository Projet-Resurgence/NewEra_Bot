from io import StringIO
import discord

"""
Construction utilities for NEBot.
Contains functions for construction cost and area calculations.
"""

def calculate_total_area(taille_moyenne, nombre_logements):
    return taille_moyenne * nombre_logements

def calculate_construction_cost(datas, total_area, building):
    mur_price = datas.get("wall_prices", {}).get(datas.get("type_murs"), (0,))[0]
    mur_cost = mur_price * total_area
    etages = building.get("nombre_etages", 1)
    prix_fonda = datas.get("prix_fondations", 0) + (etages * 50)
    fondations_cost = prix_fonda * (
        building.get("surface_net", 0) * building.get("profondeur_fondation", 0)
    )
    construction_cost = (
        total_area * datas.get("prix_moyen", 0) + mur_cost + fondations_cost
    )
    return construction_cost

def get_people_per_apartment(taille_moyenne):
    surface_per_first_4 = 8
    surface_per_additional = 6
    initial_habitants = 4
    initial_surface = initial_habitants * surface_per_first_4
    if taille_moyenne >= initial_surface:
        remaining_surface = taille_moyenne - initial_surface
        additional_habitants = remaining_surface // surface_per_additional
        total_habitants = initial_habitants + additional_habitants
    else:
        total_habitants = taille_moyenne // surface_per_first_4
    return total_habitants

async def calculate_by_population_from_datas(ctx_or_interaction, datas):
    buildings = []
    current_building = {
        "nombre_etages": 1,
        "nombre_logements": 1,
        "people_per_apartment": datas["people_per_apartment"],
        "surface": 0,
        "surface_net": 0,
        "surface_habitable": 0,
        "surface_net_habitable": 0,
        "construction_cost": 0,
        "profondeur_fondation": 3,
    }
    actual_stage_logements = 0

    while True:
        total_area = calculate_total_area(
            datas["taille_moyenne"], current_building["nombre_logements"]
        )
        current_building["surface"] = total_area
        current_building["surface_net"] = round(
            total_area / current_building["nombre_etages"]
        )
        current_building["construction_cost"] = calculate_construction_cost(
            datas, total_area, current_building
        )
        current_building["surface_habitable"] = total_area - (total_area * 0.1)
        current_building["surface_net_habitable"] = round(
            current_building["surface_habitable"] / current_building["nombre_etages"]
        )
        current_building["profondeur_fondation"] = current_building["nombre_etages"] + 1

        if (
            sum(
                building["nombre_logements"] * building["people_per_apartment"]
                for building in buildings + [current_building]
            )
            >= datas["objectif"]
        ):
            buildings.append(current_building)
            break

        current_building["nombre_logements"] += 1
        actual_stage_logements += 1
        if actual_stage_logements >= datas["max_apartments"]:
            if current_building["nombre_etages"] < datas["max_etages"]:
                current_building["nombre_etages"] += 1
                actual_stage_logements = 0
            else:
                buildings.append(current_building)
                current_building = {
                    "nombre_etages": 1,
                    "nombre_logements": 1,
                    "people_per_apartment": datas["people_per_apartment"],
                    "surface": 0,
                    "surface_net": 0,
                    "surface_habitable": 0,
                    "surface_net_habitable": 0,
                    "construction_cost": 0,
                    "profondeur_fondation": 3,
                }

    return buildings, datas

async def calculate_by_budget_from_datas(interaction, datas: dict):
    """
    Calcule les immeubles pouvant être construits avec un budget donné (déjà présent dans `datas["objectif"]`).
    Renvoie la liste des bâtiments et les données enrichies.
    """

    buildings = []
    current_building = {
        "nombre_etages": 1,
        "nombre_logements": 1,
        "people_per_apartment": datas["people_per_apartment"],
        "surface": 0,
        "surface_net": 0,
        "surface_habitable": 0,
        "surface_net_habitable": 0,
        "construction_cost": 0,
        "profondeur_fondation": 3,
    }
    actual_stage_logements = 0

    while True:
        total_area = calculate_total_area(
            datas["taille_moyenne"], current_building["nombre_logements"]
        )
        current_building["surface"] = total_area
        current_building["surface_net"] = round(
            total_area / current_building["nombre_etages"]
        )
        construction_cost = calculate_construction_cost(
            datas, total_area, current_building
        )
        current_building["construction_cost"] = construction_cost
        current_building["surface_habitable"] = total_area - (total_area * 0.1)
        current_building["surface_net_habitable"] = round(
            current_building["surface_habitable"] / current_building["nombre_etages"]
        )
        current_building["profondeur_fondation"] = current_building["nombre_etages"] + 1

        total_cost = sum(
            building["construction_cost"] for building in buildings + [current_building]
        )

        if total_cost >= datas["objectif"]:
            # Si on dépasse, on n'ajoute pas le dernier, sauf s'il n'y a aucun building encore
            if not buildings:
                buildings.append(current_building)
            break

        current_building["nombre_logements"] += 1
        actual_stage_logements += 1

        if actual_stage_logements >= datas["max_apartments"]:
            if current_building["nombre_etages"] < datas["max_etages"]:
                current_building["nombre_etages"] += 1
                actual_stage_logements = 0
            else:
                buildings.append(current_building)
                current_building = {
                    "nombre_etages": 1,
                    "nombre_logements": 1,
                    "people_per_apartment": datas["people_per_apartment"],
                    "surface": 0,
                    "surface_net": 0,
                    "surface_habitable": 0,
                    "surface_net_habitable": 0,
                    "construction_cost": 0,
                    "profondeur_fondation": 3,
                }

    return buildings, datas

async def send_building_summary(interaction, buildings: list, datas: dict):
    def convert(val):
        # Fonction de formatage monétaire, à adapter si besoin
        return f"{int(float(val)):,}".replace(",", " ")

    total_construction_cost = sum(b["construction_cost"] for b in buildings)
    total_logements = sum(b["nombre_logements"] for b in buildings)
    total_etages = sum(b["nombre_etages"] for b in buildings)
    total_habitants = sum(b["nombre_logements"] * b["people_per_apartment"] for b in buildings)
    total_surface = sum(b["surface"] for b in buildings)
    total_surface_net = sum(b["surface_net"] for b in buildings)
    total_surface_habitable = sum(b["surface_habitable"] for b in buildings)
    total_surface_net_habitable = sum(b["surface_net_habitable"] for b in buildings)

    answer = "\nBilan de la construction de l'immeuble:\n"
    for i, building in enumerate(buildings):
        logements_par_etage = building["nombre_logements"] // building["nombre_etages"]
        habitants_par_etage = logements_par_etage * building["people_per_apartment"]

        if len(answer) > 1800 and len(buildings) < 20:
            await interaction.followup.send(answer)
            answer = ""

        answer += (
            f"\n- Bâtiment {i + 1}:\n"
            f"  - Coût de construction: {convert(building['construction_cost'])} €\n"
            f"  - Nombre d'étages: {building['nombre_etages']}\n"
            f"  - Logements par étage: {logements_par_etage}\n"
            f"  - Habitants par étage: {habitants_par_etage}\n"
            f"  - Nombre total de logements: {building['nombre_logements']}\n"
            f"  - Nombre total d'habitants: {building['nombre_logements'] * building['people_per_apartment']}\n"
            f"  - Surface totale: {building['surface']} m²\n"
            f"  - Surface nette: {building['surface_net']} m²\n"
            f"  - Surface habitable: {building['surface_habitable']} m²\n"
            f"  - Surface nette habitable: {building['surface_net_habitable']} m²\n"
            f"  - Profondeur des fondations: {building['profondeur_fondation']} m\n"
        )

    if len(buildings) < 20:
        await interaction.followup.send(answer)
        answer = ""

    answer += (
        f"\n- **Bilan final:**\n"
        f"  - Coût total de construction: {convert(total_construction_cost)} €\n"
        f"  - Nombre total d'étages: {total_etages}\n"
        f"  - Nombre total de logements: {total_logements}\n"
        f"  - Nombre total d'habitants: {total_habitants}\n"
        f"  - Nombre moyen d'habitants par logement: {total_habitants / total_logements if total_logements else 0:.2f}\n"
        f"  - Surface totale brute: {total_surface} m²\n"
        f"  - Surface totale nette: {total_surface_net} m²\n"
        f"  - Surface totale habitable: {total_surface_habitable} m²\n"
        f"  - Surface totale nette habitable: {total_surface_net_habitable} m²\n"
        f"  - Moyenne du nombre d'étages par bâtiment: {total_etages / len(buildings) if buildings else 0:.2f}\n"
        f"  - Nombre total de bâtiments: {len(buildings)}\n"
        f"\n- Paramètres utilisés:\n"
        f"  - Taille moyenne des appartements: {datas['taille_moyenne']} m²\n"
        f"  - Prix moyen du mètre carré: {datas['prix_moyen']} €\n"
        f"  - Type de murs: {datas['type_murs']}\n"
        f"  - Nombre maximum d'étages: {datas['max_etages']}\n"
        f"  - Nombre maximum de logements par étage: {datas['max_apartments']}\n"
        f"  - Nombre moyen d'habitants par logement: {datas['people_per_apartment']}\n"
    )
    if datas["objectif_type"] == "habitants":
        answer += (
            f"  - Objectif de nombre d'habitants: {convert(datas['objectif'])}\n"
            f"  - Dépassement de l'objectif: {total_habitants - datas['objectif']} habitants\n"
        )
    else:
        answer += (
            f"  - Objectif de coût de construction: {convert(datas['objectif'])} €\n"
            f"  - Dépassement de l'objectif: {convert(total_construction_cost - datas['objectif'])} €\n"
        )

    if len(buildings) < 20:
        await interaction.followup.send(answer)
    else:
        with open("construction_immeuble.txt", "w", encoding="utf-8") as f:
            f.write(answer)
        await interaction.followup.send(file=discord.File("construction_immeuble.txt"))
        os.remove("construction_immeuble.txt")
