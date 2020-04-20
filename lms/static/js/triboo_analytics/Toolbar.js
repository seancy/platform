/* eslint-disable react/no-danger, import/prefer-default-export */
import React from 'react';
import PropTypes from 'prop-types'
import { pick, get } from 'lodash'

import DateRange from 'se-react-date-range'
import LabelValue from 'sec-react-label-value'
import CheckboxGroup from "se-react-checkbox-group"

class Exporter extends React.Component {
    constructor(props, context) {
        super(props, context);
        this.state={
            buttonStatus:'disabled',
            value:props.defaultValue || ''
        }
    }

    componentDidMount() {
        const {defaultValue}=this.props
        if (defaultValue != ''){
            this.fireChange(defaultValue)
        }
    }

    handleChange(item){
        const {value}=item
        this.setState({
            value,
            buttonStatus:''
        },()=>{
            this.fireChange(value)
        })
    }

    fireChange(value){
        const {onChange}=this.props
        onChange && onChange(value)
        this.setState({buttonStatus:''})
    }

    render() {
        const EXPORT_TYPES = [
            {value: 'csv', text: 'CSV report'},
            {value: 'xls', text: 'XLS report'},
            {value: 'json', text: 'JSON report'},
        ]
        const {onGo}=this.props
        return (
            <div className="exporter-wrapper">
                <ul>
                {(this.props.data || EXPORT_TYPES).map((item, index)=>{
                    const key = 'radio-'+index
                    return (
                        <li key={key}>
                            <input type="radio" name="radio0" id={key} checked={this.state.value == item.value?true:false} onChange={this.handleChange.bind(this, item)}/>
                            <label htmlFor={key}>{item.text}</label>
                        </li>
                    )
                })}
                </ul>
                <input type="button" value="Go" className={this.state.buttonStatus} onClick={onGo}/>
            </div>
        )
    }
}

class Properties extends React.Component {

    constructor(props, context) {
        super(props, context);
        this.myRef = React.createRef()
    }

    clean(){
        this.myRef.current.clean()
    }

    handleChange(selectedItems){
        const {onChange}=this.props
        onChange && onChange(selectedItems)
    }

    render() {
        return (
            <div className="properties-wrapper">
                <h4>{gettext('Select display properties')}</h4>
                <CheckboxGroup ref={this.myRef} {...pick(this.props, ['data', 'checkedList'])}
                               onChange={this.handleChange.bind(this)}/>
            </div>
        )
    }
}

export class Toolbar extends React.Component {
    constructor(props) {
        super(props);
        this.fireOnChange = this.fireOnChange.bind(this)

        const {enabledItems}=props
        const toolbarItems = this.getToolbarItems(enabledItems)
        this.state = {
            timer:null,

            selectedFilterItems:[],
            selectedProperties:[],
            startDate:'',
            endDate:'',
            exportType:'',

            toolbarItems,
            activeTabName:props.defaultActiveTabName || '' //toolbarItems.length > 0 ? toolbarItems[0].name : ''
        }
    }

    componentDidMount(){
        fetch('/analytics/common/get_properties/json/')
            .then(response=>{
                return response.json()
            })
            .then(data=>{
                this.setState((prev)=>{
                    let toolbarItems = prev.toolbarItems.map(p=>{
                        if (['filters','properties'].includes(p.name)){
                            const nameList = p.name == 'filters'?[{text:'Name', value:'user_name'}]:[]
                            const dataList = [...nameList, ...data.list.map(item=>pick(item, ['text','value']))]
                            return {...p, props:{ ...p.props, data:dataList }}
                        }else{
                            return p
                        }
                    })
                    return {
                        toolbarItems
                    }
                })
                const {onInit} = this.props
                onInit && onInit(data.list)
            })
    }

    export(){
        const {onGo}=this.props
        onGo && onGo(this.state.exportType)
    }

    fireExportTypeChange(){
        this.state.timer && clearTimeout(this.state.timer)
        this.setState({
            timer:setTimeout(()=>{
                this.doFireChange(true)
            },500)
        })
    }

    fireOnChange () {
        this.state.timer && clearTimeout(this.state.timer)
        this.setState({
            timer:setTimeout(()=>{
                this.doFireChange()
            },500)
        })
    }

    doFireChange(isExcluded=false){
        this.setState({timer:null})
        const {onChange}=this.props
        const json = pick(this.state, 'selectedFilterItems','selectedProperties', 'startDate','endDate', 'exportType')
        onChange && onChange(json, isExcluded);
    }

    getToolbarItems(enabledItems=[]){
        const propertyData = [
            {value: '', text: ''},
        ]
        const {
            selectedFilterItems = [], selectedProperties=[], exportType='',startDate='',endDate='',
        } = get(this, 'props.defaultToolbarData', {})

        return [
            {name:'filters', text: gettext('Filters'), icon: 'fa-search', active: false, component: LabelValue, props:{
                data:propertyData, selectedList:selectedFilterItems,
                onChange:(selectedFilterItems)=>this.setState({selectedFilterItems}, this.fireOnChange)
            }},
            {name:'properties', text: gettext('Properties'), icon: 'fa-sliders-h', active: false, component: Properties, props:{
                data:[], checkedList:selectedProperties.map(p => p.value),
                onChange:selectedProperties=>this.setState({selectedProperties}, this.fireOnChange)
            }},
            {name:'period', text: gettext('Period'), icon: 'fa-calendar-alt', active: false, component: DateRange, props:{
                label:'Select a time range', buttonBegin:'Last ', startDate, endDate,
                onChange:(startDate,endDate)=>{
                    this.setState({startDate,endDate}, this.fireOnChange)
                }
            }},
            {name:'export', text: gettext('Export'), icon: 'fa-file-download', active: false, component: Exporter, props:{
                onGo:this.export.bind(this), defaultValue:exportType,
                onChange:exportType=>this.setState({exportType}, this.fireExportTypeChange.bind(this))
            }},
        ]
            .filter(p=>enabledItems.includes(p.name) ||  enabledItems.length <= 0)
    }

    setActiveTab(json){
        const {onTabSwitch}=this.props
        this.setState((prev)=>{
            let activeTabName = ''
            if (prev.activeTabName != json.name){
                activeTabName = json.name
            }
            return {activeTabName}
        }, ()=>{
            onTabSwitch && onTabSwitch(json.name)
        })
    }

    render() {
        const {activeTabName}=this.state
        return (
            <div className="toolbar">
                <ul className="toolbar-tabs">
                    {this.props.children}
                    {this.state.toolbarItems.map(json =>
                        (<li key={json.name} onClick={this.setActiveTab.bind(this, json)}
                             className={json.name + (activeTabName==json.name ? ' active' : '')}>
                            <i className={'far ' + json.icon}></i><span>{json.text}</span>
                        </li>)
                    )}
                </ul>
                <div className="toolbar-contents">
                    {this.state.toolbarItems.map(json => {
                        const Component = json.component || function () {
                            return <div>no component is set.</div>
                        }
                        return (<div key={json.name} className={'toolbar-content ' + json.name + (activeTabName==json.name ? ' active' : '')}>
                            <Component {...json.props}/>
                        </div>)
                    })}
                </div>
            </div>
        )
    }
}

Toolbar.propTypes = {
    //properties:DATA_ARRAY,
    onExportTypeChange:PropTypes.func,
    onInit:PropTypes.func,
    onChange:PropTypes.func,
    defaultToolbarData:PropTypes.object
}
