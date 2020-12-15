
Courseware.prefix = '';

/* eslint-disable */
function Courseware(options) {
  this.options = options;

  Logger.bind();
  this.render();
  var $courseIndex = $('.course-index');
  var outlineVisibleInit = function() {
    //always show course outline on desktop version
    if ($courseIndex.hasClass('None') && $(window).width() > 768) {
      $courseIndex.addClass('showing');
    }
  }
  outlineVisibleInit();
  this.eventInit();
}

Courseware.prototype.eventInit = function() {
  var $courseContent = $('.course-content');
  var $courseIndex = $('.course-index');
  var $leftSideIcon = $courseIndex.find('.back-link > i');
  var iconStatusInit = function() {
    var $icon = $courseContent.find('.page-header i');
    var $iconInSearchResult = $('.courseware-results-wrapper .page-header i');
    var $leftSideIcon = $courseIndex.find('.back-link > i');
    var arr = [$icon, $iconInSearchResult, $leftSideIcon]
    for(var i=0; i<arr.length; i++) {
      if (!$courseIndex.hasClass('showing')) {
        arr[i].removeClass('fa-outdent').addClass('fa-indent').attr('title', this.options.textExtend)
      } else {
        arr[i].removeClass('fa-indent').addClass('fa-outdent').attr('title', this.options.textCollapse)
      }
    }
  }
  var toggleCourseOutline = function () {
    $courseIndex.toggleClass('showing');
    iconStatusInit();

    // 850 ms is a little bit more then 800ms the effect of course outline suppose to take.
    setTimeout(function () {
      window.dispatchEvent(new Event('resize'));
    }, 850)

  };
  iconStatusInit = iconStatusInit.bind(this)
  toggleCourseOutline = toggleCourseOutline.bind(this)
  $leftSideIcon.on('click', toggleCourseOutline);
  $('.course-content > .page-header > i').on('click', toggleCourseOutline);
  $('.courseware-results-wrapper').delegate('.page-header > i', 'click', toggleCourseOutline);
  iconStatusInit();
}

Courseware.prototype.render = function() {
    var courseContentElement = $('.course-content')[0];
    var blocks = XBlock.initializeBlocks(courseContentElement);

    if (courseContentElement.dataset.enableCompletionOnViewService === 'true') {
      RequireJS.require(['bundles/CompletionOnViewService'], function() {
          markBlocksCompletedOnViewIfNeeded(blocks[0].runtime, courseContentElement);
      });
    }

    return $('.course-content .histogram').each(function() {
      var error, histg, id;
      id = $(this).attr('id').replace(/histogram_/, '');
      try {
        histg = new Histogram(id, $(this).data('histogram'));
      } catch (_error) {
        error = _error;
        histg = error;
        if (typeof console !== "undefined" && console !== null) {
          console.log(error);
        }
      }
      return histg;
    });
  };

export { Courseware };
