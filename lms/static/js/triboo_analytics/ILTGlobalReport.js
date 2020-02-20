/* eslint-disable react/no-danger, import/prefer-default-export */
import React from 'react';
import {Toolbar} from './Toolbar'
import DataList from "se-react-data-list"
import PaginationConfig from './PaginationConfig'

export class ILTGlobalReport extends React.Component {
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
        const {data,totalData} = this.state
        const parameterObj = {
            fields: [
                {name: 'Name', fieldName: 'userName'},
                {name: 'Email', fieldName: 'email'},
                {name: 'Country', fieldName: 'country'},
            ],
            pagination: {
                pageSize: PaginationConfig.PageSize,
                rowsCount: this.state.rowsCount,
            },
            data, totalData
        }

        return (
            <React.Fragment>
                <Toolbar onChange={this.toolbarDataUpdate.bind(this)} filters={this.props.filters}
                    enabledItems={['period','export']} properties={this.props.filters}/>
                 <DataList ref={this.myRef} className="data-list" defaultLanguage={this.props.defaultLanguage}
                          enableRowsCount={true} {...parameterObj} onPageChange={this.fetchData.bind(this)}
                />

            </React.Fragment>

        )
    }
}
