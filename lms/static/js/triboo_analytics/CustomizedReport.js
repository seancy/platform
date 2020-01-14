/* eslint-disable react/no-danger, import/prefer-default-export */
import React from 'react';
import PropTypes from 'prop-types';
import 'select2'
import 'select2/dist/css/select2.css'
import {ReactRenderer} from '../../../../common/static/js/src/ReactRenderer'

export class CustomizedReport {
    constructor(props) {
        //comes from beginning of customized_report.js
        this.log = console.log.bind(console)

        $(() => {
            new ReactRenderer({
                component: ReportTypeAndCourseReport,
                selector: '.report_type_and_course_selected',
                componentName: 'CustomizedReport',
                props: props
            });
            this.$submitButton = $('input[type=submit]');
            this.$reportType = $('#report_type');
            this.$courseReport = $('#course_selected');
            this.oldCourseValues = []
            this.oldCourseTexts = []
            this.$courseReportSelect2 = this.$courseReport.select2();
            this.$accordingTrigger = $('.accordion-trigger');
            this.eventInit()
            this.resetValue()
        })
    }

    eventInit() {
        this.$submitButton.on('click', (e) => {
            e.preventDefault();
            this.synchronizeProperties();
            this.synchronizeSelectedCourses();
            this.synchronizePeriodDates();
            setTimeout(async () => {
                const json = await this.submit()
                LearningTribes.dialog.show(json.message);
            }, 200)
        })
        this.$reportType.on('change', (e) => {
            let report_text = $(e.currentTarget).find("option:selected").text()
            log('report_text', report_text)

            this.resetCourseSelect()
            this.goButtonStatusUpdate()
        })
        this.$courseReport.on('change', (e) => {
            let vals = []
            let texts = []
            $(e.currentTarget).find("option:selected").each(function() {
                vals.push($(this).val());
                texts.push($(this).text());
            })
            let old_vals = this.oldCourseValues
            let old_texts = this.oldCourseTexts
            let diff_val = this.diffElement(old_vals, vals)
            let diff_text = this.diffElement(old_texts, texts)
            if (diff_val) {
                let tag_id = 'tag_' + diff_val.split(':')[1].replace(/\+/g, '_');
                if (vals.length > old_vals.length){
                    this.addTagToBar('#course_bar', 'course-option', diff_text, tag_id)
                } else {
                    $("#course_bar button").remove('#' + tag_id);
                }
                this.oldCourseValues = vals
                this.oldCourseTexts = texts
            }
        })
        $('#table-export-selection').delegate('label', 'click', () => {
            this.goButtonStatusUpdate()
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
        $('#course_bar').delegate('button', 'click', (e) => {
            e.preventDefault();
            let this_button = $(e.currentTarget);
            let input_id = this_button[0].id;
            $(this_button).parent().children('button').remove('#' + input_id);
            let bar_texts = this.getBarTexts('#course_bar');
            let vals = this.oldCourseValues;
            let texts = this.oldCourseTexts;
            let diff_text = this.diffElement(texts, bar_texts);
            let diff_index = texts.indexOf(diff_text);
            vals.splice(diff_index, 1);
            texts.splice(diff_index, 1)
            let set_vals = vals ? vals : ''
            this.$courseReportSelect2.val(set_vals).change();
            this.oldCourseValues = vals;
            this.oldCourseTexts = texts;
        });
        this.$accordingTrigger.on('click', (e) => {
            e.preventDefault();
        });
        this.triggerExpand();
        this.resetCourseSelect();
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
            "class": tag_class,
        }).appendTo(tag_bar);
        $("<span/>", {
            "class": "query",
            text: tag_name
        }).appendTo("#" + tag_id);
        $("<span/>", {
            "class": "fa fa-times"
        }).appendTo("#" + tag_id);
    }

    resetCourseSelect() {
        this.$courseReport.val('')
    }

