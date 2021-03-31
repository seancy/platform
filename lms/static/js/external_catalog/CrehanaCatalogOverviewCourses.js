import React from "react";
import InfiniteScroll from "react-infinite-scroll-component";
import {formatDate} from "js/DateUtils";


class CrehanaCourseCard extends React.Component {
    constructor(props) {
        super(props);
        this.state = {}
    }

    render() {
        const {image, duration, languages, rating, title, url} = this.props;
        var langs = [];
        for(var i = 0; i < languages.length; i++) {
            langs.push(<img src={`/static/images/country-icons/${languages[i]}.png`}/>);
        }
        var hhmmArray = new Date(duration*1000).toISOString().substr(11, 5).split(":");
        const hh = parseInt(hhmmArray[0]);
        const mm = parseInt(hhmmArray[1]);
        return (
            <div className="courses-listing-item">
                <a href={`courses/crehana_catalog?next_url=${url}`} target="_blank">
                    <div className="card-image-wrapper" style={{backgroundImage:'url('+image+')'}}>
                        {langs}
                    </div>
                    <div className="extra">
                        <ul className="tags">
                            <li className={'active_crehana'}>{gettext("CREHANA")}</li>
                        </ul>
                        <span className="star-score">
                            <i className="fa fa-star"></i>
                            <span className="score">{parseFloat(rating).toFixed(2)}</span>
                        </span>
                    </div>
                    <h4 title={title}>{title}</h4>
                    <div className="sub-info">
                        {duration && (<span className="duration">
                            <i className="fal fa-clock"></i>
                            <span>{ hh === 0 ? gettext('${min} min').replace('${min}', mm) : gettext('${hour} h $(min) m').replace('${hour}', hh).replace('$(min)', mm)}</span>
                        </span>)}
                    </div>
                </a>
            </div>
        )
    }
}


class EdflexCourseCard extends React.Component {
    constructor(props) {
        super(props);
        this.state = {}
    }

    render() {
        const {image, duration, language, rating, title, publication_date, url, type} = this.props;
        var hhmmArray = new Date(duration*1000).toISOString().substr(11, 5).split(":");
        const hh = parseInt(hhmmArray[0]);
        const mm = parseInt(hhmmArray[1]);

        return (
            <div className="courses-listing-item">
                <a href={url} target="_blank">
                    <div className="card-image-wrapper" style={{backgroundImage:'url('+image+')'}}>
                        <img src={`/static/images/country-icons/${language}.png`}/>
                    </div>
                    <div className="extra">
                        <ul className="tags">
                            <li className={'active'}>{gettext("EDFLEX")}</li>
                            <li>{gettext(type)}</li>
                        </ul>
                        <span className="star-score">
                            <i className="fa fa-star"></i>
                            <span className="score">{parseFloat(rating).toFixed(2)}</span>
                        </span>
                    </div>
                    <h4 title={title}>{title}</h4>
                    <div className="sub-info">
                        {duration && (<span className="duration">
                            <i className="fal fa-clock"></i>
                            <span>{ hh === 0 ? gettext('${min} min').replace('${min}', mm) : gettext('${hour} h $(min) m').replace('${hour}', hh).replace('$(min)', mm)}</span>
                        </span>)}
                        <span className="date-str">
                            <i className="fal fa-calendar-week"></i>
                            <span>{formatDate(new Date(publication_date), this.props.systemLanguage || 'en', '')}</span>
                        </span>
                    </div>
                </a>
            </div>
        )
    }
}


class OverviewCoursesContainer extends React.Component {
    constructor(props) {
        super(props)
    }

    fireIndentClick() {
        const {onIndentClick} = this.props;
        onIndentClick && onIndentClick();
    }

    fireNext(){
        const {onNext}=this.props;
        onNext && onNext();
    }

    render() {
        try {
            const {crehana_courses, edflex_courses, crehana_title, edflex_title} = this.props;
            const crehana_items = [];
            const edflex_items = [];
            JSON.parse(crehana_courses).forEach((course, index) => {
                crehana_items.push(
                    <CrehanaCourseCard key={`id-${index}`}
                                {...course}
                    />
                )
            });

            JSON.parse(edflex_courses).forEach((course, index) => {
                edflex_items.push(
                    <EdflexCourseCard key={`id-${index}`}
                                {...course}
                    />
                )
            });

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
        } catch(e) {
            console.error('Error  :  ', e);
        }
    }
}

export {OverviewCoursesContainer}
