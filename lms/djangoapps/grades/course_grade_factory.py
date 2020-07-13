"""
Course Grade Factory Class
"""
from __future__ import division
from collections import namedtuple
from datetime import datetime
from logging import getLogger

import dogstats_wrapper as dog_stats_api
from six import text_type

from courseware.models import StudentModule
from openedx.core.djangoapps.signals.signals import COURSE_GRADE_CHANGED, COURSE_GRADE_NOW_PASSED
from openedx.core.lib.gating.api import get_subsection_completion_percentage_with_gradebook_edit
from student.models import CourseEnrollment
from xmodule.modulestore.django import modulestore

from .config import assume_zero_if_absent, should_persist_grades
from .course_data import CourseData
from .course_grade import CourseGrade, ZeroCourseGrade
from .models import PersistentCourseGrade, PersistentCourseProgress, PersistentSubsectionGradeOverride, prefetch

log = getLogger(__name__)


class CourseGradeFactory(object):
    """
    Factory class to create Course Grade objects.
    """
    GradeResult = namedtuple('GradeResult', ['student', 'course_grade', 'error'])

    def read(
            self,
            user,
            course=None,
            collected_block_structure=None,
            course_structure=None,
            course_key=None,
            create_if_needed=True,
    ):
        """
        Returns the CourseGrade for the given user in the course.
        Reads the value from storage.
        If not in storage, returns a ZeroGrade if ASSUME_ZERO_GRADE_IF_ABSENT.
        Else if create_if_needed, computes and returns a new value.
        Else, returns None.

        At least one of course, collected_block_structure, course_structure,
        or course_key should be provided.
        """
        course_data = CourseData(user, course, collected_block_structure, course_structure, course_key)
        try:
            return self._read(user, course_data)
        except PersistentCourseGrade.DoesNotExist:
            if assume_zero_if_absent(course_data.course_key):
                return self._create_zero(user, course_data)
            elif create_if_needed:
                return self._update(user, course_data)
            else:
                return None

    def update(
            self,
            user,
            course=None,
            collected_block_structure=None,
            course_structure=None,
            course_key=None,
            force_update_subsections=False,
    ):
        """
        Computes, updates, and returns the CourseGrade for the given
        user in the course.

        At least one of course, collected_block_structure, course_structure,
        or course_key should be provided.
        """
        course_data = CourseData(user, course, collected_block_structure, course_structure, course_key)
        return self._update(
            user,
            course_data,
            force_update_subsections=force_update_subsections
        )

    def iter(
            self,
            users,
            course=None,
            collected_block_structure=None,
            course_key=None,
            force_update=False,
    ):
        """
        Given a course and an iterable of students (User), yield a GradeResult
        for every student enrolled in the course.  GradeResult is a named tuple of:

            (student, course_grade, err_msg)

        If an error occurred, course_grade will be None and err_msg will be an
        exception message. If there was no error, err_msg is an empty string.
        """
        # Pre-fetch the collected course_structure (in _iter_grade_result) so:
        # 1. Correctness: the same version of the course is used to
        #    compute the grade for all students.
        # 2. Optimization: the collected course_structure is not
        #    retrieved from the data store multiple times.
        course_data = CourseData(
            user=None, course=course, collected_block_structure=collected_block_structure, course_key=course_key,
        )
        stats_tags = [u'action:{}'.format(course_data.course_key)]
        for user in users:
            with dog_stats_api.timer('lms.grades.CourseGradeFactory.iter', tags=stats_tags):
                yield self._iter_grade_result(user, course_data, force_update)

    def _iter_grade_result(self, user, course_data, force_update):
        try:
            kwargs = {
                'user': user,
                'course': course_data.course,
                'collected_block_structure': course_data.collected_structure,
                'course_key': course_data.course_key
            }
            if force_update:
                kwargs['force_update_subsections'] = True

            method = CourseGradeFactory().update if force_update else CourseGradeFactory().read
            course_grade = method(**kwargs)
            return self.GradeResult(user, course_grade, None)
        except Exception as exc:  # pylint: disable=broad-except
            # Keep marching on even if this student couldn't be graded for
            # some reason, but log it for future reference.
            log.exception(
                'Cannot grade student %s in course %s because of exception: %s',
                user.id,
                course_data.course_key,
                text_type(exc)
            )
            return self.GradeResult(user, None, exc)

    @staticmethod
    def _create_zero(user, course_data):
        """
        Returns a ZeroCourseGrade object for the given user and course.
        """
        log.debug(u'Grades: CreateZero, %s, User: %s', unicode(course_data), user.id)
        return ZeroCourseGrade(user, course_data)

    @staticmethod
    def _read(user, course_data):
        """
        Returns a CourseGrade object based on stored grade information
        for the given user and course.
        """
        if not should_persist_grades(course_data.course_key):
            raise PersistentCourseGrade.DoesNotExist

        persistent_grade = PersistentCourseGrade.read(user.id, course_data.course_key)
        log.info(u'Grades: Read, %s, User: %s, %s', unicode(course_data), user.id, persistent_grade)

        return CourseGrade(
            user,
            course_data,
            persistent_grade.percent_grade,
            persistent_grade.letter_grade,
            persistent_grade.letter_grade is not u''
        )

    @staticmethod
    def _update(user, course_data, force_update_subsections=False):
        """
        Computes, saves, and returns a CourseGrade object for the
        given user and course.
        Sends a COURSE_GRADE_CHANGED signal to listeners and a
        COURSE_GRADE_NOW_PASSED if learner has passed course.
        """
        should_persist = should_persist_grades(course_data.course_key)

        if should_persist and force_update_subsections:
            prefetch(user, course_data.course_key)

        course_grade = CourseGrade(
            user,
            course_data,
            force_update_subsections=force_update_subsections
        )
        course_grade = course_grade.update()

        should_persist = should_persist and course_grade.attempted
        if should_persist:
            course_grade._subsection_grade_factory.bulk_create_unsaved()
            PersistentCourseGrade.update_or_create(
                user_id=user.id,
                course_id=course_data.course_key,
                course_version=course_data.version,
                course_edited_timestamp=course_data.edited_on,
                grading_policy_hash=course_data.grading_policy_hash,
                percent_grade=course_grade.percent,
                letter_grade=course_grade.letter_grade or "",
                passed=course_grade.passed,
            )

        COURSE_GRADE_CHANGED.send_robust(
            sender=None,
            user=user,
            course_grade=course_grade,
            course_key=course_data.course_key,
            deadline=course_data.course.end,
        )
        if course_grade.passed:
            COURSE_GRADE_NOW_PASSED.send(
                sender=CourseGradeFactory,
                user=user,
                course_id=course_data.course_key,
            )

        log.info(
            u'Grades: Update, %s, User: %s, %s, persisted: %s',
            course_data.full_string(), user.id, course_grade, should_persist,
        )

        return course_grade

    def update_course_completion_percentage(self, course_key, user, course_grade=None, enrollment=None):
        from triboo_analytics.models import LeaderBoard
        course_usage_key = modulestore().make_course_usage_key(course_key)
        overrides = PersistentSubsectionGradeOverride.objects.filter(
            grade__user_id=user.id,
            grade__course_id=course_key,
        ).select_related('grade')
        overridden_subsection_keys = [i.grade.usage_key for i in overrides]
        overridden_subsection_keys = list(set(overridden_subsection_keys))
        percent_progress = get_subsection_completion_percentage_with_gradebook_edit(
            course_usage_key, user, overrides=overridden_subsection_keys
        )
        log.info(u'Course Progress Calculate: %s, User: %s, Progress: %s',
                 unicode(course_key), user.id, percent_progress)
        if not enrollment:
            enrollment = CourseEnrollment.get_enrollment(user, course_key)
        if overrides.exists():
            if not course_grade:
                course_grade = self.read(user, course_key=course_key)
            passed = course_grade.passed
            try:
                # in case that it fails to fetch courseenrollment and returns None
                if passed:
                    if not enrollment.completed:
                        completion_date = datetime.today()
                        enrollment.completed = completion_date
                        enrollment.save()
                        log.info(
                            "Create completion date for user id %d / %s: %s" % (user.id, course_key, completion_date))
                        leader_board, _ = LeaderBoard.objects.get_or_create(user=user)
                        leader_board.course_completed = leader_board.course_completed + 1
                        leader_board.save()
                        log.info(
                            "updated course completed of leaderboard score "
                            "for user: {user_id}, course_id: {course_id}".format(
                                user_id=user.id,
                                course_id=course_key
                            )
                        )
                else:
                    if enrollment.completed:
                        enrollment.completed = None
                        enrollment.save()
                        log.info("Delete completion date for user id %d / %s" % (user.id, course_key))
                        leader_board, _ = LeaderBoard.objects.get_or_create(user=user)
                        if leader_board.course_completed > 0:
                            leader_board.course_completed = leader_board.course_completed - 1
                            leader_board.save()
                        log.info(
                            "updated course completed (-1) of leaderboard score "
                            "for user: {user_id}, course_id: {course_id}".format(
                                user_id=user.id,
                                course_id=course_key
                            )
                        )
            except AttributeError:
                pass
        else:
            try:
                # in case that it fails to fetch courseenrollment and returns None
                if percent_progress == 100:
                    if not enrollment.completed:
                        completion_date = datetime.today()
                        enrollment.completed = completion_date
                        enrollment.save()
                        log.info("Create completion date for user id %d / %s: %s" % (
                            user.id, course_key, completion_date))
                        leader_board, _ = LeaderBoard.objects.get_or_create(user=user)
                        leader_board.course_completed = leader_board.course_completed + 1
                        leader_board.save()
                        log.info(
                            "updated course completed of leaderboard score "
                            "for user: {user_id}, course_id: {course_id}".format(
                                user_id=user.id,
                                course_id=course_key
                            )
                        )
                else:
                    if enrollment.completed:
                        enrollment.completed = None
                        enrollment.save()
                        log.info("Delete completion date for user id %d / %s" % (user.id, course_key))
                        leader_board, _ = LeaderBoard.objects.get_or_create(user=user)
                        leader_board.course_completed = leader_board.course_completed - 1
                        leader_board.save()
                        log.info(
                            "updated course completed (-1) of leaderboard score "
                            "for user: {user_id}, course_id: {course_id}".format(
                                user_id=user.id,
                                course_id=course_key
                            )
                        )
            except AttributeError:
                pass
        if should_persist_grades(course_key):
            PersistentCourseProgress.update_or_create(
                user_id=user.id,
                course_id=course_key,
                percent_progress=round(percent_progress / 100, 2)
            )
        return round(percent_progress / 100, 2)

    def get_course_completion_percentage(self, user, course_key, course_grade=None, enrollment=None):
        """
        return the completed percentage of the given course
        """
        try:
            persistent_progress = PersistentCourseProgress.read(user.id, course_key)
            log.info(u'Course Progress Read: %s, User: %s', unicode(course_key), user.id)
            return persistent_progress.percent_progress
        except PersistentCourseProgress.DoesNotExist:
            # check if user ever interacts with course before
            if StudentModule.objects.filter(student=user, course_id=course_key).exists():
                return self.update_course_completion_percentage(
                    course_key, user, course_grade=course_grade, enrollment=enrollment)
            else:
                return 0

    def get_nb_trophies_possible(self, course):
        """
        return the number of badges of the given course
        course :: CourseDescriptor
        """
        nb_trophies_possible = 0
        grading_rules = course.raw_grader
        for rule in grading_rules:
            nb_trophies_possible += rule.get('min_count', 0)
        return nb_trophies_possible

    def get_progress(self, user, course, progress=None, grade_summary=None, enrollment=None):
        course_key = course.id
        if not grade_summary:
            grade_summary = self.read(user, course)
        if not grade_summary:
            return

        nb_trophies_attempted = 0
        nb_trophies_earned = 0
        nb_trophies_possible = 0
        current_total_weight = 0
        trophies_by_chapter = []

        grading_rules = course.raw_grader
        grading_rules_dict = {}
        for rule in grading_rules:
            nb_trophies_possible += rule.get('min_count', 0)
            rule['available_count'] = rule.get('min_count') - rule.get('drop_count')
            if not rule.get('threshold'):
                rule['threshold'] = 1
            grading_rules_dict.update({
                rule.get('type'): rule
            })

        chapter_grades = grade_summary.chapter_grades.values()
        for chapter in chapter_grades:
            trophies = []
            for section in chapter['sections']:
                if section.graded and grading_rules_dict:
                    grader = grading_rules_dict[section.format]
                    trophy = {
                        'result': section.percent_graded,
                        'attempted': section.attempted_graded or section.override is not None,
                        'section_format': section.format,
                        'section_name': section.display_name,
                        'section_url': section.url_name,
                        'threshold': grader['threshold'],
                        'trophy_img': grader['short_label']
                    }
                    trophy['passed'] = trophy['result'] >= trophy['threshold']
                    trophies.append(trophy)
                    if trophy['attempted']:
                        nb_trophies_attempted += 1
                        if grader['available_count'] > 0:
                            current_total_weight += grader['weight'] / (grader['min_count'] - grader['drop_count'])
                            grader['available_count'] += -1
                        if trophy['passed']:
                            nb_trophies_earned += 1
            if len(trophies) > 0:
                trophies_by_chapter.append({
                    'url': chapter['url_name'],
                    'chapter_name': chapter['display_name'],
                    'trophies': trophies
                })
        current_total_weight = round(current_total_weight, 2)
        if current_total_weight > 0:
            current_score = round(grade_summary.percent * 100 / current_total_weight)
            # sometime the round function doesn't work as expected
            if current_score > 100:
                current_score = 100
        else:
            current_score = 0

        if not progress:
            progress = self.get_course_completion_percentage(
                user, course_key, course_grade=grade_summary, enrollment=enrollment)

        return {
            'current_score': current_score,
            'is_course_passed': grade_summary.passed,
            'nb_trophies_attempted': nb_trophies_attempted,
            'nb_trophies_earned': nb_trophies_earned,
            'nb_trophies_possible': nb_trophies_possible,
            'trophies_by_chapter': trophies_by_chapter,
            'progress': progress
        }
