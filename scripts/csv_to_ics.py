import csv
import os
from datetime import datetime, timedelta
from icalendar import Calendar, Event
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
# CREATE CALENDAR (NO VTIMEZONE)
# -----------------------------
def make_calendar(tzid):
    cal = Calendar()
    cal.add('prodid', '-//Aerodrome League Calendar//mxm.dk//')
    cal.add('version', '2.0')
    # DO NOT add VTIMEZONE — Google will use its internal definition
    return cal

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

    # CRITICAL: Use TZID but NO VTIMEZONE block
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
# GENERATE MOBILE FRIENDLY HTML
# ----------------------------- 
def generate_html(filename, events, title):
    html = f"""
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title}</title>
<style>
    body {{
        font-family: Arial, sans-serif;
        margin: 0;
        padding: 0;
        background: #f7f7f7;
    }}
    h1 {{
        text-align: center;
        padding: 20px;
        background: #003366;
        color: white;
        margin: 0;
        font-size: 1.4rem;
    }}
    table {{
        width: 100%;
        border-collapse: collapse;
        margin: 0;
        font-size: 1rem;
    }}
    th {{
        background: #e0e0e0;
        padding: 10px;
        text-align: left;
        font-size: 0.9rem;
    }}
    td {{
        padding: 12px 10px;
        border-bottom: 1px solid #ddd;
        background: white;
    }}
    tr:nth-child(even) td {{
        background: #f2f2f2;
    }}
    .desc {{
        color: #555;
        font-size: 0.85rem;
        margin-top: 4px;
    }}
</style>
</head>
<body>
<h1>{title}</h1>
<table>
<tr>
    <th>Date</th>
    <th>Start</th>
    <th>End</th>
    <th>Event</th>
</tr>
"""

    for row in events:
        start = parse_datetime(row['start'])
        end = parse_datetime(row['end'])
        desc = row.get('best_desc') or row.get('desc') or "Event"

        html += f"""
<tr>
    <td>{start.strftime('%m/%d')}</td>
    <td>{start.strftime('%I:%M %p')}</td>
    <td>{end.strftime('%I:%M %p')}</td>
    <td>
        {desc}
        <div class="desc">{RINK_NAMES.get(row.get('resource_id'), '')}</div>
    </td>
</tr>
"""

    html += """
</table>
</body>
</html>
"""
    html = html.strip()
    with open(filename, "w", encoding="utf-8") as f:
        f.write(html)



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

    # -----------------------------------------
    # GENERATE HTML PAGES (place this block here)
    # -----------------------------------------
    generate_html("facility.html", all_rows, "Aerodrome – All Events")

    generate_html("facility_rink.html",
                  [r for r in all_rows if r.get("resource_id") == "1"],
                  "Aerodrome – Ice Rink")

    generate_html("facility_locker.html",
                  [r for r in all_rows if r.get("resource_id") == "2"],
                  "Aerodrome – Locker Rooms")

    generate_html("facility_room.html",
                  [r for r in all_rows if r.get("resource_id") == "3"],
                  "Aerodrome – Room Rentals")

    pdf_file = generate_weekly_pdf(all_rows, tzid)
    print(f"Generated weekly PDF: {pdf_file}")

# -----------------------------
# ENTRY POINT
# -----------------------------
if __name__ == "__main__":
    csv_to_ics('events.csv')
