# Project submission checklist

The screenshot shows a required four-link project form. Each link must be a working `https://` URL. **Local PDF, HTML and ZIP files are not URLs accepted by the form** until you upload/publish them to a web-accessible service.

| Required field | How to create the link | Verified? |
|---|---|---|
| GitHub Repository Link | Create a public GitHub repository and upload the extracted public project ZIP contents. Copy its GitHub `https://github.com/...` URL. | [ ] |
| Research paper link (approved/published if applicable) | Use the viewable GitHub PDF link at `/blob/main/reports/Research_Paper.pdf`, or an authorized Google Drive PDF view link; never claim external approval or peer-reviewed publication. | [ ] |
| Deployed project link | Deploy `app.py` via https://share.streamlit.io/ from the repository and copy the resulting app's `https://...streamlit.app` address. | [ ] |
| Project feedback video link | Record an authentic 90-120s screen walkthrough + spoken reflections, use the script in `reports/Feedback_Video_Script.md` if useful, publish to YouTube (unlisted) or Loom, and copy the URL. | [ ] |

## Practical upload sequence

**Step 1:** Download the `Nassau_Route_Efficiency_Project.zip` file and extract locally.

**Step 2:** Sign in to GitHub at https://github.com/ and create a new public repository. Upload the *contents* of the extracted folder, including hidden `.streamlit/config.toml`, `.github/workflows/ci.yml`, `data/public_demo_orders.csv`, `reports/` and `assets/`. Avoid publishing private source data, customer identifiers or address information without authorization. The public package deliberately omits the original uploaded CSV.

**Step 3:** In Streamlit Community Cloud (`https://share.streamlit.io/`), create a new app from your GitHub repository. Main entry file: `app.py`; branch: `main`; dependencies: `requirements.txt`. When it finishes building, open the live app and check all five tabs. The default public demo shows the same case-study aggregate statistics.

**Step 4:** Open the research PDF from the GitHub repository itself and copy its **public page URL**. This is a research *write-up*, not a claim of academic peer review. If the form expects formal publication rather than a shareable paper, consult the platform's instructions before claiming approval.

**Step 5:** Make a screen recording while opening the dashboard. Describe the data-quality discovery honestly, plus skills learned; record in your own voice. Upload it publicly/unlisted where a reviewer can view it and copy the link. The supplied video script alone is not a video submission.

**Step 6:** Open the four links in private/incognito browsing to verify they all work without special sign-in. Paste into the fields (GitHub, paper, Streamlit, feedback video) and submit from your own account.

## Link safety checks

- The link must start with `https://` and must be accessible to evaluators.
- Do not submit a fictitious or placeholder URL. None have been generated or posted automatically.
- Make sure the source ZIP's folder is **not** added as an extra nested path inside the GitHub repository. `app.py` must be at repository root.
- The commercial site https://www.nassaucandy.com/ is background research, **not** the assignment submission portal. Its website did not provide an accessible link to your submission form.
- Protect the source file `Nassau Candy Distributor (1).csv` and any real customer details; share them only with permission.

## Troubleshooting

**Blank page or missing CSV on Streamlit Cloud:** Confirm `data/public_demo_orders.csv` is present at repo root relative to `app.py`, including identical capitalization.

**Deployment import error:** Keep `requirements.txt` in the repository root. Use Python 3.11+ and check Cloud logs for missing dependencies.

**US map blank:** Verify Streamlit browser permits Plotly map rendering and that your filters include United States. Canada is excluded from the US-state choropleth by design.

**Unexpected metrics:** The app defaults to a prominent *exploratory adjusted* view. Switch to *Raw recorded dates* to inspect the source values, which exhibit multi-year date artifacts.

**No factories/routes after filter:** Reset state, country, mode and factory multiselects, and lower the minimum dispatches slider.
