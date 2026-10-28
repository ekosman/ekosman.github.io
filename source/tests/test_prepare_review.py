import importlib.util
import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

SCRIPTS = Path(__file__).parents[1] / 'scripts'
sys.path.insert(0, str(SCRIPTS))
spec = importlib.util.spec_from_file_location('prepare_review', SCRIPTS / 'prepare_review.py')
review = importlib.util.module_from_spec(spec)
spec.loader.exec_module(review)


class ProposalTests(unittest.TestCase):
    def paper(self):
        return {'key': 'conf/test/Kosman26', 'title': 'A new paper', 'authors': ['Eitan Kosman', 'Another Author'],
                'year': '2026', 'kind': 'inproceedings', 'venue': 'Test Conference', 'urls': ['https://example.org/paper']}

    def details(self):
        return {'publication_number': 'US99B2', 'title': 'An invention', 'publication_date': '2026-10-28',
                'inventors': [{'name': 'Eitan Kosman'}, {'name': 'Another Inventor'}],
                'assignees': ['Research Company'],
                'worldwide_applications': {'2025': [{'document_id': 'patent/US88A1/en'}]}}

    def test_repeat_run_preserves_reviewers_edits_without_duplicates(self):
        papers, patents = [], []
        report = {'publications': [self.paper()]}
        review.prepare(report, papers, patents, [])
        papers[0]['title'] = 'Reviewer corrected title'
        papers[0]['topic'] = 'Generative models'
        changes, skipped = review.prepare(report, papers, patents, [])
        self.assertEqual(changes, [])
        self.assertEqual(len(papers), 1)
        self.assertEqual(papers[0]['topic'], 'Generative models')

    def test_ignored_and_unverified_authors_are_not_added(self):
        papers = []
        review.prepare({'publications': [self.paper()]}, papers, [], ['conf/test/Kosman26'])
        self.assertEqual(papers, [])
        candidate = self.paper()
        candidate['authors'] = ['Someone Else']
        changes, skipped = review.prepare({'publications': [candidate]}, papers, [], [])
        self.assertEqual(changes, [])
        self.assertEqual(len(skipped), 1)

    def test_grant_replaces_existing_family_application_with_full_inventors(self):
        patents = [{'id': 'US88A1', 'title': 'Earlier title', 'type': 'Published application'}]
        with patch.object(review, 'serpapi', return_value=self.details()):
            changes, skipped = review.prepare({'patents': [{'publication_number': 'US99B2'}]}, [], patents, [])
        self.assertEqual(len(patents), 1)
        self.assertEqual(patents[0]['id'], 'US99B2')
        self.assertEqual(len(patents[0]['inventors']), 2)
        self.assertIn('replaces US88A1', changes[0][0])

    def test_bad_patent_detail_retains_existing_records(self):
        patents = [{'id': 'US88A1', 'title': 'Earlier title', 'type': 'Published application'}]
        details = self.details()
        details['inventors'] = [{'name': 'Someone Else'}]
        with patch.object(review, 'serpapi', return_value=details):
            changes, skipped = review.prepare({'patents': [{'publication_number': 'US99B2'}]}, [], patents, [])
        self.assertEqual(changes, [])
        self.assertEqual(patents[0]['id'], 'US88A1')

    def test_proposed_papers_and_grants_build_into_public_site(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            shutil.copytree(SCRIPTS.parent, root / 'source', ignore=shutil.ignore_patterns('__pycache__'))
            (root / 'assets').mkdir()
            content = root / 'source/content'
            papers = json.loads((content / 'publications.json').read_text(encoding='utf-8'))
            patents = json.loads((content / 'patents.json').read_text(encoding='utf-8'))
            with patch.object(review, 'serpapi', return_value=self.details()):
                review.prepare({'publications': [self.paper()], 'patents': [{'publication_number': 'US99B2'}]}, papers, patents, [])
            review.save(content / 'publications.json', papers)
            review.save(content / 'patents.json', patents)
            subprocess.run([sys.executable, str(root / 'source/scripts/build.py')], check=True, capture_output=True)
            page = (root / 'index.html').read_text(encoding='utf-8')
            self.assertIn('A new paper', page)
            self.assertIn('US99B2', page)
            self.assertNotIn('{{', page)
            self.assertIn('A new paper', (root / 'assets/publications.bib').read_text(encoding='utf-8'))


if __name__ == '__main__':
    unittest.main()
