from main import get_md
import csv
md = get_md("gen8ou-1500")

folder = "./dump/"

with open(folder + "scores.csv", 'w', newline='') as csvfile:
  writer = csv.writer(csvfile, delimiter=',',
                      quotechar='"', quoting=csv.QUOTE_MINIMAL)
  writer.writerow(["Pokemon", "Combined Score", "Counter Score", "Team Score", "Usage Score"])
  results = md.analyze(["Heatran"], 1, 1, 1)[1]
  for poke in results:
    writer.writerow([poke] + list(results[poke]))