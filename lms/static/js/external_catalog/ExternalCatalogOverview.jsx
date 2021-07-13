import React from "react"
import InfiniteScroll from "react-infinite-scroll-component"
import {CrehanaCourseCard, EdflexCourseCard, AnderspinkArticleCard } from './ExternalCourseCard'


export function ExternalCatalogOverview (props) {
    const {edflex_title, crehana_title, anderspink_title, external_catalogs} = props;
    return (
        <section className="find-courses">
            <section className="banner">
                <section className="welcome-wrapper">
                    <h2>{gettext("Explore")}</h2>
                    <Switcher />
                </section>
                <Categories edflex_title={edflex_title} crehana_title={crehana_title} anderspink_title={anderspink_title} external_catalogs={external_catalogs}/>
            </section>
            <div className="courses-wrapper overview_margin">
                <OverviewCoursesContainer {...props} />
            </div>
        </section>
    )
}

function Switcher () {
    return (
        <a href="/courses">
            <span className="switcher">
                <span className="round-button">{gettext("Internal")}</span>
                <span className="round-button active">{gettext("External")}</span>
            </span>
        </a>
    )
}

function Categories ({edflex_title, crehana_title, anderspink_title, external_catalogs}) {
    return <div className="category_tabs">
        <a href="/all_external_catalog" className="current_category">{gettext("All")}</a>
        {external_catalogs.map(item =>  <a key={item.name} href={item.to} className="categories">{item.name == "EDFLEX" ? edflex_title : item.name == "CREHANA" ? crehana_title : anderspink_title}</a>)}
    </div>
}

class OverviewCoursesContainer extends React.Component {
    constructor (props) {
        super(props)
    }

    fireIndentClick () {
        const {onIndentClick} = this.props
        onIndentClick && onIndentClick()
    }

    fireNext () {
        const {onNext} = this.props
        onNext && onNext()
    }

    render () {
        try {
            const {crehana_courses, edflex_courses, anderspink_courses, crehana_title, edflex_title, anderspink_title, external_catalogs, language} = this.props;
            const crehana_items = [];
            const edflex_items = [];
            const anderspink_items = [];
            const catalogContent = []


            if(crehana_courses){
                crehana_courses.forEach((course, index) => {
                crehana_items.push(
                    <CrehanaCourseCard key={`id-${index}`}
                                {...course} systemLanguage={language}
                    />
                )
                });
                catalogContent["CREHANA"] = crehana_items
            }

            if(edflex_courses){
                edflex_courses.forEach((course, index) => {
                edflex_items.push(
                    <EdflexCourseCard key={`id-${index}`}
                                {...course} systemLanguage={language}
                    />
                )
                });
                catalogContent["EDFLEX"] = edflex_items

            }
            
            if(anderspink_courses){

                anderspink_courses.forEach((article, index) => {
                   anderspink_items.push(
                       <AnderspinkArticleCard key={`id-${index}`}
                                   {...article} systemLanguage={language}
                       />
                   )   
               });
               catalogContent["ANDERSPINK"] = anderspink_items

            }

            return (

                <main className="course-container">
                    {external_catalogs.map(catalog => <React.Fragment key={catalog.name}>
                        <div>
                        <span className={'category_name'}>{catalog.name == "EDFLEX" ? edflex_title : catalog.name == "CREHANA" ? crehana_title : anderspink_title}</span>
                        <span className={'view_all_button'}>
                            <a className={'button_underline'} href={catalog.to}>{gettext("View all")}</a> &gt;
                        </span>
                    </div>
                    <InfiniteScroll
                        className={'courses-listing'}
                        dataLength={catalogContent[catalog.name].length}
                    >
                        {catalogContent[catalog.name]}
                    </InfiniteScroll>
                    </React.Fragment>)}
                </main>
            )
        } catch (e) {
            console.error('Error  :  ', e)
        }
    }
}


class Modal extends React.Component {
    constructor (props) {
        super(props)
    }

    render () {
        const {status} = this.props, stopPropagation = e => {
            e.preventDefault()
            e.stopPropagation()
        }
        return <React.Fragment>
            <div className={`confirm-modal${status ? '' : ' hide-status'}`}>
                <div className="content-area">
                    <i className="fal fa-toggle-on"></i>
                    <div>
                        <h4>{gettext("External Resources")}</h4>
                        <p>{gettext("You are switching to the external resources catalog which is a collection of public resources, third party and external content. Please note that although the catalog is free to browse, content requiring a paid subscription, or specific authorization, will not be provided by default via this platform. Please contact your organization with any specific questions. Do you wish to continue?")}</p>
                    </div>
                </div>
                <div className="actions">
                    <a href="#" className='cancel' onClick={e => {
                        const {onCancel} = this.props
                        onCancel && onCancel()
                        stopPropagation(e)
                    }}>{gettext("Cancel")}</a>
                    <a href="#" className={`confirm${this.props.transfering ? ' disabled' : ''}`} onClick={e => {
                        const {onConfirm} = this.props
                        onConfirm && onConfirm()
                        stopPropagation(e)
                    }}>{gettext("Continue")}</a>
                </div>
            </div>
            <div className="cover-bg"></div>
        </React.Fragment>
    }
}

export class ExternalCoursesModal extends React.Component {
    constructor (props) {
        super(props)

        this.state = {
            transfering: false,
            modalStatus: false
        }
    }

    componentDidMount () {
        $('.banner').delegate('.welcome-wrapper a', 'click', (e) => {
            this.setState(state => {
                return {
                    modalStatus: !state.modalStatus
                }
            })
            e.preventDefault()
            e.stopPropagation()
            return false
        })
    }

    render () {
        return (
            <React.Fragment>
                <Modal status={this.state.modalStatus}
                    transfering={this.state.transfering}
                    onCancel={() => {this.setState({transfering: false, modalStatus: false})}}
                    onConfirm={() => {this.setState({transfering: true}); window.location = this.props.external_button_url}}
                />
            </React.Fragment>
        )
    }
}
