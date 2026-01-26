markdown
# Aerodrome Automated Calendar Feeds

This repository provides automatically updated iCalendar (`.ics`) feeds for Aerodrome events.  
The feeds refresh every **15 minutes** and are generated from the Aerodrome’s official CSV export:

https://lab540.com/aero/scheduleweek-a.csv

Code

A GitHub Action downloads the CSV, converts it into one or more ICS files, and commits the results back into this repository.  
Captains and teams can subscribe to the feeds below using any calendar app (Google Calendar, Apple Calendar, Outlook, etc.).

---

## 📅 Available Calendar Feeds

### **All Events (full facility schedule)**
Includes every event from the CSV feed.

https://raw.githubusercontent.com/epicentr/aerodrome-ical-proxy/main/facility.ics (raw.githubusercontent.com in Bing)

Code

---

## 🧊 Resource‑Specific Feeds

These feeds filter events by `resource_id` in the CSV.

### **Ice Rink — resource_id = 1**
Events occurring on the main ice surface.

https://raw.githubusercontent.com/epicentr/aerodrome-ical-proxy/main/facility_rink.ics (raw.githubusercontent.com in Bing)

Code

### **Locker Room — resource_id = 2**
Events assigned to locker room spaces.

https://raw.githubusercontent.com/epicentr/aerodrome-ical-proxy/main/facility_locker.ics (raw.githubusercontent.com in Bing)

Code

### **Room Rental — resource_id = 3**
Events for meeting rooms, party rooms, or other rental spaces.

https://raw.githubusercontent.com/epicentr/aerodrome-ical-proxy/main/facility_room.ics (raw.githubusercontent.com in Bing)

Code

---

## 🔄 How It Works

1. Every 15 minutes, GitHub Actions:
   - Downloads the latest CSV schedule  
   - Converts it into ICS format  
   - Generates multiple filtered ICS files  
   - Commits the updated files to the repository  

2. Calendar apps subscribed to these URLs automatically refresh and display the latest schedule.

---

## 🛠️ File Structure

.
├── events.csv                                  # Latest downloaded CSV (auto-updated)
├── facility.ics                              # All events
├── facility_rink.ics          # resource_id = 1
├── facility_locker.ics        # resource_id = 2
├── facility_room.ics          # resource_id = 3
└── scripts/
└── csv_to_ics.py        # CSV → ICS converter

Code

---

## 🧪 Troubleshooting

### **Events are missing or not updating**
- Your calendar app may cache feeds; force a manual refresh.
- Check the CSV source to confirm the event exists.
- The CSV may have changed formats; the converter script may need updating.

### **Calendar won’t subscribe**
- Ensure the URL starts with `https://raw.githubusercontent.com/...`
- Some apps require “Add by URL” instead of “Import file”.

---

## 📬 Contact
For issues, improvements, or feature requests (team‑specific feeds, rink name mapping, color coding, etc.), reach out to the league scheduler.


🛠️ Technical Maintainer Guide
This section documents how the automation pipeline works under the hood and how to maintain or extend it. It is intended for technical contributors responsible for keeping the feeds operational.

⚙️ Overview of the Automation Pipeline
The repository uses a GitHub Actions workflow (.github/workflows/refresh.yml) to:

Download the Aerodrome CSV schedule

Convert the CSV into one or more .ics calendar files

Commit the updated files back into the repository

Trigger calendar refreshes for all subscribers

The workflow runs every 15 minutes and can also be triggered manually.

📂 Key Files and Their Roles
File	Purpose
events.csv	Latest downloaded CSV from the Aerodrome feed
facility.ics	Master ICS feed containing all events
facility_rink.ics	Filtered feed for resource_id = 1 (Ice Rink)
facility_locker.ics	Filtered feed for resource_id = 2 (Locker Room)
facility_room.ics	Filtered feed for resource_id = 3 (Room Rental)
scripts/csv_to_ics.py	Python script that parses the CSV and generates all ICS files
.github/workflows/refresh.yml	GitHub Action that orchestrates the entire pipeline
🧩 CSV Format Requirements
The converter expects the following columns:

start — full datetime (M/D/YYYY H:MM:SS AM/PM)

end — full datetime (M/D/YYYY H:MM:SS AM/PM)

desc — event title

description — optional long description

resource_id — numeric resource identifier

resource_area_id — fallback location identifier

If the CSV format changes (column names, date formats, etc.), the converter script must be updated accordingly.

🧠 How the Converter Script Works
scripts/csv_to_ics.py performs the following steps:

Reads events.csv using csv.DictReader

Parses timestamps using Python’s datetime.strptime

Creates four calendars:

All events

Ice Rink (resource_id = 1)

Locker Room (resource_id = 2)

Room Rental (resource_id = 3)

Writes each calendar to its corresponding .ics file

If a row cannot be parsed, the script logs the error and continues.

🔄 How the GitHub Action Works
The workflow:

Checks out the repository

Downloads the CSV from the Aerodrome URL

Installs Python + dependencies

Runs the converter script

Commits any changed files

Force‑pushes to ensure calendar URLs remain stable

The cron schedule is:

Code
*/15 * * * *
This means the pipeline runs every 15 minutes.

🧪 Testing Changes
To test modifications:

Push changes to a branch

Open Actions → Refresh Calendar

Select Run workflow

Verify:

events.csv updates

All .ics files regenerate

No “Skipping row” errors appear

ICS files contain valid VEVENT entries

You can also download the generated .ics files and import them into a calendar app for validation.

🚨 Common Failure Points
Issue	Cause	Fix
ICS files empty	CSV date format changed	Update parse_datetime()
“Skipping row” errors	Unexpected timestamp or missing field	Adjust parsing logic
Workflow not running updated code	Manual run triggered from old commit	Ensure “Use workflow from: main”
CSV downloaded as HTML	Source URL changed or redirected	Update the download URL
➕ Extending the System
You can safely add:

Additional resource‑specific feeds

Team‑specific feeds

Rink name mapping

Color‑coding logic

Filtering (e.g., hide public skating)

Weekly summary exports

All extensions should be implemented inside csv_to_ics.py.

🧹 Maintenance Best Practices
Keep the converter script simple and readable

Log errors but never stop processing the file

Avoid breaking existing ICS filenames (subscribers depend on them)

Test changes in a branch before merging

Monitor workflow logs occasionally for parsing errors