    resetValue() {
        //comes from window.onload event in customized_report.js
        $("#id_query_string").val("");
        $("#id_queried_field").find("option[value='user__profile__name']").attr("selected", true)

        //comes from document.ready event in customized_report.js
        var report_types = $("#report_type > option")
        var selected_report_type = "";
        for (var i = 0; i < report_types.length; i++) {
            if (report_types[i].selected) {
                selected_report_type = report_types[i].value
            }
        }
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

    checkFieldsSuccess() {
        const reportTypeVal = this.$reportType.val()
        const courseReportVal = this.$courseReportSelect2.val()
        const selectedCoursesNum = courseReportVal ? courseReportVal.length : 0;
        const isFormatChecked = $('#table-export-selection input[name=format]:checked').length;
        if (reportTypeVal == 'learner' || reportTypeVal == 'ilt_global' || reportTypeVal == 'ilt_learner') {
            return reportTypeVal && isFormatChecked
        } else {
            return reportTypeVal && selectedCoursesNum && isFormatChecked
        }
    }

    async submit() {
        let data = {
            selected_properties: []
        }
        $('#form-customized-report').serializeArray().forEach(function ({name, value}) {
            if (name == 'selected_properties') {
                data['selected_properties'].push({name: value})
            }
            data[name] = value
        })
        return await $.post({
            url: 'export/',
            data: data
        })
        return await response.json()
    }

    synchronizeProperties() {
        var fs = $('.active-filters button')
        var hidden_queries = $('#hidden-queries')
        var html = ''
        for (var i = 0; i < fs.length; i++) {
            html += '<input type="hidden", name="queried_field_' + (i + 1) + '", value=' + fs[i].dataset.type + '>'
            html += '<input type="hidden", name="query_string_' + (i + 1) + '", value=' + fs[i].dataset.value + '>'
        }
        hidden_queries.empty().append(html)
    }

    synchronizeSelectedCourses() {
        let courseSelectedValueStr = this.$courseReportSelect2.val();
        $('#course_selected_return').val(courseSelectedValueStr)
    }

    synchronizePeriodDates() {
        let from_day = $('#from_day').val()
        let to_day = $('#to_day').val()
        $('#from_day_return').val(from_day)
        $('#to_day_return').val(to_day)
    }

    expandSection(sectionToggleButton) {
        const $toggleButtonChevron = $(sectionToggleButton).children('.fa-chevron-down');
        const $contentPanel = $(document.getElementById(sectionToggleButton.getAttribute('aria-controls')));

        $contentPanel.slideDown();
        $contentPanel.removeClass('is-hidden');
        $toggleButtonChevron.addClass('fa-rotate-180');
        sectionToggleButton.setAttribute('aria-expanded', 'true');
    }

    collapseSection(sectionToggleButton) {
        const $toggleButtonChevron = $(sectionToggleButton).children('.fa-chevron-down');
        const $contentPanel = $(document.getElementById(sectionToggleButton.getAttribute('aria-controls')));

        $contentPanel.slideUp();
        $contentPanel.addClass('is-hidden');
        $toggleButtonChevron.removeClass('fa-rotate-180');
        sectionToggleButton.setAttribute('aria-expanded', 'false');
    }

    triggerExpand() {
      const sections = Array.prototype.slice.call(document.querySelectorAll('.accordion-trigger'));

      sections.forEach(section => section.addEventListener('click', (event) => {
        const sectionToggleButton = event.currentTarget;
        if (sectionToggleButton.classList.contains('accordion-trigger')) {
          const isExpanded = sectionToggleButton.getAttribute('aria-expanded') === 'true';
          if (!isExpanded) {
            expandSection(sectionToggleButton);
          } else if (isExpanded) {
            collapseSection(sectionToggleButton);
          }
          event.preventDefault();
          event.stopImmediatePropagation();
        }
      }));
    }
}

class ReportTypeAndCourseReport extends React.Component {
    constructor(props) {
        super(props);

        this.state = {
            hideCourseReportSelect: false
        };

        $(this.refs.report_type).select2().on('select2:select', this.recreateCourseSelect.bind(this));
        setTimeout(() => {
            $(this.refs.course_selected).select2({
                multiple: true,
                width: 'off'
            });
        }, 300)

    }

    recreateCourseSelect(e) {
        let courseReportType = this.props.report_types.find(p => p.type == e.target.value).courseReportType,
            isMultiple = true, $courseSelected = $(this.refs.course_selected);
        $courseSelected.data('select2') && $courseSelected.select2("destroy")
        if (courseReportType == 'multiple' || courseReportType == 'single') {
            isMultiple = courseReportType == 'single' ? false : true;
            $courseSelected.select2({
                width: 'off',
                multiple: isMultiple
            });
            this.setState({
                hideCourseReportSelect: false
            })
        } else {
            this.setState({
                hideCourseReportSelect: true
            })
        }
    }

    render() {
        const {translation, report_types, courses} = this.props;

        return (
            <React.Fragment>
                <div className="custom-section">
                    <button className="section-button accordion-trigger"
                            aria-expanded="${ 'false' }"
                            aria-controls="report_section_contents"
                            id="report_section">
                        <p className="section-title">Select a report type</p>
                        <span className="fa fa-chevron-down" aria-hidden="true"></span>
                    </button>
                    <div id="report_section_contents" className="section-content is-hidden">
                        <div className="report-type">
                            <label htmlFor="report_type">{translation.report_type}</label>
                            <select name="report_type" id="report_type" ref="report_type"
                                    onChange={this.recreateCourseSelect.bind(this)}>
                                        <option key='' disabled selected value=''></option>
                                {report_types.map(({type, title}) => {
                                    return <option key={type} value={type}>{title}</option>
                                })}
                            </select>
                        </div>
                    </div>
                    <div id="report_bar" className="reports hide-phone is-collapsed"></div>
                </div>
                <div className="custom-section">
                    <button className="section-button accordion-trigger"
                            aria-expanded="${ 'false' }"
                            aria-controls="course_section_contents"
                            id="course_section">
                        <p className="section-title">Select course(s)</p>
                        <span className="fa fa-chevron-down" aria-hidden="true"></span>
                    </button>
                    <div id="course_section_contents" className="section-content is-hidden">
                        <div className={'course-report ' + (this.state.hideCourseReportSelect ? 'hide' : '')}>
                            <label htmlFor="course_selected">{translation.course}</label>
                            <select id="course_selected" ref="course_selected">
                                {courses.map(({cid, course_title}) => {
                                    return <option key={cid} value={cid}>{course_title}</option>
                                })}
                            </select>
                        </div>
                    </div>
                    <div id="course_bar" className="courses hide-phone is-collapsed"></div>
                </div>
            </React.Fragment>
        )
    }
}

CustomizedReport.propTypes = ReportTypeAndCourseReport.propTypes = {
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
