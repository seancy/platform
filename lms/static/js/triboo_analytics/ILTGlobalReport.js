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

    getConfig(){
        return {...{
            fields: [
                {name: 'Name', fieldName: 'userName'},

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

                {name: 'End time', fieldName: 'End Time'},
                {name: 'Duration (in hours)', fieldName: 'Duration'},
                {name: 'Max capacity', fieldName: 'Max Capacity'},
                {name: 'Enrollees', fieldName: 'Enrollees'},

                {name: 'Attendees', fieldName: 'Attendees'},
                {name: 'Attendance sheet', fieldName: 'Attendance Sheet'},
                {name: 'Location ID', fieldName: 'Location ID'},
                {name: 'Location name', fieldName: 'Location Name'},

                {name: 'Address', fieldName: 'Address'},
                {name: 'Zip code', fieldName: 'Zip Code'},
                {name: 'City', fieldName: 'City'},
            ],
        }, ...this.getBaseConfig()}
    }

    render() {
        const config = this.getConfig()
        return (
            <>
                <Toolbar onChange={this.toolbarDataUpdate.bind(this)} enabledItems={['period','export']}
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
