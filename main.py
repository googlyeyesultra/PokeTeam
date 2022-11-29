"""Handles routing, serving, and preparing pages."""
import os
import functools

from botocore.exceptions import ClientError
from flask import (Flask, render_template, request,
                   redirect, abort, url_for)
import boto3
from waitress import serve
import analyze
import display as d
import update
import corefinder
import dex
from file_constants import *

app = Flask(__name__)
app.config.from_object(__name__)
app.jinja_env.trim_blocks = True
app.jinja_env.lstrip_blocks = True
app.config["SECRET_KEY"] = os.environ["FLASK_SECRET_KEY"]

s3_session = boto3.session.Session(aws_access_key_id=os.environ["S3_ACCESS_KEY"],
                                   aws_secret_access_key=os.environ["S3_SECRET_KEY"])
s3_bucket = s3_session.resource("s3", endpoint_url=os.environ["S3_ENDPOINT"]).Bucket(os.environ["BUCKET"])


@functools.lru_cache(maxsize=64, typed=False)
def get_md(dataset):
    """Get MetagameData object for a format."""
    try:
        if not os.path.exists(DATA_DIR + dataset + ".json"):
            s3_bucket.download_file(dataset + ".json", DATA_DIR + dataset + ".json")
        if not os.path.exists(DATA_DIR + dataset + THREAT_FILE):
            s3_bucket.download_file(dataset + THREAT_FILE, DATA_DIR + dataset + THREAT_FILE)
        if not os.path.exists(DATA_DIR + dataset + TEAMMATE_FILE):
            s3_bucket.download_file(dataset + TEAMMATE_FILE, DATA_DIR + dataset + TEAMMATE_FILE)
        return analyze.MetagameData(DATA_DIR + dataset + ".json",
                                    DATA_DIR + dataset + THREAT_FILE,
                                    DATA_DIR + dataset + TEAMMATE_FILE)
    except (FileNotFoundError, ClientError):
        abort(404)

@functools.lru_cache(maxsize=12, typed=False)
def get_dex(gen):
    """Get generation appropriate dex for a format."""
    return dex.Dex(DATA_DIR + DEX_PREFIX + gen + DEX_SUFFIX)

@app.route("/", methods=['GET', 'POST'])
def select_data():
    """Page for selecting a format."""
    if request.method == 'POST':
        return redirect(url_for("analysis", dataset=request.form["selector"]))

    form = d.DataSelectForm(request.form)
    datasets = [obj.key[:-5] for obj in s3_bucket.objects.all()
                if ".json" in obj.key]
    form.selector.choices = sorted(datasets)

    if not os.path.exists(DATA_DIR + TOP_FORMATS_FILE):
        s3_bucket.download_file(TOP_FORMATS_FILE, DATA_DIR + TOP_FORMATS_FILE)

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

    usage = f'{md.pokemon[poke]["usage"]:.1%}'  # TODO MOVE THIS FORMATTING TO FRONTEND

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
                           moves=moves, abilities=abilities,
                           gen=md.gen,
                           dex=get_dex(md.gen))


@app.route("/pokemon/<dataset>/")
def pokedex(dataset):
    """Page for listing all Pokemon in a format."""
    md = get_md(dataset)
    pokemon = sorted([(x, md.pokemon[x]["usage"]) for x in md.pokemon.keys()], key=lambda pair: -pair[1])
    return render_template("Pokedex.html", pokemon=pokemon, dataset=dataset, gen=md.gen, dex=get_dex(md.gen))


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
                           item=item, dataset=dataset, holders=holders,
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
                           move=move, dataset=dataset, move_users=users,
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
                           abil=abil, dataset=dataset, abil_users=users,
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

    return render_template('TeamBuilder.html', form=form, dataset=dataset,
                           gen=md.gen, dex=get_dex(md.gen))


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
                           swaps=(sorted(swaps.items(), key=lambda kv: -kv[1][1]) if swaps else None),
                           add_links=(len(my_pokes) < 6),
                           gen=md.gen, dex=get_dex(md.gen))


@app.route("/cores/<dataset>/")
def cores(dataset):
    """Page for finding cores in a format."""
    return render_template("CoreFinder.html",
                           dataset=dataset, form=d.CoreFinderForm())


@app.route("/cores/<dataset>/find_cores", methods=['POST'])
def find_cores(dataset):
    """Part of page responsible for displaying cores in format."""
    md = get_md(dataset)

    usage_threshold = float(request.form["usage_threshold"]) / 100
    score_requirement = float(request.form["score_requirement"])
    cf = corefinder.CoreFinder(md, usage_threshold, score_requirement)

    return render_template("CoreFinderResults.html", dataset=dataset, cores=cf.find_cores(),
                           gen=md.gen, dex=get_dex(md.gen))


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
    serve(app, host='0.0.0.0', port=int(os.environ["PORT"]))
