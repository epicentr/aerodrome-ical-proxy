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
# HTML GENERATION
# -----------------------------
def generate_html(filename, events, title):
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
    }}

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
        left: -40px;
        top: 50%;
        transform: translateY(-50%) rotate(-90deg);
        background: #ff4444;
        color: white;
        padding: 4px 6px;
        font-size: 0.7rem;
        border-radius: 4px;
        font-weight: bold;
        letter-spacing: 1px;
        white-space: nowrap;
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
    future_now_marked = False
    now_local_dt = datetime.now().astimezone(LOCAL_TZ)
    today_local = now_local_dt.date()

    for row in events:
        start = parse_datetime(row['start']).replace(tzinfo=LOCAL_TZ)
        end = parse_datetime(row['end']).replace(tzinfo=LOCAL_TZ)
        duration_minutes = int((end - start).total_seconds() / 60)

        raw_desc = row.get('best_desc') or row.get('desc') or "Event"
        desc_lower = raw_desc.lower()

        is_synth = row.get('synthetic') == '1'
        keywords = ["takedown", "ice cut", "icecut"]
        is_real_ice_cut = any(k in desc_lower for k in keywords) and duration_minutes <= 20
        is_ice_cut = is_synth or is_real_ice_cut

        # MAIN PAGES DO NOT HIDE PAST EVENTS
        # (so no "if end < now: continue")

        desc = "ICE CUT?" if is_synth else ("ICE CUT" if is_real_ice_cut else raw_desc)

        date_str = start.strftime('%m/%d')

        # Day separator
        if last_date != date_str:
            html += f"""
<tr class="day-separator">
    <td colspan="4">{start.strftime('%A – %B %d')}</td>
</tr>
"""
            last_date = date_str

        # NOW LOGIC — correct for main pages
        is_current_event = False

        if start.date() == today_local:
            if start <= now_local_dt <= end and not is_ice_cut:
                is_current_event = True
                future_now_marked = True

            elif start > now_local_dt and not future_now_marked and not is_ice_cut:
                is_current_event = True
                future_now_marked = True

        row_id = "current-event" if is_current_event else ""
        row_class = "short-event" if duration_minutes < 60 else ""

        # Color coding
        if is_synth:
            row_style = "background:#999999; color:black;"
        elif is_real_ice_cut:
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
</script>

</body>
</html>
"""

    with open(filename, "w", encoding="utf-8") as f:
        f.write(html.strip())





def generate_display_html(filename, events, title):
    # Merge concurrent events first
    events = merge_concurrent_events(events)
    events = sorted(events, key=lambda r: parse_datetime(r['start']))

    html = f"""
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>{title}</title>
<meta name="viewport" content="width=device-width, initial-scale=1">

<style>
    body {{
        margin: 0;
        padding: 0;
        background-image: url('media/background.png');
        background-size: cover;
        background-position: center;
        background-attachment: fixed;
        font-family: Arial, sans-serif;
        color: #fff;
    }}

    .banner {{
        width: 100%;
        background: #2f6243;
        text-align: center;
    }}

    .banner img {{
        width: 100%;
        max-height: 200px;
        object-fit: cover;
        display: block;
    }}

    .banner-title {{
        margin: 0;
        padding: 20px;
        color: white;
        font-size: 2.4rem;
        background: rgba(0,0,0,0.35);
    }}

    .screen {{
        max-width: 1920px;
        margin: 0 auto;
        padding: 30px 40px;
        background: rgba(0,0,0,0.65);
        box-sizing: border-box;
        height: calc(100vh - 200px);
        overflow-y: auto;
    }}

    .subheader {{
        font-size: 1.6rem;
        margin-bottom: 20px;
        color: #ddd;
    }}

    table {{
        width: 100%;
        border-collapse: collapse;
        font-size: 1.8rem;
        table-layout: fixed;
    }}

    th {{
        text-align: left;
        border-bottom: 3px solid #555;
        padding: 12px 8px;
        color: #eee;
        font-size: 1.6rem;
    }}

    td {{
        padding: 16px 10px;
        vertical-align: middle;
        word-wrap: break-word;
        white-space: normal;
    }}

    tr:nth-child(even) td {{
        background: rgba(0,0,0,0.35);
    }}

    .time-col {{
        width: 300px;
        white-space: nowrap;
        font-size: 1.7rem;
    }}

    .event-col {{
        width: auto;
        font-size: 1.8rem;
    }}

    .loc-col {{
        width: 260px;
        text-align: right;
        color: #ddd;
        white-space: nowrap;
        font-size: 1.6rem;
    }}

    .icecut {{
        background: #444 !important;
        color: #fff !important;
    }}

    /* Rotated NOW badge */
    .now td:first-child {{
        position: relative;
        border-left: 6px solid #ff4444;
    }}

    .now-badge {{
        position: absolute;
        left: -55px;
        top: 50%;
        transform: translateY(-50%) rotate(-90deg);
        background: #ff4444;
        color: white;
        padding: 6px 10px;
        font-size: 1.1rem;
        font-weight: bold;
        border-radius: 4px;
        letter-spacing: 1px;
        white-space: nowrap;
    }}
