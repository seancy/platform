import React from "react";
import LabelValue from "lt-react-label-value";
import DateRange from "lt-react-date-range";
import Dropdown from 'lt-react-dropdown'
import {get} from 'lodash'


let version = 0

class ReportTypeAndCourseReport extends React.Component {
    constructor(props) {
        super(props);

        this.initState = {
          version: 0,
          reportType:get(props, ['report_types','0']) || {},
          reportTypeValue: get(props, ['report_types','0', 'value']) || '',
          selectedCourses:[],
          selectedCourseValues:[],
          selectedKeyValues:[],
          isMultiple:true,
          selectedEnrollments:0,
          limit:300000,
          hideCourseReportSelect: false,
          filterData:[{value: '', text: 'loading'}]
        }

        this.state = {...this.initState}

        window.reportTypeAndCourseReport = this
    }

    reset () {
      this.setState({
        ...this.initState,
        version: ++version,
      })
    }

    componentDidMount() {
        const nameList = [{text: gettext('Name'), value: 'user_name'}]
        fetch('/analytics/common/get_properties/json/')
            .then(response=>{
                return response.json()
            })
            .then(data=>{
                this.setState({filterData: [...nameList, ...data.list]})
            })
        this.changeLimitByFormat()
    }

    changeLimitByFormat() {
        this.getEnrollmentNumber()
        $('#table-export-selection').delegate('input', 'click', (e) => {
            let format_val = $('#table-export-selection input[name=format]:checked')[0].value;
            if (format_val == 'xls') {
                this.setState({'limit': 65000}, this.fireOnChange)
            } else {
                this.setState({'limit': 300000}, this.fireOnChange)
            }
        });
    }

    recreateCourseSelect(reportType) {
        let courseReportType = reportType.courseReportType,
            isMultiple = true;
        this.setState({reportType, reportTypeValue:reportType.value}, this.fireOnChange)
        if (courseReportType == 'multiple' || courseReportType == 'single') {
            isMultiple = courseReportType == 'single' ? false : true;
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

    fireOnChange() {
        const {onChange}=this.props
        const {reportTypeValue, selectedCourses, selectedKeyValues, startDate, endDate, selectedEnrollments, limit} = this.state
        onChange && onChange(reportTypeValue, selectedCourses, selectedKeyValues, startDate, endDate, selectedEnrollments, limit)
    }

    getReportTypeSection() {
        const {report_types} = this.props;
        const {reportTypeValue, reportType}=this.state;
        return (
          <div className="custom-section" id="report_type_section">
            <button className="section-button accordion-trigger"
                    aria-expanded="true"
                    aria-controls="report_section_contents"
                    id="report_section">
                <p className="section-title">{gettext("Select a report")}</p>
                <span className="fa fa-chevron-down fa-rotate-180" aria-hidden="true"></span>
            </button>
            <div id="report_section_contents" className="section-content">
                <div className="report-type">
                    <Dropdown sign='caret' data={report_types} value={get(report_types, ['0', 'value'])}
                              onChange={this.recreateCourseSelect.bind(this)} />
                    <input type="hidden" id='report_type' value={this.state.reportTypeValue}/>
                </div>
            </div>
            <div id="report_bar" className="reports label-bar is-collapsed is-hidden">
                {reportTypeValue && <button className="filter-option option-label">
                    <span className="query">{gettext(reportType.text)}</span>
                </button>}
            </div>
          </div>
        )
    }

    getEnrollmentNumber() {
        const {isMultiple, limit}=this.state;
        let selectedEnrollmentsNum = 0
        if (isMultiple) {
            selectedEnrollmentsNum = this.state.selectedCourses.reduce((prevVal, currVal)=>{
                return prevVal + currVal.course_enrollments;
            }, 0)
            if (selectedEnrollmentsNum > limit) {
                alert(gettext('With the selected courses, the report exceeds the maximum number of lines. Please unselect some courses.'))
            }
        } else {
            selectedEnrollmentsNum = this.state.selectedCourses.course_enrollments || '0'
        }
        this.state.selectedEnrollments = selectedEnrollmentsNum
        return selectedEnrollmentsNum
    }

    getCourseSection() {
        const {courses, courseSelectKey = 'key-select-course'} = this.props,
            {isMultiple, hideCourseReportSelect, selectedCourses, limit, selectedEnrollments}=this.state;
        const render=(text,item)=>{
            return `${text} (${item.course_enrollments || '0'})`
        }

        const handleCourseSelect = (selectedCourses)=>{
            this.setState({selectedCourses}, this.fireOnChange)
        }
        return <div className={`custom-section${hideCourseReportSelect?' hidden':''}`} id="custom_course_section">
            <button className="section-button accordion-trigger"
                    aria-expanded="false"
                    aria-controls="course_section_contents"
                    id="course_section">
                <p className="section-title">{gettext("Select course(s)")}</p>
                <span className="fa fa-chevron-down" aria-hidden="true"></span>
            </button>

            <div id="course_section_contents" className="section-content is-hidden">
                <div className={'course-report'}>
                    <p className={"section-label " + (this.state.hideCourseReportInfo ? 'hide' : '')}>
                        <p>{gettext('With the selected courses, the report will count * lines.')
                            .replace('*', this.getEnrollmentNumber())}</p>
                        <p>{gettext('The limit is 300,000 for CSV and JSON, 65,000 for XLS.')}</p>
                    </p>
                    <Dropdown key={courseSelectKey} data={courses} multiple={isMultiple} searchable={true} optionRender={render} onChange={handleCourseSelect}/>
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

    getFilterSection() {
        const {selectedKeyValues,startDate, endDate}=this.state
        const stopEvent = e => {
            e.stopPropagation();
            e.preventDefault();
            return false
        }
        return <div className="custom-section" id="filter-section">
            <button className="section-button accordion-trigger"
                    aria-expanded="false"
                    aria-controls="filter_section_contents"
                    id="filter_section">
                <p className="section-title">{gettext("Filter the data")}</p>
                <span className="fa fa-chevron-down" aria-hidden="true"></span>
            </button>
            <div id="filter_section_contents" className="section-content is-hidden">
                <section className="filter-form">
                    <div id="filter-form">
                        <div className="table-filter-form">
                            <LabelValue data={this.state.filterData} onChange={this.filterOnChange.bind(this)}
                                        placeholder={gettext('Press enter to add')} useFontAwesome={true} stopEventSpread={true}/>
                        </div>
                    </div>
                </section>
                <section className="period-form">
                    <p className="section-label">{gettext("Select a time range")+':'}</p>
                    <div id="period-table">
                        <DateRange onChange={this.periodOnChange.bind(this)}
                            //label='Select a time range'
                                   buttonText={gettext('Last * days')} useFontAwesome={true}
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
            <React.Fragment key={this.state.version}>
                {this.getReportTypeSection()}
                {this.getCourseSection()}
                {this.getFilterSection()}
            </React.Fragment>
        )
    }
}

export default ReportTypeAndCourseReport
