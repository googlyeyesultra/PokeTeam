from flask import Markup, url_for
from flask_table import Table, Col
from wtforms import Form, SelectField, FieldList
from wtforms.fields.html5 import DecimalField
import analyze
import corefinder

class PokemonForm(Form):
  selectors = FieldList(SelectField(), min_entries=6)
  usage_setting = DecimalField(default=analyze.usage_weight_default)
  counter_setting = DecimalField(default=analyze.counters_weight_default)
  team_setting = DecimalField(default=analyze.team_weight_default)

class DataSelectForm(Form):
  selector = SelectField()

class CoreFinderForm(Form):
  usage_threshold = DecimalField(default=corefinder.usage_threshold_default)
  score_requirement = DecimalField(default=corefinder.score_requirement_default)

class FloatCol(Col): # Just truncates floats down a bit.
  def td_format(self, content):
    return "{:.2f}".format(content)

class PercentCol(Col):
  def td_format(self, content):
    return "{:.0%}".format(content)

class ThreatsTable(Table):
  poke = Col("Threat")
  rating = FloatCol("Rating", column_html_attrs = {"align": "right"})

  def __init__(self, threats, dataset):
    threats_to_display = sorted(threats.items(), key=lambda k: -k[1])[:10]
    threats_to_display = [(link_for_poke(dataset, t[0]), t[1]) for t in threats_to_display]
    super().__init__([dict(zip(["poke", "rating"], t)) for t in threats_to_display])

class CountersTable(Table):
  poke = Col("Counter")
  rating = FloatCol("Rating", column_html_attrs = {"align": "right"})

  def __init__(self, poke, md, dataset):
    counters = md.find_threats([poke])
    dict_threats = md.threats_to_dict(counters, 1)
    counters_to_display = sorted(dict_threats.items(), key=lambda k: -k[1])[:10]
    counters_to_display = [(link_for_poke(dataset, c[0]), c[1]) for c in counters_to_display]
    super().__init__([dict(zip(["poke", "rating"], t)) for t in counters_to_display])

class TeamTable(Table):
  poke = Col("Teammate")
  rating = FloatCol("Rating", column_html_attrs = {"align": "right"})

  def __init__(self, poke, md, dataset):
    teammates = {}
    for mon in md.pokemon:
      teammates[mon] = md.get_team_score([poke], mon) * md.get_usage_score(mon)

    teammates_to_display = sorted(teammates.items(), key=lambda k: -k[1])[:10]
    teammates_to_display = [(link_for_poke(dataset, t[0]), t[1]) for t in teammates_to_display]
    super().__init__([dict(zip(["poke", "rating"], t)) for t in teammates_to_display])

class ItemsTable(Table):
  item = Col("Item")
  usage = PercentCol("Usage", column_html_attrs = {"align": "right"})

  def __init__(self, poke, md, dataset):
    count = md.count_pokemon(poke)
    items = sorted([(link_for_item(dataset, item[0]), item[1]/count) for item in md.pokemon[poke]["Items"].items()], key=lambda kv: -kv[1])[:5]
    super().__init__([dict(zip(["item", "usage"], t)) for t in items])

class AbilitiesTable(Table):
  abil = Col("Ability")
  usage = PercentCol("Usage", column_html_attrs = {"align": "right"})

  def __init__(self, poke, md, dataset):
    count = md.count_pokemon(poke)
    abilities = sorted([(link_for_ability(dataset, a[0]), a[1]/count) for a in md.pokemon[poke]["Abilities"].items()], key=lambda kv: -kv[1])[:5]
    super().__init__([dict(zip(["abil", "usage"], t)) for t in abilities])

class MovesTable(Table):
  move = Col("Move")
  usage = PercentCol("Usage", column_html_attrs = {"align": "right"})

  def __init__(self, poke, md, dataset):
    count = md.count_pokemon(poke)
    moves = sorted([(link_for_move(dataset, move[0]), move[1]/count) for move in md.pokemon[poke]["Moves"].items()], key=lambda kv: -kv[1])[:10]
    super().__init__([dict(zip(["move", "usage"], t)) for t in moves])

