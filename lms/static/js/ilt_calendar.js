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
  }

  Calendar.prototype.drawHeader = function() {
    var self = this;
    if(!this.header) {
      //Create the header elements
      this.header = createElement('div', 'header');
      this.header.className = 'header';

      this.title = createElement('h2');

      var right = createElement('div', 'right');
      right.addEventListener('click', function() { self.nextMonth(); });

      var left = createElement('div', 'left');
      left.addEventListener('click', function() { self.prevMonth(); });

      //Append the Elements
      this.header.appendChild(this.title);
      this.header.appendChild(right);
      this.header.appendChild(left);
      this.el && this.el.appendChild(this.header);
    }

    this.title.innerHTML = this.current.format('MMMM YYYY');
  }

  Calendar.prototype.drawDayName = function() {
    console.log('111');
    var self = this,
        name_list = ['S', 'M', 'T', 'W', 'T', 'F', 'S'];
    if(!this.day_names) {
      console.log('222');
      this.day_names = createElement('div', 'day-names');
      for (var i = 0; i < name_list.length; i++) {
        var name = createElement('div', 'day-name', name_list[i]);
        this.day_names.appendChild(name)
      }
      this.el && this.el.appendChild(this.day_names);
    }
  }

  Calendar.prototype.drawMonth = function() {
    var self = this;
    if(this.month) {
      this.oldMonth = this.month;
      this.oldMonth.className = 'month out ' + (self.next ? 'next' : 'prev');
      this.oldMonth.addEventListener('webkitAnimationEnd', function() {
        self.oldMonth.parentNode.removeChild(self.oldMonth);
        self.month = createElement('div', 'month');
        self.backFill();
        self.currentMonth();
        self.fowardFill();
        self.el.appendChild(self.month);
        window.setTimeout(function() {
          self.month.className = 'month in ' + (self.next ? 'next' : 'prev');
          var $calendar = $("#calendar");
          $(".ilt-events-list").height($calendar.outerHeight());
        }, 16);
      });
    } else {
        this.month = createElement('div', 'month');
        this.el && this.el.appendChild(this.month);
        this.backFill();
        this.currentMonth();
        this.fowardFill();
        this.month.className = 'month new';
    }
  }

  Calendar.prototype.backFill = function() {
    var clone = this.current.clone();
    var dayOfWeek = clone.day();

    if(!dayOfWeek) { return; }

    clone.subtract('days', dayOfWeek+1);

    for(var i = dayOfWeek; i > 0 ; i--) {
      this.drawDay(clone.add('days', 1));
    }
  }

  Calendar.prototype.fowardFill = function() {
    var clone = this.current.clone().add('months', 1).subtract('days', 1);
    var dayOfWeek = clone.day();

    if(dayOfWeek === 6) { return; }

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
    if(!this.week || day.day() === 0) {
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
      self.openDay(this, current_day);
    });

    //Day Name
    var name = createElement('div', 'day-name', day.format('ddd'));

    //Day Number
    var number = createElement('div', 'day-number', day.format('DD'));


    //Events
    var events = createElement('div', 'day-events');
    this.drawEvents(day, events);

    // outer.appendChild(name);
    outer.appendChild(number);
    // outer.appendChild(events);
    this.week.appendChild(outer);
  }

  Calendar.prototype.drawEvents = function(day, element) {
    var todaysEvents = this.events.reduce(function(memo, ev) {
      if(ev.start_date.isSame(day, 'day') || ev.end_date.isSame(day, 'day') || day.isBetween(ev.start_date, ev.end_date)) {
        memo.push(ev);
      }
      return memo;
    }, []);

    todaysEvents.every(function (ev, index) {
      var evSpan = createElement('span', ev.color);
      element.appendChild(evSpan);
      return index < 1
    });
  }

  Calendar.prototype.getDayClass = function(day) {
    classes = ['day'];
    if(day.month() !== this.current.month()) {
      classes.push('other');
    } else if (today.isSame(day, 'day')) {
      classes.push('today');
    }
    return classes.join(' ');
  }

  Calendar.prototype.openDay = function(el, day) {
    var details, arrow;

    var currentOpened = document.querySelector('.ilt-details');

    //Check to see if there is an open detais box on the current row
    if(currentOpened && currentOpened.parentNode === el.parentNode) {
      details = currentOpened;
      arrow = document.querySelector('.arrow');
    } else {
      //Close the open events on differnt week row
      //currentOpened && currentOpened.parentNode.removeChild(currentOpened);
      if(currentOpened) {
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
        if(ev.start_date.isSame(day, 'day') || ev.end_date.isSame(day, 'day') || day.isBetween(ev.start_date, ev.end_date)) {
          memo.push(ev);
        }
        return memo;
      }, []);

    this.renderEvents(todaysEvents, details);
    this.drawEventsList(todaysEvents);

    var offset = Math.abs(el.offsetLeft - (el.previousSibling || el.nextElementSibling).offsetLeft) / 2;
    arrow.style.left = el.offsetLeft - el.parentNode.offsetLeft + offset + 'px';
  }

  Calendar.prototype.drawEventsList = function (events) {
    event_list.innerHTML = '';
    if (events.length > 0) {
        events.forEach(function (ev) {
            var wrapper = createElement('div', 'ilt-event'),
                link = createElement('a', 'ilt-link', ''),
                title = createElement('div', 'ilt-event-title', ev.title),
                time = createElement('span', 'ilt-event-time', ev.start_at + ' to ' + ev.end_at),
                timezone = createElement('span', 'ilt-event-timezone', ev.timezone),
                instructor = createElement('span', 'ilt-event-instructor', ev.instructor),
                time_icon = createElement('i', 'far fa-clock', ''),
                timezone_icon = createElement('i', 'far fa-globe', ''),
                instructor_icon = createElement('i', 'far fa-user', ''),
                event_day = createElement('section', 'event-day', ''),
                event_day_name = createElement('div', 'event-day-name', ev.start_date.format('dddd')),
                event_day_number = createElement('h2', 'event-day-number', ev.start_date.format('DD'));
            link.href = ev.url;
            time.insertAdjacentElement('afterbegin', time_icon);
            timezone.insertAdjacentElement('afterbegin', timezone_icon);
            instructor.insertAdjacentElement('afterbegin', instructor_icon);
            link.appendChild(title);
            link.appendChild(time);
            link.appendChild(timezone);
            link.appendChild(instructor);
            event_day.appendChild(event_day_name);
            event_day.appendChild(event_day_number);
            wrapper.appendChild(event_day);
            wrapper.appendChild(link);
            event_list.appendChild(wrapper);
        });
    }
    else {
      var wrapper = createElement('div', 'ilt-event'),
          title = createElement('div', 'ilt-event-title', gettext('No Events'));
      wrapper.appendChild(title);
      event_list.appendChild(wrapper);
    }
  }

  Calendar.prototype.drawUpcomingEvents = function () {
    var upcomingEvents = this.events.reduce(function(memo, ev) {
      if(today.isSameOrBefore(ev.end_date, 'day')) {
        memo.push(ev);
      }
      return memo;
    }, []);
    if (upcomingEvents.length > 0) {
      console.log(upcomingEvents);
      upcomingEvents.forEach(function (ev) {
        var wrapper = createElement('div', 'ilt-event'),
            link = createElement('a', 'ilt-link', ''),
            title = createElement('div', 'ilt-event-title', ev.title),
            time = createElement('span', 'ilt-event-time', ev.start_at + ' to ' + ev.end_at),
            timezone = createElement('span', 'ilt-event-timezone', ev.timezone),
            instructor = createElement('span', 'ilt-event-instructor', ev.instructor),
            time_icon = createElement('i', 'far fa-clock', ''),
            timezone_icon = createElement('i', 'far fa-globe', ''),
            instructor_icon = createElement('i', 'far fa-user', ''),
            event_day = createElement('section', 'event-day', ''),
            event_day_name = createElement('div', 'event-day-name', ev.start_date.format('dddd')),
            event_day_number = createElement('h2', 'event-day-number', ev.start_date.format('DD'));
        link.href = ev.url;
        time.insertAdjacentElement('afterbegin', time_icon);
        timezone.insertAdjacentElement('afterbegin', timezone_icon);
        instructor.insertAdjacentElement('afterbegin', instructor_icon);
        link.appendChild(title);
        link.appendChild(time);
        link.appendChild(timezone);
        link.appendChild(instructor);
        event_day.appendChild(event_day_name);
        event_day.appendChild(event_day_number);
        wrapper.appendChild(event_day);
        wrapper.appendChild(link);
        event_list.appendChild(wrapper);
      });
    }
    else {
      var wrapper = createElement('div', 'ilt-event'),
          title = createElement('div', 'ilt-event-title', gettext('No Events'));
      wrapper.appendChild(title);
      event_list.appendChild(wrapper);
    }
  }

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

    if(!events.length) {
      var div = createElement('div', 'event empty');
      var span = createElement('span', '', gettext('No Events'));

      div.appendChild(span);
      wrapper.appendChild(div);
    }

    if(currentWrapper) {
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
      if(memo.indexOf(e) === -1) {
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
    if(className) {
      ele.className = className;
    }
    if(innerText) {
      ele.innderText = ele.textContent = innerText;
    }
    return ele;
  }
}();

!function() {
  var locale = document.documentElement.lang;
  moment.locale(locale);
  var event_data = [],
      calendar = new Calendar('#calendar', event_data);
  $.ajax({
      url: '/enrolled_ilt_sessions',
      success: function (data) {
          var ilt_events = data.ilt_sessions;
          var colors = ['orange', 'blue', 'yellow', 'green'];
          if (ilt_events.length > 0) {
              ilt_events.forEach(function (ev) {
                  ev.start_date = moment.tz(ev.start_at, ev.timezone);
                  ev.end_date = moment.tz(ev.end_at, ev.timezone);
                  ev.color = colors[Math.floor(Math.random() * 4)]
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
              calendar.events = ilt_events;
              calendar.drawMonth();
              calendar.drawUpcomingEvents();
          }
      }
  });

  function addDate(ev) {

  }



}();
