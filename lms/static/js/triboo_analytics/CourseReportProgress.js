import React from 'react';
import {Toolbar} from "./Toolbar";
import DataList from "se-react-data-list";
import PaginationConfig from "./PaginationConfig";


export default class CourseReportProgress extends React.Component {
    constructor(props) {
        super(props);

        this.state = {
            properties:[],

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
        const url = `/analytics/learner/json/`
        const {toolbarData} = this.state
        const getVal=(key,defaultValue)=>{
            return toolbarData && toolbarData[key]?toolbarData[key]: defaultValue || '';
        }
        let ajaxData = {
            'report_type': 'learner_report',
            'courses_selected': [''],
            'query_tuples': toolbarData && toolbarData.selectedFilterItems ?
                toolbarData.selectedFilterItems.map(p => [p.value, p.key]) : [],
            'selected_properties': toolbarData && toolbarData.selectedProperties ? toolbarData.selectedProperties.map(p => p.value): [],
            'from_day': getVal('startDate'),
            'to_day': getVal('endDate'),
            'format': getVal('exportType'),
            'csrfmiddlewaretoken': this.props.token,
            'page': {
                no: pageNo, size: PaginationConfig.PageSize
            },
        }

        $.ajax(url, {
            // method: 'get', //please change it to post in real environment.
            method: 'post',
            contentType: 'application/json; charset=utf-8',
            data: JSON.stringify(ajaxData),
            dataType: 'json',
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
        const properties=this.state.properties.map((p,index)=>({...p, checked:p.checked || false}))
        const {selectedProperties}=this.state.toolbarData;
        const dynamicFields = (selectedProperties && selectedProperties.length ? selectedProperties : properties).map(p=>({
                name: p.text,
                fieldName: p.value
            }))
        const render=(val)=>{
            return <span className={val?'in-progress-bg':'not-started-bg'}>{val?'In Progress':'Not Started'}</span>
        }
        const config = {
            fields: [
                /*{name: 'Name', fieldName: 'Name'},

                ...dynamicFields,

                {name: 'Status', fieldName: 'status', render, className:'status'},
                {name: 'Progress', fieldName: 'progress'},
                {name: 'Current Score', fieldName: 'currentScore'},
                {name: 'Badges', fieldName: 'badges'},
                {name: 'Posts', fieldName: 'posts'},
                {name: 'Total Time Spent', fieldName: 'totalTimeSpent'},
                {name: 'Enrollment Date', fieldName: 'enrollmentDate'},
                {name: 'Completion Date', fieldName: 'completionDate'},*/

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
                    <Toolbar onChange={this.toolbarDataUpdate.bind(this)} enabledItems={['period','export']}
                             onInit={properties=>this.setState({properties})}/>
                    <DataList ref={this.myRef} className="data-list" defaultLanguage={this.props.defaultLanguage}
                              enableRowsCount={true} {...config} onPageChange={this.fetchData.bind(this)}
                    />

                </div>
            </section>
        )
    }
}
