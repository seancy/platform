"""
Utilities for string manipulation.
"""

from django.core.validators import URLValidator
from django.core.exceptions import ValidationError


def str_to_bool(str):
    """
    Converts "true" (case-insensitive) to the boolean True.
    Everything else will return False (including None).

    An error will be thrown for non-string input (besides None).
    """
    return False if str is None else str.lower() == "true"


def _has_non_ascii_characters(data_string):
    """
    Check if provided string contains non ascii characters

    :param data_string: basestring or unicode object
    """
    try:
        data_string.encode('ascii')
    except UnicodeEncodeError:
        return True

    return False


def is_str_url(text):
    validator = URLValidator()
    try:
        validator(text)
        return True
    except ValidationError:
        return False
