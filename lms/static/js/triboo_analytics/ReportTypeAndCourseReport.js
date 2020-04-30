import React from "react";
import LabelValue from "sec-react-label-value";
import DateRange from "se-react-date-range";
import Dropdown from 'se-react-dropdown'
import {get} from 'lodash'

class ReportTypeAndCourseReport extends React.Component {
    constructor(props) {
        super(props);

        this.state = {
            reportType:get(props, ['report_types','0']) || {},
            reportTypeValue: get(props, ['report_types','0', 'value']) || '',
            selectedCourses:[],
            selectedCourseValues:[],
            selectedKeyValues:[],
            isMultiple:true,

            hideCourseReportSelect: false,
            filterData:[{value: '', text: 'loading'}]
        };

        //$(this.refs.report_type).select2().on('select2:select', this.recreateCourseSelect.bind(this));
        setTimeout(() => {
            $(this.refs.course_selected).select2({
                multiple: true,
                width: 'off',
                placeholder: "Course Name",
            });
        }, 300)
    }

    componentDidMount() {
        const nameList = [{text: 'Name', value: 'user_name'}]
        fetch('/analytics/common/get_properties/json/')
            .then(response=>{
                return response.json()
            })
            .then(data=>{
                this.setState({filterData: [...nameList, ...data.list]})
            })
    }

    recreateCourseSelect(reportType) {
        let courseReportType = reportType.courseReportType,
            isMultiple = true, $courseSelected = $(this.refs.course_selected);
        $courseSelected.data('select2') && $courseSelected.select2("destroy")
        this.setState({reportType, reportTypeValue:reportType.value}, this.fireOnChange)
        if (courseReportType == 'multiple' || courseReportType == 'single') {
            isMultiple = courseReportType == 'single' ? false : true;
            /*$courseSelected.select2({
                width: 'off',
                multiple: isMultiple,
                placeholder: "Course Name",
            });*/
            this.setState({
                isMultiple,
                selectedCourses:[],
                hideCourseReportSelect: false
            }, this.fireOnChange)

            if (courseReportType == 'single') {
                this.setState({
                    hideCourseReportInfo: true
                })
            } else {
                this.setState({
                    hideCourseReportInfo: false
                })
            }
        } else {
            this.setState({
                hideCourseReportSelect: true
            })
        }
    }

    filterOnChange(selectedKeyValues) {
        this.setState({selectedKeyValues}, this.fireOnChange)
    }

    periodOnChange(startDate, endDate) {
        this.setState({startDate, endDate}, this.fireOnChange)
    }

    fireOnChange(){
        const {onChange}=this.props
        const {reportTypeValue, selectedCourses, selectedKeyValues, startDate, endDate} = this.state
        onChange && onChange(reportTypeValue, selectedCourses, selectedKeyValues, startDate, endDate)
    }

    getReportTypeSection(){
        const {report_types} = this.props;
        const {reportTypeValue, reportType}=this.state;
        return <div className="custom-section" id="report_type_section">
            <button className="section-button accordion-trigger"
                    aria-expanded="${ 'false' }"
                    aria-controls="report_section_contents"
                    id="report_section">
                <p className="section-title">Select a report</p>
                <span className="fa fa-chevron-down" aria-hidden="true"></span>
            </button>
            <div id="report_section_contents" className="section-content">
                <div className="report-type">
                    <Dropdown sign='caret' data={report_types} value={get(report_types, ['0', 'value'])}
                              onChange={this.recreateCourseSelect.bind(this)} />
                    <input type="hidden" id='report_type' value={this.state.reportTypeValue}/>

                    {/*<select name="report_type" id="report_type" ref="report_type"
                    onChange={this.recreateCourseSelect.bind(this)}>
                        {report_types.map(({type, title}) => {
                            return <option key={type} value={type}>{title}</option>
                        })}
                    </select>*/}
                </div>
            </div>
            <div id="report_bar" className="reports label-bar is-collapsed">
                {reportTypeValue && <button className="filter-option option-label">
                    <span className="query">{reportType.text}</span>
                </button>}
            </div>
        </div>
    }
    //<!--is-hidden-->

