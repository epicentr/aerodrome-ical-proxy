import csv
from datetime import datetime
from icalendar import Calendar, Event

def parse_datetime(date_str, time_str):
    # CSV uses YYYY-MM-DD and HH:MM
    return datetime.strptime(f"{date_str} {time_str}", "%Y-%m-%d %H:%M")

def csv_to_ics(csv_path, ics_path):
    cal = Calendar()
    cal.add('prodid', '-//Aerodrome League Calendar//mxm.dk//')
    cal.add('version', '2.0')

    with open(csv_path, newline='') as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            try:
                start = parse_datetime(row['start_date'], row['start'])
                end = parse_datetime(row['start_date'], row['end'])

                title = (
                    row.get('best_desc')
                    or row.get('desc')
                    or row.get('description')
                    or 'Event'
                )

                location = (
                    row.get('resource_area_id')
                    or row.get('resource_id')
                    or 'Aerodrome'
                )

                event = Event()
                event.add('summary', title)
                event.add('dtstart', start)
                event.add('dtend', end)
                event.add('location', location)
                event.add('description', row.get('description', ''))

                cal.add_component(event)

            except Exception as e:
                print(f"Skipping row due to error: {e}")

    with open(ics_path, 'wb') as f:
        f.write(cal.to_ical())

if __name__ == "__main__":
    csv_to_ics('events.csv', 'facility.ics')
