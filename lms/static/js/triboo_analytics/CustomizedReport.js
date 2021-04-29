/* eslint-disable react/no-danger, import/prefer-default-export */
import React from 'react';
import PropTypes from 'prop-types';
import 'select2'
import 'select2/dist/css/select2.css'
import {ReactRenderer} from '../../../../common/static/js/src/ReactRenderer'
import {pick} from 'lodash'
import ReportTypeAndCourseReport from './ReportTypeAndCourseReport'

export class CustomizedReport {
    constructor(props) {
        //comes from beginning of customized_report.js
        this.log = console.log.bind(console)

        $(() => {
            new ReactRenderer({
                component: ReportTypeAndCourseReport,
                selector: '.report_type_and_course_selected',
                componentName: 'CustomizedReport',
                props: {...props, onChange: (reportTypeValue,
                                             selectedCourses,
                                             query_tuples,
                                             startDate,
                                             endDate,
                                             selectedEnrollments,
                                             limit) => {
                        this.reportTypeValue = reportTypeValue
                        this.selectedCourses = selectedCourses
                        this.query_tuples = query_tuples
                        this.selectedEnrollments = selectedEnrollments
                        this.limit = limit
                        this.goButtonStatusUpdate();
                        this.sectionStatusUpdate();
                    }
                }
            });
            this.$submitButton = $('input[type=submit]');
            this.$reportType = $('#report_type');
            this.$courseReport = $('#course_selected');
            this.oldCourseValues = []
            this.oldCourseTexts = []
            this.$courseReportSelect2 = this.$courseReport.select2();
            this.$accordingTrigger = $('.accordion-trigger');
            this.eventInit()
        })
    }

    eventInit() {
        this.$submitButton.on('click', (e) => {
            e.preventDefault();
            setTimeout(async () => {
                const json = await this.submit()
                LearningTribes.dialog.show(json.message);
            }, 200)
        })
        $('#table-export-selection').delegate('label', 'click', () => {
            this.goButtonStatusUpdate()
            requestAnimationFrame(() => {
              const checked = $('#table-export-selection input[name=format]:checked')[0]
              if (checked) {
                const formatBar = document.getElementById('format_bar')
                const text = checked.parentNode.querySelector('label').textContent
                if (formatBar.querySelector('button')) {
                  formatBar.querySelector('button span').innerHTML = text
                } else {
                  const button = document.createElement('button')
                  button.className = 'property-option option-label'
                  formatBar.appendChild(button)
                  const span = document.createElement('span')
                  span.innerText = text
                  button.appendChild(span)
                }
              }
            })
        })
        $('#id_selected_properties').delegate('li label', 'click', (e) => {
            let prop_name = $(e.currentTarget)[0].innerText;
            let cur_input = $(e.currentTarget.querySelector('input'));
            let prop_id = 'tag_' + cur_input[0].id;
            let target_tag = $("#property_bar").children('#' + prop_id);
            let add_class = "property-option"
            if (!target_tag.length && cur_input[0].checked) {
                this.addTagToBar('#property_bar', add_class, prop_name, prop_id)
            } else if (target_tag.length && !cur_input[0].checked) {
                $("#property_bar button").remove('#' + prop_id);
            }
            this.goButtonStatusUpdate();
        });
        $('#property_bar').delegate('button', 'click', (e) => {
            let this_button = $(e.currentTarget);
            let input_id = this_button[0].id;
            let prop_id = input_id.substr(4);
            e.preventDefault();
            $(this_button).parent().children('button').remove('#' + input_id);
            $('#' + prop_id).attr("checked", false);
        });
        $('#report_bar').delegate('button', 'click', (e) => {
            e.preventDefault();
        });
        this.$accordingTrigger.on('click', (e) => {
            e.preventDefault();
        });
        $('#format_bar').delegate('button', 'click', (e) => {
            e.preventDefault();
        });
        this.triggerExpand();
        this.reportTypeAndCourseInit();
    }

    reportTypeAndCourseInit() {
        this.$courseReport.val('').change()
        this.$reportType.val('course_summary').change();
        $('#report_bar').addClass('is-hidden');
    }

    getBarTexts(bar) {
        let buttons = $(bar).children('button')
        let texts = []
        for (let b of buttons) {
            let span = $(b).children('.query')
            texts.push($(span)[0].innerText)
        }
        return texts
    }

    diffElement(arr1, arr2) {
        if (!arr1) {
            return arr2[0]
        } else if (!arr2) {
            return arr1[0]
        }
        let long = arr1
        let short = arr2
        if (arr1.length < arr2.length) {
            long = arr2
            short = arr1
        }
        for (let item of long) {
            if (short.indexOf(item) == -1) {
                return item
            }
        }
    };

