import React from "react";
import Cookies from "js-cookie";
import {SideBar} from './Sidebar'
import {CourseContainer} from './CourseContainer'

class Modal extends React.Component{
    constructor(props) {
        super(props);
    }

    render() {
        const {status}=this.props, stopPropagation=e=>{
            e.preventDefault();
            e.stopPropagation();
        };
        return <React.Fragment>
            <div className={`confirm-modal${status?'':' hide-status'}`}>
                    <div className="content-area">
                        <i className="fal fa-toggle-on"></i>
                        <div>
                            <h4>{gettext("External Resources")}</h4>
                            <p>{gettext("You are switching to the external resources catalog which is a collection of public resources, third party and external content. Please note that although the catalog is free to browse, content requiring a paid subscription, or specific authorization, will not be provided by default via this platform. Please contact your organization with any specific questions. Do you wish to continue?")}</p>
                        </div>
                    </div>
                    <div className="actions">
                        <a href="#" className='cancel' onClick={e=>{
                            const {onCancel}=this.props;
                            onCancel && onCancel();
                            stopPropagation(e)
                        }}>{gettext("Cancel")}</a>
                        <a href="#" className={`confirm${this.props.transfering?' disabled':''}`} onClick={e=>{
                            const {onConfirm}=this.props;
                            onConfirm && onConfirm();
                            stopPropagation(e)
                        }}>{gettext("Continue")}</a>
                    </div>
                </div>
                <div className="cover-bg"></div>
        </React.Fragment>
    }
}

class Courses extends React.Component {
    constructor(props) {
        super(props);

        this.state = {
            transfering: false,
            modalStatus:false
        };
    }

    componentDidMount() {
        $('.banner').delegate('.welcome-wrapper a', 'click', (e)=>{
            this.setState(state=>{
                return {
                    modalStatus: !state.modalStatus
                }
            });
            e.preventDefault();
            e.stopPropagation();
            return false
        })
    }

    render() {
        return (
            <React.Fragment>
                <Modal status={this.state.modalStatus}
                       transfering={this.state.transfering}
                       onCancel={()=>{ this.setState({transfering:false, modalStatus:false}) }}
                       onConfirm={()=>{ this.setState({transfering: true}); window.location = '/external_catalog' }}
                />
            </React.Fragment>
        );
    }
}

class ExternalCatalog extends React.Component {
    constructor(props) {
        super(props);
        let sidebarStatus = true;
        try {
            const triboo = localStorage.getItem('triboo');
            sidebarStatus = triboo === '' ? {} : JSON.parse(triboo).sidebarStatus;
        } catch (e) {
            localStorage.setItem('triboo', {})
        }

        this.state = {
            firstTimeLoading:true,
            sidebarStatus: sidebarStatus,
            sidebarData:{
                courseTypes: [],
                courseCategories: [],
                languages: []
            },
            courses: [],
            searchParameters: {},
            isFetching: false,
            hasMore: false,
            recordCount: 0,
            searchString: '',
            pageSize: 60,
            pageNo: 1
        };
        this.fetchData = this.fetchData.bind(this);
    }

    componentDidMount() {
        this.fetchSidebarData();
        this.fetchData({}).then(()=>{
            this.setState({firstTimeLoading:false})
        });
    }

