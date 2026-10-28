#!/usr/bin/env python3
"""Prepare reviewable content edits on the automation branch, never on main."""
import hashlib
import json
import re
from datetime import date
from pathlib import Path
from urllib.parse import urlparse

from refresh import ROOT, CONTENT, known_titles, normalize, save, serpapi


def safe_url(value):
    return isinstance(value, str) and urlparse(value).scheme == 'https' and bool(urlparse(value).hostname)


def publication(candidate, papers):
    title = candidate['title']
    urls = [u for u in candidate.get('urls', []) if safe_url(u)]
    authors = candidate.get('authors') or []
    if not urls or 'Eitan Kosman' not in authors or not candidate.get('key'):
        raise ValueError('Missing publication identity or source')
    if any(normalize(title) in known_titles(p) or p.get('source_key') == candidate['key'] for p in papers):
        return None
    if any(u.rstrip('/') == p.get(k, '').rstrip('/') for u in urls for p in papers for k in ('url', 'record')):
        return None
    year = int(candidate['year'])
    if not 1900 <= year <= date.today().year + 1:
        raise ValueError('Invalid publication year')
    venue = candidate.get('venue') or 'Publication'
    preprint = venue.lower() in ('corr', 'arxiv')
    kind = 'Preprint' if preprint else ('Journal' if candidate.get('kind') == 'article' else
                                      'Workshop' if 'workshop' in venue.lower() else 'Conference')
    # Preserve full display names while using the archive's Last, First convention.
    names = [a.rsplit(' ', 1)[-1] + ', ' + a.rsplit(' ', 1)[0] if ' ' in a else a for a in authors]
    record = {'id': 'dblp-' + hashlib.sha256(candidate['key'].encode()).hexdigest()[:12],
              'source_key': candidate['key'], 'title': title, 'authors': names, 'year': year,
              'venue': venue, 'type': kind, 'topic': 'Other research', 'url': urls[0]}
    if not preprint:
        record['journal' if kind == 'Journal' else 'booktitle'] = venue
    return record


def patent(candidate, patents):
    number = candidate['publication_number']
    if not re.fullmatch(r'[A-Z]{2}\d+[AB]\d', number):
        raise ValueError('Unsupported patent publication number')
    if any(p['id'] == number for p in patents):
        return None, None
    details = serpapi('google_patents_details', patent_id='patent/' + number + '/en')
    inventors = [i['name'] for i in details['inventors']]
    if details['publication_number'] != number or not any(normalize(i) == 'eitankosman' for i in inventors):
        raise ValueError('Patent identity not confirmed')
    published = date.fromisoformat(details['publication_date'])
    granted = bool(re.search(r'B\d$', number))
    family = {a.get('document_id', '').split('/')[1] for entries in details.get('worldwide_applications', {}).values()
              for a in entries if a.get('document_id', '').startswith('patent/')}
    matches = [p for p in patents if p['id'] in family or normalize(p['title']) == normalize(details['title'])]
    if matches and (not granted or any(p['type'] == 'Granted patent' for p in matches)):
        return None, None
    if len(matches) > 1:
        raise ValueError('Multiple existing family records require manual reconciliation')
    record = {'id': number, 'title': details['title'], 'year': published.year,
              'type': 'Granted patent' if granted else 'Published application',
              'date': f'{published.day} {published:%B %Y}', 'inventors': inventors,
              'url': 'https://patents.google.com/patent/' + number + '/en',
              'assignee': ', '.join(details.get('assignees', []))}
    return record, matches[0]['id'] if matches else None


def prepare(report, papers, patents, ignored):
    changes, skipped = [], []
    for candidate in report.get('publications', []):
        if candidate.get('key') in ignored:
            continue
        try:
            record = publication(candidate, papers)
            if record:
                papers.insert(0, record)
                changes.append(('Paper', record['title'], record['url']))
        except (KeyError, TypeError, ValueError):
            skipped.append(candidate.get('title', 'Unknown paper'))
    for candidate in report.get('patents', []):
        if candidate.get('publication_number') in ignored:
            continue
        try:
            record, replaced = patent(candidate, patents)
            if record:
                if replaced:
                    patents[ next(i for i, p in enumerate(patents) if p['id'] == replaced) ] = record
                else:
                    patents.append(record)
                changes.append(('Patent' + (' (replaces ' + replaced + ')' if replaced else ''), record['title'], record['url']))
        except Exception:
            # Provider exceptions can contain credentials. Report only the candidate title.
            skipped.append(candidate.get('title', 'Unknown patent'))
    return changes, skipped


def main():
    report = json.loads((ROOT / 'refresh-report/candidates.json').read_text(encoding='utf-8'))
    papers = json.loads((CONTENT / 'publications.json').read_text(encoding='utf-8'))
    patents = json.loads((CONTENT / 'patents.json').read_text(encoding='utf-8'))
    ignored_path = CONTENT / 'discovery-ignore.json'
    ignored = json.loads(ignored_path.read_text(encoding='utf-8')) if ignored_path.exists() else []
    changes, skipped = prepare(report, papers, patents, ignored)
    if changes:
        save(CONTENT / 'publications.json', papers)
        save(CONTENT / 'patents.json', patents)
    lines = ['New research records are proposed below. Existing pending edits are preserved on this branch.', '',
             'Review authors/inventors, venue and type, and duplicate works or patent families before merging.',
             'New papers use the neutral topic **Other research**; adjust it if appropriate.',
             'Merging rebuilds and publishes the website automatically.', '', '### Added in this run', '']
    # Escape provider text so it is prose, not arbitrary Markdown links or mentions.
    def literal(value):
        return str(value).replace('`', "'").replace('\n', ' ').replace('@', '@\u200b')
    lines.extend('- ' + kind + ': `' + literal(title) + '` — <' + url.replace('>', '%3E') + '>' for kind, title, url in changes)
    if not changes:
        lines.append('No additional records this run; see Files changed for pending proposals.')
    if skipped:
        lines += ['', '### Could not prepare automatically', '']
        lines.extend('- `' + literal(title) + '` — inspect the discovery artifact.' for title in skipped)
    lines += ['', 'To dismiss a record permanently, remove the proposal and add its DBLP key or patent number to',
              '`source/content/discovery-ignore.json` on this branch before merging.', '',
              'Provider coverage:']
    lines.extend('- ' + key + ': ' + literal(value) for key, value in report.get('providers', {}).items())
    (ROOT / 'refresh-report/pr-body.md').write_text('\n'.join(lines) + '\n', encoding='utf-8')
    if skipped:
        print('::warning::Some candidates could not be prepared; see the review report.')
    print(f'Prepared {len(changes)} proposed additions or upgrades.')


if __name__ == '__main__':
    main()
