""" Retrieves dex data (item/move/Pokemon data) for a given generation.
"""

import ujson as json


class Dex:
    def __init__(self, dex_file):
        """Load dex data from file.

        Args:
            dex_file (str):
                Path to file containing dex data.
        """
        with open(dex_file, "r", encoding="utf-8") as file:
            self.data = json.load(file)

    def __getitem__(self, item):
        return self.data[item]
