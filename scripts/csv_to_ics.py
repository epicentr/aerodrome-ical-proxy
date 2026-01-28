import csv
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

LOCAL_TZID = "America/Chicago"
LOCAL_TZ = zoneinfo.ZoneInfo(LOCAL_TZID)

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
# SYNTHETIC ICE CUT GENERATION
# -----------------------------
def build_synthetic_icecuts(rows):
    """
    Build synthetic ICE CUT? events based on gaps between Ice Rink events.
    Gap > 5 minutes and <= 10 minutes => synthetic ICE CUT? with duration = gap.
    Only for resource_id == "1" (Ice Rink).
    """
    rink_events = [r for r in rows if r.get("resource_id") == "1"]
    rink_events_sorted = sorted(rink_events, key=lambda r: parse_datetime(r['start']))

    synthetic = []

    for i in range(len(rink_events_sorted) - 1):
        current = rink_events_sorted[i]
        nxt = rink_events_sorted[i + 1]

        start_current = parse_datetime(current['start']).replace(tzinfo=LOCAL_TZ)
        end_current = parse_datetime(current['end']).replace(tzinfo=LOCAL_TZ)
        start_next = parse_datetime(nxt['start']).replace(tzinfo=LOCAL_TZ)

        gap_minutes = (start_next - end_current).total_seconds() / 60.0

        if gap_minutes > 5 and gap_minutes <= 10:
            synth_start = end_current
            synth_end = end_current + timedelta(minutes=gap_minutes)

            synth_row = {
                'start': synth_start.strftime("%m/%d/%Y %I:%M:%S %p"),
                'end': synth_end.strftime("%m/%d/%Y %I:%M:%S %p"),
                'desc': 'ICE CUT?',
                'best_desc': '',
                'resource_id': '1',
                'et_color': '#999999',
                'synthetic': '1'
            }
            synthetic.append(synth_row)

    return synthetic

# -----------------------------
# HTML GENERATION
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

    /* Dark mode toggle inside container */
    .controls {{
        display: flex;
        justify-content: flex-end;
        align-items: center;
        margin-bottom: 10px;
        font-size: 0.9rem;
    }}

    .dark-toggle label {{
        cursor: pointer;
        user-select: none;
    }}

    table {{
        width: 100%;
        border-collapse: collapse;
        margin: 0;
        font-size: 1rem;
        table-layout: fixed;
    }}

    /* Sticky header */
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

    /* Narrow Date/Start/End columns */
    th:nth-child(1), td:nth-child(1) {{ min-width: 4ch; }}
    th:nth-child(2), td:nth-child(2) {{ min-width: 4ch; }}
    th:nth-child(3), td:nth-child(3) {{ min-width: 4ch; }}

    /* Sticky day separator */
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

    /* Short events (< 60 minutes) 50% height */
    .short-event td {{
        padding-top: 6px !important;
        padding-bottom: 6px !important;
    }}

    /* Rotated NOW marker */
    #current-event td {{
        border-left: 6px solid #ff4444;
        position: relative;
    }}

    #current-event td:first-child::before {{
        content: "NOW";
        position: absolute;
        left: -40px;              /* distance from table */
        top: 50%;
        transform: translateY(-50%) rotate(-90deg);
        transform-origin: center;
        background: #ff4444;
        color: white;
        padding: 4px 6px;
        font-size: 0.7rem;
        border-radius: 4px;
        font-weight: bold;
        letter-spacing: 1px;
        text-align: center;
        white-space: nowrap;
    }}

    /* Dark mode */
    body.dark {{
        background: #111 !important;
        color: #eee !important;
    }}

    body.dark .container {{
        background: rgba(30,30,30,0.9) !important;
    }}

    body.dark table {{
        color: #eee !important;
    }}

    body.dark th {{
        background: #333 !important;
        color: #eee !important;
    }}

    body.dark td {{
        border-bottom: 1px solid #444 !important;
    }}

    body.dark .day-separator td {{
        background: #444 !important;
        color: #eee !important;
    }}

    body.dark .banner {{
        background: #222 !important;
    }}
</style>
</head>

<body>

<div class="banner">
    <img src="media/banner.png" alt="Aerodrome Banner">
    <h1>{title}</h1>
</div>

