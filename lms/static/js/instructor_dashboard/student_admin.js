/* globals _, interpolate_text */

(function() {
    'use strict';
    var PendingInstructorTasks, createTaskListTable, findAndAssert, statusAjaxError;

    statusAjaxError = function() {
        return window.InstructorDashboard.util.statusAjaxError.apply(this, arguments);
    };

    createTaskListTable = function() {
        return window.InstructorDashboard.util.createTaskListTable.apply(this, arguments);
    };

    PendingInstructorTasks = function() {
        return window.InstructorDashboard.util.PendingInstructorTasks;
    };

    findAndAssert = function($root, selector) {
        var item, msg;
        item = $root.find(selector);
        if (item.length !== 1) {
            msg = 'Failed Element Selection';
            throw msg;
        } else {
            return item;
        }
    };

    this.StudentAdmin = (function() {
        function StudentAdmin($section) {
            var studentadmin = this;
            this.$section = $section;
            this.$section.data('wrapper', this);
            this.$field_student_select_progress = findAndAssert(this.$section, "input[name='student-select-progress']");
            this.$field_student_select_grade = findAndAssert(this.$section, "input[name='student-select-grade']");
            this.$progress_link = findAndAssert(this.$section, 'a.progress-link');
            this.$field_problem_select_single = findAndAssert(this.$section, "input[name='problem-select-single']");
            this.$btn_reset_attempts_single = findAndAssert(this.$section, "input[name='reset-attempts-single']");
            this.$btn_delete_state_single = this.$section.find("input[name='delete-state-single']");
            this.$btn_rescore_problem_single = this.$section.find("input[name='rescore-problem-single']");
            this.$btn_rescore_problem_if_higher_single = this.$section.find(
                "input[name='rescore-problem-if-higher-single']"
            );
            this.$btn_override_problem_score_single = this.$section.find(
                "input[name='override-problem-score-single']"
            );
            this.$field_select_score_single = findAndAssert(this.$section, "input[name='score-select-single']");
            this.$btn_task_history_single = this.$section.find("input[name='task-history-single']");
            this.$table_task_history_single = $('.task-history-single-table');
            this.$field_exam_grade = this.$section.find("input[name='entrance-exam-student-select-grade']");
            this.$btn_reset_entrance_exam_attempts = this.$section.find("input[name='reset-entrance-exam-attempts']");
            this.$btn_delete_entrance_exam_state = this.$section.find("input[name='delete-entrance-exam-state']");
            this.$btn_rescore_entrance_exam = this.$section.find("input[name='rescore-entrance-exam']");
            this.$btn_rescore_entrance_exam_if_higher = this.$section.find(
                "input[name='rescore-entrance-exam-if-higher']"
            );
            this.$btn_skip_entrance_exam = this.$section.find("input[name='skip-entrance-exam']");
            this.$btn_entrance_exam_task_history = this.$section.find("input[name='entrance-exam-task-history']");
            this.$table_entrance_exam_task_history = $('.entrance-exam-task-history-table');
            this.$field_problem_select_all = this.$section.find("input[name='problem-select-all']");
            this.$btn_reset_attempts_all = this.$section.find("input[name='reset-attempts-all']");
            this.$btn_rescore_problem_all = this.$section.find("input[name='rescore-problem-all']");
            this.$btn_rescore_problem_if_higher_all = this.$section.find("input[name='rescore-problem-all-if-higher']");
            this.$btn_task_history_all = this.$section.find("input[name='task-history-all']");
            this.$table_task_history_all = $('.task-history-all-table');
            this.instructor_tasks = new (PendingInstructorTasks())(this.$section);
            this.$request_err = findAndAssert(this.$section, '.student-specific-container .request-response-error');
            this.$request_err_grade = findAndAssert(this.$section, '.student-grade-container .request-response-error');
            this.$request_err_ee = this.$section.find('.entrance-exam-grade-container .request-response-error');
            this.$request_response_error_all = this.$section.find('.course-specific-container .request-response-error');

            this.clear_display();

            this.$progress_link.click(function(e) {
                var errorMessage, fullErrorMessage, uniqStudentIdentifier;
                e.preventDefault();
                uniqStudentIdentifier = studentadmin.$field_student_select_progress.val();
                if (!uniqStudentIdentifier) {
                    studentadmin.$request_err.text(
                        gettext('Please enter a learner email address or username.')
                    );
                    return studentadmin.$request_err.css({display: 'block'});
                }
                errorMessage = gettext("Error getting learner progress url for '<%- student_id %>'. Make sure that the learner identifier is spelled correctly.");  // eslint-disable-line max-len
                fullErrorMessage = _.template(errorMessage)({
                    student_id: uniqStudentIdentifier
                });
                return $.ajax({
                    type: 'POST',
                    dataType: 'json',
                    url: studentadmin.$progress_link.data('endpoint'),
                    data: {
                        unique_student_identifier: uniqStudentIdentifier
                    },
                    success: studentadmin.clear_errors_then(function(data) {
                        window.location = data.progress_url;
                        return window.location;
                    }),
                    error: statusAjaxError(function() {
                        studentadmin.$request_err.text(fullErrorMessage);
                        return studentadmin.$request_err.css({display: 'block'});
                    })
                });
            });
            this.$btn_reset_attempts_single.click(function() {
                var errorMessage, fullErrorMessage, fullSuccessMessage,
                    problemToReset, sendData, successMessage, uniqStudentIdentifier;
                uniqStudentIdentifier = studentadmin.$field_student_select_grade.val();
                problemToReset = studentadmin.$field_problem_select_single.val();
                if (!uniqStudentIdentifier) {
                    studentadmin.$request_err_grade.text(
                        gettext('Please enter a learner email address or username.')
                    );
                    return studentadmin.$request_err_grade.css({display: 'block'});
                }
                if (!problemToReset) {
                    studentadmin.$request_err_grade.text(gettext('Please enter a problem location.'));
                    return studentadmin.$request_err_grade.css({display: 'block'});
                }
                sendData = {
                    unique_student_identifier: uniqStudentIdentifier,
                    problem_to_reset: problemToReset,
                    delete_module: false
                };
                successMessage = gettext("Success! Problem attempts reset for problem '<%- problem_id %>' and learner '<%- student_id %>'.");  // eslint-disable-line max-len
                errorMessage = gettext("Error resetting problem attempts for problem '<%= problem_id %>' and learner '<%- student_id %>'. Make sure that the problem and learner identifiers are complete and correct.");  // eslint-disable-line max-len
                fullSuccessMessage = _.template(successMessage)({
                    problem_id: problemToReset,
                    student_id: uniqStudentIdentifier
                });
                fullErrorMessage = _.template(errorMessage)({
                    problem_id: problemToReset,
                    student_id: uniqStudentIdentifier
                });
                return $.ajax({
                    type: 'POST',
                    dataType: 'json',
                    url: studentadmin.$btn_reset_attempts_single.data('endpoint'),
                    data: sendData,
                    success: studentadmin.clear_errors_then(function() {
                        return alert(fullSuccessMessage);  // eslint-disable-line no-alert
                    }),
                    error: statusAjaxError(function() {
                        studentadmin.$request_err_grade.text(fullErrorMessage);
                        return studentadmin.$request_err_grade.css({display: 'block'});
                    })
                });
            });
            this.$btn_delete_state_single.click(function() {
                var confirmMessage, errorMessage, fullConfirmMessage,
                    fullErrorMessage, problemToReset, sendData, uniqStudentIdentifier;
                uniqStudentIdentifier = studentadmin.$field_student_select_grade.val();
                problemToReset = studentadmin.$field_problem_select_single.val();
                if (!uniqStudentIdentifier) {
                    studentadmin.$request_err_grade.text(
                        gettext('Please enter a learner email address or username.')
                    );
                    return studentadmin.$request_err_grade.css({display: 'block'});
                }
                if (!problemToReset) {
                    studentadmin.$request_err_grade.text(
                        gettext('Please enter a problem location.')
                    );
                    return studentadmin.$request_err_grade.css({display: 'block'});
                }
                confirmMessage = gettext("Delete learner '<%- student_id %>'s state on problem '<%- problem_id %>'?");
                fullConfirmMessage = _.template(confirmMessage)({
                    student_id: uniqStudentIdentifier,
                    problem_id: problemToReset
                });
                if (window.confirm(fullConfirmMessage)) {  // eslint-disable-line no-alert
                    sendData = {
                        unique_student_identifier: uniqStudentIdentifier,
                        problem_to_reset: problemToReset,
                        delete_module: true
                    };
                    errorMessage = gettext("Error deleting learner '<%- student_id %>'s state on problem '<%- problem_id %>'. Make sure that the problem and learner identifiers are complete and correct.");  // eslint-disable-line max-len
                    fullErrorMessage = _.template(errorMessage)({
                        student_id: uniqStudentIdentifier,
                        problem_id: problemToReset
                    });
                    return $.ajax({
                        type: 'POST',
                        dataType: 'json',
                        url: studentadmin.$btn_delete_state_single.data('endpoint'),
                        data: sendData,
                        success: studentadmin.clear_errors_then(function() {
                            return alert(gettext('Module state successfully deleted.'));  // eslint-disable-line no-alert, max-len
                        }),
                        error: statusAjaxError(function() {
                            studentadmin.$request_err_grade.text(fullErrorMessage);
                            return studentadmin.$request_err_grade.css({display: 'block'});
                        })
                    });
                } else {
                    return studentadmin.clear_errors();
                }
            });
            this.$btn_rescore_problem_single.click(function() {
                return studentadmin.rescore_problem_single(false);
            });
            this.$btn_rescore_problem_if_higher_single.click(function() {
                return studentadmin.rescore_problem_single(true);
            });
            this.$btn_task_history_single.click(function() {
                var errorMessage, fullErrorMessage, problemToReset, sendData, uniqStudentIdentifier;
                uniqStudentIdentifier = studentadmin.$field_student_select_grade.val();
                problemToReset = studentadmin.$field_problem_select_single.val();
                if (!uniqStudentIdentifier) {
                    studentadmin.$request_err_grade.text(
                        gettext('Please enter a learner email address or username.')
                    );
                    return studentadmin.$request_err_grade.css({display: 'block'});
                }
                if (!problemToReset) {
                    studentadmin.$request_err_grade.text(
                        gettext('Please enter a problem location.')
                    );
                    return studentadmin.$request_err_grade.css({display: 'block'});
                }
                sendData = {
                    unique_student_identifier: uniqStudentIdentifier,
                    problem_location_str: problemToReset
                };
                errorMessage = gettext("Error getting task history for problem '<%- problem_id %>' and learner '<%- student_id %>'. Make sure that the problem and learner identifiers are complete and correct.");  // eslint-disable-line max-len
                fullErrorMessage = _.template(errorMessage)({
                    student_id: uniqStudentIdentifier,
                    problem_id: problemToReset
                });
                return $.ajax({
                    type: 'POST',
                    dataType: 'json',
                    url: studentadmin.$btn_task_history_single.data('endpoint'),
                    data: sendData,
                    success: studentadmin.clear_errors_then(function(data) {
                        return createTaskListTable(studentadmin.$table_task_history_single, data.tasks);
                    }),
                    error: statusAjaxError(function() {
                        studentadmin.$request_err_grade.text(fullErrorMessage);
                        return studentadmin.$request_err_grade.css({display: 'block'});
                    })
                });
            });
            this.$btn_reset_entrance_exam_attempts.click(function() {
                var sendData, uniqStudentIdentifier;
                uniqStudentIdentifier = studentadmin.$field_exam_grade.val();
                if (!uniqStudentIdentifier) {
                    studentadmin.$request_err_ee.text(gettext(
                        'Please enter a learner email address or username.')
                    );
                    return studentadmin.$request_ee.css({display: 'block'});
                }
                sendData = {
                    unique_student_identifier: uniqStudentIdentifier,
                    delete_module: false
                };
                return $.ajax({
                    type: 'POST',
                    dataType: 'json',
                    url: studentadmin.$btn_reset_entrance_exam_attempts.data('endpoint'),
                    data: sendData,
                    success: studentadmin.clear_errors_then(function() {
                        var fullSuccessMessage, successMessage;
                        successMessage = gettext("Entrance exam attempts is being reset for learner '{student_id}'.");
                        fullSuccessMessage = interpolate_text(successMessage, {
                            student_id: uniqStudentIdentifier
                        });
                        return alert(fullSuccessMessage);  // eslint-disable-line no-alert
                    }),
                    error: statusAjaxError(function() {
                        var errorMessage, fullErrorMessage;
                        errorMessage = gettext("Error resetting entrance exam attempts for learner '{student_id}'. Make sure learner identifier is correct.");  // eslint-disable-line max-len
                        fullErrorMessage = interpolate_text(errorMessage, {
                            student_id: uniqStudentIdentifier
                        });
                        studentadmin.$request_err_ee.text(fullErrorMessage);
                        return studentadmin.$request_err_ee.css({display: 'block'});
                    })
                });
            });
            this.$btn_rescore_entrance_exam.click(function() {
                return studentadmin.rescore_entrance_exam_all(false);
            });
            this.$btn_rescore_entrance_exam_if_higher.click(function() {
                return studentadmin.rescore_entrance_exam_all(true);
            });
            this.$btn_skip_entrance_exam.click(function() {
                var confirmMessage, fullConfirmMessage, sendData, uniqStudentIdentifier;
                uniqStudentIdentifier = studentadmin.$field_exam_grade.val();
                if (!uniqStudentIdentifier) {
                    studentadmin.$request_err_ee.text(gettext("Enter a learner's username or email address."));
                    return studentadmin.$request_err_ee.css({display: 'block'});
                }
                confirmMessage = gettext("Do you want to allow this learner ('{student_id}') to skip the entrance exam?");  // eslint-disable-line max-len
                fullConfirmMessage = interpolate_text(confirmMessage, {
                    student_id: uniqStudentIdentifier
                });
                if (window.confirm(fullConfirmMessage)) {  // eslint-disable-line no-alert
                    sendData = {
                        unique_student_identifier: uniqStudentIdentifier
                    };
                    return $.ajax({
                        dataType: 'json',
                        url: studentadmin.$btn_skip_entrance_exam.data('endpoint'),
                        data: sendData,
                        type: 'POST',
                        success: studentadmin.clear_errors_then(function(data) {
                            return alert(data.message);  // eslint-disable-line no-alert
                        }),
                        error: statusAjaxError(function() {
                            var errorMessage;
                            errorMessage = gettext("An error occurred. Make sure that the learner's username or email address is correct and try again.");  // eslint-disable-line max-len
                            studentadmin.$request_err_ee.text(errorMessage);
                            return studentadmin.$request_err_ee.css({display: 'block'});
                        })
                    });
                }
                return false;
            });
            this.$btn_delete_entrance_exam_state.click(function() {
                var sendData, uniqStudentIdentifier;
                uniqStudentIdentifier = studentadmin.$field_exam_grade.val();
                if (!uniqStudentIdentifier) {
                    studentadmin.$request_err_ee.text(
                        gettext('Please enter a learner email address or username.')
                    );
                    return studentadmin.$request_err_ee.css({display: 'block'});
                }
                sendData = {
                    unique_student_identifier: uniqStudentIdentifier,
                    delete_module: true
                };
                return $.ajax({
                    type: 'POST',
                    dataType: 'json',
                    url: studentadmin.$btn_delete_entrance_exam_state.data('endpoint'),
                    data: sendData,
                    success: studentadmin.clear_errors_then(function() {
                        var fullSuccessMessage, successMessage;
                        successMessage = gettext("Entrance exam state is being deleted for learner '{student_id}'.");
                        fullSuccessMessage = interpolate_text(successMessage, {
                            student_id: uniqStudentIdentifier
                        });
                        return alert(fullSuccessMessage);  // eslint-disable-line no-alert
                    }),
                    error: statusAjaxError(function() {
                        var errorMessage, fullErrorMessage;
                        errorMessage = gettext("Error deleting entrance exam state for learner '{student_id}'. Make sure learner identifier is correct.");  // eslint-disable-line max-len
                        fullErrorMessage = interpolate_text(errorMessage, {
                            student_id: uniqStudentIdentifier
                        });
                        studentadmin.$request_err_ee.text(fullErrorMessage);
                        return studentadmin.$request_err_ee.css({display: 'block'});
                    })
                });
            });
            this.$btn_entrance_exam_task_history.click(function() {
                var sendData, uniqStudentIdentifier;
                uniqStudentIdentifier = studentadmin.$field_exam_grade.val();
                if (!uniqStudentIdentifier) {
                    studentadmin.$request_err_ee.text(
                        gettext("Enter a learner's username or email address.")
                    );
                    return studentadmin.$request_err_ee.css({display: 'block'});
                }
                sendData = {
                    unique_student_identifier: uniqStudentIdentifier
                };
                return $.ajax({
                    type: 'POST',
                    dataType: 'json',
                    url: studentadmin.$btn_entrance_exam_task_history.data('endpoint'),
                    data: sendData,
                    success: studentadmin.clear_errors_then(function(data) {
                        return createTaskListTable(studentadmin.$table_entrance_exam_task_history, data.tasks);
                    }),
                    error: statusAjaxError(function() {
                        var errorMessage, fullErrorMessage;
                        errorMessage = gettext("Error getting entrance exam task history for learner '{student_id}'. Make sure learner identifier is correct.");  // eslint-disable-line max-len
                        fullErrorMessage = interpolate_text(errorMessage, {
                            student_id: uniqStudentIdentifier
                        });
                        studentadmin.$request_err_ee.text(fullErrorMessage);
                        return studentadmin.$request_err_ee.css({display: 'block'});
                    })
                });
            });
            this.$btn_reset_attempts_all.click(function() {
                var confirmMessage, errorMessage, fullConfirmMessage,
                    fullErrorMessage, fullSuccessMessage, problemToReset, sendData, successMessage;
                problemToReset = studentadmin.$field_problem_select_all.val();
                if (!problemToReset) {
                    studentadmin.$request_response_error_all.text(
                        gettext('Please enter a problem location.')
                    );
                    return studentadmin.$request_response_error_all.css({display: 'block'});
                }
                confirmMessage = gettext("Reset attempts for all learners on problem <code>'<%- problem_id %>'</code>?");
                fullConfirmMessage = _.template(confirmMessage)({
                    problem_id: problemToReset
                });

                LearningTribes.confirmation.show(fullConfirmMessage, function () {
                    sendData = {
                        all_students: true,
                        problem_to_reset: problemToReset
                    };
                    successMessage = gettext("Successfully started task to reset attempts for problem <code>'<%- problem_id %>'</code>. Click the 'Show Task Status' button to see the status of the task.");  // eslint-disable-line max-len
                    fullSuccessMessage = _.template(successMessage)({
                        problem_id: problemToReset
                    });
                    errorMessage = gettext("Error starting a task to reset attempts for all learners on problem <code>'<%- problem_id %>'</code>. Make sure that the problem identifier is complete and correct.");  // eslint-disable-line max-len
                    fullErrorMessage = _.template(errorMessage)({
                        problem_id: problemToReset
                    });
                    return $.ajax({
                        type: 'POST',
                        dataType: 'json',
                        url: studentadmin.$btn_reset_attempts_all.data('endpoint'),
                        data: sendData,
                        success: studentadmin.clear_errors_then(function() {
                            LearningTribes.dialog.show(fullSuccessMessage)
                        }),
                        error: statusAjaxError(function() {
                            studentadmin.$request_response_error_all.text(fullErrorMessage);
                            return studentadmin.$request_response_error_all.css({display: 'block'});
                        })
                    });
                }, function () {
                    studentadmin.clear_errors();
                });
            });
            this.$btn_rescore_problem_all.click(function() {
                return studentadmin.rescore_problem_all(false);
            });
            this.$btn_rescore_problem_if_higher_all.click(function() {
                return studentadmin.rescore_problem_all(true);
            });
            this.$btn_override_problem_score_single.click(function() {
                return studentadmin.override_problem_score_single();
            });
            this.$btn_task_history_all.click(function() {
                var sendData;
                sendData = {
                    problem_location_str: studentadmin.$field_problem_select_all.val()
                };
                if (!sendData.problem_location_str) {
                    studentadmin.$request_response_error_all.text(
                        gettext('Please enter a problem location.')
                    );
                    return studentadmin.$request_response_error_all.css({display: 'block'});
                }
                return $.ajax({
                    type: 'POST',
                    dataType: 'json',
                    url: studentadmin.$btn_task_history_all.data('endpoint'),
                    data: sendData,
                    success: studentadmin.clear_errors_then(function(data) {
                        return createTaskListTable(studentadmin.$table_task_history_all, data.tasks);
                    }),
                    error: statusAjaxError(function() {
                        studentadmin.$request_response_error_all.text(
                            gettext('Error listing task history for this learner and problem.')
                        );
                        return studentadmin.$request_response_error_all.css({display: 'block'});
                    })
                });
            });
        }

        StudentAdmin.prototype.rescore_problem_single = function(onlyIfHigher) {
            var defaultErrorMessage, fullDefaultErrorMessage, fullSuccessMessage,
                problemToReset, sendData, successMessage, uniqStudentIdentifier,
                that = this;
            uniqStudentIdentifier = this.$field_student_select_grade.val();
            problemToReset = this.$field_problem_select_single.val();
            if (!uniqStudentIdentifier) {
                this.$request_err_grade.text(
                    gettext('Please enter a learner email address or username.')
                );
                return $request_err_grade.css({display: 'block'});
            }
            if (!problemToReset) {
                this.$request_err_grade.text(
                    gettext('Please enter a problem location.')
                );
                return $request_err_grade.css({display: 'block'});
            }
            sendData = {
                unique_student_identifier: uniqStudentIdentifier,
                problem_to_reset: problemToReset,
                only_if_higher: onlyIfHigher
            };
            successMessage = gettext("Started rescore problem task for problem '<%- problem_id %>' and learner '<%- student_id %>'. Click the 'Show Task Status' button to see the status of the task.");  // eslint-disable-line max-len
            fullSuccessMessage = _.template(successMessage)({
                student_id: uniqStudentIdentifier,
                problem_id: problemToReset
            });
            defaultErrorMessage = gettext("Error starting a task to rescore problem '<%- problem_id %>' for learner '<%- student_id %>'. Make sure that the the problem and learner identifiers are complete and correct.");  // eslint-disable-line max-len
            fullDefaultErrorMessage = _.template(defaultErrorMessage)({
                student_id: uniqStudentIdentifier,
                problem_id: problemToReset
            });
            return $.ajax({
                type: 'POST',
                dataType: 'json',
                url: this.$btn_rescore_problem_single.data('endpoint'),
                data: sendData,
                success: this.clear_errors_then(function() {
                    return alert(fullSuccessMessage);  // eslint-disable-line no-alert
                }),
                error: statusAjaxError(function(response) {
                    if (response.responseText) {
                        that.$request_err_grade.text(response.responseText);
                        return that.$request_err_grade.css({display: 'block'});
                    }
                    that.$request_err_grade.text(fullDefaultErrorMessage);
                    return that.$request_err_grade.css({display: 'block'});
                })
            });
        };

        StudentAdmin.prototype.override_problem_score_single = function() {
            var defaultErrorMessage, fullDefaultErrorMessage, fullSuccessMessage,
                problemToReset, score, sendData, successMessage, uniqStudentIdentifier,
                that = this;
            uniqStudentIdentifier = this.$field_student_select_grade.val();
            problemToReset = this.$field_problem_select_single.val();
            score = this.$field_select_score_single.val();
            if (!uniqStudentIdentifier) {
                this.$request_err_grade.text(
                    gettext('Please enter a learner email address or username.')
                );
                return this.$request_err_grade.css({display: 'block'});
            }
            if (!problemToReset) {
                this.$request_err_grade.text(
                    gettext('Please enter a problem location.')
                );
                return this.$request_err_grade.css({display: 'block'});
            }
            if (!score) {
                this.$request_err_grade.text(
                    gettext('Please enter a score.')
                );
                return this.$request_err_grade.css({display: 'block'});
            }
            sendData = {
                unique_student_identifier: uniqStudentIdentifier,
                problem_to_reset: problemToReset,
                score: score
            };
            successMessage = gettext("Started task to override the score for problem '<%- problem_id %>' and learner '<%- student_id %>'. Click the 'Show Task Status' button to see the status of the task.");  // eslint-disable-line max-len
            fullSuccessMessage = _.template(successMessage)({
                student_id: uniqStudentIdentifier,
                problem_id: problemToReset
            });
            defaultErrorMessage = gettext("Error starting a task to override score for problem '<%- problem_id %>' for learner '<%- student_id %>'. Make sure that the the score and the problem and learner identifiers are complete and correct.");  // eslint-disable-line max-len
            fullDefaultErrorMessage = _.template(defaultErrorMessage)({
                student_id: uniqStudentIdentifier,
                problem_id: problemToReset
            });
            return $.ajax({
                type: 'POST',
                dataType: 'json',
                url: this.$btn_override_problem_score_single.data('endpoint'),
                data: sendData,
                success: this.clear_errors_then(function() {
                    return alert(fullSuccessMessage);  // eslint-disable-line no-alert
                }),
                error: statusAjaxError(function(response) {
                    if (response.responseText) {
                        that.$request_err_grade.text(response.responseText);
                        return that.$request_err_grade.css({display: 'block'});
                    }
                    that.$request_err_grade.text(fullDefaultErrorMessage);
                    return that.$request_err_grade.css({display: 'block'});
                })
            });
        };

        StudentAdmin.prototype.rescore_entrance_exam_all = function(onlyIfHigher) {
            var sendData, uniqStudentIdentifier,
                that = this;
            uniqStudentIdentifier = this.$field_exam_grade.val();
            if (!uniqStudentIdentifier) {
                this.$request_err_ee.text(gettext(
                    'Please enter a learner email address or username.')
                );
                return this.$request_err_ee.css({display: 'block'});
            }
            sendData = {
                unique_student_identifier: uniqStudentIdentifier,
                only_if_higher: onlyIfHigher
            };
            return $.ajax({
                type: 'POST',
                dataType: 'json',
                url: this.$btn_rescore_entrance_exam.data('endpoint'),
                data: sendData,
                success: this.clear_errors_then(function() {
                    var fullSuccessMessage, successMessage;
                    successMessage = gettext("Started entrance exam rescore task for learner '{student_id}'. Click the 'Show Task Status' button to see the status of the task.");  // eslint-disable-line max-len
                    fullSuccessMessage = interpolate_text(successMessage, {
                        student_id: uniqStudentIdentifier
                    });
                    return alert(fullSuccessMessage);  // eslint-disable-line no-alert
                }),
                error: statusAjaxError(function() {
                    var errorMessage, fullErrorMessage;
                    errorMessage = gettext("Error starting a task to rescore entrance exam for learner '{student_id}'. Make sure that entrance exam has problems in it and learner identifier is correct.");  // eslint-disable-line max-len
                    fullErrorMessage = interpolate_text(errorMessage, {
                        student_id: uniqStudentIdentifier
                    });
                    that.$request_err_ee.text(fullErrorMessage);
                    return that.$request_err.css({display: 'block'});
                })
            });
        };

        StudentAdmin.prototype.rescore_problem_all = function(onlyIfHigher) {
            var confirmMessage, defaultErrorMessage, fullConfirmMessage,
                fullDefaultErrorMessage, fullSuccessMessage, problemToReset,
                sendData, successMessage,
                that = this;
            problemToReset = this.$field_problem_select_all.val();
            if (!problemToReset) {
                this.$request_response_error_all.text(
                    gettext('Please enter a problem location.')
                );
                return studentadmin.$request_response_error_all.css({display: 'block'});
            }
            confirmMessage = gettext("Rescore problem <code>'<%- problem_id %>'</code> for all learners?");
            fullConfirmMessage = _.template(confirmMessage)({
                problem_id: problemToReset
            });
            LearningTribes.confirmation.show(fullConfirmMessage, function () {
                sendData = {
                    all_students: true,
                    problem_to_reset: problemToReset,
                    only_if_higher: onlyIfHigher
                };
                successMessage = gettext("Successfully started task to rescore problem <code>'<%- problem_id %>'</code> for all learners. Click the 'Show Task Status' button to see the status of the task.");  // eslint-disable-line max-len
                fullSuccessMessage = _.template(successMessage)({
                    problem_id: problemToReset
                });
                defaultErrorMessage = gettext("Error starting a task to rescore problem <code>'<%- problem_id %>'</code>. Make sure that the problem identifier is complete and correct.");  // eslint-disable-line max-len
                fullDefaultErrorMessage = _.template(defaultErrorMessage)({
                    problem_id: problemToReset
                });
                return $.ajax({
                    type: 'POST',
                    dataType: 'json',
                    url: that.$btn_rescore_problem_all.data('endpoint'),
                    data: sendData,
                    success: that.clear_errors_then(function() {
                        LearningTribes.dialog.show(fullSuccessMessage)
                    }),
                    error: statusAjaxError(function(response) {
                        if (response.responseText) {
                            that.$request_response_error_all.text(response.responseText);
                            return that.$request_response_error_all.css({display: 'block'});
                        }
                        that.$request_response_error_all.text(fullDefaultErrorMessage);
                        return that.$request_response_error_all.css({display: 'block'});
                    })
                });
            }, function () {
                that.clear_errors();
            });
        };

        StudentAdmin.prototype.clear_errors_then = function(cb) {
            this.clear_errors();
            return function() {
                return cb != null ? cb.apply(this, arguments) : void 0;
            };
        };

        StudentAdmin.prototype.clear_errors = function() {
            this.$request_err.empty();
            this.$request_err_grade.empty();
            this.$request_err_ee.empty();
            this.$request_response_error_all.empty();
            return this.clear_display();
        };

        StudentAdmin.prototype.clear_display = function() {
            this.$request_err.css({display: 'none'});
            this.$request_err_grade.css({display: 'none'});
            this.$request_err_ee.css({display: 'none'});
            return this.$request_response_error_all.css({display: 'none'});;
        }

        StudentAdmin.prototype.onClickTitle = function() {
            return this.instructor_tasks.task_poller.start();
        };

        StudentAdmin.prototype.onExit = function() {
            return this.instructor_tasks.task_poller.stop();
        };

        return StudentAdmin;
    }());

    _.defaults(window, {
        InstructorDashboard: {}
    });

    _.defaults(window.InstructorDashboard, {
        sections: {}
    });

    _.defaults(window.InstructorDashboard.sections, {
        StudentAdmin: this.StudentAdmin
    });
}).call(this);
