from main import get_md
import cProfile as cp
pr = cp.Profile()
pr.enable()
md = get_md("gen8ou-1500")
md.analyze(["Landorus-Therian"], 1, 1, 1)
pr.disable()
pr.print_stats(sort="time")