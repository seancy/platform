/* eslint-disable react/no-danger, import/prefer-default-export */
import React from 'react';
import {Toolbar} from './Toolbar'
import DataList from "se-react-data-list"
import {PaginationConfig, ReportType} from "./Config";
import BaseReport from './BaseReport'
import {pick} from 'lodash'

export class LearnerReport extends BaseReport {
    constructor(props) {
        super(props);

        this.state = {
            ...this.state,
            properties:[],
        };
    }

    setting = {
        reportType:ReportType.LEARNER,
        dataUrl:'/analytics/learner/json/'
    }

    getConfig() {
        const propertiesFields = this.getOrderedProperties()
        return {...{
            fields: [
                {name: gettext('Name'), fieldName: 'Name', render:(value)=>{
                    return <div dangerouslySetInnerHTML={{__html: value}} />
                }},
                ...propertiesFields,

                {name: gettext('Enrollments'), fieldName: 'Enrollments'},
                {name: gettext('Successful'), fieldName: 'Successful'},
                {name: gettext('Unsuccessful'), fieldName: 'Unsuccessful'},
                {name: gettext('In Progress'), fieldName: 'In Progress'},
                {name: gettext('Not Started'), fieldName: 'Not Started'},
                {name: gettext('Average Final Score'), fieldName: 'Average Final Score'},
                {name: gettext('Badges'), fieldName: 'Badges'},
                {name: gettext('Posts'), fieldName: 'Posts'},
                {name: gettext('Total Time Spent'), fieldName: 'Total Time Spent'},
                {name: gettext('Last Login'), fieldName: 'Last Login'}
            ],
        }, ...this.getBaseConfig()}
    }

    render() {
        const config = this.getConfig()
        return (
            <section className="analytics-wrapper learner">
                <div className="report-wrapper">
                    <Toolbar
                        onChange={this.toolbarDataUpdate.bind(this)}
                             onGo={this.startExport.bind(this)}
                             onInit={properties=>this.setState({properties})}
                             periodTooltip={gettext('Display the state of learners at the end of the selected period '
                                                 + 'for learners who visited the platform during this period. '
                                                 + 'The total time spent shows the time learners spent on the platform '
                                                 + 'during the selected period.')}>
                        <h3>{gettext('Learner Report')}</h3>
                    </Toolbar>
                    <p className="last-update">
                        <span className="fal fa-sync-alt"></span>{gettext('Please, note that these reports are not live. Last update:')} {this.props.last_update}
                    </p>
                    <DataList useFontAwesome={true} ref={this.myRef} className="data-list" defaultLanguage={this.props.defaultLanguage}
                              enableRowsCount={true} {...config}
                    />
                </div>
            </section>
        )
    }
}