class ItemHoldersTable(Table):
  holder = Col("Holder")
  combined = PercentCol("Combined Usage", column_html_attrs = {"align": "right"})
  hold_percent = PercentCol("Item Usage", column_html_attrs = {"align": "right"})
  usage = PercentCol("Pokemon Usage", column_html_attrs = {"align": "right"})

  def __init__(self, item, md, dataset):
    holders = []
    for poke in md.pokemon:
      if item in md.pokemon[poke]["Items"]:
        hold = md.pokemon[poke]["Items"][item] / md.count_pokemon(poke)
        usage = md.pokemon[poke]["usage"]
        holders.append((link_for_poke(dataset, poke), hold * usage, hold, usage))

    holders = sorted(holders, key=lambda h: -h[1])[:10]

    fields = ["holder", "combined", "hold_percent", "usage"]
    super().__init__([dict(zip(fields, h)) for h in holders])

class MoveUsersTable(Table):
  user = Col("User")
  combined = PercentCol("Combined Usage", column_html_attrs = {"align": "right"})
  use_percent = PercentCol("Move Usage", column_html_attrs = {"align": "right"})
  usage = PercentCol("Pokemon Usage", column_html_attrs = {"align": "right"})

  def __init__(self, move, md, dataset):
    users = []
    for poke in md.pokemon:
      if move in md.pokemon[poke]["Moves"]:
        use = md.pokemon[poke]["Moves"][move] / md.count_pokemon(poke)
        usage = md.pokemon[poke]["usage"]
        users.append((link_for_poke(dataset, poke), use * usage, use, usage))

    users = sorted(users, key=lambda u: -u[1])[:10]

    fields = ["user", "combined", "use_percent", "usage"]
    super().__init__([dict(zip(fields, u)) for u in users])

class AbilityUsersTable(Table):
  user = Col("User")
  combined = PercentCol("Combined Usage", column_html_attrs = {"align": "right"})
  use_percent = PercentCol("Ability Usage", column_html_attrs = {"align": "right"})
  usage = PercentCol("Pokemon Usage", column_html_attrs = {"align": "right"})

  def __init__(self, abil, md, dataset):
    users = []
    for poke in md.pokemon:
      if abil in md.pokemon[poke]["Abilities"]:
        use = md.pokemon[poke]["Abilities"][abil] / md.count_pokemon(poke)
        usage = md.pokemon[poke]["usage"]
        users.append((link_for_poke(dataset, poke), use * usage, use, usage))

    users = sorted(users, key=lambda u: -u[1])[:10]

    fields = ["user", "combined", "use_percent", "usage"]
    super().__init__([dict(zip(fields, u)) for u in users])

class RecommendationsTable(Table):
  poke = Col("Recommendations")
  overall = FloatCol("Overall Score")
  counters = FloatCol("Counters Score")
  team = FloatCol("Team Score")
  usage = FloatCol("Usage Score")

  def add_link(poke):
    return Markup('<a href="javascript:handleAddPoke(\'{0}\')" class="add_link" id="{0}"><span class="fas fa-plus-square"></span></a>'.format(poke))

  def __init__(self, bundled, dataset, include_add_link):
    reco_to_display = sorted([(link_for_poke(dataset, x[0]), x[1][0], x[1][1], x[1][2], x[1][3], RecommendationsTable.add_link(x[0])) for x in bundled.items()], key=lambda k: -k[1])[:10]
    fields = ["poke", "overall", "counters", "team", "usage", "add"]
    self.add_column("add", Col("+", show=include_add_link))
    super().__init__([dict(zip(fields, r)) for r in reco_to_display])

def link_for_analysis(format_name, rating):
  dataset = format_name + "-" + rating
  return Markup('<a href="{}">{}</a>'.format(url_for("analysis", dataset=dataset), rating))

def link_for_poke(dataset, poke):
  return Markup('<a href="{}">{}</a>'.format(url_for("display_pokemon", dataset=dataset, poke=poke), poke))

def link_for_item(dataset, item):
  return Markup('<a href="{}">{}</a>'.format(url_for("display_item", dataset=dataset, item=item), item))

def link_for_move(dataset, move):
  return Markup('<a href="{}">{}</a>'.format(url_for("display_move", dataset=dataset, move=move), move))

def link_for_ability(dataset, abil):
  return Markup('<a href="{}">{}</a>'.format(url_for("display_ability", dataset=dataset, ability=abil), abil))