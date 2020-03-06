/* eslint-disable react/no-danger, import/prefer-default-export */
import React from 'react';
import {Toolbar} from './Toolbar'
import DataList from "se-react-data-list"
import PaginationConfig from './PaginationConfig'

export default class ILTGlobalReport extends React.Component {
    constructor(props) {
        super(props);
        this.state = {
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
        const url = `/static/data.json`
        const {toolbarData} = this.state
        const getVal=(key,defaultValue)=>{
            return toolbarData && toolbarData[key]?toolbarData[key]: defaultValue || '';
        }
        let ajaxData = {
            'report_type': 'ilt_global_report',
            'courses_selected': [''],
            'from_day': getVal('startDate'),
            'to_day': getVal('endDate'),
            'format': getVal('exportType'),
            'csrfmiddlewaretoken': this.props.token,
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
        const config = {
            fields: [
                {name: 'Name', fieldName: 'userName'},

                {name: 'Geographical area', fieldName: 'GeographicalArea'},
                {name: 'Course country', fieldName: 'CourseCountry'},
                {name: 'ZoneRegion', fieldName: 'Zone/Region'},
                {name: 'CourseTags', fieldName: 'Course tags'},

                {name: 'CourseCode', fieldName: 'Course code'},
                {name: 'Course', fieldName: 'Course'},
                {name: 'Section', fieldName: 'Section'},
                {name: 'Subsection', fieldName: 'Subsection'},

                {name: 'SessionID', fieldName: 'Session ID'},
                {name: 'StartDate', fieldName: 'Start date'},
                {name: 'StartTime', fieldName: 'Start time'},
                {name: 'EndDate', fieldName: 'End date'},

                {name: 'EndTime', fieldName: 'End time'},
                {name: 'Duration', fieldName: 'Duration (in hours)'},
                {name: 'MaxCapacity', fieldName: 'Max capacity'},
                {name: 'Enrollees', fieldName: 'Enrollees'},

                {name: 'Attendees', fieldName: 'Attendees'},
                {name: 'AttendanceSheet', fieldName: 'Attendance sheet'},
                {name: 'LocationID', fieldName: 'Location ID'},
                {name: 'LocationName', fieldName: 'Location name'},

                {name: 'Address', fieldName: 'Address'},
                {name: 'ZipCode', fieldName: 'Zip code'},
                {name: 'City', fieldName: 'City'},
            ],
            pagination: {
                pageSize: PaginationConfig.PageSize,
                rowsCount: this.state.rowsCount,
            },
            data, totalData
        }

        return (
            <>
                <Toolbar onChange={this.toolbarDataUpdate.bind(this)} enabledItems={['period','export']} />
                 <DataList ref={this.myRef} className="data-list" defaultLanguage={this.props.defaultLanguage}
                          enableRowsCount={true} {...config} onPageChange={this.fetchData.bind(this)}
                />
            </>
        )
    }
}
