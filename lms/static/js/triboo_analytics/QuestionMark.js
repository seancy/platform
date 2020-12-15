/* global gettext */
/* eslint react/no-array-index-key: 0 */

import PropTypes from 'prop-types';
import React from 'react';
import ReactDOM from 'react-dom'

export class QuestionMark extends React.Component {
    constructor(props) {
        super(props);
        this.state = { username: '' };

        this.handleResize = this.handleResize.bind(this);

        window.addEventListener('resize', this.handleResize)

        setTimeout(this.handleResize,500)
    }

    handleResize(e) {
        let docWidth = document.body.offsetWidth,
            elementX = this.refs.root.getBoundingClientRect().x,
            offsetVal = 0;
        if (docWidth - elementX < 100) {
            offsetVal = docWidth-elementX
        }
        this.refs.root.querySelector('.after').style.marginLeft = `-${offsetVal}px`
    }

    render() {

        return (
            <div className="wrapper">
            <span ref="root" className="icon-question">
                <span className="before"></span>
                <i className="fas fa-question-circle"></i>
                <span className="after">{this.props.tooltip}</span>
            </span>
            </div>
        );
    }
}

QuestionMark.propTypes = {
    tooltip: PropTypes.string,
};
