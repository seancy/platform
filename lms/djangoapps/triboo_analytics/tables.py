# -*- coding: utf-8 -*-
from six import text_type
from django.utils import timezone
from django.utils.safestring import mark_safe
from django_countries import countries
import django_tables2 as tables
from django_tables2.utils import A
from openedx.core.djangoapps.content.course_overviews.models import CourseOverview

from .models import (
    CourseStatus,
    format_time_spent,
    get_badges,
    LearnerCourseDailyReport,
    LearnerDailyReport,
    IltSession,
    IltLearnerReport
)


EXPORT_FORMATS = ['csv', 'xls', 'json']


def dt2str(dt):
    if isinstance(dt, timezone.datetime):
        return dt.strftime('%d/%m/%Y')
    return ""

def get_sum(bound_column, data):
    if bound_column:
        col_sum = 0
        for row in data:
            try:
                col_sum += bound_column.accessor.resolve(row)
            except ValueError:
                pass
        return col_sum
    return sum(data)


def get_avg(bound_column, data):
    if len(data) > 0:
        return get_sum(bound_column, data) / len(data)
    return 0


class SumFooterColumn(tables.Column):
    def render_footer(self, bound_column, table):
        return get_sum(bound_column, table.data)

class TimeSpentFooterColumn(tables.Column):
    def render_footer(self, bound_column, table):
        return format_time_spent(get_sum(bound_column, table.data))

class AvgFooterColumn(tables.Column):
    def render_footer(self, bound_column, table):
        return get_avg(bound_column, table.data)


class _RenderMixin(object):
    ## render_foo methods are used for html rendering
    ## value_foo methods are used for export

    def render_status(self, value):
        return CourseStatus.verbose_names[value]

    def value_enrollment_date(self, value):
        return dt2str(value)

    def render_enrollment_date(self, value):
        value = self.value_enrollment_date(value)
        return value if value != '' else '-'

    def value_completion_date(self, value):
        return dt2str(value)

    def render_completion_date(self, value):
        value = self.value_completion_date(value)
        return value if value != '' else '-'

    def value_progress(self, value):
        return "{}%".format(value)

    def render_progress(self, value):
        value = self.value_progress(value)
        return value if value != '' else '-'

    def value_current_score(self, record, value):
        if record.status == CourseStatus.not_started:
            return ''
        return "{}%".format(value)

    def render_current_score(self, record, value):
        value = self.value_current_score(record, value)
        return value if value != '' else '-'

    def value_total_time_spent(self, record, value):
        if record.status == CourseStatus.not_started:
            return ''
        return format_time_spent(value)

    def render_total_time_spent(self, record, value):
        value = self.value_total_time_spent(record, value)
        return value if value != '' else '-'

    def value_badges(self, record, value):
        x, y = get_badges(value)
        return "{} (/ {})".format(x, y)

    def render_badges(self, record, value):
        return '-' if record.status == CourseStatus.not_started else value

    def render_posts(self, record, value):
        return '-' if record.status == CourseStatus.not_started else value


class TranscriptTable(_RenderMixin, tables.Table):
    export_formats = EXPORT_FORMATS
    course_title = tables.LinkColumn('info', args=[A('course_id')],
                                     verbose_name='Course Title', empty_values=('', ))

    class Meta:
        model = LearnerCourseDailyReport
        template = 'django_tables2/bootstrap.html'
        fields = ('course_title',
                  'status',
                  'progress',
                  'badges',
                  'current_score',
                  'total_time_spent',
                  'enrollment_date',
                  'completion_date')
        unlocalize = ('course_title', 'progress', 'badges', 'current_score', 'total_time_spent',
                      'enrollment_date', 'completion_date')

    def __init__(self, data=None, order_by=None, orderable=None, empty_text=None, exclude=None, attrs=None,
                 row_attrs=None, pinned_row_attrs=None, sequence=None, prefix=None, order_by_field=None,
                 page_field=None, per_page_field=None, template=None, default=None, request=None, show_header=None,
                 show_footer=True, extra_columns=None):
        super(TranscriptTable, self).__init__(data, order_by, orderable, empty_text, exclude, attrs, row_attrs,
                                              pinned_row_attrs, sequence, prefix, order_by_field, page_field,
                                              per_page_field, template, default, request, show_header, show_footer,
                                              extra_columns)

        self.titles = {ov.id: ov.display_name for ov in CourseOverview.objects.all()}


    def before_render(self, request):
        self.path = request.path


    def render_course_title(self, record, value, bound_column):
        column = bound_column.column
        return column.render_link(
            column.compose_url(record, bound_column),
            record=record,
            value=self.titles[record.course_id]
        )


    def value_course_title(self, record):
        return self.titles[record.course_id]


    def order_course_title(self, queryset, is_descending):
        queryset = queryset.order_by(('-' if is_descending else '') + 'course_id')
        return queryset, True


