/* eslint-disable react/no-danger, import/prefer-default-export */
import React from 'react';
import {Toolbar} from './Toolbar'
import DataList from "se-react-data-list"
import {PaginationConfig, ReportType} from "./Config";
import BaseReport from './BaseReport'
import {pick} from "lodash";

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
        const propertiesFields = this.getOrderedProperties().map(p=>({
                name: p.text,
                fieldName: p.value
            }))
        return {...{
            fields: [

                {name: 'Geographical area', fieldName: 'Geographical Area'},
                {name: 'Course country', fieldName: 'Course Country'},
                {name: 'Zone/Region', fieldName: 'Zone Region'},
                {name: 'Course tags', fieldName: 'Course Tags'},

                {name: 'Course code', fieldName: 'Course Code'},
                {name: 'Course', fieldName: 'Course'},
                {name: 'Section', fieldName: 'Section'},
                {name: 'Subsection', fieldName: 'Subsection'},

                {name: 'Session ID', fieldName: 'Session ID'},
                {name: 'Start date', fieldName: 'Start Date'},
                {name: 'Start time', fieldName: 'Start Time'},
                {name: 'End date', fieldName: 'End Date'},

                {name: 'End time', fieldName: 'EndTime'},
                {name: 'Duration (in hours)', fieldName: 'Duration'},
                {name: 'Location ID', fieldName: 'Location ID'},
                {name: 'Location name', fieldName: 'Location Name'},

                {name: 'Address', fieldName: 'Address'},
                {name: 'Zip code', fieldName: 'Zip Code'},
                {name: 'City', fieldName: 'City'},
                {name: 'Name', fieldName: 'Name'},

                ...propertiesFields,

                {name: 'Enrollment status', fieldName: 'Enrollment Status'},
                {name: 'Attendee', fieldName: 'Attendee'},
                {name: 'Outward trips', fieldName: 'Outward Trips'},
                {name: 'Return trips', fieldName: 'Return Trips'},

                {name: 'Overnight stay', fieldName: 'Overnight Stay'},
                {name: 'Overnight stay address', fieldName: 'Overnight Stay Address'},
                {name: 'Comment', fieldName: 'Comment'}
            ],
        }, ...this.getBaseConfig()}
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
                          enableRowsCount={true} {...config}
                />
            </>
        )
    }
}
