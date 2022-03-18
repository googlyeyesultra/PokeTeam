import ujson as json
from modAL.models import ActiveLearner
from sklearn.ensemble import RandomForestClassifier
import random

json_file = "datasets/gen8ou-1500.json"
with open(json_file, "r") as file:
        data = json.load(file)
        pokemon = data["data"]

test_threat = "Landorus-Therian"

def avg_switchins_per_battle(a, ignored):
  # Ignore b
  battles_in = pokemon[a]["usage"] * data["info"]["number of battles"]
  total_switchins = 0
  for b in pokemon[a]["Checks and Counters"]:
    total_switchins += pokemon[a]["Checks and Counters"][b][0]

  return total_switchins / battles_in

def a_beats_b(a, b):
  if a not in pokemon[b]["Checks and Counters"]:
    return None
  return pokemon[b]["Checks and Counters"][a][1]

def b_beats_a(a, b):
  if a not in pokemon[b]["Checks and Counters"]:
    return None
  return pokemon[a]["Checks and Counters"][b][1]


feature_functions = [avg_switchins_per_battle, a_beats_b, b_beats_a]

def feature_func(poke):
  return [x(poke, test_threat) for x in feature_functions]

valid_poke_list = [x for x in pokemon if x in pokemon[test_threat]["Checks and Counters"]]
features_for_pokes = []
for poke in valid_poke_list:
  features_for_pokes.append(feature_func(poke))

learner = ActiveLearner(estimator=RandomForestClassifier())

found_false = False
found_true = False
while (not found_false or not found_true):
  query_index = random.randrange(len(valid_poke_list))
  query_sample = features_for_pokes[query_index]
  answer = input("Is " + valid_poke_list[query_index] + " a good counter for " + test_threat + "? (1Y or 2N)")
  if answer == "1":
    found_true = True
  else:
    found_false = True
  learner.teach([query_sample], [answer == "1"])

for i in range(30):
  query_index, query_sample = learner.query(features_for_pokes)
  query_index = query_index[0]
  query_sample = query_sample[0]
  prediction = learner.predict([query_sample])[0]
  answer = input("Is " + valid_poke_list[query_index] + " a good counter for " + test_threat + "? (1Y or 2N)")
  print("Prediction was " + str(prediction))
  learner.teach([query_sample], [answer == "1"])
  