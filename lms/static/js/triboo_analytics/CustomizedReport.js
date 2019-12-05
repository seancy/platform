/* eslint-disable react/no-danger, import/prefer-default-export */
import React from 'react';
import PropTypes from 'prop-types';

export class CustomizedReport extends React.Component {
    constructor(props) {
        super(props);
        /*this.state = {
            isActive: false,
            selectedItem: props.languages.find(p => p.code == props.defaultLanguageCode)
        };
        this.togglePanel = this.togglePanel.bind(this)
        this.closePanel = this.closePanel.bind(this)

        document.addEventListener('click', () => {
            this.closePanel()
        })*/

        this.state = {
            hideCourseReportSelect: false
        };
        $(() => {
            setTimeout(() => {
                $(this.refs.course_selected).select2({
                    multiple: true
                });
            }, 300)

        })

        /*setTimeout(()=>{

        },3500)*/

    }

    /*togglePanel() {
        setTimeout(() => {
            this.setState(prevState => ({isActive: true}))
        }, 20)
    }

    closePanel() {
        this.setState({
            isActive: false
        })
    }

    selectItem(language) {
        this.setState({
            selectedItem: language
        })
        this.closePanel();
        this.props.callback(language.code);
    }*/

    recreateCourseSelect(e) {
        let courseReportType = this.props.report_types.find(p => p.type == e.target.value).courseReportType,
            isMultiple = true, $courseSelected = $(this.refs.course_selected);
        $courseSelected.data('select2') && $courseSelected.select2("destroy")
        if (courseReportType == 'multiple' || courseReportType == 'single') {
            isMultiple = courseReportType == 'single' ? false : true;
            $courseSelected.select2({
                multiple: isMultiple
            });
            this.setState({
                hideCourseReportSelect:false
            })
        }else{
            this.setState({
                hideCourseReportSelect:true
            })
        }
    }

    render() {
        const {translation, report_types, courses, user_properties, export_formats} = this.props;
        /*let {isActive, selectedItem} = this.state;
        const getIcon = (code) => {
            return `${staticImageUrl}${code}.png`
        }*/

        return (
            <React.Fragment>
                {/*<select defaultValue={selectedItem.code}>
                    {languages.map(({code, name}) => {
                        return (<option key={code} value={code}>{name}</option>)
                    })}
                </select>
                <div className={'select-selected' + (isActive ? ' select-arrow-active' : '')} onClick={this.togglePanel}>
                    <img src={getIcon(selectedItem.code)} alt={selectedItem.name}/>
                    <span>{selectedItem.name}</span>
                </div>
                <ul className={'select-items' + (!isActive ? ' select-hide' : '')}>
                    {languages.map((language) => {
                        let {code, name} = language
                        return (
                            <li key={code} className={(code == selectedItem.code?'same-as-selected':'')} onClick={this.selectItem.bind(this, language)}><img src={getIcon(code)} alt={name}/><span>{name}</span></li>
                        )
                    })}
                </ul>*/}
                <div>
                    <label htmlFor="report_type">{translation.report_type}</label>

                    {/*<Select options={report_types.map(({type,title})=>({label:title,value:type}))}/>*/}
                    <select name="report_type" id="report_type" onChange={this.recreateCourseSelect.bind(this)}>
                        {report_types.map(({type, title}) => {
                            return <option key={type} value={type}>{title}</option>
                        })}
                    </select>
                </div>
                <div className={this.state.hideCourseReportSelect?'hide':''}>
                    <label htmlFor="course_selected">{translation.course}</label>
                    <select id="course_selected" ref="course_selected">
                        {courses.map(({cid, course_title}) => {
                            return <option key={cid} value={course_title}>{course_title}</option>
                        })}
                    </select>
                </div>
                {/*<section className="search-form">
                    <div id="filter-form" role="search" aria-label="course" className="wrapper-search-context">
                        <form className="table-filter-form">
                            <button type="submit" className="filter-submit">{translation.filter}</button>
                            <button type="submit" id="clear-all-filters" className="clear-filters">
                                <i className="fa fa-refresh icon"></i>{translation.reset}
                            </button>
                        </form>
                    </div>
                    <div id="filter-bar" className="filters hide-phone is-collapsed"></div>
                    <div id="filter-message" className="search-status-label"></div>
                </section>
                <div className="table-user-properties-form-customized">
                    <div id="user-properties">
                        {user_properties.map(({key, value}) => {
                            let idStr = "id_selected_properties_"+key;
                            return (
                                <li key={key}>
                                    <input type="checkbox" name="selected_properties"
                                        id={idStr} value={value}/>
                                    <label htmlFor={idStr}>{value}</label>
                                </li>
                            )
                        })}
                    </div>
                    <div className="table-export-customized">
                        <p>{translation.format}</p>
                        <div id="table-export-selection">
                            {export_formats.map((formatName) => {
                                let idStr = "id-" + formatName;
                                return (<li key={formatName}>
                                    <input type="radio" name="format" id={idStr}/>
                                    <label htmlFor={idStr}><code>{formatName}</code></label>
                                </li>)
                            })}
                        </div>
                        <p id="export-notification"></p>
                        <p id="export-error"></p>
                    </div>
                    <input type="submit" value={translation.go}/>
                </div>*/}

            </React.Fragment>
        )
    }
}

CustomizedReport.propTypes = {
    translation: PropTypes.shape({
        report_type: PropTypes.string,
        course: PropTypes.string,
        filter: PropTypes.string,
        reset: PropTypes.string,
        format: PropTypes.string,
        go: PropTypes.string
    }),
    report_types: PropTypes.arrayOf(PropTypes.shape({
        type: PropTypes.string,
        title: PropTypes.string
    })),
    courses: PropTypes.arrayOf(PropTypes.shape({
        cid: PropTypes.string,
        course_title: PropTypes.string
    })),
    user_properties: PropTypes.arrayOf(PropTypes.shape({
        key: PropTypes.string,
        value: PropTypes.string
    })),
    export_formats: PropTypes.array,

};
