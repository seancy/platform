import React from 'react';
import Dropdown from 'se-react-dropdown'
import {get, pick} from 'lodash'

//for leader board page.
export class LeaderBoard extends React.Component {
    constructor(props) {
        super(props);

        this.state = {
            cacheObj:{},
            isLoading: false,
            ...pick(props, ['lastUpdate', 'totalUser', 'mission', 'list'])
        };
    }

    componentDidMount() {
        this.fetchData('')
    }

    getPeriodFilter () {
        const months = [
            {text: gettext('All'), value: 'all'},
            {text: gettext('Week'), value: 'week'},
            {text: gettext('Month'), value: 'month'},
        ]
        return <Dropdown sign='caret' data={months} onChange={this._handlePeriodChange.bind(this)}/>
    }

    _handlePeriodChange(item){
        this.fetchData(item.value)
    }

    fetchData(period){
        const {cacheObj}=this.state
        this.setState({isLoading:true})
        if (!cacheObj[period]){
            fetch(`/analytics/leaderboard/json/?period=${period}`)
                .then(res=>res.json())
                .then(({list, mission, lastUpdate, totalUser})=>{
                    let obj = { list, lastUpdate, mission, totalUser, isLoading:false}
                    this.setState(obj)
                    this.setState(prevState=>{
                        const tempObj=prevState.cacheObj
                        tempObj[period]={list, lastUpdate}
                        return {
                            cacheObj:tempObj
                        }
                    })
                })
        }else{
            const currentObj = cacheObj[period]
            let obj = { list: currentObj.list, lastUpdate:currentObj.lastUpdate, isLoading:false}
            this.setState(obj)
        }

    }

    getRank() {
        const {list, totalUser, lastUpdate} = this.state;

        const forceLastItemActive = (index)=>{
            const isForceActive = list.filter(p=>p.Active).length <= 0
            // return index == list.length - 1 && isForceActive ? true : false
            return false
        }

        return <div className={'rank' + (this.state.isLoading ?' loading':'')}>
            <table>
                <thead>
                <tr>
                    <th>{gettext('Position')}</th>
                    <th>{gettext('Name')}</th>
                    <th>{gettext('Points')}</th>
                </tr>
                </thead>
                <tbody>
                {list.map((item, index) => {
                    return (<tr key={index} {...(item.Active || forceLastItemActive(index) ? {className:'active'}:{})}>
                        <td className={item.OrderStatus}>{`${item.Rank}.`}</td>
                        <td><img src={`${item.Portrait}`}
                                 alt=""/><b>{item.Name}</b><time>{item.DateStr}</time></td>
                        <td><strong>{item.Points} {gettext('pt.')}</strong></td>
                    </tr>)
                })}
                </tbody>
            </table>
            <div className="loading-block"><i className="fas fa-spinner fa-spin"></i></div>
            <div className="last-update">
                <i className="fa fa-user"></i>
                <small>{gettext('There are currently ${totalUser} learners. Last update: ${lastUpdate}.').replace(/(\${totalUser})/, totalUser).replace(/(\${lastUpdate})/, lastUpdate)}</small>
            </div>
        </div>
    }

    getMission() {
        const getMissionItem = (key) => {
            const originalValue = get(this.state, `mission.${key}`, '')
            const {message, times} = get(this.props, `missionConfig.${key}`, {})
            const value = originalValue * times
            return {message, times, value}
        }
        return <aside className="mission">
            <h2>{gettext('Missions')}</h2>
            <div className="table-wrapper">
                <table>
                    <thead><tr><th>{gettext('Missions')}</th><th>{gettext('Points')}</th></tr></thead>
                    <tbody>
                    {Object.keys(this.props.missionConfig).map(key => {
                        const {message, times, value} = getMissionItem(key)
                        return <tr key={key}>
                            <td>
                                <div>{message}</div>
                                <small>{gettext('You have won ${value} point(s).').replace(/(\${value})/, value)}</small>
                            </td>
                            <td>+{times}</td>
                        </tr>
                    })}
                    </tbody>
                </table>
            </div>
        </aside>
    }

    render() {
        return (
            <React.Fragment>
                <section className="banner">
                    <section className="welcome-wrapper">
                        <h2>{gettext("Leaderboard")}</h2>
                    </section>
                </section>
                <section className="headline-lists">
                    <section className="headline">
                        <h2>{gettext('Leaderboard')}</h2>
                        <div className="period">
                            <span>{gettext('Ranking')}</span>
                            <i>|</i>
                            {this.getPeriodFilter()}
                        </div>

                    </section>
                    <section className="lists">
                        {this.getRank()}
                        {this.getMission()}
                    </section>
                </section>

            </React.Fragment>
        )
    }
}

//for dashboard's leader side board
export class LeaderSideBoard extends React.Component {
    constructor(props) {
        super(props);

        this.state = {
            list:[]
        }
    }

    componentDidMount() {
        this.fetchData('', 5)
    }

    fetchData(period, top){
        fetch(`/analytics/leaderboard/json/?period=${period}&top=${top}`)
            .then(res=>res.json())
            .then(({list})=>{
                this.setState({ list })
            })
    }

    render() {
        return (
            <React.Fragment>
                <div className="title">
                    <h3>{gettext('Leaderboard')}</h3>
                    <a href="/analytics/leaderboard/">{gettext('Show more')} <i className="far fa-chevron-right"></i> </a>
                </div>
                <div className="board-content">
                    <table>
                        <thead>
                        <tr>
                            <th>{gettext('Position')}</th>
                            <th>{gettext('Name')}</th>
                            <th>{gettext('Points')}</th>
                        </tr>
                        </thead>
                        <tbody>
                        {this.state.list.map((item, index) => {
                            return (<tr key={index}>
                                <td><strong>{`${index + 1}.`}</strong></td>
                                <td><img src={`${item.Portrait}`}
                                         alt=""/>{item.Name}</td>
                                <td><strong>{item.Points}</strong> <span>points</span></td>
                            </tr>)
                        })}
                        </tbody>
                    </table>
                </div>
            </React.Fragment>
        )
    }
}
