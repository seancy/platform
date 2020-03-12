/* eslint-disable react/no-danger, import/prefer-default-export */
import React from 'react';
import Tab from "se-react-tab"
import ILTGlobalReport from './ILTGlobalReport'
import ILTLearnerReport from './ILTLearnerReport'

export class ILTReport extends React.Component {
    constructor(props) {
        super(props);
        this.state = {
        };
        this.myRef = React.createRef()
    }

    render() {
        const {defaultLanguage,token} = this.props
        const data = [
            {text: 'ILT Global Report', value: 'global', component: ILTGlobalReport, props:{
                    defaultLanguage, token
            }},
            {text: 'ILT Learner Report', value: 'learner', component: ILTLearnerReport, props:{
                    defaultLanguage, token
            }}
        ]

        return (
            <Tab activeValue={(new URLSearchParams(location.search)).get('report')}
                 onChange={console.log} data={data}/>
        )
    }
}
