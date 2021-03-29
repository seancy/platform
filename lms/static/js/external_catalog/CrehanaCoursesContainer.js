import React from "react";
import InfiniteScroll from "react-infinite-scroll-component";


class CourseCard extends React.Component {
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
                            <span>{ hh === 0 ? gettext('${min} min').replace('${min}', mm) : mm === 0 ? gettext('${hour} hours').replace('${hour}', hh): gettext('${hour} h $(min) m').replace('${hour}', hh).replace('$(min)', mm)}</span>
                        </span>)}
                    </div>
                </a>
            </div>
        )
    }
}

class InfiniteManuallyScroll extends InfiniteScroll {
    constructor(props) {
        super(props);
    }

    isElementAtBottom(target, scrollThreshold) {
        return false;
    }
}

class CoursesContainer extends React.Component {
    constructor(props) {
        super(props);
    }

    fireIndentClick() {
        const {onIndentClick} = this.props;
        onIndentClick && onIndentClick();
    }

    fireNext(){
        const {onNext}=this.props;
        document.getElementById('id_show_loading').style.display = 'block';
        document.getElementById('id_show_more_btn').style.display = 'none';
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
                <InfiniteManuallyScroll
                    className={'courses-listing'}
                  dataLength={items.length}
                  next={this.fireNext.bind(this)}
                  hasMore={hasMore}
                >
                    {data.length<=0 && firstTimeLoading ? skeletons : items}
                </InfiniteManuallyScroll>
                <div className="show_more_button_container">
                    <h5 id="id_show_loading" style={{display: 'none'}}><i className={'fal fa-spinner fa-spin'}></i><span> Loading...</span></h5>
                    <a id="id_show_more_btn" style={{display: hasMore ? 'block' : 'none'}} className="show_more_button" onClick={this.fireNext.bind(this)}>{gettext('Show more')}</a>
                </div>
            </main>
        )
    }
}

export {CoursesContainer}
