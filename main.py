from flask import Flask, render_template, request, redirect, Markup, abort, url_for
from waitress import serve
import analyze
import display as d
import os
import update
from hashlib import blake2s
import corefinder
import functools

app = Flask(__name__)
app.config.from_object(__name__)
app.config['SECRET_KEY'] = 'DBE71E66D9EC317B7D2F13DB134F2'

@functools.lru_cache(maxsize=128, typed=False)
def get_md(dataset):
    try:
      return analyze.MetagameData("datasets/" + dataset + ".json", "datasets/" + dataset + "_threats.npy")
    except FileNotFoundError:
      abort(404)

@app.route("/", methods=['GET', 'POST'])
def select_data():
  form = d.DataSelectForm(request.form)
  form.selector.choices = sorted([filename[:-5] for filename in os.listdir("datasets") if ".json" in filename])

  if request.method == 'POST':
    return redirect(url_for("analysis", dataset=request.form["selector"]))
  else:
    with open("datasets/top_formats") as f:
      lines = []
      top = f.read().splitlines()
      for f in top:
        format_name, ratings = f.split(" ")
        line = format_name
        for rating in ratings.split(","):
          link = d.link_for_analysis(format_name, rating)
          line += " " + link
        lines.append(line)
      
    return render_template("DataSelector.html", form=form, top=lines)

@app.route("/pokemon/<dataset>/<poke>/")
def display_pokemon(dataset, poke):
  md = get_md(dataset)
  if poke not in md.pokemon:
    abort(404)

  usage = "{:.1%}".format(md.pokemon[poke]["usage"])

  counters_table = d.CountersTable(poke, md, dataset)
  team_table = d.TeamTable(poke, md, dataset)
  moves_table = d.MovesTable(poke, md, dataset)
  items_table = d.ItemsTable(poke, md, dataset)
  abilities_table = d.AbilitiesTable(poke, md, dataset)

  return render_template("PokemonInfo.html", poke=poke, dataset=dataset, usage=usage, counters=counters_table, team=team_table, items=items_table, moves=moves_table, abilities=abilities_table)

@app.route("/pokemon/<dataset>/")
def pokedex(dataset):
  md = get_md(dataset)
  pokemon = [d.link_for_poke(dataset, p) for p in sorted(md.pokemon.keys())]
  return render_template("Pokedex.html", pokemon=pokemon, dataset=dataset)

@app.route("/items/<dataset>/<item>/")
def display_item(dataset, item):
  md = get_md(dataset)

  item_holders = d.ItemHoldersTable(item, md, dataset)
  if not item_holders.items:
    abort(404)

  return render_template("ItemInfo.html", item = item, dataset = dataset, holders = item_holders)

@app.route("/items/<dataset>/")
def item_dex(dataset):
  md = get_md(dataset)
  
  items = set()
  for poke in md.pokemon:
    top_items = sorted(md.pokemon[poke]["Items"].items(), key=lambda kv: -kv[1])[:5]
    for item in top_items:
      items.add(item[0])

  items_display = [d.link_for_item(dataset, i) for i in sorted(list(items))]
  return render_template("ItemDex.html", items=items_display, dataset=dataset)

@app.route("/moves/<dataset>/<move>/")
def display_move(dataset, move):
  md = get_md(dataset)

  move_users = d.MoveUsersTable(move, md, dataset)

  if not move_users.items:
    abort(404)

  return render_template("MoveInfo.html", move = move, dataset = dataset, users = move_users)

@app.route("/moves/<dataset>/")
def move_dex(dataset):
  md = get_md(dataset)
  
  moves = set()
  for poke in md.pokemon:
    top_moves = sorted(md.pokemon[poke]["Moves"].items(), key=lambda kv: -kv[1])[:10]
    for move in top_moves:
      moves.add(move[0])

  moves_display = [d.link_for_move(dataset, m) for m in sorted(list(moves)) if m]
  return render_template("MoveDex.html", moves=moves_display, dataset=dataset)

@app.route("/abilities/<dataset>/<ability>/")
def display_ability(dataset, ability):
  md = get_md(dataset)

  abil_users = d.AbilityUsersTable(ability, md, dataset)

  if not abil_users.items:
    abort(404)

  return render_template("AbilityInfo.html", abil = ability, dataset = dataset, users = abil_users)

