from math import floor
from file_constants import *
import ujson as json
from collections import Counter
import os

SPEED_TIER_THRESHOLD = .01


def build_speed_tiers():
    for file in os.scandir(TEMP_DATA_DIR):
        if file.name[-5:] == ".json":
            with open(file, "r", encoding="utf-8") as f:
                data = json.load(f)
                pokemon = data["pokemon"]
                gen = data["info"]["gen"]
                level = data["info"]["level"]
                speed_tiers = {}
                with open(TEMP_DATA_DIR + DEX_PREFIX + str(gen) + DEX_SUFFIX, "r", encoding="utf-8") as dex_f:
                    dex = json.load(dex_f)

                    for poke in pokemon:
                        if pokemon[poke]["usage"] < SPEED_TIER_THRESHOLD:
                            del pokemon[poke]["Spreads"]
                            continue

                        speeds = Counter()
                        base = dex["pokemon"][poke]["base_stats"]["Speed"]
                        for spread in pokemon[poke]["Spreads"]:
                            nature = spread.split(":")[0]
                            ev = int(spread.split("/")[-1])
                            speed = calc_speed(base, ev, nature, level, gen)
                            speeds[speed] += pokemon[poke]["Spreads"][spread] / pokemon[poke]["count"]

                        for speed in speeds:
                            if speeds[speed] * pokemon[poke]["usage"] > SPEED_TIER_THRESHOLD:
                                if speed not in speed_tiers:
                                    speed_tiers[speed] = []
                                speed_tiers[speed].append((poke, round(speeds[speed], 2), speeds[speed] * pokemon[poke]["usage"]))

                        del pokemon[poke]["Spreads"]

                for speed_tier in speed_tiers:
                    # List most relevant first.
                    speed_tiers[speed_tier] = [(s[0], s[1]) for s in sorted(speed_tiers[speed_tier], key=lambda k: -k[2])]

                speed_tiers = {k: speed_tiers[k] for k in sorted(speed_tiers, reverse=True)}
                if int(gen) <= 2:
                    multipliers = [1/2, 33/50, 1, 3/2, 2]
                else:
                    multipliers = [1/2, 2/3, 1, 3/2, 2]

                modified_speed_tiers = {}
                for index, mult in enumerate(multipliers):
                    for speed in speed_tiers:
                        new_speed = floor(speed*mult)
                        if new_speed in modified_speed_tiers:
                            modified_speed_tiers[new_speed][index] = speed_tiers[speed]
                        else:
                            modified_speed_tiers[new_speed] = [[]] * len(multipliers)
                            modified_speed_tiers[new_speed][index] = speed_tiers[speed]

                data["speed_tiers"] = {k: modified_speed_tiers[k] for k in sorted(modified_speed_tiers, reverse=True)}

            with open(file, "w", encoding="utf-8") as f:
                json.dump(data, f)


def calc_speed(base, ev, nature, level, gen):
    if int(gen) <= 2:
        return floor(((base + 15) * 2 + 63) * level / 100) + 5

    iv = 31
    if nature in ["Timid", "Hasty", "Jolly", "Naive"]:
        mult = 1.1
    elif nature in ["Brave", "Relaxed", "Quiet", "Sassy"]:
        mult = .9
        if ev == 0:
            iv = 0  # If negative nature and 0 speed investment, assume min speed for trick room, gyro ball, etc.
    else:
        mult = 1

    return floor((floor((2*base + iv + floor(ev/4)) * level / 100) + 5) * mult)
