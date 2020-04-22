import 'select2'
import '../../../../node_modules/select2/dist/css/select2.css'

function initSelect() {
    $('.analytics-header form select').select2();
}

/* eslint-disable react/no-danger, import/prefer-default-export */
import React from 'react';
import Tab from "se-react-tab"
import Summary from './CourseReportSummary'
import Progress from './CourseReportProgress'
import TimeSpent from './CourseReportTimeSpent'

import { pick } from 'lodash'

class CourseReport extends React.Component {
    constructor(props) {
        super(props);
        initSelect()

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

        return (
            <Tab activeValue={(new URLSearchParams(location.search)).get('report')} data={data}>
                <div className="last-update">
                    <i className="fa fa-history"></i>{gettext("Please, note that these reports are not live. Last update:")} {this.props.last_update}
                </div>
            </Tab>
        )
    }
}

export { CourseReport }
