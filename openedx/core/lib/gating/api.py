"""
API for the gating djangoapp
"""
import json
import logging
import sys

from django.contrib.auth.models import User
from django.db.models import signals
from django.urls import reverse
from django.utils.translation import ugettext as _

from completion.models import BlockCompletion
from completion import waffle as completion_waffle
from lms.djangoapps.courseware.access import _has_access_to_course
from lms.djangoapps.course_blocks.api import get_course_blocks
from lms.djangoapps.grades.models import PersistentSubsectionGradeOverride
from lms.djangoapps.grades.subsection_grade_factory import SubsectionGradeFactory
from milestones import api as milestones_api
from opaque_keys.edx.keys import UsageKey
from openedx.core.lib.gating.exceptions import GatingValidationError
from util import milestones_helpers
from xmodule.modulestore.django import modulestore
from xmodule.modulestore.exceptions import ItemNotFoundError

log = logging.getLogger(__name__)

# This is used to namespace gating-specific milestones
GATING_NAMESPACE_QUALIFIER = '.gating'


def _get_prerequisite_milestone(prereq_content_key):
    """
    Get gating milestone associated with the given content usage key.

    Arguments:
        prereq_content_key (str|UsageKey): The content usage key

    Returns:
        dict: Milestone dict
    """
    milestones = milestones_api.get_milestones("{usage_key}{qualifier}".format(
        usage_key=prereq_content_key,
        qualifier=GATING_NAMESPACE_QUALIFIER
    ))

    if not milestones:
        log.warning("Could not find gating milestone for prereq UsageKey %s", prereq_content_key)
        return None

    if len(milestones) > 1:
        # We should only ever have one gating milestone per UsageKey
        # Log a warning here and pick the first one
        log.warning("Multiple gating milestones found for prereq UsageKey %s", prereq_content_key)

    return milestones[0]


def _validate_min_score(min_score):
    """
    Validates the minimum score entered by the Studio user.

    Arguments:
        min_score (str|int): The minimum score to validate

    Returns:
        None

    Raises:
        GatingValidationError: If the minimum score is not valid
    """
    if min_score:
        message = _("%(min_score)s is not a valid grade percentage") % {'min_score': min_score}
        try:
            min_score = int(min_score)
        except ValueError:
            raise GatingValidationError(message)

        if min_score < 0 or min_score > 100:
            raise GatingValidationError(message)


def gating_enabled(default=None):
    """
    Decorator that checks the enable_subsection_gating course flag to
    see if the subsection gating feature is active for a given course.
    If not, calls to the decorated function return the specified default value.

    Arguments:
        default (ANY): The value to return if the enable_subsection_gating course flag is False

    Returns:
        ANY: The specified default value if the gating feature is off,
        otherwise the result of the decorated function
    """
    def wrap(f):  # pylint: disable=missing-docstring
        def function_wrapper(course, *args):  # pylint: disable=missing-docstring
            if not course.enable_subsection_gating:
                return default
            return f(course, *args)
        return function_wrapper
    return wrap


def find_gating_milestones(course_key, content_key=None, relationship=None, user=None):
    """
    Finds gating milestone dicts related to the given supplied parameters.

    Arguments:
        course_key (str|CourseKey): The course key
        content_key (str|UsageKey): The content usage key
        relationship (str): The relationship type (e.g. 'requires')
        user (dict): The user dict (e.g. {'id': 4})

    Returns:
        list: A list of milestone dicts
    """
    return [
        m for m in milestones_api.get_course_content_milestones(course_key, content_key, relationship, user)
        if GATING_NAMESPACE_QUALIFIER in m.get('namespace')
    ]


def get_gating_milestone(course_key, content_key, relationship):
    """
    Gets a single gating milestone dict related to the given supplied parameters.

    Arguments:
        course_key (str|CourseKey): The course key
        content_key (str|UsageKey): The content usage key
        relationship (str): The relationship type (e.g. 'requires')

    Returns:
        dict or None: The gating milestone dict or None
    """
    try:
        return find_gating_milestones(course_key, content_key, relationship)[0]
    except IndexError:
        return None


