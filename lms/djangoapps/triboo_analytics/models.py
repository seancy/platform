# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from collections import defaultdict
import hashlib
import json
import logging
import multiprocessing
import uuid
from django.contrib.auth.models import User
from django.core.validators import MaxValueValidator
from django.db import models, connections
from django.db.models import Sum, Count
from django.http import Http404
from datetime import date, datetime
from django.utils import timezone
from pytz import UTC
from django.utils.translation import ugettext_noop
from django_countries.fields import CountryField
from model_utils.fields import AutoLastModifiedField
from model_utils.models import TimeStampedModel
from requests import ConnectionError

from courseware.courses import get_course_by_id
from courseware.models import XModuleUserStateSummaryField, StudentModule
from lms.djangoapps.grades.course_grade_factory import CourseGradeFactory
import lms.lib.comment_client as cc
from opaque_keys.edx.keys import CourseKey, UsageKey
from opaque_keys.edx.django.models import CourseKeyField, UsageKeyField
from openedx.core.djangoapps.content.course_overviews.models import CourseOverview
from openedx.core.djangoapps.content.course_structures.api.v0.api import course_structure, CourseStructureNotAvailableError
from openedx.core.djangoapps.content.course_structures.tasks import update_course_structure
from openedx.core.djangoapps.models.course_details import CourseDetails
from openedx.core.djangoapps.site_configuration.models import SiteConfiguration
from student.models import CourseEnrollment, UserProfile
from track.backends.django import TrackingLog
from xmodule.modulestore.django import modulestore
from six import text_type

ANALYTICS_ACCESS_GROUP = "Triboo Analytics Admin"
ANALYTICS_LIMITED_ACCESS_GROUP = "Restricted Triboo Analytics Admin"

ANALYTICS_WORKER_USER = "analytics_worker"

IDLE_TIME = 900 # 15 minutes

logger = logging.getLogger('triboo_analytics')


def create_analytics_worker():
    user = User(username=ANALYTICS_WORKER_USER,
                email="analytics_worker@learning-tribes.com",
                is_active=True,
                is_staff=True)
    user.set_password(uuid.uuid4().hex)
    user.save()

    profile = UserProfile(user=user)
    profile.save()


def get_day_limits(day=None, offset=0):
    day = (day or timezone.now()) + timezone.timedelta(days=offset)
    day_start = day.replace(hour=0, minute=0, second=0, microsecond=0)
    day_end = day_start + timezone.timedelta(days=1)
    return day_start, day_end


class CourseStatus(object):
    not_started = 0
    in_progress = 1
    finished = 2
    failed = 3
    verbose_names = ['Not Started', 'In Progress', 'Successful', 'Unsuccessful']


def format_time_spent(seconds):
    m, s = divmod(seconds, 60)
    h, m = divmod(m, 60)
    return "%d:%02d:%02d" % (h, m, s)


def format_badges(badges_earned, badges_possible):
    return "{} / {}".format(badges_earned, badges_possible)


def get_badges(report_badges):
    badges = report_badges.split(" / ")
    if len(badges) == 2:
        return int(badges[0]), int(badges[1])
    return 0, 0


def get_combined_org(org_combination):
    combined_org = ""
    for org in org_combination:
        combined_org += "+%s" % org
    return combined_org[1:]


class TrackingLogHelper(object):
    def __init__(self, course_keys):
        self.block_sections_by_course = {}
        self.sections_by_course = {}
        for course_key in course_keys:
            sections, block_sections = self.get_sections(course_key)
            course_id_str = "%s" % course_key
            self.sections_by_course[course_id_str] = sections
            self.block_sections_by_course[course_id_str] = block_sections


    @classmethod
    def get_chapter_url(cls, block_id):
        chapter_url_start = block_id.find("@chapter+block@")
        if chapter_url_start > 0:
            return block_id[chapter_url_start+15:]
        return None


    @classmethod
    def get_section_url(cls, block_id):
        section_url_start = block_id.find("@sequential+block@")
        if section_url_start > 0:
            return block_id[section_url_start+18:]
        return None


    @classmethod
    def get_sections(cls, course_key):
        """
        returns 2 dicts:
        1) a dict giving the combined display name for the combined url of each section
        the combined display name of a section is formatted as "chapter.display_name / section.display_name"
        2) a dict giving the combined url of the parent section for each block id of the course
        the combined url of a section is formatted as "chapter_url/section_url" where:
        - chapter_url is the part of the chapter block id after '@chapter+block@'
        - section_url is the part of the section block id after '@sequential+block@'
        """
        _sections = {}

        section_urls = {}
        parentage = {}
        outline = course_structure(course_key)

        for block_id, block in outline['blocks'].iteritems():
            if block['type'] == "chapter":
                chapter_url = cls.get_chapter_url(block_id)
                for section_id in block['children']:
                    section_url = cls.get_section_url(section_id)
                    combined_section_url = "%s/%s" % (chapter_url, section_url)
                    section_urls[section_id] = combined_section_url
                    _sections[section_id] = {
                        'combined_url': combined_section_url,
                        'chapter_display_name': block['display_name']
                    }
            else:
                if block['type'] != "course" and len(block['children']) > 0:
                    parent_id = block_id
                    parent_type = block['type']
                    for child_id in block['children']:
                        parentage[child_id] = {
                            'parent_id': parent_id,
                            'parent_type': parent_type
                        }

        done = False
        while not done:
            done = True
            for child_id, child in parentage.iteritems():
                if child['parent_type'] != "sequential":
                    done = False
                    parent_id = child['parent_id']
                    child['parent_id'] = parentage[parent_id]['parent_id']
                    child['parent_type'] = parentage[parent_id]['parent_type']

        block_sections = {child_id: section_urls[child['parent_id']] for child_id, child in parentage.iteritems()}

        sections = {}
        for block_id, block in outline['blocks'].iteritems():
            if block_id in _sections.keys():
                combined_url = _sections[block_id]['combined_url']
                combined_display_name = "%s / %s" % (_sections[block_id]['chapter_display_name'],
                                                     block['display_name'])
                sections[combined_url] = combined_display_name

        return sections, block_sections


    @classmethod
    def get_day_tracking_logs(cls, day_start, day_end):
        """
        retrieve the TrackingLog objects with time between [like day_start, day_end[
        and sort these logs by user_id and order them by time
        """
        tracking_logs = TrackingLog.objects.filter(
                            time__gte=day_start, time__lt=day_end).exclude(
                            user_id=None).only('event_type', 'time', 'user_id', 'agent', 'time_spent')
        user_logs = defaultdict(list)
        for l in tracking_logs:
            user_logs[l.user_id].append(l)
        for user_id, logs in user_logs.iteritems():
            user_logs[user_id] = sorted(logs, key=lambda v:v.time)
            first_log_time = user_logs[user_id][0].time
            try:
                user = User.objects.get(id=user_id)
                if user.last_login.date() < first_log_time.date():
                    logger.info("user %d last_login %s should => %s" % (user_id, user.last_login, first_log_time))
                    user.last_login = first_log_time
                    user.save()
            except User.DoesNotExist:
                pass

        return user_logs


    def update_logs(self, day=None):
        day_start, day_end = get_day_limits(day=day)
        user_logs = self.get_day_tracking_logs(day_start, day_end)

        for user_id, logs in user_logs.iteritems():
            if len(logs) >= 2:
                log_pairs = zip(logs[:-1], logs[1:])
                for log1, log2 in log_pairs:
                    total_seconds = (log2.time - log1.time).total_seconds()
                    time_spent = total_seconds if total_seconds < IDLE_TIME else IDLE_TIME
                    self.update_log(log1, time_spent)
                self.update_log(logs[-1], IDLE_TIME)
            elif len(logs) == 1:
                self.update_log(logs[0], IDLE_TIME)


    def update_log(self, tracking_log, time_spent):
        tracking_log.time_spent = time_spent
        section = self.get_parent_section_combined_url(tracking_log.event_type)
        if section:
            tracking_log.section = section
        tracking_log.save()


    def get_parent_section_combined_url(self, event_type):
        section = None
        pieces = event_type.split('/')
        nb_pieces = len(pieces)
        if nb_pieces > 4 and pieces[1] == "courses":
            course_id = pieces[2]
            if course_id in self.block_sections_by_course.keys():
                if pieces[3] == "courseware" and nb_pieces > 5:
                    section = "%s/%s" % (pieces[4], pieces[5])
                elif pieces[3] == "xblock":
                    block_id = "%s" % pieces[4]
                    if block_id in self.block_sections_by_course[course_id].keys():
                        section = self.block_sections_by_course[course_id][block_id]
        return section


