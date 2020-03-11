import 'select2'
import '../../../../node_modules/select2/dist/css/select2.css'

/*class CourseReportTemp {
    constructor(){
        $('.analytics-header form select').select2();
    }
}*/

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
        this.state = {
            data: [],

        };
        //this.myRef = React.createRef()

        initSelect()
    }


    render() {
        const {} = this.state
        const functionStrs = ['Summary', 'Progress', 'Time Spent']
        const [Summary0,Progress0,TimeSpent0] = functionStrs.map(p=>{
            return (props)=>{
                return (<div className={`${p.toLowerCase()}-component ${(props.className || '')}`}>
                    {p} component
                </div>)
            }
        })
        const common_props = pick(this.props, 'defaultLanguage', 'token')
        const data = [
            {text: 'Summary', value: 'summary', component: Summary, props:common_props},
            {text: 'Progress', value: 'progress', component: Progress, props:common_props},
            {text: 'Time Spent', value: 'time_spent', component: TimeSpent, props:common_props},
        ]

        return (
            <Tab onChange={console.log} data={data}/>
        )
    }
}



export { CourseReport }
