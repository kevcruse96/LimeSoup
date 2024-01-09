from DBGater.db_singleton_mongo import SynDevAdmin, FullTextAdmin
from LimeSoup import RSCSoup
import xml.etree.ElementTree as ET
from pprint import pprint
from time import sleep
import random
from Borges.db_scripts.create_dummy_col import create_dummy_col
import json

db = SynDevAdmin.db_access()
db.connect()
paper_col = db.collection("RSCPapers")
paragraphs_col = db.collection('RSCParagraphs_Test')

create_dummy_col("RSCPapers_Test", col_to_dupe=paper_col, randomize=False, sample_size=47000)

paper_col = db.collection('RSCPapers_Test')

def update_papers_parsed(papers_to_update):
    for p in papers_to_update:
        paper_col.update_one(
            {'_id': p['_id']},
            {'$set': {
                    'parser_error': p['parser_error'],
                    'parser_version': p['parser_version'],
                    'parser_successful': p['parser_successful'],
                }
            }
        )

paragraphs_to_insert = []
paragraph_total = []
papers_to_update = []
error_ct = []
none_ct = []
total = 20000
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

test_parsing = []
for i, paper in enumerate(paper_col.find({'$and': [
    {'Paper_Content_HTML': {'$exists': True}},
    {'$or':
        [
            {'parser_successful': {'$exists': False}},
            {'parser_successful': False}
        ]
    }]
})):
    if paper['Paper_Content_HTML'] is not None:
        try:
            parsed_paper = RSCSoup.parse(paper['Paper_Content_HTML'])
            # TODO: abstract is currently extracted as type: section_h1... is this an issue?
            parsed_paper['DOI'] = paper['DOI']
            parsed_paper['Journal'] = paper['Journal']
            unwound_sections, ancestors, total_paras = unwind_sections(parsed_paper['Sections'], collected_content=[],
                                                                       ancestors=['_root'])
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
            error = None
            parsed = True
        except Exception as e:
            error = str(e)
            error_ct.append({paper['DOI']: error})
            parsed = False
        papers_to_update.append(
            {
                '_id': paper['_id'],
                'parser_error': str(error),
                'parser_version': 'The Royal Society of Chemistry+0.4.0',
                'parser_successful': parsed,
            }
        )
    else:
        none_ct.append(paper['DOI'])

    if (i + 1) % 1 == 0:
        if paragraphs_to_insert:
            paragraphs_col.insert_many(paragraphs_to_insert)
        update_papers_parsed(papers_to_update)
        paragraphs_to_insert = []
        papers_to_update = []

        with open('./logs/rsc_errors.json', 'w') as fp:
            json.dump(error_ct, fp)

        with open('./logs/rsc_none_dois.json', 'w') as fp:
            json.dump(none_ct, fp)

    print(f'{i + 1}/{total} ({len(error_ct)} errors, {len(none_ct)} empty content)', end='\r')

print()

