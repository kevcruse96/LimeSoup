from DBGater.db_singleton_mongo import SynDevAdmin, FullTextAdmin
import json
from LimeSoup import SpringerNatureSoup, SpringerSoup
import xml.etree.ElementTree as ET
from pprint import pprint
from time import sleep
from statistics import mean, median
import sys, traceback

import random

db = SynDevAdmin.db_access()
old_db = FullTextAdmin.db_access()

db.connect()
old_db.connect()

paper_col = db.collection("SpringerPapers_Test")

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

for i, paper in enumerate(paper_col.find({})):
    if i == 1:
        try:
            parsed_paper = SpringerNatureSoup.parse(paper['Paper_Content'])
            # First, check things were parsed correctly
            pprint(parsed_paper)

            # Optionally, format things for insertion into a Paragraphs MongoDB collection
            unwound_sections, ancestors, total_paras = unwind_sections(
                parsed_paper['Sections'],
                collected_content=[],
                ancestors=['_root']
            )
        except Exception as e:
            print(e)
            ex_type, ex, tb = sys.exc_info()
            pprint(traceback.print_tb(tb))
            print(paper['DOI'])
        break
    else:
        continue