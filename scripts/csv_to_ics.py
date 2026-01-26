import csv
import os
from datetime import datetime, timedelta
from icalendar import Calendar, Event
from zoneinfo import ZoneInfo
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas

# -----------------------------
# RINK NAME MAPPING
# -----------------------------
RINK_NAMES = {
    "1": "Ice Rink",
    "2": "Locker Room",
    "3": "Room Rental"
}

# -----------------------------
# PARSE CSV DATETIME
# -----------------------------
def parse_datetime(dt_str):
    return datetime.strptime(dt_str.strip(), "%m/%d/%Y %I:%M:%S %p")

# -----------------------------
# CREATE CALENDAR WITH TIMEZONE
# -----------------------------
def make_calendar(tzid):
    cal = Calendar()
    cal.add('prodid', '-//Aerodrome League Calendar//mxm.dk//')
    cal.add('version', '2.0')
    cal.add('X-WR-TIMEZONE', tzid)
    add_timezone(cal, tzid)
    return cal

# -----------------------------
# ADD STATIC VTIMEZONE BLOCK
# -----------------------------
def add_timezone(cal, tzid):
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

# -----------------------------
# ADD EVENT TO CALENDAR
# -----------------------------
def add_event(cal, row, tzid):
    start = parse_datetime(row['start'])
    end = parse_datetime(row['end'])

    title = row.get('best_desc') or row.get('desc') or 'Event'
    location = RINK_NAMES.get(row.get('resource_id'), 'Aerodrome')

    event = Event()
    event.add('summary', title)
    event.add('dtstart', start, parameters={'TZID': tzid})
    event.add('dtend', end, parameters={'TZID': tzid})
    event.add('location', location)
    event.add('description', row.get('description', ''))

    cal.add_component(event)

# -----------------------------
# WEEKLY PDF EXPORT
# -----------------------------
def generate_weekly_pdf(rows, tzid):
    today = datetime.now()
    monday = today - timedelta(days=today.weekday())
    sunday = monday + timedelta(days=6)

    filename = f"week_{monday.strftime('%Y-%m-%d')}.pdf"
    c = canvas.Canvas(filename, pagesize=letter)

    c.setFont("Helvetica-Bold", 16)
    c.drawString(50, 750, f"Aerodrome Weekly Schedule ({monday.strftime('%b %d')} - {sunday.strftime('%b %d')})")

    y = 720
    c.setFont("Helvetica", 10)

    for row in rows:
        start = parse_datetime(row['start'])
        if monday <= start <= sunday:
            line = f"{start.strftime('%a %m/%d %I:%M %p')} — {row['desc']} ({RINK_NAMES.get(row['resource_id'], 'Unknown')})"
            c.drawString(50, y, line)
            y -= 14
            if y < 50:
                c.showPage()
                y = 750

    c.save()
    return filename

# -----------------------------
# MAIN CSV → ICS PROCESSOR
# -----------------------------
def csv_to_ics(csv_path):
    # FIXED TIMEZONE — REQUIRED FOR GOOGLE CALENDAR
    tzid = "America/Chicago"

    cal_all = make_calendar(tzid)
    cal_rink = make_calendar(tzid)
    cal_locker = make_calendar(tzid)
    cal_room = make_calendar(tzid)

    all_rows = []

    with open(csv_path, newline='') as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            all_rows.append(row)
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

    with open('facility.ics', 'wb') as f:
        f.write(cal_all.to_ical())

    with open('facility_rink.ics', 'wb') as f:
        f.write(cal_rink.to_ical())

    with open('facility_locker.ics', 'wb') as f:
        f.write(cal_locker.to_ical())

    with open('facility_room.ics', 'wb') as f:
        f.write(cal_room.to_ical())

    pdf_file = generate_weekly_pdf(all_rows, tzid)
    print(f"Generated weekly PDF: {pdf_file}")

# -----------------------------
# ENTRY POINT
# -----------------------------
if __name__ == "__main__":
    csv_to_ics('events.csv')
