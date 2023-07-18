"""Handles routing, serving, and preparing pages."""
import functools

from flask import (Flask, render_template, request,
                   redirect, abort, url_for)

from waitress import serve
import analyze
import update
import corefinder
import dex
import os
from file_constants import *
from file_loader import DataFilePath

app = Flask(__name__)
app.config.from_object(__name__)
app.jinja_env.trim_blocks = True
app.jinja_env.lstrip_blocks = True
app.jinja_env.policies['json.dumps_kwargs'] = {'sort_keys': False, 'ensure_ascii': False}
app.config["SECRET_KEY"] = os.environ["FLASK_SECRET_KEY"]


@functools.lru_cache(maxsize=64, typed=False)
def get_md(dataset):
    """Get MetagameData object for a format."""
    try:
        metagame = DataFilePath(dataset + ".json")  # TODO maybe don't hardcode
        threats = DataFilePath(dataset + THREAT_FILE)
        team = DataFilePath(dataset + TEAMMATE_FILE)
        return analyze.MetagameData(metagame, threats, team)
    except FileNotFoundError:
        abort(404)


@functools.lru_cache(maxsize=12, typed=False)
def get_dex(gen):
    """Get generation appropriate dex for a format."""
    try:
        return dex.Dex(DataFilePath(DEX_PREFIX + gen + DEX_SUFFIX))
    except FileNotFoundError:
        abort(500)


@app.route("/", methods=['GET', 'POST'])
def select_data():
    """Page for selecting a format."""
    with open(DataFilePath(DATE_FILE), encoding="utf-8") as date_fd:
        date = date_fd.read()

    with open(DataFilePath(FORMATS_FILE), encoding="utf-8") as f:
        top = f.read().splitlines()
        formats = []
        for metagame in top:
            format_name, battles_played, counters, ratings = metagame.split(" ")
            counters = counters == "C"
            ratings = ratings.split(",")
            formats.append((format_name, counters, battles_played, ratings))

    return render_template("DataSelector.html", date=date, formats=formats)


@app.route("/pokemon/<dataset>/<poke>/")
def display_pokemon(dataset, poke):
    """Page for displaying data for a specific Pokemon."""
    md = get_md(dataset)
    if poke not in md.pokemon:
        abort(404)

    usage = md.pokemon[poke]["usage"]

    if md.counters:
        counters = sorted(md.find_counters(poke).items(), key=lambda kv: -kv[1])
        for i in range(len(counters)):  # Only show things that actually counter.
            if counters[i][1] <= 0:
                counters = counters[:i]
                break
    else:
        counters = None

    teammates = sorted(md.partner_scores(poke).items(), key=lambda kv: -kv[1])
    for i in range(len(teammates)):  # Only show positive teammates.
        if teammates[i][1] <= 0:
            teammates = teammates[:i]
            break

    items = list(md.pokemon[poke]["Items"].items())
    moves = list(md.pokemon[poke]["Moves"].items())
    abilities = list(md.pokemon[poke]["Abilities"].items())

    return render_template("PokemonInfo.html",
                           poke=poke, dataset=dataset,
                           usage=usage,
                           counters=counters,
                           teammates=teammates, items=items,
                           moves=moves, abilities=abilities,
                           gen=md.gen,
                           dex=get_dex(md.gen))


@app.route("/pokemon/<dataset>/")
def pokedex(dataset):
    """Page for listing all Pokemon in a format."""
    md = get_md(dataset)
    # TODO sort the pokemon in the json so we don't have to sort here?
    pokemon = sorted([(x, md.pokemon[x]["usage"]) for x in md.pokemon.keys()], key=lambda pair: -pair[1])
    return render_template("Pokedex.html", pokemon=pokemon, dataset=dataset, gen=md.gen, dex=get_dex(md.gen))


@app.route("/items/<dataset>/<item>/")
def display_item(dataset, item):
    """Page for displaying information about an item."""
    md = get_md(dataset)

    if item not in md.items:
        abort(404)

    return render_template("ItemInfo.html",
                           item=item, dataset=dataset, holders=md.items[item],
                           gen=md.gen, dex=get_dex(md.gen))


@app.route("/items/<dataset>/")
def item_dex(dataset):
    """Page for listing all items in a format."""
    md = get_md(dataset)
    return render_template("ItemDex.html",
                           items=md.items, dataset=dataset,
                           gen=md.gen, dex=get_dex(md.gen))


@app.route("/moves/<dataset>/<move>/")
def display_move(dataset, move):
    """Page for information about a specific move."""
    md = get_md(dataset)

    if move not in md.moves:
        abort(404)

    return render_template("MoveInfo.html",
                           move=move, dataset=dataset, move_users=md.moves[move],
                           gen=md.gen, dex=get_dex(md.gen))