class UserBaseTable(tables.Table):
    export_formats = EXPORT_FORMATS

    user_name = tables.Column(accessor='user.profile.name', verbose_name='Name')

    user_email = tables.Column(accessor='user.email', verbose_name='Email')
    user_username = tables.Column(accessor='user.username', verbose_name='Username')
    user_date_joined = tables.Column(accessor='user.date_joined', verbose_name='Date Joined')

    user_country = tables.Column(accessor='user.profile.country', verbose_name='Country')
    user_lt_area = tables.Column(accessor='user.profile.lt_area', verbose_name='Commercial Zone')
    user_lt_sub_area = tables.Column(accessor='user.profile.lt_sub_area', verbose_name='Commercial Region')
    user_city = tables.Column(accessor='user.profile.city', verbose_name='City')
    user_location = tables.Column(accessor='user.profile.location', verbose_name='Location')
    user_lt_address = tables.Column(accessor='user.profile.lt_address', verbose_name='Address')
    user_lt_address_2 = tables.Column(accessor='user.profile.lt_address_2', verbose_name='Address 2')
    user_lt_phone_number = tables.Column(accessor='user.profile.lt_phone_number', verbose_name='Phone Number')
    user_lt_gdpr = tables.Column(accessor='user.profile.lt_gdpr', verbose_name='GDPR')
    user_lt_company = tables.Column(accessor='user.profile.lt_company', verbose_name='Company')
    user_lt_employee_id = tables.Column(accessor='user.profile.lt_employee_id', verbose_name='Employee ID')
    user_lt_hire_date = tables.Column(accessor='user.profile.lt_hire_date', verbose_name='Hire Date')
    user_lt_level = tables.Column(accessor='user.profile.lt_level', verbose_name='Level')
    user_lt_job_code = tables.Column(accessor='user.profile.lt_job_code', verbose_name='Job Code')
    user_lt_job_description = tables.Column(accessor='user.profile.lt_job_description', verbose_name='Job Description')
    user_lt_department = tables.Column(accessor='user.profile.lt_department', verbose_name='Department')
    user_lt_supervisor = tables.Column(accessor='user.profile.lt_supervisor', verbose_name='Supervisor')
    user_lt_ilt_supervisor = tables.Column(accessor='user.profile.lt_ilt_supervisor', verbose_name='ILT Supervisor')
    user_lt_learning_group = tables.Column(accessor='user.profile.lt_learning_group', verbose_name='Learning Group')
    user_lt_exempt_status = tables.Column(accessor='user.profile.lt_exempt_status', verbose_name='Exempt Status')
    user_lt_comments = tables.Column(accessor='user.profile.lt_comments', verbose_name='Comments')

    def order_user_name(self, queryset, is_descending):
        queryset = queryset.order_by(('-' if is_descending else '') + 'user__profile__name')
        return queryset, True

    def order_user_email(self, queryset, is_descending):
        queryset = queryset.order_by(('-' if is_descending else '') + 'user__email')
        return queryset, True

    def order_user_username(self, queryset, is_descending):
        queryset = queryset.order_by(('-' if is_descending else '') + 'user__username')
        return queryset, True

    def order_user_date_joined(self, queryset, is_descending):
        queryset = queryset.order_by(('-' if is_descending else '') + 'user__date_joined')
        return queryset, True

    # def render_user_country(self, value):
    #     return dict(countries)[value]

    def order_user_country(self, queryset, is_descending):
        queryset = queryset.order_by(('-' if is_descending else '') + 'user__profile__country')
        return queryset, True

    def order_user_lt_area(self, queryset, is_descending):
        queryset = queryset.order_by(('-' if is_descending else '') + 'user__profile__lt_area')
        return queryset, True

    def order_user_lt_sub_area(self, queryset, is_descending):
        queryset = queryset.order_by(('-' if is_descending else '') + 'user__profile__lt_sub_area')
        return queryset, True

    def order_user_city(self, queryset, is_descending):
        queryset = queryset.order_by(('-' if is_descending else '') + 'user__profile__city')
        return queryset, True

    def order_user_location(self, queryset, is_descending):
        queryset = queryset.order_by(('-' if is_descending else '') + 'user__profile__location')
        return queryset, True

    def order_user_lt_address(self, queryset, is_descending):
        queryset = queryset.order_by(('-' if is_descending else '') + 'user__profile__lt_address')
        return queryset, True

    def order_user_lt_address_2(self, queryset, is_descending):
        queryset = queryset.order_by(('-' if is_descending else '') + 'user__profile__lt_address_2')
        return queryset, True

    def order_user_lt_phone_number(self, queryset, is_descending):
        queryset = queryset.order_by(('-' if is_descending else '') + 'user__profile__lt_phone_number')
        return queryset, True

    def order_user_lt_gdpr(self, queryset, is_descending):
        queryset = queryset.order_by(('-' if is_descending else '') + 'user__profile__lt_gdpr')
        return queryset, True

    def order_user_lt_company(self, queryset, is_descending):
        queryset = queryset.order_by(('-' if is_descending else '') + 'user__profile__lt_company')
        return queryset, True

    def order_user_lt_employee_id(self, queryset, is_descending):
        queryset = queryset.order_by(('-' if is_descending else '') + 'user__profile__lt_employee_id')
        return queryset, True

    def order_user_lt_hire_date(self, queryset, is_descending):
        queryset = queryset.order_by(('-' if is_descending else '') + 'user__profile__lt_hire_date')
        return queryset, True

    def order_user_lt_level(self, queryset, is_descending):
        queryset = queryset.order_by(('-' if is_descending else '') + 'user__profile__lt_level')
        return queryset, True

    def order_user_lt_job_code(self, queryset, is_descending):
        queryset = queryset.order_by(('-' if is_descending else '') + 'user__profile__lt_job_code')
        return queryset, True

    def order_user_lt_job_description(self, queryset, is_descending):
        queryset = queryset.order_by(('-' if is_descending else '') + 'user__profile__lt_job_description')
        return queryset, True

    def order_user_lt_department(self, queryset, is_descending):
        queryset = queryset.order_by(('-' if is_descending else '') + 'user__profile__lt_department')
        return queryset, True

    def order_user_lt_supervisor(self, queryset, is_descending):
        queryset = queryset.order_by(('-' if is_descending else '') + 'user__profile__lt_supervisor')
        return queryset, True

    def order_user_lt_ilt_supervisor(self, queryset, is_descending):
        queryset = queryset.order_by(('-' if is_descending else '') + 'user__profile__lt_ilt_supervisor')
        return queryset, True

    def order_user_lt_learning_group(self, queryset, is_descending):
        queryset = queryset.order_by(('-' if is_descending else '') + 'user__profile__lt_learning_group')
        return queryset, True

    def order_user_lt_exempt_status(self, queryset, is_descending):
        queryset = queryset.order_by(('-' if is_descending else '') + 'user__profile__lt_exempt_status')
        return queryset, True

    def order_user_lt_comments(self, queryset, is_descending):
        queryset = queryset.order_by(('-' if is_descending else '') + 'user__profile__lt_comments')
        return queryset, True


