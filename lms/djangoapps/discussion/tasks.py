"""
Defines asynchronous celery task for sending email notification (through edx-ace)
pertaining to new discussion forum comments.
"""
import logging
from urlparse import urljoin

import analytics
from celery import task
from django.conf import settings
from django.contrib.auth.models import User
from django.contrib.sites.models import Site

from celery_utils.logged_task import LoggedTask
from django_comment_common.utils import set_course_discussion_settings
from django_comment_common.models import DiscussionsIdMapping
from edx_ace import ace
from edx_ace.utils import date
from edx_ace.recipient import Recipient
from opaque_keys.edx.keys import CourseKey
from lms.djangoapps.django_comment_client.utils import permalink, get_accessible_discussion_xblocks_by_course_id
import lms.lib.comment_client as cc

from openedx.core.djangoapps.content.course_overviews.models import CourseOverview
from openedx.core.djangoapps.ace_common.template_context import get_base_template_context
from openedx.core.djangoapps.ace_common.message import BaseMessageType
from openedx.core.djangoapps.site_configuration import helpers as configuration_helpers
from openedx.core.lib.celery.task_utils import emulate_http_request


log = logging.getLogger(__name__)


DEFAULT_LANGUAGE = 'en'
ROUTING_KEY = getattr(settings, 'ACE_ROUTING_KEY', None)


@task(base=LoggedTask)
def update_discussions_map(context):
    """
    Updates the mapping between discussion_id to discussion block usage key
    for all discussion blocks in the given course.

    context is a dict that contains:
        course_id (string): identifier of the course
    """
    course_key = CourseKey.from_string(context['course_id'])
    discussion_blocks = get_accessible_discussion_xblocks_by_course_id(course_key, include_all=True)
    discussions_id_map = {
        discussion_block.discussion_id: unicode(discussion_block.location)
        for discussion_block in discussion_blocks
    }
    DiscussionsIdMapping.update_mapping(course_key, discussions_id_map)


class ResponseNotification(BaseMessageType):
    pass


@task(base=LoggedTask, routing_key=ROUTING_KEY)
def send_ace_message(context):
    context['course_id'] = CourseKey.from_string(context['course_id'])

    if _should_send_message(context):
        context['site'] = Site.objects.get(id=context['site_id'])
        thread_author = User.objects.get(id=context['thread_author_id'])
        with emulate_http_request(site=context['site'], user=thread_author):
            message_context = _build_message_context(context)
            message = ResponseNotification().personalize(
                Recipient(thread_author.username, thread_author.email),
                _get_course_language(context['course_id']),
                message_context
            )
            log.info('Sending forum comment email notification with context %s', message_context)

            # if email service is disabled, do nothing
            email_service_enabled = configuration_helpers.get_value('ENABLE_EMAIL_SERVICE', True)
            if email_service_enabled:
                ace.send(message)
            _track_notification_sent(message, context)


def _track_notification_sent(message, context):
    """
    Send analytics event for a sent email
    """
    properties = {
        'app_label': 'discussion',
        'name': 'responsenotification',  # This is 'Campaign' in GA
        'language': message.language,
        'uuid': unicode(message.uuid),
        'send_uuid': unicode(message.send_uuid),
        'thread_id': context['thread_id'],
        'thread_created_at': date.deserialize(context['thread_created_at']),
        'nonInteraction': 1,
    }
    analytics.track(
        user_id=context['thread_author_id'],
        event='edx.bi.email.sent',
        course_id=context['course_id'],
        properties=properties
    )


def _should_send_message(context):
    cc_thread_author = cc.User(id=context['thread_author_id'], course_id=context['course_id'])
    return (
        _is_user_subscribed_to_thread(cc_thread_author, context['thread_id']) and
        _is_not_subcomment(context['comment_id']) and
        _is_first_comment(context['comment_id'], context['thread_id'])
    )


def _is_not_subcomment(comment_id):
    comment = cc.Comment.find(id=comment_id).retrieve()
    return not getattr(comment, 'parent_id', None)


def _is_first_comment(comment_id, thread_id):
    thread = cc.Thread.find(id=thread_id).retrieve(with_responses=True)
    first_comment = thread.children[0]
    return first_comment.get('id') == comment_id


def _is_user_subscribed_to_thread(cc_user, thread_id):
    paginated_result = cc_user.subscribed_threads()
    thread_ids = {thread['id'] for thread in paginated_result.collection}

    while paginated_result.page < paginated_result.num_pages:
        next_page = paginated_result.page + 1
        paginated_result = cc_user.subscribed_threads(query_params={'page': next_page})
        thread_ids.update(thread['id'] for thread in paginated_result.collection)

    return thread_id in thread_ids


def _get_course_language(course_id):
    course_overview = CourseOverview.objects.get(id=course_id)
    language = course_overview.language or DEFAULT_LANGUAGE
    return language


def _build_message_context(context):
    message_context = get_base_template_context(context['site'])
    message_context.update(context)
    thread_author = User.objects.get(id=context['thread_author_id'])
    comment_author = User.objects.get(id=context['comment_author_id'])
    message_context.update({
        'thread_username': thread_author.username,
        'comment_username': comment_author.username,
        'post_link': _get_thread_url(context),
        'comment_created_at': date.deserialize(context['comment_created_at']),
        'thread_created_at': date.deserialize(context['thread_created_at'])
    })
    return message_context


def _get_thread_url(context):
    thread_content = {
        'type': 'thread',
        'course_id': context['course_id'],
        'commentable_id': context['thread_commentable_id'],
        'id': context['thread_id'],
    }
    return urljoin(context['site'].domain, permalink(thread_content))