</style>
</head>
<body>

<div class="banner">
    <img src="media/banner.png" alt="Aerodrome Banner">
    <div class="banner-title">{title}</div>
</div>

<div class="screen">
    <div class="subheader">Today – {datetime.now().astimezone(LOCAL_TZ).strftime('%A, %B %d')}</div>

    <table>
        <tr>
            <th class="time-col">Time</th>
            <th class="event-col">Event</th>
            <th class="loc-col">Location</th>
        </tr>
"""

    now = datetime.now().astimezone(LOCAL_TZ)
    today = now.date()
    future_now_marked = False

    def text_color(bg):
        if not bg or not bg.startswith("#") or len(bg) not in (4, 7):
            return "black"
        bg = bg.lstrip("#")
        if len(bg) == 3:
            bg = "".join(c * 2 for c in bg)
        r = int(bg[0:2], 16)
        g = int(bg[2:4], 16)
        b = int(bg[4:6], 16)
        luminance = (0.299*r + 0.587*g + 0.114*b)
        return "white" if luminance < 140 else "black"

    for row in events:
        start = parse_datetime(row['start']).replace(tzinfo=LOCAL_TZ)
        end = parse_datetime(row['end']).replace(tzinfo=LOCAL_TZ)

        # DISPLAY PAGE hides past events
        if end < now:
            continue

        if start.date() != today:
            continue

        raw = row.get('best_desc') or row.get('desc') or "Event"
        desc_lower = raw.lower()
        duration = int((end - start).total_seconds() / 60)

        keywords = ["takedown", "ice cut", "icecut"]
        is_real = any(k in desc_lower for k in keywords) and duration <= 20
        is_synth = row.get('synthetic') == '1'
        is_icecut = is_real or is_synth

        desc = "ICE CUT?" if is_synth else ("ICE CUT" if is_real else raw)

        # NOW LOGIC — correct for display page
        is_now = False

        if start <= now <= end and not is_icecut:
            is_now = True
            future_now_marked = True

        elif start > now and not future_now_marked and not is_icecut:
            is_now = True
            future_now_marked = True

        classes = ["now"] if is_now else []
        class_attr = f' class="{" ".join(classes)}"' if classes else ""

        # Color coding
        if is_synth:
            row_style = "background:#999999; color:black;"
        elif is_real:
            row_style = "background:#cccccc; color:black;"
        else:
            color = (row.get('et_color') or '').strip()
            if color:
                fg = text_color(color)
                row_style = f"background:{color}; color:{fg};"
            else:
                row_style = ""

        loc = RINK_NAMES.get(row.get('resource_id'), '')

        badge_html = '<div class="now-badge">NOW</div>' if is_now else ""

        html += f"""
        <tr{class_attr} style="{row_style}">
            <td class="time-col">{badge_html}{start.strftime('%I:%M %p')} – {end.strftime('%I:%M %p')}</td>
            <td class="event-col">{desc}</td>
            <td class="loc-col">{loc}</td>
        </tr>
