# Automatic website updates

The workflow in `.github/workflows/refresh-site.yml` builds and deploys on pushes
to `main`, every Monday at 06:23 UTC, and when run manually from GitHub Actions.
Schedules can be delayed; this is not an exact delivery time.

## One-time setup

1. Commit and push these files to `ekosman/ekosman.github.io` on `main`.
2. In **Settings → Pages → Build and deployment → Source**, select **GitHub Actions**.
   This replaces the older branch-based publishing instructions.
3. Enable Actions if disabled. The workflow requests permission to save metric
   snapshots to `main`. If branch protection prevents bot pushes, allow this
   workflow to push, or remove the `Save refreshed snapshots` step. Without that
   step, updates deploy but are not saved for future fallbacks.
   Also enable **Settings → Actions → General → Workflow permissions → Allow
   GitHub Actions to create and approve pull requests**. The workflow creates PRs;
   it never approves or merges them automatically.
4. For automatic Scholar counts and patent discovery, create a
   [SerpApi account](https://serpapi.com/) and save its key under
   **Settings → Secrets and variables → Actions → New repository secret**,
   named **`SERPAPI_KEY`**. Keep it out of repository files and browser JavaScript.
   Check the provider's current quota and pricing before choosing a plan.
5. Open **Actions → Refresh and publish website → Run workflow** on `main`.
   Check the provider statuses in the run summary and the Pages deployment.

No personal GitHub token is required. The workflow uses GitHub's built-in token.
Without SerpApi, GitHub metrics and DBLP discovery still run; Scholar retains its
dated snapshot, and patent discovery is explicitly marked unconfigured.

## What happens automatically

| Content | Behavior |
| --- | --- |
| GitHub repositories | Refresh saved descriptions, cards, stars and forks for owned public repositories, excluding forks; feature the top three by stars |
| Scholar totals | Refresh citations, h-index and i10-index through SerpApi |
| Per-paper citations | Match exact normalized titles or explicit aliases; refresh unambiguous matches and retain unmatched badges' original dates |
| New publications | Check DBLP and propose content additions in one review PR |
| New patents | Search Google Patents, verify full inventor details, and propose additions or grant upgrades in that PR |
| Source edits | Rebuild the page and BibTeX on every push to `main` |
| Deployment | Publish the generated public files to GitHub Pages |

New papers, venue changes, grants, and patent families require editorial review.
The script adds proposals on a review branch; they enter the public archive only
after you merge. It does not infer legal status beyond the publication kind code.
Title changes and national equivalents make blind imports prone to duplicates.
Existing curated bibliography and featured descriptions are preserved. DBLP can
lag publishers, so discovery is not an exhaustive guarantee.

The workflow opens or updates **Review new papers and patents** from the branch
`automation/research-updates`. Open **Files changed**, check the authors/inventors,
venue, year, publication type and possible duplicates, then **Merge pull request**.
Merging triggers the existing build and deployment. Generated HTML and BibTeX are
built for validation before opening the PR, and rebuilt for publication on merge;
the PR contains the content JSON edits so the diff stays readable.

You can correct topics or metadata directly on the PR branch. Later runs append
new records and merge `main` into that branch without force-pushing or overwriting
your edits. A merge conflict stops the review job for manual resolution and does
not block the separate Pages deployment. If you close the PR without merging,
proposals pause until you reopen it.

To reject an individual proposal permanently, remove it from the JSON and add
its DBLP `source_key` or patent publication number to the array in
`source/content/discovery-ignore.json`, then merge the remaining changes.
Records lacking enough verified metadata remain in the discovery artifact and
are mentioned in the PR body when a PR exists. See the run summary and
**research-refresh-report** artifact for provider coverage and raw candidate data.
An optional `aliases` array on a publication records older titles for matching.
Bio, employment, education, talks, service, and photographs remain manual edits
in `source/scripts/template.html` and `assets/`.

## Failures and monitoring

Providers update independently. Failed, incomplete, or malformed responses retain
that provider's previous snapshot. Dates only advance for successfully refreshed
data. Provider failures produce warnings and appear in the summary; they do not
stop publishing available content. A green workflow can include an unavailable
provider: inspect the summary when checking freshness.

SerpApi usually needs one Scholar request and one patent search request per weekly
run for this profile, plus one details request for each new patent proposal.
Larger result sets use pagination, with explicit safety limits.
Manual runs also use quota. Public GitHub schedules may be disabled after 60 days
without repository activity; re-enable in Actions if needed.

## Local checks

```sh
python -m unittest discover -s source/tests -v
python source/scripts/refresh.py
python source/scripts/build.py
```

The updater requires network access. `SERPAPI_KEY` is optional; `GITHUB_TOKEN` can
be supplied locally for GitHub rate limits. Local reports are ignored by Git.

References: [GitHub Pages workflows](https://docs.github.com/en/pages/getting-started-with-github-pages/using-custom-workflows-with-github-pages),
[Scholar author API](https://serpapi.com/google-scholar-author-api),
[patent search API](https://serpapi.com/google-patents-api).
