/* eslint-disable react/no-danger, import/prefer-default-export */
import React from 'react';
import {Toolbar} from './Toolbar'
import DataList from "se-react-data-list"
import PaginationConfig from './PaginationConfig'

export class LearnerReport extends React.Component {
    constructor(props) {
        super(props);

        this.state = {
            //for initialize toolbar components
            filters: this.props.filters || [],
            properties: this.props.properties || [],

            //storing toolbar data
            toolbarData: {},

            //ajax result
            data: [],
            totalData: {},
            rowsCount: 0,
        };

        this.myRef = React.createRef()


    }

    componentDidMount() {
        this.fetchData(1)
    }

    toolbarDataUpdate(toolbarData){
        this.setState(s=>{
            return {
                toolbarData
            }
        },()=>{
            this.fetchData(1)
            this.myRef.current.resetPage(1)
        })
    }

    fetchData(pageNo) {
        //send ajax request with parameters
        //hand response to json
        //set json to state

        const url = `/static/data.json`
        const {toolbarData} = this.state
        const getVal=(key,defaultValue)=>{
            return toolbarData && toolbarData[key]?toolbarData[key]: defaultValue || '';
        }
        let ajaxData = {
            'report_type': 'learner_report',
            'courses_selected': [''],
            'query_tuples': toolbarData && toolbarData.selectedFilterItems ?
                toolbarData.selectedFilterItems.map(p => [p.text, p.value]) : [],
            'selected_properties': toolbarData && toolbarData.selectedProperties ?
                toolbarData.selectedProperties.map(p => p.value): [],
            'from_day': getVal('startDate'),
            'to_day': getVal('endDate'),
            'format': getVal('exportType'),
            'csrfmiddlewaretoken': 'nDou5pR169v76UwtX4XOpbQsSTLu6SexeWyd0ykjGR2ahYMV0OY7nddkYQqnT6ze',
            'page': {
                no: pageNo, size: PaginationConfig.PageSize
            },
        }

        $.ajax(url, {
            method: 'get', //please change it to post in real environment.
            dataType: 'json',
            data: ajaxData,
            success: (json) => {
                this.setState((s, p) => {
                    return {
                        data: json.list,
                        totalData: json.total, //{email: 'total:', first_name: json.total},
                        rowsCount: json.pagination.rowsCount
                    }
                })
            }
        })
    }

    render() {
        const config = {
            fields: [
                {name: 'Name', fieldName: 'Name'},
                {name: 'Email', fieldName: 'Email'},
                {name: 'Country', fieldName: 'Country'},
                {name: 'Commerical Zone', fieldName: 'CommericalZone'},
                {name: 'Commerical Region', fieldName: 'CommericalRegion'},
                {name: 'City', fieldName: 'City'},
                {name: 'Employee', fieldName: 'Employee'},
                {name: 'Enrollments', fieldName: 'Enrollments'},
                {name: 'Successful', fieldName: 'Successful'},
                {name: 'Unsuccessful', fieldName: 'Unsuccessful'},
                {name: 'In Progress', fieldName: 'InProgress'},
                {name: 'Not Started', fieldName: 'NotStarted'},
                {name: 'Average Final Score', fieldName: 'AverageFinalScore'},
                {name: 'Badges', fieldName: 'Badges'},
                {name: 'Posts', fieldName: 'Posts'},
                {name: 'Total Time Spent', fieldName: 'TotalTimeSpent'},
                {name: 'Last Login', fieldName: 'LastLogin'}
            ],
            pagination: {
                pageSize: PaginationConfig.PageSize,
                rowsCount: this.state.rowsCount,
            },
            data: this.state.data,
            totalData: this.state.totalData
        }

        return (
            <section className="analytics-wrapper learner">
                <div className="report-wrapper">

                    <div className="last-update">
                        <i className="fa fa-history"></i>{gettext('Please, note that these reports are not live. Last update:')}{this.props.last_update}
                    </div>
                    <Toolbar onChange={this.toolbarDataUpdate.bind(this)} filters={this.props.filters}
                             properties={this.props.filters}/>
                    <DataList ref={this.myRef} className="data-list" defaultLanguage={this.props.defaultLanguage}
                              enableRowsCount={true} {...config} onPageChange={this.fetchData.bind(this)}
                    />

                </div>
            </section>
        )
    }
}
