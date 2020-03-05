# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django import forms
from pytz import utc
from datetime import datetime, timedelta
from django.utils.translation import ugettext_lazy as _
from django.utils.translation import pgettext_lazy


AVAILABLE_CHOICES = {
    'name': _('Name'),
    'email': _('Email'),
    'username': _('Username'),
    'date_joined': _('Date Joined'),
    'level_of_education': _('Education'),
    'gender': _('Gender'),
    'country': _('Country'),
    'lt_area': _('Commercial Zone'),
    'lt_sub_area': _('Commercial Region'),
    'city': _('City'),
    'location': pgettext_lazy('user.profile', 'Location'),
    'lt_address': pgettext_lazy('user.profile', 'Address'),
    'lt_address_2': _('Address 2'),
    'lt_phone_number': _('Phone Number'),
    'lt_gdpr': _('GDPR'),
    'lt_company': _('Company'),
    'lt_employee_id': _('Employee ID'),
    'lt_hire_date': _('Hire Date'),
    'lt_level': _('Level'),
    'lt_job_code': _('Job Code'),
    'lt_job_description': _('Job Description'),
    'lt_department': _('Department'),
    'lt_supervisor': _('Supervisor'),
    'lt_ilt_supervisor': _('ILT Supervisor'),
    'lt_learning_group': _('Learning Group'),
    'lt_exempt_status': _('Exempt Status'),
    'lt_comments': _('Comments'),
}


class UserPropertiesHelper():
    def __init__(self, analytics_user_properties={}):
        self.possible_choices_db_prefix = []
        self.possible_choices = []
        self.initial_choices = ["user_name"]
        for prop in AVAILABLE_CHOICES.keys():
            if prop in analytics_user_properties.keys():
                prefix = "user_"
                db_prefix = "user__"
                if prop not in ['email', 'username', 'date_joined']:
                    db_prefix += "profile__"

                self.possible_choices.append(("%s%s" % (prefix, prop), AVAILABLE_CHOICES[prop]))
                self.possible_choices_db_prefix.append(("%s%s" % (db_prefix, prop), AVAILABLE_CHOICES[prop]))

                if analytics_user_properties[prop] == "default":
                    self.initial_choices.append("%s%s" % (prefix, prop))
        self.possible_choices.sort(key=lambda choice: choice[1])
        self.possible_choices_db_prefix.sort(key=lambda choice: choice[1])


    def get_possible_choices(self, db_prefix=True):
        if db_prefix:
            return self.possible_choices_db_prefix
        return self.possible_choices


    def get_initial_choices(self):
        return self.initial_choices


class TimePeriodForm(forms.Form):
    from_day = forms.CharField(required=False, initial='', label=_('From'))
    to_day = forms.CharField(required=False, initial='', label=_('To'))

    course_id = forms.CharField(widget=forms.HiddenInput(), required=False)
    report = forms.CharField(widget=forms.HiddenInput(), required=False)
    query_string = forms.CharField(widget=forms.HiddenInput(), required=False)
    queried_field = forms.CharField(widget=forms.HiddenInput(), required=False)
    selected_properties = forms.CharField(widget=forms.MultipleHiddenInput(), required=False)

    def __init__(self, data=None):
        super(TimePeriodForm, self).__init__(data)
        self.period = None
        if data:
            from_day = data.get('from_day', None)
            to_day = data.get('to_day', None)
            if from_day and to_day:
                from_date = utc.localize(datetime.strptime(from_day, '%Y-%m-%d'))
                to_date = utc.localize(datetime.strptime(to_day, '%Y-%m-%d')) + timedelta(days=1)
                self.period = (from_date, to_date)


class TableFilterForm(forms.Form):
    query_string = forms.CharField(required=False, initial='', label=_('Query'))
    queried_field = forms.ChoiceField(required=False, label=_('Field'))

    course_id = forms.CharField(widget=forms.HiddenInput(), required=False)
    report = forms.CharField(widget=forms.HiddenInput(), required=False)
    selected_properties = forms.CharField(widget=forms.MultipleHiddenInput(), required=False)
    from_day = forms.CharField(widget=forms.HiddenInput(), required=False)
    to_day = forms.CharField(widget=forms.HiddenInput(), required=False)

    def __init__(self, data=None, choices=[]):
        super(TableFilterForm, self).__init__(data)
        self.fields['queried_field'].choices = [('user__profile__name', _('Name'))] + choices


class UserPropertiesForm(forms.Form):
    selected_properties = forms.MultipleChoiceField(
        required=False,
        widget=forms.CheckboxSelectMultiple,
        label=_('Select the user properties you want to display')
    )

    course_id = forms.CharField(widget=forms.HiddenInput(), required=False)
    report = forms.CharField(widget=forms.HiddenInput(), required=False)
    page = forms.CharField(widget=forms.HiddenInput(), required=False)
    query_string = forms.CharField(widget=forms.HiddenInput(), required=False)
    queried_field = forms.CharField(widget=forms.HiddenInput(), required=False)
    from_day = forms.CharField(widget=forms.HiddenInput(), required=False)
    to_day = forms.CharField(widget=forms.HiddenInput(), required=False)

    def __init__(self, data=None, choices=[], initial={}):
        super(UserPropertiesForm, self).__init__(data, initial={'selected_properties': initial})
        self.fields['selected_properties'].choices = choices
        self.fields['selected_properties'].initial = initial


    def clean(self):
        cleaned_data = super(UserPropertiesForm, self).clean()
        all_properties = ["user_%s" % prop for prop in AVAILABLE_CHOICES.keys()]
        if len(cleaned_data['selected_properties']) > 0:
            cleaned_data['excluded_properties'] = set(all_properties) - set(cleaned_data['selected_properties'])
        else:
            cleaned_data['excluded_properties'] = set(all_properties) - set(self.initial['selected_properties'])
        return cleaned_data
