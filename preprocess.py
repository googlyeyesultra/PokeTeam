"""Handles validation and pre-processing of Smogon statistics."""

import ujson as json
import numpy as np
import re

COUNTER_COVERED_FACTOR = 1
MIN_USAGE = 0.0015
MIN_BATTLES = 500
# TODO define min move/item usage, maybe digits to round


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

    counters = True
    if "doubles" in json_file.name or "vgc" in json_file.name:
        # Doubles formats don't have good checks/counters data,
        # but it's sometimes included in the raw data.
        counters = False

    indices = {}
    with open(json_file, "r", encoding="utf-8") as file:
        data = json.load(file)

        if data["info"]["number of battles"] < MIN_BATTLES:
            raise ValueError("Not enough battles.")

        pokemon = data.pop("data")

        pokemon = {name: info for (name, info) in pokemon.items()
                   if info["usage"] > MIN_USAGE
                   and len(info["Teammates"]) > 1
                   and info["Raw count"] > 100}

        has_counters_data = 0
        for poke in pokemon:
            pokemon[poke]["Teammates"] = {t: data for (t, data)
                                          in pokemon[poke]["Teammates"].items()
                                          if t in pokemon}

            if counters:
                pokemon[poke]["Checks and Counters"] = \
                    {c: data for (c, data)
                     in pokemon[poke]["Checks and Counters"].items()
                     if c in pokemon}
                if pokemon[poke]["Checks and Counters"]:
                    has_counters_data += 1

        if has_counters_data <= len(pokemon) / 2:
            counters = False
            
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
            pokemon[poke]["count"] = sum(pokemon[poke]["Abilities"].values())
            total_pokes += pokemon[poke]["count"]
            total_team_members += sum(pokemon[poke]["Teammates"].values())

        data["info"]["total_pokes"] = round(total_pokes, 3)
        data["info"]["pokes_per_team"] = round(total_team_members / total_pokes + 1, 3)
        data["info"]["num_teams"] = round(total_pokes / data["info"]["pokes_per_team"], 3)

        # Round values to reduce size of files.
        # Also convert to percentages.
        for poke in pokemon:
            pokemon[poke]["usage"] = round(pokemon[poke]["usage"], 3)
            pokemon[poke]["Moves"] = \
                {m: round(data/pokemon[poke]["count"], 3) for (m, data)
                 in pokemon[poke]["Moves"].items()}
            pokemon[poke]["Abilities"] = \
                {a: round(data/pokemon[poke]["count"], 3) for (a, data)
                 in pokemon[poke]["Abilities"].items()}
            pokemon[poke]["Items"] = \
                {i: round(data/pokemon[poke]["count"], 3) for (i, data)
                 in pokemon[poke]["Items"].items()}

        total_pairs = 0
        for poke in pokemon:
            # Divide by 2 - otherwise we count (A, B) and (B, A).
            total_pairs += sum(pokemon[poke]["Teammates"].values()) / 2

        data["info"]["total_pairs"] = round(total_pairs, 3)

    if counters:
        threat_matrix = np.empty((len(pokemon), len(pokemon)), dtype=np.single)
        for index, mon in enumerate(pokemon):
            for column, c_mon in enumerate(pokemon):
                threat_matrix[index, column] = \
                    _threat_for_poke(pokemon, c_mon, mon)

        with open(threat_file, "wb") as file:
            np.save(file, threat_matrix)

    # team score for X given Y is TODO
    # If X never appears with Y, needs to be 0.
    # If X appears on every team with Y, needs to be huge.
    # P(X|Y): 1 if x appears on every team with Y. Maybe divide by 1-P(X|Y)? Except it's per slot, so it won't be 1. 0 if never appears with Y.
    # P(Y|X): Not obviously useful?
    # P(X|not Y):
    # P(Y|not X):
    team_matrix = np.empty((len(pokemon), len(pokemon)), dtype=np.single)
    for index, mon in enumerate(pokemon):
        for column, c_mon in enumerate(pokemon):
            denom = _p_x_given_not_y(pokemon, c_mon, mon, data["info"]["total_pairs"])
            num = _p_x_given_y(pokemon, c_mon, mon)
            if num == 0:
                team_matrix[index, column] = 0
            elif denom == 0:
                team_matrix[index, column] = np.inf
            else:
                team_matrix[index, column] = num / denom

    with open(teammate_file, "wb") as file:
        np.save(file, team_matrix)

    # Clear the raw data since we only need the matrices.
    for poke in pokemon:
        del pokemon[poke]["Checks and Counters"]
        del pokemon[poke]["Teammates"]
        del pokemon[poke]["Happiness"]
        del pokemon[poke]["Spreads"]
        del pokemon[poke]["Viability Ceiling"]
        del pokemon[poke]["Raw count"]

    del data["info"]["cutoff"]
    del data["info"]["cutoff deviation"]
    del data["info"]["team type"]

    data["pokemon"] = pokemon

    abils = {}
    for poke in pokemon:
        sorted_abils = sorted(pokemon[poke]["Abilities"].items(), key=lambda i: -i[1])[:10]
        pokemon[poke]["Abilities"] = dict([a for a in sorted_abils if a[1] > .05])
        usage = pokemon[poke]["usage"]
        for k in pokemon[poke]["Abilities"]:
            use = pokemon[poke]["Abilities"][k]
            entry = (poke, round(usage * use, 3), use, usage)
            if k in abils:
                abils[k].append(entry)
            else:
                abils[k] = [entry]

    for abil in abils:
        abils[abil] = sorted(abils[abil], key=lambda t: -t[1])[:10]
    data["abilities"] = dict(sorted(abils.items()))

    moves = {}
    for poke in pokemon:
        sorted_moves = sorted(pokemon[poke]["Moves"].items(), key=lambda i: -i[1])[:10]
        pokemon[poke]["Moves"] = dict([m for m in sorted_moves if m[1] > .05])
        usage = pokemon[poke]["usage"]
        for k in pokemon[poke]["Moves"]:
            use = pokemon[poke]["Moves"][k]
            entry = (poke, round(usage * use, 3), use, usage)
            if k in moves:
                moves[k].append(entry)
            else:
                moves[k] = [entry]

    for move in moves:
        moves[move] = sorted(moves[move], key=lambda t: -t[1])[:10]
    data["moves"] = dict(sorted(moves.items()))

    items = {}
    for poke in pokemon:
        sorted_items = sorted(pokemon[poke]["Items"].items(), key=lambda i: -i[1])[:10]
        pokemon[poke]["Items"] = dict([i for i in sorted_items if i[1] > .05])
        usage = pokemon[poke]["usage"]
        for k in pokemon[poke]["Items"]:
            use = pokemon[poke]["Items"][k]
            entry = (poke, round(usage * use, 3), use, usage)
            if k in items:
                items[k].append(entry)
            else:
                items[k] = [entry]

    for item in items:
        items[item] = sorted(items[item], key=lambda t: -t[1])[:10]
    data["items"] = dict(sorted(items.items()))

    # Want to match gen1, gen8, gen10, but not the extra digit in gen81v1.
    # Supports through gen 19.
    data["info"]["gen"] = re.match("^gen(1?[0-9]?)", data["info"]["metagame"]).group(1)

    with open(json_file, "w", encoding="utf-8") as file:
        json.dump(data, file)

    # Return a little info for the top format list.
    return data["info"]["metagame"], data["info"]["number of battles"], data["info"]["counters"]


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
        x (str): Nam^gen(1?[0-9]?)e of a Pokemon.

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
