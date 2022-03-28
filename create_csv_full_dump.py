from main import get_md
import csv
import os
md = get_md("gen8ou-1500")

folder = "./dump/"

for file in os.scandir(folder):
    os.remove(file)


def a_beats_b(a, b):
    if a not in md.pokemon[b]["Checks and Counters"]:
        return ""
    return md.pokemon[b]["Checks and Counters"][a][1]


def b_beats_a(a, b):
    if a not in md.pokemon[b]["Checks and Counters"]:
        return ""
    return md.pokemon[a]["Checks and Counters"][b][1]


def std_dev_a_beats_b(a, b):
    if a not in md.pokemon[b]["Checks and Counters"]:
        return ""
    return md.pokemon[b]["Checks and Counters"][a][2]


def std_dev_b_beats_a(a, b):
    if a not in md.pokemon[b]["Checks and Counters"]:
        return ""
    return md.pokemon[a]["Checks and Counters"][b][2]


def neither_wins(a, b):
    if a not in md.pokemon[b]["Checks and Counters"]:
        return ""
    return 1 - a_beats_b(a, b) - b_beats_a(a, b)


def matchup_count(a, b):
    if a not in md.pokemon[b]["Checks and Counters"]:
        return ""
    return md.pokemon[a]["Checks and Counters"][b][0]


pairwise_funcs = [a_beats_b, b_beats_a, std_dev_a_beats_b,
                  std_dev_b_beats_a, neither_wins, matchup_count]

poke_list = list(md.pokemon.keys())

with open(folder + "pivot_table.csv", 'w', newline='') as csvfile:
    writer = csv.writer(csvfile, delimiter=',', quotechar='"',
                        quoting=csv.QUOTE_MINIMAL)
    writer.writerow(["a", "b"] + [x.__name__ for x in pairwise_funcs])
    for a in poke_list:
        for b in poke_list:
            row_data = [a, b]
            for func in pairwise_funcs:
                row_data.append(func(a, b))
            writer.writerow(row_data)


def usage(a):
    return md.pokemon[a]["usage"]


def offense_evs(a):
    offense = 0
    for spread, spread_weight in md.pokemon[a]["Spreads"].items():
        spread_list = [float(x) for x in spread.split(":")[1].split("/")]
        offense += (spread_list[1] + spread_list[3]) * \
            spread_weight / md.count_pokemon(a)

    return offense


def defense_evs(a):
    defense = 0
    for spread, spread_weight in md.pokemon[a]["Spreads"].items():
        spread_list = [float(x) for x in spread.split(":")[1].split("/")]
        defense += ((spread_list[0] + spread_list[2] + spread_list[4])
                    * spread_weight / md.count_pokemon(a))
    return defense


def avg_switchins_per_battle(a):
    battles_in = md.pokemon[a]["usage"] * md.num_battles # TODO not certain about this
    total_switchins = 0
    for b in md.pokemon[a]["Checks and Counters"]:
        total_switchins += md.pokemon[a]["Checks and Counters"][b][0]

    return total_switchins / battles_in


indiv_funcs = [usage, avg_switchins_per_battle, offense_evs, defense_evs]

with open(folder + "indiv_data.csv", 'w', newline='') as csvfile:
    writer = csv.writer(csvfile, delimiter=',',
                        quotechar='"', quoting=csv.QUOTE_MINIMAL)
    writer.writerow(["Pokemon"] + [x.__name__ for x in indiv_funcs])
    for func in indiv_funcs:
        for a in poke_list:
            row_data = [a] + [x(a) for x in indiv_funcs]
            writer.writerow(row_data)


def num_battles():
    return md.num_battles


metagame_funcs = [num_battles]

with open(folder + "metagame_data.csv", 'w', newline='') as csvfile:
    writer = csv.writer(csvfile, delimiter=',', quotechar='"',
                        quoting=csv.QUOTE_MINIMAL)
    writer.writerow([x.__name__ for x in metagame_funcs])
    writer.writerow([x() for x in metagame_funcs])