def get_day():
    return timezone.now().date()

class AutoCreatedField(models.DateField):
    """
    A DateField that automatically populates itself at
    object creation.

    By default, sets editable=False, default=timezone.now.

    """
    def __init__(self, *args, **kwargs):
        kwargs.setdefault('editable', False)
        kwargs.setdefault('default', get_day)
        super(AutoCreatedField, self).__init__(*args, **kwargs)


class TimeModel(models.Model):
    """
    An abstract base class model that provides self-updating
    ``created`` and ``modified`` fields.

    """
    created = AutoCreatedField('created')
    modified = AutoLastModifiedField('modified')

    class Meta:
        abstract = True


class ReportMixin(object):
    @classmethod
    def filter_by_day(cls, date_time=None, **kwargs):
        day = date_time.date() if date_time else timezone.now().date()
        return cls.objects.filter(created=day, **kwargs)

    @classmethod
    def get_by_day(cls, date_time=None, **kwargs):
        day = date_time.date() if date_time else timezone.now().date()
        try:
            return cls.objects.get(created=day, **kwargs)
        except cls.DoesNotExist:
            return None


class UnicodeMixin(object):
    def __unicode__(self):
        result = {}
        for k, v in self.__dict__.iteritems():
            if k not in ['_state', 'modified']:
                result[k] = v.strftime('%Y-%m-%d %H:%S %Z') if isinstance(v, timezone.datetime) else v
        return unicode(result)


class UniqueVisitorsMixin(object):
    @classmethod
    def _get_unique_visitors_csv_data(cls, unique_visitors):
        unique_visitors_csv_data = {"per_day": "", "per_week": "", "per_month": ""}

        unique_visitors = unique_visitors.values('created', 'unique_visitors').order_by('created')
        if unique_visitors:
            current_week = unique_visitors[0]['created'].strftime('%W')
            per_week = {current_week: []}
            current_month = unique_visitors[0]['created'].strftime('%m-%Y')
            per_month = {current_month: []}

            for uv in unique_visitors:
                unique_visitors_csv_data['per_day'] += "%s,%d\\n" % (uv['created'].strftime('%d-%m-%Y'), uv['unique_visitors'])

                uv_week = uv['created'].strftime('%W')
                if uv_week != current_week:
                    current_week = uv_week
                    per_week[current_week] = [uv['unique_visitors']]
                else:
                    per_week[current_week].append(uv['unique_visitors'])

                uv_month = uv['created'].strftime('%m-%Y')
                if uv_month != current_month:
                    current_month = uv_month
                    per_month[current_month] = [uv['unique_visitors']]
                else:
                    per_month[current_month].append(uv['unique_visitors'])

            weeks = per_week.keys()
            weeks.sort()
            for week in weeks:
                visitors = per_week[week]
                avg = int(round(sum(visitors) / float(len(visitors))))
                unique_visitors_csv_data['per_week'] += "%s,%d\\n" % (week, avg)

            months = per_month.keys()
            months.sort()
            for month in months:
                visitors = per_month[month]
                avg = int(round(sum(visitors) / float(len(visitors))))
                unique_visitors_csv_data['per_month'] += "%s,%d\\n" % (month, avg)

        return unique_visitors_csv_data


class ReportLog(UnicodeMixin, TimeStampedModel):
    class Meta(object):
        app_label = "triboo_analytics"
        get_latest_by = "created"

    learner_visit = models.DateTimeField(default=None, null=True)
    learner_course = models.DateTimeField(default=None, null=True)
    learner = models.DateTimeField(default=None, null=True)
    course = models.DateTimeField(default=None, null=True)
    microsite = models.DateTimeField(default=None, null=True)
    country = models.DateTimeField(default=None, null=True)

    @classmethod
    def get_latest(cls, from_date=None, to_date=None):
        filter_kwargs = {
            'learner_visit__isnull': False,
            'learner_course__isnull': False,
            'learner__isnull': False,
            'course__isnull': False,
            'microsite__isnull': False,
            'country__isnull': False
        }
        try:
            if from_date:
                if to_date:
                    filter_kwargs['created__gte'] = from_date
                    filter_kwargs['created__lte'] = to_date
                else:
                    filter_kwargs['created__gte'] = from_date
            elif to_date:
                filter_kwargs['created__lte'] = to_date
            return cls.objects.filter(**filter_kwargs).latest()
        except cls.DoesNotExist:
            return None

    @classmethod
    def update_or_create(cls, **kwargs):
        today_start, today_end = get_day_limits()
        cls.objects.update_or_create(created__gte=today_start,
                                     created__lt=today_end,
                                     defaults=kwargs)


class LearnerVisitsDailyReport(UnicodeMixin, ReportMixin, TimeModel):
    class Meta(object):
        app_label = "triboo_analytics"
        get_latest_by = "created"
        unique_together = ('created', 'user', 'course_id', 'device')
        index_together = ['created', 'user', 'course_id', 'device']

    user = models.ForeignKey(User, null=False)
    course_id = CourseKeyField(max_length=255, null=True)
    org = models.CharField(max_length=255, db_index=True, null=True, default=None)
    device = models.CharField(max_length=255, null=False)
    time_spent = models.PositiveIntegerField(default=0)


    @classmethod
    def generate_day_reports(cls, day=None):
        previous_day_start, previous_day_end = get_day_limits(day=day, offset=-1)
        previous_day_tracking_logs = TrackingLogHelper.get_day_tracking_logs(previous_day_start, previous_day_end)
        for user_id, user_logs in previous_day_tracking_logs.iteritems():
            if User.objects.filter(id=user_id).exists():
                cls.update_or_create(user_id, user_logs, day)


    @classmethod
    def generate_today_reports(cls):
        cls.generate_day_reports()
        ReportLog.update_or_create(learner_visit=timezone.now())


    @classmethod
    def update_or_create(cls, user_id, user_tracking_logs, day=None):
        # group visit by course_id, device, cumulate time_spent
        reports = defaultdict(lambda: 0)
        for l in user_tracking_logs:
            if l.time_spent:
                reports[(l.course_id, l.device)] += l.time_spent

        if not day:
            day = timezone.now().date()
        for (course_id, device), time_spent in reports.iteritems():
            org = course_id.org if course_id != CourseKeyField.Empty else None

            cls.objects.update_or_create(user_id=user_id,
                                         course_id=course_id,
                                         org=org,
                                         device=device,
                                         created=day,
                                         defaults={'time_spent': int(time_spent)})


    @classmethod
    def get_active_user_ids(cls, from_date, to_date, course_id=None):
        if course_id:
            reports = cls.objects.filter(created__gte=from_date,
                                         created__lte=to_date,
                                         user__is_active=True,
                                         course_id=course_id)
        else:
            reports = cls.objects.filter(created__gte=from_date, created__lte=to_date, user__is_active=True,)
        return [result['user'] for result in reports.values('user').distinct()]


