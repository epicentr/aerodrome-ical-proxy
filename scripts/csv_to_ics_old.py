import csv
import os
from datetime import datetime, timedelta
from icalendar import Calendar, Event
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
import zoneinfo

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

    # Use TZID but NO VTIMEZONE block
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
    # Sort events by start time so day separators appear correctly
    events = sorted(events, key=lambda r: parse_datetime(r['start']))

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
        background-image: url('media/background.png');
        background-size: cover;
        background-position: center;
        background-attachment: fixed;
        color: #333;
    }}

    .banner {{
        width: 100%;
        margin: 0;
        padding: 0;
        background: #2f6243;
        text-align: center;
    }}

    .banner img {{
        width: 100%;
        max-height: 200px;
        object-fit: cover;
        display: block;
    }}

    h1 {{
        margin: 0;
        padding: 20px;
        color: white;
        font-size: 1.8rem;
        background: rgba(0,0,0,0.35);
    }}

    .container {{
        padding: 20px;
        max-width: 900px;
        margin: 20px auto;
        background: rgba(255,255,255,0.92);
        border-radius: 10px;
    }}

    table {{
        width: 100%;
        border-collapse: collapse;
        margin: 0;
        font-size: 1rem;
        table-layout: fixed;
    }}

    th {{
        background: #e0e0e0;
        padding: 10px;
        text-align: left;
        font-size: 0.9rem;
        position: sticky;
        top: 0;
        z-index: 5;
        border-bottom: 2px solid #ccc;
    }}

    td {{
        padding: 12px 10px;
        border-bottom: 1px solid #ddd;
        word-wrap: break-word;
        white-space: normal;
        transition: background 0.2s ease;
    }}

    tr:hover td {{
        background: rgba(0,0,0,0.08);
    }}

    th:nth-child(1), td:nth-child(1) {{ min-width: 8ch; }}
    th:nth-child(2), td:nth-child(2) {{ min-width: 8ch; }}
    th:nth-child(3), td:nth-child(3) {{ min-width: 8ch; }}

    .day-separator td {{
        background: #2f6243 !important;
        color: white !important;
        font-weight: bold;
        padding: 8px;
        text-align: center;
        border-top: 2px solid #1e402c;
        border-bottom: 2px solid #1e402c;
        position: sticky;
        top: 42px;
        z-index: 4;
    }}

    .desc {{
        color: inherit;
        font-size: 0.85rem;
        margin-top: 4px;
    }}
</style>
</head>

<body>

<div class="banner">
    <img src="media/banner.png" alt="Aerodrome Banner">
    <h1>{title}</h1>
</div>

<div class="container">
<table>
<tr>
    <th>Date</th>
    <th>Start</th>
    <th>End</th>
    <th>Event</th>
</tr>
"""

    last_date = None
    current_event_marked = False

    now_local_dt = datetime.now().astimezone()
    today_local = now_local_dt.date()
    local_tz = zoneinfo.ZoneInfo("America/Chicago")

    for row in events:
        # Parse and localize times
        start = parse_datetime(row['start'])
        end = parse_datetime(row['end'])
        start = start.replace(tzinfo=local_tz)
        end = end.replace(tzinfo=local_tz)

        duration_minutes = int((end - start).total_seconds() / 60)

        raw_desc = row.get('best_desc') or row.get('desc') or "Event"
        desc_lower = raw_desc.lower()

        # ICE CUT detection (Option A)
        is_ice_cut = ("takedown" in desc_lower) and (duration_minutes == 10)

        # Replace displayed text
        desc = "ICE CUT" if is_ice_cut else raw_desc

        date_str = start.strftime('%m/%d')

        # Insert day separator
        if last_date != date_str:
            html += f"""
<tr class="day-separator">
    <td colspan="4">{start.strftime('%A – %B %d')}</td>
