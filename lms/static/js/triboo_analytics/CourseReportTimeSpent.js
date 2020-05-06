import React from 'react';
import {Toolbar} from "./Toolbar";
import DataList from "se-react-data-list";
import {PaginationConfig, ReportType} from "./Config";
import BaseReport from './BaseReport'
import {pick, flatten} from "lodash";

export default class CourseReportTimeSpent extends BaseReport {
    constructor(props) {
        super(props);

        this.state = {
            ...this.state,
            properties:[],
        };
    }

    setting = {
        extraParams:{course_id: this.props.course_id},
        reportType:ReportType.COURSE_TIME_SPENT,
        dataUrl:'/analytics/course/json/'
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
            subFields = flatten(complexDynamicFields.map(keyL1=>{
                return complexDynamicKeys.filter(key=>{
                    return key.split('/')[0] == keyL1
                }).map(key=>{
                    const arr = key.split('/')
                    const keyL2 = arr[1]
                    return {name:keyL2,fieldName:key}
                })
            }))
        }
        return {dynamicFields, subFields}
    }

    getConfig(){
        /*const properties=this.state.properties.filter(p=>p.type == 'default')
        const {selectedProperties}=this.state.toolbarData;*/
        const propertiesFields = this.getOrderedProperties().map(p=>({
                name: p.text,
                fieldName: p.value
            }))
        const {dynamicFields, subFields}=this.getDynamicFields()

        return {...{
            keyField:"ID",
            fields:[
                {name: 'Name', fieldName: 'Name'},
                ...propertiesFields,
                ...dynamicFields
            ], subFields,
            cellRender:v=>{
                if ((v.startsWith('Yes') || v.startsWith('No')) && v.includes(':')){
                    const arr = v.split(':')
                    return (<><span className={"trophy-no fa fa-"+ (v.startsWith('Yes')?'check':'times')}></span> {arr[1]}</> )
                }else{
                    return v
                }
            },
        }, ...this.getBaseConfig()}
    }

    render() {
        const config = this.getConfig()
        return (
            <>
                <Toolbar onChange={this.toolbarDataUpdate.bind(this)}
                         onGo={this.startExport.bind(this)}
                         {...pick(this.props, ['onTabSwitch', 'defaultToolbarData', 'defaultActiveTabName'])}
                         onInit={properties=>this.setState({properties})}
                         periodTooltip={gettext('Display the time learners spent in the course during the selected period '
                                              + 'for learners who visited the course during this period.')}/>
                 {this.props.children}
                <DataList useFontAwesome={true} ref={this.myRef} className="data-list" defaultLanguage={this.props.defaultLanguage}
                          enableRowsCount={true} {...config}
                />
            </>
        )
    }
}
