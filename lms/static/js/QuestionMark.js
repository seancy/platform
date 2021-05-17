/* global gettext */
/* eslint react/no-array-index-key: 0 */

import PropTypes from 'prop-types';
import React from 'react';
import ReactDOM from 'react-dom'

class Notification extends React.Component {
    constructor(props) {
        super(props);
    }

    disposeButtonClick(e, callbackName){
        const {element=$('#page-notification')[0]}=this.props, unmount = ()=>ReactDOM.unmountComponentAtNode(element), callback = this.props[callbackName];
        callback ? (callback(e)!==false && unmount()) : unmount();
    }

    render() {
        const {type,title, message, cancelText, confirmText}=this.props,
            iconObj = {warning:'question', error:'exclamation-triangle', info:'check'}

        return <div className={`wrapper wrapper-notification wrapper-notification-${type||"warning"} is-shown`}
                    id={`notification-${type||"warning"}`} aria-hidden="false" aria-labelledby="notification-warning-title" tabIndex="-1"
                    aria-describedby="notification-warning-description" role="dialog">
            <div className="notification">
                <a href="#" className="fal fa-times action action-close" onClick={e=>this.disposeButtonClick(e, 'onCancel')}></a>
                <div>
                    <span className={`feedback-symbol fa fa-${iconObj[type] || 'warning'}`} aria-hidden="true"></span>
                    <div className="copy">
                        {title && <h2 className="title">{title}{/*You've made some changes*/}</h2>}
                        <p className="message" dangerouslySetInnerHTML={{ __html: (message || '') }}></p>
                    </div>
                </div>
                <nav className={"nav-actions" + ((cancelText == null && confirmText == null) ?' hidden':'')}>
                    <ul>
                        <li className="nav-item">
                            <button className="action-secondary" onClick={e=>this.disposeButtonClick(e, 'onCancel')}>{cancelText || 'Cancel'}</button>
                        </li>
                        <li className="nav-item">
                            <button className="action-primary" onClick={e=>this.disposeButtonClick(e, 'onConfirm')}>{confirmText||'Confirm'}</button>
                        </li>
                    </ul>
                </nav>
            </div>
        </div>

        /*
        return (
            <div className="wrapper">
            <span ref="root" className="icon-question">
                <span className="before"></span>
                <i className="fas fa-question-circle"></i>
                <span className="after" dangerouslySetInnerHTML={{__html:this.props.tooltip}}></span>
            </span>
            </div>
        );*/
    }
}

class QuestionMark extends React.Component {
    constructor(props) {
        super(props);
        this.myRef = React.createRef();

        this.handleResize = this.handleResize.bind(this)
    }

    handleResize(e) {
        if (!this.myRef.current) return

        const docWidth = document.body.offsetWidth
        const elementX = this.myRef.current.getBoundingClientRect().x
        if (docWidth - elementX < 100){
          this.myRef.current.classList.add('icon-question--left')
        } else {
          this.myRef.current.classList.remove('icon-question--left')
        }
    }

    componentDidMount () {
      window.addEventListener('resize', this.handleResize)
      this.handleResize()
    }

    componentWillUnmount () {
      window.removeEventListener('resize', this.handleResize)
    }

    render() {
        return (
            <div className="wrapper">
            <span ref={this.myRef} className="icon-question">
                <span className="before"></span>
                <i className="fas fa-question-circle"></i>
                <span className="after" dangerouslySetInnerHTML={{__html:this.props.tooltip}}></span>
            </span>
            </div>
        );
    }
}

import Dropdown from 'lt-react-dropdown'


window.LearningTribes = window.LearningTribes || {};

const _Notification = function (obj) {
    var {element }= obj;
    if (element == null){
        var $el = $('#page-notification')
        if ($el.length <= 0) {
            ($('#admin-panel') || $('body')).append('<div id="page-notification"></div>')
            $el = $('#page-notification')
        }
        element = $el[0]
    }
    ReactDOM.render(
      React.createElement(Notification, obj, null),
      element
    );
}
//window.LearningTribes.Notification = window.LearningTribes.Notification || {}
var _NFactory = function(type) {
    return function(obj) {
        //:'warning'
        new _Notification(_.extend(obj, {type}));
    }
}
window.LearningTribes.Notification = {
    Warning:_NFactory('warning'),
    Error:_NFactory('error'),
    Info:_NFactory('info'),
}
//['warning', 'error', 'info']
/*window.LearningTribes.Notification.Warning = function(obj) {
    new _Notification(_.extend(obj, {type:'warning'}));
}
window.LearningTribes.Notification.Error = function(obj) {
    new _Notification(_.extend(obj, {type:'error'}));
}
window.LearningTribes.Notification.Info = function(obj) {
    new _Notification(_.extend(obj, {type:'info'}));
}*/

export {Notification, QuestionMark, Dropdown, ReactDOM, React}

QuestionMark.propTypes = {
    tooltip: PropTypes.string,
};
