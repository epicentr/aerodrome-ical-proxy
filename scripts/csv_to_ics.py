import csv
from datetime import datetime, timedelta
from icalendar import Calendar, Event
import zoneinfo

# -----------------------------
# CONSTANTS
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
# CREATE CALENDAR
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
# SYNTHETIC ICE CUT GENERATION
# -----------------------------
def build_synthetic_icecuts(rows):
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

        if 5 < gap_minutes <= 10:
            synth_start = end_current
            synth_end = end_current + timedelta(minutes=gap_minutes)

            synthetic.append({
                'start': synth_start.strftime("%m/%d/%Y %I:%M:%S %p"),
                'end': synth_end.strftime("%m/%d/%Y %I:%M:%S %p"),
                'desc': 'ICE CUT?',
                'best_desc': '',
                'resource_id': '1',
                'et_color': '#999999',
                'synthetic': '1'
            })

    return synthetic

# -----------------------------
# MERGE CONCURRENT EVENTS (DISPLAY ONLY)
# -----------------------------
def merge_concurrent_events(events):
    events_sorted = sorted(events, key=lambda r: parse_datetime(r['start']))
    merged = []
    i = 0
    n = len(events_sorted)

    while i < n:
        current = events_sorted[i]
        group = [current]
        start_i = parse_datetime(current['start'])

        j = i + 1
        while j < n:
            if parse_datetime(events_sorted[j]['start']) == start_i:
                group.append(events_sorted[j])
                j += 1
            else:
                break

        if len(group) == 1:
            merged.append(current)
        else:
            descs = [
                (r.get('best_desc') or r.get('desc') or "Event").strip()
                for r in group
            ]
            word_lists = [d.split() for d in descs]

            common_prefix = []
            for words in zip(*word_lists):
                if all(w == words[0] for w in words):
                    common_prefix.append(words[0])
                else:
                    break

            merged_desc = " ".join(common_prefix) if common_prefix else descs[0]

            base = dict(group[0])
            base['desc'] = merged_desc
            base['best_desc'] = merged_desc
            merged.append(base)

        i = j

    return merged

# -----------------------------
# STANDARD HTML GENERATOR
# -----------------------------
# (unchanged — omitted here for brevity, but included in your actual file)
# Your full generate_html() function stays exactly as you provided it.

