/* eslint-disable react/no-danger, import/prefer-default-export */
import React from 'react';
import {Toolbar} from './Toolbar'
import DataList from "se-react-data-list"
import PaginationConfig from './PaginationConfig'

export default class ILTLearnerReport extends React.Component {
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
        //send ajax request with parameters
        //hand response to json
        //set json to state

        const url = `/analytics/ilt/learner/json/`
        const {toolbarData} = this.state
        const getVal=(key,defaultValue)=>{
            return toolbarData && toolbarData[key]?toolbarData[key]: defaultValue || '';
        }
        let ajaxData = {
            'report_type': 'ilt_learner_report',
            'courses_selected': [''],
            'query_tuples': toolbarData && toolbarData.selectedFilterItems ?
                toolbarData.selectedFilterItems.map(p => [p.value, p.key]) : [],
            'selected_properties': toolbarData && toolbarData.selectedProperties ? toolbarData.selectedProperties.map(p => p.value): [],
            'from_day': getVal('startDate'),
            'to_day': getVal('endDate'),
            'format': getVal('exportType'),
            'csrfmiddlewaretoken': $("input[name=csrfmiddlewaretoken]").val(),
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

        const config = {
            fields: [

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
                {name: 'LocationID', fieldName: 'Location ID'},
                {name: 'LocationName', fieldName: 'Location name'},

                {name: 'Address', fieldName: 'Address'},
                {name: 'ZipCode', fieldName: 'Zip code'},
                {name: 'City', fieldName: 'City'},
                {name: 'Name', fieldName: 'Name'},

                ...dynamicFields,

                {name: 'EnrollmentStatus', fieldName: 'Enrollment status'},
                {name: 'Attendee', fieldName: 'Attendee'},
                {name: 'OutwardTrips', fieldName: 'Outward trips'},
                {name: 'ReturnTrips', fieldName: 'Return trips'},

                {name: 'OvernightStay', fieldName: 'Overnight stay'},
                {name: 'OvernightStayAddress', fieldName: 'Overnight stay address'},
                {name: 'Comment', fieldName: 'Comment'}
            ],
            pagination: {
                pageSize: PaginationConfig.PageSize,
                rowsCount: this.state.rowsCount,
            },
            data: this.state.data,
            totalData: this.state.totalData
        }

        return (
            <>
                <Toolbar onChange={this.toolbarDataUpdate.bind(this)}
                         onInit={properties=>this.setState({properties})}/>
                <DataList ref={this.myRef} className="data-list" defaultLanguage={this.props.defaultLanguage}
                          enableRowsCount={true} {...config} onPageChange={this.fetchData.bind(this)}
                />
            </>
        )
    }
}
