"""Finds cores.

Cores are groups of 2 or more Pokemon that are commonly used together.
"""

from networkx.algorithms import clique
from networkx import Graph
import numpy

SCORE_REQUIREMENT_DEFAULT = 3
USAGE_THRESHOLD_DEFAULT = 1


class CoreFinder:
    """Responsible for finding cores within a metagame."""

    def __init__(self, md, usage_threshold, score_requirement):
        """Load metagame data and preferences.

        Construct a graph with edges where a score based on
        teammate probabilities is greater than the score requirement.

        Args:
            md (MetagameData): Metagame to find cores in.

            usage_threshold (float >= 0):
            Mininum usage for a Pokemon to be included. Note that some Pokemon
            with low usage are already excluded by MetagameData.

            score_requirement (float): How closely linked two Pokemon need
            to be to be considered to be in a core together.
        """
        self.keys = [x for x in md.pokemon.keys() if md.pokemon[x]
                     ["usage"] >= usage_threshold]

        data = numpy.empty((len(self.keys), len(self.keys)), dtype=bool)
        for poke_index, poke in enumerate(self.keys):
            for team_poke_index, team_poke in enumerate(self.keys):
                if poke_index == team_poke_index:
                    data[poke_index, team_poke_index] = True
                else:
                    symmetric_score = (md._get_team_score([poke], team_poke) * md._get_team_score([team_poke], poke)) ** .5
                    data[poke_index, team_poke_index] = (symmetric_score > score_requirement)

        self.graph = Graph(data)

    def find_cores(self):
        """Find cores.

        Look for maximal cliques on a graph,
        where the edges are based on teammate probabilities.

        Returns:
            list of list of str: List of lists of Pokemon Names. Each sublist
            corresponds to a core, containing the Pokemon within it.
        """
        cores = []
        for x in clique.find_cliques(self.graph):
            if len(x) > 20:
                # Lumping the whole metagame together is not useful.
                return None
            # One mon is not a core.
            if len(x) >= 2:
                cores.append([self.keys[y] for y in x])

        cores.sort(key=lambda x: len(x))
        return cores
