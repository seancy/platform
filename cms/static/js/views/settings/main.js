define(['js/views/validation', 'codemirror', 'underscore', 'jquery', 'jquery.ui', 'tinymce', 'js/utils/date_utils',
    'js/models/uploads', 'js/views/uploads', 'js/views/license', 'js/models/license',
    'common/js/components/views/feedback_notification', 'jquery.timepicker', 'date', 'gettext',
    'js/views/learning_info', 'js/views/instructor_info', 'js/views/reminder_info', 'js/views/course_tags_info',
    'edx-ui-toolkit/js/utils/string-utils'],
       function(ValidatingView, CodeMirror, _, $, ui, tinymce, DateUtils, FileUploadModel,
                FileUploadDialog, LicenseView, LicenseModel, NotificationView,
                timepicker, date, gettext, LearningInfoView, InstructorInfoView, ReminderInfoView, CourseTagsInfo, StringUtils) {
           'use strict';
           var DetailsView = ValidatingView.extend({
    // Model class is CMS.Models.Settings.CourseDetails
               events: {
                   'input input': 'updateModel',
                   'input textarea': 'updateModel',
        // Leaving change in as fallback for older browsers
                   'change input': 'updateModel',
                   'change textarea': 'updateModel',
                   'change select': 'updateModel',
                   'click .remove-course-introduction-video': 'removeVideo',
                   'focus #course-about-sidebar-html': 'codeMirrorize',
                   'mouseover .timezone': 'updateTime',
        // would love to move to a general superclass, but event hashes don't inherit in backbone :-(
                   'focus :input': 'inputFocus',
                   'blur :input': 'inputUnfocus',
                   'click .action-upload-image': 'uploadImage',
                   'click .add-course-learning-info': 'addLearningFields',
                   'click .add-course-instructor-info': 'addInstructorFields',
                   'click .add-course-reminder-info': 'addReminderFields',
                   'click #course-order-increase': 'increaseCourseOrder',
                   'click #course-order-decrease': 'decreaseCourseOrder',
                   'click .add-course-tags': 'addCourseTags',
                   'click .delete-course-btn': 'deleteCourse'
               },

               initialize: function(options) {
                   options = options || {};
        // fill in fields
                   this.$el.find('#course-category').val(this.model.get('course_category'));
                   this.$el.find('#course-country').val(this.model.get('course_country'));
                   this.$el.find('#course-language').val(this.model.get('language'));
                   this.$el.find('#course-organization').val(this.model.get('org'));
                   this.$el.find('#course-number').val(this.model.get('course_id'));
                   this.$el.find('#course-name').val(this.model.get('run'));
                   this.$el.find('.set-date').datepicker({dateFormat: 'm/d/yy'});

        // Avoid showing broken image on mistyped/nonexistent image
                   this.$el.find('img').error(function() {
                       $(this).hide();
                   });
                   this.$el.find('img').load(function() {
                       $(this).show();
                   });

                   this.listenTo(this.model, 'invalid', this.handleValidationError);
                   this.listenTo(this.model, 'change', this.showNotificationBar);
                   this.selectorToField = _.invert(this.fieldToSelectorMap);
        // handle license separately, to avoid reimplementing view logic
                   this.licenseModel = new LicenseModel({asString: this.model.get('license')});
                   this.licenseView = new LicenseView({
                       model: this.licenseModel,
                       el: this.$('#course-license-selector').get(),
                       showPreview: true
                   });
                   this.listenTo(this.licenseModel, 'change', this.handleLicenseChange);

                   if (options.showMinGradeWarning || false) {
                       new NotificationView.Warning({
                           title: gettext('Course Credit Requirements'),
                           message: gettext('The minimum grade for course credit is not set.'),
                           closeIcon: true
                       }).show();
                   }

                   this.learning_info_view = new LearningInfoView({
                       el: $('.course-settings-learning-fields'),
                       model: this.model
                   });

                   this.instructor_info_view = new InstructorInfoView({
                       el: $('.course-instructor-details-fields'),
                       model: this.model
                   });

                   this.reminder_info_view = new ReminderInfoView({
                       el: $('.course-reminder-details-fields'),
                       model: this.model
                   });

                   this.course_tags_info_view = new CourseTagsInfo({
                       el: $('.course-tags'),
                       model: this.model
                   });

                   // This is used to set WYSIWYG text editor for course overview and desc.
                   tinymce.init({
                       selector: '.tinymce-editor',
                       statusbar: false,
                       menubar: false,
                       language: options.langCode,
                       plugins: 'lists link code',
                       toolbar: 'bold italic bullist numlist blockquote link unlink code',
                       init_instance_callback: function(editor) {
                           editor.on('Dirty', function(e) {
                               $('#' + this.id).trigger('change');
                           });
                       }
                   });

                   this.exportUrl = options.exportUrl;
                   this.homepageUrl = options.homepageUrl;
               },

               render: function() {
        // Clear any image preview timeouts set in this.updateImagePreview
                   clearTimeout(this.imageTimer);

                   DateUtils.setupDatePicker('start_date', this);
                   DateUtils.setupDatePicker('end_date', this);
                   DateUtils.setupDatePicker('certificate_available_date', this);
                   DateUtils.setupDatePicker('enrollment_start', this);
                   DateUtils.setupDatePicker('enrollment_end', this);

                   this.$el.find('#' + this.fieldToSelectorMap.overview).val(this.model.get('overview'));
                   tinymce.get('course-overview').setContent(this.model.get('overview'));

                   if (this.model.get('title') !== '') {
                       this.$el.find('#' + this.fieldToSelectorMap.title).val(this.model.get('title'));
                   } else {
                       var displayName = this.$el.find('#' + this.fieldToSelectorMap.title).attr('data-display-name');
                       this.$el.find('#' + this.fieldToSelectorMap.title).val(displayName);
                   }

                   this.$el.find('#' + this.fieldToSelectorMap.course_finish_days).val(this.model.get('course_finish_days'));
                   this.$el.find('#' + this.fieldToSelectorMap.course_re_enroll_time).val(this.model.get('course_re_enroll_time'));
                   this.$el.find('#' + this.fieldToSelectorMap.re_enroll_time_unit).val(this.model.get('re_enroll_time_unit'));
                   this.$el.find('#' + this.fieldToSelectorMap.periodic_reminder_day).val(this.model.get('periodic_reminder_day'));
                   if (this.model.get('periodic_reminder_enabled')) {
                       this.$('#' + this.fieldToSelectorMap.periodic_reminder_enabled).attr('checked', this.model.get('periodic_reminder_enabled'));
                   } else {
                       this.$('#' + this.fieldToSelectorMap.periodic_reminder_enabled).removeAttr('checked');
                   }

                   this.$el.find('#course-order').val(this.model.get('course_order'));

                   this.$el.find('#' + this.fieldToSelectorMap.subtitle).val(this.model.get('subtitle'));
                   this.$el.find('#' + this.fieldToSelectorMap.duration).val(this.model.get('duration'));
                   if (this.model.get('duration')) {
                       this.$el.find('#' + this.fieldToSelectorMap.course_duration_number).val(Number(this.model.get('duration').split(' ')[0]));
                       this.$el.find('#' + this.fieldToSelectorMap.course_duration_unit).val(this.model.get('duration').split(' ')[1]);
                   } else {
                       this.$el.find('#' + this.fieldToSelectorMap.course_duration_number).val(0);
                       this.$el.find('#' + this.fieldToSelectorMap.course_duration_unit).val('minutes');
                   }
                   this.$el.find('#' + this.fieldToSelectorMap.description).val(this.model.get('description'));
                   tinymce.get('course-description').setContent(this.model.get('description'));

                   this.$el.find('#' + this.fieldToSelectorMap.short_description).val(this.model.get('short_description'));
                   this.$el.find('#' + this.fieldToSelectorMap.about_sidebar_html).val(
                       this.model.get('about_sidebar_html')
                   );
                   this.codeMirrorize(null, $('#course-about-sidebar-html')[0]);

                   var videoSample = this.model.videosourceSample();
                   if (videoSample == null) {
                       // just pass
                   } else if (videoSample.includes('//www.youtube.com/embed/')) {
                       this.$el.find('.current-course-introduction-video iframe').attr('src', videoSample).show();
                       this.$el.find('.current-course-introduction-video video').hide();
                   } else {
                       this.$el.find('.current-course-introduction-video iframe').hide();
                       this.$el.find('.current-course-introduction-video video').show().find('source')
                       .attr('src', videoSample);
                       this.$el.find('#intro-video').get(0).load();
                       if (videoSample === '') {
                           this.$el.find('.current-course-introduction-video .video-error').show();
                       } else {
                           this.$el.find('.current-course-introduction-video .video-error').hide();
                       }
                   }
                   this.$el.find('#' + this.fieldToSelectorMap.intro_video).val(this.model.get('intro_video') || '');
                   if (this.model.has('intro_video')) {
                       this.$el.find('.remove-course-introduction-video').show();
                   } else this.$el.find('.remove-course-introduction-video').hide();

                   this.$el.find('#' + this.fieldToSelectorMap.effort).val(this.model.get('effort'));

                   var courseImageURL = this.model.get('course_image_asset_path');
                   this.$el.find('#course-image-url').val(courseImageURL);
                   this.$el.find('#course-image').attr('src', courseImageURL);

                   var bannerImageURL = this.model.get('banner_image_asset_path');
                   this.$el.find('#banner-image-url').val(bannerImageURL);
                   this.$el.find('#banner-image').attr('src', bannerImageURL);

                   var videoThumbnailImageURL = this.model.get('video_thumbnail_image_asset_path');
                   this.$el.find('#video-thumbnail-image-url').val(videoThumbnailImageURL);
                   this.$el.find('#video-thumbnail-image').attr('src', videoThumbnailImageURL);

                   var pre_requisite_courses = this.model.get('pre_requisite_courses');
                   pre_requisite_courses = pre_requisite_courses.length > 0 ? pre_requisite_courses : '';
                   this.$el.find('#' + this.fieldToSelectorMap.pre_requisite_courses).val(pre_requisite_courses);

                   if (this.model.get('entrance_exam_enabled') === 'true') {
                       this.$('#' + this.fieldToSelectorMap.entrance_exam_enabled).attr('checked', this.model.get('entrance_exam_enabled'));
                       this.$('.div-grade-requirements').show();
                   } else {
                       this.$('#' + this.fieldToSelectorMap.entrance_exam_enabled).removeAttr('checked');
                       this.$('.div-grade-requirements').hide();
                   }

                   if (this.model.get('course_mandatory_enabled')) {
                       this.$('#' + this.fieldToSelectorMap.course_mandatory_enabled).attr('checked', this.model.get('course_mandatory_enabled'));
                   } else {
                       this.$('#' + this.fieldToSelectorMap.course_mandatory_enabled).removeAttr('checked');
                   }

                   this.$('#' + this.fieldToSelectorMap.entrance_exam_minimum_score_pct).val(this.model.get('entrance_exam_minimum_score_pct'));

                   var selfPacedButton = this.$('#course-pace-self-paced'),
                       instructorPacedButton = this.$('#course-pace-instructor-paced'),
                       paceToggleTip = this.$('#course-pace-toggle-tip');
                   (this.model.get('self_paced') ? selfPacedButton : instructorPacedButton).attr('checked', true);
                   if (this.model.canTogglePace()) {
                       selfPacedButton.removeAttr('disabled');
                       instructorPacedButton.removeAttr('disabled');
                       paceToggleTip.text('');
                   } else {
                       selfPacedButton.attr('disabled', true);
                       instructorPacedButton.attr('disabled', true);
                       paceToggleTip.text(gettext('Course pacing cannot be changed once a course has started.'));
                   }

                   this.licenseView.render();
                   this.learning_info_view.render();
                   this.instructor_info_view.render();
                   this.reminder_info_view.render();
                   this.course_tags_info_view.render();

                   return this;
               },
               fieldToSelectorMap: {
                   language: 'course-language',
                   start_date: 'course-start',
                   end_date: 'course-end',
                   course_category: 'course-category',
                   course_country: 'course-country',
                   enrollment_start: 'enrollment-start',
                   enrollment_end: 'enrollment-end',
                   certificate_available_date: 'certificate-available',
                   overview: 'course-overview',
                   title: 'course-title',
                   subtitle: 'course-subtitle',
                   course_duration_number: 'course-duration-number',
                   course_duration_unit: 'course-duration-unit',
                   description: 'course-description',
                   about_sidebar_html: 'course-about-sidebar-html',
                   short_description: 'course-short-description',
                   intro_video: 'course-introduction-video',
                   effort: 'course-effort',
                   course_image_asset_path: 'course-image-url',
                   banner_image_asset_path: 'banner-image-url',
                   video_thumbnail_image_asset_path: 'video-thumbnail-image-url',
                   pre_requisite_courses: 'pre-requisite-course',
                   entrance_exam_enabled: 'entrance-exam-enabled',
                   entrance_exam_minimum_score_pct: 'entrance-exam-minimum-score-pct',
                   course_settings_learning_fields: 'course-settings-learning-fields',
                   add_course_learning_info: 'add-course-learning-info',
                   add_course_instructor_info: 'add-course-instructor-info',
                   course_learning_info: 'course-learning-info',
                   add_course_reminder_info: 'add-course-reminder-info',
                   course_finish_days: 'course-finish-days',
                   course_re_enroll_time: 'course-re-enroll-time',
                   re_enroll_time_unit: 're-enroll-time-unit',
                   periodic_reminder_enabled: 'periodic-reminder-enabled',
                   periodic_reminder_day: 'periodic-reminder-day',
                   course_order: 'course-order',
                   course_order_increase: 'course-order-increase',
                   course_order_decrease: 'course-order-decrease',
                   course_mandatory_enabled: 'course-mandatory-enabled'
               },

               addLearningFields: function() {
        /*
        * Add new course learning fields.
        * */
                   var existingInfo = _.clone(this.model.get('learning_info'));
                   existingInfo.push('');
                   this.model.set('learning_info', existingInfo);
               },

               addInstructorFields: function() {
        /*
        * Add new course instructor fields.
        * */
                   var instructors = this.model.get('instructor_info').instructors.slice(0);
                   instructors.push({
                       name: '',
                       title: '',
                       organization: '',
                       image: '',
                       bio: ''
                   });
                   this.model.set('instructor_info', {instructors: instructors});
               },

               addReminderFields: function() {
                   /*
                    * Add new course email reminder fields.
                    * */
                   var existingInfo = _.clone(this.model.get('reminder_info'));
                   existingInfo.push('');
                   this.model.set('reminder_info', existingInfo);
               },

               increaseCourseOrder: function() {
                   var order = this.model.get('course_order');
                   if (order == null) {
                       this.$el.find('#course-order').val(10);
                       this.model.set('course_order', 10);
                   } else {
                       this.$el.find('#course-order').val(parseInt(order) + 10);
                       this.model.set('course_order', parseInt(order) + 10);
                   }
               },

               decreaseCourseOrder: function() {
                   var order = this.model.get('course_order');
                   if (order === '0') {
                       // empty filed
                   } else if (order == null || parseInt(order) - 10 <= 0) {
                       this.$el.find('#course-order').val(0);
                       this.model.set('course_order', 0);
                   } else {
                       this.$el.find('#course-order').val(parseInt(order) - 10);
                       this.model.set('course_order', parseInt(order) - 10);
                   }
               },

               updateTime: function(e) {
                   var now = new Date(),
                       hours = now.getUTCHours(),
                       minutes = now.getUTCMinutes(),
                       currentTimeText = StringUtils.interpolate(
                           gettext('{hours}:{minutes} (current UTC time)'), {
                               hours: hours,
                               minutes: minutes
                           }
                       );

                   $(e.currentTarget).attr('title', currentTimeText);
               },

               addCourseTags: function() {
                   var courseTags = _.clone(this.model.get('vendor'));
                   var tagInputValue = this.$el.find('#course-vendor').val().trim();
                   if (tagInputValue === '' || courseTags.indexOf(tagInputValue) > -1) {
                       return;
                   }
                   courseTags.push(tagInputValue);
                   this.model.set('vendor', courseTags);
                   this.course_tags_info_view.render();
               },

               deleteCourse: function() {
                   var dialogId = _.template($('#course-delete-dialog-tpl').html());
                   var dialogContent = dialogId({exportUrl: this.exportUrl});
                   var requestUrl = this.model.urlRoot;
                   var homepageUrl = this.homepageUrl;
                   LearningTribes.confirmation.show({ /* global LearningTribes */
                       message: dialogContent,
                       confirmationText: gettext('I want to delete the course'),
                       cancelationText: gettext('Cancel'),
                       confirmationCallback: function() {
                           $.ajax({
                               type: 'DELETE',
                               url: requestUrl
                           }).done(function() {
                               self.location.href = homepageUrl;
                           }).fail(function() {
                               self.location.href = homepageUrl;
                           });
                       }
                   });
               },

               updateModel: function(event) {
                   var value;
                   var index = event.currentTarget.getAttribute('data-index');
                   switch (event.currentTarget.id) {
                   case 'course-learning-info-' + index:
                       value = $(event.currentTarget).val();
                       var learningInfo = this.model.get('learning_info');
                       learningInfo[index] = value;
                       this.showNotificationBar();
                       break;
                   case 'course-reminder-info-' + index:
                       value = $(event.currentTarget).val();
                       var reminderInfo = this.model.get('reminder_info');
                       reminderInfo[index] = value;
                       this.showNotificationBar();
                       break;
                   case 'course-instructor-name-' + index:
                   case 'course-instructor-title-' + index:
                   case 'course-instructor-organization-' + index:
                   case 'course-instructor-bio-' + index:
                       value = $(event.currentTarget).val();
                       var field = event.currentTarget.getAttribute('data-field'),
                           instructors = this.model.get('instructor_info').instructors.slice(0);
                       instructors[index][field] = value;
                       this.model.set('instructor_info', {instructors: instructors});
                       this.showNotificationBar();
                       break;
                   case 'course-instructor-image-' + index:
                       instructors = this.model.get('instructor_info').instructors.slice(0);
                       instructors[index].image = $(event.currentTarget).val();
                       this.model.set('instructor_info', {instructors: instructors});
                       this.showNotificationBar();
                       this.updateImagePreview(event.currentTarget, '#course-instructor-image-preview-' + index);
                       break;
                   case 'course-image-url':
                       this.updateImageField(event, 'course_image_name', '#course-image');
                       break;
                   case 'banner-image-url':
                       this.updateImageField(event, 'banner_image_name', '#banner-image');
                       break;
                   case 'video-thumbnail-image-url':
                       this.updateImageField(event, 'video_thumbnail_image_name', '#video-thumbnail-image');
                       break;
                   case 'entrance-exam-enabled':
                       if ($(event.currentTarget).is(':checked')) {
                           this.$('.div-grade-requirements').show();
                       } else {
                           this.$('.div-grade-requirements').hide();
                       }
                       this.setField(event);
                       break;
                   case 'entrance-exam-minimum-score-pct':
            // If the val is an empty string then update model with default value.
                       if ($(event.currentTarget).val() === '') {
                           this.model.set('entrance_exam_minimum_score_pct', this.model.defaults.entrance_exam_minimum_score_pct);
                       } else {
                           this.setField(event);
                       }
                       break;
                   case 'pre-requisite-course':
                       var value = $(event.currentTarget).val();
                       value = value === '' ? [] : [value];
                       this.model.set('pre_requisite_courses', value);
                       break;
        // Don't make the user reload the page to check the Youtube ID.
        // Wait for a second to load the video, avoiding egregious AJAX calls.
                   case 'course-introduction-video':
                       this.clearValidationErrors();
                       var previewsource = this.model.set_videosource($(event.currentTarget).val());
                       clearTimeout(this.videoTimer);
                       this.videoTimer = setTimeout(_.bind(function() {
                           if (previewsource == null) {
                               this.$el.find('.current-course-introduction-video iframe').attr('src', '').show();
                               this.$el.find('.current-course-introduction-video video').hide();
                           } else if (previewsource.includes('//www.youtube.com/embed/')) {
                               this.$el.find('.current-course-introduction-video iframe').attr('src', previewsource).show();
                               this.$el.find('.current-course-introduction-video video').hide();
                           } else {
                               this.$el.find('.current-course-introduction-video iframe').hide();
                               this.$el.find('.current-course-introduction-video video').show().find('source')
                               .attr('src', previewsource);
                               this.$el.find('#intro-video').get(0).load();
                               if (previewsource === '') {
                                   this.$el.find('.current-course-introduction-video .video-error').show();
                               } else {
                                   this.$el.find('.current-course-introduction-video .video-error').hide();
                               }
                           }
                           if (this.model.has('intro_video')) {
                               this.$el.find('.remove-course-introduction-video').show();
                           } else {
                               this.$el.find('.remove-course-introduction-video').hide();
                           }
                       }, this), 1000);
                       break;
                   case 'course-pace-self-paced':
            // Fallthrough to handle both radio buttons
                   case 'course-pace-instructor-paced':
                       this.model.set('self_paced', JSON.parse(event.currentTarget.value));
                       break;

                   case 'course-duration-number':
                       var durationNum = $(event.currentTarget).val();
                       var durationUnit = this.$el.find('#' + this.fieldToSelectorMap.course_duration_unit).val();
                       if (durationNum !== '') {
                           this.model.set('duration', durationNum + ' ' + durationUnit);
                       } else {
                           this.model.set('duration', '');
                       }
                       break;
                   case 'course-duration-unit':
                       durationNum = this.$el.find('#' + this.fieldToSelectorMap.course_duration_number).val();
                       durationUnit = $(event.currentTarget).val();
                       if (durationNum) {
                           this.model.set('duration', durationNum + ' ' + durationUnit);
                       } else {
                           this.model.set('duration', '');
                       }
                       break;

                   case 'course-order':
                   case 'course-mandatory-enabled':
                   case 'periodic-reminder-enabled':
                   case 'periodic-reminder-day':
                   case 'course-re-enroll-time':
                   case 're-enroll-time-unit':
                   case 'course-finish-days':
                   case 'course-language':
                   case 'course-category':
                   case 'course-country':
                   case 'course-effort':
                   case 'course-title':
                   case 'course-subtitle':
                   case 'course-short-description':
                       this.setField(event);
                       break;
                   case 'course-overview':
                   case 'course-description':
                       tinymce.activeEditor.save();
                       this.setField(event);
                       break;
                   case 'course-vendor':
                       break;
                   default: // Everything else is handled by datepickers and CodeMirror.
                       break;
                   }

                   var name = event.currentTarget.getAttribute('name');
                   var checkedValue = [];
                   if (name === 'learning-group[]') {
                       $("input[name='learning-group[]']:checked").each(function() {
                           checkedValue.push($(this).val());
                       });
                       this.model.set('enrollment_learning_groups', checkedValue);
                   } else if (name === 'course-tag[]') {
                       $("input[name='course-tag[]']:checked").each(function() {
                           checkedValue.push($(this).val());
                       });
                       this.model.set('vendor', checkedValue);
                   }
               },

               updateImageField: function(event, image_field, selector) {
                   this.setField(event);
                   var url = $(event.currentTarget).val();
                   var image_name = _.last(url.split('/'));
        // If image path is entered directly, we need to strip the asset prefix
                   image_name = _.last(image_name.split('block@'));
                   this.model.set(image_field, image_name);
                   this.updateImagePreview(event.currentTarget, selector);
               },
               updateImagePreview: function(imagePathInputElement, previewSelector) {
        // Wait to set the image src until the user stops typing
                   clearTimeout(this.imageTimer);
                   this.imageTimer = setTimeout(function() {
                       $(previewSelector).attr('src', $(imagePathInputElement).val());
                   }, 1000);
               },
               removeVideo: function(event) {
                   event.preventDefault();
                   if (this.model.has('intro_video')) {
                       this.model.set_videosource(null);
                       this.$el.find('.current-course-introduction-video iframe').attr('src', '').show();
                       this.$el.find('.current-course-introduction-video video').hide();
                       this.$el.find('#' + this.fieldToSelectorMap.intro_video).val('');
                       this.$el.find('.remove-course-introduction-video').hide();
                   }
               },
               codeMirrors: {},
               codeMirrorize: function(e, forcedTarget) {
                   var thisTarget, cachethis, field, cmTextArea;
                   if (forcedTarget) {
                       thisTarget = forcedTarget;
                       thisTarget.id = $(thisTarget).attr('id');
                   } else if (e !== null) {
                       thisTarget = e.currentTarget;
                   } else {
            // e and forcedTarget can be null so don't deference it
            // This is because in cases where we have a marketing site
            // we don't display the codeMirrors for editing the marketing
            // materials, except we do need to show the 'set course image'
            // workflow. So in this case e = forcedTarget = null.
                       return;
                   }

                   if (!this.codeMirrors[thisTarget.id]) {
                       cachethis = this;
                       field = this.selectorToField[thisTarget.id];
                       this.codeMirrors[thisTarget.id] = CodeMirror.fromTextArea(thisTarget, {
                           mode: 'text/html', lineNumbers: true, lineWrapping: true});
                       this.codeMirrors[thisTarget.id].on('change', function(mirror) {
                           mirror.save();
                           cachethis.clearValidationErrors();
                           var newVal = mirror.getValue();
                           if (cachethis.model.get(field) !== newVal) {
                               cachethis.setAndValidate(field, newVal);
                           }
                       });
                       cmTextArea = this.codeMirrors[thisTarget.id].getInputField();
                       cmTextArea.setAttribute('id', thisTarget.id + '-cm-textarea');
                   }
               },

               revertView: function() {
                   // Make sure that the CodeMirror instance has the correct
                   // data from its corresponding textarea
                   var self = this;
                   this.model.fetch({
                       success: function() {
                           self.render();
                           _.each(self.codeMirrors, function(mirror) {
                               var ele = mirror.getTextArea();
                               var field = self.selectorToField[ele.id];
                               mirror.setValue(self.model.get(field));
                           });
                           self.licenseModel.setFromString(self.model.get('license'), {silent: true});
                           self.licenseView.render();
                       },
                       reset: true,
                       silent: true});
               },
               setAndValidate: function(attr, value) {
        // If we call model.set() with {validate: true}, model fields
        // will not be set if validation fails. This puts the UI and
        // the model in an inconsistent state, and causes us to not
        // see the right validation errors the next time validate() is
        // called on the model. So we set *without* validating, then
        // call validate ourselves.
                   this.model.set(attr, value);
                   this.model.isValid();
               },

               showNotificationBar: function() {
                   // We always call showNotificationBar with the same args, just
                   // delegate to superclass
                   ValidatingView.prototype.showNotificationBar.call(this,
                       this.save_message,
                       _.bind(this.saveView, this),
                       _.bind(this.revertView, this));
               },

               uploadImage: function(event) {
                   event.preventDefault();
                   var title = '',
                       selector = '',
                       image_key = '',
                       image_path_key = '';
                   switch (event.currentTarget.id) {
                   case 'upload-course-image':
                       title = gettext('Upload your course image.');
                       selector = '#course-image';
                       image_key = 'course_image_name';
                       image_path_key = 'course_image_asset_path';
                       break;
                   case 'upload-banner-image':
                       title = gettext('Upload your banner image.');
                       selector = '#banner-image';
                       image_key = 'banner_image_name';
                       image_path_key = 'banner_image_asset_path';
                       break;
                   case 'upload-video-thumbnail-image':
                       title = gettext('Upload your video thumbnail image.');
                       selector = '#video-thumbnail-image';
                       image_key = 'video_thumbnail_image_name';
                       image_path_key = 'video_thumbnail_image_asset_path';
                       break;
                   }

                   var upload = new FileUploadModel({
                       title: title,
                       message: gettext('Files must be in JPEG or PNG format.'),
                       mimeTypes: ['image/jpeg', 'image/png']
                   });
                   var self = this;
                   var modal = new FileUploadDialog({
                       model: upload,
                       onSuccess: function(response) {
                           var options = {};
                           options[image_key] = response.asset.display_name;
                           options[image_path_key] = response.asset.url;
                           self.model.set(options);
                           self.render();
                           $(selector).attr('src', self.model.get(image_path_key));
                       }
                   });
                   modal.show();
               },

               handleLicenseChange: function() {
                   this.showNotificationBar();
                   this.model.set('license', this.licenseModel.toString());
               }
           });

           return DetailsView;
       }); // end define()
