# Publish your website on GitHub Pages

The package is configured for the GitHub username linked from your existing website: **ekosman**. The intended site address is **https://ekosman.github.io/**. It becomes available after you publish. This package does not create or modify a GitHub repository automatically.

## Option 1: Publish through the GitHub website

### 1. Create the repository

Sign in to GitHub. Choose **New repository** and name it exactly:

```text
ekosman.github.io
```

Select **Public**, add a README, and create the repository. GitHub Pages is available with GitHub Free for public repositories.

If this repository already exists, use it. Keep an existing `CNAME` file if you use a custom domain. If your GitHub username is different, name the repository `YOUR_USERNAME.github.io` and update the site address as described below.

### 2. Upload the website

1. Extract `Eitan_Kosman_Blue_Website.zip` on your computer.
2. Open its `eitan-kosman-blue-website` folder.
3. In your repository, choose **Add file → Upload files**.
4. Upload the **contents of that folder**. Upload the actual files and folders, not the ZIP and not the containing folder itself.
5. Commit the upload to the `main` branch.

`index.html` must be at the top level of the repository, beside `assets/`. It must not be inside another `eitan-kosman-blue-website` folder on GitHub. The optional `source/` folder contains the editable sources and can be uploaded too.

The package includes `.nojekyll`, which tells GitHub to serve the site as ordinary static files. Some file pickers hide files beginning with a period. If it is missing after upload, use **Add file → Create new file**, name it `.nojekyll`, and commit the empty file.

### 3. Enable Pages

In the repository:

1. Open **Settings → Pages**.
2. Under **Build and deployment**, set **Source** to **Deploy from a branch**.
3. Set the branch to **main**.
4. Set the folder to **/ (root)**.
5. Select **Save**.

No theme, framework, GitHub Actions workflow, or build command is needed.

### 4. Open the live site

Wait for the Pages deployment to finish. GitHub says changes can take up to 10 minutes to publish. The **Settings → Pages** screen will show the published address and a **Visit site** link. The repository's **Actions** tab shows the Pages deployment status.

Your intended address is:

```text
https://ekosman.github.io/
```

### 5. Check the finished result

Open the site on a phone and desktop. Try the research illustration, publication search, a citation download, the patent archive, and your contact links. Update your Google Sites homepage, Google Scholar homepage, and LinkedIn website field to point to the new address when you are ready.

## Option 2: Publish using Git

Create an empty public repository named `ekosman.github.io` on GitHub, without adding a README. Then open a terminal inside the extracted `eitan-kosman-blue-website` folder:

```bash
git init
git add .
git commit -m "Create personal research website"
git branch -M main
git remote add origin https://github.com/ekosman/ekosman.github.io.git
git push -u origin main
```

Use your normal GitHub authentication. If the repository already has files, clone it and copy the website into that checkout instead of initializing a separate repository or forcing a push.

Then enable **Settings → Pages → Deploy from a branch → main → / (root)** as above.

For future updates:

```bash
git add .
git commit -m "Update research website"
git push
```

## Updating publications and experience

1. Edit `source/content/publications.json` or `source/content/patents.json` for records.
2. Edit `source/scripts/template.html` for the biography, experience, education, talks, and service.
3. Run `python3 source/scripts/build.py`.
4. Preview `index.html` locally.
5. Commit and push the updated source and generated files.

Each publication has an `id`, `title`, `authors`, `year`, `venue`, `type`, `topic`, and `url`. Author names use `Last, First`. Optional fields include `pdf`, `record`, `project`, `first`, `booktitle`, `journal`, `volume`, `number`, `pages`, and `doi`. Use an existing entry as the template. The built in topic buttons use `Generative models`, `Graphs & structure`, and `Motion & vision`.

After adding a publication, the page and bibliography are regenerated together. If you only edit the JSON online without running the generator, the visible website will not change.

## A different username, repository, or custom domain

Local CSS, JavaScript, and image links use relative paths, so the website also works under a project path such as `https://YOUR_USERNAME.github.io/research/`.

Replace `https://ekosman.github.io/` with your final site address in:

* `source/scripts/template.html`, then regenerate `index.html`.
* `sitemap.xml`.
* The homepage link in `404.html`.
* The sitemap line in `robots.txt`.

This updates the canonical URL, social preview URL, structured data, and search indexing links. Update the GitHub profile links only if your account name has also changed. For a custom domain, follow GitHub's domain setup guide and retain the resulting `CNAME` file.

## Troubleshooting

| Symptom | Check |
| --- | --- |
| 404 at the site address | Repository name, Pages source, selected branch, and root folder |
| GitHub displays the README instead of your site | Make sure `index.html` is at the repository root |
| Missing styling or graphics | Upload the entire `assets/` folder with its original filenames |
| A change is not visible yet | Check deployment completion, then refresh with the browser cache bypassed |
| Content JSON changed but the page did not | Run the generator and upload the regenerated `index.html` |
| An external paper page blocks your browser | Use the alternate arXiv or PDF link where supplied |
| A social preview still shows an old image | Preview providers may cache metadata after a deployment |

## Official GitHub documentation

* [Quickstart for GitHub Pages](https://docs.github.com/en/pages/quickstart)
* [Configuring a publishing source](https://docs.github.com/en/pages/getting-started-with-github-pages/configuring-a-publishing-source-for-your-github-pages-site)
* [Managing a custom domain](https://docs.github.com/en/pages/configuring-a-custom-domain-for-your-github-pages-site)

Publishing steps checked against GitHub's documentation on 26 October 2026.

## Impact metrics

`source/content/impact.json` holds the dated Google Scholar snapshot, per paper citation counts and public repository snapshot. Update these fields and run the generator to refresh the saved figures. Citation counts are from Google Scholar on 26 October 2026. The website refreshes GitHub stars and forks on each visit using GitHub's public API, excluding repositories forked from other owners. If the API is unavailable or rate limited, dated saved figures remain visible. Google Scholar counts use the saved snapshot and link directly to the citation record. No API key is required.
