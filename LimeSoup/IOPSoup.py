from LimeSoup.lime_soup import Soup, RuleIngredient
from LimeSoup.parser.parser_paper_IOP import ParserPaper

from pprint import pprint

import re


__author__ = 'Zheren Wang'
__maintainer__ = 'Kevin Cruse'
__email__ = 'kevcruse96@gmail.com'
__version__ = '0.1.2'


class IOPRemoveTrash(RuleIngredient):
    @staticmethod
    def _parse(xml_str):
        # Tags to be removed from the xml paper

        # Before creating BeautifulSoup object, remove in-line citation groupings
        # removes chunks like [10], [1, 3], [4-6], and replaces with emtpy string
        # if there is a space before, that will be retained (need this in case enclosing is surrounded by () + other
        # discussion... somewhat hacky workaround but seems better than leaving in the "[, ]", "[-]", etc. substrings.
        # If there are any remaining, then just remove using parser.remove_tags() method
        xml_str = re.sub(r'(?:(\[)?<xref ref-type="bibr".*?(\]|\)))', '', xml_str)

        parser = ParserPaper(xml_str, parser_type='lxml', debugging=False)

        list_remove = [
            {'name': 'ref-list'},
            {'name': 'table-wrap'},
            {'name': 'fig'},
            {'name': 'xref', 'ref-type': 'bibr'},
            {'name': 'label'},
            {'name': 'disp-formula'},
            {'name': 'inline-formula'}
        ]

        parser.remove_tags(rules=list_remove)

        if parser.soup.find(**{'name': 'xref', 'ref-type': 'bibr'}):
            print(parser.soup.find(**{'name': 'xref', 'ref-type': "bibr"}))
            print('Did not remove xref bibr correctly')
            stop
        return parser.raw_xml

class IOPCreateTags(RuleIngredient):

    @staticmethod
    def _parse(xml_str):
        parser = ParserPaper(xml_str, parser_type='lxml', debugging=False)
        try:
            # This create a standard of sections tag name
            parser.create_tag_sections()
        except:
            pass
        return parser.raw_xml

class IOPReplaceSectionTag(RuleIngredient):

    @staticmethod
    def _parse(xml_str):
        parser = ParserPaper(xml_str, parser_type='lxml', debugging=False)
        parser.change_name_tag_sections()
        return parser.raw_xml

class IOPReformat(RuleIngredient):

    @staticmethod
    def _parse(xml_str):
        new_xml = xml_str.replace('>/','>')
        parser = ParserPaper(new_xml, parser_type='lxml',debugging=False)
        return parser.raw_xml

class IOPCollect(RuleIngredient):

    @staticmethod
    def _parse(xml_str):
        parser = ParserPaper(xml_str, parser_type='lxml', debugging=False)
        # Collect information from the paper using ParserPaper

        # As of 2024-04, we already have journal title from download
        # try:
        #     journal_name = next(x for x in parser.get(rules=[{"name": "journal-title"}]))
        # except StopIteration:
        #     journal_name = None

        # As of 2024-04, we already have article title from download
        # parser.get_title(rules=[
        #     {'name': 'article-title'}
        # ]
        # )

        # As of 2024-04, this is the correct way to get DOI...
        # should against what was parsed from download
        doi = parser.get(rules=[
            {'name': 'article-id',
            'pub-id-type': 'doi'}
        ])
        parser.deal_with_sections()
        data = parser.data_sections
        parser.create_abstract(rule={'name': 'abstract'})

        obj = {
            'DOI': "".join(doi),
            'Keywords': [],
            'Sections': data
        }
        return obj


IOPSoup = Soup(parser_version=__version__)
IOPSoup.add_ingredient(IOPReformat())
IOPSoup.add_ingredient(IOPRemoveTrash())
IOPSoup.add_ingredient(IOPCreateTags())
IOPSoup.add_ingredient(IOPReplaceSectionTag())
IOPSoup.add_ingredient(IOPCollect())


# if __name__ == '__main__':
#     filename = "cm10_4_045302.xml"
#     with open(filename, "r", encoding="utf-8") as f:
#         paper = f.read()

#     parsed_paper = IOPSoup.parse(paper)
#     print(parsed_paper )
    # if parsed_paper['DOI']:
    #     print(parsed_paper)
    # data = parsed_paper["obj"]
