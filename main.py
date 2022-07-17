"""Handles routing, serving, and preparing pages."""
import os
from hashlib import blake2s
import functools
from flask import (Flask, render_template, request,
                   redirect, abort, url_for)
from waitress import serve
import analyze
import display as d
import update
import corefinder
from file_constants import DATA_DIR, TOP_FORMATS_FILE, THREAT_FILE

app = Flask(__name__)
app.config.from_object(__name__)
app.jinja_env.trim_blocks = True
app.jinja_env.lstrip_blocks = True
app.config['SECRET_KEY'] = 'DBE71E66D9EC317B7D2F13DB134F2'

@functools.lru_cache(maxsize=128, typed=False)
def get_md(dataset):
    """Get MetagameData object for a format."""
    try:
        return analyze.MetagameData(DATA_DIR + dataset + ".json",
                                    DATA_DIR + dataset + THREAT_FILE)
    except FileNotFoundError:
        abort(404)


@app.route("/", methods=['GET', 'POST'])
def select_data():
    """Page for selecting a format."""
    form = d.DataSelectForm(request.form)
    form.selector.choices = sorted([filename[:-5]
                                    for filename in os.listdir("datasets")
                                    if ".json" in filename])

    if request.method == 'POST':
        return redirect(url_for("analysis", dataset=request.form["selector"]))

    with open(DATA_DIR + TOP_FORMATS_FILE, encoding="utf-8") as f:
        top = f.read().splitlines()
        formats = []
        for metagame in top:
            format_name, ratings = metagame.split(" ")
            formats.append((format_name, ratings.split(",")))

    return render_template("DataSelector.html", form=form, top=formats)


@app.route("/pokemon/<dataset>/<poke>/")
def display_pokemon(dataset, poke):
    """Page for displaying data for a specific Pokemon."""
    md = get_md(dataset)
    if poke not in md.pokemon:
        abort(404)

    usage = f'{md.pokemon[poke]["usage"]:.1%}' # MOVE THIS FORMATTING TO FRONTEND

    counters = sorted(md.find_counters(poke).items(), key=lambda kv: -kv[1])
    teammates = sorted(md.partner_scores(poke).items(), key=lambda kv: -kv[1])
    count = md.count_pokemon(poke)
    items = sorted([(item[0], item[1]/count) for item in md.pokemon[poke]["Items"].items()],
                   key=lambda kv: -kv[1])
    moves = sorted([(m[0], m[1]/count) for m in md.pokemon[poke]["Moves"].items()],
                   key=lambda kv: -kv[1])
    abilities = sorted([(a[0], a[1]/count) for a in md.pokemon[poke]["Abilities"].items()],
                           key=lambda kv: -kv[1])

    return render_template("PokemonInfo.html",
                           poke=poke, dataset=dataset,
                           usage=usage,
                           counters=counters,
                           teammates=teammates, items=items,
                           moves=moves, abilities=abilities)


@app.route("/pokemon/<dataset>/")
def pokedex(dataset):
    """Page for listing all Pokemon in a format."""
    md = get_md(dataset)
    pokemon = sorted(md.pokemon.keys())
    return render_template("Pokedex.html", pokemon=pokemon, dataset=dataset)


@app.route("/items/<dataset>/<item>/")
def display_item(dataset, item):
    """Page for displaying information about an item."""
    md = get_md(dataset)

    holders = []
    for poke in md.pokemon:
        if item in md.pokemon[poke]["Items"]:
            hold = md.pokemon[poke]["Items"][item] / md.count_pokemon(poke)
            usage = md.pokemon[poke]["usage"]
            holders.append((poke, hold * usage, hold, usage))

    holders.sort(key=lambda h: -h[1])
    if not holders:
        abort(404)

    return render_template("ItemInfo.html",
                           item=item, dataset=dataset, holders=holders)


@app.route("/items/<dataset>/")
def item_dex(dataset):
    """Page for listing all items in a format."""
    md = get_md(dataset)

    items = set()
    for poke in md.pokemon:
        top_items = sorted(
            md.pokemon[poke]["Items"].items(), key=lambda kv: -kv[1])[:5]
        for item in top_items:
            items.add(item[0])

    return render_template("ItemDex.html",
                           items=sorted(list(items)), dataset=dataset)


