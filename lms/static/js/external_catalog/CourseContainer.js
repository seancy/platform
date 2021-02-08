import React from "react";
import InfiniteScroll from "react-infinite-scroll-component";
import {formatDate} from "js/DateUtils";

class CourseCard extends React.Component {
    constructor(props) {
        super(props);
        this.state = {}
    }

    render() {
        const {image_url, publication_date, language, rating, title, duration, url, type} = this.props;
        return (
            <div className="courses-listing-item">
                <a href={url} target="_blank">
                    <div className="card-image-wrapper">
                        <img src={image_url} alt=""/>
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
                            <span>{ gettext('${min} min').replace('${min}', parseFloat(duration / 60).toFixed(0))} </span>
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

class CourseContainer extends React.Component {
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
        const {data, hasMore, recordCount, searchString, firstTimeLoading} = this.props;
        const items = [];
        data.forEach((course, index) => {
            items.push(
                <CourseCard key={`id-${index}`}
                            systemLanguage={this.props.language}
                            {...course}
                />
            )
        });
        const skeletons = Array(12).fill(1).map((val,index)=><div key={'index'+index} className="skeleton"></div>);

        return (
            <main className="course-container">
                <div><i className={`fal fa-indent ${this.props.indent ? 'hidden' : ''}`}
                      onClick={this.fireIndentClick.bind(this)}></i>{firstTimeLoading ? '' :
                    (recordCount ? gettext('${recordCount} resources found').replace('${recordCount}', recordCount) : gettext('We couldn\'t find any results for "${searchString}".').replace('${searchString}', searchString) )}
                </div>
                <InfiniteScroll
                    className={'courses-listing'}
                  dataLength={items.length}
                  next={this.fireNext.bind(this)}
                  hasMore={hasMore}
                  loader={<h5><i className={'fal fa-spinner fa-spin'}></i><span>Loading...</span></h5>}
                >
                    {data.length<=0 && firstTimeLoading ? skeletons : items}
                </InfiniteScroll>
            </main>
        )
    }
}

export {CourseContainer}
