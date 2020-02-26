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
import {Toolbar} from './Toolbar'
import DataList from "se-react-data-list"
import Tab from "se-react-tab"

import PaginationConfig from './PaginationConfig'

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
            {text: 'Summary', value: 'summary', component: Summary},
            {text: 'Progress', value: 'progress', component: Progress},
            {text: 'Time Spent', value: 'time_spent', component: TimeSpent},
        ]

        return (
            <Tab onChange={console.log} data={data}/>
        )
    }
}

{/*
<>
        <ul className="analytics-nav">
            <li className="nav-item summary active">Summary</li>
            <li className="nav-item progress">Progress</li>
            <li className="nav-item time_spent">Time Spent</li>
        </ul>
        <div className="analytics-nav-content">
            test info2...
        </div>

        <Toolbar onChange={this.toolbarDataUpdate.bind(this)} filters={this.props.filters}
            enabledItems={['period','export']} properties={this.props.filters}/>
         <DataList ref={this.myRef} className="data-list" defaultLanguage={this.props.defaultLanguage}
                  enableRowsCount={true} {...parameterObj} onPageChange={this.fetchData.bind(this)}
        />
    </>
*/}

class Summary extends React.Component {
    constructor(props) {
        super(props);
        this.state = {
            //storing toolbar data
            toolbarData: {},

            //ajax result
            data: [],
            totalData: {},
            rowsCount: 0,
        };
        this.myRef = React.createRef()

        initSelect();
    }

    componentDidMount() {
        this.fetchData(1)
    }

    toolbarDataUpdate(toolbarData){
        this.setState(s=>{
            return {
                toolbarData
            }
        },()=>{
            this.fetchData(1)
            this.myRef.current.resetPage(1)
        })
    }

    fetchData(pageNo) {
        const url = `/static/data.json`
        const {toolbarData} = this.state
        const getVal=(key,defaultValue)=>{
            return toolbarData && toolbarData[key]?toolbarData[key]: defaultValue || '';
        }
        let ajaxData = {
            'report_type': 'learner_report',
            'courses_selected': [''],
            'from_day': getVal('startDate'),
            'to_day': getVal('endDate'),
            'format': getVal('exportType'),
            'csrfmiddlewaretoken': 'nDou5pR169v76UwtX4XOpbQsSTLu6SexeWyd0ykjGR2ahYMV0OY7nddkYQqnT6ze',
            'page': {
                no: pageNo, size: PaginationConfig.PageSize
            },
        }

        $.ajax(url, {
            method: 'get', //please change it to post in real environment.
            dataType: 'json',
            data: ajaxData,
            success: (json) => {
                this.setState((s, p) => {
                    return {
                        data: json.list,
                        totalData: json.total, //{email: 'total:', first_name: json.total},
                        rowsCount: json.pagination.rowsCount
                    }
                })
            }
        })
    }

    render() {
        const {data,totalData} = this.state
        //Name	Email	Country	Commercial Zone	Commercial Region	City	Location
        // Employee ID	Status	Progress	Current Score	Badges
        // Total Time Spent	Enrollment Date	Completion Date
        const render=(val)=>{
            return <span className={val?'in-progress-bg':''}>In Progress</span>
            //val ? () :

            /*
            <span className="not-started-bg" >Not Started</span>*/
        }
        const parameterObj = {
            fields: [
                {name: 'Name', fieldName: 'userName'},
                {name: 'Email', fieldName: 'email'},
                {name: 'Commercial Zone', fieldName: 'commercialZone'},
                {name: 'City', fieldName: 'city'},
                {name: 'Location', fieldName: 'location'},
                {name: 'Employee ID', fieldName: 'employeeID'},
                {name: 'Status', fieldName: 'status', render},
                {name: 'Progress', fieldName: 'progress'},
                {name: 'Current Score', fieldName: 'currentScore'},
                {name: 'Badges', fieldName: 'badges'},
                {name: 'Posts', fieldName: 'posts'},
                {name: 'Total Time Spent', fieldName: 'totalTimeSpent'},
                {name: 'Enrollment Date', fieldName: 'enrollmentDate'},
                {name: 'Completion Date', fieldName: 'completionDate'},
            ],
            pagination: {
                pageSize: PaginationConfig.PageSize,
                rowsCount: this.state.rowsCount,
            },
            data, totalData
        }

        return (
            <>
                <Toolbar onChange={this.toolbarDataUpdate.bind(this)} filters={this.props.filters}
                    enabledItems={['filters','period', 'properties','export']} properties={this.props.filters}/>
                 <DataList ref={this.myRef} className="data-list" defaultLanguage={this.props.defaultLanguage}
                          enableRowsCount={true} {...parameterObj} onPageChange={this.fetchData.bind(this)}
                />
            </>
        )
    }
}

export { CourseReport }
