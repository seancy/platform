/* eslint-disable react/no-danger, import/prefer-default-export */
import React from 'react';
import DateRange from 'se-react-date-range'
import LabelValue from 'sec-react-label-value'
//import Dropdown from "se-react-dropdown"
import CheckboxGroup from "se-react-checkbox-group"

function Filter(props) {
    const json = props || [
        {value: 'a0', text: 'name'},
        {value: 'a1', text: 'address'},
        {value: 'a2', text: 'city'},
        {value: 'a3', text: 'gender'},
        {value: 'a43', text: 'country'}
    ]
    return (<LabelValue {...json}/>)
}

class Exporter extends React.Component {
    constructor(props, context) {
        super(props, context);
        this.myRef = React.createRef()
    }

    clean(){
        //this.myRef.current.clean()
    }

    handleChange(){
        console.log(this.myRef.current.getData())
    }

    render() {
        const arr = this.props.data || [
            {value: 'a0', text: 'CVS report'},
            {value: 'a1', text: 'XLS report'},
            {value: 'a2', text: 'JSON report'},
        ]

        return (
            <div className="exporter-wrapper">
                <ul>
                {arr.map((item, index)=>{
                    const key = 'radio-'+index
                    return (
                        <li>
                            <input key={key} type="radio" name="radio0" id={key}/>
                            <label htmlFor={key}>{item.text}</label>
                        </li>
                    )
                })}
                </ul>
                {/*<CheckboxGroup ref={this.myRef} data={arr} onChange={this.handleChange.bind(this)}/>*/}

                <input type="button" value="Go" onClick={this.clean.bind(this)}/>
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

    handleChange(){
        console.log(this.myRef.current.getData())
    }

    render() {
        const arr = [
            {value: 'a0', text: 'name'},
            {value: 'a1', text: 'address'},
            {value: 'a2', text: 'city'},
            {value: 'a3', text: 'gender'},
            {value: 'a43', text: 'country'}
        ]

        return (
            <div className="properties-wrapper">
                <CheckboxGroup ref={this.myRef} data={arr} onChange={this.handleChange.bind(this)}/>

                <input type="button" value="Reset" onClick={this.clean.bind(this)}/>
            </div>
        )
    }
}


export class Toolbar extends React.Component {
    constructor(props) {
        super(props);
        const filterData = [
            {value:'a', text:'Address'},
            {value:'b', text:'City'},
            {value:'c', text:'Commercial'},
            {value:'d', text:'Region'},
            {value:'e', text:'Zone'},
            {value:'f', text:'Company'},
            {value:'g', text:'Country'},
            {value:'h', text:'Department'},
            {value:'i', text:'Email'},
            {value:'j', text:'Employee ID'},
            {value:'k', text:'Hire Date'},
            {value:'l', text:'ILT Supervisor'},
            {value:'m', text:'Job Code'},
            {value:'n', text:'Learning Group'},
            {value:'o', text:'Level'},
            {value:'p', text:'Location'},
        ]
        this.state = {
            toolbarItems: [
                {name: 'filters', icon: 'fa-search', active: true, component: Filter, props:{data:filterData}},
                {name: 'properties', icon: 'fa-sliders-h', active: false, component: Properties},
                {name: 'period', icon: 'fa-calendar-alt', active: false, component: DateRange, props:{
                    label:'Select a time range， Last', startDateName:'start0', endDateName:'end0' }},
                {name: 'export', icon: 'fa-file-export', active: false, component: Exporter},
            ]
            //hideCourseReportSelect: false
        };
    }

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
                        (<li onClick={this.turnOnTab.bind(this, json)}
                             className={json.name + (json.active && ' active' || '')}>
                            <i className={'far ' + json.icon}></i><span>{json.name}</span>
                        </li>)
                    )}
                </ul>
                <div className="toolbar-contents">
                    {this.state.toolbarItems.map(json => {
                        const Component = json.component || function () {
                            return <div>no component is set.</div>
                        }
                        return (<div className={'toolbar-content ' + json.name + (json.active && ' active' || '')}>
                            <Component {...json.props}/>
                        </div>)


                    })}
                </div>
            </div>
        )
    }
}

