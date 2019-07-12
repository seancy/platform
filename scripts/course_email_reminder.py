#!/usr/bin/env python
"""
This script is to check courses that have reminder settings.

It will be send email to students who have enrolled in the course
when the difference between the enrollment data and today matches one
of the reminders.

And when students automatically enrolled in the course, we send them
email and reset his/her status on this course and send remind email
again when the data matches
"""
from __future__ import division

import logging
import os
import time
from dateutil import relativedelta
from logging.handlers import TimedRotatingFileHandler

from django.conf import settings
from django.db.models import Q
from django.utils import timezone

from completion.models import BlockCompletion
from courseware.models import StudentModule
from instructor.enrollment import get_email_params, get_user_email_language, render_message_to_string
from lms.djangoapps.grades.config.models import PersistentGradesEnabledFlag
from lms.djangoapps.grades.models import (
    PersistentCourseGrade,
    PersistentCourseProgress,
    PersistentSubsectionGrade,
    PersistentSubsectionGradeOverride
)
from openedx.core.djangoapps.content.course_overviews.models import CourseOverview
from student.models import CourseEnrollment
from util.email_utils import send_mail_with_alias as send_mail
from xmodule.modulestore.django import modulestore


logger = logging.getLogger("edx.scripts.course_email_reminder")

d = os.path.dirname('/edx/var/log/cms/course_email_reminder.log')
if not os.path.exists(d):
    os.makedirs(d)

log_handler = TimedRotatingFileHandler("/edx/var/log/cms/course_email_reminder.log",
                                       when="W0",
                                       backupCount=5,
                                       encoding="utf-8")
log_formatter = logging.Formatter('%(asctime)s [%(name)s] [%(filename)s:%(lineno)d] %(levelname)s  - %(message)s')
log_formatter.converter = time.gmtime
log_handler.setFormatter(log_formatter)
logger.addHandler(log_handler)


TIME_NOW = timezone.now()


def set_time(timez):
    """
    for testing
    """
    global TIME_NOW
    TIME_NOW = timez


def course_filter(course_id):
    descriptor = modulestore().get_course(course_id)
    if descriptor:
        return len(descriptor.reminder_info) > 0
    return False


def get_course_with_reminders():
    """
    get all the courses' ID that have course email reminders
    """

    # filter the course that not end yet or doesn't have end date
    overviews = CourseOverview.objects.all().filter(Q(end__gte=TIME_NOW) | Q(end=None))
    courses = [c.id for c in overviews if course_filter(c.id) and c.has_started()]
    return courses


def get_course_enrollment():
    """
    return a dict including unfinished course_enrollment
    and finished course_enrollment
    """
    unfinished = CourseEnrollment.objects.filter(
        course_id__in=get_course_with_reminders(),
        is_active=True,
        completed__isnull=True
    ).select_related('user')

    finished = CourseEnrollment.objects.filter(
        is_active=True,
        completed__isnull=False
    ).select_related('user')
    return {
        "unfinished": unfinished,
        "finished": finished
    }


def course_re_enroll(course_enrollment):
    """
    re-enroll a student in the course, reset the enrollment date and completed day
    and delete the student state
    """
    course_enrollment.created = timezone.now()
    course_enrollment.completed = None
    course_enrollment.save()
    student_modules = StudentModule.objects.filter(
        course_id=course_enrollment.course_id,
        student=course_enrollment.user
    )
    student_modules.delete()

    if PersistentGradesEnabledFlag(course_enrollment.course_id):
        try:
            grade = PersistentCourseGrade.read(course_enrollment.user_id, course_enrollment.course_id)
            grade.delete()
            logger.info("reset course grade for user: {user_name}, course_id: {course_id}".format(
                user_name=course_enrollment.user.username,
                course_id=course_enrollment.course_id
            ))
        except Exception as e:
            logger.error("failed to reset course grade for user: {user_name}, course_id: {course_id}, "
                         "reason: {reason}".format(user_name=course_enrollment.user.username,
                                                   course_id=course_enrollment.course_id,
                                                   reason=e
                                                   ))

        try:
            progress = PersistentCourseProgress.read(course_enrollment.user_id, course_enrollment.course_id)
            progress.percent_progress = 0
            progress.save()
            logger.info("reset course progress for user: {user_name}, course_id: {course_id}".format(
                user_name=course_enrollment.user.username,
                course_id=course_enrollment.course_id
            ))
        except Exception as e:
            logger.error("failed to reset course progress for user: {user_name}, course_id: {course_id}, "
                         "reason: {reason}".format(user_name=course_enrollment.user.username,
                                                   course_id=course_enrollment.course_id,
                                                   reason=e
                                                   ))

        try:
            completions = BlockCompletion.user_course_completion_queryset(
                course_enrollment.user, course_enrollment.course_id
            )
            completions.update(completion=0)
            logger.info("reset course page completions for user: {user_name}, course_id: {course_id}".format(
                user_name=course_enrollment.user.username,
                course_id=course_enrollment.course_id
            ))
        except Exception as e:
            logger.error("failed to reset course page completions for user: {user_name}, course_id: {course_id}, "
                         "reason: {reason}".format(user_name=course_enrollment.user.username,
                                                   course_id=course_enrollment.course_id,
                                                   reason=e
                                                   ))

        try:
            subsection_grades = PersistentSubsectionGrade.bulk_read_grades(
                course_enrollment.user_id, course_enrollment.course_id
            )
            for i in subsection_grades:
                i.earned_all = 0
                i.earned_graded = 0
                i.first_attempted = None
                i.save()
                try:
                    override = PersistentSubsectionGradeOverride.objects.get(grade=i)
                    override.delete()
                except PersistentSubsectionGradeOverride.DoesNotExist:
                    pass

            logger.info("reset course subsection grade for user: {user_name}, course_id: {course_id}".format(
                user_name=course_enrollment.user.username,
                course_id=course_enrollment.course_id
            ))
        except Exception as e:
            logger.error("failed to reset course subsection grade for user: {user_name}, course_id: {course_id}, "
                         "reason: {reason}".format(user_name=course_enrollment.user.username,
                                                   course_id=course_enrollment.course_id,
                                                   reason=e
                                                   ))


