/* eslint-disable react/no-danger, import/prefer-default-export */
import React from 'react';
import {Toolbar} from './Toolbar'
import DataList from "se-react-data-list"
import {PaginationConfig, ReportType} from "./Config";
import BaseReport from './BaseReport'
import {pick} from "lodash";

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
        dataUrl:'/analytics/ilt/json/'
    }

    render() {
        const {data,totalData} = this.state
        const config = {
            ...pick(this.state, ['isLoading']),
            fields: [
                {name: 'Name', fieldName: 'userName'},

                {name: 'Geographical area', fieldName: 'GeographicalArea'},
                {name: 'Course country', fieldName: 'CourseCountry'},
                {name: 'Zone/Region', fieldName: 'ZoneRegion'},
                {name: 'Course tags', fieldName: 'CourseTags'},

                {name: 'Course code', fieldName: 'CourseCode'},
                {name: 'Course', fieldName: 'Course'},
                {name: 'Section', fieldName: 'Section'},
                {name: 'Subsection', fieldName: 'Subsection'},

                {name: 'Session ID', fieldName: 'SessionID'},
                {name: 'Start date', fieldName: 'StartDate'},
                {name: 'Start time', fieldName: 'StartTime'},
                {name: 'End date', fieldName: 'EndDate'},

                {name: 'End time', fieldName: 'EndTime'},
                {name: 'Duration (in hours)', fieldName: 'Duration'},
                {name: 'Max capacity', fieldName: 'MaxCapacity'},
                {name: 'Enrollees', fieldName: 'Enrollees'},

                {name: 'Attendees', fieldName: 'Attendees'},
                {name: 'Attendance sheet', fieldName: 'AttendanceSheet'},
                {name: 'Location ID', fieldName: 'LocationID'},
                {name: 'Location name', fieldName: 'LocationName'},

                {name: 'Address', fieldName: 'Address'},
                {name: 'Zip code', fieldName: 'ZipCode'},
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
                    onGo={this.startExport.bind(this)}
                     onInit={properties=>this.setState({properties})}/>
                 <DataList ref={this.myRef} className="data-list" defaultLanguage={this.props.defaultLanguage}
                          enableRowsCount={true} {...config} onPageChange={this.fetchData.bind(this)}
                />
            </>
        )
    }
}
