import React from "react";

const LastUpdate = function (props) {
    return (<p className="last-update">
        <span
            className="fal fa-sync-alt"></span>{gettext('Please, note that these reports are not live. Last update:')} {props.last_update}
    </p>)
}

export {LastUpdate}
