from LimeSoup.lime_soup import Soup, RuleIngredient
from LimeSoup.parser.parser_paper_IOP import ParserPaper
from LimeSoup.parser.paragraphs import extract_paragraphs_recursive

from pprint import pprint

import re

__author__ = 'Zheren Wang'
__maintainer__ = 'Kevin Cruse'
__email__ = 'kevcruse96@gmail.com'
__version__ = '0.2.0'

class IOPRemoveTrash(RuleIngredient):
    @staticmethod
    def _parse(xml_str):
        # Tags to be removed from the xml paper

        # Before creating BeautifulSoup object, remove in-line citation groupings
        # removes chunks like [10], [1, 3], [4-6], and replaces with emtpy string
        # if there is a space before, that will be retained (need this in case enclosing is surrounded by () + other
        # discussion... somewhat hacky workaround but seems better than leaving in the "[, ]", "[-]", etc. substrings.
        # If there are any remaining, then just remove using parser.remove_tags() method

        # remove formatting for inline citations
        xml_str = re.sub(r'(?:(\[)?<xref ref-type="bibr".*?\/xref>(\]|\))?)', '', xml_str)

        # remove empty title tags (happens around List of Symbols sections
        xml_str = xml_str.replace("<title/>", "")

        # add carots for exponentials (only for digits, not for inline citations)
        # note that this does not cover cases like below:
        # <mml:msup><mml:mrow><mml:mn>10</mml:mn></mml:mrow><mml:mrow><mml:mn>17</mml:mn></mml:mrow></mml:msup>
        xml_str = re.sub(r"<sup>([\d+|[\−\d+])", r"<sup>^\1", xml_str)

        # remove Google script tags
        xml_str = re.sub(r"<\?.*?\s?(<.*>)?\?>", r"\1", xml_str)

        parser = ParserPaper(xml_str, parser_type='html.parser', debugging=False)

        list_remove = [
            {'name': 'ref-list'},
            {'name': 'table-wrap'},
            {'name': 'fig'},
            {'name': 'xref', 'ref-type': 'bibr'},
            {'name': 'label'},
            {'name': 'disp-formula'},
            {'name': 'def-list', 'list-content': 'abbreviations'}
        ]
        parser.remove_tags(rules=list_remove)

        # Added 202405
        list_strip = [
            {'name': 'inline-formula'},
            {'name': 'mml:math'},
            {'name': 'mml:msub'},
            {'name': 'mml:mi'},
            {'name': 'mml:mrow'},
            {'name': 'mml:mn'},
            {'name': 'mml:msub'},
            {'name': 'sub'},
            {'name': 'sup'},
            # Uncommenting this will separate list items into separate paragraphs... we don't want this
            # since synthesis descriptions could then be separated
            # {'name': 'list-item'}
        ]
        parser.strip_tags(rules=list_strip)

        # Added 20240521
        parser.rename_tag(rule={'name': 'list'}, new_name='p')

        return parser

class IOPCreateTags(RuleIngredient):

    @staticmethod
    def _parse(parser):
        # parser = ParserPaper(xml_str, parser_type='html.parser', debugging=False)
        try:
            # This create a standard of sections tag name
            parser.create_tag_sections()
        except:
            pass
        return parser

class IOPReplaceSectionTag(RuleIngredient):

    # As of 2024-04 this is being reworked
    # TODO this probably isn't needed as IOPCreateTags() does something similar?
    # This seems to replace IOPCreateTags (something doesn't work correctly with IOPCreateTags)

    @staticmethod
    def _parse(parser):
        # parser = ParserPaper(xml_str, parser_type='html.parser', debugging=False)
        parser.change_name_tag_sections()
        parser.create_tag_to_paragraphs_inside_tag({'name': 'body'}, 'h2', name_section='')
        return parser


class IOPCollect(RuleIngredient):

    @staticmethod
    def _parse(parser):

        # As of 2024-04, this is the correct way to get DOI...
        # should check against what was parsed from download
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
IOPSoup.add_ingredient(IOPRemoveTrash())
IOPSoup.add_ingredient(IOPCreateTags())
IOPSoup.add_ingredient(IOPReplaceSectionTag())
IOPSoup.add_ingredient(IOPCollect())