<div class="container">
    <div class="controls">
        <div class="dark-toggle">
            <label>
                <input type="checkbox" id="darkModeSwitch">
                🌙 Dark Mode
            </label>
        </div>
    </div>

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

    now_local_dt = datetime.now().astimezone(LOCAL_TZ)
    today_local = now_local_dt.date()

    for row in events:
        start = parse_datetime(row['start']).replace(tzinfo=LOCAL_TZ)
        end = parse_datetime(row['end']).replace(tzinfo=LOCAL_TZ)
        duration_minutes = int((end - start).total_seconds() / 60)

        raw_desc = row.get('best_desc') or row.get('desc') or "Event"
        desc_lower = raw_desc.lower()

        is_synthetic = row.get('synthetic') == '1'

        # Real ICE CUT detection (broad match, <= 20 minutes)
        keywords = ["takedown", "ice cut", "icecut"]
        is_real_ice_cut = any(k in desc_lower for k in keywords) and duration_minutes <= 20

        # Overall ICE CUT flag
        is_ice_cut = is_synthetic or is_real_ice_cut

        # Display text
        if is_synthetic:
            desc = "ICE CUT?"
        elif is_real_ice_cut:
            desc = "ICE CUT"
        else:
            desc = raw_desc

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

        # Short event class
        row_class = "short-event" if duration_minutes < 60 else ""

        # Color coding
        if is_synthetic:
            # Synthetic ICE CUT? darker gray
            row_style = "background:#999999; color:black;"
        elif is_real_ice_cut:
            # Real ICE CUT light gray
            row_style = "background:#cccccc; color:black;"
        else:
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

        id_attr = f' id="{row_id}"' if row_id else ""
        class_attr = f' class="{row_class}"' if row_class else ""

        html += f"""
<tr{id_attr}{class_attr} style="{row_style}">
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
    // Auto-scroll to current event
    const el = document.getElementById("current-event");
    if (el) {
        el.scrollIntoView({ behavior: "smooth", block: "center" });
    }

    // Dark mode toggle
    const toggle = document.getElementById("darkModeSwitch");
    if (toggle) {
        toggle.addEventListener("change", () => {
            document.body.classList.toggle("dark", toggle.checked);
        });
    }
</script>

</body>
</html>
"""

    with open(filename, "w", encoding="utf-8") as f:
        f.write(html.strip())

# -----------------------------
# MAIN CSV → ICS PROCESSOR
# -----------------------------
def csv_to_ics(csv_path):
    tzid = LOCAL_TZID

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

                # ICS: only real events, no synthetic
                add_event(cal_all, row, tzid)

                if resource == "1":
                    add_event(cal_rink, row, tzid)
                elif resource == "2":
                    add_event(cal_locker, row, tzid)
                elif resource == "3":
                    add_event(cal_room, row, tzid)

            except Exception as e:
                print(f"Skipping row due to error: {e}")

    # Build synthetic ICE CUT? events (only for rink)
    synthetic_rows = build_synthetic_icecuts(all_rows)

    # Real ICE CUT rows (for ICE CUT page)
    ice_cut_rows_real = []
    for r in all_rows:
        start = parse_datetime(r['start']).replace(tzinfo=LOCAL_TZ)
        end = parse_datetime(r['end']).replace(tzinfo=LOCAL_TZ)
        duration = int((end - start).total_seconds() / 60)
        desc = (r.get("best_desc") or r.get("desc") or "").lower()
        keywords = ["takedown", "ice cut", "icecut"]
        if any(k in desc for k in keywords) and duration <= 20:
            ice_cut_rows_real.append(r)

    # ICE CUT page events: real + synthetic, chronological
    ice_cut_page_rows = ice_cut_rows_real + synthetic_rows

    # Write ICS files (no synthetic)
    with open('facility.ics', 'wb') as f:
        f.write(cal_all.to_ical())

    with open('facility_rink.ics', 'wb') as f:
        f.write(cal_rink.to_ical())

    with open('facility_locker.ics', 'wb') as f:
        f.write(cal_locker.to_ical())

    with open('facility_room.ics', 'wb') as f:
        f.write(cal_room.to_ical())

    # HTML pages
    # facility.html: all events + synthetic
    generate_html("facility.html", all_rows + synthetic_rows, "Aerodrome – All Events")

    # facility_rink.html: rink events + synthetic
    rink_rows = [r for r in all_rows if r.get("resource_id") == "1"]
    generate_html("facility_rink.html", rink_rows + synthetic_rows, "Aerodrome – Ice Rink")

    # facility_locker.html: locker events only (no synthetic)
    locker_rows = [r for r in all_rows if r.get("resource_id") == "2"]
    generate_html("facility_locker.html", locker_rows, "Aerodrome – Locker Rooms")

    # facility_room.html: room events only (no synthetic)
    room_rows = [r for r in all_rows if r.get("resource_id") == "3"]
    generate_html("facility_room.html", room_rows, "Aerodrome – Room Rentals")

    # facility_icecut.html: real + synthetic ICE CUTs
    generate_html("facility_icecut.html", ice_cut_page_rows, "Aerodrome – ICE CUT Schedule")

    # Weekly PDF (real events only)
    pdf_file = generate_weekly_pdf(all_rows, tzid)
    print(f"Generated weekly PDF: {pdf_file}")

# -----------------------------
# ENTRY POINT
# -----------------------------
if __name__ == "__main__":
    csv_to_ics('events.csv')
