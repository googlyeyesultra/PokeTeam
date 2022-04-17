"""Contains tables, links, and forms that make up the UI."""

from flask import Markup, url_for
from flask_table import Table, Col
from wtforms import Form, SelectField, FieldList
from wtforms.fields import DecimalField
import analyze
import corefinder

_MAX_TABLE_LEN = 10

class PokemonForm(Form):
    """Form containing Pokemon selectors and weightings for analysis."""
    selectors = FieldList(SelectField(), min_entries=6)
    usage_setting = DecimalField(default=analyze.USAGE_WEIGHT_DEFAULT)
    counter_setting = DecimalField(default=analyze.COUNTER_WEIGHT_DEFAULT)
    team_setting = DecimalField(default=analyze.TEAM_WEIGHT_DEFAULT)


class DataSelectForm(Form):
    """Form to select which metagame to work with."""
    selector = SelectField()


class CoreFinderForm(Form):
    """Form to select settings for core finding."""
    usage_threshold = DecimalField(default=corefinder.USAGE_THRESHOLD_DEFAULT)
    score_requirement = DecimalField(
        default=corefinder.SCORE_REQUIREMENT_DEFAULT)


class FloatCol(Col):  # Just truncates floats down a bit.
    """Generic float table column. Truncates floats."""
    def td_format(self, content):
        return f"{content:.2f}"


class PercentCol(Col):
    """Generic percent table column."""
    def td_format(self, content):
        return f"{content:.0%}"


class ThreatsTable(Table):
    """Table that renders top threats."""
    poke = Col("Threat")
    rating = FloatCol("Rating", column_html_attrs={"align": "right"})
    classes = ["data-table"]

    def __init__(self, threats, dataset):
        threats_to_display = sorted(threats.items(), key=lambda k: -k[1])[:_MAX_TABLE_LEN]
        threats_to_display = [(link_for_poke(dataset, t[0]), t[1])
                              for t in threats_to_display]
        super().__init__([dict(zip(["poke", "rating"], t))
                          for t in threats_to_display])


class CountersTable(Table):
    """Table that lists counters to a given Pokemon."""
    poke = Col("Counter")
    rating = FloatCol("Rating", column_html_attrs={"align": "right"})
    classes = ["data-table"]

    def __init__(self, poke, md, dataset):
        dict_threats = md.find_counters(poke)
        counters_to_display = sorted(
            dict_threats.items(), key=lambda k: -k[1])[:_MAX_TABLE_LEN]
        counters_to_display = [(link_for_poke(dataset, c[0]), c[1])
                               for c in counters_to_display]
        super().__init__([dict(zip(["poke", "rating"], t))
                          for t in counters_to_display])


class TeamTable(Table):
    """Table that renders top teammates for a given Pokemon."""
    poke = Col("Teammate")
    rating = FloatCol("Rating", column_html_attrs={"align": "right"})
    classes = ["data-table"]

    def __init__(self, poke, md, dataset):
        teammates = md.partner_scores(poke)
        teammates_to_display = sorted(teammates.items(),
                                      key=lambda k: -k[1])[:_MAX_TABLE_LEN]
        teammates_to_display = [(link_for_poke(dataset, t[0]), t[1])
                                for t in teammates_to_display]
        super().__init__([dict(zip(["poke", "rating"], t))
                          for t in teammates_to_display])


class ItemsTable(Table):
    """Table that shows what items a Pokemon uses."""
    item = Col("Item")
    usage = PercentCol("Usage", column_html_attrs={"align": "right"})
    classes = ["data-table"]

    def __init__(self, poke, md, dataset):
        count = md.count_pokemon(poke)  # TODO move some of this into analyze?
        items = sorted([(link_for_item(dataset, item[0]), item[1]/count)
                       for item in md.pokemon[poke]["Items"].items()],
                       key=lambda kv: -kv[1])[:5]
        super().__init__([dict(zip(["item", "usage"], t)) for t in items])


class AbilitiesTable(Table):
    """Table that shows what abilities a Pokemon uses."""
    abil = Col("Ability")
    usage = PercentCol("Usage", column_html_attrs={"align": "right"})
    classes = ["data-table"]

    def __init__(self, poke, md, dataset):
        count = md.count_pokemon(poke)  # TODO move some of this into analyze?
        abilities = sorted([(link_for_ability(dataset, a[0]), a[1]/count)
                           for a in md.pokemon[poke]["Abilities"].items()],
                           key=lambda kv: -kv[1])[:5]
        super().__init__([dict(zip(["abil", "usage"], t)) for t in abilities])


class MovesTable(Table):
    """Table that shows what moves a Pokemon uses."""
    move = Col("Move")
    usage = PercentCol("Usage", column_html_attrs={"align": "right"})
    classes = ["data-table"]

    def __init__(self, poke, md, dataset):
        count = md.count_pokemon(poke)  # TODO move some of this into analyze?
        moves = sorted([(link_for_move(dataset, move[0]), move[1]/count)
                       for move in md.pokemon[poke]["Moves"].items()],
                       key=lambda kv: -kv[1])[:_MAX_TABLE_LEN]
        super().__init__([dict(zip(["move", "usage"], t)) for t in moves])


