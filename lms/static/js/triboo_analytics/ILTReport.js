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
        //const {} = this.state
        /*const functionStrs = ['Summary', 'Progress', 'Time Spent']
        const [Summary,Progress,TimeSpent] = functionStrs.map(p=>{
            return (props)=>{
                return (<div className={`${p.toLowerCase()}-component ${(props.className || '')}`}>
                    {p} component
                </div>)
            }
        })*/
        const {defaultLanguage,token} = this.props
        const data = [
            {text: 'ILT Global Report', value: 'summary', component: ILTGlobalReport, props:{
                    defaultLanguage, token
            }},
            {text: 'ILT Learner Report', value: 'progress', component: ILTLearnerReport, props:{
                    defaultLanguage, token
            }}
        ]

        return (
            <Tab onChange={console.log} data={data}/>
        )
    }
}
