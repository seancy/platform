import React from 'react';
import {PaginationConfig} from "./Config";
import {get, merge, omit} from "lodash";

export default class BaseReport extends React.Component{
    constructor(props){
        super(props)
        this.state = {
            isLoading:false,
            properties:[],

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

    getOrderedProperties(){
        const {data}=this.state;
        const {selectedProperties}=this.state.toolbarData;
        let properties=selectedProperties && selectedProperties.length ?
            selectedProperties : this.state.properties.filter(p=>p.type == 'default')
        let orderedProperties = []
        if (data && data.length > 0){
            const firstRow = data[0]
            const propertiesValues = properties.map(p=>p.value)
            orderedProperties = Object.keys(firstRow)
                .filter(key=>{
                    return propertiesValues.includes(key);
                })
                .map(key=>{
                    const item = properties.find(p=>p.value == key)
                    return item || {text:key, value:key}
                });
        }
        return orderedProperties.length > 0 ? orderedProperties : properties;
    }

    generateParameter(){
        const {toolbarData} = this.state
        const getVal=(key,defaultValue)=>{
            return toolbarData && toolbarData[key]?toolbarData[key]: defaultValue || '';
        }

        return {...{
            'report_type': get(this.setting, 'reportType', ''),
            'query_tuples': get(toolbarData, 'selectedFilterItems', []).map(p => [p.value, p.key]),
            'selected_properties': get(toolbarData,'selectedProperties',[]).map(p => p.value),
            'from_day': getVal('startDate'),
            'to_day': getVal('endDate'),
            'csrfmiddlewaretoken': this.props.token,
            'page': {
                size: PaginationConfig.PageSize
            }
        }, ...get(this.setting, 'extraParams', {})}
    }

    fetchData(pageNo) {
        const url = get(this.setting, 'dataUrl', '')
        let ajaxData = merge(this.generateParameter(),{
            page:{
                no: pageNo
            }
        })
        this.setState({isLoading:true})
        $.ajax(url, {
            // method: 'get', //please change it to post in real environment.
            method: 'post',
            contentType: 'application/json; charset=utf-8',
            data: JSON.stringify(ajaxData),
            dataType: 'json',
            success: (json) => {
                this.setState((s, p) => {
                    return {
                        isLoading:false,
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
