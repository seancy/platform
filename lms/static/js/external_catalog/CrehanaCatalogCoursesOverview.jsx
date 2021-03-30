import React from "react";
import Cookies from "js-cookie";
import {OverviewCoursesContainer} from './CrehanaCatalogOverviewCourses'


class CrehanaCatalogCoursesOverview extends React.Component {
    constructor(props) {
        super(props);
    }

    render() {
        try {
            const Switcher = props => {
                return <a href="/courses"><span className="switcher"><span
                    className="round-button">{gettext("Internal")}</span><span
                    className="round-button active">{gettext("External")}</span></span></a>
            };
            const Categories = props => {
                return <div className="category_tabs">
                    <a href="/all_external_catalog" className="current_category">{gettext("All")}</a>
                    <a href="/edflex_catalog" className="categories">{this.props.edflex_title}</a>
                    <a href="/crehana_catalog" className="categories">{this.props.crehana_title}</a>
                </div>
            };

            return (
                <section className="find-courses">
                    <section className="banner">
                        <section className="welcome-wrapper">
                            <h2>{gettext("Explore")}</h2>
                            <Switcher/>
                        </section>
                        <Categories/>
                    </section>
                    <div className="courses-wrapper overview_margin">
                        <OverviewCoursesContainer
                            crehana_courses={this.props.crehana_courses}
                            edflex_courses={this.props.edflex_courses}
                            crehana_title={this.props.crehana_title}
                            edflex_title={this.props.edflex_title}
                        />
                    </div>
                </section>
            )
        } catch(e) {
            console.error('Error:', e);
        }
    }
}

export {CrehanaCatalogCoursesOverview};