# -----------------------------
# DIGITAL DISPLAY HTML (1080p)
# -----------------------------
def generate_display_html(filename, events, title):
    events = merge_concurrent_events(events)
    events = sorted(events, key=lambda r: parse_datetime(r['start']))

    html = f"""
<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<title>{title}</title>
<style>
    body {{
        margin: 0;
        padding: 0;
        background: #000;
        color: #fff;
        font-family: Arial, sans-serif;
        overflow: hidden;
    }}
    .screen {{
        width: 1920px;
        height: 1080px;
        padding: 40px;
        box-sizing: border-box;
    }}
    .header {{
        font-size: 3rem;
        font-weight: bold;
        margin-bottom: 10px;
    }}
    .subheader {{
        font-size: 1.6rem;
        margin-bottom: 30px;
        color: #ccc;
    }}
    table {{
        width: 100%;
        border-collapse: collapse;
        font-size: 1.8rem;
    }}
    th {{
        text-align: left;
        border-bottom: 3px solid #444;
        padding-bottom: 10px;
        color: #ccc;
    }}
    td {{
        padding: 14px 10px;
    }}
    tr:nth-child(even) td {{
        background: #111;
    }}
    .icecut {{
        background: #444 !important;
        color: #fff !important;
    }}
    .now {{
        outline: 4px solid #ff4444;
    }}
</style>
</head>
<body>

<div class="screen">
    <div class="header">{title}</div>
    <div class="subheader">Today – {datetime.now().astimezone(LOCAL_TZ).strftime('%A, %B %d')}</div>

    <table>
        <tr>
            <th>Time</th>
            <th>Event</th>
            <th>Location</th>
        </tr>
"""

    now = datetime.now().astimezone(LOCAL_TZ)
    today = now.date()
    marked = False

    for row in events:
        start = parse_datetime(row['start']).replace(tzinfo=LOCAL_TZ)
        end = parse_datetime(row['end']).replace(tzinfo=LOCAL_TZ)

        if start.date() != today:
            continue

        raw = row.get('best_desc') or row.get('desc') or "Event"
        desc_lower = raw.lower()
        duration = int((end - start).total_seconds() / 60)

        keywords = ["takedown", "ice cut", "icecut"]
        is_real = any(k in desc_lower for k in keywords) and duration <= 20
        is_synth = row.get('synthetic') == '1'
        is_icecut = is_real or is_synth

        desc = "ICE CUT" if is_real else ("ICE CUT?" if is_synth else raw)

        is_now = False
        if start <= now <= end or (start > now and not marked):
            is_now = True

        classes = []
        if is_icecut:
            classes.append("icecut")
        if is_now and not marked:
            classes.append("now")
            marked = True

        class_attr = f' class="{" ".join(classes)}"' if classes else ""
        loc = RINK_NAMES.get(row.get('resource_id'), '')

        html += f"""
        <tr{class_attr}>
            <td>{start.strftime('%I:%M %p')} – {end.strftime('%I:%M %p')}</td>
            <td>{desc}</td>
            <td>{loc}</td>
        </tr>
"""

    html += """
    </table>
</div>

<script>
setTimeout(() => location.reload(), 60000);
</script>

</body>
</html>
"""

    with open(filename, "w", encoding="utf-8") as f:
        f.write(html.strip())

# -----------------------------
# MAIN PROCESSOR
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
                add_event(cal_all, row, tzid)
                if resource == "1":
                    add_event(cal_rink, row, tzid)
                elif resource == "2":
                    add_event(cal_locker, row, tzid)
                elif resource == "3":
                    add_event(cal_room, row, tzid)
            except Exception as e:
                print(f"Skipping row: {e}")

    synthetic = build_synthetic_icecuts(all_rows)

    ice_real = []
    for r in all_rows:
        start = parse_datetime(r['start']).replace(tzinfo=LOCAL_TZ)
        end = parse_datetime(r['end']).replace(tzinfo=LOCAL_TZ)
        duration = int((end - start).total_seconds() / 60)
        desc = (r.get("best_desc") or r.get("desc") or "").lower()
        if any(k in desc for k in ["takedown", "ice cut", "icecut"]) and duration <= 20:
            ice_real.append(r)

    ice_page = ice_real + synthetic

    # Write ICS
    with open('facility.ics', 'wb') as f: f.write(cal_all.to_ical())
    with open('facility_rink.ics', 'wb') as f: f.write(cal_rink.to_ical())
    with open('facility_locker.ics', 'wb') as f: f.write(cal_locker.to_ical())
    with open('facility_room.ics', 'wb') as f: f.write(cal_room.to_ical())

    # HTML pages
    generate_html("facility.html", all_rows + synthetic, "Aerodrome – All Events")
    generate_html("facility_rink.html", [r for r in all_rows if r.get("resource_id") == "1"] + synthetic, "Aerodrome – Ice Rink")
    generate_html("facility_locker.html", [r for r in all_rows if r.get("resource_id") == "2"], "Aerodrome – Locker Rooms")
    generate_html("facility_room.html", [r for r in all_rows if r.get("resource_id") == "3"], "Aerodrome – Room Rentals")
    generate_html("facility_icecut.html", ice_page, "Aerodrome – ICE CUT Schedule")

    # NEW: Digital display page
    generate_display_html("facility_display.html", all_rows + synthetic, "Aerodrome – Rink Schedule")

# -----------------------------
# ENTRY POINT
# -----------------------------
if __name__ == "__main__":
    csv_to_ics('events.csv')
