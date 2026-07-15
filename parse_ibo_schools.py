import json
from bs4 import BeautifulSoup

with open("ibo_page.html", "r", encoding="utf-8") as f:
    html = f.read()

soup = BeautifulSoup(html, 'html.parser')
results_text = soup.find(string=lambda t: 'schools' in t.lower() if t else False)
print(f"Any mention of schools count? {results_text}")

# Let's see if there's any other json payload
print(len(html))
