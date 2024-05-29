import re

from LimeSoup.lime_soup import Soup, RuleIngredient
from LimeSoup.parser.paragraphs import extract_paragraphs_recursive
from LimeSoup.parser.parser_paper import ParserPaper

from pprint import pprint

__author__ = 'Jason Madeano, Haoyan Huo'
__maintainer__ = 'Kevin Cruse, Sanghoon Lee'
__email__ = 'kevcruse96@gmail.com, sh.lee@lbl.gov'
__version__ = '0.3.0'


class SpringerNatureRemoveTagsSmallSub(RuleIngredient):

    @staticmethod
    def _parse(html_str):
        """
        Deal with spaces in the sub, small tag and then remove it.
        """

        # Optional: remove formatting for inline citations
        # required closed brackets/parentheses... if open, only the reference is removed but bracket, comma formatting
        # will remain
        html_str = re.sub(
            r'(?:(\[)<a data-track="click" data-track-action="reference anchor".*?\/a>(\]|\)))',
            '',
            html_str
        )

        # remove space characters
        html_str = re.sub(r'\xa0', ' ', html_str)
        html_str = re.sub(r'\u2009', ' ', html_str)

        # add carots for exponentials (only for digits, not for inline citations)
        html_str = re.sub(r"<sup>([\d+|[\−\d+])", r"<sup>^\1", html_str)

        parser = ParserPaper(html_str, parser_type='html.parser', debugging=False)
        rules = [{'name': 'small'},
                 {'name': 'sub'},
                 {'name': 'span', 'class': 'small_caps'},
                 {'name': 'b'},
                 {'name': 'i'},
                 {'name': 'sup'},
                 {'name': 'span', 'class': 'italic'},
                 {'name': 'span', 'class': 'bold'},
                 {'name': 'strong'},
                 {'name': 'span', 'class': 'small_caps'}]

        # Remove some specific all span that are inside of a paragraph 'p'
        parser.strip_tags(rules)
        return parser


class SpringerNatureRemoveTrash(RuleIngredient):
    """
    Selects the article div and removes all of the excess (ie. the sidebar,
    Nature contact info, etc). Also strips the items listed below.
    """

    @staticmethod
    def _parse(parser):
        # Tags to be removed from the HTML paper ECS
        list_remove = [
            {'name': 'li', 'itemprop': 'citation'},  # Citations/References
            {'name': 'div', 'id': 'article-comments-section'},  # Comments
            {'name': 'figure'},  # Figures
            {'name': 'code'},  # Code inside the HTML
            {'name': 'div', 'class': 'figure-at-a-glance'},  # Copy of all figures

            # # Still deciding how to deal with removing all references,
            # # Currently all superscript references are removed.
            # {'name': 'a'}
            {'name': 'a','data-track-action':"reference anchor"}, # FixAPR24) remove reference numbers from main text - still has brackets and commas
            {'name': 'a', 'data-track-action': 'figure anchor'},  # Figure Link
            {'name': 'a', 'data-track-action': 'supplementary material anchor'},  # Supplementary Link
            {'name': 'section', 'aria-labelledby': 'inline-recommendations'},
            {'name': 'div', 'class': 'app-checklist-banner--on-mobile'},
            {'name': 'span', 'class': 'c-article-section__title-number'}
        ]
        parser.remove_tags(rules=list_remove)

        return parser


class SpringerNatureCollectMetadata(RuleIngredient):
    """
    Collect metadata such as Title, Journal Name, DOI and Content Type.
    """

    @staticmethod
    def _parse(parser):
        # This dictionary structure should match other parsers,
        # "Valid Article" and "Content Type" are specific to Nature Parser
        doi = parser.extract_first_meta('citation_doi')
        if doi is None:
            doi = parser.extract_first_meta('prism.doi')
        if doi is not None:
            doi = re.sub(r'^doi:\s*', '', doi)
            doi = re.sub(r'\s+', '', doi)

        # TODO: We can actually use heuristics to get the title as <h1>.
        # this can be implemented later.
        title = parser.extract_first_meta('citation_title')
        if title is None:
            title = parser.extract_first_meta('twitter:title')
        if title is not None:
            title = re.sub(r'\s+', ' ', title)

        journal = parser.extract_first_meta('citation_journal_title')

        # FIXME: separate keywords into single words by comma
        keywords = parser.extract_meta('keywords')
        article_type = parser.extract_first_meta('WT.cg_s')
        obj = {
            'Content Type': article_type,
            'DOI': doi,
            'Title': title,
            'Keywords': keywords,
            'Journal': journal,
        }

        return [obj, parser]


