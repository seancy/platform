import 'select2'
import '../../../../node_modules/select2/dist/css/select2.css'

/* eslint-disable react/no-danger, import/prefer-default-export */
import React from 'react';
import Tab from "se-react-tab"
import Summary from './CourseReportSummary'
import Progress from './CourseReportProgress'
import TimeSpent from './CourseReportTimeSpent'
import Dropdown from 'se-react-dropdown'

import { pick } from 'lodash'

class CourseReport extends React.Component {
    constructor(props) {
        super(props);

        this.state = {
            activeTabName:'',
            toolbarData:{}
        }
    }

    render() {
        const urlParams = new URLSearchParams(location.search)
        const course_id = urlParams.get('course_id')
        //const token = urlParams.get('csrfmiddlewaretoken')  please keep it.
        const common_props = {...pick(this.props, 'defaultLanguage', 'token'), ...{
            course_id,
            defaultToolbarData:this.state.toolbarData,
            defaultActiveTabName:this.state.activeTabName,
            onTabSwitch:activeTabName=>{
                this.setState({activeTabName})
            },
            onChange:toolbarData=>this.setState({ toolbarData })
        }}
        const data = [
            {text: gettext('Summary'), value: 'summary', component: Summary, props:common_props},
            {text: gettext('Progress'), value: 'progress', component: Progress, props:common_props},
            {text: gettext('Time Spent'), value: 'time_spent', component: TimeSpent, props:common_props},
        ]
        const {last_update}=this.props
        return (last_update &&
            <Tab activeValue={(new URLSearchParams(location.search)).get('report')} data={data}>
                <div className="last-update">
                    <span className="fal fa-sync-alt"></span>{gettext("Please, note that these reports are not live. Last update:")} {last_update}
                </div>
            </Tab>
        )
    }
}


class CourseReportDropdown extends React.Component {
    constructor(props) {
        super(props);

        const {data}=this.props
        this.state = {
            selectedCourse:data?data[0] || '': '',
        }
    }

    fireOnChange(){

    }

    go(){

        const {url,token}=this.props
        const courseID = this.state.selectedCourse.value
        window.location = `${url}?course_id=${encodeURIComponent(courseID)}&csrfmiddlewaretoken=${token}`
        console.log(this.state.selectedCourse)
    }

    render() {
        const {data,labelText,submitText}=this.props
        return (<>
            <label htmlFor="course_id">{labelText}</label>
            <Dropdown data={data} searchable={true}
                      onChange={selectedCourse=>this.setState({selectedCourse}, this.fireOnChange)}/>
            <input type="button" value={submitText} onClick={this.go.bind(this)}/>
        </>)
    }
}

export { CourseReport,CourseReportDropdown }