@app.route("/moves/<dataset>/<move>/")
def display_move(dataset, move):
    """Page for information about a specific move."""
    md = get_md(dataset)

    users = []
    for poke in md.pokemon:
        if move in md.pokemon[poke]["Moves"]:
            use = md.pokemon[poke]["Moves"][move] / md.count_pokemon(poke)
            usage = md.pokemon[poke]["usage"]
            users.append((poke, use * usage, use, usage))

    users.sort(key=lambda u: -u[1])

    if not users:
        abort(404)

    return render_template("MoveInfo.html",
                           move=move, dataset=dataset, move_users=users)


@app.route("/moves/<dataset>/")
def move_dex(dataset):
    """Page that lists all moves in a format."""
    md = get_md(dataset)

    moves = set()
    for poke in md.pokemon:
        top_moves = sorted(
            md.pokemon[poke]["Moves"].items(), key=lambda kv: -kv[1])[:10]
        for move in top_moves:
            moves.add(move[0])

    display_moves = [m for m in sorted(list(moves)) if m]
    return render_template("MoveDex.html",
                           moves=display_moves, dataset=dataset)


@app.route("/abilities/<dataset>/<abil>/")
def display_ability(dataset, abil):
    """Page for details about a specific ability."""
    md = get_md(dataset)

    users = []
    for poke in md.pokemon:  # TODO move some of this into analyze?
        if abil in md.pokemon[poke]["Abilities"]:
            use = (md.pokemon[poke]["Abilities"][abil] /
                   md.count_pokemon(poke))
            usage = md.pokemon[poke]["usage"]
            users.append((poke, use * usage, use, usage))

    users.sort(key=lambda u: -u[1])

    if not users:
        abort(404)

    return render_template("AbilityInfo.html",
                           abil=abil, dataset=dataset, abil_users=users)


@app.route("/abilities/<dataset>/")
def ability_dex(dataset):
    """Page that lists all abilities in a format."""
    md = get_md(dataset)

    abils = set()
    for poke in md.pokemon:
        for abil in md.pokemon[poke]["Abilities"].items():
            if abil[1] / md.count_pokemon(poke) > .06:
                abils.add(abil[0])

    display_abils = [a for a in sorted(list(abils)) if a]
    return render_template("AbilityDex.html",
                           abilities=display_abils, dataset=dataset)


@app.route("/analysis/<dataset>/")
def analysis(dataset):
    """Page that contains the main team builder."""
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
    """Part of page responsible for displaying team building results."""
    md = get_md(dataset)

    my_pokes = []
    usage_setting = float(request.form["usage_setting"])
    counter_setting = float(request.form["counter_setting"])
    team_setting = float(request.form["team_setting"])

    for selector in request.form.items():
        if selector[1] and "selector" in selector[0]:
            my_pokes.append(selector[1])

    weights = analyze.Weights(counter_setting, team_setting, usage_setting)
    threats, bundled, suggested_team, swaps = md.analyze(my_pokes, weights)

    recommendations = sorted(bundled, key=lambda p: -p[1])

    return render_template("TeamBuilderAnalysis.html",
                           dataset=dataset,
                           threats=sorted(threats.items(), key=lambda k: -k[1]),
                           recommendations=recommendations,
                           suggested_team=suggested_team,
                           swaps=(swaps.items() if swaps else None),
                           add_links=(len(my_pokes) < 6))


@app.route("/cores/<dataset>/")
def cores(dataset):
    """Page for finding cores in a format."""
    return render_template("CoreFinder.html",
                           dataset=dataset, form=d.CoreFinderForm())


@app.route("/cores/<dataset>/find_cores", methods=['POST'])
def find_cores(dataset):
    """Part of page responsible for displaying cores in format."""
    md = get_md(dataset)

    usage_threshold = float(request.form["usage_threshold"])
    score_requirement = float(request.form["score_requirement"])
    cf = corefinder.CoreFinder(md, usage_threshold, score_requirement)

    return render_template("CoreFinderResults.html", dataset=dataset, cores=cf.find_cores())


@app.route("/update/<key>/")
def request_update(key):
    """Endpoint to download new statistics. Not for public use."""
    # This isn't real security,
    # but it's hopefully enough to prevent random people forcing updates.
    blake = blake2s()
    blake.update(key.encode())
    hex_result = blake.hexdigest()
    expected_hex = \
        '0a7758f62d5f8c069bf2a4c24fcb98dc23df90b738cb7ac1e792ed702c746fb8'

    if hex_result != expected_hex:
        abort(401)

    update.update()
    return "Update complete!"


if __name__ == "__main__":
    serve(app, host='0.0.0.0', port=int(os.environ.get("PORT", 8080)))
