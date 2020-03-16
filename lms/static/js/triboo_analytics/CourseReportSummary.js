import React from 'react';
import {Toolbar} from "./Toolbar";
import DataList from "se-react-data-list";
import {PaginationConfig, ReportType} from "./Config";
import BaseReport from './BaseReport'

export default class CourseReportSummary extends BaseReport {
    constructor(props) {
        super(props);

        this.state = {
            ...this.state,
            properties:[],
        };
    }

    setting = {
        extraParams:{course_id: this.props.course_id},
        reportType:ReportType.COURSE_SUMMARY,
        dataUrl:'/analytics/course/summary/json/'
    }

    getConfig(){
        /*const properties=this.state.properties.filter(p=>p.type == 'default')
        const {selectedProperties}=this.state.toolbarData;*/
        const propertiesFields = this.getOrderedProperties().map(p=>({
                name: p.text,
                fieldName: p.value
            }))
        const render=(val)=>{
            return <span className={val?'in-progress-bg':'not-started-bg'}>{val?'In Progress':'Not Started'}</span>
        }
        return {
            fields: [
                {name: 'Name', fieldName: 'Name'},
                ...propertiesFields,

                {name: 'Status', fieldName: 'status', render, className:'status'},
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
            data: this.state.data,
            totalData: this.state.totalData
        }
    }

    render() {
        const config = this.getConfig()
        return (
            <>
                <Toolbar onChange={this.toolbarDataUpdate.bind(this)}
                         onGo={this.startExport.bind(this)}
                         onInit={properties=>this.setState({properties})}/>
                <DataList ref={this.myRef} className="data-list" defaultLanguage={this.props.defaultLanguage}
                          enableRowsCount={true} {...config} onPageChange={this.fetchData.bind(this)}
                />
            </>
        )
    }
}