class LearnerCourseDailyReport(UnicodeMixin, ReportMixin, TimeModel):
    class Meta(object):
        app_label = "triboo_analytics"
        get_latest_by = "created"
        unique_together = ('created', 'user', 'course_id')
        index_together = (['created', 'user', 'course_id'],
                          ['created', 'course_id'])

    user = models.ForeignKey(User, null=False)
    course_id = CourseKeyField(max_length=255, db_index=True, null=False)
    org = models.CharField(max_length=255, db_index=True, null=False)
    status = models.PositiveSmallIntegerField(help_text="not started: 0; in progress: 1; finished: 2; failed: 3; ",
                                              default=0)
    progress = models.PositiveSmallIntegerField(default=0, validators=[MaxValueValidator(100)])
    badges = models.CharField(max_length=20, default="0 / 0")
    current_score = models.PositiveSmallIntegerField(default=0, validators=[MaxValueValidator(100)])
    posts = models.PositiveIntegerField(default=0)
    total_time_spent = models.PositiveIntegerField(default=0)
    enrollment_date = models.DateTimeField(default=None, null=True, blank=True)
    completion_date = models.DateTimeField(default=None, null=True, blank=True)


    @classmethod
    def generate_today_reports(cls, last_analytics_success, overviews, sections_by_course, multi_process=False):
        analytics_worker = User.objects.get(username=ANALYTICS_WORKER_USER)

        nb_processes = 2 * multiprocessing.cpu_count() if multi_process else 1

        nb_courses = len(overviews)
        i = 0
        for overview in overviews:
            i += 1
            course_id = overview.id
            course_last_update = overview.modified.date()
            course_id_str = "%s" % course_id
            try:
                course = get_course_by_id(course_id)
            except Http404:
                logger.error("course_id=%s returned Http404" % course_key)
                continue
            Badge.refresh(course_id, course, analytics_worker)

            sections = sections_by_course[course_id_str]
            
            enrollments = CourseEnrollment.objects.filter(is_active=True,
                                                          course_id=course_id,
                                                          user__is_active=True)
            nb_enrollments = len(enrollments)

            logger.info("learner course report for course_id=%s (%d / %d): %d enrollments" % (
                        course_id, i, nb_courses, nb_enrollments))

            if (not multi_process
                and (nb_enrollments > 10000)
                and (not last_analytics_success or (course_last_update >= last_analytics_success))):
                multi_process = True
                logger.info("force multiprocessing")

            if multi_process:
                enrollment_ids = [e_id for e_id in enrollments.values_list('id', flat=True)]

                enrollments_by_process = []
                for j in range(0, nb_processes):
                    enrollments_by_process.append([])

                j = 0
                for enrollment_id in enrollment_ids:
                    enrollments_by_process[j].append(enrollment_id)
                    j += 1
                    if j == nb_processes:
                        j = 0

                connections.close_all()
                processes = []
                for process_enrollments in enrollments_by_process:
                    process = multiprocessing.Process(target=cls.process_generate_today_reports,
                                                      args=(last_analytics_success, course_last_update, process_enrollments, course, sections,))
                    process.start()
                    processes.append(process)
                [process.join() for process in processes]

            else:
                enrollments = enrollments.prefetch_related('user')
                for enrollment in enrollments:
                    cls.generate_enrollment_report(last_analytics_success, course_last_update, enrollment, course, sections)

        ReportLog.update_or_create(learner_course=timezone.now())


    @classmethod
    def process_generate_today_reports(cls, last_analytics_success, course_last_update, enrollment_ids, course, sections):
        for enrollment_id in enrollment_ids:
            enrollment = CourseEnrollment.objects.get(id=enrollment_id)
            cls.generate_enrollment_report(last_analytics_success, course_last_update, enrollment, course, sections)


    @classmethod
    def generate_enrollment_report(cls, last_analytics_success, course_last_update, enrollment, course, sections):
        updated = cls.update_or_create(last_analytics_success, course_last_update, enrollment, course)
        if updated:
            LearnerSectionDailyReport.update_or_create(enrollment, sections)


    @classmethod
    def update_or_create(cls, last_analytics_success, course_last_update, enrollment, course):
        course_key = enrollment.course_id
        user = enrollment.user
        day = timezone.now().date()

        report_needs_update = True
        if user.is_active:
            if last_analytics_success:
                try:
                    last_report = cls.objects.get(course_id=course_key, user_id=user.id, created=last_analytics_success)
                    if ((not enrollment.gradebook_edit or enrollment.gradebook_edit.date() < last_report.created)
                        and (not user.last_login or user.last_login.date() < last_report.created)
                        and course_last_update < last_report.created
                        and enrollment.completed == last_report.completion_date):
                        report_needs_update = False
                        cls.objects.update_or_create(created=day,
                                                     user=user,
                                                     course_id=course_key,
                                                     defaults={'org': course_key.org,
                                                               'total_time_spent': last_report.total_time_spent,
                                                               'status': last_report.status,
                                                               'progress': last_report.progress,
                                                               'badges': last_report.badges,
                                                               'current_score': last_report.current_score,
                                                               'posts': last_report.posts,
                                                               'enrollment_date': enrollment.created,
                                                               'completion_date': enrollment.completed})
                except cls.DoesNotExist:
                    pass

            if report_needs_update:
                with modulestore().bulk_operations(course_key):
                    total_time_spent = (LearnerVisitsDailyReport.objects.filter(
                                            user=user, course_id=course_key, created__gte=enrollment.created).aggregate(
                                            Sum('time_spent')).get('time_spent__sum') or 0)

                    progress = CourseGradeFactory().get_progress(user, course)
                    progress['progress'] *= 100.0
                    if not progress:
                        logger.warning('course=%s user_id=%d does not have progress info => empty report.' % (
                            course_key, user.id))
                        cls.objects.update_or_create(
                            created=day,
                            user=user,
                            course_id=course_key,
                            defaults={'org': course_key.org,
                                      'status': CourseStatus.not_started,
                                      'progress': 0,
                                      'badges': 0,
                                      'current_score': 0,
                                      'posts': 0,
                                      'total_time_spent': 0,
                                      'enrollment_date': enrollment.created,
                                      'completion_date': None})
                        return

                    if progress['progress'] == 100:
                        status = CourseStatus.failed

                        if progress['nb_trophies_possible'] == 0 or progress['is_course_passed']:
                            status = CourseStatus.finished

                    else:
                        # by gradebook edit a user could have a progress > 0 while total_time_spent = 0
                        if total_time_spent > 0 or progress['progress'] > 0:
                            status = CourseStatus.in_progress
                        else:
                            status = CourseStatus.not_started

                    posts = 0
                    try:
                        cc_user = cc.User(id=user.id, course_id=course_key).to_dict()
                        posts = cc_user.get('comments_count', 0) + cc_user.get('threads_count', 0)
                    except (cc.CommentClient500Error, cc.CommentClientRequestError, ConnectionError):
                        pass

                    cls.objects.update_or_create(
                        created=day,
                        user=user,
                        course_id=course_key,
                        defaults={'org': course_key.org,
                                  'total_time_spent': total_time_spent,
                                  'status': status,
                                  'progress': progress['progress'],
                                  'badges': format_badges(progress['nb_trophies_earned'], progress['nb_trophies_possible']),
                                  'current_score': progress['current_score'],
                                  'posts': posts,
                                  'enrollment_date': enrollment.created,
                                  'completion_date': enrollment.completed})

                    LearnerBadgeDailyReport.update_or_create(course_key, user, progress['trophies_by_chapter'])
            return report_needs_update
        return False


class LearnerSectionDailyReportMockup(object):
    def __init__(self, learner_section_daily_report, total_time_spent):
        self.course_id = learner_section_daily_report.course_id
        self.user = learner_section_daily_report.user
        self.section_key = learner_section_daily_report.section_key
        self.section_name = learner_section_daily_report.section_name
        self.total_time_spent = total_time_spent