"""

    html += """
    </table>
</div>

<script>
    // Auto-scroll to first NOW event
    window.addEventListener("load", () => {
        const current = document.querySelector(".now");
        if (current) {
            current.scrollIntoView({
                behavior: "smooth",
                block: "center"
            });
        }
    });

    setTimeout(() => location.reload(), 60000);
</script>

</body>
</html>
"""

    with open(filename, "w", encoding="utf-8") as f:
        f.write(html.strip())

def generate_display_multi_html(filename, events):
    # Merge concurrent events
    events = merge_concurrent_events(events)
    events = sorted(events, key=lambda r: parse_datetime(r['start']))

    html = """
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>Schedule Display</title>
<meta name="viewport" content="width=device-width, initial-scale=1">

<style>
    body {
        margin: 0;
        padding: 0;
        background-image: url('media/background.png');
        background-size: cover;
        background-position: center;
        background-attachment: fixed;
        font-family: Arial, sans-serif;
        color: #fff;
    }

    .banner {
        width: 100%;
        background: #2f6243;
        text-align: center;
    }

    .banner img {
        width: 100%;
        max-height: 200px;
        object-fit: cover;
        display: block;
    }

    .banner-title {
        margin: 0;
        padding: 20px;
        color: white;
        font-size: 2.4rem;
        background: rgba(0,0,0,0.35);
    }

    .day-selector {
        text-align: center;
        margin: 20px 0;
    }

    .day-selector button {
        background: #2f6243;
        color: white;
        border: none;
        padding: 10px 18px;
        margin: 0 6px;
        border-radius: 6px;
        font-size: 1.2rem;
        cursor: pointer;
    }

    .day-selector button.active {
        background: #4fa86b;
    }

    .screen {
        max-width: 1920px;
        margin: 0 auto;
        padding: 30px 40px;
        background: rgba(0,0,0,0.65);
        box-sizing: border-box;
        height: calc(100vh - 260px);
        overflow-y: auto;
    }

    table {
        width: 100%;
        border-collapse: collapse;
        font-size: 1.8rem;
        table-layout: fixed;
    }

    th {
        text-align: left;
        border-bottom: 3px solid #555;
        padding: 12px 8px;
        color: #eee;
        font-size: 1.6rem;
    }

    td {
        padding: 16px 10px;
        vertical-align: middle;
        word-wrap: break-word;
        white-space: normal;
    }

    tr:nth-child(even) td {
        background: rgba(0,0,0,0.35);
    }

    .time-col { width: 300px; }
    .event-col { width: auto; }
    .loc-col { width: 260px; text-align: right; }

    .icecut {
        background: #444 !important;
        color: #fff !important;
    }

    .now td:first-child {
        position: relative;
        border-left: 6px solid #ff4444;
    }

    .now-badge {
        position: absolute;
        left: -55px;
        top: 50%;
        transform: translateY(-50%) rotate(-90deg);
        background: #ff4444;
        color: white;
        padding: 6px 10px;
        font-size: 1.1rem;
        font-weight: bold;
        border-radius: 4px;
        letter-spacing: 1px;
        white-space: nowrap;
    }
</style>
</head>
<body>

<div class="banner">
    <img src="media/banner.png">
    <div class="banner-title">Schedule Display</div>
</div>

<div class="day-selector">
    <button onclick="setDay(0)" id="btn0">Today</button>
    <button onclick="setDay(1)" id="btn1">Tomorrow</button>
    <button onclick="setDay(2)" id="btn2">+2 Days</button>
    <button onclick="setDay(3)" id="btn3">+3 Days</button>
    <button onclick="setDay(4)" id="btn4">+4 Days</button>
</div>

<div class="screen">
<table>
<tr>
    <th class="time-col">Time</th>
    <th class="event-col">Event</th>
    <th class="loc-col">Location</th>
</tr>
"""

    # Insert placeholder for JS to fill
    html += "<tbody id='event-body'></tbody>"

    html += """
</table>
</div>

<script>
function getDayParam() {
    const url = new URL(window.location.href);
    return parseInt(url.searchParams.get("day") || "0");
}

