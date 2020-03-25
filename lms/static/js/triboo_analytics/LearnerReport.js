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

    getConfig(){
        /*const properties=this.state.properties.filter(p=>p.type == 'default')
        const {selectedProperties}=this.state.toolbarData;*/
        const propertiesFields = this.getOrderedProperties().map(p=>({
                name: p.text,
                fieldName: p.value
            }))

        return {...{
            fields: [
                {name: 'Name', fieldName: 'Name'},
                ...propertiesFields,

                {name: 'Enrollments', fieldName: 'Enrollments'},
                {name: 'Successful', fieldName: 'Successful'},
                {name: 'Unsuccessful', fieldName: 'Unsuccessful'},
                {name: 'In Progress', fieldName: 'In Progress'},
                {name: 'Not Started', fieldName: 'Not Started'},
                {name: 'Average Final Score', fieldName: 'Average Final Score'},
                {name: 'Badges', fieldName: 'Badges'},
                {name: 'Posts', fieldName: 'Posts'},
                {name: 'Total Time Spent', fieldName: 'Total Time Spent'},
                {name: 'Last Login', fieldName: 'Last Login'}
            ],
        }, ...this.getBaseConfig()}
    }

    render() {
        const config = this.getConfig()
        return (
            <section className="analytics-wrapper learner">
                <div className="report-wrapper">
                    <div className="last-update">
                        <i className="fa fa-history"></i>{gettext('Please, note that these reports are not live. Last update:')}{this.props.last_update}
                    </div>
                    <Toolbar onChange={this.toolbarDataUpdate.bind(this)}
                             onGo={this.startExport.bind(this)}
                             onInit={properties=>this.setState({properties})}/>
                    <DataList ref={this.myRef} className="data-list" defaultLanguage={this.props.defaultLanguage}
                              enableRowsCount={true} {...config}
                    />
                </div>
            </section>
        )
    }
}