class LearnerSectionDailyReport(TimeModel, ReportMixin):
    class Meta(object):
        app_label = "triboo_analytics"
        get_latest_by = "created"
        unique_together = ('created', 'user', 'course_id', 'section_key')
        index_together = (['created', 'user', 'course_id', 'section_key'],
                          ['created', 'course_id'])

    user = models.ForeignKey(User, null=False)
    course_id = CourseKeyField(max_length=255, db_index=True, null=False)
    section_key = models.CharField(max_length=100, null=False)
    section_name = models.CharField(max_length=512, null=False)
    total_time_spent = models.PositiveIntegerField(default=0)


    @classmethod
    def update_or_create(cls, enrollment, sections):
        day = timezone.now().date()
        yesterday = timezone.now() + timezone.timedelta(days=-1)
        for section_combined_url, section_combined_display_name in sections.iteritems():
            total_time_spent = (TrackingLog.objects.filter(user_id=enrollment.user.id,
                                                           section=section_combined_url,
                                                           time__gte=enrollment.created).aggregate(
                                                               Sum('time_spent')).get('time_spent__sum') or 0)
            total_time_spent = int(round(total_time_spent))
            cls.objects.update_or_create(created=day,
                                         user=enrollment.user,
                                         course_id=enrollment.course_id,
                                         section_key=section_combined_url,
                                         defaults={'section_name': section_combined_display_name,
                                                   'total_time_spent': total_time_spent})


    @classmethod
    def filter_by_period(cls, course_id, date_time=None, period_start=None, **kwargs):
        day = date_time.date() if date_time else timezone.now().date()
        new_results = cls.objects.filter(course_id=course_id, created=day, **kwargs)
        results = []
        if period_start:
            old_results = cls.objects.filter(course_id=course_id, created=period_start, **kwargs)
            old_time_spent_by_user = { (r.user_id, r.section_key): r.total_time_spent for r in old_results }
            for r in new_results:
                old_time_spent = 0
                try:
                    old_time_spent = old_time_spent_by_user[(r.user_id, r.section_key)]
                except KeyError:
                    pass
                results.append(LearnerSectionDailyReportMockup(r, (r.total_time_spent - old_time_spent)))
        else:
            results = new_results

        dataset = {}
        sections = {}
        for res in results:
            key = res.user.id
            if key not in dataset.keys():
                dataset[key] = {'user': res.user}
            dataset[key][res.section_key] = res.total_time_spent
            sections[res.section_key] = res.section_name

        return dataset.values(), sections


class Badge(models.Model):
    class Meta(object):
        app_label = "triboo_analytics"
        unique_together = ['course_id', 'badge_hash']
        index_together = ['course_id', 'badge_hash']

    course_id = CourseKeyField(max_length=255, db_index=True, null=False)
    badge_hash = models.CharField(max_length=100, db_index=True, null=False)
    order = models.PositiveSmallIntegerField(default=0)
    grading_rule = models.CharField(max_length=255, null=False, blank=False)
    section_name = models.CharField(max_length=255, null=False, blank=False)
    threshold = models.PositiveSmallIntegerField(default=0, validators=[MaxValueValidator(100)])


    @classmethod
    def get_badge_hash(cls, grading_rule, chapter_url, section_url):
        m = hashlib.md5()
        badge = "%s-%s-%s" % (grading_rule.encode('utf-8'),
                              chapter_url.encode('utf-8'),
                              section_url.encode('utf-8'))
        m.update(badge)
        return m.hexdigest()


    @classmethod
    def refresh(cls, course_key, course, analytics_worker):
        hashes = []

        progress = CourseGradeFactory().get_progress(analytics_worker, course)
        i = 0
        for chapter in progress['trophies_by_chapter']:
            for trophy in chapter['trophies']:
                i += 1
                badge_hash = cls.get_badge_hash(trophy['section_format'],
                                            chapter['url'],
                                            trophy['section_url'])
                hashes.append(badge_hash)
                cls.objects.update_or_create(course_id=course_key,
                                             badge_hash=badge_hash,
                                             defaults={'order': i,
                                                       'grading_rule': trophy['section_format'],
                                                       'section_name': trophy['section_name'],
                                                       'threshold': (trophy['threshold'] * 100)})

        course_badges = cls.objects.filter(course_id=course_key).exclude(badge_hash__in=hashes).delete()


class LearnerBadgeDailyReport(UnicodeMixin, ReportMixin, TimeModel):
    class Meta(object):
       app_label = "triboo_analytics"
       get_latest_by = "created"
       unique_together = ['created', 'user', 'badge']
       index_together = ['created', 'user', 'badge']

    user = models.ForeignKey(User, null=False, on_delete=models.CASCADE)
    badge = models.ForeignKey(Badge, null=False, on_delete=models.CASCADE)
    score = models.FloatField(default=0, null=True, blank=True)
    success = models.BooleanField(default=False)
    success_date = models.DateTimeField(default=None, null=True, blank=True)


    @classmethod
    def update_or_create(cls, course_key, user, trophies_by_chapter):
        day = timezone.now().date()
        for chapter in trophies_by_chapter:
            for trophy in chapter['trophies']:
                badge_hash = Badge.get_badge_hash(trophy['section_format'],
                                                  chapter['url'],
                                                  trophy['section_url'])
                try:
                    badge = Badge.objects.get(course_id=course_key, badge_hash=badge_hash)
                except Badge.DoesNotExist:
                    logger.error("user_id=%d - course=%s - progress trophy %s (%s %s) does not exist in Badge" % (
                        user.id, course_key, badge_hash, chapter['chapter_name'], trophy['section_name']))
                    continue

                score = trophy['result'] * 100
                success = True if score >= badge.threshold else False
                cls.objects.update_or_create(created=day,
                                             user=user,
                                             badge=badge,
                                             defaults={'score': score,
                                                       'success': success})


class LearnerDailyReportMockup(object):
    def __init__(self, learner_daily_report, total_time_spent):
        self.org = learner_daily_report.org
        self.user = learner_daily_report.user
        self.enrollments = learner_daily_report.enrollments
        self.average_final_score = learner_daily_report.average_final_score
        self.badges = learner_daily_report.badges
        self.posts = learner_daily_report.posts
        self.finished = learner_daily_report.finished
        self.failed = learner_daily_report.failed
        self.not_started = learner_daily_report.not_started
        self.in_progress = learner_daily_report.in_progress
        self.total_time_spent = total_time_spent


