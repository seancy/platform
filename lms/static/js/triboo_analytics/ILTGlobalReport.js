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
                {name: 'Geographical area', fieldName: 'Geographical area'},
                {name: 'Course country', fieldName: 'Course country'},
                {name: 'Zone/Region', fieldName: 'Zone/Regionn'},
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
                {name: 'Max capacity', fieldName: 'Max capacity'},
                {name: 'Enrollees', fieldName: 'Enrollees'},

                {name: 'Attendees', fieldName: 'Attendees'},
                {name: 'Attendance sheet', fieldName: 'Attendance sheet'},
                {name: 'Location ID', fieldName: 'Location ID'},
                {name: 'Location name', fieldName: 'Location name'},

                {name: 'Location address', fieldName: 'Location address'},
                {name: 'Zip code', fieldName: 'Zip code'},
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
                     onInit={properties=>this.setState({properties})}
                     periodTooltip={gettext('Filter the sessions starting in the selected period.')}/>
                 {this.props.children}
                 <DataList useFontAwesome={true} ref={this.myRef} className="data-list" defaultLanguage={this.props.defaultLanguage}
                          enableRowsCount={true} {...config}
                />
            </>
        )
    }
}
