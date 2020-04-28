import React from "react";
import LabelValue from "sec-react-label-value";
import DateRange from "se-react-date-range";

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
        this.setState({selectedKeyValues}, this.fireOnChange)
    }

    periodOnChange(e, f) {
        console.log('e', e, f)
    }

    fireOnChange(){
        const {onChange}=this.props
        const {selectedKeyValues} = this.state
        onChange && onChange('', '', selectedKeyValues)
    }

    stopCollapse(e){
        if (e.key == 'Enter'){
            e.preventDefault();
            e.stopPropagation()
            return false
        }

    }
    render() {
        const {report_types, courses} = this.props;

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
                                <input type="text" className="test3" onKeyDown={this.stopCollapse.bind(this)}/>
                                <LabelValue data={this.state.filterData} onChange={this.filterOnChange.bind(this)} stopEventSpread={true} />
                            </div>
                          </div>
                        </section>
                        <section class="period-form">
                            <p class="section-label">Select a time range:</p>
                            <div id="period-table">
                                <DateRange onChange={this.periodOnChange.bind(this)}
                                           //label='Select a time range'
                                           buttonBegin='Last '
                                    startDateName='from_day' endDateName='to_day'/>
                            </div>
                        </section>
                    </div>
                    <div id="filter-bar" class="filters is-collapsed"></div>
                </div>
            </React.Fragment>
        )
    }
}

export default ReportTypeAndCourseReport