class LearnerDailyReport(UnicodeMixin, ReportMixin, TimeModel):
    class Meta(object):
        app_label = "triboo_analytics"
        get_latest_by = "created"
        unique_together = ('created', 'user', 'org')
        index_together = ['created', 'user', 'org']

    user = models.ForeignKey(User, null=False)
    org = models.CharField(max_length=255, db_index=True, null=False)
    enrollments = models.PositiveIntegerField(default=0)
    average_final_score = models.PositiveSmallIntegerField(default=0)
    badges = models.CharField(max_length=20, default="0 / 0")
    posts = models.PositiveIntegerField(default=0)
    finished = models.PositiveSmallIntegerField(default=0, verbose_name=CourseStatus.verbose_names[CourseStatus.finished])
    failed = models.PositiveSmallIntegerField(default=0, verbose_name=CourseStatus.verbose_names[CourseStatus.failed])
    not_started = models.PositiveSmallIntegerField(default=0, verbose_name=CourseStatus.verbose_names[CourseStatus.not_started])
    in_progress = models.PositiveSmallIntegerField(default=0, verbose_name=CourseStatus.verbose_names[CourseStatus.in_progress])
    total_time_spent = models.PositiveIntegerField(default=0)

    @classmethod
    def generate_today_reports(cls, learner_course_reports, org_combinations):
        reports_by_user_org = defaultdict(list)
        for report in learner_course_reports:
            reports_by_user_org[(report.user_id, report.org)].append(report)

        for (user_id, org), reports in reports_by_user_org.iteritems():
            logger.debug("learner report for user_id=%d org=%s" % (user_id, org))
            cls.update_or_create(user_id, org, reports)

        for combination in org_combinations:
            cls.update_or_create_combined_orgs(combination, reports_by_user_org)

        ReportLog.update_or_create(learner=timezone.now())


    @classmethod
    def update_or_create(cls, user_id, org, learner_course_reports):
        posts = 0
        badges_earned = 0
        badges_possible = 0
        finished = 0
        failed = 0
        in_progress = 0
        not_started = 0
        total_score = 0
        nb_completed_courses = 0
        for report in learner_course_reports:
            posts += report.posts
            earned, possible = get_badges(report.badges)
            badges_earned += earned
            badges_possible += possible
            if report.status == CourseStatus.finished:
                finished += 1
            elif report.status == CourseStatus.failed:
                failed += 1
            elif report.status == CourseStatus.in_progress:
                in_progress += 1
            elif report.status == CourseStatus.not_started:
                not_started += 1
            if report.status in [CourseStatus.finished, CourseStatus.failed]:
                total_score += report.current_score
                nb_completed_courses += 1

        average_final_score = 0
        if nb_completed_courses > 0:
            average_final_score = total_score / nb_completed_courses

        total_time_spent = (LearnerVisitsDailyReport.objects.filter(user_id=user_id).aggregate(
                                Sum('time_spent')).get('time_spent__sum') or 0)

        cls.objects.update_or_create(
            created=timezone.now().date(),
            user_id=user_id,
            org=org,
            defaults={'enrollments': len(learner_course_reports),
                      'average_final_score': average_final_score,
                      'badges': format_badges(badges_earned, badges_possible),
                      'posts': posts,
                      'finished': finished,
                      'failed': failed,
                      'not_started': not_started,
                      'in_progress': in_progress,
                      'total_time_spent': total_time_spent})


    @classmethod
    def update_or_create_combined_orgs(cls, org_combination, learner_course_reports_by_user_org):
        combined_org = get_combined_org(org_combination)

        learner_course_reports_by_user = defaultdict(list)
        for (user_id, org), reports in learner_course_reports_by_user_org.iteritems():
            if org in org_combination:
                learner_course_reports_by_user[user_id] += reports

        for user_id, reports in learner_course_reports_by_user.iteritems():
            logger.debug("learner report for user_id=%d org=%s" % (user_id, combined_org))
            cls.update_or_create(user_id, combined_org, reports)


    @classmethod
    def filter_by_period(cls, org, date_time=None, period_start=None, **kwargs):
        day = date_time.date() if date_time else timezone.now().date()
        new_results = cls.objects.filter(org=org, created=day, **kwargs)
        for new_res in new_results:
            logger.info("LAETITIA -- %s" % new_res)
        if period_start:
            results = []
            old_results = cls.objects.filter(org=org, created=period_start, **kwargs)
            for old_res in old_results:
                logger.info("LAETITIA -- %s" % old_res)
            old_time_spent_by_user = { r.user_id: r.total_time_spent for r in old_results }
            for r in new_results:
                old_time_spent = 0
                try:
                    old_time_spent = old_time_spent_by_user[r.user_id]
                except KeyError:
                    pass
                results.append(LearnerDailyReportMockup(r, (r.total_time_spent - old_time_spent)))
            return results
        return new_results
        

class CourseDailyReport(UnicodeMixin, ReportMixin, UniqueVisitorsMixin, TimeModel):
    class Meta(object):
        app_label = "triboo_analytics"
        get_latest_by = "created"
        unique_together = ('created', 'course_id')
        index_together = ['created', 'course_id']

    course_id = CourseKeyField(max_length=255, db_index=True, null=False)
    enrollments = models.PositiveIntegerField(default=0)
    unique_visitors = models.PositiveIntegerField(default=0)
    average_final_score = models.PositiveSmallIntegerField(default=0)
    posts = models.PositiveIntegerField(default=0)
    finished = models.PositiveIntegerField(default=0, verbose_name=CourseStatus.verbose_names[CourseStatus.finished])
    failed = models.PositiveIntegerField(default=0, verbose_name=CourseStatus.verbose_names[CourseStatus.failed])
    in_progress = models.PositiveIntegerField(default=0, verbose_name=CourseStatus.verbose_names[CourseStatus.in_progress])
    not_started = models.PositiveIntegerField(default=0, verbose_name=CourseStatus.verbose_names[CourseStatus.not_started])
    average_complete_time = models.PositiveIntegerField(default=0)


    @classmethod
    def generate_today_reports(cls, learner_course_reports):
        reports_by_course = defaultdict(list)
        for report in learner_course_reports:
            reports_by_course[report.course_id].append(report)

        for course_id, reports in reports_by_course.iteritems():
            logger.debug("course report for course_id=%s" % course_id)
            cls.update_or_create(course_id, reports)

        ReportLog.update_or_create(course=timezone.now())


    @classmethod
    def update_or_create(cls, course_id, learner_course_reports):
        posts = 0
        finished = 0
        failed = 0
        in_progress = 0
        not_started = 0
        nb_completed_courses = 0
        total_score = 0
        total_time = 0
        for report in learner_course_reports:
            posts += report.posts
            if report.status == CourseStatus.finished:
                finished += 1
            elif report.status == CourseStatus.failed:
                failed += 1
            elif report.status == CourseStatus.in_progress:
                in_progress += 1
            elif report.status == CourseStatus.not_started:
                not_started += 1
            if report.status in [CourseStatus.finished, CourseStatus.failed]:
                total_score += report.current_score
                total_time += report.total_time_spent
                nb_completed_courses += 1

        average_final_score = 0
        average_complete_time = 0
        if nb_completed_courses > 0:
            average_final_score = total_score / nb_completed_courses
            average_complete_time = total_time / nb_completed_courses

        today_unique_visitors = (LearnerVisitsDailyReport.filter_by_day(course_id=course_id).aggregate(
                                    Count('user_id', distinct=True)).get('user_id__count') or 0)

        cls.objects.update_or_create(
            created=timezone.now().date(),
            course_id=course_id,
            defaults={'enrollments': len(learner_course_reports),
                      'unique_visitors': today_unique_visitors,
                      'average_final_score': average_final_score,
                      'posts': posts,
                      'finished': finished,
                      'failed': failed,
                      'in_progress': in_progress,
                      'not_started': not_started,
                      'average_complete_time': average_complete_time})


    @classmethod
    def get_enrollments_csv_data(cls, course_id):
        course_overview = CourseOverview.objects.get(id=course_id)
        enrollments_csv_data = ""
        enrollments = cls.objects.filter(course_id=course_id, created__gte=course_overview.start
                        ).values('created', 'enrollments').order_by('created')
        for e in enrollments:
            enrollments_csv_data += "%s,%d\\n" % (e['created'].strftime('%d-%m-%Y'), e['enrollments'])
        return enrollments_csv_data


    @classmethod
    def update_or_create_unique_visitors(cls, day, course_id):
        unique_visitors = (LearnerVisitsDailyReport.filter_by_day(date_time=day, course_id=course_id).aggregate(
                            Count('user_id', distinct=True)).get('user_id__count') or 0)
        cls.objects.update_or_create(
            created=day,
            course_id=course_id,
            defaults={'unique_visitors': unique_visitors})


    @classmethod
    def get_unique_visitors_csv_data(cls, course_id, from_date=None, to_date=None):
        course_overview = CourseOverview.objects.get(id=course_id)

        unique_visitors = cls.objects.filter(course_id=course_id, created__gte=course_overview.start)


        if from_date:
            if course_overview.start > from_date:
                from_date = course_overview.start
            if to_date:
                unique_visitors = cls.objects.filter(course_id=course_id,
                                                     created__gte=from_date,
                                                     created__lte=to_date)
            else:
                unique_visitors = cls.objects.filter(course_id=course_id,
                                                     created__gte=from_date)
        else:
            if to_date:
                unique_visitors = cls.objects.filter(course_id=course_id,
                                                     created__gte=course_overview.start,
                                                     created__lte=to_date)
            else:
                unique_visitors = cls.objects.filter(course_id=course_id,
                                                     created__gte=course_overview.start)

        return cls._get_unique_visitors_csv_data(unique_visitors)


