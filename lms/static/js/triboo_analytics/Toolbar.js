/* eslint-disable react/no-danger, import/prefer-default-export */
import React from 'react';
import PropTypes from 'prop-types'

import DateRange from 'se-react-date-range'
import LabelValue from 'sec-react-label-value'
import CheckboxGroup from "se-react-checkbox-group"

class Exporter extends React.Component {
    constructor(props, context) {
        super(props, context);
        this.state={
            value:''
        }
    }

    handleChange(item){
        const {value}=item
        this.setState({
            value
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
                <input type="button" value="Go" onClick={()=>{}}/>
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
        this.state = {
            selectedFilterItems:[],
            selectedProperties:[],
            startDate:'',
            endDate:'',
            exportType:'',
            toolbarItems: this.getToolbarItems(enabledItems) || []
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
                            return {...p, props:{ ...p.props, data:data.list }}
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

    getToolbarItems(enabledItems=[]){
        const propertyData = [
            {value: 'failed', text: 'load data failed'},
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
                onChange:exportType=>this.setState({exportType}, this.fireOnChange)
            }},
        ].filter(p=>enabledItems.includes(p.name) ||  enabledItems.length <= 0).map((p,index)=>{
            let active = false
            if (index == 0){
                active=true
            }
            return {...p, active}
        })
    }

    fireOnChange () {
        const {onChange}=this.props
        const json = ['selectedFilterItems','selectedProperties', 'startDate','endDate','exportType']
            .reduce((mem, key)=>({...mem, [key]:this.state[key]}), {});
        onChange && onChange(json);
    };

    turnOnTab(json) {
        this.setState((prevState, props) => ({
            toolbarItems: prevState.toolbarItems.map(p => {
                if (p.name == json.name) {
                    p.active = true;
                } else {
                    p.active = false;
                }
                return p;
            })
        }))
    }

    render() {
        return (
            <div className="toolbar">
                <ul className="toolbar-tabs">
                    {this.state.toolbarItems.map(json =>
                        (<li key={json.name} onClick={this.turnOnTab.bind(this, json)}
                             className={json.name + (json.active && ' active' || '')}>
                            <i className={'far ' + json.icon}></i><span>{json.text}</span>
                        </li>)
                    )}
                </ul>
                <div className="toolbar-contents">
                    {this.state.toolbarItems.map(json => {
                        const Component = json.component || function () {
                            return <div>no component is set.</div>
                        }
                        return (<div key={json.name} className={'toolbar-content ' + json.name + (json.active && ' active' || '')}>
                            <Component {...json.props}/>
                        </div>)


                    })}
                </div>
            </div>
        )
    }
}

const DATA_ARRAY = PropTypes.arrayOf(PropTypes.exact({
    value:PropTypes.string,
    text:PropTypes.string,
    checked:PropTypes.bool
}))

Toolbar.propTypes = {
    //properties:DATA_ARRAY,
    onInit:PropTypes.func,
    onChange:PropTypes.func,
}