def get_prerequisites(course_key):
    """
    Find all the gating milestones associated with a course and the
    XBlock info associated with those gating milestones.

    Arguments:
        course_key (str|CourseKey): The course key

    Returns:
        list: A list of dicts containing the milestone and associated XBlock info
    """
    course_content_milestones = find_gating_milestones(course_key)

    milestones_by_block_id = {}
    block_ids = []
    for milestone in course_content_milestones:
        prereq_content_key = _get_gating_block_id(milestone)
        block_id = UsageKey.from_string(prereq_content_key).block_id
        block_ids.append(block_id)
        milestones_by_block_id[block_id] = milestone

    result = []
    for block in modulestore().get_items(course_key, qualifiers={'name': block_ids}):
        milestone = milestones_by_block_id.get(block.location.block_id)
        if milestone:
            milestone['block_display_name'] = block.display_name
            milestone['block_usage_key'] = unicode(block.location)
            result.append(milestone)

    return result


def add_prerequisite(course_key, prereq_content_key):
    """
    Creates a new Milestone and CourseContentMilestone indicating that
    the given course content fulfills a prerequisite for gating

    Arguments:
        course_key (str|CourseKey): The course key
        prereq_content_key (str|UsageKey): The prerequisite content usage key

    Returns:
        None
    """
    milestone = milestones_api.add_milestone(
        {
            'name': _('Gating milestone for {usage_key}').format(usage_key=unicode(prereq_content_key)),
            'namespace': "{usage_key}{qualifier}".format(
                usage_key=prereq_content_key,
                qualifier=GATING_NAMESPACE_QUALIFIER
            ),
            'description': _('System defined milestone'),
        },
        propagate=False
    )
    milestones_api.add_course_content_milestone(course_key, prereq_content_key, 'fulfills', milestone)


def remove_prerequisite(prereq_content_key):
    """
    Removes the Milestone and CourseContentMilestones related to the gating
    prerequisite which the given course content fulfills

    Arguments:
        prereq_content_key (str|UsageKey): The prerequisite content usage key

    Returns:
        None
    """
    milestones = milestones_api.get_milestones("{usage_key}{qualifier}".format(
        usage_key=prereq_content_key,
        qualifier=GATING_NAMESPACE_QUALIFIER
    ))
    for milestone in milestones:
        milestones_api.remove_milestone(milestone.get('id'))


def is_prerequisite(course_key, prereq_content_key):
    """
    Returns True if there is at least one CourseContentMilestone
    which the given course content fulfills

    Arguments:
        course_key (str|CourseKey): The course key
        prereq_content_key (str|UsageKey): The prerequisite content usage key

    Returns:
        bool: True if the course content fulfills a CourseContentMilestone, otherwise False
    """
    return get_gating_milestone(
        course_key,
        prereq_content_key,
        'fulfills'
    ) is not None


def set_required_content(course_key, gated_content_key, prereq_content_key, min_score='', min_completion=''):
    """
    Adds a `requires` milestone relationship for the given gated_content_key if a prerequisite
    prereq_content_key is provided. If prereq_content_key is None, removes the `requires`
    milestone relationship.

    Arguments:
        course_key (str|CourseKey): The course key
        gated_content_key (str|UsageKey): The gated content usage key
        prereq_content_key (str|UsageKey): The prerequisite content usage key
        min_score (str|int): The minimum score
        min_completion (str|int): The minimum completion percentage

    Returns:
        None
    """
    milestone = None
    for gating_milestone in find_gating_milestones(course_key, gated_content_key, 'requires'):
        if not prereq_content_key or prereq_content_key not in gating_milestone.get('namespace'):
            milestones_api.remove_course_content_milestone(course_key, gated_content_key, gating_milestone)
        else:
            milestone = gating_milestone

    if prereq_content_key:
        _validate_min_score(min_score)
        requirements = {'min_score': min_score, 'min_completion': min_completion}
        if not milestone:
            milestone = _get_prerequisite_milestone(prereq_content_key)
        milestones_api.add_course_content_milestone(course_key, gated_content_key, 'requires', milestone, requirements)