</tr>
"""
            last_date = date_str

        # TIME-BASED CURRENT EVENT LOGIC
        is_today = start.date() == today_local
        is_current_event = False

        if is_today:
            if start <= now_local_dt <= end:
                # Event happening right now
                is_current_event = True
            elif start > now_local_dt and not current_event_marked:
                # Next upcoming event today
                is_current_event = True

        row_id = "current-event" if (is_current_event and not current_event_marked) else ""
        if row_id:
            current_event_marked = True

        # Color coding
        color = row.get('et_color', '').strip()

        def text_color(bg):
            if not bg or not bg.startswith("#") or len(bg) not in (4, 7):
                return "black"
            bg = bg.lstrip("#")
            if len(bg) == 3:
                bg = "".join(c*2 for c in bg)
            r = int(bg[0:2], 16)
            g = int(bg[2:4], 16)
            b = int(bg[4:6], 16)
            luminance = (0.299*r + 0.587*g + 0.114*b)
            return "white" if luminance < 140 else "black"

        fg = text_color(color)
        row_style = f"background:{color}; color:{fg};" if color else ""

        html += f"""
<tr {'id="current-event"' if row_id else ''} style="{row_style}">
    <td>{date_str}</td>
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
</div>

<script>
    const el = document.getElementById("current-event");
    if (el) {
        el.scrollIntoView({ behavior: "smooth", block: "center" });
    }
</script>

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

    # Write ICS files
    with open('facility.ics', 'wb') as f:
        f.write(cal_all.to_ical())

    with open('facility_rink.ics', 'wb') as f:
        f.write(cal_rink.to_ical())

    with open('facility_locker.ics', 'wb') as f:
        f.write(cal_locker.to_ical())

    with open('facility_room.ics', 'wb') as f:
        f.write(cal_room.to_ical())

    # Generate HTML pages
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

    # ICE CUT PAGE (desc contains "takedown" and duration == 10 minutes)
    ice_cut_rows = []
    local_tz = zoneinfo.ZoneInfo("America/Chicago")

    for r in all_rows:
        start = parse_datetime(r['start']).replace(tzinfo=local_tz)
        end = parse_datetime(r['end']).replace(tzinfo=local_tz)
        duration = int((end - start).total_seconds() / 60)
        desc = (r.get("best_desc") or r.get("desc") or "").lower()

        if "takedown" in desc and duration == 10:
            ice_cut_rows.append(r)

    generate_html("facility_icecut.html",
                  ice_cut_rows,
                  "Aerodrome – ICE CUT Schedule")

    pdf_file = generate_weekly_pdf(all_rows, tzid)
    print(f"Generated weekly PDF: {pdf_file}")

# -----------------------------
# ENTRY POINT
# -----------------------------
if __name__ == "__main__":
    csv_to_ics('events.csv')
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
    # Sort events by start time so day separators appear correctly
    events = sorted(events, key=lambda r: parse_datetime(r['start']))

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
        background-image: url('media/background.png');
        background-size: cover;
        background-position: center;
        background-attachment: fixed;
        color: #333;
    }}

    .banner {{
        width: 100%;
        margin: 0;
        padding: 0;
        background: #2f6243;
        text-align: center;
    }}

    .banner img {{
        width: 100%;
        max-height: 200px;
        object-fit: cover;
        display: block;
    }}

    h1 {{
        margin: 0;
        padding: 20px;
        color: white;
        font-size: 1.8rem;
        background: rgba(0,0,0,0.35);
    }}

    .container {{
        padding: 20px;
        max-width: 900px;
        margin: 20px auto;
        background: rgba(255,255,255,0.92);
        border-radius: 10px;
    }}

    table {{
        width: 100%;
        border-collapse: collapse;
        margin: 0;
        font-size: 1rem;
        table-layout: fixed;
    }}

    th {{
        background: #e0e0e0;
        padding: 10px;
        text-align: left;
        font-size: 0.9rem;
        position: sticky;
        top: 0;
        z-index: 5;
        border-bottom: 2px solid #ccc;
    }}

    td {{
        padding: 12px 10px;
        border-bottom: 1px solid #ddd;
        word-wrap: break-word;
        white-space: normal;
        transition: background 0.2s ease;
    }}

    tr:hover td {{
        background: rgba(0,0,0,0.08);
    }}

    th:nth-child(1), td:nth-child(1) {{ min-width: 8ch; }}
    th:nth-child(2), td:nth-child(2) {{ min-width: 8ch; }}
    th:nth-child(3), td:nth-child(3) {{ min-width: 8ch; }}

    .day-separator td {{
        background: #2f6243 !important;
        color: white !important;
        font-weight: bold;
        padding: 8px;
        text-align: center;
        border-top: 2px solid #1e402c;
        border-bottom: 2px solid #1e402c;
        position: sticky;
        top: 42px;
        z-index: 4;
    }}

    .desc {{
        color: inherit;
        font-size: 0.85rem;
        margin-top: 4px;
    }}
