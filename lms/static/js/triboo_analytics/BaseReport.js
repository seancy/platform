import React from 'react';
import {PaginationConfig} from "./Config";
import {get, merge, omit} from "lodash";

export default class BaseReport extends React.Component{
    constructor(props){
        super(props)
        this.state = {
            //storing toolbar data
            toolbarData: {},

            //ajax result
            data: [],
            totalData: {},
            rowsCount: 0,
        }

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

    generateParameter(){
        const {toolbarData} = this.state
        const getVal=(key,defaultValue)=>{
            return toolbarData && toolbarData[key]?toolbarData[key]: defaultValue || '';
        }
        return {
            'report_type': get(this.setting, 'reportType', ''),
            'courses_selected': [''],
            'query_tuples': get(toolbarData, 'selectedFilterItems', []).map(p => [p.value, p.key]),
            'selected_properties': get(toolbarData,'selectedProperties',[]).map(p => p.value),
            'from_day': getVal('startDate'),
            'to_day': getVal('endDate'),
            'csrfmiddlewaretoken': this.props.token,
            'page': {
                size: PaginationConfig.PageSize
            },
        }
    }

    fetchData(pageNo) {
        const url = get(this.setting, 'dataUrl', '')
        let ajaxData = merge(this.generateParameter(),{
            page:{
                no: pageNo
            }
        })
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

    startExport(type){
        const url = `/analytics/export/`
        let ajaxData = omit({
            ...this.generateParameter(),
            format: type,
            report_type:get(this.setting, 'reportType', '')
        }, 'page')
        $.ajax(url, {
            // method: 'get', //please change it to post in real environment.
            method: 'post',
            contentType: 'application/json; charset=utf-8',
            data: JSON.stringify(ajaxData),
            dataType: 'json',
            success: (result) => {
                LearningTribes.dialog.show(result.message, 3000)
            }
        })
    }
}
