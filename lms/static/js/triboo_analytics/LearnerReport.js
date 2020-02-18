/* eslint-disable react/no-danger, import/prefer-default-export */
import React from 'react';
import {Toolbar} from './Toolbar'
import DataList from "se-react-data-list"

export class LearnerReport extends React.Component {
    constructor(props) {
        super(props);

        this.state = {
            filters:this.props.filters || [],
            properties:this.props.properties || [],
            data:[]
        };

        this.myRef = React.createRef()


    }

    componentDidMount() {
    }


    fetchData(parameters){
        //send ajax request with parameters
        //hand response to json
        //set json to state
        console.log(parameters)
    }

    render() {
        //const json = this.fetchData();
        const {data}=this.state
        const FAKE_JSON = {
            pagination:{
                pageSize:2,
                rowsCount:99,
            },
            fields : [
                //{ name:'', fieldName:'id' },
                { name:'Name', fieldName:'userName' },
                { name:'Email', fieldName:'email' },
                { name:'Country', fieldName:'country' },
                /*{ name:'Commerical Zone', fieldName:'country' },
                { name:'Commerical Region', fieldName:'country' },
                { name:'City', fieldName:'country' },
                { name:'Employee', fieldName:'country' },
                { name:'Enrollments', fieldName:'country' },
                { name:'Successful', fieldName:'country' },
                { name:'Unsuccessful', fieldName:'country' },
                { name:'In Progress', fieldName:'country' },
                { name:'Not Started', fieldName:'country' },
                { name:'Average Final Score', fieldName:'country' },
                { name:'Badges', fieldName:'country' },
                { name:'Posts', fieldName:'country' },
                { name:'Total Time Spent', fieldName:'country' },
                { name:'Last Login', fieldName:'country' },*/
            ],
            data : [
                { id:'a0', test1:'t1', userName:'The Honor', email:'honor@example.com', country:'US' },
                { id:'a1', test1:'t11', userName:'Judy Sim', email:'audit@example.com', country:'France' },
                { id:'a2', test1:'t1111', userName:'verified', email:'verified@example.com', country:'Brazil' },
            ],
            totalData : {
                email:'3'
            }
        }

        const json = FAKE_JSON
        return (
            <section ref={this.myRef} className="analytics-wrapper learner">
                <div className="report-wrapper">

                    <div className="last-update">
                        <i className="fa fa-history"></i>{gettext('Please, note that these reports are not live. Last update:')}{this.props.last_update}
                    </div>
                    <Toolbar onChange={this.fetchData.bind(this)} filters={this.props.filters}
                             properties={this.props.filters}/>
                    <DataList className="data-list" defaultLanguage={this.props.defaultLanguage} enableRowsCount={true} {...json}/>

                </div>
            </section>
        )
    }
}
