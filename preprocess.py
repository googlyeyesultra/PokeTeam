"""Handles validation and pre-processing of Smogon statistics."""

import ujson as json
import numpy as np
import re
import os

MIN_USAGE = 0.0015
MIN_BATTLES = 500
SPEED_TIER_THRESHOLD = .005
MIN_SUB_USAGE = .05  # Minimum usage for items/abilities/moves.
MAX_SUB_TO_KEEP = 10  # Most items/abilities/moves to keep per Pokemon, and Pokemon per move/item/ability.
DIGITS_KEPT = 3

# TODO json dump file options everywhere in this file (raise if nan, force utf-8)

# TODO check if no counters data, if so don't write file
def raw_counters(json_file, raw_counters_file):
    if "doubles" in json_file.name or "vgc" in json_file.name:
        # Doubles formats don't have good checks/counters data,
        # but it's sometimes included in the raw data.
        return

    with open(json_file, "r", encoding="utf-8") as f:
        data = json.load(f)["data"]
        pokemon_counters = {}
        for poke in data:
            pokemon_counters[poke] = data[poke]["Checks and Counters"]

    with open(raw_counters_file, "w", encoding="utf-8") as f:
        json.dump(pokemon_counters, f)


# TODO args may not be str?
def prepare_files(json_file, raw_counters_file, threat_file, teammate_file):
    """Validate and pre-process files directly from Smogon.

    Removes Pokemon with extremely low usage.
    Removes Pokemon without counters data.
    Trims out counters data for Pokemon that are no longer included.
    Verifies that there is a reasonable number of Pokemon remaining.
    Builds a threat matrix and a teammate matrix.

    Args:
        json_file (str): Path to file containing raw version of
        Smogon's chaos json for a metagame. File will be overwritten.

        raw_counters_file (str): Path to file containing counters data for 0-rating version of metagame.

        threat_file (str): Path to save the numpy threat matrix to.
        File will be overwritten.
        threat_matrix[x, y] is how threatening the Pokemon with index
        y is to the Pokemon with index x.
        
        teammate_file (str): Path to save the numpy teammate matrix to.
        File will be overwritten.
        team_matrix[x, y] is how good a teammate the Pokemon with index
        y is to the Pokemon with index x.

    Returns:
        str: name of metagame (e.g. gen8ou)
        int: number of battles in metagame (not filtered by rating)
    """

    counters = os.path.isfile(raw_counters_file)

    indices = {}
    with open(json_file, "r", encoding="utf-8") as file:
        data = json.load(file)

        if data["info"]["number of battles"] < MIN_BATTLES:
            raise ValueError("Not enough battles.")

        pokemon = {name: info for (name, info) in data.pop("data").items()
                   if info["usage"] > MIN_USAGE
                   and len(info["Teammates"]) > 1
                   and info["Raw count"] > 100}

        pokemon_to_remove = []
        while True:
            for poke in pokemon_to_remove:
                del pokemon[poke]
            pokemon_to_remove = []

            for poke in pokemon:
                pokemon[poke]["Teammates"] = {t: data for (t, data)
                                              in pokemon[poke]["Teammates"].items()
                                              if t in pokemon}

                # Empty teammate lists create issues, so we have to remove that mon.
                # Then after that's gone, we need to go back and remove any references to it.
                if len(pokemon[poke]["Teammates"]) < 5 or sum(pokemon[poke]["Teammates"].values()) == 0:
                    pokemon_to_remove.append(poke)

            if not pokemon_to_remove:
                break
            
        data["info"]["counters"] = counters

        if len(pokemon) < 20:
            raise ValueError("Not enough Pokemon remaining after cleanup.")

        for index, mon in enumerate(pokemon):
            indices[mon] = index
        data["indices"] = indices

        # Fix no move being an empty string.
        for poke in pokemon:
            if "" in pokemon[poke]["Moves"]:
                pokemon[poke]["Moves"]["nomove"] = pokemon[poke]["Moves"].pop("")

        # Calculate average pokemon per team. Typically a little less than 6.
        # Smaller in some formats like 1v1.
        # Can't just use number of battles since that isn't weighted by rating.
        total_pokes = 0
        total_team_members = 0
        for poke in pokemon:
            pokemon[poke]["count"] = sum(pokemon[poke]["Abilities"].values())  # Leave this unrounded to avoid div by 0.
            total_pokes += pokemon[poke]["count"]
            total_team_members += sum(pokemon[poke]["Teammates"].values())

        data["info"]["total_pokes"] = round(total_pokes, DIGITS_KEPT)
        data["info"]["pokes_per_team"] = round(total_team_members / total_pokes + 1, DIGITS_KEPT)
        data["info"]["num_teams"] = round(total_pokes / data["info"]["pokes_per_team"], DIGITS_KEPT)

        # Round values to reduce size of files.
        # Also convert to percentages.
        for poke in pokemon:
            pokemon[poke]["usage"] = round(pokemon[poke]["usage"], DIGITS_KEPT)
            pokemon[poke]["Moves"] = \
                {m: round(data/pokemon[poke]["count"], DIGITS_KEPT) for (m, data)
                 in pokemon[poke]["Moves"].items()}
            pokemon[poke]["Abilities"] = \
                {a: round(data/pokemon[poke]["count"], DIGITS_KEPT) for (a, data)
                 in pokemon[poke]["Abilities"].items()}
            pokemon[poke]["Items"] = \
                {i: round(data/pokemon[poke]["count"], DIGITS_KEPT) for (i, data)
                 in pokemon[poke]["Items"].items()}

    if counters:
        with open(raw_counters_file, "r", encoding="utf-8") as raw_c:
            raw_c_data = json.load(raw_c)
            threat_matrix = np.empty((len(pokemon), len(pokemon)), dtype=np.single)
            for index, mon in enumerate(pokemon):
                for column, c_mon in enumerate(pokemon):
                    threat_matrix[index, column] = \
                        _threat_for_poke(pokemon, raw_c_data, c_mon, mon)

        with open(threat_file, "wb") as file:
            np.save(file, threat_matrix)

    team_matrix = np.empty((len(pokemon), len(pokemon)), dtype=np.single)
    for index, mon in enumerate(pokemon):
        for column, c_mon in enumerate(pokemon):
            if c_mon not in pokemon[mon]["Teammates"]:
                team_matrix[index, column] = 0
            else:
                cAndC = pokemon[c_mon]["Teammates"][c_mon] if c_mon in pokemon[c_mon]["Teammates"] else 0
                num = pokemon[mon]["Teammates"][c_mon]
                denom = pokemon[mon]["count"] - num + cAndC
                if denom <= 0:
                    team_matrix[index, column] = np.inf
                else:
                    team_matrix[index, column] = num / denom / pokemon[c_mon]["usage"]

    with open(teammate_file, "wb") as file:
        np.save(file, team_matrix)

    # Want to match gen1, gen8, gen10, but not the extra digit in gen81v1.
    data["info"]["gen"] = re.match("^gen(\d+)(?!v\d)", data["info"]["metagame"]).group(1)

    # Clear the raw data since we only need the matrices.
    for poke in pokemon:
        del pokemon[poke]["Checks and Counters"]
        del pokemon[poke]["Teammates"]
        del pokemon[poke]["Happiness"]
        del pokemon[poke]["Viability Ceiling"]
        del pokemon[poke]["Raw count"]

    del data["info"]["cutoff"]
    del data["info"]["cutoff deviation"]
    del data["info"]["team type"]

    data["pokemon"] = pokemon
    data["abilities"] = _users(pokemon, "Abilities")
    data["moves"] = _users(pokemon, "Moves")
    data["items"] = _users(pokemon, "Items")

    if ("vgc" in data["info"]["metagame"] or
        "battlestadium" in data["info"]["metagame"] or
        "nintendocup1997" in data["info"]["metagame"]):  # Technically this is a weird variable level format.
        data["info"]["level"] = 50
    elif data["info"]["metagame"].endswith("lc"):
        data["info"]["level"] = 5
    else:
        data["info"]["level"] = 100

    with open(json_file, "w", encoding="utf-8") as file:
        json.dump(data, file)

    # Return a little info for the top format list.
    return data["info"]["metagame"], data["info"]["number of battles"], data["info"]["counters"]


