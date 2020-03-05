function iltValidation() {

    const data_url = "/ilt-validation-request-data/";

    const ILTValidationList = new Vue({
        el: "#ilt-validation-page",
        data: {
            pending_all: [],
            approved_all: [],
            declined_all: [],
            to_validate: {},
            to_unsubscribe: {},
            session_info: {},
            accommodation: false,
            date_format: "YYYY-MM-DD HH:mm",
            cached_request: {}
        },
        computed: {
            current_pending_sessions: function () {
                var result = [];
                for (var i in this.pending_all) {
                    var r_info = this.pending_all[i],
                        usage_key = r_info.usage_key,
                        course_key = r_info.course_key,
                        sess_key = r_info.session_id;
                    result.push(this.session_info[course_key][usage_key][sess_key])
                }
                return result
            },

            current_approved_sessions: function () {
                var result = [];
                for (var i in this.approved_all) {
                    var r_info = this.approved_all[i],
                        usage_key = r_info.usage_key,
                        course_key = r_info.course_key,
                        sess_key = r_info.session_id;
                    result.push(this.session_info[course_key][usage_key][sess_key])
                }
                return result
            },

            current_declined_sessions: function () {
                var result = [];
                for (var i in this.declined_all) {
                    var r_info = this.declined_all[i],
                        usage_key = r_info.usage_key,
                        course_key = r_info.course_key,
                        sess_key = r_info.session_id;
                    result.push(this.session_info[course_key][usage_key][sess_key])
                }
                return result
            }
        },
        methods: {
            showSaveButton: function () {

            },

            validate: function (action, index) {
                var request = this.pending_all[index],
                    data = {};
                data.course_key = request.course_key;
                data.usage_key = request.usage_key;
                data.session_id = request.session_id;
                data.user_id = request.user_id;
                data.action = action;
                data.info = {};
                data.info.number_of_one_way = request.number_of_one_way;
                data.info.number_of_return = request.number_of_return;
                data.info.accommodation = request.accommodation;
                data.info.comment = request.comment;
                request.status = action;
                Vue.http.post(data_url, data).then(function (resp) {
                    ILTValidationList.pending_all.splice(index, 1);
                    if (action === "approved") {
                        ILTValidationList.approved_all.push(request);
                    }
                    else {
                        ILTValidationList.declined_all.push(request);
                    }
                })
            },

            unsubscribe: function (index, type) {
                var request = this[type][index],
                    url = "/courses/" + request.course_key + "/xblock/" + request.usage_key + "/handler_noauth/batch_unenroll";
                Vue.http.post(url, {
                    identifiers: request.user_name,
                    session: request.session_id
                }).then(function (resp) {
                    ILTValidationList[type].splice(index, 1);
                })
            },

            getCookie: function (name) {
                var value = '; ' + document.cookie,
                    parts = value.split('; ' + name + '=');
                if (parts.length === 2) return parts.pop().split(';').shift()
            },
            
            combineDate: function (date1, date2) {
                var d1 = moment(date1),
                    d2 = moment(date2);
                if (d1.isSame(d2, 'year') && d1.isSame(d2, 'month') && d1.isSame(d2, 'date')) {
                    return d1.format(this.date_format) + ' - ' + d2.format('HH:mm')
                } else {
                    return d1.format(this.date_format) + ' - ' + d2.format(this.date_format)
                }
            },

            edit: function (index) {
                var request = this.pending_all[index];
                this.cached_request[index] = Object.assign({}, request);
                request.is_editing = true
            },

            save: function (index) {
                var request = this.pending_all[index],
                    data = {};
                data.course_key = request.course_key;
                data.usage_key = request.usage_key;
                data.session_id = request.session_id;
                data.user_id = request.user_id;
                data.info = {};
                data.info.number_of_one_way = request.number_of_one_way;
                data.info.number_of_return = request.number_of_return;
                data.info.accommodation = request.accommodation;
                data.info.comment = request.comment;
                console.log(data);
                Vue.http.post(data_url, data).then(function (resp) {
                    request.is_editing = false;
                })
            },

            cancel: function (index) {
                console.log(this.cached_request);
                var request = this.pending_all[index];
                request.number_of_one_way = this.cached_request[index].number_of_one_way;
                request.number_of_return = this.cached_request[index].number_of_return;
                request.accommodation = this.cached_request[index].accommodation;
                request.session_id = this.cached_request[index].session_id;
                request.comment = this.cached_request[index].comment;
                request.is_editing = false
            },

            chooseTab: function (tab) {
                if (tab === 'pending') {
                    $(".pending-tab").addClass("active");
                    $(".pending-requests").show();
                    $(".approved-tab").removeClass("active");
                    $(".declined-tab").removeClass("active");
                    $(".approved-requests").hide();
                    $(".declined-requests").hide();
                }
                else if (tab === 'approved') {
                    $(".pending-tab").removeClass("active");
                    $(".pending-requests").hide();
                    $(".approved-tab").addClass("active");
                    $(".declined-tab").removeClass("active");
                    $(".approved-requests").show();
                    $(".declined-requests").hide();
                }
                else {
                    $(".pending-tab").removeClass("active");
                    $(".pending-requests").hide();
                    $(".approved-tab").removeClass("active");
                    $(".declined-tab").addClass("active");
                    $(".approved-requests").hide();
                    $(".declined-requests").show();
                }
            },

            isWithinDeadline: function (index) {
                var request = this.pending_all[index],
                    session_id = request.session_id;
                for (var i in request.dropdown_list) {
                    if (request.dropdown_list[i][2] == session_id) {
                        var class_names = request.dropdown_list[i][1];
                        return class_names.includes('within-deadline')
                    }
                }
            },

            trans: function (text) {
                return gettext(text)
            }
        },
        created: function () {
            Vue.http.get(data_url).then(function (resp) {
                fetchData(resp)
            })
        }
    });

    function fetchData(resp) {
        resp.json().then(function (data) {
            ILTValidationList.to_validate = {};
            ILTValidationList.to_unsubscribe = {};
            ILTValidationList.pending_all = data.pending_all;
            ILTValidationList.session_info = data.session_info;
            ILTValidationList.accommodation = data.accommodation;
            ILTValidationList.date_format = data.date_format;
            ILTValidationList.cached_request = {};
            ILTValidationList.approved_all = data.approved_all;
            ILTValidationList.declined_all = data.declined_all;
        })
    }

    function getValidationList() {
        Vue.http.get(data_url).then(function (resp) {
            fetchData(resp)
        })
    }

    // initialize
    // getValidationList()
}