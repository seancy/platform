/* eslint-disable react/no-danger, import/prefer-default-export */
import React from 'react';
import {Toolbar} from './Toolbar'
import DataList from "lt-react-data-list"
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

    getConfig() {
        const propertiesFields = this.getOrderedProperties()
        const translationRender={
            render:v=>gettext(v)
        }
        return {...{
            fields: [

                {name: gettext('Geographical area'), fieldName: 'Geographical area', ...translationRender},
                {name: gettext('Course country'), fieldName: 'Course country', ...translationRender},
                {name: gettext('Zone/Region'), fieldName: 'Zone/Region', ...translationRender},
                {name: gettext('Course tags'), fieldName: 'Course tags'},

                {name: gettext('Course code'), fieldName: 'Course code'},
                {name: gettext('Course name'), fieldName: 'Course name'},
                {name: gettext('Section'), fieldName: 'Section'},
                {name: gettext('Subsection'), fieldName: 'Subsection'},

                {name: gettext('Session ID'), fieldName: 'Session ID'},
                {name: gettext('Start date'), fieldName: 'Start date'},
                {name: gettext('Start time'), fieldName: 'Start time'},
                {name: gettext('End date'), fieldName: 'End date'},

                {name: gettext('End time'), fieldName: 'End time'},
                {name: gettext('Duration (in hours)'), fieldName: 'Duration (in hours)'},
                {name: gettext('Location ID'), fieldName: 'Location ID'},
                {name: gettext('Location name'), fieldName: 'Location name'},

                {name: gettext('Location address'), fieldName: 'Location address'},
                {name: gettext('Zip code'), fieldName: 'Zip code'},
                {name: gettext('City'), fieldName: 'City'},
                {name: gettext('Name'), fieldName: 'Name'},

                ...propertiesFields,

                {name: gettext('Enrollment status'), fieldName: 'Enrollment status', ...translationRender},
                {name: gettext('Attendees'), fieldName: 'Attendee', ...translationRender},
                {name: gettext('Outward trips'), fieldName: 'Outward trips'},
                {name: gettext('Return trips'), fieldName: 'Return trips'},

                {name: gettext('Overnight stay'), fieldName: 'Overnight stay', ...translationRender},
                {name: gettext('Overnight stay address'), fieldName: 'Overnight stay address'},
                {name: gettext('Comment'), fieldName: 'Comment'}
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
