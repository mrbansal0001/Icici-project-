import json
from bs4 import BeautifulSoup

with open("ibo_page.html", "r", encoding="utf-8") as f:
    html = f.read()
    
soup = BeautifulSoup(html, 'html.parser')
map_div = soup.find('div', class_='Map')
if map_div and 'data-map-2' in map_div.attrs:
    data = json.loads(map_div['data-map-2'])
    schools = data.get('data', [])
    print(f"Found {len(schools)} schools in JSON!")
    print(schools[0])
    print(schools[1])
else:
    print("Could not find map data.")