class ProgressColumn(tables.Column):
    def render(self, value):
        if value['result'] >= value['threshold']:
            return mark_safe("<span class='trophy-yes fa fa-check'></span> %d%%" % value['result'])
        return mark_safe("<span class='trophy-no fa fa-times'></span> %d%%" % value['result'])


    def value(self, value):
        if value['result'] >= value['threshold']:
            return "Yes: %d" % value['result']
        return "No: %d" % value['result']


    def render_footer(self, bound_column, table):
        col_avg = 0
        nb_rows = len(table.data)
        if nb_rows > 0:
            try:
                col_sum = sum(bound_column.accessor.resolve(row)['result'] for row in table.data)
                col_avg = col_sum / nb_rows
            except ValueError:
                pass
        return "%d%%" % col_avg


def get_progress_table_class(trophies):
    attributes = {}
    for trophy_name, trophy_verbose in trophies:
        attributes[trophy_name] = ProgressColumn(verbose_name=trophy_verbose)

    return type("ProgressTable", (UserBaseTable,), attributes)


class HeaderColumn(tables.Column):
    def __init__(self, verbose_name=None, accessor=None, default=None,
                 visible=True, orderable=None, attrs=None, order_by=None,
                 empty_values=None, localize=None, footer=None, exclude_from_export=True, colspan=1):
        super(HeaderColumn, self).__init__(verbose_name, accessor, default,
            visible, orderable, attrs, order_by, empty_values, localize, footer,
            exclude_from_export)
        self.colspan = colspan


