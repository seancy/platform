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

                {name: 'Geographical area', fieldName: 'Geographical area'},
                {name: 'Course country', fieldName: 'Course country'},
                {name: 'Zone/Region', fieldName: 'Zone/Region'},
                {name: 'Course tags', fieldName: 'Course tags'},

                {name: 'Course code', fieldName: 'Course code'},
                {name: 'Course name', fieldName: 'Course name'},
                {name: 'Section', fieldName: 'Section'},
                {name: 'Subsection', fieldName: 'Subsection'},

                {name: 'Session ID', fieldName: 'Session ID'},
                {name: 'Start date', fieldName: 'Start date'},
                {name: 'Start time', fieldName: 'Start time'},
                {name: 'End date', fieldName: 'End date'},

                {name: 'End time', fieldName: 'End time'},
                {name: 'Duration (in hours)', fieldName: 'Duration (in hours)'},
                {name: 'Location ID', fieldName: 'Location ID'},
                {name: 'Location name', fieldName: 'Location name'},

                {name: 'Location address', fieldName: 'Location address'},
                {name: 'Zip code', fieldName: 'Zip code'},
                {name: 'City', fieldName: 'City'},
                {name: 'Name', fieldName: 'Name'},

                ...propertiesFields,

                {name: 'Enrollment status', fieldName: 'Enrollment status'},
                {name: 'Attendee', fieldName: 'Attendee'},
                {name: 'Outward trips', fieldName: 'Outward trips'},
                {name: 'Return trips', fieldName: 'Return trips'},

                {name: 'Overnight stay', fieldName: 'Overnight stay'},
                {name: 'Overnight stay address', fieldName: 'Overnight stay address'},
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
