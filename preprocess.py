"""Handles validation and pre-processing of Smogon statistics."""

import ujson as json
import numpy as np
import math

COUNTER_COVERED_FACTOR = 1
MIN_USAGE = 0.0015


def prepare_files(json_file, threat_file, teammate_file):
    """Validate and pre-process files directly from Smogon.

    Removes Pokemon with extremely low usage.
    Removes Pokemon without counters data.
    Trims out counters data for Pokemon that are no longer included.
    Verifies that there is a reasonable number of Pokemon remaining.
    Builds a threat matrix and a teammate matrix.

    Args:
        json_file (str): Path to file containing raw version of
        Smogon's chaos json for a metagame. File will be overwritten.

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
                           and info["usage"] > MIN_USAGE)}

            changes = num_pokes != len(pokemon)

            # Clear out checks/counters for Pokemon we don't have.
            for poke in pokemon:
                pokemon[poke]["Checks and Counters"] = \
                    {c: data for (c, data)
                     in pokemon[poke]["Checks and Counters"].items()
                     if c in pokemon}

        # Not enough data to even try.
        assert len(pokemon) >= 20, "Not enough Pokemon remaining after cleanup."
        for index, mon in enumerate(pokemon):
            indices[mon] = index
        data["indices"] = indices
        data["data"] = pokemon

        # Calculate average pokemon per team. Typically a little less than 6.
        # Smaller in some formats like 1v1.
        # Can't just use number of battles since that isn't weighted by rating.
        total_pokes = 0
        total_team_members = 0
        for poke in pokemon:
            total_pokes += sum(pokemon[poke]["Abilities"].values())
            total_team_members += sum(pokemon[poke]["Teammates"].values())

        data["total_pokes"] = total_pokes
        data["pokes_per_team"] = total_team_members / total_pokes + 1
        data["num_teams"] = total_pokes / data["pokes_per_team"]

        total_pairs = 0
        for poke in pokemon:
            # Divide by 2 - otherwise we count (A, B) and (B, A).
            total_pairs += sum(pokemon[poke]["Teammates"].values()) / 2

        data["total_pairs"] = total_pairs

    threat_matrix = np.empty((len(pokemon), len(pokemon)))
    for index, mon in enumerate(pokemon):
        for column, c_mon in enumerate(pokemon):
            threat_matrix[index, column] = \
                _threat_for_poke(pokemon, c_mon, mon)

    with open(threat_file, "wb") as file:
        np.save(file, threat_matrix)

    total_pairs = 0
    for mon in pokemon:
        total_pairs += sum(pokemon[mon]["Teammates"].values())  # TODO if we save this sum we can speed up some other operations

    # team score for X given Y is TODO
    # If X never appears with Y, needs to be 0.
    # If X appears on every team with Y, needs to be huge.
    # P(X|Y): 1 if x appears on every team with Y. Maybe divide by 1-P(X|Y)? Except it's per slot, so it won't be 1. 0 if never appears with Y.
    # P(Y|X): Not obviously useful?
    # P(X|not Y):
    # P(Y|not X):
    team_matrix = np.empty((len(pokemon), len(pokemon)))
    for index, mon in enumerate(pokemon):
        for column, c_mon in enumerate(pokemon):
            denom = _p_x_given_not_y(pokemon, c_mon, mon, total_pairs)
            if denom == 0:
                team_matrix[index, column] = math.inf
            else:
                team_matrix[index, column] = _p_x_given_y(pokemon, c_mon, mon) / denom

    with open(teammate_file, "wb") as file:
        np.save(file, team_matrix)

    # Clear the raw data since we only need the matrices.
    for poke in pokemon:
        del pokemon[poke]["Checks and Counters"]
        # del pokemon[poke]["Teammates"]  # Corefinder still uses this data.

    with open(json_file, "w", encoding="utf-8") as file:
        json.dump(data, file)

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


def _p_x_given_y(pokemon, x, y):
    """Calculate probability that x appears in a slot if y is on team.

    Args:
        x (str): Name of a Pokemon.

        y (str): Name of a Pokemon.

    Returns:
        float [0, 1]: Probability(x is in a slot|y is on that team)
    """
    if y not in pokemon[x]["Teammates"]:
        return 0  # Never appear together.

    return pokemon[x]["Teammates"][y] / sum(pokemon[y]["Teammates"].values())


def _p_x_given_not_y(pokemon, x, y, total_pairs):  # TODO try using this other ways. What about dividing by opposite direction? p(y|not x)?
    """Calculate probability that x appears on a slot if y does not.

    Args:
        x (str): Name of a Pokemon.

        y (str): Name of a Pokemon.

    Returns:
        float [0, 1]: Probability(x is on a team|y is not on that team)
    """

    if y not in pokemon[x]["Teammates"]:
        # Never appear together, so P(x|not y) = p(x)
        return sum(pokemon[x]["Teammates"].values()) / total_pairs

    # P(x|not y) = P(x and not y) / P(not y)
    # (x - (x U y)) is count of times x appeared without y
    count_x_and_not_y = sum(pokemon[x]["Teammates"].values()) - pokemon[x]["Teammates"][y]
    count_not_y = total_pairs - sum(pokemon[y]["Teammates"].values())
    return count_x_and_not_y / count_not_y