</style>
</head>

<body>

<div class="banner">
    <img src="media/banner.png" alt="Aerodrome Banner">
    <h1>{title}</h1>
</div>

<div class="container">
<table>
<tr>
    <th>Date</th>
    <th>Start</th>
    <th>End</th>
    <th>Event</th>
</tr>
"""

    last_date = None
    current_event_marked = False

    now_local_dt = datetime.now().astimezone()
    today_local = now_local_dt.date()

    for row in events:
        start = parse_datetime(row['start'])
        end = parse_datetime(row['end'])
        duration_minutes = int((end - start).total_seconds() / 60)

        raw_desc = row.get('best_desc') or row.get('desc') or "Event"
        desc_lower = raw_desc.lower()

        # ICE CUT detection (Option A)
        is_ice_cut = ("takedown" in desc_lower) and (duration_minutes == 10)

        # Replace displayed text
        desc = "ICE CUT" if is_ice_cut else raw_desc

        date_str = start.strftime('%m/%d')

        # Insert day separator
        if last_date != date_str:
            html += f"""
<tr class="day-separator">
    <td colspan="4">{start.strftime('%A – %B %d')}</td>
</tr>
"""
            last_date = date_str

        # TIME-BASED CURRENT EVENT LOGIC
        is_today = start.date() == today_local
        is_current_event = False

        if is_today:
            if start <= now_local_dt <= end:
                is_current_event = True
            elif start > now_local_dt and not current_event_marked:
                is_current_event = True

        row_id = "current-event" if (is_current_event and not current_event_marked) else ""
        if row_id:
            current_event_marked = True

        # Color coding
        color = row.get('et_color', '').strip()

        def text_color(bg):
            if not bg or not bg.startswith("#") or len(bg) not in (4, 7):
                return "black"
            bg = bg.lstrip("#")
            if len(bg) == 3:
                bg = "".join(c*2 for c in bg)
            r = int(bg[0:2], 16)
            g = int(bg[2:4], 16)
            b = int(bg[4:6], 16)
            luminance = (0.299*r + 0.587*g + 0.114*b)
            return "white" if luminance < 140 else "black"

        fg = text_color(color)
        row_style = f"background:{color}; color:{fg};" if color else ""

        html += f"""
<tr {'id="current-event"' if row_id else ''} style="{row_style}">
    <td>{date_str}</td>
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
</div>

<script>
    const el = document.getElementById("current-event");
    if (el) {
        el.scrollIntoView({ behavior: "smooth", block: "center" });
    }
</script>

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

    # Write ICS files
    with open('facility.ics', 'wb') as f:
        f.write(cal_all.to_ical())

    with open('facility_rink.ics', 'wb') as f:
        f.write(cal_rink.to_ical())

    with open('facility_locker.ics', 'wb') as f:
        f.write(cal_locker.to_ical())

    with open('facility_room.ics', 'wb') as f:
        f.write(cal_room.to_ical())

    # Generate HTML pages
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

    # ICE CUT PAGE
    ice_cut_rows = []
    for r in all_rows:
        start = parse_datetime(r['start'])
        end = parse_datetime(r['end'])
        duration = int((end - start).total_seconds() / 60)
        desc = (r.get("best_desc") or r.get("desc") or "").lower()

        if "takedown" in desc and duration == 10:
            ice_cut_rows.append(r)

    generate_html("facility_icecut.html",
                  ice_cut_rows,
                  "Aerodrome – ICE CUT Schedule")

    pdf_file = generate_weekly_pdf(all_rows, tzid)
    print(f"Generated weekly PDF: {pdf_file}")


# -----------------------------
# ENTRY POINT
# -----------------------------
if __name__ == "__main__":
    csv_to_ics('events.csv')
