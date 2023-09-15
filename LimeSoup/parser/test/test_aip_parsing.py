from DBGater.db_singleton_mongo import SynDevAdmin, FullTextAdmin
from LimeSoup import AIPSoup
from LimeSoup import ElsevierSoup
from LimeSoup import RSCSoup
import xml.etree.ElementTree as ET
from pprint import pprint
from time import sleep
from statistics import mean, median

# from Borges.spiders.AIP.download_abstract import download_abstract

db = SynDevAdmin.db_access()
db.connect()
paper_col = db.collection("AIPPapers_Test")
paragraphs_col = db.collection("AIPParagraphs_Test")

# note that in recursive functions, args with a default will be overwritten if already assigned (like collected_content)
def unwind_sections(sections, collected_content=[], ancestors=['_root'], i=0):
    for section in sections:
        if type(section) == str: # sometimes only has one element and is a string
            section = {'content': [section]}

        if type(section) == dict: # should have 'content' key with individual paragraphs / sections
            if type(section['content']) == str:
                section['content'] = [section['content']]

            if 'name' in section.keys() and section['name']:
                path = '$$'.join(ancestors) + "$$" + section['name']
            else:
                path = '$$'.join(ancestors)

        if all([type(s) == dict for s in section['content']]): # next layer has subsections
            collected_content, ancestors, i = unwind_sections(
                section['content'],
                collected_content=collected_content,
                ancestors=path.split('$$'),
                i=i
            )
        else:
            for j, subsection in enumerate(section['content']):
                if type(subsection) == str:
                    collected_content.append({
                        'ancestors': path.split('$$'),
                        'path': path,
                        'text': subsection,
                        'order': j,
                        'order_root': i
                    })
                    i += 1
                else:
                    collected_content, ancestors, i = unwind_sections(
                        [subsection],
                        collected_content=collected_content,
                        ancestors=path.split('$$'),
                        i=i
                    )
    ancestors = ancestors[:-1] if len(ancestors)>1 else ['_root']
    return collected_content, ancestors, i

paragraph_totals = []
paragraphs_to_insert = []
total = 600
for i, paper in enumerate(paper_col.find({'Combined_Paper_Content': {'$exists': True}})): # grab later from /abstract API endpoint
    try:
        parsed_paper = AIPSoup.parse(paper['Combined_Paper_Content'])
    except:
        print(paper['DOI'])
    unwound_sections, ancestors, total_paras = unwind_sections(parsed_paper['Sections'], collected_content=[], ancestors=['_root'])
    paragraph_totals.append(total_paras)
    for para in unwound_sections:
        paragraphs_to_insert.append(
            {
                'DOI': paper['DOI'],
                'Publisher': paper['Publisher'],
                'path': para['path'],
                'ancestors': para['ancestors'],
                'text': para['text'],
                'order': para['order'],
                'order_root': para['order_root']
            }
        )

    if (i+1) % 1 == 0:
        if paragraphs_to_insert:
            paragraphs_col.insert_many(paragraphs_to_insert)
        paragraphs_to_insert = []

    print(f'{i+1}/{total}', end='\r')

print()
print(mean(paragraph_totals))
print(median(paragraph_totals))
print(max(paragraph_totals))
print(min(paragraph_totals))