function setDay(n) {
    const url = new URL(window.location.href);
    url.searchParams.set("day", n);
    window.location.href = url.toString();
}

const selectedDay = getDayParam();
document.getElementById("btn" + selectedDay).classList.add("active");

// Inject event rows from Python
const events = JSON.parse(`REPLACE_EVENTS_JSON`);

function render() {
    const body = document.getElementById("event-body");
    body.innerHTML = "";

    const now = new Date();
    const today = new Date(now.getFullYear(), now.getMonth(), now.getDate());
    const target = new Date(today);
    target.setDate(today.getDate() + selectedDay);

    let futureNowMarked = false;

    for (const ev of events) {
        const start = new Date(ev.start);
        const end = new Date(ev.end);

        // Filter by selected day
        if (start.toDateString() !== target.toDateString()) continue;

        // Hide past events ONLY on Today
        if (selectedDay === 0 && end < now) continue;

        const isIceCut = ev.is_icecut;

        let isNow = false;

        if (selectedDay === 0) {
            if (start <= now && now <= end && !isIceCut) {
                isNow = true;
                futureNowMarked = true;
            } else if (start > now && !futureNowMarked && !isIceCut) {
                isNow = true;
                futureNowMarked = true;
            }
        }

        const tr = document.createElement("tr");
        if (isNow) tr.classList.add("now");
        if (ev.row_style) tr.setAttribute("style", ev.row_style);

        tr.innerHTML = `
            <td class="time-col">${isNow ? '<div class="now-badge">NOW</div>' : ''}${ev.time}</td>
            <td class="event-col">${ev.desc}</td>
            <td class="loc-col">${ev.loc}</td>
        `;

        body.appendChild(tr);
    }

    // Auto-scroll only on Today
    if (selectedDay === 0) {
        const nowRow = document.querySelector(".now");
        if (nowRow) nowRow.scrollIntoView({ behavior: "smooth", block: "center" });
    }
}

render();
</script>

</body>
</html>
"""

    # Build JSON for JS
    out = []
    for row in events:
        start = parse_datetime(row['start']).replace(tzinfo=LOCAL_TZ)
        end = parse_datetime(row['end']).replace(tzinfo=LOCAL_TZ)

        raw = row.get('best_desc') or row.get('desc') or "Event"
        desc_lower = raw.lower()
        duration = int((end - start).total_seconds() / 60)

        keywords = ["takedown", "ice cut", "icecut"]
        is_real = any(k in desc_lower for k in keywords) and duration <= 20
        is_synth = row.get('synthetic') == '1'
        is_icecut = is_real or is_synth

        desc = "ICE CUT?" if is_synth else ("ICE CUT" if is_real else raw)

        # Color coding
        if is_synth:
            row_style = "background:#999999; color:black;"
        elif is_real:
            row_style = "background:#cccccc; color:black;"
        else:
            color = (row.get('et_color') or '').strip()
            if color:
                fg = "white" if sum(int(color[i:i+2], 16) * w for i, w in zip((1,3,5),(0.299,0.587,0.114))) < 140 else "black"
                row_style = f"background:{color}; color:{fg};"
            else:
                row_style = ""

        out.append({
            "start": start.isoformat(),
            "end": end.isoformat(),
            "desc": desc,
            "loc": RINK_NAMES.get(row.get('resource_id'), ''),
            "time": f"{start.strftime('%I:%M %p')} – {end.strftime('%I:%M %p')}",
            "is_icecut": is_icecut,
            "row_style": row_style
        })

    html = html.replace("REPLACE_EVENTS_JSON", json.dumps(out))

    with open(filename, "w", encoding="utf-8") as f:
        f.write(html)

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
    generate_display_multi_html("display_multi.html", all_rows + synthetic_rows)
    

    # NEW: Digital display page
    generate_display_html("facility_display.html", all_rows + synthetic, "Aerodrome – Rink Schedule")

# -----------------------------
# ENTRY POINT
# -----------------------------
if __name__ == "__main__":
    csv_to_ics('events.csv')
