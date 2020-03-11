import React from 'react';
import {Toolbar} from "./Toolbar";
import DataList from "se-react-data-list";
import PaginationConfig from "./PaginationConfig";


export default class CourseReportTimeSpent extends React.Component {
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
        const url = `/analytics/course/time_spent/json/`
        const {toolbarData} = this.state
        const getVal=(key,defaultValue)=>{
            return toolbarData && toolbarData[key]?toolbarData[key]: defaultValue || '';
        }
        let ajaxData = {
            'report_type': 'course_report_time_spent',
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

    getDynamicFields(){
        const {data} = this.state

        const propertiesValues = this.state.properties.map(p=>p.value)
        //const propertiesValues = fields.map(f=>f.fieldName)

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


    render() {
        //



        const properties=this.state.properties.map((p,index)=>({...p, checked:p.checked || false}))
        const {selectedProperties}=this.state.toolbarData;
        const propertiesFields = (selectedProperties && selectedProperties.length ? selectedProperties : properties).map(p=>({
                name: p.text,
                fieldName: p.value
            }))
        const {data}=this.state;
        //let dynamicFields = []
        const {dynamicFields, subFields}=this.getDynamicFields()
        /*if (data && data.length > 0){
            const firstRow = data[0]
            const propertiesValues = this.state.properties.map(p=>p.value)
            dynamicFields = Object.keys(firstRow).filter(key=>{
                return !propertiesValues.includes(key) && key != 'Name';
            }).map(key=>({name:key, fieldName:key}));
        }*/

        const config = {
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
