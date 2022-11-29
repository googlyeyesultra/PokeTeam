"""Handles analysis of a given metagame.

This module is responsible for loading data for a given metagame.
It evaluates Pokemon and teams and makes recommendations.
"""

import math
from dataclasses import dataclass
import ujson as json
import numpy as np


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

    def _get_counter_score(self, threats, team_size, poke):
        """Generate a score based on how good a Pokemon \
            is at countering threats to a team.

        Args:
            threats (1d numpy array): Each index contains how threatening
            the Pokemon with that index is to the team.

            team_size (int): Number of Pokemon on team so far.

            poke (str): Name of Pokemon being considered.

        Returns:
            float >= 0: High score corresponds to being strong against threats.
        """
        new_threats = threats + self._threat_matrix[self._indices[poke]]
        return 100 ** (-(new_threats[new_threats > 0].sum() / (team_size + 1)))

    def _get_team_score(self, team, poke):
        """Generate a score based on how well a Pokemon \
            works with given teammates.

        Args:
            team (list of str): List of Pokemon on team already.

            poke (str): Name of Pokemon being considered.

        Returns:
            float >= 0: High score corresponds to going well with teammates.
        """

        # Geometric mean of the P(X|Y)/P(X|not Y) ratio
        # Where x is the mon we're considering adding.
        # Log form required.
        log_sum = 0
        sum_usage_factor = 0
        for mon in team:
            # P(X|not Y) is 0 if X doesn't occur without Y.
            # So Y needs to be on team.
            # On the flip side, if P(X|Y) is 0, we need to not put Y on the team.
            # This is common where X and Y are the same mon.

            ratio = self._team_matrix[self._indices[mon], self._indices[poke]]
            if ratio == 0:
                # This behaves the same way multiplying by 0 would in the non-log form.
                log_sum = -math.inf
                break
            else:
                log_sum += math.log10(ratio)

        return 10 ** (log_sum / len(team))

    def _get_usage_score(self, poke):
        """Generate a score based on often a Pokemon is used.

        Args:
            poke (str): Name of Pokemon being considered.

        Returns:
            float >= 0: High score corresponds to high usage.
        """
        return self.pokemon[poke]["usage"]

    @staticmethod
    def _mean_func(val):
        """Calculate a quasi-arithmetic mean.

        Compute the (unweighted) quasi-arithmetic mean of a, b, c by taking
        _mean_inverse_func(_mean_func(a) + _mean_func(b) + _mean_func(c))

        Args:
            val (float): Number to include in average.

        Returns:
            float: Processed number to include in mean.
        """
        return math.log(val, 10)

    @staticmethod
    def _mean_inverse_func(mean_sum):
        """Calculate a quasi-arithmetic mean.

        Compute the (unweighted) quasi-arithmetic mean of a, b, c by taking
        _mean_inverse_func(_mean_func(a) + _mean_func(b) + _mean_func(c))

        Args:
            mean_sum (float): Sum of processed values.

        Returns:
            float: Final result of quasi-arithmetic mean.
        """
        return 10 ** mean_sum

    def _get_combined_score(self,
                            counter_score, team_score, usage_score, weights):
        """Generate a combined score based on the three partial scores.

        Combines the counter, team, and usage scores, along with their weights,
        to come up with an overall fitness rating.

        Args:
            counter_score (float >= 0):
                How good the Pokemon is at beating counters to the team.
            team_score (float >= 0):
                How well the Pokemon works with the rest of the team.
            usage_score (float >= 0):
                How often the Pokemon is used in general.
            weights (Weights):
                How much we care about each of the scores.

        Returns:
            float >= 0: Overall fitness score. Higher values are better.
        """
        assert team_score >= 0, "Team score < 0: " + str(team_score)
        assert usage_score >= 0, "Usage score < 0: " + str(usage_score)
        assert counter_score >= 0, "Counter score < 0: " + str(counter_score)

        if team_score == 0 or usage_score == 0 or counter_score == 0:
            return 0

        mean = (MetagameData._mean_func(counter_score) * weights.counter
                + MetagameData._mean_func(team_score) * weights.team
                + MetagameData._mean_func(usage_score) * weights.usage)
        mean /= weights.total
        mean = MetagameData._mean_inverse_func(mean)
        return mean

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
        c_scores = []
        t_scores = []
        u_scores = []
        for poke in self.pokemon:
            c_scores.append(self._get_counter_score(threats, len(team), poke))
            t_scores.append(self._get_team_score(team, poke))
            u_scores.append(self._get_usage_score(poke))

        scores = []
        for index, poke in enumerate(self.pokemon):
            combined = self._get_combined_score(
                c_scores[index], t_scores[index], u_scores[index], weights)

            scores.append((poke, combined, c_scores[index],
                t_scores[index], u_scores[index]))

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
        if not scores:
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
                    change_made = False
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

        threats_dict = self._threats_to_dict(threats, len(team))
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

    def partner_scores(self, poke):
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
