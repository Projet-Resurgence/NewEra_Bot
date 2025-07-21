"""
Text formatting utilities for NEBot.
Contains functions for converting country names.
"""
import string

car_sal1 = list("ABCDEFGHIJKLMNOPQRSTUVWXYZ")
car_sal2 = ["𝐀", "𝐁", "𝐂", "𝐃", "𝐄", "𝐅", "𝐆", "𝐇", "𝐈", "𝐉", "𝐊", "𝐋", "𝐌", "𝐍", "𝐎", "𝐏", "𝐐", "𝐑", "𝐒", "𝐓", "𝐔", "𝐕", "𝐖", "𝐗", "𝐘", "𝐙"]
accents = ["é", "è", "ê", "ë", "à", "â", "ä", "ô", "ö", "ù", "û", "ü", "î", "ï", "ç"]

def convert_country_name(old_name: str) -> str:
    new_name = ""
    for i in str(old_name):
        if i.isupper():
            new_name += car_sal2[car_sal1.index(i)]
        else:
            new_name += i
    return new_name

def convert_country_name_channel(old_name: str) -> str:
    new_name = ""
    car_space = {
        "good": ["「", "」"],
        "bad": ["《", "》"]
    }
    for i in range(len(old_name)):
        if i == 0:
            new_name += old_name[i]
        elif (old_name[i-1] not in string.ascii_letters) and (old_name[i-1] in car_sal2) and (old_name[i] in string.ascii_letters) and (old_name[i-1] not in accents) and (old_name[i] not in car_sal2):
            new_name += car_sal2[car_sal1.index(old_name[i].upper())]
        else:
            new_name += old_name[i]
    new_name = new_name.replace(car_space["bad"][0], car_space["good"][0])
    new_name = new_name.replace(car_space["bad"][1], car_space["good"][1])
    return new_name

def parse_mentions(message:str):
    """
        Parse a message to extract mentions in the format "Name (ID)".
        The function looks for the keyword "Mention : " in the message and extracts
        all mentions that follow it. Each mention is expected to be in the format
        "Name (ID)" and separated by a pipe "|" character.
        Args:
            message (str): The input message containing mentions.
        Returns:
            dict: A dictionary where the keys are the names and the values are the IDs
                  of the mentions. If no mentions are found, an empty dictionary is returned.
        Example:
            message = "Some text before Mention : John Doe (123) | Jane Smith (456)"
            result = parse_mentions(message)
            # result will be {'John Doe': '123', 'Jane Smith': '456'}
        """
    # Séparer sur "Mention : " et ignorer la partie avant la première occurrence
    parts = message.split("Mention : ", 1)
    if len(parts) < 2:
        return {}  # Si aucun "Mention : ", renvoyer un dictionnaire vide

    mentions_part = parts[1]  # Obtenir la partie après "Mention : "
    
    # Séparer les mentions individuelles
    mentions_list = mentions_part.split("|")

    mentions_dict = {}
    for mention in mentions_list:
        try:
            name, id_part = mention.split("(")
            id_value = id_part.replace(")", "").strip()
            mentions_dict[name.strip()] = id_value
        except ValueError:
            # Si la structure est incorrecte (pas de parenthèses), ignorer la mention
            continue

    return mentions_dict
