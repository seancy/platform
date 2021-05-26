/* eslint-disable react/no-danger, import/prefer-default-export */
import React from 'react';
import PropTypes from 'prop-types'
import { pick, get } from 'lodash'

import DateRange from 'lt-react-date-range'
import LabelValue from 'lt-react-label-value'
import {Exporter} from './Exporter'
import {Properties} from './Properties'
import {PeriodFilter} from './PeriodFilter'


const debounce = (f, time) => {
    let debounced
    return function (...args) {
        const actor = () => f.apply(this, args)
        clearTimeout(debounced)
        debounced = setTimeout(actor, time)
    }
}

export class Toolbar extends React.Component {
    constructor(props) {
        super(props);
        this.fireOnChange = debounce(this.doFireChange.bind(this), 1000).bind(this)

        const {enabledItems}=props
        const toolbarItems = this.getToolbarItems(enabledItems)
        this.state = {
            timer:null,

            selectedFilterItems:[],
            selectedProperties:[],
            startDate:'',
            endDate:'',
            activeButton:'',
            exportType:'',

            toolbarItems,
            activeTabName:props.defaultActiveTabName || '' //toolbarItems.length > 0 ? toolbarItems[0].name : ''
        }
    }

    componentDidMount() {
        fetch('/analytics/common/get_properties/json/')
            .then(response=>{
                return response.json()
            })
            .then(data=>{
                this.setState((prev)=>{
                    let toolbarItems = prev.toolbarItems.map(p=>{
                        if (['filters','properties'].includes(p.name)) {
                            const nameList = p.name == 'filters'?[{text:gettext('Name'), value:'user_name'}]:[]
                            const dataList = [...nameList, ...data.list.map(item=>pick(item, ['text','value']))]
                            return {...p, props:{ ...p.props, data:dataList }}
                        } else {
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
            .catch(()=>{
                this.setState((prev)=>{
                    let toolbarItems = prev.toolbarItems.map(p=>{
                        if (['filters','properties'].includes(p.name)) {
                            return {...p, props: {...p.props, data: [{text: 'api: an error raised', value: ''}]}}
                        } else {
                            return p
                        }
                    })
                    return {
                        toolbarItems
                    }
                })

            })
    }

    export() {
        const {onGo}=this.props
        onGo && onGo(this.state.exportType)
    }

    fireExportTypeChange() {
        this.state.timer && clearTimeout(this.state.timer)
        this.setState({
            timer:setTimeout(()=>{
                this.doFireChange(true)
            },500)
        })
    }

    doFireChange(isExcluded=false) {
        this.setState({timer:null})
        const {onChange}=this.props
        const json = pick(this.state, 'selectedFilterItems','selectedProperties', 'startDate','endDate', 'activeButton', 'exportType')
        onChange && onChange(json, isExcluded);
    }

    getToolbarItems(enabledItems=[]) {
        const propertyData = [
            {value: '', text: ''},
        ]
        const {
            selectedFilterItems = [], selectedProperties=[], exportType='',startDate='',endDate='', activeButton=''
        } = get(this, 'props.defaultToolbarData', {})

        return [
            {name:'filters', text: gettext('Filters'), icon: 'fa-search', active: false, component: LabelValue, props:{
                data:propertyData, selectedList:selectedFilterItems,useFontAwesome:true, placeholder:gettext('Press enter to add'),
                onChange:(selectedFilterItems)=>this.setState({selectedFilterItems}, this.fireOnChange)
            }},
            {name:'properties', text: gettext('Properties'), icon: 'fa-sliders-h', active: false, component: Properties, props:{
                data:[], checkedList:selectedProperties.map(p => p.value),
                onChange:selectedProperties=>this.setState({selectedProperties}, this.fireOnChange)
            }},
            {name:'period', text: gettext('Period'), icon: 'fa-calendar-alt', active: false, component: PeriodFilter, props:{
                label:gettext('Select a time range'), buttonText:gettext('Last * days'), startDate, endDate, activeButton, useFontAwesome:true, periodTooltip: this.props.periodTooltip,
                onChange:(startDate,endDate, activeButton)=>{
                    this.setState({startDate,endDate, activeButton}, this.fireOnChange)
                }
            }},
            {name:'export', text: gettext('Export'), icon: 'fa-file-download', active: false, component: Exporter, props:{
                onGo:this.export.bind(this), defaultValue:exportType,
                onChange:exportType=>this.setState({exportType}, this.fireExportTypeChange.bind(this))
            }},
        ]
            .filter(p=>enabledItems.includes(p.name) ||  enabledItems.length <= 0)
    }

    setActiveTab(json) {
        const {onTabSwitch}=this.props
        let activeTabName = ''
        this.setState((prev)=>{
            if (prev.activeTabName != json.name) {
                activeTabName = json.name
            }
            return {activeTabName}
        }, ()=>{
            onTabSwitch && onTabSwitch(activeTabName)
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
                            <i className={'fal ' + json.icon}></i><span>{json.text}</span>
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
