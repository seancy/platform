const MyCourses = function (tab) {
    function updateCourseList(activeTab) {
        var $courses = $(".listing-courses li.course-item");
        var activeStatus = activeTab;
        if (activeTab == 'not-started') {
            activeStatus = 'Not_started';
        } else if (activeTab == 'started') {
            activeStatus = 'Started';
        } else if (activeTab == 'finished') {
            activeStatus = 'Finished';
        }
        $courses.each(function () {
            if (activeStatus == 'all-courses' || $(this).data('status') == activeStatus) {
                $(this).show();
            } else {
                $(this).hide();
            }
        })
    }


    $(".my-courses-nav li").click(function () {
        $(this).find('.btn-link').addClass('active-section');
        $(this).siblings().find('.btn-link').removeClass('active-section');
        updateCourseList($(this).attr('id'));
        const $courses = $('.my-courses article.course')
        $courses.addClass('skeleton')
        setTimeout(()=>{
            $courses.removeClass('skeleton')
        },500)
    });

    $('document').ready(function () {
        updateCourseList(tab);
        setTimeout(()=>{
            $('.my-courses article.skeleton').removeClass('skeleton')
        }, 500)

    });
}

export {MyCourses};
