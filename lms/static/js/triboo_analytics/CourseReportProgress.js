import React from 'react';
import {Toolbar} from "./Toolbar";
import DataList from "se-react-data-list";
import {PaginationConfig, ReportType} from "./Config";
import BaseReport from './BaseReport'

export default class CourseReportProgress extends BaseReport {
    constructor(props) {
        super(props);

        this.state = {
            ...this.state,
            properties:[],
        };
    }

    setting = {
        reportType:ReportType.COURSE_PROGRESS,
        dataUrl:'/analytics/course/progress/json/'
    }

    getConfig(){
        const properties=this.state.properties.map((p,index)=>({...p, checked:p.checked || false}))
        const {selectedProperties}=this.state.toolbarData;
        const propertiesFields = (selectedProperties && selectedProperties.length ? selectedProperties : properties).map(p=>({
                name: p.text,
                fieldName: p.value
            }))
        const {data}=this.state;
        let dynamicFields = []
        if (data && data.length > 0){
            const firstRow = data[0]
            const propertiesValues = this.state.properties.map(p=>p.value)
            dynamicFields = Object.keys(firstRow).filter(key=>{
                return !propertiesValues.includes(key) && key != 'Name';
            }).map(key=>({name:key, fieldName:key}));
        }

        return {
            fields:[
                {name: 'Name', fieldName: 'Name'},
                ...propertiesFields,
                ...dynamicFields
            ],
            cellRender:v=>{
                if ((v.startsWith('Yes') || v.startsWith('No')) && v.includes(':')){
                    const arr = v.split(':')
                    return (<><span class={"trophy-no fa fa-"+ (v.startsWith('Yes')?'check':'times')}></span> {arr[1]}</> )
                }else{
                    return v
                }
            },
            pagination: {
                pageSize: PaginationConfig.PageSize,
                rowsCount: this.state.rowsCount,
            },
            data: this.state.data,
            totalData: this.state.totalData
        }
    }
    render() {
        const config = this.getConfig()
        return (
            <>
                <Toolbar onChange={this.toolbarDataUpdate.bind(this)}
                         onExportTypeChange={this.startExport.bind(this)} onGo={this.startExport.bind(this)}
                         onInit={properties=>this.setState({properties})}/>
                <DataList ref={this.myRef} className="data-list" defaultLanguage={this.props.defaultLanguage}
                          enableRowsCount={true} {...config} onPageChange={this.fetchData.bind(this)}
                />
            </>
        )
    }
}
