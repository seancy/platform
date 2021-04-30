/* global gettext */
/* eslint react/no-array-index-key: 0 */

import PropTypes from 'prop-types';
import React from 'react';

export class QuestionMark extends React.Component {
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

QuestionMark.propTypes = {
    tooltip: PropTypes.string,
};
