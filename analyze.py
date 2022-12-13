"""Handles analysis of a given metagame.

This module is responsible for loading data for a given metagame.
It evaluates Pokemon and teams and makes recommendations.
"""

import math
from dataclasses import dataclass
import ujson as json
import numpy as np
from scipy.stats.mstats import gmean


COUNTER_WEIGHT_DEFAULT = 2
TEAM_WEIGHT_DEFAULT = 5
USAGE_WEIGHT_DEFAULT = 2  # TODO maybe move this up to 3


@dataclass(frozen=True)
class Weights:
    """Simple wrapper for score weights."""

    def __init__(self, counter_weight, team_weight, usage_weight):
        """Construct weight set.

        Args:
            counter_weight (float >=0): How important counter score is.

            team_weight (float >=0): How important team score is.

            usage_weight (float >=0): How important usage score is.
        """
        # If all weights are 0, treat them as all equal.
        if counter_weight == 0 and team_weight == 0 and usage_weight == 0:
            counter_weight = 1
            team_weight = 1
            usage_weight = 1

        # Have to use this in init as class is immutable.
        object.__setattr__(self, 'counter', counter_weight)
        object.__setattr__(self, 'team', team_weight)
        object.__setattr__(self, 'usage', usage_weight)
        object.__setattr__(self, 'total',
                           counter_weight + team_weight + usage_weight)