def get_required_content(course_key, gated_content_key):
    """
    Returns the prerequisite content usage key, minimum score and minimum completion percentage needed for fulfillment
    of that prerequisite for the given gated_content_key.

    Args:
        course_key (str|CourseKey): The course key
        gated_content_key (str|UsageKey): The gated content usage key

    Returns:
        tuple: The prerequisite content usage key, minimum score and minimum completion percentage,
        (None, None, None) if the content is not gated
    """
    milestone = get_gating_milestone(course_key, gated_content_key, 'requires')
    if milestone:
        return (
            _get_gating_block_id(milestone),
            milestone.get('requirements', {}).get('min_score', None),
            milestone.get('requirements', {}).get('min_completion', None),
        )
    else:
        return None, None, None


@gating_enabled(default=[])
def get_gated_content(course, user):
    """
    Returns the unfulfilled gated content usage keys in the given course.

    Arguments:
        course (CourseDescriptor): The course
        user (User): The user

    Returns:
        list: The list of gated content usage keys for the given course
    """
    if _has_access_to_course(user, 'staff', course.id):
        return []
    else:
        # Get the unfulfilled gating milestones for this course, for this user
        return [
            m['content_id'] for m in find_gating_milestones(
                course.id,
                None,
                'requires',
                {'id': user.id}
            )
        ]


def is_gate_fulfilled(course_key, gating_content_key, user_id):
    """
    Determines if a prerequisite section specified by gating_content_key
    has any unfulfilled milestones.

    Arguments:
        course_key (CourseUsageLocator): Course locator
        gating_content_key (BlockUsageLocator): The locator for the section content
        user_id: The id of the user

    Returns:
        Returns True if section has no unfufilled milestones or is not a prerequisite.
        Returns False otherwise
    """
    gating_milestone = get_gating_milestone(course_key, gating_content_key, "fulfills")
    if not gating_milestone:
        return True

    unfulfilled_milestones = [
        m['content_id'] for m in find_gating_milestones(
            course_key,
            None,
            'requires',
            {'id': user_id}
        ) if m['namespace'] == gating_milestone['namespace']
    ]
    return not unfulfilled_milestones


def compute_is_prereq_met(content_id, user_id, recalc_on_unmet=False):
    """
    Returns true if the prequiste has been met for a given milestone.
    Will recalculate the subsection grade if specified and prereq unmet

    Arguments:
        content_id (BlockUsageLocator): BlockUsageLocator for the content
        user_id: The id of the user
        recalc_on_unmet: Recalculate the grade if prereq has not yet been met

    Returns:
        tuple: True|False,
        prereq_meta_info = { 'url': prereq_url|None, 'display_name': prereq_name|None}
    """
    course_key = content_id.course_key

    # if unfullfilled milestones exist it means prereq has not been met
    unfulfilled_milestones = milestones_helpers.get_course_content_milestones(
        course_key,
        content_id,
        'requires',
        user_id
    )

    prereq_met = not unfulfilled_milestones
    prereq_meta_info = {'url': None, 'display_name': None}

    if prereq_met or not recalc_on_unmet:
        return prereq_met, prereq_meta_info

    milestone = unfulfilled_milestones[0]
    student = User.objects.get(id=user_id)
    store = modulestore()

    with store.bulk_operations(course_key):
        subsection_usage_key = UsageKey.from_string(_get_gating_block_id(milestone))
        subsection = store.get_item(subsection_usage_key)
        prereq_meta_info = {
            'url': reverse('jump_to', kwargs={'course_id': course_key, 'location': subsection_usage_key}),
            'display_name': subsection.display_name
        }
        prereq_met = update_milestone(milestone, subsection_usage_key, milestone, student)

    return prereq_met, prereq_meta_info


def update_milestone(milestone, usage_key, prereq_milestone, user, grade_percentage=None, completion_percentage=None):
    """
    Updates the milestone record based on evaluation of prerequisite met.

    Arguments:
        milestone: The gated milestone being evaluated
        usage_key: Usage key of the prerequisite subsection
        prereq_milestone: The gating milestone
        user: The user who has fulfilled milestone
        grade_percentage: Grade percentage of prerequisite subsection
        completion_percentage: Completion percentage of prerequisite subsection

    Returns:
        True if prerequisite has been met, False if not
    """
    min_score, min_completion = _get_minimum_required_percentage(milestone)
    if not grade_percentage:
        grade_percentage = get_subsection_grade_percentage(usage_key, user) if min_score > 0 else 0
    if not completion_percentage:
        completion_percentage = get_subsection_completion_percentage_with_gradebook_edit(usage_key, user) \
            if min_completion > 0 else 0

    if grade_percentage >= min_score and completion_percentage >= min_completion:
        milestones_helpers.add_user_milestone({'id': user.id}, prereq_milestone)
        return True
    else:
        milestones_helpers.remove_user_milestone({'id': user.id}, prereq_milestone)
        return False


