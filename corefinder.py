"""Finds cores.

Cores are groups of 2 or more Pokemon that are commonly used together.
"""

from networkx.algorithms import clique
from networkx import Graph
import numpy as np

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
        self.pokemon_names = []
        usage_indices = []
        for index, name in enumerate(md.pokemon):
            if md.pokemon[name]["usage"] > usage_threshold:
                self.pokemon_names.append(name)
                usage_indices.append(index)

        core_matrix = np.array(md._team_matrix)[usage_indices, :][:, usage_indices]
        np.fill_diagonal(core_matrix, 1)
        core_matrix *= core_matrix.transpose()
        core_matrix = core_matrix > score_requirement

        self.graph = Graph(core_matrix)

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
                cores.append([self.pokemon_names[y] for y in x])

        cores.sort(key=lambda x: len(x))
        return cores
