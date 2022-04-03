"""Handles validation and pre-processing of Smogon statistics."""

import ujson as json
import numpy as np

COUNTER_COVERED_FACTOR = 1


def prepare_files(json_file, threat_file):
    """Validate and pre-process files directly from Smogon.

    Removes Pokemon with extremely low usage.
    Removes Pokemon without counters data.
    Trims out counters data for Pokemon that are no longer included.
    Verifies that there is a reasonable number of Pokemon remaining.
    Builds a threat matrix.

    Args:
        json_file (str): Path to file containing raw version of
        Smogon's chaos json for a metagame. File will be overwritten.

        threat_file (str): Path to save the numpy threat matrix to.
        File will be overwritten.
        threat_matrix[x, y] is how threatening the Pokemon with index
        y is to the Pokemon with index x.

    Returns:
        str: name of metagame (e.g. gen8ou)
        int: number of battles in metagame (not filtered by rating)
    """
    indices = {}
    with open(json_file, "r", encoding="utf-8") as file:
        data = json.load(file)
        pokemon = data["data"].items()
        changes = True
        while changes:
            num_pokes = len(pokemon)
            # First, get rid of any Pokemon without counters data.
            # Also trim out some Pokemon with extraordinarily low usage.
            pokemon = {name: info for (name, info) in data["data"].items()
                       if (len(info["Checks and Counters"]) > 9
                           and info["usage"] > 0.0015)}

            changes = num_pokes != len(pokemon)

            # Clear out checks/counters for pokemon we don't have.
            for poke in pokemon:
                pokemon[poke]["Checks and Counters"] = \
                    {c: data for (c, data)
                     in pokemon[poke]["Checks and Counters"].items()
                     if c in pokemon}

        assert len(pokemon) >= 20  # Not enough data to even try.
        for index, mon in enumerate(pokemon):
            indices[mon] = index
        data["indices"] = indices
        data["data"] = pokemon

        #  Calculate total number of Pokemon that appear.
        total = 0
        for poke in pokemon:
            total += sum(pokemon[poke]["Abilities"].values())

        data["total_pokes"] = total

    with open(json_file, "w", encoding="utf-8") as file:
        json.dump(data, file)

    with open(threat_file, "wb") as file:
        threat_matrix = np.empty((len(pokemon), len(pokemon)))
        for index, mon in enumerate(pokemon):
            for column, c_mon in enumerate(pokemon):
                threat_matrix[index, column] = \
                    _threat_for_poke(pokemon, c_mon, mon)

        np.save(file, threat_matrix)

    # Return a little info for the top format list.
    return data["info"]["metagame"], data["info"]["number of battles"]


def _threat_for_poke(pokemon, threat, poke):
    """Calculate how threatening threat is to poke.

    Args:
        pokemon (dict[str] -> dict): Data for all Pokemon in the format.
        threat (str): Name of Pokemon that is a threat.
        poke (str): Name of a Pokemon that is being threatened.

    Returns:
        float: How threatening threat is to poke.
        Higher values are more threatening. Ranges from neg->pos.

    """
    if poke not in pokemon[threat]["Checks and Counters"]:
        return 0

    weight = pokemon[threat]["usage"]
    strength = (pokemon[poke]["Checks and Counters"][threat][1]
                - pokemon[threat]["Checks and Counters"][poke][1])
    sum_wins = (pokemon[poke]["Checks and Counters"][threat][1]
                + pokemon[threat]["Checks and Counters"][poke][1])
    if sum_wins == 0:
        return 0
    strength /= sum_wins  # Scale so that we eliminate ties.
    if strength < 0:
        # Don't need one counter for every mon that's weak to something.
        strength *= COUNTER_COVERED_FACTOR
    return strength * weight
