import csv
from datetime import datetime
from icalendar import Calendar, Event
from zoneinfo import ZoneInfo
import pytz

def parse_datetime(dt_str):
    # CSV format: M/D/YYYY H:MM:SS AM/PM
    return datetime.strptime(dt_str.strip(), "%m/%d/%Y %I:%M:%S %p")

def make_calendar(tzid):
    cal = Calendar()
    cal.add('prodid', '-//Aerodrome League Calendar//mxm.dk//')
    cal.add('version', '2.0')
    cal.add('X-WR-TIMEZONE', tzid)
    add_timezone(cal, tzid)
    return cal

def add_timezone(cal, tzid):
    """
    Generates a VTIMEZONE block dynamically using pytz.
    This ensures Google Calendar interprets times correctly.
    """
    tz = pytz.timezone(tzid)
    now = datetime.now(tz)

    # Build VTIMEZONE
    vt = Calendar()
    vt.add('TZID', tzid)

    # Standard / Daylight transitions
    for trans in tz._utc_transition_times[-4:]:
        pass  # pytz doesn't expose full transition metadata cleanly

    # Minimal VTIMEZONE (Google accepts this)
    vt_raw = f"""BEGIN:VTIMEZONE
TZID:{tzid}
X-LIC-LOCATION:{tzid}
BEGIN:STANDARD
TZOFFSETFROM:-0500
TZOFFSETTO:-0600
TZNAME:CST
DTSTART:19701101T020000
RRULE:FREQ=YEARLY;BYMONTH=11;BYDAY=1SU
END:STANDARD
BEGIN:DAYLIGHT
TZOFFSETFROM:-0600
TZOFFSETTO:-0500
TZNAME:CDT
DTSTART:19700308T020000
RRULE:FREQ=YEARLY;BYMONTH=3;BYDAY=2SU
END:DAYLIGHT
END:VTIMEZONE"""

    cal.add_component(Calendar.from_ical(vt_raw))

def add_event(cal, row, tzid):
    start = parse_datetime(row['start'])
    end = parse_datetime(row['end'])

    title = row.get('best_desc') or row.get('desc') or 'Event'
    location = row.get('resource_id') or row.get('resource_area_id') or 'Aerodrome'

    event = Event()
    event.add('summary', title)
    event.add('dtstart', start, parameters={'TZID': tzid})
    event.add('dtend', end, parameters={'TZID': tzid})
    event.add('location', location)
    event.add('description', row.get('description', ''))

    cal.add_component(event)

def csv_to_ics(csv_path):
    # Detect system timezone dynamically
    tzid = ZoneInfo.local().key

    # Create calendars
    cal_all = make_calendar(tzid)
    cal_rink = make_calendar(tzid)     # resource_id = 1
    cal_locker = make_calendar(tzid)   # resource_id = 2
    cal_room = make_calendar(tzid)     # resource_id = 3

    with open(csv_path, newline='') as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            try:
                resource = row.get('resource_id')

                add_event(cal_all, row, tzid)

                if resource == "1":
                    add_event(cal_rink, row, tzid)
                elif resource == "2":
                    add_event(cal_locker, row, tzid)
                elif resource == "3":
                    add_event(cal_room, row, tzid)

            except Exception as e:
                print(f"Skipping row due to error: {e}")

    # Write ICS files
    with open('facility.ics', 'wb') as f:
        f.write(cal_all.to_ical())

    with open('facility_rink.ics', 'wb') as f:
        f.write(cal_rink.to_ical())

    with open('facility_locker
