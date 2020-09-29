function intermediate_certificates_init() {

    Vue.component('select2', {
        props: ['options', 'value', 'placeholder'],
        template: '<select><slot></slot></select>',
        mounted: function () {
            var vm = this;
            $(this.$el)
            // init select2
                .select2({
                    data: this.options,
                    placeholder: this.placeholder
                })
                .val(this.value)
                .trigger('change')
                // emit event on change.
                .on('change', function () {
                    vm.$emit('input', this.value)
                    vm.$emit('change')
                })
        },
        destroyed: function () {
            $(this.$el).off().select2('destroy')
        }
    });

    var h = window.location.href
    var pre_url = h.substring(0, h.lastIndexOf('/'))
    console.log('pre_url', pre_url)
    const data_url = pre_url + "/intermediate_certificates_data"
    const certificate_count_url = pre_url + '/intermediate_certificates_count'

    var IntermediateCertificate = new Vue({
        el: '#intermediate_certificate_container',
        data: {
            selected_user: '',
            selected_cohort: '',
            title_list: [],
            cohort_list: [],
            user_list: [],
            cohort_users: {},
            all_users: [],
            switchShow: false,
        },
        computed: {
            current_cohorts: function () {
                return this.cohort_list
            },
            current_users: function () {
                return this.user_list
            },
        },
        methods: {
            changeUsers: function () {
                var cohort_option = $('select#id_select_cohort.select2-hidden-accessible')
                var cohort_value = cohort_option.val()
                var user_option = $('select#id_select_user.select2-hidden-accessible')
                console.log('cohort_value: ', cohort_value)
                console.log('cohort_users: ', this.cohort_users)
                console.log('all_users: ', this.all_users)
                var current_user_list = this.all_users.slice(0)
                if (cohort_value != -1) {
                    current_user_list = this.cohort_users[cohort_value][0]
                }
                if (current_user_list[current_user_list.length - 1].id != -1) {
                    current_user_list.push({'id': -1, 'text': 'All'})
                }
                console.log('current_user_list: ', current_user_list)
                user_option.empty()
                    .select2({
                        data: current_user_list,
                        placeholder: user_option[0].dataset.ph
                    }).val(0).change()
                checkAndEnableSubmitBtn()
            },
            checkSubmit: function () {
                checkAndEnableSubmitBtn()
            },
        },
    });

    function checkAndEnableSubmitBtn() {
        var self = IntermediateCertificate;
        var title_option = $('select#id_select_title.select2-hidden-accessible')
        var cohort_option = $('select#id_select_cohort.select2-hidden-accessible')
        var user_option = $('select#id_select_user.select2-hidden-accessible')
        var submit_button = $('#generate-intermediate-certificates-submit')
        var data = {};
        data.certificate_title = title_option.val();
        data.cohort_id = cohort_option.val();
        data.user_id = user_option.val();
        data.date_start = $('#ic_date_start').val();
        data.date_end = $('#ic_date_end').val();
        if (data.certificate_title && data.cohort_id && data.user_id) {
            self.switchShow = true;
            submit_button[0].disabled = true;
            Vue.http.post(certificate_count_url, data).then(function (resp) {
                // console.log('resp', resp)
                resp.json().then(function (data) {
                    // console.log('summaryCount', data)
                    self.switchShow = false;
                    var cert_count = data;
                    if (cert_count > 1000) {
                        alert(gettext('The number of certificates to export exceeds 1,000. Please narrow your search.'));
                        submit_button[0].disabled = true;
                    } else {
                        submit_button[0].disabled = false;
                    }
                });
            });
        } else {
            submit_button[0].disabled = true;
        }
    }

    function initOptions() {
        var title_option = $('select#id_select_title.select2-hidden-accessible')
        var cohort_option = $('select#id_select_cohort.select2-hidden-accessible')
        var user_option = $('select#id_select_user.select2-hidden-accessible')
        title_option.empty()
            .select2({
                data: IntermediateCertificate.title_list,
                placeholder: title_option[0].dataset.ph
            }).val(0).change()
        cohort_option.empty()
            .select2({
                data: IntermediateCertificate.cohort_list,
                placeholder: cohort_option[0].dataset.ph
            }).val(0).change()
        user_option.empty()
            .select2({
                data: IntermediateCertificate.user_list,
                placeholder: user_option[0].dataset.ph
            }).val(0).change()
        console.log('reset: ', user_option)
    }

    function fetchData(resp) {
        resp.json().then(function (data) {
            var all_option = {'id': -1, 'text': 'All'}
            IntermediateCertificate.title_list = data.certificate_titles;
            IntermediateCertificate.cohort_list = data.cohorts;
            IntermediateCertificate.cohort_list.push(all_option);
            IntermediateCertificate.all_users = data.users.slice(0);
            IntermediateCertificate.user_list = data.users;
            IntermediateCertificate.user_list.push(all_option);
            IntermediateCertificate.cohort_users = data.cohort_users;
            initOptions()
        })
    }

    function getICData() {
        Vue.http.get(data_url).then(function (resp) {
            fetchData(resp)
        })
    }

    // initialize
    getICData()
    console.log('intermediate_certificates_init')
}