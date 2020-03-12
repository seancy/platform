import React from 'react';
import {Toolbar} from "./Toolbar";
import DataList from "se-react-data-list";
import {PaginationConfig, ReportType} from "./Config";
import BaseReport from './BaseReport'

export default class CourseReportTimeSpent extends BaseReport {
    constructor(props) {
        super(props);

        this.state = {
            ...this.state,
            properties:[],
        };
    }

    setting = {
        reportType:ReportType.COURSE_TIME_SPENT,
        dataUrl:'/analytics/course/time_spent/json/'
    }

    getDynamicFields(){
        const {data} = this.state
        const propertiesValues = this.state.properties.map(p=>p.value)

        let dynamicFields = [], subFields = []
        if (data && data.length > 0){
            const firstRow = data[0]
            const dynamicKeys = Object.keys(firstRow)
                .filter(key=>{
                    return !propertiesValues.includes(key) && key != 'Name' // && !key.split('/')[1]
                })
            const complexDynamicKeys = dynamicKeys.filter(key=>key.split('/')[1])
            const complexDynamicKeysL1 = complexDynamicKeys.map(key=>key.split('/')[0])
            //const complexDynamicKeysL2 = complexDynamicKeys.map(key=>key.split('/')[1])

            const normalDynamicFields = dynamicKeys.filter(key=>!key.split('/')[1])
            const complexDynamicFields = [...new Set(complexDynamicKeys.map(key=>key.split('/')[0]))]
            const countSpan = (key)=>{
                return complexDynamicKeysL1.filter(l1key=>key==l1key).length
            }

            dynamicFields = [...normalDynamicFields.map(key=>({name:key,fieldName:key})),
                ...complexDynamicFields.map(key=>({name:key,fieldName:key, colSpan:countSpan(key)}))]
            subFields = complexDynamicKeys.map(key=>{
                const arr = key.split('/')
                const keyL2 = arr[1]
                return {name:keyL2,fieldName:key}
            })
        }
        return {dynamicFields, subFields}
    }

    getConfig(){
        const properties=this.state.properties.map((p,index)=>({...p, checked:p.checked || false}))
        const {selectedProperties}=this.state.toolbarData;
        const propertiesFields = (selectedProperties && selectedProperties.length ? selectedProperties : properties).map(p=>({
                name: p.text,
                fieldName: p.value
            }))
        const {dynamicFields, subFields}=this.getDynamicFields()

        return {
            fields:[
                {name: 'Name', fieldName: 'Name'},
                ...propertiesFields,
                ...dynamicFields
            ], subFields,
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
