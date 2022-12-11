"""Contains tables, links, and forms that make up the UI."""

from wtforms import Form, SelectField, FieldList
from wtforms.fields import DecimalField
import analyze
import corefinder

class CoreFinderForm(Form):
    """Form to select settings for core finding."""
    usage_threshold = DecimalField(default=corefinder.USAGE_THRESHOLD_DEFAULT, places=1)
    score_requirement = DecimalField(
        default=corefinder.SCORE_REQUIREMENT_DEFAULT)