class MicrositeDailyReport(UnicodeMixin, ReportMixin, UniqueVisitorsMixin, TimeModel):
    class Meta:
        app_label = "triboo_analytics"
        get_latest_by = "created"
        unique_together = ('created', 'org')
        index_together = ['created', 'org']

    org = models.CharField(max_length=255, null=False)
    users = models.PositiveIntegerField(default=0)
    courses = models.PositiveIntegerField(default=0)
    finished = models.PositiveIntegerField(default=0)
    unique_visitors = models.PositiveIntegerField(default=0)
    average_time_spent = models.PositiveIntegerField(default=0)
    total_time_spent_on_mobile = models.PositiveIntegerField(default=0)
    total_time_spent_on_desktop = models.PositiveIntegerField(default=0)

    @classmethod
    def generate_today_reports(cls, course_ids, learner_course_reports, org_combinations):
        course_ids_by_org = defaultdict(list)
        for course_id in course_ids:
            course_ids_by_org[course_id.org].append(course_id)

        reports_by_org = defaultdict(list)
        for report in learner_course_reports:
            reports_by_org[report.org].append(report)

        for org, reports in reports_by_org.iteritems():
            logger.debug("microsite report for org=%s" % org)
            cls.update_or_create(org, course_ids_by_org[org], reports)

        for combination in org_combinations:
            cls.update_or_create_combined_orgs(combination, reports_by_org)

        ReportLog.update_or_create(microsite=timezone.now())


    @classmethod
    def update_or_create(cls, org, course_ids, learner_course_reports):
        users = set()
        finished = 0
        for report in learner_course_reports:
            users.add(report.user_id)
            if report.status == CourseStatus.finished:
                finished += 1

        total_time_spent_on_mobile = (LearnerVisitsDailyReport.objects.filter(
                                        org=org, course_id__in=course_ids, device="mobile").aggregate(
                                        Sum('time_spent')).get('time_spent__sum') or 0)
        total_time_spent_on_desktop = (LearnerVisitsDailyReport.objects.filter(
                                        org=org, course_id__in=course_ids, device="desktop").aggregate(
                                        Sum('time_spent')).get('time_spent__sum') or 0)

        today_unique_visitors = (LearnerVisitsDailyReport.filter_by_day(org=org).aggregate(
                                    Count('user_id', distinct=True)).get('user_id__count') or 0)

        all_unique_visitors = (LearnerVisitsDailyReport.objects.filter(org=org).aggregate(
                                Count('user_id', distinct=True)).get('user_id__count') or 0)
        average_time_spent = 0
        if all_unique_visitors > 0:
            average_time_spent = (total_time_spent_on_mobile + total_time_spent_on_desktop) / all_unique_visitors

        cls.objects.update_or_create(
            created=timezone.now().date(),
            org=org,
            defaults={'users': len(users),
                      'courses': len(course_ids),
                      'finished': finished,
                      'unique_visitors': today_unique_visitors,
                      'average_time_spent': average_time_spent,
                      'total_time_spent_on_mobile': total_time_spent_on_mobile,
                      'total_time_spent_on_desktop': total_time_spent_on_desktop})


    @classmethod
    def update_or_create_combined_orgs(cls, org_combination, learner_course_reports_by_org):
        combined_org = get_combined_org(org_combination)

        learner_course_reports = []
        courses = 0
        finished = 0
        total_time_spent_on_mobile = 0
        total_time_spent_on_desktop = 0

        for org in org_combination:
            microsite_report = cls.get_by_day(org=org)
            if not microsite_report:
                logger.error("combined microsite report for %s could not be generated: no report found for %s" % (
                    org_combination, org))
                return
            learner_course_reports += learner_course_reports_by_org[org]
            courses += microsite_report.courses
            finished += microsite_report.finished
            total_time_spent_on_mobile += microsite_report.total_time_spent_on_mobile
            total_time_spent_on_desktop += microsite_report.total_time_spent_on_desktop

        users = set()
        for report in learner_course_reports:
            users.add(report.user_id)

        today_unique_visitors = (LearnerVisitsDailyReport.filter_by_day(org__in=org_combination).aggregate(
                                Count('user_id', distinct=True)).get('user_id__count') or 0)

        all_unique_visitors = (LearnerVisitsDailyReport.objects.filter(org__in=org_combination).aggregate(
                                Count('user_id', distinct=True)).get('user_id__count') or 0)
        average_time_spent = 0
        if all_unique_visitors > 0:
            average_time_spent = (total_time_spent_on_mobile + total_time_spent_on_desktop) / all_unique_visitors

        logger.debug("microsite report for org=%s" % combined_org)
        cls.objects.update_or_create(
            created=timezone.now().date(),
            org=combined_org,
            defaults={'users': len(users),
                      'courses': courses,
                      'finished': finished,
                      'unique_visitors': today_unique_visitors,
                      'average_time_spent': average_time_spent,
                      'total_time_spent_on_mobile': total_time_spent_on_mobile,
                      'total_time_spent_on_desktop': total_time_spent_on_desktop})


    @classmethod
    def update_or_create_unique_visitors(cls, day, org):
        unique_visitors = (LearnerVisitsDailyReport.filter_by_day(date_time=day, org=org).aggregate(
                            Count('user_id', distinct=True)).get('user_id__count') or 0)
        cls.objects.update_or_create(
            created=day,
            org=org,
            defaults={'unique_visitors': unique_visitors})


    @classmethod
    def update_or_create_combined_orgs_unique_visitors(cls, day, org_combination):
        combined_org = get_combined_org(org_combination)
        learner_visits = LearnerVisitsDailyReport.objects.none()
        for org in org_combination:
            org_learner_visits = LearnerVisitsDailyReport.filter_by_day(date_time=day, org=org)
            learner_visits = learner_visits | org_learner_visits
        unique_visitors = (learner_visits.aggregate(Count('user_id', distinct=True)).get('user_id__count') or 0)
        cls.objects.update_or_create(
            created=day,
            org=combined_org,
            defaults={'unique_visitors': unique_visitors})


    @classmethod
    def get_unique_visitors_csv_data(cls, org, from_date=None, to_date=None):
        if from_date:
            if to_date:
                unique_visitors = cls.objects.filter(org=org, created__gte=from_date, created__lte=to_date)
            else:
                unique_visitors = cls.objects.filter(org=org, created__gte=from_date)
        else:
            if to_date:
                unique_visitors = cls.objects.filter(org=org, created__lte=to_date)
            else:
                unique_visitors = cls.objects.filter(org=org)

        return cls._get_unique_visitors_csv_data(unique_visitors)