class ItemHoldersTable(Table):
    """Table that shows what Pokemon use a given item."""
    holder = Col("Holder")
    combined = PercentCol(
        "Combined Usage", column_html_attrs={"align": "right"})
    hold_percent = PercentCol(
        "Item Usage", column_html_attrs={"align": "right"})
    usage = PercentCol("Pokemon Usage", column_html_attrs={"align": "right"})
    classes = ["data-table"]

    def __init__(self, item, md, dataset):
        holders = [] # TODO move some of this into analyze?
        for poke in md.pokemon:
            if item in md.pokemon[poke]["Items"]:
                hold = md.pokemon[poke]["Items"][item] / md.count_pokemon(poke)
                usage = md.pokemon[poke]["usage"]
                holders.append((link_for_poke(dataset, poke),
                               hold * usage, hold, usage))

        holders = sorted(holders, key=lambda h: -h[1])[:_MAX_TABLE_LEN]

        fields = ["holder", "combined", "hold_percent", "usage"]
        super().__init__([dict(zip(fields, h)) for h in holders])


class MoveUsersTable(Table):
    """Table that shows what Pokemon use a given move."""
    user = Col("User")
    combined = PercentCol(
        "Combined Usage", column_html_attrs={"align": "right"})
    use_percent = PercentCol(
        "Move Usage", column_html_attrs={"align": "right"})
    usage = PercentCol("Pokemon Usage", column_html_attrs={"align": "right"})
    classes = ["data-table"]

    def __init__(self, move, md, dataset):
        users = []
        for poke in md.pokemon:  # TODO move some of this into analyze?
            if move in md.pokemon[poke]["Moves"]:
                use = md.pokemon[poke]["Moves"][move] / md.count_pokemon(poke)
                usage = md.pokemon[poke]["usage"]
                users.append((link_for_poke(dataset, poke),
                             use * usage, use, usage))

        users = sorted(users, key=lambda u: -u[1])[:_MAX_TABLE_LEN]

        fields = ["user", "combined", "use_percent", "usage"]
        super().__init__([dict(zip(fields, u)) for u in users])


class AbilityUsersTable(Table):
    """Table that shows what Pokemon use a given ability."""
    user = Col("User")
    combined = PercentCol(
        "Combined Usage", column_html_attrs={"align": "right"})
    use_percent = PercentCol(
        "Ability Usage", column_html_attrs={"align": "right"})
    usage = PercentCol("Pokemon Usage", column_html_attrs={"align": "right"})
    classes = ["data-table"]

    def __init__(self, abil, md, dataset):
        users = []
        for poke in md.pokemon:  # TODO move some of this into analyze?
            if abil in md.pokemon[poke]["Abilities"]:
                use = (md.pokemon[poke]["Abilities"][abil] /
                       md.count_pokemon(poke))
                usage = md.pokemon[poke]["usage"]
                users.append((link_for_poke(dataset, poke),
                             use * usage, use, usage))

        users = sorted(users, key=lambda u: -u[1])[:_MAX_TABLE_LEN]

        fields = ["user", "combined", "use_percent", "usage"]
        super().__init__([dict(zip(fields, u)) for u in users])


class RecommendationsTable(Table):
    """Table that provides recommendations for a team."""
    poke = Col("Recommendations")
    overall = FloatCol("Overall Score")
    counter = FloatCol("Counter Score")
    team = FloatCol("Team Score")
    usage = FloatCol("Usage Score")
    classes = ["data-table"]

    @staticmethod
    def add_link(poke):
        """Build link to add the Pokemon to the team."""
        return Markup(
            f'<a href="javascript:handleAddPoke(\'{poke}\')"'
            f'class="add_link" id="{poke}">'
            '<span class="fas fa-plus-square"></span></a>')

    def __init__(self, bundled, dataset, include_add_link):
        reco_to_display = sorted([(link_for_poke(dataset, x[0]),
                                   x[1][0],
                                   x[1][1],
                                   x[1][2],
                                   x[1][3],
                                   RecommendationsTable.add_link(x[0]))
                                  for x in bundled.items()],
                                 key=lambda k: -k[1])[:_MAX_TABLE_LEN]
        fields = ["poke", "overall", "counter", "team", "usage", "add"]
        self.add_column("add", Col("+", show=include_add_link))
        super().__init__([dict(zip(fields, r)) for r in reco_to_display])

def link_for_analysis(format_name, rating):
    """Build link for team analysis page for a given format."""
    dataset = format_name + "-" + rating
    url = url_for("analysis", dataset=dataset)
    return Markup(f'<a href="{url}">{rating}</a>')

def link_for_poke(dataset, poke):
    """Build link for a Pokemon page within given dataset."""
    url = url_for("display_pokemon", dataset=dataset, poke=poke)
    return Markup(f'<a href="{url}"><span class="poke-icon" data-poke="{poke}">'
                  f'</span>{poke}</a>')

def link_for_item(dataset, item):
    """Build link for an item page within given dataset."""
    url = url_for("display_item", dataset=dataset, item=item)
    return Markup(f'<a href="{url}"><span class="item-icon" data-item="{item}">'
                  f'</span><span class="item-name" data-item="{item}">{item}</span></a>')

def link_for_move(dataset, move):
    """Build link for a move page within given dataset."""
    url = url_for("display_move", dataset=dataset, move=move)
    return Markup(f'<a href="{url}"><span class="move-name" data-move="{move}">{move}</span></a>')

def link_for_ability(dataset, abil):
    """Build link for an ability page within given dataset."""
    url = url_for("display_ability", dataset=dataset, ability=abil)
    return Markup(f'<a href="{url}"><span class="abil-name" data-abil="{abil}">{abil}</span></a>')