class CourseSectionColumn(TimeSpentFooterColumn):
    def __init__(self, verbose_name=None, accessor=None, default=None,
                 visible=True, orderable=None, attrs=None, order_by=None,
                 empty_values=None, localize=None, footer=None,
                 exclude_from_export=False, chapter=None):
        super(CourseSectionColumn, self).__init__(verbose_name, accessor, default,
            visible, orderable, attrs, order_by, empty_values, localize, footer,
            exclude_from_export)
        self.chapter = chapter

    def render(self, value):
        return format_time_spent(value)


    def short_header(self):
        chapter_prefix = "%s / " % self.chapter
        if self.verbose_name.startswith(chapter_prefix):
            return self.verbose_name[len(chapter_prefix):]
        return self.verbose_name


def get_time_spent_table_class(chapters, sections):
    attributes = {}
    for chapter in chapters:
        attributes[chapter['key']] = HeaderColumn(verbose_name=chapter['name'],
                                                  colspan=chapter['colspan'])
    for section in sections:
        attributes[section['key']] = CourseSectionColumn(verbose_name=section['name'],
                                                         chapter=section['chapter'])

    return type("TimeSpentTable", (UserBaseTable,), attributes)


class LearnerBaseTable(UserBaseTable):
    badges = tables.Column(footer=lambda table: get_sum(
                None, [get_badges(row.badges)[0] for row in table.data]))
    total_time_spent = TimeSpentFooterColumn()


class CourseTable(_RenderMixin, LearnerBaseTable):
    current_score = tables.Column(footer=lambda table: "{}%".format(
                         get_avg(None, [r.current_score for r in table.data if r.status != CourseStatus.not_started])))
    progress = tables.Column(footer=lambda table: "{}%".format(
                         get_avg(None, [r.progress for r in table.data])))
    posts = SumFooterColumn()

    class Meta:
        model = LearnerCourseDailyReport
        template = 'django_tables2/bootstrap.html'
        fields = ('user_name',
                  'user_email',
                  'user_username',
                  'user_date_joined',
                  'user_country',
                  'user_lt_area',
                  'user_lt_sub_area',
                  'user_city',
                  'user_location',
                  'user_lt_address',
                  'user_lt_address_2',
                  'user_lt_phone_number',
                  'user_lt_gdpr',
                  'user_lt_company',
                  'user_lt_employee_id',
                  'user_lt_hire_date',
                  'user_lt_level',
                  'user_lt_job_code',
                  'user_lt_job_description',
                  'user_lt_department',
                  'user_lt_supervisor',
                  'user_lt_ilt_supervisor',
                  'user_lt_learning_group',
                  'user_lt_exempt_status',
                  'user_lt_comments',
                  'status',
                  'progress',
                  'current_score',
                  'badges',
                  'posts',
                  'total_time_spent',
                  'enrollment_date',
                  'completion_date')
        unlocalize = ('user_name', 'user_email', 'user_username', 'user_date_joined', 'user_country',
                    'user_lt_area', 'user_lt_sub_area', 'user_city', 'user_location', 'user_lt_address', 'user_lt_address_2',
                    'user_lt_phone_number', 'user_lt_gdpr', 'user_lt_company', 'user_lt_employee_id', 'user_lt_hire_date',
                    'user_lt_level', 'user_lt_job_code', 'user_lt_job_description', 'user_lt_department', 'user_lt_supervisor',
                    'user_lt_ilt_supervisor', 'user_lt_learning_group', 'user_lt_exempt_status', 'user_lt_comments',
                    'progress', 'current_score', 'badges', 'posts', 'total_time_spent', 'enrollment_date', 'completion_date')


