import re
import regex

from LimeSoup.lime_soup import Soup, RuleIngredient
from LimeSoup.parser.paragraphs import extract_paragraphs_recursive
from LimeSoup.parser.parser_paper import ParserPaper

from pprint import pprint

__author__ = 'Zheren Wang'
__maintainer__ = 'Kevin Cruse'
__email__ = 'kevcruse96@gmail.com'
__version__ = '0.2.0'


class AIPRemoveTrash(RuleIngredient):
    """
    Selects the article div and removes all of the excess (ie. the sidebar,
    etc). Also strips the items listed below.
    """

    @staticmethod
    def _parse(html_str):
        parser = ParserPaper(html_str, parser_type='html.parser', debugging=False)
        # Tags to be removed from the HTML paper
        list_remove = [
            {'name': 'div', 'class': ['figure', 'figure-image-content']},  # Figures
            {'name': 'code'},  # Code inside the HTML
            {'name': 'div', 'class': 'tableWrapper'},  # Tables
            {'name': 'div', 'class': 'table-article'},  # Tables
            {'name': 'div', 'class': 'NLM_table'},  # Tables
            {'name': 'span', 'class': 'ref-lnk'},  # Ref Link
            {'name': 'div', 'class': 'ack'},  # Acknowledgement
            {'name': 'div', 'class': 'NLM_sec-type_appendix'},  # Appendix
            {'name': 'div', 'class': 'article-paragraphs'},  # References
            {'name': 'xref', 'ref-type': 'bibr'}, # removes in-line citation numbers
            # {'name': 'inline-formula'}, # moving to strip_tags as of 2023-12-15
            # {'name': 'disp-formula'}, # moving to strip_tags as of 2023-12-21
            # {'name': 'label'},  # this tag is used for things like list item markers, so we lose that (should be okay)... actually decided to keep as of 2023-01-18
            {'name': 'caption'}, # figure captions typically
            {'name': 'table'},
            {'name': 'table-wrap'},
            {'name': 'fig'},
            {'name': 'ack'},
            # Added 1/10/24... seems to be related to LaTeX markdown, but would be good to check on
            {'name': 'tex-math'}, #
        ]
        parser.remove_tags(rules=list_remove)

        return parser


class AIPCollectMetadata(RuleIngredient):
    """
    Collect metadata such as Title, Journal Name, DOI.

    2023-08-22 Update: new API for AIP does not include much metadata in fulltext response... removing ingredient for now
    Will grab this from the /metadata endpoint of their API later
    """

    @staticmethod
    def _parse(parser):

        trim = lambda tag: re.sub(r'(^[\s\n]+)|([\s\n]+$)', '', tag)
        
        # This dictionary structure should match other parsers,
        # "Valid Article" and "Content Type" are specific to AIP Parser
        title = parser.get_first_title([{'name': 'header', 'class': 'publicationContentTitle'}])
        title = trim(title)

        # meta info includes journal & doi
        meta_info = parser.soup.find(**{'name': 'div', 'class': 'publicationContentCitation'}).strings
        meta_info = map(trim, meta_info)
        journal = next(meta_info)

        doi = None
        
        # search for DOI
        for each in meta_info:
            doi_ = re.search(r'(?<=https://doi.org/).+', each)
            if doi_ is not None:
                doi = doi_.group()
                doi = trim(doi)
                break

        if doi is None:
            raise ValueError("Cannot find doi.")
        
        # keywords
        keywords = parser.get_keywords([{'name': 'li', 'class': 'topicTags'}])
        
        obj = {
            'DOI': doi,
            'Title': title,
            'Journal': journal,
            'Keywords': keywords
        }

        return obj, parser