    addTagToBar(tag_bar, tag_class, tag_name, tag_id) {
        $("<button/>", {
            "id": tag_id,
            "class": tag_class + " option-label"
        }).appendTo(tag_bar);
        $("<span/>", {
            "class": "query",
            text: tag_name
        }).appendTo("#" + tag_id);
        $("<span/>", {
            "class": "fa fa-times"
        }).appendTo("#" + tag_id);
    }

    goButtonStatusUpdate() {
        setTimeout(() => {
            if (this.checkFieldsSuccess()) {
                this.$submitButton.removeClass('disabled')
            } else if (!this.$submitButton.hasClass('disabled')) {
                this.$submitButton.addClass('disabled')
            }
        }, 200)
    }

    sectionStatusUpdate() {
        const reportTypeVal =  this.reportTypeValue
        if (reportTypeVal == 'ilt_global') {
            $('.filter-form').hide()
            $('.table-user-properties-form-customized').hide()
        } else {
            $('.filter-form').show()
            $('.table-user-properties-form-customized').show()
        }
    }

    checkFieldsSuccess() {
        const reportTypeVal =  this.reportTypeValue //this.$reportType.val()
        const courseReportVal = this.selectedCourses //this.$courseReportSelect2.val()
        const selectedCoursesNum = courseReportVal ? (courseReportVal.length || courseReportVal.value) : 0;
        const isFormatChecked = $('#table-export-selection input[name=format]:checked').length;
        const isBelowlimit = this.selectedEnrollments <= this.limit
        if (reportTypeVal == 'learner' || reportTypeVal == 'ilt_global' || reportTypeVal == 'ilt_learner') {
            return reportTypeVal && isFormatChecked && isBelowlimit
        } else {
            return reportTypeVal && selectedCoursesNum && isFormatChecked && isBelowlimit
        }
    }

    async submit() {
        let data = {
            report_type:this.reportTypeValue,
            courses_selected: this.selectedCourses.value || this.selectedCourses.map(p=>p.value).join(','),
            query_tuples: (this.query_tuples || []).map(p=>{
                const {value, key} = pick(p, ['key', 'value'])
                return [value, key]
            }),
            selected_properties: []
        }
        $('#form-customized-report').serializeArray().forEach(function ({name, value}) {
            if (name == 'selected_properties') {
                data['selected_properties'].push(value)
            } else {
                data[name] = value
            }
        })
        console.log('data', data)
        return await $.post({
            url: 'export/',
            //data: data
            data: JSON.stringify(data),
        })
        return await response.json()
    }

    expandSection(sectionToggleButton) {
        const $toggleButtonChevron = $(sectionToggleButton).children('.fa-chevron-down');
        const $contentPanel = $(document.getElementById(sectionToggleButton.getAttribute('aria-controls')));

        //$contentPanel.slideDown();
        $contentPanel.removeClass('is-hidden');
        $toggleButtonChevron.addClass('fa-rotate-180');
        sectionToggleButton.setAttribute('aria-expanded', 'true');
    }

    collapseSection(sectionToggleButton) {
        const $toggleButtonChevron = $(sectionToggleButton).children('.fa-chevron-down');
        const $contentPanel = $(document.getElementById(sectionToggleButton.getAttribute('aria-controls')));

        //$contentPanel.slideUp();
        $contentPanel.addClass('is-hidden');
        $toggleButtonChevron.removeClass('fa-rotate-180');
        sectionToggleButton.setAttribute('aria-expanded', 'false');
    }

    triggerExpand() {
      const sections = Array.prototype.slice.call(document.querySelectorAll('.accordion-trigger'));
      const sectionToggleButtons =  document.querySelectorAll('.section-button');

      sections.forEach(section => section.addEventListener('click', (event) => {
        const sectionToggleButton = event.currentTarget;
        if (sectionToggleButton.classList.contains('accordion-trigger')) {
          const isExpanded = sectionToggleButton.getAttribute('aria-expanded') === 'true';
          if (!isExpanded) {
            for (const button of sectionToggleButtons) {
                this.collapseSection(button);
                $(button).siblings('.label-bar').removeClass('is-hidden')
            }
            this.expandSection(sectionToggleButton);
            const $labelBar = $(sectionToggleButton).siblings('.label-bar')
            $labelBar.addClass('is-hidden')
          } else if (isExpanded) {
            this.collapseSection(sectionToggleButton);
            $(sectionToggleButton).siblings('.label-bar').removeClass('is-hidden')
          }
          event.preventDefault();
          event.stopImmediatePropagation();
        }
      }));
    }
}


CustomizedReport.propTypes = {
    translation: PropTypes.shape({
        report_type: PropTypes.string,
        course: PropTypes.string
    }),
    report_types: PropTypes.arrayOf(PropTypes.shape({
        type: PropTypes.string,
        title: PropTypes.string
    })),
    courses: PropTypes.arrayOf(PropTypes.shape({
        cid: PropTypes.string,
        course_title: PropTypes.string
    }))
};
