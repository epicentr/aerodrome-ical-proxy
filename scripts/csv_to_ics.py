import csv
from datetime import datetime
from icalendar import Calendar, Event

def parse_datetime(dt_str):
    return datetime.strptime(dt_str.strip(), "%m/%d/%Y %I:%M:%S %p")

def make_calendar():
    cal = Calendar()
    cal.add('prodid', '-//Aerodrome League Calendar//mxm.dk//')
    cal.add('version', '2.0')
    return cal

def add_event(cal, row):
    start = parse_datetime(row['start'])
    end = parse_datetime(row['end'])
    title = row.get('best_desc') or row.get('desc') or 'Event'
    location = row.get('resource_id') or row.get('resource_area_id') or 'Aerodrome'

    event = Event()
    event.add('summary', title)
    event.add('dtstart', start)
    event.add('dtend', end)
    event.add('location', location)
    event.add('description', row.get('description', ''))
    cal.add_component(event)

def csv_to_ics(csv_path):
    # master calendar
    cal_all = make_calendar()

    # resource-specific calendars
    cal_rink = make_calendar()     # resource_id = 1
    cal_locker = make_calendar()   # resource_id = 2
    cal_room = make_calendar()     # resource_id = 3

    with open(csv_path, newline='') as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            try:
                resource = row.get('resource_id')
                add_event(cal_all, row)

                if resource == "1":
                    add_event(cal_rink, row)
                elif resource == "2":
                    add_event(cal_locker, row)
                elif resource == "3":
                    add_event(cal_room, row)

            except Exception as e:
                print(f"Skipping row due to error: {e}")

    # write all calendars
    with open('facility.ics', 'wb') as f:
        f.write(cal_all.to_ical())

    with open('facility_rink.ics', 'wb') as f:
        f.write(cal_rink.to_ical())

    with open('facility_locker.ics', 'wb') as f:
        f.write(cal_locker.to_ical())

    with open('facility_room.ics', 'wb') as f:
        f.write(cal_room.to_ical())

if __name__ == "__main__":
    csv_to_ics('events.csv')
