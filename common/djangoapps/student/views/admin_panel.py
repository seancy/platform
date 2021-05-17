# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.conf import settings
from django.contrib.auth.models import User
from django.contrib.admin.views.decorators import staff_member_required
from django.core.exceptions import PermissionDenied
from django.db.models import IntegerField, Case, Value, When, Q
from django.utils.decorators import method_decorator
from django.utils.translation import ugettext as _
from django.views.generic import ListView
from edxmako.shortcuts import render_to_response
from openedx.core.djangoapps.site_configuration import helpers as configuration_helpers
from student.roles import STUDIO_ADMIN_ACCESS_GROUP


class AdminPanel(ListView):
    model = User
    paginate_by = 100
    template_name = "admin_panel/admin_panel.html"
    template_engine = "mako"
    context_object_name = "user_list"
    order_types = {
        'u': 'username', '-u': '-username', 'e': 'email', '-e': '-email',
        'f': 'first_name', '-f': '-first_name', 'l': 'last_name', '-l': '-last_name',
        's': 'is_active', '-s': '-is_active', 'a': 'level', '-a': '-level'
    }
    current_order = 'u'

    def get(self, request, *args, **kwargs):
        response = super(AdminPanel, self).get(request, *args, **kwargs)
        response["Cache-Control"] = "no-cache, no-store, must-revalidate"  # HTTP 1.1.
        response["Pragma"] = "no-cache"  # HTTP 1.0.
        response["Expires"] = "0"  # Proxies.
        return response

    def get_context_data(self, **kwargs):
        context = super(AdminPanel, self).get_context_data(**kwargs)
        context['route'] = "user_list"
        context['search_string'] = self.request.GET.get('name', '')
        context['current_order'] = self.current_order
        return context

    def get_queryset(self):
        object_list = self.model.objects.all().prefetch_related("groups")
        name = self.request.GET.get('name', '')
        if name:
            object_list = object_list.filter(
                Q(username__icontains=name) |
                Q(email__icontains=name) |
                Q(first_name__icontains=name) |
                Q(last_name__icontains=name)
            )
        order = self.request.GET.get('order', 'u')
        if order not in self.order_types:
            order = 'u'
        self.current_order = order
        if order in ['a', '-a']:
            platform_admins = object_list.filter(Q(is_staff=True) | Q(is_superuser=True)).annotate(level=Case(
                When(is_superuser=True, then=Value(3)),
                default=Value(2),
                output_field=IntegerField()
            ))
            studio_admins = object_list.exclude(Q(is_staff=True) | Q(is_superuser=True)).filter(
                groups__name=STUDIO_ADMIN_ACCESS_GROUP
            ).annotate(level=Value(1, output_field=IntegerField()))
            learners = object_list.exclude(
                Q(is_staff=True) | Q(is_superuser=True) | Q(groups__name=STUDIO_ADMIN_ACCESS_GROUP)
            ).annotate(level=Value(0, output_field=IntegerField()))

            object_list = learners.union(studio_admins, platform_admins)
        ordering = self.order_types.get(order, 'username')
        if ordering != 'username':
            ordering = [ordering, 'username']
        else:
            ordering = ['username']
        object_list = object_list.order_by(*ordering)

        return object_list

    @method_decorator(staff_member_required(login_url='/login'))
    def dispatch(self, request, *args, **kwargs):
        return super(AdminPanel, self).dispatch(request, *args, **kwargs)


def get_date_format():
    date_format = _("NUMBERIC_SHORT_DATE_SLASH")
    if date_format == "NUMBERIC_SHORT_DATE_SLASH":
        date_format = "%Y/%m/%d"
    js_date_format = date_format.replace("%Y", 'yy').replace("%m", "mm").replace("%d", "dd")
    return date_format, js_date_format


@staff_member_required(login_url='/login')
def create_user(request):
    profile_fields = configuration_helpers.get_value(
        'ANALYTICS_USER_PROPERTIES',
        settings.FEATURES.get('ANALYTICS_USER_PROPERTIES', {})
    )
    platform_level_options = [{'text': _('Learner'), 'value': '0'}, {'text': _('Studio Admin'), 'value': '1'},
                              {'text': _('Platform Admin'), 'value': '2'}]
    if request.user.is_superuser:
        platform_level_options.append({'text': _('Super Platform Admin'), 'value': '3'})
    context = {"route": "user_create", "user_id": "", "profile_fields": profile_fields,
               "date_format": get_date_format()[1], "platform_level_options": platform_level_options}
    return render_to_response("admin_panel/admin_panel.html", context)


@staff_member_required(login_url='/login')
def edit_user(request, user_id):
    user = User.objects.get(id=user_id)
    if user.is_superuser and not request.user.is_superuser:
        raise PermissionDenied
    profile_fields = configuration_helpers.get_value(
        'ANALYTICS_USER_PROPERTIES',
        settings.FEATURES.get('ANALYTICS_USER_PROPERTIES', {})
    )
    platform_level_options = [{'text': _('Learner'), 'value': '0'}, {'text': _('Studio Admin'), 'value': '1'},
                              {'text': _('Platform Admin'), 'value': '2'}]
    if request.user.is_superuser:
        platform_level_options.append({'text': _('Super Platform Admin'), 'value': '3'})
    context = {"route": "user_edit", "user_id": user_id, "profile_fields": profile_fields,
               "date_format": get_date_format()[1], "platform_level_options": platform_level_options}
    return render_to_response("admin_panel/admin_panel.html", context)