    fetchSidebarData() {
        fetch("/external_catalog", {
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': Cookies.get('csrftoken'),
            },
        })
            .then(res => res.json())
            .then(
                (result) => {
                    this.setState({
                        sidebarData: this.parseSidebarData(result.facet_content)
                    })
                }
            )
    }

    parseSidebarData({type, categories, language}){
        const sortFn = (a, b) => {
            if (a.text < b.text) {
                return -1;
            }
            if (a.text > b.text) {
                return 1;
            }
            return 0;
        };
        const languageNameObj = {
            fr: gettext('French'), en: gettext('English'), es: gettext('Spanish'),
            pt: gettext('Portuguese'), it: gettext('Italian'), de: gettext('German'),
            zh: gettext('Mandarin')
        };
        language.forEach(function(item, index, arr) {
            if(item.value == null) {
                arr.splice(index, 1);
            }
        });
        return {
            courseTypes: type.map(p => ({...p, text: gettext(p.value), label: p.count})),
            courseCategories: categories.sort(sortFn),
            languages: language.map(p => ({text: languageNameObj[p.value], value: p.value, label: p.count}))
        }
    }

    fetchData(p) {
        const {filterValue, topic, selectedCourseTypes, selectedLanguages} = p || this.state.searchParameters;
        const {pageSize, pageNo} = this.state;
        const obj = {
            search_content: filterValue || '',
            filter_content: {},
            page_size: pageSize,
            page_no: pageNo
        };
        if (topic && topic.value) {
            obj.filter_content['categories'] = topic.text
        }

        if (selectedCourseTypes && selectedCourseTypes.length > 0) {
            obj.filter_content['type'] = selectedCourseTypes.map(p => p.value)
        }
        if (selectedLanguages && selectedLanguages.length > 0) {
            obj.filter_content['language'] = selectedLanguages.map(p => p.value)
        }
        this.setState({isFetching:true});
        return fetch("/external_catalog/courses", {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': Cookies.get('csrftoken'),
            },
            body: JSON.stringify(obj),
        })
            .then(res => res.json())
            .then(
                (result) => {
                    const {facet_content,course_list,course_count,search_content}=result;
                    this.setState(prev=>{
                        return {
                            isFetching:false,
                            recordCount: course_count,
                            searchString: search_content,
                            hasMore: this.getHasMore(course_count),
                            sidebarData: this.parseSidebarData(facet_content),
                            courses: prev.courses.concat(course_list)
                        }
                    });
                },
            )
            .catch(error => {
                this.setState({
                    recordCount: 0,
                    searchString: '',
                    hasMore: false,
                    sidebarData: {},
                    courses: []
                });
                console.error('Error:', error);
            })
    }

    startFetch(searchParameters){
        this.setState({
            pageNo:1,
            searchParameters,
            courses:[]
        },this.fetchData)
    }

    updateSidebarDisplayStatus(sidebarStatus) {
        this.setState({sidebarStatus}, ()=>{
            localStorage.setItem('triboo', JSON.stringify({sidebarStatus}))
        })
    }

    getHasMore(course_count){
        const {pageSize, pageNo} = this.state;
        return ((pageSize * pageNo) < course_count)
    }

    fetchMoreData() {
        if (this.getHasMore(this.state.recordCount) && !this.state.isFetching) {
            this.setState(() => {
                return {pageNo: this.state.pageNo + 1}
            }, this.fetchData)
        }
    }

    render() {
        const {sidebarStatus, courses, sidebarData} = this.state;
        const Switcher = props => {
            return <a href="/courses"><span className="switcher"><span className="round-button">{gettext("Internal")}</span><span className="round-button active">{gettext("External")}</span></span></a>
        };
        return (
            <section className="find-courses">
                <section className="banner">
                    <section className="welcome-wrapper">
                        <h2>{gettext("Explore")}</h2>
                        <Switcher/>
                    </section>
                </section>
                <div className="courses-wrapper">
                    <SideBar
                        {...sidebarData}
                        status={this.state.sidebarStatus}
                        onToggle={this.updateSidebarDisplayStatus.bind(this)}
                        onApply={this.startFetch.bind(this)}
                        onChange={this.startFetch.bind(this)}
                    />
                    {/*<Switcher/>*/}
                    <CourseContainer
                        indent={sidebarStatus}
                        {..._.pick(this.state, ['hasMore', 'recordCount', 'searchString', 'firstTimeLoading'])}
                        {..._.pick(this.props, ['language'])}
                        onNext={this.fetchMoreData.bind(this)}
                        onIndentClick={() => this.setState({sidebarStatus: true}, ()=>{
                            localStorage.setItem('triboo', JSON.stringify({sidebarStatus:true}))
                        })}
                        data={courses}
                    />
                </div>
            </section>
        )
    }
}

export {ExternalCatalog, Courses};
