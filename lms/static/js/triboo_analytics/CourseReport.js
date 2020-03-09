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
        const [Summary0,Progress,TimeSpent] = functionStrs.map(p=>{
            return (props)=>{
                return (<div className={`${p.toLowerCase()}-component ${(props.className || '')}`}>
                    {p} component
                </div>)
            }
        })
        const data = [
            {text: 'Summary', value: 'summary', component: Summary, props:{filters:this.props.filters, defaultLanguage: this.props.defaultLanguage}},
            {text: 'Progress', value: 'progress', component: Progress},
            {text: 'Time Spent', value: 'time_spent', component: TimeSpent},
        ]

        return (
            <Tab onChange={console.log} data={data}/>
        )
    }
}



export { CourseReport }
