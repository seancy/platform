import * as momentTemp from 'moment'
import * as momentTZ from 'moment-timezone'
import './commerce/credit.js'
import './dashboard/credit.js'
import './dashboard/donation.js'
import './dashboard/dropdown.js'
import './dashboard/legacy.js'
import './dashboard/progress_ring.js'
import './dashboard/track_events.js'

window.moment = momentTemp
window.moment.tz = momentTZ