class LearnerDailyTable(LearnerBaseTable):
    user_name = tables.LinkColumn('analytics_learner_transcript', args=[A('user.id')],
                                  verbose_name='Name', text=lambda record: record.user.profile.name)
    enrollments = SumFooterColumn()
    finished = SumFooterColumn()
    failed = SumFooterColumn()
    in_progress = SumFooterColumn()
    not_started = SumFooterColumn()
    posts = SumFooterColumn()
    average_final_score = tables.Column(footer=lambda table: "{}%".format(
                                    get_avg(None, [r.average_final_score for r in table.data])))
    user_last_login = tables.Column(accessor='user.last_login', verbose_name='Last Login')

    class Meta:
        model = LearnerDailyReport
        template = 'django_tables2/bootstrap.html'
        fields = ('user_name',
                  'user_email',
                  'user_username',
                  'user_date_joined',
                  'user_country',
                  'user_lt_area',
                  'user_lt_sub_area',
                  'user_city',
                  'user_location',
                  'user_lt_address',
                  'user_lt_address_2',
                  'user_lt_phone_number',
                  'user_lt_gdpr',
                  'user_lt_company',
                  'user_lt_employee_id',
                  'user_lt_hire_date',
                  'user_lt_level',
                  'user_lt_job_code',
                  'user_lt_job_description',
                  'user_lt_department',
                  'user_lt_supervisor',
                  'user_lt_ilt_supervisor',
                  'user_lt_learning_group',
                  'user_lt_exempt_status',
                  'user_lt_comments',
                  'enrollments',
                  'finished',
                  'failed',
                  'in_progress',
                  'not_started',
                  'average_final_score',
                  'badges',
                  'posts',
                  'total_time_spent',
                  'user_last_login')
        unlocalize = ('user_name', 'user_email', 'user_username', 'user_date_joined', 'user_country',
                    'user_lt_area', 'user_lt_sub_area', 'user_city', 'user_location', 'user_lt_address', 'user_lt_address_2',
                    'user_lt_phone_number', 'user_lt_gdpr', 'user_lt_company', 'user_lt_employee_id', 'user_lt_hire_date',
                    'user_lt_level', 'user_lt_job_code', 'user_lt_job_description', 'user_lt_department', 'user_lt_supervisor',
                    'user_lt_ilt_supervisor', 'user_lt_learning_group', 'user_lt_exempt_status', 'user_lt_comments',
                    'enrollments', 'finished', 'failed', 'in_progress', 'not_started', 'average_final_score',
                    'badges', 'posts', 'total_time_spent', 'user_last_login')

    def render_total_time_spent(self, value):
        return format_time_spent(value)

    def render_average_final_score(self, value):
        return "{}%".format(value)

    def value_user_last_login(self, value):
        return dt2str(value)

    def render_user_last_login(self, value):
        value = self.value_user_last_login(value)
        return value if value != '' else '-'

    def order_user_last_login(self, queryset, is_descending):
        queryset = queryset.order_by(('-' if is_descending else '') + 'user__last_login')
        return queryset, True


