import requests
import json
from datetime import datetime, timedelta
from uuid import uuid4

# URL to the JSON file
url = "https://firebasestorage.googleapis.com/v0/b/abfall-ammerland.appspot.com/o/and%2F5%2Fawbapp.json?alt=media"

# Load JSON file as text
response = requests.get(url)
if response.status_code == 200:
    raw_text = response.text
    # Split JSON blocks based on the '##' delimiter
    blocks = raw_text.split('##')
    # Parse each JSON block
    data = [json.loads(block) for block in blocks if block.strip()]
else:
    print("Error loading the JSON file.")
    exit()

# Function to display streets based on the location ID and select a street
def display_streets_for_ort(ortid):
    streets = [s for s in data[0] if s['ortid'] == ortid]
    
    if not streets:
        print(f"No streets found for location with ID {ortid}.")
        return None
    
    print(f"Streets in location with ID {ortid}:")
    for street in streets:
        print(f"{street['id']}: {street['bez']}")

    street_id = int(input("Enter the ID of the desired street: "))
    selected_street = next((s for s in streets if s['id'] == street_id), None)
    
    if selected_street:
        return selected_street['id'], selected_street['bez']
    else:
        print("Invalid street ID.")
        return None

# Function to filter waste collection dates for a specific street or section
def get_abfalltermine(ortid, street_id, street_name):
    sections = [sec for sec in data[1] if sec['strid'] == street_id]
    
    if sections:
        print(f"The street '{street_name}' has the following sections:")
        for section in sections:
            print(f"{section['id']}: {section['grenze']}")
        
        option = input("Do you want to display all sections or select a specific section? (all/enter ID): ")
        if option.lower() == "all":
            # Show all sections
            for section in sections:
                print(f"\nWaste collection dates for section '{section['grenze']}':")
                section_id = section['id']
                waste_entries = [entry for entry in data[3] if entry['strid'] == section_id]
                display_abfalltermine(get_waste_dates(waste_entries))
        else:
            # Show only the selected section
            try:
                selected_section_id = int(option)
                selected_section = next((sec for sec in sections if sec['id'] == selected_section_id), None)
                if selected_section:
                    print(f"\nWaste collection dates for section '{selected_section['grenze']}':")
                    waste_entries = [entry for entry in data[3] if entry['strid'] == selected_section_id]
                    display_abfalltermine(get_waste_dates(waste_entries))
                else:
                    print("Invalid section ID.")
            except ValueError:
                print("Invalid input.")
    else:
        print(f"The street '{street_name}' has no sections.")
        waste_entries = [entry for entry in data[3] if entry['strid'] == street_id]
        display_abfalltermine(get_waste_dates(waste_entries))

# Function to display waste collection dates
def display_abfalltermine(collection_days):
    if collection_days:
        for type, date in sorted(collection_days, key=lambda x: x[1]):
            print(f"{type}: {date.strftime('%Y-%m-%d')}")
        save_abfalltermine_to_ics(collection_days)
    else:
        print("No waste collection dates found.")

# Function to save waste collection dates to an ICS calendar file
def save_abfalltermine_to_ics(collection_days, filename="waste_collection.ics"):
    header = "BEGIN:VCALENDAR\nVERSION:2.0\nPRODID:-//Waste Collection//EN\n"
    events = []
    for abfall_type, date in sorted(collection_days, key=lambda x: x[1]):
        start = date.strftime("%Y%m%d")
        end = (date + timedelta(days=1)).strftime("%Y%m%d")
        uid = str(uuid4())
        event = (
            "BEGIN:VEVENT\n"
            f"UID:{uid}\n"
            f"DTSTAMP:{datetime.utcnow().strftime('%Y%m%dT%H%M%SZ')}\n"
            f"SUMMARY:{abfall_type}\n"
            f"DTSTART;VALUE=DATE:{start}\n"
            f"DTEND;VALUE=DATE:{end}\n"
            "END:VEVENT\n"
        )
        events.append(event)
    footer = "END:VCALENDAR\n"
    with open(filename, "w") as f:
        f.write(header + "".join(events) + footer)
    print(f"Saved waste collection dates to {filename}")

# Function to retrieve waste collection dates from waste_entries
def get_waste_dates(waste_entries):
    collection_days = []
    for entry in waste_entries:
        year = entry['jahr'] + 2000
        start_date = datetime(year, 1, 1)

        if entry['resttag']:
            rest_dates = calculate_dates(start_date, entry['resttag'] - 1, entry['restgu'], "Restmüll")
            collection_days.extend([("Restmüll", date) for date in rest_dates])
        
        if entry['biotag']:
            bio_dates = calculate_dates(start_date, entry['biotag'] - 1, entry['biogu'], "Bioabfall")
            collection_days.extend([("Bioabfall", date) for date in bio_dates])
        
        if entry['werttag']:
            wert_dates = calculate_dates(start_date, entry['werttag'] - 1, entry['wertgu'], "Gelber Sack")
            collection_days.extend([("Gelber Sack", date) for date in wert_dates])
        
        if entry['papier']:
            paper_dates = [
                datetime.strptime(d['datum'], '%Y-%m-%d')
                for d in data[5]
                if d.get('papier') == entry['papier']
            ]
            for paper_date in paper_dates:
                collection_days.append(("Papier", paper_date))
    
    return collection_days

# Helper function to calculate recurring dates until the end of the current year
def calculate_dates(start_date, days_offset, is_even_week, abfall_type=""):
    end_date = datetime(datetime.now().year, 12, 31)
    current_date = start_date + timedelta(days=days_offset)

    if is_even_week:
        if current_date.isocalendar().week % 2 != 0:
            current_date += timedelta(weeks=1)
    else:
        if current_date.isocalendar().week % 2 == 0:
            current_date += timedelta(weeks=1)
    
    dates = []
    interval = 14  # Fixed interval of two weeks for biowaste

    while current_date <= end_date:
        dates.append(current_date)
        current_date += timedelta(days=interval)
    
    return dates

# Input for location and street selection
print("Locations:")
print("1: Apen")
print("2: Bad Zwischenahn")
print("3: Edewecht")
print("4: Rastede")
print("5: Westerstede")
print("6: Wiefelstede")

ortid = int(input("Enter the location ID: "))
street_info = display_streets_for_ort(ortid)

if street_info:
    street_id, street_name = street_info
    get_abfalltermine(ortid, street_id, street_name)