@app.route("/abilities/<dataset>/")
def ability_dex(dataset):
  md = get_md(dataset)
  
  abils = set()
  for poke in md.pokemon:
    for abil in md.pokemon[poke]["Abilities"].items():
      if abil[1] / md.count_pokemon(poke) > .06:
        abils.add(abil[0])

  abilities_display = [d.link_for_ability(dataset, a) for a in sorted(list(abils)) if a]
  return render_template("AbilityDex.html", abilities=abilities_display, dataset=dataset)

@app.route("/analysis/<dataset>/")
def analysis(dataset):
  form = d.PokemonForm(request.form)
  md = get_md(dataset)
  sorted_pokemon = sorted(md.pokemon)
  first = True
  for selector in form.selectors:
    selector.choices = [(x, x) for x in sorted_pokemon]
    if first:
      first = False
    else:
      selector.choices = [("", "None")] + selector.choices

  return render_template('TeamBuilder.html', form=form, dataset=dataset)

@app.route("/analysis/<dataset>/run_analysis", methods=['POST'])
def output_analysis(dataset):
  threats_table = None
  recommendations_table = None
  team = None
  swaps_text = None
  md = get_md(dataset)

  my_pokes = []
  usage_setting = float(request.form["usage_setting"])
  counter_setting = float(request.form["counter_setting"])
  team_setting = float(request.form["team_setting"])
  
  for selector in request.form.items():
    if selector[1] and "selector" in selector[0]:
      my_pokes.append(selector[1])

  threats, bundled, suggested_team, swaps = md.analyze(my_pokes, usage_setting, counter_setting, team_setting)

  threats_table = d.ThreatsTable(threats, dataset)
  recommendations_table = d.RecommendationsTable(bundled, dataset, len(my_pokes) < 6)

  if suggested_team:
    js_array = "['" + "','".join(suggested_team) + "']"
    suggested_team = [d.link_for_poke(dataset, t) for t in suggested_team]
    try_team_link = '<a href="javascript:tryTeam({})" class="try_team_link">Try it!</span></a>'.format(js_array)
    team = Markup("Possible team including your selections: {}. {}".format(", ".join(suggested_team), try_team_link))

  if swaps:
    swaps_text = "Consider making one of the following changes:"
    for swap in swaps:
      swaps_text += "<br>Swap {} for {}.".format(d.link_for_poke(dataset, swap), d.link_for_poke(dataset, swaps[swap]))
      swaps_text += ' <a href="javascript:handleSwapPoke(\'{}\', \'{}\')" class="swap_link"><span class="fas fa-exchange-alt"></span></a>'.format(swap, swaps[swap])

    swaps_text = Markup(swaps_text)

  return render_template("TeamBuilderAnalysis.html", threats=threats_table, recommendations=recommendations_table, team=team, swaps=swaps_text)

@app.route("/cores/<dataset>/")
def cores(dataset):
  return render_template("CoreFinder.html", dataset=dataset, form=d.CoreFinderForm())

@app.route("/cores/<dataset>/find_cores", methods=['POST'])
def find_cores(dataset):
  md = get_md(dataset)
  
  usage_threshold = float(request.form["usage_threshold"])
  score_requirement = float(request.form["score_requirement"])
  cf = corefinder.CoreFinder(md, usage_threshold, score_requirement)
  unlinked_cores = cf.find_cores()
  linked_cores = []
  for core in unlinked_cores:
    linked_cores.append([d.link_for_poke(dataset, x) for x in core])

  return render_template("CoreFinderResults.html", cores=linked_cores)

@app.route("/update/<key>/")
def request_update(key):
  # This isn't exactly real security, but it's hopefully enough to prevent random people forcing updates.
  blake = blake2s()
  blake.update(key.encode())
  hex = blake.hexdigest()
  expectedhex = '0a7758f62d5f8c069bf2a4c24fcb98dc23df90b738cb7ac1e792ed702c746fb8'

  if hex == expectedhex:
    update.update()
    return("Update complete!")
  else:
    abort(401)

if __name__ == "__main__":
  serve(app, host='0.0.0.0', port=8080)