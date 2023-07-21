"""Handles validation and pre-processing of Smogon statistics."""

import ujson as json
import numpy as np
import re
import os

MIN_BATTLES = 500  # Throw out the whole thing if there aren't at least this many battles.
MIN_POKEMON = 20  # Needs to be at least this many Pokemon

# Thresholds to throw out a Pokemon.
MIN_POKE_RAW_COUNT = 100
MIN_TEAMMATES = 5
MIN_USAGE = 0.0015

# Need to be at least this many Pokemon with counters, or at least this proportion, in order for there to be counters data.
MIN_TO_HAVE_COUNTERS = 5  # How many values need to be in checks/counters data for a Pokemon to be considered have counters data.
MIN_COUNTERS_COUNT = 50
MIN_COUNTERS_FRAC = .1

SPEED_TIER_THRESHOLD = .005  # Throw out irrelevant speed tiers.
MIN_SUB_USAGE = .05  # Minimum usage for items/abilities/moves.
MAX_SUB_TO_KEEP = 10  # Most items/abilities/moves to keep per Pokemon, and Pokemon per move/item/ability.
DIGITS_KEPT = 3  # We round off numbers to shrink the files.


class ValidationError(Exception):
    """Used to indicate a file can't be used.
    This is not for malformed files, but for cases where there is insufficient data
    or there is something about the metagame that makes it unusuable.
    """
    pass


def raw_counters(json_file, raw_counters_file):
    """Pulls counters data out of a data file.

    We do this so that other ratings can share the counters data from the
    0 rating, since that rating has much more counters data.

    Note that we still need to build the counters matrices separately
    for each rating, since the indices of Pokemon will be different
    (as some are missing due to low usage in some ratings).

    Args:
        json_file: Path to data file from Smogon.
        raw_counters_file: Output file path - just the checks and counters data.
    """
    with open(json_file, "r", encoding="utf-8") as f:
        has_counters = 0
        pokemon = json.load(f)["data"]
        pokemon_counters = {}
        for poke in pokemon:
            pokemon_counters[poke] = pokemon[poke]["Checks and Counters"]
            if len(pokemon_counters[poke]) >= MIN_TO_HAVE_COUNTERS:
                has_counters += 1

    # Some formats are missing counters data.
    if has_counters > MIN_COUNTERS_COUNT or has_counters > MIN_COUNTERS_FRAC * len(pokemon):
        with open(raw_counters_file, "w", encoding="utf-8") as f:
            json.dump(pokemon_counters, f)


