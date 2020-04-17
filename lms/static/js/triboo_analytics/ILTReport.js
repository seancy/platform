/* eslint-disable react/no-danger, import/prefer-default-export */
import React from 'react';
import Tab from "se-react-tab"
import ILTGlobalReport from './ILTGlobalReport'
import ILTLearnerReport from './ILTLearnerReport'
import {pick} from "lodash";

export class ILTReport extends React.Component {
    constructor(props) {
        super(props);
        this.state = {
            activeTabName:'',
            toolbarData:{}
        };
        this.myRef = React.createRef()
    }

    render() {
        const {defaultLanguage,token} = this.props
        const commonProps = {...pick(this.props, 'defaultLanguage', 'token'), ...{
            defaultToolbarData:this.state.toolbarData,
            defaultActiveTabName:this.state.activeTabName,
            onTabSwitch:activeTabName=>{
                this.setState({activeTabName})
            },
            onChange:toolbarData=>this.setState({ toolbarData })
        }}
        const data = [
            {text: 'ILT Global Report', value: 'global', component: ILTGlobalReport, props:commonProps},
            {text: 'ILT Learner Report', value: 'learner', component: ILTLearnerReport, props:commonProps}
        ]

        return (
            <>
                <h3>{gettext('ILT Report')}</h3>
                <Tab activeValue={(new URLSearchParams(location.search)).get('report')}
                 onChange={console.log} data={data}/>
            </>
        )
    }
}