class CountryDailyReport(UnicodeMixin, ReportMixin, TimeModel):
    class Meta:
        app_label = "triboo_analytics"
        get_latest_by = "created"
        unique_together = ('created', 'org', 'country')
        index_together = ['created', 'org']

    org = models.CharField(max_length=255, null=False)
    country = CountryField(null=True)
    nb_users = models.PositiveIntegerField(default=0)

    @classmethod
    def generate_today_reports(cls, learner_course_reports, org_combinations):
        reports_by_org = defaultdict(list)
        for report in learner_course_reports:
            reports_by_org[report.org].append(report)

        for org, reports in reports_by_org.iteritems():
            logger.debug("country reports for org=%s" % org)
            cls.update_or_create(org, reports)

        for combination in org_combinations:
            cls.update_or_create_combined_orgs(combination, reports_by_org)

        ReportLog.update_or_create(country=timezone.now())



    @classmethod
    def update_or_create(cls, org, learner_course_reports):
        users_by_country = defaultdict(int)
        users = []
        for report in learner_course_reports:
            if report.user.id not in users:
                users.append(report.user.id)
                users_by_country[report.user.profile.country] += 1

        for country, nb_users in users_by_country.iteritems():
            cls.objects.update_or_create(
                created=timezone.now().date(),
                org=org,
                country=country,
                defaults={'nb_users': nb_users})


    @classmethod
    def update_or_create_combined_orgs(cls, org_combination, learner_course_reports_by_org):
        combined_org = get_combined_org(org_combination)

        learner_course_reports = []
        for org in org_combination:
            learner_course_reports += learner_course_reports_by_org[org]

        logger.debug("country reports for org=%s" % combined_org)
        cls.update_or_create(combined_org, learner_course_reports)


class IltModule(TimeStampedModel):
    class Meta(object):
        app_label = "triboo_analytics"

    id = UsageKeyField(db_index=True, primary_key=True, max_length=255)
    course_id = CourseKeyField(max_length=255, null=False)
    course_display_name = models.TextField(null=False)
    course_country = models.TextField(null=True, blank=True)
    course_tags = models.TextField(null=True, blank=True)
    chapter_display_name = models.TextField(null=True, blank=True)
    section_display_name = models.TextField(null=True, blank=True)


class IltSession(TimeStampedModel):
    class Meta(object):
        app_label = "triboo_analytics"
        unique_together = ('ilt_module', 'session_nb')
        index_together = ['ilt_module', 'session_nb']

    ilt_module = models.ForeignKey(IltModule, null=False)
    session_nb = models.PositiveSmallIntegerField(null=True)
    org = models.CharField(max_length=255, db_index=True, null=True, default=None)
    start = models.DateTimeField(default=None, null=True, blank=True)
    end = models.DateTimeField(default=None, null=True, blank=True)
    duration = models.PositiveSmallIntegerField(default=0)
    seats = models.PositiveSmallIntegerField(default=0)
    ack_attendance_sheet = models.BooleanField(default=False)
    location_id = models.TextField(null=True, blank=True, default=None)
    location = models.TextField(null=True, blank=True, default=None)
    address = models.TextField(null=True, blank=True, default=None)
    zip_code = models.TextField(null=True, blank=True, default=None)
    city = models.TextField(null=True, blank=True, default=None)
    area = models.TextField(null=True, blank=True, default=None)
    enrollees = models.PositiveSmallIntegerField(default=0)
    attendees = models.PositiveSmallIntegerField(default=0)
    is_active = models.BooleanField(default=True)

    def session_id(self):
        module_id = "%s" % self.ilt_module.id
        start = module_id.find("@ilt+block@")
        if start > 0:
            module_id = module_id[start+11:]
        return "%s_%d" % (module_id, self.session_nb)

    @classmethod
    def get_ilt_blocks(cls):
        overviews = CourseOverview.objects.all()
        ilt_blocks = {}
        for overview in overviews:
            course_ilt_blocks = []
            try:
                course_details = CourseDetails.fetch(overview.id)
                outline = course_structure(overview.id)
                outline = outline['blocks']
                for block_id, block in outline.iteritems():
                    if block['type'] == "ilt":
                        course_ilt_blocks.append(block_id)
                        ilt_blocks[block_id] = {
                            'course_id': overview.id,
                            'course_display_name': overview.display_name,
                            'course_country': course_details.course_country,
                            'course_tags': ", ".join(course_details.vendor)
                        }
                    for child in block['children']:
                        outline[child]['parent'] = block_id

                for ilt_block_id in course_ilt_blocks:
                    parent_id = outline[ilt_block_id]['parent']
                    vertical = outline[parent_id]
                    sequential = outline[vertical['parent']]
                    ilt_blocks[ilt_block_id]['section_display_name'] = sequential['display_name']
                    chapter = outline[sequential['parent']]
                    ilt_blocks[ilt_block_id]['chapter_display_name'] = chapter['display_name']

            except CourseStructureNotAvailableError:
                pass

        return ilt_blocks


    @classmethod
    def generate_today_reports(cls):
        cls.objects.all().update(is_active=False)
        IltLearnerReport.objects.all().update(is_active=False)

        ilt_blocks = cls.get_ilt_blocks()
        for ilt_block_id, ilt_block_info in ilt_blocks.iteritems():
            logger.info("ILT Module %s" % ilt_block_id)
            ilt_module_id = UsageKey.from_string(ilt_block_id)
            ilt_module, _ = IltModule.objects.update_or_create(
                                id=ilt_module_id,
                                defaults={'course_id': ilt_block_info['course_id'],
                                          'course_display_name': ilt_block_info['course_display_name'],
                                          'course_country': ilt_block_info['course_country'],
                                          'course_tags': ilt_block_info['course_tags'],
                                          'chapter_display_name': ilt_block_info['chapter_display_name'],
                                          'section_display_name': ilt_block_info['section_display_name']})

            sessions = XModuleUserStateSummaryField.objects.filter(usage_id=ilt_module_id,
                                                                   field_name="sessions").only('value')
            if len(sessions) == 1:
                sessions = json.loads(sessions[0].value)
                if "counter" in sessions.keys():
                    del(sessions['counter'])

            else:
                sessions = {}
                logger.info("ILT Module %s has no sessions => pass" % ilt_block_id)
                pass

            registrations = XModuleUserStateSummaryField.objects.filter(usage_id=ilt_module_id,
                                                                        field_name="enrolled_users").only('value')
            registrations = json.loads(registrations[0].value) if len(registrations) == 1 else {}

            scores = StudentModule.objects.filter(module_state_key=ilt_module_id).only('student_id', 'grade')

            users = {}
            for score in scores:
                users[score.student.id] = {
                    'user': score.student,
                    'session_nb': None,
                    'registration': None,
                    'attendee': (score.grade > 0) if score.grade else False
                }
            for session_nb, session_registrations in registrations.iteritems():
                for user_id, registration in session_registrations.iteritems():
                    user_id = int(user_id)
                    if user_id in users.keys():
                        users[user_id]['session_nb'] = session_nb
                        users[user_id]['registration'] = registration
                    else:
                        try:
                            user = User.objects.get(id=user_id)
                            users[user_id] = {
                                'user': user,
                                'session_nb': session_nb,
                                'registration': registration,
                                'attendee': False
                            }
                        except User.DoesNotExist:
                            pass

            try:
                cls.update_or_create(ilt_module, ilt_module_id.org, sessions, users)
                IltLearnerReport.generate_today_reports(ilt_module, users)
            except Exception as err:  # pylint: disable=broad-except
                logger.error('Error with %s: %r', ilt_block_id, err)
                pass

        cls.objects.filter(is_active=False).delete()
        IltLearnerReport.objects.filter(is_active=False).delete()


    @classmethod
    def update_or_create(cls, ilt_module, org, sessions, users):
        for session_nb, session in sessions.iteritems():
            enrollees = 0
            attendees = 0
            for user_id, user_session in users.iteritems():
                if user_session['session_nb'] == session_nb:
                    if user_session['registration']['status'] in ["accepted", "confirmed"]:
                        enrollees += 1
                    if user_session['attendee']:
                        attendees += 1
            cls.objects.update_or_create(ilt_module=ilt_module,
                                         session_nb=session_nb,
                                         defaults={'start': datetime.strptime(session['start_at'], '%Y-%m-%dT%H:%M').replace(tzinfo=UTC),
                                                   'end': datetime.strptime(session['end_at'], '%Y-%m-%dT%H:%M').replace(tzinfo=UTC),
                                                   'duration': session.get('duration', 0),
                                                   'seats': session['total_seats'],
                                                   'ack_attendance_sheet': session.get('ack_attendance_sheet', False),
                                                   'location_id': session.get('location_id', ""),
                                                   'location': session['location'],
                                                   'address': session.get('address', ""),
                                                   'zip_code': session.get('zip_code', ""),
                                                   'city': session.get('city', ""),
                                                   'area': session.get('area_region', ""),
                                                   'org': org,
                                                   'enrollees': enrollees,
                                                   'attendees': attendees,
                                                   'is_active': True})


