import json
import csv
import re

with open("cbse_github_schools.json", "r", encoding="utf-8") as f:
    payload = json.load(f)
    
data = payload.get('data', [])
print(f"Loaded {len(data)} schools from JSON.")

with open("cbse_schools_india.csv", "w", newline="", encoding="utf-8") as f:
    writer = csv.writer(f)
    writer.writerow(["School_Name", "Address", "Pincode", "Board"])
    
    for school in data:
        name = school.get("schoolName", "")
        address = school.get("address", "")
        state = school.get("state", "")
        district = school.get("district", "")
        
        full_addr = f"{address}, {district}, {state}".strip()
        
        pincode = ""
        match = re.search(r'\b\d{6}\b', full_addr)
        if match:
            pincode = match.group(0)
                
        writer.writerow([name, full_addr, pincode, "CBSE"])

print("Successfully created cbse_schools_india.csv!")
