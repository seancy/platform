/* eslint-disable react/no-danger, import/prefer-default-export */
import React from 'react';
import DateRange from 'se-react-date-range'
import Dropdown from "se-react-dropdown"

function Filter() {
    const arr = [
        { value:'a0', text:'name' },
        { value:'a1', text:'address' },
        { value:'a2', text:'city' },
        { value:'a3', text:'gender' },
        { value:'a4', text:'country' },

    ]
    //
    return (<Dropdown data={arr}/>)
}

export class Toolbar extends React.Component {
    constructor(props) {
        super(props);
        this.state = {
            toolbarItems: [
                { name:'filters', icon:'fa-search', active: true, component: Filter },
                { name:'properties', icon:'fa-sliders-h', active: false },
                { name:'period', icon:'fa-calendar-alt', active: false, component:DateRange },
                { name:'export', icon:'fa-file-export', active: false },
            ]
            //hideCourseReportSelect: false
        };
    }

    turnOnTab(json){
        this.setState((prevState, props)=>({
            toolbarItems: prevState.toolbarItems.map(p=>{
                if (p.name == json.name){
                    p.active = true;
                }else{
                    p.active = false;
                }
                return p;
            })
        }))
    }

    render(){
        return (
            <div className="toolbar">
                <ul className="toolbar-tabs">
                    {this.state.toolbarItems.map(json=>
                        (<li onClick={this.turnOnTab.bind(this, json)} className={json.name + (json.active && ' active' || '')}>
                            <i className={'far ' + json.icon}></i><span>{json.name}</span>
                        </li>)
                    )}
                    {/*<li className="filters"><i className="far fa-search"></i><span>filters</span></li>
                    <li className="properties"><i className="far fa-sliders-h"></i><span>properties</span></li>
                    <li className="period"><i className="far fa-calendar-alt"></i><span>period</span></li>
                    <li className="export"><i className="far fa-file-export"></i><span>export</span></li>*/}
                </ul>
                <div className="toolbar-contents">
                    {this.state.toolbarItems.map(json=>{
                        const Component = json.component || function () {
                            return <div>no component is set.</div>
                        }
                        return (<div className={'toolbar-content '+json.name + (json.active && ' active' || '')}>
                            <Component/>
                        </div>)


                    })}
                </div>
                {/*<div className="toolbar-content filters">
                    filters content.
                </div>
                <DateRange className="toolbar-content period" />*/}
            </div>
        )
    }
}