def _users(pokemon, key):  # Creates data for how often a move/ability/item is used by different Pokemon. Also strips low usage things.
    items = {}
    for poke in pokemon:
        sorted_items = sorted(pokemon[poke][key].items(), key=lambda i: -i[1])[:MAX_SUB_TO_KEEP]
        pokemon[poke][key] = dict([i for i in sorted_items if i[1] > MIN_SUB_USAGE])
        usage = pokemon[poke]["usage"]
        for k in pokemon[poke][key]:
            use = pokemon[poke][key][k]
            entry = (poke, round(usage * use, DIGITS_KEPT), use, usage)
            if k in items:
                items[k].append(entry)
            else:
                items[k] = [entry]

    for item in items:
        items[item] = sorted(items[item], key=lambda t: -t[1])[:MAX_SUB_TO_KEEP]

    return dict(sorted(items.items()))


def _threat_for_poke(pokemon, counters_data, threat, poke):
    """Calculate how threatening threat is to poke.

    Args:
        pokemon (dict[str] -> dict): Data for all Pokemon in the format.
        counters_data (dict[str] -> dict): Counters from 0 rating for all Pokemon in the format.
        threat (str): Name of Pokemon that is a threat.
        poke (str): Name of a Pokemon that is being threatened.

    Returns:
        float: How threatening threat is to poke.
        Higher values are more threatening. Ranges from neg->pos.

    """

    if poke not in counters_data[threat]:
        return 0

    weight = pokemon[threat]["usage"]
    strength = (counters_data[poke][threat][1]
                - counters_data[threat][poke][1])

    return strength * weight