@app.route("/moves/<dataset>/")
def move_dex(dataset):
    """Page that lists all moves in a format."""
    md = get_md(dataset)
    return render_template("MoveDex.html",
                           moves=md.moves, dataset=dataset,
                           gen=md.gen, dex=get_dex(md.gen))


@app.route("/abilities/<dataset>/<abil>/")
def display_ability(dataset, abil):
    """Page for details about a specific ability."""
    md = get_md(dataset)

    if abil not in md.abilities:
        abort(404)

    return render_template("AbilityInfo.html",
                           abil=abil, dataset=dataset, abil_users=md.abilities[abil],
                           gen=md.gen, dex=get_dex(md.gen))


@app.route("/abilities/<dataset>/")
def ability_dex(dataset):
    """Page that lists all abilities in a format."""
    md = get_md(dataset)
    return render_template("AbilityDex.html",
                           abilities=md.abilities, dataset=dataset,
                           gen=md.gen, dex=get_dex(md.gen))


@app.route("/analysis/<dataset>/")
def analysis(dataset):
    """Page that contains the main team builder."""
    md = get_md(dataset)

    return render_template('TeamBuilder.html', dataset=dataset,
                           has_counters_data=md.counters,
                           gen=md.gen, dex=get_dex(md.gen),
                           usage_setting=analyze.USAGE_WEIGHT_DEFAULT,
                           counter_setting=analyze.COUNTER_WEIGHT_DEFAULT,
                           team_setting=analyze.TEAM_WEIGHT_DEFAULT)


@app.route("/analysis/<dataset>/run_analysis", methods=['POST'])
def output_analysis(dataset):
    """Part of page responsible for displaying team building results."""

    if "pokemon" in request.form:
        my_pokes = request.form.getlist("pokemon")
    else:
        my_pokes = []

    md = get_md(dataset)

    usage_setting = float(request.form["usage_weight"])
    if md.counters:
        counter_setting = float(request.form["counter_weight"])
    else:
        counter_setting = 0
    team_setting = float(request.form["team_weight"])

    weights = analyze.Weights(counter_setting, team_setting, usage_setting)
    threats, bundled, suggested_team, swaps = md.analyze(my_pokes, weights)

    recommendations = sorted(bundled, key=lambda p: -p[1])
    return render_template("TeamBuilderAnalysis.html",
                           dataset=dataset, has_counters_data=md.counters,
                           threats=sorted(threats.items(), key=lambda k: -k[1]),
                           recommendations=recommendations,
                           suggested_team=suggested_team,
                           swaps=(sorted(swaps.items(), key=lambda kv: -kv[1][1]) if swaps else None),
                           add_links=(len(my_pokes) < 6),
                           gen=md.gen, dex=get_dex(md.gen))


@app.route("/cores/<dataset>/")
def cores(dataset):
    """Page for finding cores in a format."""
    return render_template("CoreFinder.html",
                           usage_weight=corefinder.USAGE_WEIGHT_DEFAULT,
                           target_edges=corefinder.TARGET_EDGES_DEFAULT,
                           min_edges=corefinder.MIN_EDGES,
                           max_edges=corefinder.MAX_EDGES,
                           dataset=dataset)


@app.route("/cores/<dataset>/find_cores", methods=['POST'])
def find_cores(dataset):
    """Part of page responsible for displaying cores in format."""

    usage_weight = float(request.form["usage_weight"])
    target_edges = float(request.form["target_edges"])
    if target_edges < corefinder.MIN_EDGES or target_edges > corefinder.MAX_EDGES:
        return render_template("NumberEdgesError.html",
                               min_edges=corefinder.MIN_EDGES,
                               max_edges=corefinder.MAX_EDGES)

    md = get_md(dataset)
    cf = corefinder.CoreFinder(md, usage_weight, target_edges)

    return render_template("CoreFinderResults.html", dataset=dataset, cores=cf.find_cores(),
                           gen=md.gen)


@app.route("/speed_tiers/<dataset>/")
def speed_tiers(dataset):
    """Page for displaying speed tiers in a format."""
    md = get_md(dataset)
    return render_template("SpeedTiers.html",
                           speed_tiers=md.speed_tiers,
                           dataset=dataset)


@app.route("/update/<key>/")
def request_update(key):
    """Endpoint to download new statistics. Not for public use."""
    if key != os.environ["UPDATE_PASS"]:
        abort(401)

    update.update()
    return "Update complete!"


if __name__ == "__main__":
    if not os.path.exists(DATA_DIR):
        os.mkdir(DATA_DIR)

    print("Server starting.")
    serve(app, host='0.0.0.0', port=int(os.environ["PORT"]))
