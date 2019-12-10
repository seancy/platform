/* eslint-disable react/no-danger, import/prefer-default-export */
import React from 'react';
import PropTypes from 'prop-types';
import 'select2'
import '../../../../node_modules/select2/dist/css/select2.css'
import {ReactRenderer} from '../../../../common/static/js/src/ReactRenderer'

export class CustomizedReport {
    constructor(props) {
        $(() => {
            new ReactRenderer({
                component: ReportTypeAndCourseReport,
                selector: '.report_type_and_course_selected',
                componentName: 'CustomizedReport',
                props: props
            });
            this.$submitButton = $('input[type=submit]');
            this.$courseReport = $('#course_selected');
            this.$courseReportSelect2 = this.$courseReport.select2();
            this.eventInit()
        })
    }

    eventInit() {
        this.$submitButton.on('click', (e) => {
            e.preventDefault();
            this.synchronizeSelectedCourses();
            setTimeout(async ()=>{
                const json = await this.submit()
                console.log(json)
                LearningTribes.dialog.show(json.message);
            },200)
        })
        this.$courseReport.on('change',()=>{
            if (this.checkFieldsSuccess()){
                this.$submitButton.removeClass('disabled')
            }else if (!this.$submitButton.hasClass('disabled')){
                this.$submitButton.addClass('disabled')
            }
        })
    }

    checkFieldsSuccess(){
        const courseReportVal = this.$courseReportSelect2.val()
        const selectedCoursesNum = courseReportVal ? courseReportVal.length : 0;
        if (selectedCoursesNum>0){
            return true;
        }
    }

    async submit() {
        let data = {}
        $('#form-customized-report').serializeArray().forEach(function (x) {
            data[x.name] = x.value
        })
        ///analytics/customized/export/
        return await $.post({
            url:'export/',
            data:data
        })
        return await response.json()
    }

    synchronizeSelectedCourses() {
        let courseSelectedValueStr = this.$courseReportSelect2.val();
        $('#course_selected_return').val(courseSelectedValueStr)
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
                <div>
                    <label htmlFor="report_type">{translation.report_type}</label>
                    <select name="report_type" id="report_type" ref="report_type"
                            onChange={this.recreateCourseSelect.bind(this)}>
                        {report_types.map(({type, title}) => {
                            return <option key={type} value={type}>{title}</option>
                        })}
                    </select>
                </div>
                <div className={'course-report ' + (this.state.hideCourseReportSelect ? 'hide' : '')}>
                    <label htmlFor="course_selected">{translation.course}</label>
                    <select id="course_selected" ref="course_selected">
                        {courses.map(({cid, course_title}) => {
                            return <option key={cid} value={cid}>{course_title}</option>
                        })}
                    </select>
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
