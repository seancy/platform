/* eslint-disable react/no-danger, import/prefer-default-export */
import React from 'react';
import {Toolbar} from './Toolbar'
import DataList from "se-react-data-list"
import {PaginationConfig, ReportType} from "./Config";
import BaseReport from './BaseReport'

export default class ILTGlobalReport extends BaseReport {
    constructor(props) {
        super(props);
        this.state = {
            ...this.state,
            properties:[],
        };
    }

    setting = {
        reportType:ReportType.ILT_GLOBAL,
        dataUrl:'/analytics/ilt/global/json/'
    }

    render() {
        const {data,totalData} = this.state
        const config = {
            fields: [
                {name: 'Name', fieldName: 'userName'},

                {name: 'Geographical area', fieldName: 'GeographicalArea'},
                {name: 'Course country', fieldName: 'CourseCountry'},
                {name: 'ZoneRegion', fieldName: 'Zone/Region'},
                {name: 'CourseTags', fieldName: 'Course tags'},

                {name: 'CourseCode', fieldName: 'Course code'},
                {name: 'Course', fieldName: 'Course'},
                {name: 'Section', fieldName: 'Section'},
                {name: 'Subsection', fieldName: 'Subsection'},

                {name: 'SessionID', fieldName: 'Session ID'},
                {name: 'StartDate', fieldName: 'Start date'},
                {name: 'StartTime', fieldName: 'Start time'},
                {name: 'EndDate', fieldName: 'End date'},

                {name: 'EndTime', fieldName: 'End time'},
                {name: 'Duration', fieldName: 'Duration (in hours)'},
                {name: 'MaxCapacity', fieldName: 'Max capacity'},
                {name: 'Enrollees', fieldName: 'Enrollees'},

                {name: 'Attendees', fieldName: 'Attendees'},
                {name: 'AttendanceSheet', fieldName: 'Attendance sheet'},
                {name: 'LocationID', fieldName: 'Location ID'},
                {name: 'LocationName', fieldName: 'Location name'},

                {name: 'Address', fieldName: 'Address'},
                {name: 'ZipCode', fieldName: 'Zip code'},
                {name: 'City', fieldName: 'City'},
            ],
            pagination: {
                pageSize: PaginationConfig.PageSize,
                rowsCount: this.state.rowsCount,
            },
            data, totalData
        }

        return (
            <>
                <Toolbar onChange={this.toolbarDataUpdate.bind(this)} enabledItems={['period','export']}
                    onExportTypeChange={this.startExport.bind(this)} onGo={this.startExport.bind(this)}
                     onInit={properties=>this.setState({properties})}/>
                 <DataList ref={this.myRef} className="data-list" defaultLanguage={this.props.defaultLanguage}
                          enableRowsCount={true} {...config} onPageChange={this.fetchData.bind(this)}
                />
            </>
        )
    }
}
