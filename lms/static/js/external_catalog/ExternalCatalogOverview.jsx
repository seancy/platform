import React from "react"
import InfiniteScroll from "react-infinite-scroll-component"
import {CrehanaCourseCard, EdflexCourseCard} from './ExternalCourseCard'


export function ExternalCatalogOverview (props) {
    return (
        <section className="find-courses">
            <section className="banner">
                <section className="welcome-wrapper">
                    <h2>{gettext("Explore")}</h2>
                    <Switcher />
                </section>
                <Categories edflex_title={props.edflex_title} crehana_title={props.crehana_title} />
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

function Categories ({edflex_title, crehana_title}) {
    return <div className="category_tabs">
        <a href="/all_external_catalog" className="current_category">{gettext("All")}</a>
        <a href="/edflex_catalog" className="categories">{edflex_title}</a>
        <a href="/crehana_catalog" className="categories">{crehana_title}</a>
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
            const {crehana_courses, edflex_courses, crehana_title, edflex_title} = this.props
            const crehana_items = []
            const edflex_items = []
            JSON.parse(crehana_courses).forEach((course, index) => {
                crehana_items.push(
                    <CrehanaCourseCard key={`id-${index}`} systemLanguage={this.props.language}
                        {...course}
                    />
                )
            })

            JSON.parse(edflex_courses).forEach((course, index) => {
                edflex_items.push(
                    <EdflexCourseCard key={`id-${index}`} systemLanguage={this.props.language}
                        {...course}
                    />
                )
            })

            return (
                <main className="course-container">
                    <div>
                        <span className={'category_name'}>{edflex_title}</span>
                        <span className={'view_all_button'}>
                            <a className={'button_underline'} href="/edflex_catalog">{gettext("View all")}</a> &gt;
                        </span>
                    </div>
                    <InfiniteScroll
                        className={'courses-listing'}
                        dataLength={edflex_items.length}
                    >
                        {edflex_items}
                    </InfiniteScroll>
                    <div>
                        <span className={'category_name'}>{crehana_title}</span>
                        <span className={'view_all_button'}>
                            <a className={'button_underline'} href="/crehana_catalog">{gettext("View all")}</a> &gt;
                        </span>
                    </div>
                    <InfiniteScroll
                        className={'courses-listing'}
                        dataLength={crehana_items.length}
                    >
                        {crehana_items}
                    </InfiniteScroll>
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