def prepare_files(json_file, raw_counters_file, threat_file, teammate_file):
    """Validate and pre-process files directly from Smogon.

    Removes Pokemon with extremely low usage.
    Removes Pokemon without counters data.
    Trims out counters data for Pokemon that are no longer included.
    Verifies that there is a reasonable number of Pokemon remaining.
    Builds a threat matrix and a teammate matrix.

    Args:
        json_file: Path to file containing raw version of
        Smogon's chaos json for a metagame. File will be overwritten.

        raw_counters_file: Path to file containing counters data for 0-rating version of metagame.
        If it doesn't exist, counter-based functionality will be disabled.

        threat_file: Path to save the numpy threat matrix to.
        threat_matrix[x, y] is how threatening the Pokemon with index
        y is to the Pokemon with index x.
        
        teammate_file: Path to save the numpy teammate matrix to.
        team_matrix[x, y] is how good a teammate the Pokemon with index
        y is to the Pokemon with index x.

    Raises:
        ValidationError: if the data is unusuable (for instance, if there are very few Pokemon).
        A message is included with details.

    Returns:
        str: name of metagame (e.g. gen8ou)
        int: number of battles in metagame (not filtered by rating)
        bool: whether the format has counters data
    """
    with open(json_file, "r", encoding="utf-8") as file:
        data = json.load(file)

    if data["info"]["number of battles"] < MIN_BATTLES:
        raise ValidationError("Not enough battles.")
    elif len(data["data"]) < MIN_POKEMON:
        raise ValidationError("Not enough Pokemon.")

    # Quick filter. We pop "data", since we rename that to "pokemon" in our output.
    pokemon = {name: info for (name, info) in data.pop("data").items()
               if info["usage"] > MIN_USAGE
               and len(info["Teammates"]) >= MIN_TEAMMATES
               and info["Raw count"] > MIN_POKE_RAW_COUNT}

    pokemon_to_remove = []
    while True:
        for poke in pokemon_to_remove:
            del pokemon[poke]
        pokemon_to_remove = []

        for poke in pokemon:
            pokemon[poke]["Teammates"] = {t: data for (t, data)
                                          in pokemon[poke]["Teammates"].items()
                                          if t in pokemon and data > 0}

            # Empty teammate lists create issues, so we have to remove that poke.
            # Then after that's gone, we need to go back and remove any references to it.
            if len(pokemon[poke]["Teammates"]) < MIN_TEAMMATES:
                pokemon_to_remove.append(poke)

        if len(pokemon) < MIN_POKEMON:
            raise ValidationError("Not enough Pokemon remaining after cleanup.")

        if not pokemon_to_remove:
            break

    indices = {}  # Build Pokemon name->number mapping.
    for index, poke in enumerate(pokemon):
        indices[poke] = index
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

    data["info"]["counters"] = os.path.isfile(raw_counters_file)  # Do we have counters data for this format?
    if data["info"]["counters"]:
        with open(raw_counters_file, "r", encoding="utf-8") as raw_c:
            raw_c_data = json.load(raw_c)
        threat_matrix = np.empty((len(pokemon), len(pokemon)), dtype=np.single)
        for index, poke in enumerate(pokemon):
            for column, c_poke in enumerate(pokemon):
                threat_matrix[index, column] = _threat_for_poke(pokemon, raw_c_data, c_poke, poke)

        with open(threat_file, "wb") as file:
            np.save(file, threat_matrix)

    team_matrix = np.empty((len(pokemon), len(pokemon)), dtype=np.single)
    for index, poke in enumerate(pokemon):
        for column, c_poke in enumerate(pokemon):
            if c_poke not in pokemon[poke]["Teammates"]:
                team_matrix[index, column] = 0
            else:
                # In the normal case, we use #times they both occur / (#times the first poke occurs - #times they both occur)
                # This has some good properties - if they never occur together, we get 0, and if they always occur together, we get infinity.
                # Unfortunately, if Pokemon can occur multiple times, the denominator can be negative,
                # so we add the number of times the teammate occurs with itself.
                c_and_c = pokemon[c_poke]["Teammates"][c_poke] if c_poke in pokemon[c_poke]["Teammates"] else 0
                num = pokemon[poke]["Teammates"][c_poke]
                denom = pokemon[poke]["count"] - num + c_and_c
                if denom <= 0:
                    team_matrix[index, column] = np.inf
                else:
                    # We also scale by usage. Pokemon with high usage would otherwise show up as teammates for everything,
                    # and the usage is already taken into account via the usage score.
                    team_matrix[index, column] = num / denom / pokemon[c_poke]["usage"]

    with open(teammate_file, "wb") as file:
        np.save(file, team_matrix)

    # Want to match gen1, gen8, gen10, etc. but not the extra digit in gen81v1.
    data["info"]["gen"] = re.match(r"^gen(\d+)(?!v\d)", data["info"]["metagame"]).group(1)

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


def _users(pokemon, key):
    """For each Pokemon, we strip low usage items/moves/abilities.
    For each item/move/ability, we create a list of the most common users of it.
    Most common is defined based on the total number of times that Pokemon with that move occurs.
    For instance, a Pokemon that uses something 100% of the time but only appears on .01% of teams will likely not appear.

    Args:
        pokemon: All of the Pokemon data.
        key (str): Sub-item type to process (items, moves, abilities).
    """
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