class IltBaseTable(tables.Table):
    export_formats = EXPORT_FORMATS
    
    course_area =  tables.Column(accessor='ilt_module.course_country', verbose_name='Geographical area')
    course_country = tables.Column(accessor='ilt_module.course_country', verbose_name='Course country')
    course_tags = tables.Column(accessor='ilt_module.course_tags', verbose_name='Course tags')
    course_code = tables.Column(accessor='ilt_module.course_id', verbose_name='Course code')
    course_display_name = tables.Column(accessor='ilt_module.course_display_name', verbose_name='Course')
    chapter_display_name = tables.Column(accessor='ilt_module.chapter_display_name', verbose_name='Chapter')
    section_display_name = tables.Column(accessor='ilt_module.section_display_name', verbose_name='Section')

    def render_course_area(self, value):
        if value:
            if value == "All countries":
                return "All"
            elif value == "France":
                return "FR"
            elif value == "Romania":
                return "BK"
        return "-"

    def order_session_id(self, queryset, is_descending):
        queryset = queryset.order_by(('-' if is_descending else '') + 'ilt_module__course_country')
        return queryset, True

    def render_course_code(self, record, value):
        prefix = "course-v1:%s+" % record.org
        return text_type(value)[len(prefix):]

    def render_start_day(self, value):
        return value.strftime('%d/%m/%Y')

    def render_start_time(self, value):
        return value.strftime("%H:%M:%S")

    def render_end_day(self, value):
        return value.strftime('%d/%m/%Y')

    def render_end_time(self, value):
        return value.strftime("%H:%M:%S")

    def render_ack_attendance_sheet(self, value):
        return "Received" if value else "Expected"


class IltTable(IltBaseTable):
    area = tables.Column(verbose_name='Zone/Region')
    session_id = tables.Column(verbose_name='Session ID')
    start_day = tables.Column(accessor='start', verbose_name='Start date')
    start_time = tables.Column(accessor='start', verbose_name='Start time')
    end_day = tables.Column(accessor='end', verbose_name='End date')
    end_time = tables.Column(accessor='end', verbose_name='End time')
    duration = tables.Column(verbose_name='Duration (in hours)')
    seats = tables.Column(verbose_name='Max capacity')
    enrollees = tables.Column(verbose_name='Enrollees')
    attendees = tables.Column(verbose_name='Attendees')
    ack_attendance_sheet = tables.Column(verbose_name='Attendance sheet')
    location_id = tables.Column(verbose_name='Location ID')
    location = tables.Column(verbose_name='Location name')
    address = tables.Column(verbose_name='Address')
    zip_code = tables.Column(verbose_name='Zip code')
    city = tables.Column(verbose_name='City')

    class Meta:
        model = IltSession
        template = 'django_tables2/bootstrap.html'
        fields = ('course_area',
                  'course_country',
                  'area',
                  'course_tags',
                  'course_code',
                  'course_display_name',
                  'chapter_display_name',
                  'section_display_name',
                  'session_id',
                  'start_day',
                  'start_time',
                  'end_day',
                  'end_time',
                  'duration',
                  'seats',
                  'enrollees',
                  'attendees',
                  'ack_attendance_sheet',
                  'location_id',
                  'location',
                  'address',
                  'zip_code',
                  'city')
        unlocalize = ('area', 'course_tags', 'course_code', 'course_display_name',
                      'chapter_display_name', 'section_display_name', 'session_id',
                      'start_day', 'start_time', 'end_day', 'end_time', 'duration', 'seats',
                      'enrollees', 'attendees', 'location_id', 'location', 'address', 'zip_code', 'city')

    def order_session_id(self, queryset, is_descending):
        order = '-' if is_descending else ''
        queryset = queryset.order_by(order + 'ilt_module__id', order + 'session_nb')
        return queryset, True


