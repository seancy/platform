import React from "react";

const LastUpdate = function (props) {
    return (<p className="last-update">
        <span
            className="fal fa-sync-alt"></span>{gettext('Please, note that these reports are not live. Last update:')} {props.last_update}
    </p>)
}

const StatusRender = (value) => {
    let statusConfig = {
        'Not Started': 'not-started-bg',
        'In Progress': 'in-progress-bg',
        'Successful': 'finished-bg'
    }
    return <span className={statusConfig[value]}>{gettext(value)}</span>

}, PercentRender = value => {
    return value && value.indexOf('%') < 0 ? `${value}%` : value

}
export {LastUpdate,StatusRender,PercentRender}
