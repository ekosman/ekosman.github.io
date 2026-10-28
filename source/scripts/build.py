#!/usr/bin/env python3
"""Regenerate the static site after editing content JSON or template.html.

Python 3, standard library only. No command is needed to view or deploy the website.
"""
import json
from html import escape
from pathlib import Path

ROOT=Path(__file__).resolve().parent.parent
DIST=ROOT.parent
papers=json.loads((ROOT/'content/publications.json').read_text(encoding='utf-8'))
patents=json.loads((ROOT/'content/patents.json').read_text(encoding='utf-8'))

impact=json.loads((ROOT/'content/impact.json').read_text(encoding='utf-8'))

def display_date(value):
    from datetime import date
    parsed = date.fromisoformat(value)
    return f'{parsed.day} {parsed:%B %Y}'

def name(author):
    if ', ' in author:
        last, first = author.split(', ',1)
        return first+' '+last
    return author

def names(authors):
    return ', '.join('<strong>'+escape(name(a))+'</strong>' if name(a)=='Eitan Kosman' else escape(name(a)) for a in authors)

def bibtex(p):
    entry='article' if p['type'] in ['Journal','Preprint'] else 'inproceedings'
    fields={'title':p['title'],'author':' and '.join(p['authors']),'year':str(p['year'])}
    if p['type']=='Preprint':fields['journal']='arXiv preprint arXiv:'+p['url'].split('/')[-1]
    for key in ['booktitle','journal','volume','number','pages','doi']:
        if key in p:fields[key]=p[key]
    fields['url']=p.get('record',p['url'])
    return '@'+entry+'{kosman'+str(p['year'])+p['id'].replace('-','')+',\n'+',\n'.join('  '+k+' = {'+v+'}' for k,v in fields.items())+'\n}'

citations={}
rows=[]
for p in papers:
    citations[p['id']]={'title':p['title'],'bibtex':bibtex(p)}
    authors=names(p['authors'])
    if len(p['authors'])>9:
        authors=escape(name(p['authors'][0]))+' et al., including <strong>Eitan Kosman</strong>'
        authors+='<details class="author-disclosure"><summary>All '+str(len(p['authors']))+' authors</summary><p>'+names(p['authors'])+'</p></details>'
    links=[]
    for text,key in [('Paper ↗','url'),('PDF ↗','pdf'),('Proceedings ↗' if p['type']!='Journal' else 'Journal ↗','record'),('Project ↗','project')]:
        if key in p:links.append('<a href="'+escape(p[key])+'" target="_blank" rel="noopener noreferrer">'+text+'</a>')
    links.append('<button class="js-only" type="button" data-cite="'+escape(p['id'])+'" aria-label="Cite '+escape(p['title'])+'">Cite ↗</button>')
    if p['id'] in impact['papers']:
        metric=impact['papers'][p['id']]
        links.append('<a class="citation-count" href="'+escape(metric['url'])+'" target="_blank" rel="noopener noreferrer" title="Google Scholar snapshot, '+escape(metric.get('as_of',impact['as_of']))+'">'+str(metric['count'])+(' citation' if metric['count']==1 else ' citations')+' ↗</a>')
    topics=[p['topic']]
    if p['id']=='edge':topics.append('Generative models')
    first='<span class="pub-first">FIRST AUTHOR</span>' if p.get('first') else ''
    rows.append(f'''<article class="publication" id="pub-{escape(p['id'])}" data-topics="{escape('|'.join(topics))}">
      <div class="pub-year">{p['year']}</div><div class="pub-body"><div class="pub-topline"><span class="pub-venue">{escape(p['venue'])}</span><span class="pub-type">{escape(p['type'])}</span>{first}</div><h3><a href="{escape(p.get('record',p['url']))}" target="_blank" rel="noopener noreferrer">{escape(p['title'])}</a></h3><div class="pub-authors">{authors}</div><div class="pub-links">{''.join(links)}</div></div></article>''')

patent_rows=[]
for p in patents:
    if p['id']=='US12284397B2':continue
    inventor_names=' · '.join('<strong>'+escape(a)+'</strong>' if a=='Eitan Kosman' else escape(a) for a in p['inventors'])
    patent_rows.append(f'''<a class="patent-entry" href="{escape(p['url'])}" target="_blank" rel="noopener noreferrer"><div class="patent-id">{escape(p['id'])}<span>{p['year']} · {escape(p['type'])}</span></div><div><h4>{escape(p['title'])}</h4><p>{inventor_names}</p></div><span aria-hidden="true">↗</span></a>''')

page=(ROOT/'scripts/template.html').read_text(encoding='utf-8').replace('{{PUBLICATIONS}}','\n'.join(rows)).replace('{{PATENTS}}','\n'.join(patent_rows)).replace('{{CITATIONS}}',json.dumps(citations,ensure_ascii=False).replace('</','<\\/'))
page=page.replace('{{PUBLICATION_COUNT}}',str(len(papers))).replace('{{APPLICATION_COUNT}}',str(len(patent_rows)))
page=page.replace('{{SCHOLAR_DATE}}',display_date(impact['as_of'])).replace('{{GITHUB_DATE}}',display_date(impact.get('github_as_of',impact['as_of'])))
repo_cards=[]
for r in impact['repositories']:
    repo_cards.append('<article class="repo-card" data-repo="'+escape(r['name'])+'"><a href="'+escape(r['url'])+'" target="_blank" rel="noopener noreferrer"><h3>'+escape(r['name'])+' <span aria-hidden="true">↗</span></h3></a><p>'+escape(r['description'])+'</p><div class="repo-counts"><a href="'+escape(r['url'])+'/stargazers"><b data-stars>'+str(r['stars'])+'</b> stars</a><a href="'+escape(r['url'])+'/forks"><b data-forks>'+str(r['forks'])+'</b> forks</a></div></article>')
page=page.replace('{{REPO_FEATURED}}',''.join(repo_cards[:3])).replace('{{REPO_ARCHIVE}}',''.join(repo_cards[3:]))
for key,value in {'TOTAL_STARS':sum(r['stars'] for r in impact['repositories']),'TOTAL_FORKS':sum(r['forks'] for r in impact['repositories']),'TOTAL_CITATIONS':impact['citations'],'H_INDEX':impact['h_index'],'I10_INDEX':impact['i10_index']}.items():
    page=page.replace('{{'+key+'}}',str(value))
if '{{' in page:
    raise ValueError('Unresolved template placeholder')
(DIST/'index.html').write_text(page,encoding='utf-8')
(DIST/'assets/publications.bib').write_text('\n\n'.join(v['bibtex'] for v in citations.values())+'\n',encoding='utf-8')
print(f'Generated {len(papers)} publications and {len(patents)} patent records.')