class IltLearnerTable(IltBaseTable, UserBaseTable):
    area = tables.Column(accessor='ilt_session.area', verbose_name='Zone/Region')
    session_id = tables.Column(accessor='ilt_session.session_id', verbose_name='Session ID')
    start_day = tables.Column(accessor='ilt_session.start', verbose_name='Start date')
    start_time = tables.Column(accessor='ilt_session.start', verbose_name='Start time')
    end_day = tables.Column(accessor='ilt_session.end', verbose_name='End date')
    end_time = tables.Column(accessor='ilt_session.end', verbose_name='End time')
    duration = tables.Column(accessor='ilt_session.duration', verbose_name='Duration (in hours)')
    seats = tables.Column(accessor='ilt_session.seats', verbose_name='Max capacity')
    enrollees = tables.Column(accessor='ilt_session.enrollees', verbose_name='Enrollees')
    attendees = tables.Column(accessor='ilt_session.attendees', verbose_name='Attendees')
    ack_attendance_sheet = tables.Column(accessor='ilt_session.ack_attendance_sheet', verbose_name='Attendance sheet')
    location_id = tables.Column(accessor='ilt_session.location_id', verbose_name='Location ID')
    location = tables.Column(accessor='ilt_session.location', verbose_name='Location name')
    address = tables.Column(accessor='ilt_session.address', verbose_name='Address')
    zip_code = tables.Column(accessor='ilt_session.zip_code', verbose_name='Zip code')
    city = tables.Column(accessor='ilt_session.city', verbose_name='City')
    status = tables.Column(verbose_name='Enrollment status')
    attendee = tables.Column(verbose_name='Attendee')
    outward_trips = tables.Column(verbose_name='Outward trips')
    return_trips = tables.Column(verbose_name='Return trips')
    accommodation = tables.Column(verbose_name='Overnight stay')
    hotel = tables.Column(verbose_name='Overnight stay address')
    comment = tables.Column(verbose_name='Comment')

    class Meta:
        model = IltLearnerReport
        template = 'django_tables2/bootstrap.html'
        fields = ('course_area',
                  'course_country',
                  'area',
                  'course_tags',
                  'course_code',
                  'course_display_name',
                  'chapter_display_name',
                  'section_display_name',
                  'session_id',
                  'start_day',
                  'start_time',
                  'end_day',
                  'end_time',
                  'duration',
                  'seats',
                  'enrollees',
                  'attendees',
                  'ack_attendance_sheet',
                  'location_id',
                  'location',
                  'address',
                  'zip_code',
                  'city',
                  'user_name',
                  'user_email',
                  'user_username',
                  'user_date_joined',
                  'user_country',
                  'user_lt_area',
                  'user_lt_sub_area',
                  'user_city',
                  'user_location',
                  'user_lt_address',
                  'user_lt_address_2',
                  'user_lt_phone_number',
                  'user_lt_gdpr',
                  'user_lt_company',
                  'user_lt_employee_id',
                  'user_lt_hire_date',
                  'user_lt_level',
                  'user_lt_job_code',
                  'user_lt_job_description',
                  'user_lt_department',
                  'user_lt_supervisor',
                  'user_lt_ilt_supervisor',
                  'user_lt_learning_group',
                  'user_lt_exempt_status',
                  'user_lt_comments',
                  'status',
                  'attendee',
                  'outward_trips',
                  'return_trips',
                  'accommodation',
                  'hotel',
                  'comment')
        unlocalize = ('area', 'course_tags', 'course_code', 'course_display_name',
                      'chapter_display_name', 'section_display_name', 'session_id',
                      'start_day', 'start_time', 'end_day', 'end_time', 'duration', 'seats',
                      'enrollees', 'attendees', 'location_id', 'location', 'address', 'zip_code', 'city',
                      'user_name', 'user_email', 'user_username', 'user_date_joined', 'user_country',
                      'user_lt_area', 'user_lt_sub_area', 'user_city', 'user_location', 'user_lt_address', 'user_lt_address_2',
                      'user_lt_phone_number', 'user_lt_gdpr', 'user_lt_company', 'user_lt_employee_id', 'user_lt_hire_date',
                      'user_lt_level', 'user_lt_job_code', 'user_lt_job_description', 'user_lt_department', 'user_lt_supervisor',
                      'user_lt_ilt_supervisor', 'user_lt_learning_group', 'user_lt_exempt_status', 'user_lt_comments',
                      'attendee', 'outward_trips', 'return_trips', 'accommodation', 'hotel', 'comment')

    def order_session_id(self, queryset, is_descending):
        order = '-' if is_descending else ''
        queryset = queryset.order_by(order + 'ilt_module__id', order + 'ilt_session__session_nb')
        return queryset, True