class AIPCleanArticleBody(RuleIngredient):
    @staticmethod
    def _parse(parser):
        """
        Find the article body, then remove some tags
        """
        # obj, parser = parser_obj # Only throwing parser around at first with not metadata

        # # old style
        # article_body = parser.soup.find(**{'name': 'article', 'class': 'article'})
        # # new style
        # if article_body is None:
        #     article_body = parser.soup.find(**{'name': 'div', 'class': 'left-article'})
        # if article_body is None:
        #     raise ValueError('Cannot find article body')
        # parser = ParserPaper(str(article_body), parser_type='html.parser')
        article_body = parser.soup.find(**{'name': 'fulltext'})
        if article_body is None:
            raise ValueError('Cannot find article body')
        parser = ParserPaper(str(article_body), parser_type='html.parser')

        # 2023-01-18 ===> list items are divided by <p></p> tags, so the following is a bit of a hacky
        # way to change those tags and join everything in the same previous paragraph
        list_para_parent_rule = {'name': "list"}
        list_para_child_rule = {'name': 'p'}
        parser.rename_child_based_on_parent(
            list_para_parent_rule,
            list_para_child_rule,
            'named-content'
        )

        # 2023-01-18 ===> created new function to remove the <label></label> tags that denote section headings,
        # that way we can keep list item labels but remove this junk
        section_label_tag_rule = {'name': 'label'}
        section_label_next_sibling_rule = {'name': 'title'}
        parser.remove_tag_based_on_next_sibling(
            section_label_tag_rule,
            section_label_next_sibling_rule,
        )



        rules = [
        #     {'name': 'div', 'class': 'abstractInFull'},
        #     {'name': 'div', 'class': 'sectionInfo'},
            {'name': 'list'}, # TODO: decide on this... was implemented previously
            {'name': 'list-item'},
            {'name': 'label'},
            #{'name': 'italic'},
            {'name': 'named-content'},
            {'name': 'ext-link'},
            {'name': 'xref'},
            {'name': 'bold'},
            # Below added 2023-12-15, test with 10.1063/1.3075216
            {'name': 'etal'},
            {'name': 'mixed-citation'},
            {'name': 'source'},
            {'name': 'volume'},
            {'name': 'fpage'},
            {'name': 'lpage'},
            {'name': 'year'},
            {'name': 'underline'}, # check 10.1063/1.4861795
            {'name': 'inline-supplementary-material'}, # check 10.1063/1.4979560
            # added below 2023-12-15, test with 10.1063/1.3085997
            {'name': 'inline-formula'},
            {'name': regex.compile("mml:.*(?<!mstyle|mo|mi|msub|mrow|math)$")},
            {'name': 'inline-graphic'},
            {'name': 'monospace'},
            {'name': 'publisher-name'},
            {'name': 'publisher-loc'},
            {'name': 'year'},
            {'name': 'pub-id'},
            {'name': 'roman'},
            # Using above regex instead... should remove below)
            # {'name': 'mml:math'},
            # {'name': 'mml:mrow'},
            # # {'name': 'mml:mi'},
            # {'name': 'mml:mtext'},
            # {'name': 'mml:msub'},
            # {'name': 'mml:msup'},
            # {'name': 'mml:msubsup'},
            # #{'name': 'mml:mo'},
            # {'name': 'mml:msqrt'},
            # # added below 2023-12-21, test with 10.1063/1.4861795
            # {'name': 'mml:mover'},
            # {'name': 'alternatives'},
            # # added below 2024-1-11, test with 10.1063/1.4985139
            # # {'name': 'mml:mstyle'},
            # {'name': 'mml:mfenced'},
            # {'name': 'mml:mfrac'},
            # {'name': 'mml:mspace'},
            # {'name': 'mml:mpadded'},
            # {'name': 'mml:mphantom'}
        ]
        parser.strip_tags(rules)

        # deal with listgroup
        rules = [
            {'name': 'table', 'class': 'listgroup'}
        ]
        parser.flatten_tags(rules)

        # deal with formula
        rules = [
            {'name': 'span', 'class': 'equationTd'},
            {'name': 'table', 'class': 'formula-display'},
            {'name': 'disp-formula'},
            {'name': 'disp-formula-group'}
        ]
        parser.flatten_tags(rules)

        # sub title
        rules = {'name': 'div', 'class': 'head-b'}
        parser.rename_tag(rules, 'h4')

        # sub sub title
        rules = {'name': 'div', 'class': 'head-c'}
        parser.rename_tag(rules, 'h4')

        # abstract header is not in h4 tag
        rules = {'name': 'div', 'class': 'sectionHeading'}
        parser.rename_tag(rules, 'h4')

        # section titles
        rules = {'name': 'title'}
        parser.rename_tag(rules, 'h1')

        secondary_heading_parent_rule = {'name': "sec", 'id': re.compile('s\d[A-Z]$')}
        secondary_heading_child_rule = {'name': 'h1'}
        parser.rename_child_based_on_parent(
            secondary_heading_parent_rule,
            secondary_heading_child_rule,
            'h2'
        )

        tertiary_heading_parent_rule = {'name': "sec", 'id': re.compile('s\d[A-Z]\d$')}
        tertiary_heading_child_rule= {'name': 'h2'}
        parser.rename_child_based_on_parent(
            tertiary_heading_parent_rule,
            tertiary_heading_child_rule,
            'h3'
        )

        # Quartenary headings?

        return parser


class AIPCollect(RuleIngredient):
    @staticmethod
    def _parse(parser):
        # obj, parser = parser_obj # Only throwing parser around at first with not metadata

        # Parse abstract
        # abstract_body = parser.soup.find(**{'name': 'div', 'class': 'hlFld-Abstract'})
        abstract_body = parser.soup.find(**{'name': 'abstract'})
        if abstract_body:
            abstract = extract_paragraphs_recursive(abstract_body)

            # for each in abstract:
            #     each['type'] = 'abstract' # We don't seem to get section titles anymore, so need to hardcode the abstract data structure
            abstract_data= {
                'type': 'abstract',
                'name': 'Abstract',
                'content': []
            }
            for each in abstract:
                abstract_data['content'].append(each)
            abstract_data = [abstract_data]
        else:
            abstract_data = []
        
        # Full text
        # full_text_body = parser.soup.find(**{'name': 'div', 'class': 'hlFld-Fulltext'})
        full_text_body = parser.soup.find(**{'name': 'body'})
        if full_text_body is not None:
            full_text = extract_paragraphs_recursive(full_text_body)
        else:
            full_text = []

        # remove indexes
        data = abstract_data + list(full_text) # as of 2023-08 abstract needs to be downloaded separately
        for i, sec in enumerate(data):
            # for sections that have no title
            if isinstance(sec, str):
                data[i] = {
                    'type': '',
                    'name': '',
                    'content': sec
                }

        def remove_indexes(sections):
            """
            remove indexes in section header
            """
            # include number, greek number and capital char
            # indexes_pattern = re.compile(r'^([A-z0-9]+)(\.|\s)(\s)+')
            # updated 2024-02-12 (accepts full words as "index" but removes numbers, single letters, and roman numerals)
            indexes_pattern = re.compile(r'^([A-z]{1}|[IVXMCDL]+|[0-9]+)(\.|\s)(\s)+')
            for sec in sections:
                if isinstance(sec, dict):
                    sec['name'] = re.sub(indexes_pattern, '', sec['name'])
                    remove_indexes(sec['content'])
                pprint(sec)

        remove_indexes(data)

        obj = {'Sections': data}

        return obj


AIPSoup = Soup(parser_version=__version__)
AIPSoup.add_ingredient(AIPRemoveTrash())
# AIPSoup.add_ingredient(AIPCollectMetadata())
AIPSoup.add_ingredient(AIPCleanArticleBody())
AIPSoup.add_ingredient(AIPCollect())