    getCourseSection(){
        //(this.state.hideCourseReportSelect ? 'hide' : '')
        const {courses} = this.props, {isMultiple, hideCourseReportSelect, selectedCourses}=this.state;
        const render=(text,item)=>{
            return `${text} (${item.course_enrollments || '0'} users)`
        }
        const getEnrollmentNumber=()=>{
            return isMultiple ? this.state.selectedCourses.reduce((prevVal, currVal)=>{
                return prevVal + currVal.course_enrollments;
            }, 0) : (this.state.selectedCourses.course_enrollments || '0')
        }
        const handleCourseSelect = (selectedCourses)=>{
            this.setState({selectedCourses}, this.fireOnChange)
        }
        return <div className={`custom-section${hideCourseReportSelect?' hidden':''}`} id="custom_course_section">
            <button className="section-button accordion-trigger"
                    aria-expanded="${ 'false' }"
                    aria-controls="course_section_contents"
                    id="course_section">
                <p className="section-title">Select course(s)</p>
                <span className="fa fa-chevron-down" aria-hidden="true"></span>
            </button>

            <div id="course_section_contents" className="section-content is-hidden">
                <div className={'course-report'}>
                    <p className={"section-label " + (this.state.hideCourseReportInfo ? 'hide' : '')}>
                        The enrollments of the courses you have been selected is:
                        <span id="enrollment_selected">{getEnrollmentNumber()}</span>
                        . (<span id="enrollment_limit">{this.props.limit || 300000}</span> at most)
                    </p>
                    <Dropdown data={courses} multiple={isMultiple} optionRender={render} onChange={handleCourseSelect}/>
                    {/*<select id="course_selected" ref="course_selected">
                        {courses.map(({cid, course_title, course_enrollments}) => {
                            return <option key={cid} value={cid}>{course_title} ({course_enrollments} users)</option>
                        })}
                    </select>*/}
                </div>
            </div>
            <div id="course_bar" className="courses label-bar is-collapsed">
                {isMultiple && selectedCourses.map(({key, value, text})=>(<button className="filter-option option-label" >
                    <span className="query">{`${text}`}</span>
                </button>))}
                {!isMultiple && selectedCourses.text && <button className="filter-option option-label" >
                    <span className="query">{`${selectedCourses.text}`}</span>
                </button>}

            </div>
        </div>
    }
    getFilterSection(){
        const {selectedKeyValues,startDate, endDate}=this.state
        const stopEvent = e => {
            e.stopPropagation();
            e.preventDefault();
            return false
        }
        return <div className="custom-section" id="filter-section">
            <button className="section-button accordion-trigger"
                    aria-expanded="${ 'false' }"
                    aria-controls="filter_section_contents"
                    id="filter_section">
                <p className="section-title">Filter the data</p>
                <span className="fa fa-chevron-down" aria-hidden="true"></span>
            </button>
            <div id="filter_section_contents" className="section-content is-hidden">
                <section className="filter-form">
                    <div id="filter-form">
                        <div className="table-filter-form">
                            <LabelValue data={this.state.filterData} onChange={this.filterOnChange.bind(this)}
                                        stopEventSpread={true}/>
                        </div>
                    </div>
                </section>
                <section className="period-form">
                    <p className="section-label">Select a time range:</p>
                    <div id="period-table">
                        <DateRange onChange={this.periodOnChange.bind(this)}
                            //label='Select a time range'
                                   buttonBegin='Last '
                                   startDateName='from_day' endDateName='to_day'/>
                    </div>
                </section>
            </div>
            <div id="filter-bar2" className="filters label-bar is-collapsed">
                {selectedKeyValues.map(({key, value, text})=>(<button className="filter-option option-label" onClick={stopEvent}>
                    <span className="query">{`${text}:${value}`}</span>
                </button>))}
                {startDate && <button className="filter-option option-label start-date" onClick={stopEvent}>
                    <span className="query">{startDate}</span>
                </button>}
                {(startDate && endDate) ? <span>-</span> :''}
                {endDate && <button className="filter-option option-label end-date" onClick={stopEvent}>
                    <span className="query">{endDate}</span>
                </button>}
            </div>
        </div>
    }

    render() {
        const { } = this.props;
        return (
            <React.Fragment>
                {this.getReportTypeSection()}
                {this.getCourseSection()}
                {this.getFilterSection()}
            </React.Fragment>
        )
    }
}

export default ReportTypeAndCourseReport