def _get_gating_block_id(milestone):
    """
    Return the block id of the gating milestone
    """
    return milestone.get('namespace', '').replace(GATING_NAMESPACE_QUALIFIER, '')


def get_subsection_grade_percentage(subsection_usage_key, user):
    """
    Computes grade percentage for a subsection in a given course for a user

    Arguments:
        subsection_usage_key: key of subsection
        user: The user whose grade needs to be computed

    Returns:
        User's grade percentage for given subsection
    """
    subsection_grade_percentage = 0.0
    try:
        subsection_structure = get_course_blocks(user, subsection_usage_key)
        if any(subsection_structure):
            subsection_grade_factory = SubsectionGradeFactory(user, course_structure=subsection_structure)
            if subsection_usage_key in subsection_structure:
                # this will force a recalculation of the subsection grade
                subsection_grade = subsection_grade_factory.update(
                    subsection_structure[subsection_usage_key], only_if_higher=True, persist_grade=True
                )
                subsection_grade_percentage = subsection_grade.percent_graded * 100.0
    except ItemNotFoundError as err:
        log.warning("Could not find course_block for subsection=%s error=%s", subsection_usage_key, err)
    return subsection_grade_percentage


def get_subsection_completion_percentage_with_gradebook_edit(subsection_usage_key, user, overrides=None):
    """
    Computes completion percentage for a subsection in a given course for a user, consider the gradeook override
    Arguments:
        subsection_usage_key: key of subsection
        user: The user whose completion percentage needs to be computed
        overrides: list of usage_keys of subsections which are overridden
    Returns:
        User's completion percentage for given subsection
    """
    overridden_blocks = []
    # skip override check in testing mode
    if overrides is None and "pytest" not in sys.modules:
        grade_overrides = PersistentSubsectionGradeOverride.objects.filter(
            grade__user_id=user.id,
            grade__course_id=subsection_usage_key.course_key,
        ).select_related('grade')
        overridden_subsection_keys = [i.grade.usage_key for i in grade_overrides]
        overrides = list(set(overridden_subsection_keys))
    if overrides:
        for key in overrides:
            struct = get_course_blocks(user, key)
            if any(struct):
                blocks = [
                    block for block in struct
                    if block.block_type not in ['chapter', 'sequential', 'vertical', 'course', 'discussion']
                ]
                overridden_blocks = overridden_blocks + blocks
    subsection_completion_percentage = 0.0
    try:
        subsection_structure = get_course_blocks(user, subsection_usage_key)
        if any(subsection_structure):
            if completion_waffle.waffle().is_enabled(completion_waffle.ENABLE_COMPLETION_TRACKING):
                from lms.djangoapps.grades.signals.handlers import recalculate_course_completion_percentage
                subsection_grade_factory = SubsectionGradeFactory(user, course_structure=subsection_structure)

                # no need to trigger the signal to recalculate progress again, so we disconnect the signals
                # and reconnect it afterwards
                signals.post_save.disconnect(receiver=recalculate_course_completion_percentage, sender=BlockCompletion)
                for block in subsection_structure:
                    if block.block_type == 'problem':
                        subsection_grade = subsection_grade_factory.update(
                            subsection_structure[block], persist_grade=False
                        )
                        if not subsection_grade.all_total.possible:
                            BlockCompletion.objects.submit_completion(
                                user=user,
                                course_key=subsection_usage_key.course_key,
                                block_key=block,
                                completion=1.0,)
                signals.post_save.connect(receiver=recalculate_course_completion_percentage, sender=BlockCompletion)
            completable_blocks = [
                block for block in subsection_structure
                if block.block_type not in ['chapter', 'sequential', 'vertical', 'course', 'discussion']
            ]
            if not completable_blocks:
                return 0
            subsection_completion_total = 0
            course_block_completions = BlockCompletion.get_course_completions(user, subsection_usage_key.course_key)
            for block in completable_blocks:
                if block in overridden_blocks:
                    subsection_completion_total += 1
                elif course_block_completions.get(block):
                    subsection_completion_total += course_block_completions.get(block)
            subsection_completion_percentage = min(
                100 * (subsection_completion_total / float(len(completable_blocks))), 100
            )

    except ItemNotFoundError as err:
        log.warning("Could not find course_block for subsection=%s error=%s", subsection_usage_key, err)

    return subsection_completion_percentage


