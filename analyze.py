import ujson as json
import numpy as np
import math

usage_weight_default = 2
counters_weight_default = 2
team_weight_default = 5

counter_covered_factor = 1

class MetagameData:
  def __init__(self, json_file, threat_file):
    with open(json_file, "r") as file:
        data = json.load(file)
        self.pokemon = data["data"]
        self.num_battles = data["info"]["number of battles"]
        self.indices = data["indices"]
    with open(threat_file, "rb") as file:
      self.threat_matrix = np.load(file)

  @staticmethod
  def prepare_files(json_file, threat_file):
    data = None
    pokemon = None
    indices = {}
    with open(json_file, "r") as file:
        data = json.load(file)
        pokemon = data["data"].items()
        changes = True
        while changes:
          num_pokes = len(pokemon)
          # First, we need to get rid of any pokemon that don't have checks/counters data.
          # Also trim out some pokemon with extraordinarily low usage.
          pokemon = {name: info for (name, info) in data["data"].items() if len(info["Checks and Counters"]) > 9 and info["usage"] > 0.0015}
          
          changes = num_pokes != len(pokemon)

          # Clear out checks/counters for pokemon we don't have.
          for poke in pokemon:
              pokemon[poke]["Checks and Counters"] = {c: data for (c, data) in pokemon[poke]["Checks and Counters"].items() if c in pokemon}

        assert len(pokemon) >= 20  # Not enough data to even try.
        for index, mon in enumerate(pokemon):
          indices[mon] = index
        data["indices"] = indices
        data["data"] = pokemon
    with open(json_file, "w") as file:
        json.dump(data, file)

    with open(threat_file, "wb") as file:
      threat_matrix = np.empty((len(pokemon), len(pokemon)))
      for index, mon in enumerate(pokemon):
        for column, c_mon in enumerate(pokemon):
          threat_matrix[index, column] = MetagameData.threat_for_poke(pokemon, c_mon, mon)
      
      np.save(file, threat_matrix)

    return (data["info"]["metagame"], data["info"]["number of battles"]) # Return a little info for the top format list.

  @staticmethod
  def threat_for_poke(pokemon, threat, poke):
    if poke in pokemon[threat]["Checks and Counters"]:
      weight = pokemon[threat]["usage"]
      strength = (pokemon[poke]["Checks and Counters"][threat][1] - pokemon[threat]["Checks and Counters"][poke][1])
      sum_wins = pokemon[poke]["Checks and Counters"][threat][1] + pokemon[threat]["Checks and Counters"][poke][1]
      if sum_wins == 0:
        return 0
      strength /= sum_wins # Scale so that we eliminate ties.
      if strength < 0:
        strength *= counter_covered_factor  # We don't really need one counter for every mon that's weak to something.
      return strength * weight
    else:
      return 0

  def find_threats(self, team):
    team_indices = [self.indices[t] for t in team]
    summed = self.threat_matrix[team_indices].sum(0)

    return summed

  def get_counter_score(self, threats, team_size, poke):
    new_threats = threats + self.threat_matrix[self.indices[poke]]
    return 100 ** (-(new_threats[new_threats > 0].sum() / (team_size + 1)))

  def count_pokemon(self, poke):
    return sum(self.pokemon[poke]["Abilities"].values())

  def p_x_given_y(self, x, y):
    if y in self.pokemon[x]["Teammates"]:
      return self.pokemon[x]["Teammates"][y] / self.count_pokemon(y)
    else:
      return 0 # Never appear together

  def p_x_given_not_y(self, x, y):
    if y in self.pokemon[x]["Teammates"]:
      # P(x|not y) = P(x and not y) / P(not y)
      # (x - (x U y)) is count of times x appeared without y
      count_x_and_not_y = self.count_pokemon(x) - self.pokemon[x]["Teammates"][y]
      return (count_x_and_not_y / self.num_battles / (1 - self.pokemon[y]["usage"]))
    else:
      return self.pokemon[x]["usage"] # Never appear together, so P(x|not y) = p(x)

  def get_team_score(self, team, poke):
    product_ratios = 1
    for mon in team:
      product_ratios *= self.p_x_given_y(poke, mon) / self.p_x_given_not_y(poke, mon)
    
    return product_ratios ** (1/len(team))

  def get_usage_score(self, poke):
    return self.pokemon[poke]["usage"]

  def get_combined_score(self, counter_score, counters_weight, team_score, team_weight, usage_score, usage_weight):
    assert(team_score >= 0)
    assert(usage_score >= 0)
    assert(counter_score >= 0)
    if team_score == 0 or usage_score == 0 or counter_score == 0:
      return 0

    # General form of quasi-arithmetic means.
    def mean_func(x):
      return math.log(x, 10)

    def mean_inverse_func(x):
      return 10 ** x

    if counters_weight + team_weight + usage_weight == 0:
      counters_weight = 1
      team_weight = 1
      usage_weight = 1
    mean = mean_func(counter_score) * counters_weight + mean_func(team_score) * team_weight + mean_func(usage_score) * usage_weight
    mean /= counters_weight + team_weight + usage_weight
    mean = mean_inverse_func(mean)
    return mean

  def threats_to_dict(self, threats, team_length):
    threats_dict = {}
    for poke in self.pokemon:
      threats_dict[poke] = threats[self.indices[poke]] / team_length * 100
    
    return threats_dict

  def analyze(self, team, usage_weight, counters_weight, team_weight, recursive=False):
    threats = self.find_threats(team)
    
    c_scores = []
    t_scores = []
    u_scores = []
    for poke in self.pokemon:
      c_scores.append(self.get_counter_score(threats, len(team), poke))
      t_scores.append(self.get_team_score(team, poke))
      u_scores.append(self.get_usage_score(poke))

    scores = {}
    for index, poke in enumerate(self.pokemon):
      combined = self.get_combined_score(c_scores[index], counters_weight,
                                    t_scores[index], team_weight,
                                    u_scores[index], usage_weight)
      scores[poke] = (combined, c_scores[index], t_scores[index], u_scores[index])
      
    sorted_scores = sorted(scores.items(), key=lambda kv: kv[1][0], reverse=True)

    if recursive:
        return sorted_scores[0][0]
    else:
        my_team = None
        if len(team) < 5:
            my_team = team.copy()
            my_team.append(sorted_scores[0][0])
            while len(my_team) < 6:
                new_member = self.analyze(my_team, usage_weight, counters_weight, team_weight, True)
                my_team.append(new_member)

            change_made = True
            teams = set(tuple(sorted(my_team)))
            while change_made:
                change_made = False
                for x in range(len(team), 6):
                  old_member = my_team[x]
                  team_without = my_team[:x] + my_team[x+1:]
                  new_member = self.analyze(team_without, usage_weight, counters_weight, team_weight, True)
                  if new_member != old_member:
                    change_made = True
                    my_team[x] = new_member
                    sorted_team = tuple(sorted(my_team))
                    if sorted_team in teams:
                      change_made = False
                      break
                    else:
                      teams.add(sorted_team)

        swaps = None
        if len(team) == 6:
            swaps = {}
            # Instead of building the rest of the team, suggest some possible single swaps.
            for x in range(6):
                new_poke = self.analyze(team[:x] + team[x + 1:], usage_weight, counters_weight, team_weight, True)
                if new_poke != team[x]:
                    swaps[team[x]] = new_poke
                    
        return self.threats_to_dict(threats, len(team)), scores, my_team, swaps