def send_re_enroll_email(course_enrollment):
    """
    send email to student who is automatically re-enrolled in the course
    """
    descriptor = modulestore().get_course(course_enrollment.course_id)
    re_enroll_time = descriptor.course_re_enroll_time

    # if the course doesn't have a automatically re-enroll time, just pass
    if not re_enroll_time:
        pass
    else:
        time_unit = descriptor.re_enroll_time_unit or 'month'
        completed = course_enrollment.completed
        r = relativedelta.relativedelta(TIME_NOW, completed)
        sending_mail = False
        if time_unit == 'month' and r.years*12 + r.months >= re_enroll_time:
            sending_mail = True
        elif time_unit == 'year' and r.years >= re_enroll_time:
            sending_mail = True

        if sending_mail:
            # sending_mail is true means we have to re-enroll the student in the course
            course_re_enroll(course_enrollment)
            course = course_enrollment.course_overview
            username = course_enrollment.user.first_name or course_enrollment.user.profile.name \
                       or course_enrollment.user.username
            params = get_email_params(course, True)
            params['finish_days'] = descriptor.course_finish_days
            params['username'] = username
            params['re_enroll_time'] = descriptor.course_re_enroll_time
            params['time_unit'] = time_unit
            params['email_address'] = course_enrollment.user.email
            subject, message = render_message_to_string(
                'emails/course_re_enroll_email_subject.txt',
                'emails/course_re_enroll_email_message.txt',
                params,
                language=get_user_email_language(course_enrollment.user)
            )
            subject = subject.strip('\n')
            try:
                send_mail(subject, message, settings.CONTACT_EMAIL, [course_enrollment.user.email], fail_silently=False)
                logger.info("send re_enroll_email to username: {username}, id: {user_id}, "
                            "email: {email}, course_id: {course_id}".format(
                                username=course_enrollment.user.username,
                                user_id=course_enrollment.user.id,
                                email=course_enrollment.user.email,
                                course_id=course_enrollment.course_id
                            ))
            except Exception:
                logger.exception(Exception)


def send_reminder_email(course_enrollment):
    """
    send reminder email to student, to reminder him/her the deadline of the course
    """
    descriptor = modulestore().get_course(course_enrollment.course_id)
    finish_days = descriptor.course_finish_days

    # if the course is required to finish within certain days, we check the reminder info,
    # otherwise do nothing
    if not finish_days:
        return

    created = course_enrollment.created
    delta = TIME_NOW - created
    send = False

    if descriptor.periodic_reminder_enabled and descriptor.periodic_reminder_day > 0:
        if delta.days > 0 and delta.days % descriptor.periodic_reminder_day == 0:
            send = True
    elif delta.days in descriptor.reminder_info:
        send = True

    if send:
        if delta.days > finish_days:
            overdue = True
            days_left = delta.days - finish_days
        else:
            overdue = False
            days_left = finish_days - delta.days
        time_unit = descriptor.re_enroll_time_unit or 'month'
        course = course_enrollment.course_overview
        username = course_enrollment.user.first_name or course_enrollment.user.profile.name \
                   or course_enrollment.user.username
        params = get_email_params(course, True)
        params['username'] = username
        params['overdue'] = overdue
        params['days_left'] = days_left
        params['finish_days'] = finish_days
        params['re_enroll_time'] = descriptor.course_re_enroll_time
        params['time_unit'] = time_unit
        params['email_address'] = course_enrollment.user.email
        subject, message = render_message_to_string(
            'emails/course_reminder_email_subject.txt',
            'emails/course_reminder_email_message.txt',
            params,
            language=get_user_email_language(course_enrollment.user)
        )
        subject = subject.strip('\n')
        try:
            send_mail(subject, message, settings.CONTACT_EMAIL, [course_enrollment.user.email], fail_silently=False)
            logger.info("send reminder_email to username: {username}, id: {user_id}, "
                        "email: {email}, course_id: {course_id}".format(
                            username=course_enrollment.user.username,
                            user_id=course_enrollment.user.id,
                            email=course_enrollment.user.email,
                            course_id=course_enrollment.course_id
                        ))
        except Exception:
            logger.exception(Exception)


def process_email():
    """
    send email to students
    """
    for enrollment in get_course_enrollment().get('finished'):
        send_re_enroll_email(enrollment)
    for enrollment in get_course_enrollment().get('unfinished'):
        send_reminder_email(enrollment)


if __name__ == '__main__':
    logger.info("start to send reminder emails...")
    process_email()
    logger.info("finish sending reminder emails.")
