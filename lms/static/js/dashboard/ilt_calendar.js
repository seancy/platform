!function() {
  var today = moment(),
      event_list = document.querySelector('.ilt-events-list')
  function Calendar(selector, events) {
    this.el = document.querySelector(selector);
    this.events = events;
    this.current = moment().date(1);
    this.next = true;
    this.draw();
  }

  Calendar.prototype.draw = function() {
    //Create Header
    this.drawHeader();

    // Draw week day names
    this.drawDayName();

    //Draw Month
    this.drawMonth();
  };

  Calendar.prototype.drawHeader = function() {
    var self = this;
    if (!this.header) {
      //Create the header elements
      this.header = createElement('div', 'header');
      this.header.className = 'header';

      this.title = createElement('h2', 'month-name');
      this.navigator = createElement('div', 'calendar-nav');

      var right = createElement('span', 'nav-right far fa-chevron-right');
      right.addEventListener('click', function() { self.nextMonth(); });

      var left = createElement('span', 'nav-left far fa-chevron-left');
      left.addEventListener('click', function() { self.prevMonth(); });

      //Append the Elements
      this.navigator.appendChild(left);
      this.navigator.appendChild(right);
      this.header.appendChild(this.title);
      this.header.appendChild(this.navigator);

      this.el && this.el.appendChild(this.header);
    }

    this.title.innerHTML = this.current.format('MMMM YYYY');
    var icon = createElement('i', 'far fa-calendar-week');
    this.title.insertAdjacentElement('afterbegin', icon);
  }

  Calendar.prototype.drawDayName = function() {
    console.log('111');
    var self = this,
        name_list = moment.weekdaysShort();
    if (!this.day_names) {
      console.log('222');
      this.day_names = createElement('div', 'day-names');
      for (var i = 0; i < name_list.length; i++) {
        var name = createElement('div', 'day-name'+' weekday-'+i, name_list[i]);
        this.day_names.appendChild(name)
      }
      this.el && this.el.appendChild(this.day_names);
    }
    $(".day-names .day-name").removeClass('highlight')
  }

  Calendar.prototype.drawMonth = function() {
    var self = this;
    if (this.month) {
      this.oldMonth = this.month;
      this.oldMonth.className = 'month out ' + (!self.next ? 'next' : 'prev');
      this.oldMonth.addEventListener('webkitAnimationEnd', function() {
        self.oldMonth.parentNode.removeChild(self.oldMonth);
        self.month = createElement('div', 'month');
        self.backFill();
        self.currentMonth();
        self.fowardFill();
        self.el.appendChild(self.month);
        window.setTimeout(function() {
          self.month.className = 'month in ' + (!self.next ? 'next' : 'prev');
          if (today.month() === self.current.month()) {
            var highlight_selector = ".weekday-" + today.day(),
                active_day = document.querySelector(".today");
            $(highlight_selector).addClass("highlight");
            self.drawUpcomingEvents()
          }
        }, 16);
      });
    } else {
        this.month = createElement('div', 'month');
        this.el && this.el.appendChild(this.month);
        this.backFill();
        this.currentMonth();
        this.fowardFill();
        this.month.className = 'month new';
        if (today.month() === self.current.month()) {
          var highlight_selector = ".weekday-" + today.day();
          $(highlight_selector).addClass("highlight");
        }
    }
  };

  Calendar.prototype.backFill = function() {
    var clone = this.current.clone();
    var dayOfWeek = clone.day();

    if (!dayOfWeek) { return; }

    clone.subtract('days', dayOfWeek+1);

    for(var i = dayOfWeek; i > 0 ; i--) {
      this.drawDay(clone.add('days', 1));
    }
  }

  Calendar.prototype.fowardFill = function() {
    var clone = this.current.clone().add('months', 1).subtract('days', 1);
    var dayOfWeek = clone.day();

    if (dayOfWeek === 6) { return; }

    for(var i = dayOfWeek; i < 6 ; i++) {
      this.drawDay(clone.add('days', 1));
    }
  }

  Calendar.prototype.currentMonth = function() {
    var clone = this.current.clone();

    while(clone.month() === this.current.month()) {
      this.drawDay(clone);
      clone.add('days', 1);
    }
  }

  Calendar.prototype.getWeek = function(day) {
    if (!this.week || day.day() === 0) {
      this.week = createElement('div', 'week');
      this.month.appendChild(this.week);
    }
  }

  Calendar.prototype.drawDay = function(day) {
    var self = this;
    this.getWeek(day);

    //Outer Day
    var outer = createElement('div', this.getDayClass(day));
    var current_day = day.clone();
    outer.addEventListener('click', function() {
      $(".ilt-calendar-wrapper").removeClass('no-upcoming-session');
      if (window.outerWidth < 768) {
        $("#calendar").hide();
        $(".ilt-events-wrapper").removeClass("mobile-events")
      }
      self.openDay(this, current_day);
      var week_days = document.getElementsByClassName('day');
      for (var i = 0; i < week_days.length; i++) {
        week_days[i].classList.remove('active-day');
        week_days[i].classList.add('inactive-day')
      }
      this.classList.add("active-day");
      this.classList.remove("inactive-day");
      $(".highlight").removeClass("highlight");
      var highlight_selector = ".weekday-" + current_day.day();
      $(highlight_selector).addClass("highlight");
    });

    var day_wrapper = createElement('span', 'day-wrapper');

    //Day Number
    var number = createElement('span', 'day-number', day.format('DD'));

    var dayEvents = this.events.reduce(function(memo, ev) {
      if (ev.start_date.isSame(day, 'day') || ev.end_date.isSame(day, 'day') || day.isBetween(ev.start_date, ev.end_date)) {
        memo.push(ev);
      }
      return memo;
    }, []);

    if (dayEvents.length > 0) {
      outer.classList.add('has-event')
    }

    // outer.appendChild(name);
    day_wrapper.appendChild(number);
    outer.appendChild(day_wrapper);
    //outer.appendChild(events);
    this.week.appendChild(outer);
  }

  Calendar.prototype.getDayClass = function(day) {
    var classes = ['day', 'weekday-'+day.day()];
    if (day.month() !== this.current.month()) {
      classes.push('other');
    } else if (today.isSame(day, 'day')) {
      classes.push('today');
    }
    return classes.join(' ');
  };

  Calendar.prototype.openDay = function(el, day) {
    var details, arrow;

    var currentOpened = document.querySelector('.ilt-details');

    //Check to see if there is an open detais box on the current row
    if (currentOpened && currentOpened.parentNode === el.parentNode) {
      details = currentOpened;
      arrow = document.querySelector('.arrow');
    } else {
      //Close the open events on differnt week row
      //currentOpened && currentOpened.parentNode.removeChild(currentOpened);
      if (currentOpened) {
        currentOpened.addEventListener('webkitAnimationEnd', function() {
          currentOpened.parentNode.removeChild(currentOpened);
        });
        currentOpened.addEventListener('oanimationend', function() {
          currentOpened.parentNode.removeChild(currentOpened);
        });
        currentOpened.addEventListener('msAnimationEnd', function() {
          currentOpened.parentNode.removeChild(currentOpened);
        });
        currentOpened.addEventListener('animationend', function() {
          currentOpened.parentNode.removeChild(currentOpened);
        });
        currentOpened.className = 'ilt-details out';
      }

      //Create the Details Container
      details = createElement('div', 'ilt-details in');

      //Create the arrow
      var arrow = createElement('div', 'arrow');

      //Create the event wrapper

      details.appendChild(arrow);
      el.parentNode.appendChild(details);
    }

    var todaysEvents = this.events.reduce(function(memo, ev) {
        if (ev.start_date.isSame(day, 'day') || ev.end_date.isSame(day, 'day') || day.isBetween(ev.start_date, ev.end_date)) {
          memo.push(ev);
        }
        return memo;
      }, []);

    this.renderEvents(todaysEvents, details);
    this.drawEventsList(todaysEvents, day);

    var offset = Math.abs(el.offsetLeft - (el.previousSibling || el.nextElementSibling).offsetLeft) / 2;
    arrow.style.left = el.offsetLeft - el.parentNode.offsetLeft + offset + 'px';
  };

  Calendar.prototype.convert_date = function (start, end) {
    var date_format = "YYYY-MM-DD HH:mm";
    if (moment.locale() == 'fr') {
      if (window.outerWidth < 768) {
        date_format = "DD-MM HH:mm"
      } else {
        date_format = "DD-MM-YYYY HH:mm"
      }
    } else {
      if (window.outerWidth < 768) {
        date_format = "MM-DD HH:mm"
      }
    }

    return start.format(date_format) + "\xa0 - \xa0" + end.format(date_format)
  };

  Date.prototype.addHours = function (h) {
    this.setTime(this.getTime() + (h * 60 * 60 * 1000));
    return this;
  };

  Calendar.prototype.teacherTimeToLocal = function (time, offsetHours) {
    time += time.toUpperCase().endsWith('Z') ? '' : 'Z';
    var dateObj = new Date(time);
    dateObj.addHours(-offsetHours);
    return dateObj.toISOString();
  };

  Calendar.prototype.drawEventsList = function (events, day) {
    var self = this;
    event_list.innerHTML = '';
    if (events.length > 0) {
        events.forEach(function (ev) {
            var wrapper = createElement('div', 'ilt-event swiper-slide'),
                session_info = createElement('div', 'ilt-event-info'),
                link = createElement('a', 'ilt-link', ''),
                course_name = createElement('h3', 'ilt-event-title', ev.course+" : "),
                title = createElement('h3', 'ilt-event-title', ev.title),
                time = createElement('span', 'ilt-event-time', self.convert_date(ev.start_date, ev.end_date)),
                timezone = createElement('span', 'ilt-event-timezone', ev.timezone),
                instructor = createElement('span', 'ilt-event-instructor', ev.instructor),
                location = createElement('span', 'ilt-event-location', ev.location),
                time_icon = createElement('i', 'far fa-clock', ''),
                timezone_icon = createElement('i', 'far fa-globe', ''),
                instructor_icon = createElement('i', 'far fa-user', ''),
                location_icon = createElement('i', 'far fa-location-circle', ''),
                left_info = createElement('div', 'left-info'),
                right_info = createElement('div', 'right-info'),
                duration = createElement('span', 'ilt-event-duration', ev.duration + ' ' + gettext('hours')),
                duration_icon = createElement('i', 'far fa-history', ''),
                area = createElement('span', 'ilt-event-area', ev.area_region),
                area_icon = createElement('i', 'far fa-globe-stand', ''),
                address = createElement('span', 'ilt-event-address', ev.address),
                address_icon = createElement('i', 'far fa-street-view', ''),
                zip_code = createElement('span', 'ilt-event-zip', moment.locale() == 'fr'? ev.zip_code + ", " + ev.city: ev.city + ", " + ev.zip_code),
                zip_code_icon = createElement('i', 'far fa-map-marker-alt', ''),
                location_id = createElement('span', 'ilt-event-location-id', ev.location_id),
                location_id_icon = createElement('i', 'far fa-map-marker-alt', ''),
                button = createElement('a', 'ical-download'),
                button_icon = createElement('i', 'far fa-calendar-plus', ''),
                button_text = createElement('span', 'ical-download-text', gettext('Add to Calendar')),
                event_day = createElement('section', 'event-day', ''),
                event_day_name = createElement('div', 'event-day-name', day.format('ddd')),
                event_day_number = createElement('h2', 'event-day-number', day.date()),
                regexp = /(ftp|http|https):\/\/(\w+:{0,1}\w*@)?(\S+)(:[0-9]+)?(\/|\/([\w#!:.?+=&%@!\-\/]))?/;
            if (regexp.test(ev.location)) {
                var location = createElement('a', 'ilt-event-location', ev.location);
                location.href = ev.location;
                location.target = "_blank"
            } else {
                var location = createElement('span', 'ilt-event-location', ev.location)
            }
            link.href = ev.url;
            link.target = "_blank";
            time.insertAdjacentElement('afterbegin', time_icon);
            timezone.insertAdjacentElement('afterbegin', timezone_icon);
            area.classList.add("hidden");
            if (ev.instructor == undefined) {
              instructor.classList.add("hidden")
            }
            instructor.insertAdjacentElement('afterbegin', instructor_icon);
            location.insertAdjacentElement('afterbegin', location_icon);
            link.appendChild(course_name);
            link.appendChild(title);
            duration.insertAdjacentElement('afterbegin', duration_icon);
            area.insertAdjacentElement('afterbegin', area_icon);
            address.insertAdjacentElement('afterbegin', address_icon);
            zip_code.insertAdjacentElement('afterbegin', zip_code_icon);
            location_id.insertAdjacentElement('afterbegin', location_id_icon);
            if (ev.duration == undefined) {
              duration.classList.add("hidden")
            }
            if (ev.area_region == undefined) {
              area.classList.add("hidden")
            }
            if (ev.address == undefined) {
              address.classList.add("hidden")
            }
            if (ev.zip_code == undefined && ev.city == undefined) {
              zip_code.classList.add("hidden")
            }
            if (ev.location_id == undefined) {
              location_id.classList.add("hidden")
            }
            button.appendChild(button_icon);
            button.appendChild(button_text);
            button.addEventListener('click', function () {
              var cal = ics(),
                  uid = ev.url.split("/").slice(-2, -1)[0];
                cal.addEvent(uid, ev.title, ev.course, ev.location,
                    self.teacherTimeToLocal(ev.start_at, ev.timezone_offset),
                    self.teacherTimeToLocal(ev.end_at, ev.timezone_offset));
                cal.download()
            });
            left_info.appendChild(time);
            left_info.appendChild(duration);
            left_info.appendChild(timezone);
            left_info.appendChild(instructor);
            left_info.appendChild(area);
            right_info.appendChild(location);
            right_info.appendChild(address);
            right_info.appendChild(zip_code);
            right_info.appendChild(location_id);
            session_info.appendChild(left_info);
            session_info.appendChild(right_info);
            session_info.appendChild(button);
            event_day.appendChild(event_day_name);
            event_day.appendChild(event_day_number);
            wrapper.appendChild(event_day);
            wrapper.appendChild(link);
            wrapper.appendChild(session_info);
            event_list.appendChild(wrapper);
        });
        this.swiper.destroy();
        var loop = events.length > 1;
        this.initSwiper(loop);
        $(".upcoming-session").removeClass("hidden");
        if (loop) {
          $('.ilt-calendar-wrapper').find('.swiper-button-next').removeClass("swiper-button-disabled");
          $('#ilt-calendar').find('.swiper-pagination').show();
        }
        else {
          $('.ilt-calendar-wrapper').find('.swiper-button-next').addClass("swiper-button-disabled");
          $('#ilt-calendar').find('.swiper-pagination').hide();
        }
    }
    else {
      var empty_event = createElement('h3', 'ilt-empty-event', gettext('No sessions available'));
      event_list.appendChild(empty_event);
      $(".upcoming-session").addClass("hidden");
      this.swiper.destroy();
      $('.ilt-calendar-wrapper').find('.swiper-button-next').addClass("swiper-button-disabled");
      $('#ilt-calendar').find('.swiper-pagination').hide();
    }
  };

  Calendar.prototype.drawUpcomingEvents = function () {
    var self = this;
    event_list.innerHTML = '';
    var upcomingEvents = this.events.reduce(function(memo, ev) {
      if (today.isSameOrBefore(ev.end_date, 'day')) {
        memo.push(ev);
      }
      return memo;
    }, []);
    if (upcomingEvents.length > 0) {
      var event_length = 0;
      upcomingEvents.forEach(function (ev) {
        var clone_event_date;
        if (today.isSameOrBefore(ev.start_date)) {
          clone_event_date = ev.start_date.clone()
        } else {
          clone_event_date = today.clone()
        }

        while (clone_event_date.isSameOrBefore(ev.end_date) || clone_event_date.date() == ev.end_date.date()) {
          var wrapper = createElement('div', 'ilt-event swiper-slide'),
            session_info = createElement('div', 'ilt-event-info'),
            link = createElement('a', 'ilt-link', ''),
            course_name = createElement('h3', 'ilt-event-title', ev.course+" : "),
            title = createElement('h3', 'ilt-event-title', ev.title),
            time = createElement('span', 'ilt-event-time', self.convert_date(ev.start_date, ev.end_date)),
            timezone = createElement('span', 'ilt-event-timezone', ev.timezone),
            time_icon = createElement('i', 'far fa-clock', ''),
            timezone_icon = createElement('i', 'far fa-globe', ''),
            instructor = createElement('span', 'ilt-event-instructor', ev.instructor),
            instructor_icon = createElement('i', 'far fa-user', ''),
            location_icon = createElement('i', 'far fa-location-circle', ''),
            left_info = createElement('div', 'left-info'),
            right_info = createElement('div', 'right-info'),
            duration = createElement('span', 'ilt-event-duration', ev.duration + ' ' + gettext('hours')),
            duration_icon = createElement('i', 'far fa-history', ''),
            area = createElement('span', 'ilt-event-area', ev.area_region),
            area_icon = createElement('i', 'far fa-globe-stand', ''),
            address = createElement('span', 'ilt-event-address', ev.address),
            address_icon = createElement('i', 'far fa-street-view', ''),
            zip_code = createElement('span', 'ilt-event-zip', moment.locale() == 'fr'? ev.zip_code + ", " + ev.city: ev.city + ", " + ev.zip_code),
            zip_code_icon = createElement('i', 'far fa-map-marker-alt', ''),
            location_id = createElement('span', 'ilt-event-location-id', ev.location_id),
            location_id_icon = createElement('i', 'far fa-map-marker-alt', ''),
            button = createElement('a', 'ical-download'),
            button_icon = createElement('i', 'far fa-calendar-plus', ''),
            button_text = createElement('span', 'ical-download-text', gettext('Add to Calendar')),
            event_day = createElement('section', 'event-day', ''),
            event_day_name = createElement('div', 'event-day-name', clone_event_date.format('ddd')),
            event_day_number = createElement('h2', 'event-day-number', clone_event_date.date()),
            regexp = /(ftp|http|https):\/\/(\w+:{0,1}\w*@)?(\S+)(:[0-9]+)?(\/|\/([\w#!:.?+=&%@!\-\/]))?/;
          if (regexp.test(ev.location)) {
              var location = createElement('a', 'ilt-event-location', ev.location);
              location.href = ev.location;
              location.target = "_blank"
          } else {
              var location = createElement('span', 'ilt-event-location', ev.location)
          }
          link.href = ev.url;
          link.target = "_blank";
          time.insertAdjacentElement('afterbegin', time_icon);
          timezone.insertAdjacentElement('afterbegin', timezone_icon);
          area.classList.add("hidden");
          if (ev.instructor == undefined) {
            instructor.classList.add("hidden")
          }
          instructor.insertAdjacentElement('afterbegin', instructor_icon);
          location.insertAdjacentElement('afterbegin', location_icon);
          link.appendChild(course_name);
          link.appendChild(title);
          duration.insertAdjacentElement('afterbegin', duration_icon);
          area.insertAdjacentElement('afterbegin', area_icon);
          address.insertAdjacentElement('afterbegin', address_icon);
          zip_code.insertAdjacentElement('afterbegin', zip_code_icon);
          location_id.insertAdjacentElement('afterbegin', location_id_icon);
          if (ev.duration == undefined) {
            duration.classList.add("hidden")
          }
          if (ev.area_region == undefined) {
            area.classList.add("hidden")
          }
          if (ev.address == undefined) {
            address.classList.add("hidden")
          }
          if (ev.zip_code == undefined && ev.city == undefined) {
            zip_code.classList.add("hidden")
          }
          if (ev.location_id == undefined) {
            location_id.classList.add("hidden")
          }
          button.appendChild(button_icon);
          button.appendChild(button_text);
          button.addEventListener('click', function () {
            var cal = ics(),
                uid = ev.url.split("/").slice(-2, -1)[0];
              cal.addEvent(uid, ev.title, ev.course, ev.location,
                  self.teacherTimeToLocal(ev.start_at, ev.timezone_offset),
                  self.teacherTimeToLocal(ev.end_at, ev.timezone_offset));
              cal.download()
          });
          left_info.appendChild(time);
          left_info.appendChild(duration);
          left_info.appendChild(timezone);
          left_info.appendChild(instructor);
          left_info.appendChild(area);
          right_info.appendChild(location);
          right_info.appendChild(address);
          right_info.appendChild(zip_code);
          right_info.appendChild(location_id);
          session_info.appendChild(left_info);
          session_info.appendChild(right_info);
          session_info.appendChild(button);
          event_day.appendChild(event_day_name);
          event_day.appendChild(event_day_number);
          wrapper.appendChild(event_day);
          wrapper.appendChild(link);
          wrapper.appendChild(session_info);
          event_list.appendChild(wrapper);
          clone_event_date.add(1, 'day');
          event_length += 1
        }
      });
      var loop = event_length > 1;
      this.swiper.destroy();
      this.initSwiper(loop);
      if (loop) {
        $('.ilt-calendar-wrapper').find('.swiper-button-next').removeClass("swiper-button-disabled");
        $('#ilt-calendar').find('.swiper-pagination').show();
      }
    }
    else {
      $(".ilt-calendar-wrapper").addClass('no-upcoming-session');
      $('#ilt-calendar').find('.swiper-pagination').hide();
    }
  };

  Calendar.prototype.renderEvents = function(events, ele) {
    //Remove any events in the current details element
    var currentWrapper = ele.querySelector('.events');
    var wrapper = createElement('div', 'events in' + (currentWrapper ? ' new' : ''));

    events.forEach(function(ev) {
      var div = createElement('div', 'event');
      var square = createElement('div', 'event-category ' + ev.color);
      var span = createElement('span', '', ev.title);

      div.appendChild(square);
      div.appendChild(span);
      wrapper.appendChild(div);
    });

    if (!events.length) {
      var div = createElement('div', 'event empty');
      var span = createElement('span', '', gettext('No Events'));

      div.appendChild(span);
      wrapper.appendChild(div);
    }

    if (currentWrapper) {
      currentWrapper.className = 'events out';
      currentWrapper.addEventListener('webkitAnimationEnd', function() {
        currentWrapper.parentNode.removeChild(currentWrapper);
        ele.appendChild(wrapper);
      });
      currentWrapper.addEventListener('oanimationend', function() {
        currentWrapper.parentNode.removeChild(currentWrapper);
        ele.appendChild(wrapper);
      });
      currentWrapper.addEventListener('msAnimationEnd', function() {
        currentWrapper.parentNode.removeChild(currentWrapper);
        ele.appendChild(wrapper);
      });
      currentWrapper.addEventListener('animationend', function() {
        currentWrapper.parentNode.removeChild(currentWrapper);
        ele.appendChild(wrapper);
      });
    } else {
      ele.appendChild(wrapper);
    }
  }

  Calendar.prototype.drawLegend = function() {
    var legend = createElement('div', 'legend');
    var calendars = this.events.map(function(e) {
      return e.calendar + '|' + e.color;
    }).reduce(function(memo, e) {
      if (memo.indexOf(e) === -1) {
        memo.push(e);
      }
      return memo;
    }, []).forEach(function(e) {
      var parts = e.split('|');
      var entry = createElement('span', 'entry ' +  parts[1], parts[0]);
      legend.appendChild(entry);
    });
    this.el && this.el.appendChild(legend);
  }

  Calendar.prototype.nextMonth = function() {
    this.current.add('months', 1);
    this.next = true;
    this.draw();
  }

  Calendar.prototype.prevMonth = function() {
    this.current.subtract('months', 1);
    this.next = false;
    this.draw();
  }

  window.Calendar = Calendar;

  function createElement(tagName, className, innerText) {
    var ele = document.createElement(tagName);
    if (className) {
      ele.className = className;
    }
    if (innerText) {
      ele.innderText = ele.textContent = innerText;
    }
    return ele;
  }
  
  Calendar.prototype.initSwiper = function (loop) {
    var swiper = new Swiper('#ilt-events', {
      slidesPerView: 1,
      spaceBetween: 30,
      loop: loop,
      cssMode: true,
      navigation: {
        nextEl: '#ilt-calendar .swiper-button-next',
        prevEl: '#ilt-calendar .swiper-button-prev',
      },
      pagination: {
        el: '#ilt-calendar .swiper-pagination'
      },
      keyboard: true,
    });
    this.swiper = swiper;
  };

  $(".back-to-calendar").on('click', function () {
    $("#calendar").show();
    $(".ilt-events-wrapper").addClass("mobile-events")
  })
}();

!function() {
  var locale = document.documentElement.lang;
  moment.locale(locale);
  $.ajax({
      url: '/enrolled_ilt_sessions',
      success: function (data) {
          var ilt_events = data.ilt_sessions,
              has_upcoming_sessions = false,
              today = moment(),
              colors = ['orange', 'blue', 'yellow', 'green'];
          if (ilt_events.length > 0) {
              ilt_events.forEach(function (ev) {
                  ev.start_date = moment(ev.start_at);
                  ev.end_date = moment(ev.end_at);
                  ev.color = colors[Math.floor(Math.random() * 4)];
                  if (ev.end_date.isSame(today, 'day') || ev.end_date.isAfter(today, 'day')) {
                    has_upcoming_sessions = true
                  }
              });
              ilt_events.sort(function (a, b) {
                  if (a.start_date.isBefore(b.start_date)) {
                      return -1
                  }
                  else if (a.start_date.isSame(b.start_date)) {
                      if (a.end_date.isBefore(b.end_date)) {
                          return -1
                      }
                      else {
                          return 1
                      }
                  }
                  else {
                      return 1
                  }
              });
              $(".ilt-calendar-wrapper").addClass('has-past-session');
              var calendar = new Calendar('#calendar', ilt_events);
              calendar.initSwiper(false);
              $('.ilt-calendar-wrapper').find('.swiper-button-next').addClass("swiper-button-disabled")
              if (has_upcoming_sessions) {
                  $(".ilt-calendar-wrapper").removeClass('no-upcoming-session');
                  calendar.drawUpcomingEvents();
              }
          }
      }
  });

}();
