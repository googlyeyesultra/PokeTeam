"""Simple profiling of analysis.
Just a quick and dirty way to do some basic profiling.
"""

from main import get_md
from analyze import Weights
import cProfile as cp
pr = cp.Profile()
pr.enable()
md = get_md("gen8ou-1500")
weights = Weights(1, 1, 1)
md.analyze(["Landorus-Therian"], weights)
pr.disable()
pr.print_stats(sort="time")
