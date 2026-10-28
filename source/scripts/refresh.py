#!/usr/bin/env python3
"""Refresh public metrics; collect new research records for editorial review.

Standard library only. Each provider is transactional: failures retain its snapshot.
Never log request URLs, as the optional SerpApi URL contains a secret.
"""
import copy
import json
import os
import re
import unicodedata
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlencode, urlparse
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[2]
CONTENT = ROOT / 'source/content'


def normalize(value):
    return re.sub(r'[^a-z0-9]', '', unicodedata.normalize('NFKD', value).lower())


def integer(value):
    if type(value) is not int or value < 0:
        raise ValueError('Expected a nonnegative integer')
    return value


def fetch(url, token=None, xml=False):
    headers = {'User-Agent': 'ekosman-website-updater', 'Accept': 'application/xml' if xml else 'application/json'}
    if token:
        headers['Authorization'] = 'Bearer ' + token
    with urlopen(Request(url, headers=headers), timeout=30) as response:
        body = response.read(10_000_001)
    if len(body) > 10_000_000:
        raise ValueError('Response too large')
    return ET.fromstring(body) if xml else json.loads(body)


def serpapi(engine, **params):
    data = fetch('https://serpapi.com/search.json?' + urlencode({
        'engine': engine, 'api_key': os.environ['SERPAPI_KEY'], **params}))
    if data.get('error'):
        raise ValueError('Provider returned an error')
    return data


def refresh_github(impact, today):
    repos = []
    for page in range(1, 101):
        batch = fetch('https://api.github.com/users/ekosman/repos?' + urlencode({
            'type': 'owner', 'per_page': 100, 'page': page}), os.getenv('GITHUB_TOKEN'))
        if not isinstance(batch, list):
            raise ValueError('Invalid repository response')
        for repo in batch:
            if repo['fork']:
                continue
            if repo['owner']['login'].lower() != 'ekosman':
                raise ValueError('Unexpected repository owner')
            repos.append({'name': repo['name'], 'url': repo['html_url'],
                          'description': repo.get('description') or 'Public code and experiments.',
                          'stars': integer(repo['stargazers_count']),
                          'forks': integer(repo['forks_count'])})
        if len(batch) < 100:
            break
    else:
        raise ValueError('Incomplete repository response')
    if not repos:
        raise ValueError('Empty repository response')
    impact['repositories'] = sorted(repos, key=lambda r: (-r['stars'], r['name'].lower()))
    impact['github_as_of'] = today


def known_titles(paper):
    return {normalize(t) for t in [paper['title'], *paper.get('aliases', [])]}


def refresh_scholar(impact, papers, today):
    articles = []
    first = None
    for start in range(0, 1000, 100):
        data = serpapi('google_scholar_author', author_id='c83p77gAAAAJ', hl='en', num=100, start=start)
        first = first or data
        batch = data['articles']
        if not isinstance(batch, list):
            raise ValueError('Invalid articles')
        articles.extend(batch)
        if not data.get('serpapi_pagination', {}).get('next'):
            break
    else:
        raise ValueError('Incomplete Scholar response')
    if not articles:
        raise ValueError('Empty Scholar response')
    table = first['cited_by']['table']
    # English response fields, never infer a metric from its position in the table.
    totals = {}
    for field, target in [('citations', 'citations'), ('h_index', 'h_index'), ('i10_index', 'i10_index')]:
        matches = [row[field]['all'] for row in table if field in row]
        if len(matches) != 1:
            raise ValueError('Missing Scholar metric')
        totals[target] = integer(matches[0])
    metrics = copy.deepcopy(impact['papers'])
    for paper in papers:
        matches = [a for a in articles if normalize(a['title']) in known_titles(paper)]
        # Ambiguous/merged records are not summed or guessed.
        if len(matches) != 1:
            continue
        cited = matches[0].get('cited_by', {})
        if 'value' not in cited:
            continue
        count = integer(cited['value'])
        link = cited.get('link') or matches[0]['link']
        if urlparse(link).hostname != 'scholar.google.com' or not link.startswith('https://'):
            raise ValueError('Unexpected citation URL')
        metrics[paper['id']] = {'count': count, 'url': link, 'as_of': today}
    # Give unmatched badges their original date before advancing the total's date.
    for metric in metrics.values():
        metric.setdefault('as_of', impact['as_of'])
    impact.update(totals)
    impact['papers'] = metrics
    impact['as_of'] = today


