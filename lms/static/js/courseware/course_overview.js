
$(function () {
    setTimeout(function () {
      var $courseDescription = $('.course-description');
      var $description = $('.subtitle-description-wrapper');
      if ($description.height() >= 172){
        $courseDescription.addClass('extend-mode');
      }
      var $subtitle = $courseDescription.find('.subtitle');
      if ($subtitle.height()<=16){
        $courseDescription.addClass('no-title-mode');
      }
    }, 2000)

    $('body').delegate('.extend-link', 'click', function (e) {
      var $src = $(e.currentTarget);
      var $courseDescription = $src.parent('.course-description');
      $courseDescription.toggleClass('all-paragraphs');
    })

    setTimeout(function () {
        $('.container .intro').removeClass('skeleton')
    },2500)
})
