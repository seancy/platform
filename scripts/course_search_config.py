#!/bin/bash
"""
Elasticsearch config reset utility.
"""
from contentstore.courseware_index import CoursewareSearchIndexer
from search.search_engine_base import SearchEngine
from xmodule.modulestore.django import modulestore


def index_config(index, body):
    """Used for setting index setting and mapping.
    """
    searcher = SearchEngine.get_search_engine(index)
    searcher._es.indices.close(index)
    searcher._es.indices.delete(index)
    searcher._es.indices.create(index, body=body)


def reindex_courses():
    course_keys = [course.id for course in modulestore().get_courses()]
    for course_key in course_keys:
        CoursewareSearchIndexer.do_course_reindex(modulestore(), course_key)


def setup():
    index_name = "courseware_index"
    config_body = {
        "settings": {
            "analysis": {
                "analyzer": {
                    "partword": {
                        "type": "custom",
                        "tokenizer": "partword_tokenizer",
                        "filter": [
                            "lowercase"
                        ]
                    }
                },
                "tokenizer": {
                    "partword_tokenizer": {
                        "type": "nGram",
                        "min_gram": 1,
                        "max_gram": 50
                    }
                }
            }
        },
        "mappings": {
            "course_info": {
                "properties": {
                    "content": {
                        "properties": {
                            "display_name": {
                                "type": "string",
                                "analyzer": "partword"
                            }
                        }
                    }
                }
            }
        }
    }
    index_config(index_name, config_body)
    reindex_courses()


if __name__ == "__main__":
    setup()