class IltLearnerReport(TimeModel):
    class Meta(object):
        app_label = "triboo_analytics"
        unique_together = ('ilt_module', 'user')
        index_together = ['ilt_module', 'user']

    ilt_module = models.ForeignKey(IltModule, db_index=True, null=False)
    user = models.ForeignKey(User, db_index=True, null=False)
    org = models.CharField(max_length=255, db_index=True, null=True, default=None)
    ilt_session = models.ForeignKey(IltSession, null=True)
    STATUS_CHOICES = (
        ('pending', ugettext_noop("Pending")),
        ('accepted', ugettext_noop("Accepted")),
        ('confirmed', ugettext_noop("Confirmed")),
        ('refused', ugettext_noop("Refused"))
    )
    status = models.CharField(null=False, max_length=9, choices=STATUS_CHOICES)
    attendee = models.BooleanField(default=False)
    outward_trips = models.PositiveSmallIntegerField(default=0)
    return_trips = models.PositiveSmallIntegerField(default=0)
    accommodation = models.BooleanField(default=False)
    comment = models.TextField(null=True, blank=True, default=None)
    hotel = models.TextField(null=True, blank=True, default=None)
    is_active = models.BooleanField(default=True)


    @classmethod
    def generate_today_reports(cls, ilt_module, users):
        for _, user_session in users.iteritems():
            cls.update_or_create(ilt_module, user_session)

    @classmethod
    def update_or_create(cls, ilt_module, user_session):
        ilt_session = None
        if user_session['session_nb']:
            ilt_session = IltSession.objects.get(ilt_module=ilt_module, session_nb=user_session['session_nb'])

        status = "Confirmed"
        outward_trips = 1
        return_trips = 1
        accommodation = False
        comment = None
        hotel = None

        if user_session['registration']:
            status = user_session['registration']['status']
            outward_trips = user_session['registration']['number_of_one_way']
            return_trips = user_session['registration']['number_of_return']
            if user_session['registration']['accommodation'] == "yes":
                accommodation = True
            comment = user_session['registration']['comment']
            hotel = user_session['registration'].get('hotel', None)

        cls.objects.update_or_create(ilt_module=ilt_module,
                                     user=user_session['user'],
                                     defaults={'org': ilt_module.id.org,
                                               'ilt_session': ilt_session,
                                               'status': status,
                                               'attendee': user_session['attendee'],
                                               'outward_trips': outward_trips,
                                               'return_trips': return_trips,
                                               'accommodation': accommodation,
                                               'comment': comment,
                                               'hotel': hotel,
                                               'is_active': True})


def get_org_combinations():
    org_combinations = []
    for configuration in SiteConfiguration.objects.filter(enabled=True).all():
        course_org_filter = configuration.get_value('course_org_filter', None)
        if course_org_filter and isinstance(course_org_filter, list) and len(course_org_filter) > 1:
            org_combinations.append(course_org_filter)
    return org_combinations


def generate_today_reports(multi_process=False):
    try:
        User.objects.get(username=ANALYTICS_WORKER_USER)
    except User.DoesNotExist:
        create_analytics_worker()

    yesterday = timezone.now() + timezone.timedelta(days=-1)
    overviews = CourseOverview.objects.filter(start__lte=yesterday).only('id')
    course_ids = [o.id for o in overviews]

    logger.info("start updating course structures")
    for course_id in course_ids:
        update_course_structure.apply(args=[text_type(course_id)])

    logger.info("start updating tracking logs")
    tracking_log_helper = TrackingLogHelper(course_ids)
    tracking_log_helper.update_logs(day=yesterday)

    logger.info("start Learner Visits reports")
    LearnerVisitsDailyReport.generate_today_reports()

    last_analytics_success = None
    last_reportlog = ReportLog.get_latest()
    if last_reportlog:
        last_analytics_success = last_reportlog.created.date()

    if last_analytics_success:
        LearnerSectionDailyReport.filter_by_day(timezone.now()).delete()
        last_reports = LearnerSectionDailyReport.filter_by_day(last_reportlog.created, user__is_active=True)
        new_reports = [LearnerSectionDailyReport(created=timezone.now().date(),
                                                 user_id=report.user_id,
                                                 course_id=report.course_id,
                                                 section_key=report.section_key,
                                                 section_name=report.section_name,
                                                 total_time_spent=report.total_time_spent) for report in last_reports]
        LearnerSectionDailyReport.objects.bulk_create(new_reports)

        LearnerBadgeDailyReport.filter_by_day(timezone.now()).delete()
        last_reports = LearnerBadgeDailyReport.filter_by_day(last_reportlog.created, user__is_active=True)
        new_reports = [LearnerBadgeDailyReport(created=timezone.now().date(),
                                               user_id=report.user_id,
                                               badge_id=report.badge_id,
                                               success=report.success,
                                               success_date=report.success_date) for report in last_reports]
        LearnerBadgeDailyReport.objects.bulk_create(new_reports)



    logger.info("start Learner Course reports")
    LearnerCourseDailyReport.generate_today_reports(last_analytics_success, overviews, tracking_log_helper.sections_by_course, multi_process=multi_process)

    logger.info("start double checking generated Learner Course reports")
    check_generated_learner_course_reports(last_analytics_success, overviews, tracking_log_helper.sections_by_course)

    logger.info("fetch Learner Course reports")
    learner_course_reports = LearnerCourseDailyReport.filter_by_day().prefetch_related('user__profile')

    org_combinations = get_org_combinations()

    logger.info("start Learner reports")
    LearnerDailyReport.generate_today_reports(learner_course_reports, org_combinations)

    logger.info("start Course reports")
    CourseDailyReport.generate_today_reports(learner_course_reports)

    logger.info("start Microsite reports")
    MicrositeDailyReport.generate_today_reports(course_ids, learner_course_reports, org_combinations)

    logger.info("start Country reports")
    CountryDailyReport.generate_today_reports(learner_course_reports, org_combinations)

    logger.info("start ILT reports")
    IltSession.generate_today_reports()


def check_generated_learner_course_reports(last_analytics_success, overviews, sections_by_course):
    all_good = False
    course_last_updates = {o.id: o.modified.date() for o in overviews}
    course_ids_to_check = [o.id for o in overviews]
    while not all_good:
        course_ids_nok = []
        logger.info("new check round with %d courses" % len(course_ids_to_check))
        for course_id in course_ids_to_check:
            course_id_needs_fix = False
            logger.info("checking %s" % course_id)
            sections = sections_by_course["%s" % course_id]
            enrollments = CourseEnrollment.objects.filter(is_active=True, course_id=course_id, user__is_active=True)
            for enrollment in enrollments:
                if not LearnerCourseDailyReport.filter_by_day(course_id=course_id, user_id=enrollment.user_id).exists():
                    course_id_needs_fix = True
                    logger.info("missing report for user_id=%d => trying to generate it" % enrollment.user_id)
                    LearnerCourseDailyReport.generate_enrollment_report(last_analytics_success, course_last_updates[course_id], enrollment, sections)
            if course_id_needs_fix:
                course_ids_nok.append(course_id)
        if len(course_ids_nok) == 0:
            all_good = True
        else:
            course_ids_to_check = course_ids_nok