def get_subsection_completion_percentage(subsection_usage_key, user):
    """
    Computes completion percentage for a subsection in a given course for a user
    Arguments:
        subsection_usage_key: key of subsection
        user: The user whose completion percentage needs to be computed
    Returns:
        User's completion percentage for given subsection
    """
    subsection_completion_percentage = 0.0
    try:
        subsection_structure = get_course_blocks(user, subsection_usage_key)
        if any(subsection_structure):
            subsection_grade_factory = SubsectionGradeFactory(user, course_structure=subsection_structure)
            for block in subsection_structure:
                if completion_waffle.waffle().is_enabled(completion_waffle.ENABLE_COMPLETION_TRACKING):
                    if block.block_type == 'problem':
                        subsection_grade = subsection_grade_factory.update(subsection_structure[block], persist_grade=False)
                        if not subsection_grade.all_total.possible:
                            BlockCompletion.objects.submit_completion(
                                user=user,
                                course_key=subsection_usage_key.course_key,
                                block_key=block,
                                completion=1.0,)
            completable_blocks = [
                block for block in subsection_structure
                if block.block_type not in ['chapter', 'sequential', 'vertical', 'course', 'discussion']
            ]
            if not completable_blocks:
                return 0
            subsection_completion_total = 0
            course_block_completions = BlockCompletion.get_course_completions(user, subsection_usage_key.course_key)
            for block in completable_blocks:
                if course_block_completions.get(block):
                    subsection_completion_total += course_block_completions.get(block)
            subsection_completion_percentage = min(
                100 * (subsection_completion_total / float(len(completable_blocks))), 100
            )

    except ItemNotFoundError as err:
        log.warning("Could not find course_block for subsection=%s error=%s", subsection_usage_key, err)

    return subsection_completion_percentage


def _get_minimum_required_percentage(milestone):
    """
    Returns the minimum score and minimum completion percentage requirement for the given milestone.
    """
    # Default minimum score and minimum completion percentage to 100
    min_score = 100
    min_completion = 100
    requirements = milestone.get('requirements')
    if requirements:
        try:
            min_score = int(requirements.get('min_score'))
        except (ValueError, TypeError):
            log.warning(
                u'Gating: Failed to find minimum score for gating milestone %s, defaulting to 100',
                json.dumps(milestone)
            )
        try:
            min_completion = int(requirements.get('min_completion', 0))
        except (ValueError, TypeError):
            log.warning(
                u'Gating: Failed to find minimum completion percentage for gating milestone %s, defaulting to 100',
                json.dumps(milestone)
            )
    return min_score, min_completion


def _get_subsection_percentage(subsection_grade):
    """
    Returns the percentage value of the given subsection_grade.
    """
    return subsection_grade.percent_graded * 100.0


def complete_subsection(subsection_usage_key, user):
    """
    Complete all blocks in the given subsection
    """
    from lms.djangoapps.grades.course_grade_factory import CourseGradeFactory
    from lms.djangoapps.grades.signals.handlers import recalculate_course_completion_percentage
    try:
        subsection_structure = get_course_blocks(user, subsection_usage_key)
        if any(subsection_structure):
            completable_blocks = [
                (block, 1) for block in subsection_structure
                if block.block_type not in ['chapter', 'sequential', 'vertical', 'course']
            ]
            if completable_blocks:
                signals.post_save.disconnect(receiver=recalculate_course_completion_percentage, sender=BlockCompletion)
                BlockCompletion.objects.submit_batch_completion(
                    user, subsection_usage_key.course_key, completable_blocks
                )
                CourseGradeFactory().update_course_completion_percentage(subsection_usage_key.course_key, user)
    except ItemNotFoundError as err:
        log.warning("Could not find course_block for subsection=%s error=%s", subsection_usage_key, err)