class SpringerNatureExtractArticleBody(RuleIngredient):
    """
    Take the body section out of the HTML DOM.
    """

    @staticmethod
    def _parse(parser_obj):
        obj, parser = parser_obj

        # style 1
        article_body = parser.soup.find(attrs={'data-article-body': 'true'})

        if article_body is None:
            # style 2
            article_body = parser.soup.find('article')
            rules_to_remove = [
                {'name': 'header'},
                {'name': 'nav'},
                {'class': 'article-keywords'},
                {'class': 'figures-at-a-glance'},
            ]
            if article_body:
                for rule in rules_to_remove:
                    for tag in article_body.find_all(**rule):
                        tag.extract()

        if article_body is None:
            raise ValueError('Cannot find article body. You '
                             'should inspect this HTML file carefully.')

        parser = ParserPaper(str(article_body), parser_type='html.parser')

        return [obj, parser]


class SpringerNatureCollect(RuleIngredient):
    @staticmethod
    def _parse(parser_obj):
        obj, parser = parser_obj

        ending_sections = [
            re.compile(r'.*?acknowledge?ment.*?', re.IGNORECASE),
            re.compile(r'.*?reference.*?', re.IGNORECASE),
            re.compile(r'.*?author\s*information.*?', re.IGNORECASE),
            re.compile(r'.*?related\s*links.*?', re.IGNORECASE), #FixAPR24) do not remove references
            re.compile(r'.*?about\s*this\s*article.*?', re.IGNORECASE),
            re.compile(r'.*?data\s*availability\s*statement.*?', re.IGNORECASE),
        ]

        section_status = {
            'should_trim': False
        }

        def trim_sections(sections):
            """
            Remove anything after "ending_sections"
            """
            if isinstance(sections, dict):
                for rule in ending_sections:
                    if not section_status['should_trim']:
                        if rule.match(sections['name']):
                            section_status['should_trim'] = True
                            break

                should_include, secs = trim_sections(sections['content'])
                sections['content'] = secs

                return should_include, sections
            elif isinstance(sections, list):
                final_secs = []
                for sub_sec in sections:
                    should_include, sub_sec = trim_sections(sub_sec)
                    if should_include:
                        final_secs.append(sub_sec)

                return len(final_secs) > 0, final_secs
            else:
                return not section_status['should_trim'], sections

        raw_sections = extract_paragraphs_recursive(parser.soup)

        # remove brackets and formatting from citations
        # for sec in raw_sections:
        #     # sec['content'] = [re.sub('\n*\s+\n*', ' ', s) for s in sec['content']]
        #     # sec['content'] = [re.sub(r'\s?\[(\s|-\s|–\s|,\s)*\]', '', s) for s in sec['content']]
        #     pprint(sec)
        # stop

        should_include, trimmed_sections = trim_sections(raw_sections)

        # Fix abstract, if the first element is just a plain text.
        if len(trimmed_sections) > 1 and \
                isinstance(trimmed_sections[0], str) and \
                isinstance(trimmed_sections[1], dict):
            trimmed_sections[0] = {
                'type': 'section_abstract_heuristics',
                'name': 'Abstract',
                'content': [trimmed_sections[0]],
            }

        # ref = [par for par in trimmed_sections if 'reference' in par['name'].lower()] # FixAPR24) add references
        # trimmed_sections = [par for par in trimmed_sections if 'reference' not in par['name'].lower()] # FixAPR24) add references
        obj['Sections'] = trimmed_sections
        # obj['References'] = ref # FixAPR24) add references

        return obj


SpringerNatureSoup = Soup(parser_version=__version__)
SpringerNatureSoup.add_ingredient(SpringerNatureRemoveTagsSmallSub())
SpringerNatureSoup.add_ingredient(SpringerNatureRemoveTrash())
SpringerNatureSoup.add_ingredient(SpringerNatureCollectMetadata())
SpringerNatureSoup.add_ingredient(SpringerNatureExtractArticleBody())
SpringerNatureSoup.add_ingredient(SpringerNatureCollect())
