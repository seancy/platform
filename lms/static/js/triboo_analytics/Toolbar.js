/* eslint-disable react/no-danger, import/prefer-default-export */
import React from 'react';
import PropTypes from 'prop-types'
import { pick } from 'lodash'

import DateRange from 'se-react-date-range'
import LabelValue from 'sec-react-label-value'
import CheckboxGroup from "se-react-checkbox-group"

class Exporter extends React.Component {
    constructor(props, context) {
        super(props, context);
        this.state={
            buttonStatus:'disabled',
            value:''
        }
    }

    handleChange(item){
        const {value}=item
        this.setState({
            value,
            buttonStatus:''
        },()=>{
            const {onChange}=this.props
            onChange && onChange(value)

        })
    }

    render() {
        const EXPORT_TYPES = [
            {value: 'cvs', text: 'CVS report'},
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
                            <input type="radio" name="radio0" id={key} onClick={this.handleChange.bind(this, item)}/>
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
                <CheckboxGroup ref={this.myRef} data={this.props.data} onChange={this.handleChange.bind(this)}/>
                <input type="button" value="Reset" onClick={this.clean.bind(this)}/>
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
            selectedFilterItems:[],
            selectedProperties:[],
            startDate:'',
            endDate:'',
            exportType:'',

            toolbarItems,
            activeTabName:toolbarItems.length > 0 ? toolbarItems[0].name : ''
        };
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
        //const json = pick(this.state, 'selectedFilterItems','selectedProperties', 'startDate','endDate','exportType')
        onGo && onGo(this.state.exportType)
    }

    fireExportTypeChange(){
        const {onExportTypeChange}=this.props
        onExportTypeChange && onExportTypeChange(this.state.exportType);
    }

    fireOnChange () {
        const {onChange}=this.props
        const json = pick(this.state, 'selectedFilterItems','selectedProperties', 'startDate','endDate', 'exportType')
        onChange && onChange(json);
    }

    getToolbarItems(enabledItems=[]){
        const propertyData = [
            {value: '', text: ''},
        ]
        return [
            {name:'filters', text: gettext('filters'), icon: 'fa-search', active: false, component: LabelValue, props:{
                data:propertyData,
                onChange:(selectedFilterItems)=>this.setState({selectedFilterItems}, this.fireOnChange)
            }},
            {name:'properties', text: gettext('properties'), icon: 'fa-sliders-h', active: false, component: Properties, props:{
                data:propertyData,
                onChange:selectedProperties=>this.setState({selectedProperties}, this.fireOnChange)
            }},
            {name:'period', text: gettext('period'), icon: 'fa-calendar-alt', active: false, component: DateRange, props:{
                label:'Select a time range， Last',
                onChange:(startDate,endDate)=>{
                    this.setState({startDate,endDate}, this.fireOnChange)
                }
            }},
            {name:'export', text: gettext('export'), icon: 'fa-file-export', active: false, component: Exporter, props:{
                onGo:this.export.bind(this),
                onChange:exportType=>this.setState({exportType}, this.fireExportTypeChange.bind(this))
            }},
        ]
            .filter(p=>enabledItems.includes(p.name) ||  enabledItems.length <= 0)
    }

    render() {
        const {activeTabName}=this.state
        return (
            <div className="toolbar">
                <ul className="toolbar-tabs">
                    {this.state.toolbarItems.map(json =>
                        (<li key={json.name} onClick={()=>this.setState({activeTabName:json.name})}
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

/*const DATA_ARRAY = PropTypes.arrayOf(PropTypes.exact({
    value:PropTypes.string,
    text:PropTypes.string,
    checked:PropTypes.bool
}))*/

Toolbar.propTypes = {
    //properties:DATA_ARRAY,
    onExportTypeChange:PropTypes.func,
    onInit:PropTypes.func,
    onChange:PropTypes.func,
}
