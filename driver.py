from LimeSoup import (
    ACSSoup, 
    APSSoup, 
    ECSSoup, 
    ElsevierSoup, 
    IOPSoup, 
    NatureSoup, 
    RSCSoup, 
    SpringerSoup, 
    WileySoup,
)
import json

with open('data/10114911543949.html', 'r', encoding = 'utf-8') as f:
    html_str = f.read()

data = ECSSoup.parse(html_str)

with open('Parsed/10114911543949.json', 'w', encoding = 'utf-8') as f:
    json.dump(data, f, sort_keys=True, indent=4, ensure_ascii=False)