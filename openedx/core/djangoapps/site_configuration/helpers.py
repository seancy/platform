"""
Helpers methods for site configuration.
"""
from django.conf import settings

from microsite_configuration import microsite


def get_current_site_configuration():
    """
    Return configuration for the current site.

    Returns:
         (openedx.core.djangoapps.site_configuration.models.SiteConfiguration): SiteConfiguration instance associated
         with the current site.
    """

    # Import is placed here to avoid circular import
    from openedx.core.djangoapps.theming.helpers import get_current_site
    site = get_current_site()

    # Import is placed here to avoid model import at project startup.
    from openedx.core.djangoapps.site_configuration.models import SiteConfiguration
    try:
        return getattr(site, "configuration", None)
    except SiteConfiguration.DoesNotExist:
        return None


def is_site_configuration_enabled():
    """
    Returns True is there is SiteConfiguration instance associated with the current site and it is enabled, otherwise
    returns False.

    Returns:
        (bool): True if SiteConfiguration is present and enabled, False otherwise
    """
    configuration = get_current_site_configuration()
    if configuration:
        return configuration.enabled
    return False


def has_configuration_override(name):
    """
    Returns True/False whether a Site Configuration has a definition for the
    specified key.

    Args:
       name (str): Name of the configuration dict to retrieve.

    Returns:
        (bool): True if given key is present in the configuration.
    """
    configuration = get_current_site_configuration()
    if configuration and name in configuration.values:
        return True
    return False


def get_configuration_value(name, default=None):
    """
    Return Configuration value for the key specified as name argument.

    Args:
        name (str): Name of the key for which to return configuration value.
        default: default value tp return if key is not found in the configuration

    Returns:
        Configuration value for the given key or returns `None` if configuration is not enabled.
    """
    configuration = get_current_site_configuration()
    if configuration:
        return configuration.get_value(name, default)
    return default


def get_configuration_dict(name, default=None):
    """
    Returns a dictionary product after merging the current site's configuration and
    the default value.

    Args:
        name (str): Name of the configuration dict to retrieve.
        default (dict): default dict containing key-value pairs of default values.

    Returns:
        Configuration value for the given key or returns `{}` if configuration is not enabled.
    """

    default = default or {}
    output = default.copy()
    output.update(
        get_configuration_value(name, {}) or {},
    )

    return output


def get_value(val_name, default=None, **kwargs):
    """
    Return configuration value for the key specified as name argument.

    Args:
        val_name (str): Name of the key for which to return configuration value.
        default: default value tp return if key is not found in the configuration

    Returns:
        Configuration/Microsite value for the given key.
    """

    if is_site_configuration_enabled():
        # Retrieve the requested field/value from the site configuration
        configuration_value = get_configuration_value(val_name, default=default)
    else:
        # Retrieve the requested field/value from the microsite configuration
        configuration_value = microsite.get_value(val_name, default=default, **kwargs)

    # Attempt to perform a dictionary update using the provided default
    # This will fail if either the default or the microsite value is not a dictionary
    try:
        value = dict(default)
        value.update(configuration_value)

    # If the dictionary update fails, just use the microsite value
    # TypeError: default is not iterable (simple value or None)
    # ValueError: default is iterable but not a dict (list, not dict)
    # AttributeError: default does not have an 'update' method
    except (TypeError, ValueError, AttributeError):
        value = configuration_value

    # Return the end result to the caller
    return value


def get_dict(name, default=None):
    """
    Returns a dictionary product after merging configuration and
    the default value.

    Args:
        name (str): Name of the configuration dict to retrieve.
        default (dict): default dict containing key-value pairs of default values.

    Returns:
        Configuration value for the given key or returns `{}` if configuration not found.
    """
    default = default or {}

    if is_site_configuration_enabled():
        return get_configuration_dict(name, default)
    else:
        return microsite.get_dict(name, default)


def has_override_value(name):
    """
    Returns True/False whether configuration has a definition for the
    specified key.

    Args:
       name (str): Name of the configuration dict to retrieve.

    Returns:
        (bool): True if given key is present in the configuration.
    """
    if is_site_configuration_enabled():
        return has_configuration_override(name)
    else:
        return microsite.has_override_value(name)


def get_value_for_org(org, val_name, default=None):
    """
    This returns a configuration value for a site configuration or microsite configuration
    which has an org_filter that matches with the argument.

    Args:
        org (str): Course org filter, this value will be used to filter out the correct site configuration.
        name (str): Name of the key for which to return configuration value.
        default: default value to return if key is not present in the configuration

    Returns:
        Configuration value for the given key.

    """
    # Here we first look for the asked org inside site configuration, and if org is not present in site configuration
    # then we go ahead and look it inside microsite configuration.
    # Import is placed here to avoid model import at project startup.
    from openedx.core.djangoapps.site_configuration.models import SiteConfiguration
    if SiteConfiguration.has_org(org):
        return SiteConfiguration.get_value_for_org(org, val_name, default)
    else:
        return microsite.get_value_for_org(org, val_name, default)


def get_current_site_orgs():
    """
    This returns the orgs configured in site configuration or microsite configuration for the current site.

    Returns:
        list: A list of organization names.
    """
    course_org_filter = get_value('course_org_filter')
    # Make sure we have a list
    if course_org_filter and not isinstance(course_org_filter, list):
        course_org_filter = [course_org_filter]
    return sorted(course_org_filter) if course_org_filter else None


def get_all_orgs():
    """
    This returns all of the orgs that are considered in site configurations or microsite configuration,
    This can be used, for example, to do filtering.

    Returns:
        A list of all organizations present in either microsite configuration or site configuration.
    """
    # Import is placed here to avoid model import at project startup.
    from openedx.core.djangoapps.site_configuration.models import SiteConfiguration
    site_configuration_orgs = SiteConfiguration.get_all_orgs()
    microsite_orgs = microsite.get_all_orgs()

    return site_configuration_orgs.union(microsite_orgs)


def page_title_breadcrumbs(*crumbs, **kwargs):
    """
    This function creates a suitable page title in the form:
    Specific | Less Specific | General | edX
    It will output the correct platform name for the request.
    Pass in a `separator` kwarg to override the default of " | "
    """
    platform_name = get_value('PLATFORM_NAME', settings.PLATFORM_NAME)
    separator = kwargs.get("separator", " | ")
    crumbs = [c for c in crumbs if c is not None]
    if crumbs:
        return u'{}{}{}'.format(separator.join(crumbs), separator, platform_name)
    else:
        return platform_name
