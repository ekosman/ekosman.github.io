import copy
import importlib.util
import unittest
import tempfile
from pathlib import Path
from unittest.mock import patch
import xml.etree.ElementTree as ET
from io import BytesIO
from urllib.error import HTTPError

spec = importlib.util.spec_from_file_location('refresh', Path(__file__).parents[1] / 'scripts/refresh.py')
refresh = importlib.util.module_from_spec(spec)
spec.loader.exec_module(refresh)


class RefreshTests(unittest.TestCase):
    def test_html_challenge_has_actionable_error(self):
        with self.assertRaisesRegex(refresh.ProviderError, 'HTML bot-check'):
            refresh.parse_xml(b'<!doctype html><html><title>Making sure you are not a bot</title></html>')

    def test_dblp_dtd_character_entities(self):
        root = refresh.parse_xml(b'<!DOCTYPE dblpperson SYSTEM "dblp.dtd"><dblpperson><author>J&ouml;rg &amp; Co</author></dblpperson>')
        self.assertEqual(root.findtext('author'), 'Jörg & Co')

    def test_publications_fall_back_to_arxiv_when_dblp_is_blocked(self):
        feed = ET.fromstring('''<feed xmlns="http://www.w3.org/2005/Atom" xmlns:os="http://a9.com/-/spec/opensearch/1.1/">
          <os:totalResults>2</os:totalResults>
          <entry><id>http://arxiv.org/abs/2601.12345v2</id><title>Existing paper renamed</title><published>2026-01-01</published><author><name>Eitan Kosman</name></author></entry>
          <entry><id>http://arxiv.org/abs/2610.12345v1</id><title>New paper</title><published>2026-10-28</published><author><name>Eitan Kosman</name></author></entry>
        </feed>''')
        with patch.object(refresh, 'fetch', side_effect=[refresh.ProviderError('HTML bot-check'), feed]):
            result = refresh.discover_publications([{'title': 'Old title', 'url': 'https://arxiv.org/abs/2601.12345'}])
        self.assertEqual([r['key'] for r in result], ['arxiv/2610.12345'])

    def test_serpapi_errors_include_status_and_redact_secret_and_url(self):
        body = b'{"error":"Request rejected: https://serpapi.com/search?api_key=secret-key secret-key"}'
        error = HTTPError('https://serpapi.com/search', 400, 'Bad Request', {}, BytesIO(body))
        with patch.dict(refresh.os.environ, {'SERPAPI_KEY': 'secret-key'}), patch.object(refresh, 'fetch', side_effect=error):
            with self.assertRaises(refresh.ProviderError) as caught:
                refresh.serpapi('google_patents', q='test')
        self.assertIn('HTTP 400', str(caught.exception))
        self.assertNotIn('secret-key', str(caught.exception))
        self.assertNotIn('https://', str(caught.exception))

    def test_scholar_numeric_strings_and_http_citation_link(self):
        response = self.scholar_response()
        response['cited_by']['table'][0]['citations']['all'] = '1,500'
        response['articles'][0]['cited_by'] = {'value': '7', 'link': 'http://scholar.google.com/scholar?cites=1'}
        impact = {'as_of': '2026-10-26', 'papers': {}}
        with patch.object(refresh, 'serpapi', return_value=response):
            refresh.refresh_scholar(impact, [{'id': 'known', 'title': 'Known Paper'}], '2026-10-28')
        self.assertEqual(impact['citations'], 1500)
        self.assertEqual(impact['papers']['known']['count'], 7)
        self.assertTrue(impact['papers']['known']['url'].startswith('https://'))

    def test_patent_query_and_pagination_use_provider_next_page(self):
        responses = [{'organic_results': [], 'serpapi_pagination': {'next': 'https://serpapi.com/search?engine=google_patents&page=1'}},
                     {'organic_results': []}]
        with patch.object(refresh, 'serpapi', side_effect=responses) as request:
            self.assertEqual(refresh.discover_patents([]), [])
        first = request.call_args_list[0].kwargs
        self.assertEqual(first['q'], 'inventor:(Eitan Kosman)')
        self.assertNotIn('page', first)
        self.assertEqual(request.call_args_list[1].kwargs['page'], 1)

    def test_github_pagination_and_excludes_forks(self):
        repo = {'name': 'test', 'owner': {'login': 'ekosman'}, 'html_url': 'https://github.com/ekosman/test',
                'fork': False, 'stargazers_count': 2, 'forks_count': 1}
        fork = {**repo, 'fork': True}
        impact = {}
        with patch.object(refresh, 'fetch', side_effect=[[fork] * 100, [repo]]) as request:
            refresh.refresh_github(impact, '2026-10-28')
        self.assertEqual(request.call_count, 2)
        self.assertEqual(len(impact['repositories']), 1)
        self.assertEqual(impact['github_as_of'], '2026-10-28')

    def scholar_response(self):
        return {'cited_by': {'table': [{'citations': {'all': 150}}, {'h_index': {'all': 6}},
                                     {'i10_index': {'all': 4}}]},
                'articles': [{'title': 'Known Paper', 'cited_by': {'value': 7,
                              'link': 'https://scholar.google.com/scholar?cites=1'}}]}

    def test_scholar_keeps_unmatched_badge_date(self):
        impact = {'as_of': '2026-10-26', 'papers': {'missing': {'count': 3, 'url': 'https://scholar.google.com/'}}}
        with patch.object(refresh, 'serpapi', return_value=self.scholar_response()):
            refresh.refresh_scholar(impact, [{'id': 'known', 'title': 'Known Paper'}], '2026-10-28')
        self.assertEqual(impact['citations'], 150)
        self.assertEqual(impact['papers']['missing']['as_of'], '2026-10-26')
        self.assertEqual(impact['papers']['known']['as_of'], '2026-10-28')

    def test_invalid_scholar_never_partially_updates(self):
        response = self.scholar_response()
        response['articles'][0]['cited_by']['value'] = -1
        impact = {'as_of': '2026-10-26', 'citations': 144, 'papers': {}}
        before = copy.deepcopy(impact)
        with patch.object(refresh, 'serpapi', return_value=response):
            with self.assertRaises(ValueError):
                refresh.refresh_scholar(impact, [{'id': 'known', 'title': 'Known Paper'}], '2026-10-28')
        self.assertEqual(impact, before)

    def test_dblp_deduplicates_aliases_and_arxiv_links(self):
        xml = ET.fromstring('''<dblpperson name="Eitan Kosman">
          <r><article key="old"><title>Old title.</title><year>2024</year></article></r>
          <r><article key="renamed"><title>Renamed work</title><ee>https://arxiv.org/abs/1234.56789</ee></article></r>
          <r><article key="new"><title>A new <i>paper</i>.</title><year>2026</year><author>Eitan Kosman</author></article></r>
        </dblpperson>''')
        papers = [{'title': 'Current title', 'aliases': ['Old title'], 'url': 'https://arxiv.org/abs/1234.56789'}]
        with patch.object(refresh, 'fetch', return_value=xml):
            result = refresh.discover_publications(papers)
        self.assertEqual([r['title'] for r in result], ['A new paper'])

    def test_patents_ignores_existing_id_and_equivalent_title(self):
        response = {'organic_results': [
            {'publication_number': 'US1A1', 'title': 'Known'},
            {'publication_number': 'EP2A1', 'title': 'Known'},
            {'publication_number': 'US3A1', 'title': 'New invention'}]}
        with patch.object(refresh, 'serpapi', return_value=response):
            result = refresh.discover_patents([{'id': 'US1A1', 'title': 'Known'}])
        self.assertEqual([r['publication_number'] for r in result], ['US3A1'])

    def test_new_grant_is_reported_for_existing_application(self):
        response = {'organic_results': [{'publication_number': 'US9B2', 'title': 'Known'}]}
        with patch.object(refresh, 'serpapi', return_value=response):
            result = refresh.discover_patents([{'id': 'US1A1', 'title': 'Known'}])
        self.assertEqual(result[0]['publication_number'], 'US9B2')

    def test_all_provider_failures_preserve_snapshot_and_report_failure(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            content = root / 'source/content'
            content.mkdir(parents=True)
            impact = {'as_of': '2026-10-26', 'citations': 144, 'papers': {}, 'repositories': []}
            refresh.save(content / 'impact.json', impact)
            refresh.save(content / 'publications.json', [])
            refresh.save(content / 'patents.json', [])
            with patch.object(refresh, 'ROOT', root), patch.object(refresh, 'CONTENT', content), \
                 patch.object(refresh, 'fetch', side_effect=OSError('offline')), \
                 patch.dict(refresh.os.environ, {'SERPAPI_KEY': ''}, clear=True):
                refresh.main()
            import json
            self.assertEqual(json.loads((content / 'impact.json').read_text()), impact)
            report = json.loads((root / 'refresh-report/candidates.json').read_text())
            self.assertIn('failed', report['providers']['github'])
            self.assertIn('not configured', report['providers']['scholar'])


if __name__ == '__main__':
    unittest.main()
