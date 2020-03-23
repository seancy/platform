import React from 'react';
import {Toolbar} from "./Toolbar";
import DataList from "se-react-data-list";
import {PaginationConfig, ReportType} from "./Config";
import BaseReport from './BaseReport'
import {pick} from "lodash";
import PropTypes from "prop-types";

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
        dataUrl:'/analytics/course/json/'
    }

    getConfig(){
        const propertiesFields = this.getOrderedProperties().map(p=>({
                name: p.text,
                fieldName: p.value
            }))
        const render=(val)=>{
            return <span className={val?'in-progress-bg':'not-started-bg'}>{val?'In Progress':'Not Started'}</span>
        }
        return {
            ...pick(this.state, ['isLoading', 'data', 'totalData']),
            keyField:"ID",
            fields: [
                {name: 'Name', fieldName: 'Name'},
                ...propertiesFields,

                {name: 'Status', fieldName: 'Status', render, className:'status'},
                {name: 'Progress', fieldName: 'Progress'},
                {name: 'Current Score', fieldName: 'Current Score'},
                {name: 'Badges', fieldName: 'Badges'},
                {name: 'Posts', fieldName: 'Posts'},
                {name: 'Total Time Spent', fieldName: 'Total Time Spent'},
                {name: 'Enrollment Date', fieldName: 'Enrollment Date'},
                {name: 'Completion Date', fieldName: 'Completion Date'},

            ],
            pagination: {
                pageSize: PaginationConfig.PageSize,
                rowsCount: this.state.rowsCount,
            }
        }
    }

    render() {
        const config = this.getConfig()
        return (
            <>
                <Toolbar onChange={this.toolbarDataUpdate.bind(this)}
                         onGo={this.startExport.bind(this)}
                         {...pick(this.props, ['onTabSwitch', 'defaultToolbarData', 'defaultActiveTabName'])}
                         onInit={properties=>this.setState({properties})}/>
                <DataList ref={this.myRef} className="data-list" defaultLanguage={this.props.defaultLanguage}
                          enableRowsCount={true} {...config} onPageChange={this.fetchData.bind(this)}
                />
            </>
        )
    }
}

CourseReportSummary.propTypes = {
    defaultLanguage: PropTypes.string,
    token: PropTypes.string,
    course_id: PropTypes.string,
    defaultToolbarData:PropTypes.object,
    onChange:PropTypes.func
}
