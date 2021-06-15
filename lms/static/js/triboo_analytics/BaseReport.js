import React from 'react';
import {PaginationConfig} from "./Config";
import {get, merge, omit, isEmpty, pick} from "lodash";


export default class BaseReport extends React.Component{
    constructor(props) {
        super(props)
        this.state = {
            timer:null,

            isLoading:false,
            properties:[],

            //storing toolbar data
            toolbarData: {},

            //ajax result
            message:'',
            columns:[],
            data: [],
            totalData: {},
            rowsCount: 0,
            xhrFetchData: null,
            fields: [],
            subFields: undefined,
            applyDisabled: true,
        }

        this.myRef = React.createRef()
    }

    componentDidMount() {
        const toolbarData = get(this, 'props.defaultToolbarData', {})
        const {selectedFilterItems=[], selectedProperties=[], startDate='', endDate=''} = toolbarData
        if (Object.keys(toolbarData).length <= 0 ||
            (selectedFilterItems.length <= 0 &&
            selectedProperties.length <= 0  &&
            startDate == '' &&
            endDate == '') ) {
            this.fetchData(1)
        }

        this.updateFields()
    }

    getFields () {
        const propertiesFields = this.getOrderedProperties()
        const {dynamicFields, subFields} = this.getDynamicFields()
        return {
            fields: [
                {name: gettext('Name'), fieldName: 'Name', render:(value)=>{
                    return <div dangerouslySetInnerHTML={{__html: value}} />
                }},

                ...propertiesFields,

                ...dynamicFields,
            ],
            subFields,
        }
    }

    getDynamicFields () {
        return {
            dynamicFields: [],
        }
    }

    updateFields () {
        this.setState(this.getFields())
    }

    toolbarDataUpdate(toolbarData, isExcluded) {
        this.setState(prev => ({
            toolbarData,
            applyDisabled: isExcluded === true && prev.applyDisabled,
        }), () => {
            if (!isExcluded) this.applyQuery()

            const {onChange} = this.props
            onChange && onChange(this.state.toolbarData)
        })
    }

    applyQuery () {
        this.fetchData(1)
        this.updateFields()
        this.myRef.current.resetPage(1)
        this.setState({
            applyDisabled: true,
        })
    }

    getOrderedProperties() {
        const {data}=this.state;
        const {selectedProperties}=this.state.toolbarData;
        const properties = selectedProperties && selectedProperties.length
            ? selectedProperties
            : this.state.properties.filter(p => p.type === 'default')

        let orderedProperties = []
        if (data && data.length > 0) {
            const firstRow = data[0]
            const propertiesValues = properties.map(p=>p.value)
            orderedProperties = Object.keys(firstRow)
                .filter(key => propertiesValues.includes(key))
                .map(key=>{
                    const item = properties.find(p=>p.value == key)
                    return item || {text:key, value:key}
                });
        }
        const propertiesFieldsToBeTranslate = ['user_country', 'user_gender']
        return (orderedProperties.length > 0 ? orderedProperties : properties)
            .map(p=>({
                name: p.text,
                fieldName: p.value,
                render:(cellValue, row, item)=>{
                    let finalVal = (cellValue == null || cellValue === '') ? '—' :
                        (propertiesFieldsToBeTranslate.includes(item.fieldName) ? gettext(cellValue) : cellValue.toString())
                    return finalVal
                }
            }));
    }

    generateParameter() {
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

    getBaseConfig() {
        return {
            onSort:(sort, pageNo)=>{
                sort == '' ?
                    this.fetchData(pageNo) :
                    this.fetchData(pageNo, sort)
            },
            onPageChange:(pageNo, sort)=>{
                sort == '' ?
                    this.fetchData(pageNo) :
                    this.fetchData(pageNo, sort)
            },
            ...pick(this.state, ['isLoading', 'data', 'totalData', 'message']),
            totalRowsText:gettext('Total: * rows'),
            emptyText:gettext('No data available'),
            pagination: {
                pageSize: PaginationConfig.PageSize,
                rowsCount: this.state.rowsCount,
            }
        }
    }

    fetchData(pageNo, sort='+ID') {
        const url = get(this.setting, 'dataUrl', '')
        let ajaxData = merge(this.generateParameter(),{
            page:{
                no: pageNo
            }, ...(sort!=''?{sort}:{})
        })

        const isValidateDate = v => {
          if (!v) return true
          if (isNaN(new Date(v).getTime())) return false
          return true
        }

        if (!isValidateDate(ajaxData.from_day)) return
        if (!isValidateDate(ajaxData.to_day)) return

        const xhrFetchData = $.ajax(url, {
            // method: 'get', //please change it to post in real environment.
            method: 'post',
            contentType: 'application/json; charset=utf-8',
            data: JSON.stringify(ajaxData),
            dataType: 'json',
            beforeSend: () => {
              if (this.state.xhrFetchData) this.state.xhrFetchData.abort()
              this.setState(() => ({
                xhrFetchData,
                isLoading: true
              }))
            },
            success: (json) => {
                this.setState((s, p) => {
                    return {
                        message: json.message,
                        isLoading:false,
                        data: json.list,
                        columns:json.columns,
                        totalData: json.total, //{email: 'total:', first_name: json.total},
                        rowsCount: json.pagination.rowsCount
                    }
                }, this.updateFields)
            },
            error:(json)=>{
                this.setState((s, p) => {
                    return {
                        message: get(json, 'responseJSON.message', ''),
                        isLoading:false
                    }
                })
            }
        })
    }

    startExport(type) {
        const url = `/analytics/export/`
        let ajaxData = omit({
            ...this.generateParameter(),
            format: type,
            report_type:get(this.setting, 'reportType', '')
        }, 'page')
        const showMessage = (result)=>{
            LearningTribes.dialog.show(result.message, 3000)
        }
        $.ajax(url, {
            // method: 'get', //please change it to post in real environment.
            method: 'post',
            contentType: 'application/json; charset=utf-8',
            data: JSON.stringify(ajaxData),
            dataType: 'json',
            success: showMessage,
            error:showMessage
        })
    }
}
