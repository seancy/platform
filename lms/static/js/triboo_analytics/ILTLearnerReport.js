/* eslint-disable react/no-danger, import/prefer-default-export */
import React from 'react';
import {Toolbar} from './Toolbar'
import DataList from "se-react-data-list"
import {PaginationConfig, ReportType} from "./Config";
import BaseReport from './BaseReport'

export default class ILTLearnerReport extends BaseReport {
    constructor(props) {
        super(props);
        this.state = {
            ...this.state,
            properties:[],
        };
    }

    setting = {
        reportType:ReportType.ILT_LEARNER,
        dataUrl:'/analytics/ilt/json/'
    }

    getConfig(){
        /*const properties=this.state.properties.filter(p=>p.type == 'default')
        const {selectedProperties}=this.state.toolbarData;*/
        const propertiesFields = this.getOrderedProperties().map(p=>({
                name: p.text,
                fieldName: p.value
            }))
        return {
            fields: [

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
                {name: 'LocationID', fieldName: 'Location ID'},
                {name: 'LocationName', fieldName: 'Location name'},

                {name: 'Address', fieldName: 'Address'},
                {name: 'ZipCode', fieldName: 'Zip code'},
                {name: 'City', fieldName: 'City'},
                {name: 'Name', fieldName: 'Name'},

                ...propertiesFields,

                {name: 'EnrollmentStatus', fieldName: 'Enrollment status'},
                {name: 'Attendee', fieldName: 'Attendee'},
                {name: 'OutwardTrips', fieldName: 'Outward trips'},
                {name: 'ReturnTrips', fieldName: 'Return trips'},

                {name: 'OvernightStay', fieldName: 'Overnight stay'},
                {name: 'OvernightStayAddress', fieldName: 'Overnight stay address'},
                {name: 'Comment', fieldName: 'Comment'}
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
