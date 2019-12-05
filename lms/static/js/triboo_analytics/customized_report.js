var log = console.log.bind(console)

$(window).on("load", function () {
    $("#id_query_string").val("");
    $("#id_queried_field").find("option[value='user__profile__name']").attr("selected",true)
});

$(document).ready(function() {
    var report_types = $("#report_type > option")
    var selected_report_type = "";
    for (var i = 0; i < report_types.length; i++) {
        if (report_types[i].selected) {
            selected_report_type = report_types[i].value
        }
    }
    if (selected_report_type === 'course_summary') {
        $('#course_selected').select2({
            multiple: true
        });
    } else {
        $('#course_selected').select2()
    }

    // $('#submit-button').on('click', function (e) {
    //     e.preventDefault();
    //     console.log('e', e)
    //     console.log('e.currentTarget', e.currentTarget)
    //     console.log('e.currentTarget.form.action', e.currentTarget.form.action)
    //     $.ajax(e.currentTarget.form.action, {
    //         success: function (data) {
    //             LearningTribes.dialog.show(data.message)
    //         },
    //         error: function (data) {
    //             $('#export-error').text(data.message);
    //         }
    //     });
    // });
});

$('#course_selected').change(function() {
    var o = $('#course_selected > option')
    var all = "";
    for (var i = 0; i < o.length; i++) {
        if (o[i].selected) {
            all += o[i].value + ", ";
        }
    }
    all = all.substr(0, all.length - 2);
    $("#course_selected_return").val(all);
    log($("#course_selected_return")[0].value)
});