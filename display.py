"""Contains tables, links, and forms that make up the UI."""

from wtforms import Form, SelectField, FieldList
from wtforms.fields import DecimalField
import analyze
import corefinder


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
    usage_threshold = DecimalField(default=corefinder.USAGE_THRESHOLD_DEFAULT, places=1)
    score_requirement = DecimalField(
        default=corefinder.SCORE_REQUIREMENT_DEFAULT)
