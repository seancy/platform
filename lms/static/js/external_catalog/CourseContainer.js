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
                    <div className="card-image-wrapper" style={{backgroundImage:'url('+image_url+')'}}>
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

class InfiniteManuallyScroll extends InfiniteScroll {
    constructor(props) {
        super(props);
    }

    isElementAtBottom(target, scrollThreshold) {
        return false;
    }
}

class CourseContainer extends React.Component {
    constructor(props) {
        super(props);

        this.state = {
            selected_option: '-start_date',
            selected_name: gettext('Most Recent').trim()
        };

        this.all_options = Array(
                ['-start_date', gettext('Most Recent').trim()],
                ['+start_date', gettext('Oldest').trim()],
                ['+display_name', gettext('Title A-Z').trim()],
                ['-display_name', gettext('Title Z-A').trim()],
        );
    }

    fireIndentClick() {
        const {onIndentClick} = this.props;
        onIndentClick && onIndentClick();
    }

    fireNext() {
        const {onNext}=this.props;
        document.getElementById('id_show_loading').style.display = 'block';
        document.getElementById('id_show_more_btn').style.display = 'none';
        onNext && onNext();
    }

    fireOnChange() {
        const {props} = this, {onChange} = props;

        const DELAY = 500;
        if (Date.now()-this.start < DELAY) {
            clearTimeout(this.timer)
        };
        this.start = Date.now();

        this.timer = setTimeout(()=>{
            onChange && onChange(this.state.selected_option);
        }, DELAY);
    }

    applySortType(event) {
        let el = $(event.target);
        this.state.selected_name = el.text();
        let selected_option = el.attr("sort_type");

        this.setState({
            selected_option
        }, this.fireOnChange)
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

        const sort_items = [];
        this.all_options.forEach(
            (option, index) => {
                if (option[0] != this.state.selected_option) {
                    sort_items.push(
                        <a href="#">
                            <div onClick={this.applySortType.bind(this)} class="discovery-sort-item" sort_type={option[0]}>{option[1]}</div>
                        </a>
                    );
                }
            }
        )

        return (
            <main className="course-container">
                <div><i className={`fal fa-indent ${this.props.indent ? 'hidden' : ''}`}
                      onClick={this.fireIndentClick.bind(this)}></i>{firstTimeLoading ? '' :
                    (recordCount ? gettext('${recordCount} resources found').replace('${recordCount}', recordCount) : gettext('We couldn\'t find any results for "${searchString}".').replace('${searchString}', searchString) )}
                    <span id="discovery-courses-sort-options" className="discovery-sort-options">
                        <span>{gettext('Sort by')} |</span>
                        <span class="discovery-selected-item">{this.state.selected_name}<span class="sort_icon"/></span>
                        <div class="discovery-sort-menu">
                            {sort_items}
                        </div>
                    </span>
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

export {CourseContainer}
