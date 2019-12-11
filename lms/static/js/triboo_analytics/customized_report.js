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
});