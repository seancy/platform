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
        dataUrl:'/analytics/ilt/learner/json/'
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
                {name: 'Location ID', fieldName: 'LocationID'},
                {name: 'Location name', fieldName: 'LocationName'},

                {name: 'Address', fieldName: 'Address'},
                {name: 'Zip code', fieldName: 'ZipCode'},
                {name: 'City', fieldName: 'City'},
                {name: 'Name', fieldName: 'Name'},

                ...propertiesFields,

                {name: 'Enrollment status', fieldName: 'EnrollmentStatus'},
                {name: 'Attendee', fieldName: 'Attendee'},
                {name: 'Outward trips', fieldName: 'OutwardTrips'},
                {name: 'Return trips', fieldName: 'ReturnTrips'},

                {name: 'Overnight stay', fieldName: 'OvernightStay'},
                {name: 'Overnight stay address', fieldName: 'OvernightStayAddress'},
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