class MetagameData:
    """Core of analyze.

    Contains data for a provided metagame and performs useful analysis on it.
    """

    def __init__(self, json_file, threat_file, team_file):
        """Load metagame data from file.

        Args:
            json_file (str):
                Path to file containing pre-processed and validated version of
                Smogon's chaos json for a metagame.
            threat_file (str):
                Path to file containing a numpy matrix.
                threat_matrix[x, y] is how threatening the Pokemon with index
                y is to the Pokemon with index x.
        """
        with open(json_file, "r", encoding="utf-8") as file:
            data = json.load(file)
            self.pokemon = data["pokemon"]
            self._indices = data["indices"]
            self._total_pokes = data["info"]["total_pokes"]
            self._pokes_per_team = data["info"]["pokes_per_team"]
            self._num_teams = data["info"]["num_teams"]
            self._total_pairs = data["info"]["total_pairs"]
            self.gen = data["info"]["gen"]
            self.items = data["items"]
            self.abilities = data["abilities"]
            self.moves = data["moves"]

        with open(threat_file, "rb") as file:
            self._threat_matrix = np.load(file)

        with open(team_file, "rb") as file:
            self._team_matrix = np.load(file)

    def _find_threats(self, team):
        """Generate threat ratings for threats for a provided team.

        Args:
            team (list of str): List of Pokemon names representing a
            partial or full team.

        Returns:
            summed (1d numpy array of float): Each index contains how
            threatening the Pokemon with that index is to the team.
        """
        team_indices = [self._indices[t] for t in team]
        summed = self._threat_matrix[team_indices].sum(0)

        return summed

    def count_pokemon(self, poke):
        """Count how many times a given Pokemon was used.

        Args:
            poke (str): Name of Pokemon to check.

        Returns:
            float > 0: Number of times that Pokemon appeared on a team.
            Note that it can be a non-integer as Smogon weights statistics by
            player rating.
        """
        return self.pokemon[poke]["count"]


    def _threats_to_dict(self, threats, team_length):
        """Convert threats to a dict of name -> threat rating.

        Convert from array with arbitrary indices to a dictionary
        from name -> threat rating. Also adjusts for team size and scales for
        display purposes.

        Args:
            threats (1d numpy array): Each index contains how threatening
            the Pokemon with that index is to the team.

            team_length (int >= 0): Number of Pokemon on the team.

        Returns:
            threats_dict (dict): Dictionary mapping Pokemon name
            to threat rating. Rating is scaled for display and normalized
            relative to team length.
        """
        threats_dict = {}
        for poke in self.pokemon:
            threats_dict[poke] = 100 * (threats[self._indices[poke]] /
                                        team_length)

        return threats_dict

    def _scores(self, team, threats, weights):
        """Calculate each of the scores for every potential Pokemon.

        Args:
            team (list of str): Pokemon names that are already on the team.
            threats (1d numpy array of float): Each index contains how
            threatening the Pokemon with that index is to the team.

            weights (Weights): How much to value each score when combining.

        Returns:
            scores (list of tuple): (name, combined, counter, team, usage)
            Each value is a float >= 0.
            In order by index of Pokemon.
        """
        u_scores = [self.pokemon[p]["usage"] for p in self.pokemon]
        team_indices = [self._indices[t] for t in team]
        if team:
            t_scores = gmean(self._team_matrix[team_indices], 0)
            new_threats = np.repeat(threats[None, :], len(self.pokemon), axis=0) + self._threat_matrix
            sum_pos = np.nansum(np.where(new_threats>0, new_threats, np.nan), 1)
            c_scores = 100 ** (-sum_pos / (len(team) + 1))
        else:
            t_scores = np.ones((len(self.pokemon,)))
            c_scores = np.ones((len(self.pokemon,)))

        stacked = np.stack((c_scores, t_scores, u_scores))

        combined_scores = gmean(stacked, axis=0, weights=[[weights.counter],
                                                          [weights.team],
                                                          [weights.usage]])
        scores = list(zip(self._indices.keys(), combined_scores, c_scores, t_scores, u_scores))

        # TODO consider refactoring to return a dictionary.
        # Maybe dict (name -> a scores object)
        return scores

    def _get_best(self, team, weights, scores=None):
        """Find the best addition (greedily) to a partial team.

        Args:
            team (list of str): Names of Pokemon already on the team.

            weights (Weights): How important each kind of score is.

            scores (list of tuples): scores for each Poke to avoid recalculating.

        Returns:
            str: Name of best Pokemon to add.
        """
        if scores is None:
            threats = self._find_threats(team)
            scores = self._scores(team, threats, weights)
        return sorted(scores, key=lambda kv: -kv[1])[0][0]

    def _get_best_with_improvement(self, team, current, weights):
        """Find the best swap for a Pokemon on a team.

        Args:
            team (list of str): Names of Pokemon already on the team, except the one to swap.

            current (str): Name of Pokemon we're considering swapping out.

            weights (Weights): How important each kind of score is.

            scores (list of tuples): scores for each Poke to avoid recalculating.

        Returns:
            (str, float): Name of best Pokemon to swap in (can be same), how much of an improvement it is.
        """
        threats = self._find_threats(team)
        scores = self._scores(team, threats, weights)
        best = self._get_best(team, weights, scores)
        improvement = scores[self._indices[best]][1] - scores[self._indices[current]][1]
        return best, improvement

    def _build_full(self, team, best, weights):
        """Recommend a full team from a partial one.

        Args:
            team (list of str): Partial team to extend.

            best (str): Current best next Pokemon.
            Passed to avoid recalculating.

            weights (Weights): How important each kind of score is.

        Returns:
            my_team (list of str): List of Pokemon names on full team.
            None if team is already full.
        """
        if len(team) == 6:
            return None

        my_team = team.copy()
        my_team.append(best)
        while len(my_team) < 6:
            # Greedily add new members until full.
            new_member = self._get_best(my_team, weights)
            my_team.append(new_member)

        # Try swapping out individual Pokemon to see if we can improve.
        change_made = True
        teams = set(tuple(sorted(my_team)))
        while change_made:
            change_made = False
            most_improvement = (None, 0, -1)  # Mon to use, score, index of swap.
            # Start at len(team) to leave Pokemon the user specified in.
            for x in range(len(team), 6):
                old_member = my_team[x]
                team_without = my_team[:x] + my_team[x+1:]
                improvement = self._get_best_with_improvement(team_without, old_member, weights) + (x,)
                if improvement[1] > most_improvement[1]:
                    most_improvement = improvement

            if most_improvement[0]:
                change_made = True
                my_team[most_improvement[2]] = most_improvement[0]
                sorted_team = tuple(sorted(my_team))
                if sorted_team in teams:  # Break cycles.
                    break

                teams.add(sorted_team)

        return my_team

    def _suggest_swaps(self, team, weights):
        """Suggest swaps for a full team.

        Args:
            team (list of str): Names of Pokemon on team.
            weights (Weights): How important each kind of score is.

        Returns:
            swaps (dict str->(str, float)): Suggested swaps.
            swaps["Aipom"] = ("Pichu", 1.2)
            means you should consider swapping Aipom with Pichu
            and that it believes that improves the team by 1.2
            None if team is not full.
        """
        if len(team) != 6:
            return None

        swaps = {}
        # Try removing each individual Pokemon and test if anything is better.
        for x in range(6):
            swap = self._get_best_with_improvement(team[:x] + team[x + 1:], team[x], weights)
            if swap[0] != team[x]:
                swaps[team[x]] = swap

        return swaps

    def analyze(self, team, weights):
        """Perform full analysis of a team.

        Args:
            team (list of str): Names of Pokemon already on team.
            weights (Weights): How important each kind of score is.

        Returns:
            threats_dict (dict str->float): Maps Pokemon name to how
            threatening that Pokemon is to the team.

            scores (list of tuple):
            (Pokemon name, combined score, counter score, team score, usage score).

            my_team (list of str): Suggested full team,
            or None if team is already full.

            swaps (dict str->str): Mapping between Pokemon to replace
            and what to replace it with, or None if team is not yet full.
        """
        threats = self._find_threats(team)
        scores = self._scores(team, threats, weights)
        best = self._get_best(team, weights, scores)
        my_team = self._build_full(team, best, weights)
        swaps = self._suggest_swaps(team, weights)

        if team:
            threats_dict = self._threats_to_dict(threats, len(team))
        else:
            threats_dict = {}
        return threats_dict, scores, my_team, swaps

    def find_counters(self, poke):
        """Find counters for a single Pokemon.

        Args:
            poke (str): Pokemon to find counters for.

        Returns:
            dict str->float: Dictionary of Pokemon name ->
            how good of a counter it is.
        """
        return self._threats_to_dict(self._find_threats([poke]), 1)

    def partner_scores(self, poke): # TODO this is broken now
        """Find how well each possible partner goes with poke.

        For display purposes only - this bakes in usage score.

        Args:
            poke (str): Name of Pokemon to be accompanied.

        Returns:
            dict str->float: How good each Pokemon is as a partner.
        """
        teammates = {}
        for partner in self.pokemon:
            teammates[partner] = (self._get_team_score([poke], partner)
                                  * self._get_usage_score(partner))

        return teammates
