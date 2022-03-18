import analyze as a
from networkx.algorithms import clique
from networkx import Graph
import numpy

score_requirement_default = .03
usage_threshold_default = .01

class CoreFinder:
  def __init__(self, md, usage_threshold, score_requirement):
    self.keys = [x for x in md.pokemon.keys() if md.pokemon[x]["usage"] >= usage_threshold]

    data = numpy.empty((len(self.keys), len(self.keys)), dtype=bool)
    for poke_index, poke in enumerate(self.keys):
      for team_poke_index, team_poke in enumerate(self.keys):
        if poke_index == team_poke_index:
          data[poke_index, team_poke_index] = True
        elif team_poke in md.pokemon[poke]["Teammates"]:
          symmetric_score = md.pokemon[poke]["Teammates"][team_poke] / md.count_pokemon(poke) * (1 - md.pokemon[team_poke]["usage"])
          symmetric_score *= md.pokemon[team_poke]["Teammates"][poke] / md.count_pokemon(team_poke) * (1 - md.pokemon[poke]["usage"])
          data[poke_index, team_poke_index] = (symmetric_score > score_requirement)
        else:
          data[poke_index, team_poke_index] = False

    self.graph = Graph(data)

  def find_cores(self):
    ret_val = []
    for x in clique.find_cliques(self.graph):
      if len(x) > 20:
        return []
      if len(x) >= 2: # One mon is not a core, nor is lumping most of the format together a core.
        ret_val.append([self.keys[y] for y in x])

    return ret_val