def discover_publications(papers):
    root = fetch('https://dblp.org/pid/298/2651.xml', xml=True)
    if root.tag != 'dblpperson' or root.get('name') != 'Eitan Kosman':
        raise ValueError('Unexpected DBLP profile')
    known = set().union(*(known_titles(p) for p in papers))
    links = {p[k].rstrip('/') for p in papers for k in ('url', 'record') if k in p}
    found = []
    for record in root.findall('r'):
        entry = next(iter(record), None)
        if entry is None:
            continue
        title = ''.join(entry.find('title').itertext()).rstrip('.')
        urls = [e.text for e in entry.findall('ee') if e.text]
        if normalize(title) in known or any(u.rstrip('/') in links for u in urls):
            continue
        found.append({'key': entry.get('key'), 'title': title,
                      'kind': entry.tag,
                      'year': entry.findtext('year'), 'venue': entry.findtext('booktitle') or entry.findtext('journal'),
                      'authors': [a.text for a in entry.findall('author')], 'urls': urls})
    return found


def discover_patents(patents):
    known = {p['id'] for p in patents}
    titles = {normalize(p['title']) for p in patents}
    found = []
    for page in range(10):
        data = serpapi('google_patents', inventor='Eitan Kosman', num=100, page=page)
        batch = data.get('organic_results')
        if not isinstance(batch, list):
            raise ValueError('Missing patent results')
        for record in batch:
            number = record.get('publication_number', '')
            if number in known:
                continue
            # A newly issued grant deserves review even when the application title matches.
            if normalize(record.get('title', '')) in titles and not re.search(r'B\d+$', number):
                continue
            # Search results may abbreviate inventors; keep candidates out of the public archive.
            found.append({k: record.get(k) for k in ('publication_number', 'title', 'patent_link',
                          'publication_date', 'inventor', 'assignee')})
        if not data.get('serpapi_pagination', {}).get('next'):
            break
    else:
        raise ValueError('Incomplete patent results')
    return found


def save(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')


def main():
    impact = json.loads((CONTENT / 'impact.json').read_text(encoding='utf-8'))
    papers = json.loads((CONTENT / 'publications.json').read_text(encoding='utf-8'))
    patents = json.loads((CONTENT / 'patents.json').read_text(encoding='utf-8'))
    today = datetime.now(timezone.utc).date().isoformat()
    report = {'checked_at': today, 'providers': {}, 'publications': [], 'patents': []}

    def run(name, operation, metric=False):
        nonlocal impact
        snapshot = copy.deepcopy(impact)
        try:
            result = operation(snapshot) if metric else operation()
            if metric:
                impact = snapshot
            else:
                report[name] = result
            report['providers'][name] = 'ok'
            print(name + ': refreshed' if metric else name + ': checked')
        except Exception as error:
            # Exception strings from HTTP libraries can contain API keys.
            report['providers'][name] = 'failed (' + type(error).__name__ + '); previous data retained'
            print('::warning::' + name + ': unavailable; previous data retained')

    run('github', lambda data: refresh_github(data, today), metric=True)
    run('publications', lambda: discover_publications(papers))
    if os.getenv('SERPAPI_KEY'):
        run('scholar', lambda data: refresh_scholar(data, papers, today), metric=True)
        run('patents', lambda: discover_patents(patents))
    else:
        report['providers'].update(scholar='not configured: SERPAPI_KEY', patents='not configured: SERPAPI_KEY')
        print('Scholar and patent discovery skipped: SERPAPI_KEY is not configured.')
    save(CONTENT / 'impact.json', impact)
    output = ROOT / 'refresh-report'
    output.mkdir(exist_ok=True)
    save(output / 'candidates.json', report)
    lines = ['# Website refresh', '', 'Checked: ' + today, '']
    lines.extend('- ' + name + ': ' + state for name, state in report['providers'].items())
    lines += ['', 'New records need review to avoid duplicate papers and patent families.']
    for category in ('publications', 'patents'):
        lines += ['', '## ' + category.title(), '']
        lines.extend('- ' + str(item.get('title')) + ' — ' + str(item.get('patent_link') or item.get('urls')) for item in report[category])
        if not report[category]:
            lines.append('No candidates returned. See provider status above for coverage.')
    summary = '\n'.join(lines) + '\n'
    (output / 'summary.md').write_text(summary, encoding='utf-8')
    if os.getenv('GITHUB_STEP_SUMMARY'):
        with open(os.environ['GITHUB_STEP_SUMMARY'], 'a', encoding='utf-8') as stream:
            stream.write(summary)


if __name__ == '__main__':
    main()
