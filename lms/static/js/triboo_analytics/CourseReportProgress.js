import React from 'react';
import {Toolbar} from "./Toolbar";
import DataList from "se-react-data-list";
import {PaginationConfig, ReportType} from "./Config";
import BaseReport from './BaseReport'
import {pick} from "lodash";

export default class CourseReportProgress extends BaseReport {
    constructor(props) {
        super(props);


        this.state = {
            ...this.state,
        };
    }

    setting = {
        extraParams:{course_id: this.props.course_id},
        reportType:ReportType.COURSE_PROGRESS,
        dataUrl:'/analytics/course/json/'
    }

    getConfig() {
        //const properties= this.state.properties.filter(p=>p.type == 'default')
        //const {selectedProperties}=this.state.toolbarData;
        const propertiesFields = this.getOrderedProperties().map(p=>({
                name: p.text,
                fieldName: p.value
            }))
        const {data, columns}=this.state;
        let dynamicFields = []
        if (data && data.length > 0){
            const firstRow = data[0]
            const propertiesValues = this.state.properties.map(p=>p.value)
            const dynamicKeys = columns.length > 0 ? columns :
                Object.keys(firstRow).filter(key=>{
                    return !propertiesValues.includes(key) && key != 'Name';
                })
            dynamicFields = dynamicKeys.map(key=>({name:key, fieldName:key}));
        }

        return {...{
            keyField:"ID",
            fields:[
                {name: 'Name', fieldName: 'Name'},
                ...propertiesFields,
                ...dynamicFields
            ],
            cellRender:v=>{
                if ((v.startsWith('Yes') || v.startsWith('No')) && v.includes(':')) {
                    const arr = v.split(':')
                    return (<><span className={"trophy-" + (v.startsWith('Yes')?'yes fa fa-check':'no fa fa-times')}></span> {arr[1]}</> )
                } else {
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
                         periodTooltip={gettext('Display the progress of learners at the end of the selected period '
                                             + 'for learners who visited the course during this period.')}/>
                 {this.props.children}
                <DataList useFontAwesome={true} ref={this.myRef} className="data-list" defaultLanguage={this.props.defaultLanguage}
                          enableRowsCount={true} {...config}
                />
            </>
        )
    }
}
