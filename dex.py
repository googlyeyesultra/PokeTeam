"""Retrieves dex data (item/move/Pokemon data) for a given generation.
This includes base stats, descriptions, typing, and more.
This does not include data that can depend on the metagame, such as what abilities or moves a Pokemon uses.
"""
import ujson as json


class Dex:
    """Access to Pokedex data.
    Initialize with a dex file, and then access like:
    dex.pokemon["Machamp"] or dex.items["Choice Scarf"]
    """
    def __init__(self, dex_file):
        """Load dex data from file.

        Args:
            dex_file (str): Path to file containing dex data.
        """
        with open(dex_file, "r", encoding="utf-8") as file:
            self.data = json.load(file)

    def __getattr__(self, item):  # Allows for dex.pokemon["Machamp"] instead of dex["pokemon"]["Machamp"]
        return self.data[item]
