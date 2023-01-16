"""Finds cores.

Cores are groups of 2 or more Pokemon that are commonly used together.
"""

from networkx.algorithms import clique
from networkx.algorithms.approximation import greedy_tsp as tsp
from networkx import Graph
import numpy as np
from collections import Counter

TARGET_EDGES_DEFAULT = 100
USAGE_WEIGHT_DEFAULT = 1


class CoreFinder:
    """Responsible for finding cores within a metagame."""

    def __init__(self, md, usage_weight, target_edges):
        """Load metagame data and preferences.

        Construct a graph with edges where a score based on
        teammate probabilities is greater than the score requirement.

        Args:
            md (MetagameData): Metagame to find cores in.

            usage_weight (float >= 0):
            Higher usage_weight makes higher usage Pokemon appear in cores more often.

            target_edges (int >= 1):
            Higher target_edges makes more and larger cores (and takes longer to run).
        """
        self.pokemon_names = list(md.pokemon.keys())
        usages = [md.pokemon[poke]["usage"] ** usage_weight for poke in md.pokemon]

        core_matrix = np.array(md._team_matrix)
        core_matrix *= usages
        np.fill_diagonal(core_matrix, 0)
        core_matrix *= core_matrix.transpose()

        num_edges = len(md.pokemon) ** 2
        core_matrix = core_matrix > np.quantile(core_matrix, max(.5, 1 - target_edges * 2 / num_edges))

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
            # One mon is not a core.
            if len(x) >= 2:
                cores.append(Counter([self.pokemon_names[y] for y in x]))

        cores_graph = Graph()
        for index1, core1 in enumerate(cores):
            for index2, core2 in enumerate(cores[:index1]):
                weight = (core1 - core2).total() + (core2 - core1).total()
                cores_graph.add_edge(index1, index2, weight=weight)

        ordered_indices = tsp(cores_graph)  # This is a cycle. We want a shortest path, so we need to break an edge.
        longest_edge = max(range(len(ordered_indices)-1), key=lambda k: cores_graph[ordered_indices[k]][ordered_indices[k+1]]["weight"])
        ordered_indices = ordered_indices[longest_edge+1:-1] + ordered_indices[:longest_edge+1]
        assert len(ordered_indices) == len(cores)
        return [sorted(cores[i].elements()) for i in ordered_indices]
