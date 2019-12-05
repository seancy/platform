/* eslint-disable react/no-danger, import/prefer-default-export */
import React from 'react';
import PropTypes from 'prop-types';

export class CustomizedReport extends React.Component {
    constructor(props) {
        super(props);

        this.state = {
            hideCourseReportSelect: false
        };
        $(() => {
            setTimeout(() => {
                $(this.refs.course_selected).select2({
                    multiple: true,
                    width:'off'
                });
            }, 300)

        })
    }

    recreateCourseSelect(e) {
        let courseReportType = this.props.report_types.find(p => p.type == e.target.value).courseReportType,
            isMultiple = true, $courseSelected = $(this.refs.course_selected);
        $courseSelected.data('select2') && $courseSelected.select2("destroy")
        if (courseReportType == 'multiple' || courseReportType == 'single') {
            isMultiple = courseReportType == 'single' ? false : true;
            $courseSelected.select2({
                width:'off',
                multiple: isMultiple
            });
            this.setState({
                hideCourseReportSelect:false
            })
        }else{
            this.setState({
                hideCourseReportSelect:true
            })
        }
    }

    render() {
        const {translation, report_types, courses} = this.props;

        return (
            <React.Fragment>
                <div>
                    <label htmlFor="report_type">{translation.report_type}</label>
                    <select name="report_type" id="report_type" onChange={this.recreateCourseSelect.bind(this)}>
                        {report_types.map(({type, title}) => {
                            return <option key={type} value={type}>{title}</option>
                        })}
                    </select>
                </div>
                <div className={'course-report ' + (this.state.hideCourseReportSelect?'hide':'')}>
                    <label htmlFor="course_selected">{translation.course}</label>
                    <select id="course_selected" ref="course_selected">
                        {courses.map(({cid, course_title}) => {
                            return <option key={cid} value={course_title}>{course_title}</option>
                        })}
                    </select>
                </div>
            </React.Fragment>
        )
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
