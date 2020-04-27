/* eslint-disable react/no-danger, import/prefer-default-export */
import React from 'react';
import PropTypes from 'prop-types';
import 'select2'
import 'select2/dist/css/select2.css'
import {ReactRenderer} from '../../../../common/static/js/src/ReactRenderer'
import LabelValue from 'sec-react-label-value'
import DateRange from 'se-react-date-range'
import {pick} from 'lodash'

export class CustomizedReport {
    constructor(props) {
        //comes from beginning of customized_report.js
        this.log = console.log.bind(console)

        $(() => {
            new ReactRenderer({
                component: ReportTypeAndCourseReport,
                selector: '.report_type_and_course_selected',
                componentName: 'CustomizedReport',
                props: {...props, onChange: (a0, a1, query_tuples)=>{
                        this.query_tuples = query_tuples
                    }
                }
            });
            this.$submitButton = $('input[type=submit]');
            this.$reportType = $('#report_type');
            this.$courseReport = $('#course_selected');
            this.oldCourseValues = []
            this.oldCourseTexts = []
            this.selectedEnrollments = 0
            this.enrollmentLimit = 6
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
            //this.synchronizePeriodDates();
            setTimeout(async () => {
                const json = await this.submit()
                LearningTribes.dialog.show(json.message);
            }, 200)
        })
        this.$reportType.on('change', () => {
            let report_text = this.$reportType.find("option:selected").text()
            let report_id = "tag_" + report_text.replace(/\ /g, '_')
            $('#report_bar').empty()
            this.addTagToBar('#report_bar', 'report-option', report_text, report_id)
            $('#' + report_id + ' .fa').css('display','none')
            this.resetCourseSelect()
            this.goButtonStatusUpdate()
        })
        this.$courseReport.on('change', () => {
            let report_val = this.$reportType.find("option:selected").val()
            if (report_val == 'course_summary') {
                let vals = []
                let texts = []
                let nums = []
                this.$courseReport.find("option:selected").each(function() {
                    vals.push($(this).val());
                    let t = $(this).text();
                    let split_ind = t.lastIndexOf('(');
                    let ctext = t.substring(0, split_ind - 1);
                    let cnum = t.substring(split_ind + 1, t.lastIndexOf('user') - 1);
                    texts.push(ctext);
                    nums.push(cnum);
                })
                let old_vals = this.oldCourseValues
                let old_texts = this.oldCourseTexts
                let diff_val = this.diffElement(old_vals, vals)
                let diff_text = this.diffElement(old_texts, texts)
                let sum_nums = 0
                if (nums.length > 0) {
                    sum_nums = nums.reduce(function (a, b) {
                        return parseInt(a) + parseInt(b);
                    })
                }
                if (sum_nums > this.enrollmentLimit) {
                    alert('The enrollments of the courses you have been selected is above the limit.')
                    let set_vals = this.oldCourseValues ? this.oldCourseValues : ''
                    this.$courseReportSelect2.val(set_vals).change();
                } else if (diff_val) {
                    let tag_id = 'tag_' + diff_val.split(':')[1].replace(/\+/g, '_');
                    if (vals.length > old_vals.length){
                        this.addTagToBar('#course_bar', 'course-option', diff_text, tag_id)
                    } else {
                        $("#course_bar button").remove('#' + tag_id);
                    }
                    this.oldCourseValues = vals
                    this.oldCourseTexts = texts
                    this.selectedEnrollments = nums
                }
            } else if (report_val == 'course_progress' || report_val == 'course_time_spent') {
                let t = this.$courseReport.find("option:selected").text()
                let val = this.$courseReport.find("option:selected").val()
                let split_ind = t.lastIndexOf('(');
                let ctext = t.substring(0, split_ind - 1);
                let cnum = t.substring(split_ind + 1, t.lastIndexOf('user') - 1);
                let cid = "tag_" + ctext.replace(/\ /g, '_')
                $('#course_bar').empty()
                this.addTagToBar('#course_bar', 'course-option', ctext, cid)
                $('#' + cid + ' .fa').css('display','none')
                this.selectedEnrollments.push(cnum)
            }
            let current_num = 0
            if (this.selectedEnrollments.length > 0) {
                current_num = this.selectedEnrollments.reduce(function (a, b) {
                    return parseInt(a) + parseInt(b);
                })
            }
            $('#enrollment_selected')[0].innerText = current_num
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
            let report_val = this.$reportType.find("option:selected").val()
            if (report_val == 'course_summary'){
                let this_button = $(e.currentTarget);
                let input_id = this_button[0].id;
                $(this_button).parent().children('button').remove('#' + input_id);
                let bar_texts = this.getBarTexts('#course_bar');
                let vals = this.oldCourseValues;
                let texts = this.oldCourseTexts;
                let nums = this.selectedEnrollments;
                let diff_text = this.diffElement(texts, bar_texts);
                let diff_index = texts.indexOf(diff_text);
                vals.splice(diff_index, 1);
                texts.splice(diff_index, 1);
                nums.splice(diff_index, 1);
                let set_vals = vals ? vals : ''
                this.$courseReportSelect2.val(set_vals).change();
                this.oldCourseValues = vals;
                this.oldCourseTexts = texts;
                this.selectedEnrollments = nums;
            }
            let current_num = 0
            if (this.selectedEnrollments.length > 0) {
                current_num = this.selectedEnrollments.reduce(function (a, b) {
                    return parseInt(a) + parseInt(b);
                })
            }
            $('#enrollment_selected')[0].innerText = current_num
        });
        $('#report_bar').delegate('button', 'click', (e) => {
            e.preventDefault();
        });
        this.$accordingTrigger.on('click', (e) => {
            e.preventDefault();
        });
        $('#table-export-selection').delegate('input', 'click', (e) => {
            let format_val = $('#table-export-selection input[name=format]:checked')[0].value;
            if (format_val == 'xls') {
                this.enrollmentLimit = 4
            } else {
                this.enrollmentLimit = 6
            }
            $('#enrollment_limit').text(this.enrollmentLimit)
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

    resetCourseSelect() {
        let report_val = this.$reportType.find("option:selected").val()
        if (report_val == 'course_summary'){
            $('#course_selected option').remove('#null-option')
            $('#custom_course_section').removeClass('is-hidden')
        } else if (report_val == 'course_progress' || report_val == 'course_time_spent') {
            // <option key='' disabled selected value='' id='null-option'></option>
            $('#course_selected option').remove('#null-option')
            $("<option/>", {
                "id": 'null-option',
                value: '',
                key: ''
            }).prependTo('#course_selected');
            $('#custom_course_section').removeClass('is-hidden')
        } else {
            $('#custom_course_section').addClass('is-hidden')
        }
        this.$courseReport.val('').change()
        $('#course_bar').empty()
        this.oldCourseValues = []
        this.oldCourseTexts = []
        this.selectedEnrollments = []
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
        //const {query_tuples}=this.state
        let data = {
            query_tuples2: this.query_tuples.map(p=>pick(p, ['key', 'value'])),
            selected_properties: []
        }
        $('#form-customized-report').serializeArray().forEach(function ({name, value}) {
            if (name == 'selected_properties') {
                data['selected_properties'].push({name: value})
            } else {
                data[name] = value
            }
        })
        console.log('data', data)
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

    /*synchronizePeriodDates() {
        let from_day = $('#from_day').val()
        let to_day = $('#to_day').val()
        $('#from_day_return').val(from_day)
        $('#to_day_return').val(to_day)
    }*/

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
            $(sectionToggleButton).siblings('.label-bar').addClass('is-hidden')
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

class ReportTypeAndCourseReport extends React.Component {
    constructor(props) {
        super(props);

        this.state = {
            selectedKeyValues:[],
            hideCourseReportSelect: false,
            filterData:[{value: '', text: 'loading'}]
        };

        $(this.refs.report_type).select2().on('select2:select', this.recreateCourseSelect.bind(this));
        setTimeout(() => {
            $(this.refs.course_selected).select2({
                multiple: true,
                width: 'off',
                placeholder: "Course Name",
            });
        }, 300)

    }

    componentDidMount() {
        fetch('/analytics/common/get_properties/json/')
            .then(response=>{
                return response.json()
            })
            .then(data=>{
                this.setState({filterData: data.list})
            })
    }

    recreateCourseSelect(e) {
        let courseReportType = this.props.report_types.find(p => p.type == e.target.value).courseReportType,
            isMultiple = true, $courseSelected = $(this.refs.course_selected);
        $courseSelected.data('select2') && $courseSelected.select2("destroy")
        if (courseReportType == 'multiple' || courseReportType == 'single') {
            isMultiple = courseReportType == 'single' ? false : true;
            $courseSelected.select2({
                width: 'off',
                multiple: isMultiple,
                placeholder: "Course Name",
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

    filterOnChange(selectedKeyValues) {
        //query_tuples
        this.setState({selectedKeyValues}, this.fireOnChange)

        //console.log('e', e)
    }

    periodOnChange(e, f) {
        console.log('e', e, f)
    }

    fireOnChange(){
        const {onChange}=this.props
        const {selectedKeyValues} = this.state
        onChange && onChange('', '', selectedKeyValues)
    }

    render() {
        const {translation, report_types, courses} = this.props;

        const propertyData = [
            {value: 'zzz', text: 'aaa'},
        ]

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
                    <div id="report_section_contents" className="section-content">
                        <div className="report-type">
                            <select name="report_type" id="report_type" ref="report_type"
                            onChange={this.recreateCourseSelect.bind(this)}>
                                {report_types.map(({type, title}) => {
                                    return <option key={type} value={type}>{title}</option>
                                })}
                            </select>
                        </div>
                    </div>
                    <div id="report_bar" className="reports label-bar is-collapsed"></div>
                </div>
                <div className="custom-section" id="custom_course_section">
                    <button className="section-button accordion-trigger"
                            aria-expanded="${ 'false' }"
                            aria-controls="course_section_contents"
                            id="course_section">
                        <p className="section-title">Select course(s)</p>
                        <span className="fa fa-chevron-down" aria-hidden="true"></span>
                    </button>
                    <div id="course_section_contents" className="section-content is-hidden">
                        <div className={'course-report ' + (this.state.hideCourseReportSelect ? 'hide' : '')}>
                            <p className="section-label">The enrollments of the courses you have been selected is:
                                <span id="enrollment_selected">0</span>
                                . (<span id="enrollment_limit">6</span> at most)
                            </p>
                            <select id="course_selected" ref="course_selected">
                                {courses.map(({cid, course_title, course_enrollments}) => {
                                    return <option key={cid} value={cid}>{course_title} ({course_enrollments} users)</option>
                                })}
                            </select>
                        </div>
                    </div>
                    <div id="course_bar" className="courses label-bar is-collapsed"></div>
                </div>
                <div class="custom-section" id="filter-section">
                    <button class="section-button accordion-trigger"
                            aria-expanded="${ 'false' }"
                            aria-controls="filter_section_contents"
                            id="filter_section">
                        <p class="section-title">Filter your data</p>
                        <span class="fa fa-chevron-down" aria-hidden="true"></span>
                    </button>
                    <div id="filter_section_contents" class="section-content is-hidden">
                        <section class="filter-form">
                            <p class="section-label">Select user properties:</p>
                          <div id="filter-form">
                            <div class="table-filter-form">
                                <LabelValue data={this.state.filterData} onChange={this.filterOnChange.bind(this)} />
                            </div>
                          </div>
                        </section>
                        <section class="period-form">
                            <p class="section-label">Select a time range:</p>
                            <div id="period-table">
                                <DateRange onChange={this.periodOnChange.bind(this)}
                                           //label='Select a time range'
                                           buttonBegin='Last '
                                    startDateName='from_day2' endDateName='to_day2'/>
                            </div>
                        </section>
                    </div>
                    <div id="filter-bar" class="filters is-collapsed"></div>
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
