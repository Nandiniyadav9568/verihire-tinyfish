# VeriHire + TinyFish Search

## Problem Statement

Students frequently receive internship and placement-related emails that may contain fake job offers, recruitment-fee requests, suspicious links, or requests for sensitive personal information. It can be difficult to distinguish genuine opportunities from fraudulent ones.

There is a need for a simple solution that helps students identify suspicious emails and investigate the claimed employer using relevant information available on the web.

## Proposed Solution

VeriHire is an email scam detection system designed to help students analyze potentially fraudulent internship and placement-related emails. It identifies suspicious warning signs, generates a risk score, and displays a report with safety recommendations.

By integrating the TinyFish Search API, VeriHire can also search for publicly available information about the claimed employer and possible recruitment scams. This provides additional context to help students investigate opportunities before trusting them.

## Project Objectives

- Identify suspicious indicators in internship and placement-related emails.
- Generate a risk score and a readable risk report.
- Use TinyFish to research the claimed employer and relevant scam reports.
- Display available web research results and source links.
- Encourage students to verify opportunities through official employer channels.

- 
## How TinyFish Search Works and Its Relevance to VeriHire

### What is TinyFish?

TinyFish Search API enables VeriHire to search the web for publicly available information related to a claimed employer and potential recruitment scams. It returns search results that can include titles, URLs, and snippets.

### Search Phrases Used in VeriHire

VeriHire uses meaningful search phrases to investigate internship and placement-related emails. For example:

- **Company name + recruitment + internship scam** – Searches for reports or warnings associated with a company's recruitment process.
- **Company name + careers + scam** – Looks for publicly available information about potentially fraudulent career opportunities.
- **Company name + impersonation** – Searches for information about people or websites pretending to represent the claimed employer.
- **Company domain + recruitment scam** – Helps investigate reports associated with the domain mentioned in an email.

For example, if an email claims to represent a company named ABC Technologies, a research query could be:

`ABC Technologies recruitment careers internship scam impersonation`

These phrases are intended to find relevant public information. They do not automatically prove that a company or email is fraudulent.

### Why Is This Relevant to VeriHire?

Students may receive fake internship offers that use the names of real companies. Checking only the wording of an email may not reveal whether the opportunity has been reported as suspicious.

TinyFish adds an external web-research layer to VeriHire by searching for relevant employer information and possible recruitment scam reports. This helps users review evidence beyond the email itself.

### How the Search Results Are Used

1. The user submits an internship or placement-related email.
2. VeriHire's local analysis checks the email for suspicious warning signs.
3. With the user's consent, the backend sends the claimed company name and/or sender domain to TinyFish as a search query.
4. TinyFish returns available web-search results.
5. VeriHire displays the source links and snippets in the Web Research section.
6. The user reviews the information and independently verifies the opportunity.

### How TinyFish Complements Risk Scoring

VeriHire's local rules calculate the email risk score. TinyFish provides additional web research, which is displayed separately from that score.

A search result is not proof of fraud, and the absence of negative results does not prove that an opportunity is genuine. Users should verify offers through official company websites and recruitment contacts.

### Example Use Case

Suppose a student receives an internship offer claiming to come from ABC Technologies. The email asks the student to pay a registration fee.

VeriHire can flag the payment request as a warning sign. TinyFish can then search for publicly available information related to ABC Technologies, internship recruitment, scams, and impersonation. The student can review the search results and verify the offer through the company's official recruitment channels before taking action.

This combination of email analysis and web research makes VeriHire more informative and relevant to its goal of helping students identify potentially fraudulent internship and placement-related emails.
# VeriHire + TinyFish Search

Your existing dark/lime responsive website, with a same-origin Python backend and live research inside the risk report.

## 1. Start locally

Requires Python 3.10+.

```bash
python -m venv .venv
# macOS/Linux:
source .venv/bin/activate
# Windows PowerShell instead: .venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

Set the key **in the server terminal**, never in the HTML or JavaScript:

```bash
# macOS/Linux
export TINYFISH_API_KEY='YOUR_PRIVATE_TINYFISH_KEY'
python app.py
```

Windows PowerShell:

```powershell
$env:TINYFISH_API_KEY="YOUR_PRIVATE_TINYFISH_KEY"
python app.py
```

Open http://127.0.0.1:8000. Keep using that exact address (not localhost) so the browser origin matches. Do not open the HTML as a file. The example environment file is a reference only; the app does not automatically load .env files.

## 2. Try it

1. Paste the sender and email as before.
2. Enter the employer name, especially if the sender uses Gmail or another public provider.
3. Enable the TinyFish research consent checkbox.
4. Click Analyze email.
5. Read the local risk score and the new Web research section below it.

The backend sends only the company name and/or sender domain as a short search query. It rejects email body fields. Never put personal information in the company field. Your browser email inputs are not persisted by the application; browser extensions or autofill are outside its control.

## 3. Why the chat preview cannot run research

Inspection found that a Flask backend already existed, and the Analyze Email button already called its same-origin `/api/research` route. The confirmed usage was the Julius/chat HTML preview, not a deployed Python web service. That preview does not start this Flask backend. Adding a secret to frontend code would not fix that problem and would expose it.

The fix keeps the HTML, CSS, layout, local-analysis code and existing features unchanged. It improves response validation, missing-backend/network/timeout errors and overlapping request cleanup; adds a non-sensitive health endpoint and a Render deployment configuration; and retains server-only authentication. Open the locally served or deployed site for live research. No browser preview or application error response contains the TinyFish key. Do not use frontend environment prefixes such as VITE_, NEXT_PUBLIC_, or PUBLIC_ for the API key.

## 4. Publish it on Render (recommended next step; not already deployed)

Since you currently use only the chat preview, there is no existing hosting-platform environment panel to configure. Render is one supported deployment path; using it is optional. The exact setup below is based on Render's official Flask and environment-variable documentation.

1. Extract the download. Put **the contents of this project folder** at the root of a new private GitHub repository. Do not commit your real key or any .env file. If you upload the enclosing folder instead, set Render's Root Directory to `verihire-tinyfish` for manual Web Service creation.
2. In Render Dashboard, choose **New > Web Service** and connect the repository. This must be a Web Service, not a Static Site.
3. Select Python 3. Set Build Command to `pip install -r requirements.txt`.
4. Set Start Command to `gunicorn --workers 1 --threads 4 --timeout 40 --bind 0.0.0.0:$PORT app:app`.
5. Set Health Check Path to `/health`.
6. In the service's **Environment** pane, under **Environment Variables**, click **+ Add Environment Variable**. Add **Key** `TINYFISH_API_KEY` and put your real TinyFish key in its private **Value** field. Never put it into a build command or frontend file.
7. Add `SITE_ACCESS_TOKEN` with a long random password. Enter this password (NOT the TinyFish key) in the existing site access password field when testing. This is a pilot access gate, not full user authentication.
8. Select **Save, rebuild, and deploy** when changing environment settings. A Save only action does not restart the existing service with the new values.
9. Open the HTTPS URL Render provides. The backend automatically uses Render's `RENDER_EXTERNAL_URL` for the allowed origin. If you use your own domain, add `PUBLIC_ORIGIN` with that exact HTTPS origin and redeploy; then open that domain consistently.

Alternatively, the supplied Blueprint configuration can provision the same service if the project contents are at the repository root. It prompts for TINYFISH_API_KEY and generates SITE_ACCESS_TOKEN privately. Retrieve that generated SITE_ACCESS_TOKEN from the service's Environment settings for the existing website password field.

Official hosting sources:
- https://render.com/docs/deploy-flask
- https://render.com/docs/configure-environment-variables
- https://render.com/docs/environment-variables
- https://render.com/docs/blueprint-spec

## 5. Other Python hosting

Deploy the whole folder on a Python-capable host, not a static-only host. Configure these secrets/environment variables in its private settings:

- TINYFISH_API_KEY: your actual TinyFish API key.
- PUBLIC_ORIGIN: the exact public HTTPS origin, e.g. https://verihire.example (no path).
- SITE_ACCESS_TOKEN: a long random password to restrict searches while testing. Visitors enter this in the site access password field; it is never stored by the app.

Production start command on Linux:

```bash
gunicorn --workers 1 --threads 4 --timeout 40 --bind 0.0.0.0:$PORT app:app
```

Set PORT=8000 if your host does not supply it. Use HTTPS through your hosting provider. Never use Flask's development server for public deployment.

The in-memory limits are 5 searches/minute per observed IP, 20/minute overall, and 3 simultaneous provider requests. Use exactly one worker and one instance for these limits. Behind a reverse proxy, users may share a single observed IP, making the limit stricter; arbitrary forwarded-IP headers are deliberately not trusted. Before removing the site password, exposing this publicly, or adding instances, add real user authentication, trusted-proxy configuration, shared Redis rate limits, host-level quotas, abuse protection and spending alerts/limits if available. The included password is a simple pilot gate, not full account authentication. Rate limits alone do not prevent API cost abuse.

The app returns only the intended public page and script; it does not expose the project directory or secrets. It does not log request bodies or query terms. Review your hosting provider's own logging and data-retention policies. No email content is sent to TinyFish. Company/domain query terms are sent to TinyFish and are subject to its policies.

## 6. Official API contract

Source: https://docs.tinyfish.ai/search-api/reference
Authentication: https://docs.tinyfish.ai/authentication

- GET https://api.search.tinyfish.ai
- Header: X-API-Key (server-side environment secret)
- Parameters: query, purpose, location=US, language=en
- TinyFish Search uses URL query parameters and **no JSON request body**. The browser-to-VeriHire call is a separate POST with JSON company/domain fields; do not confuse it with the provider API. Do not substitute the Agent run endpoint for Search.
- Response: results[] with title, snippet, url, site_name, optional date
- One upstream search per consented analysis. No automatic retries or caching.
- Handles missing configuration, upstream authentication failures, allowance/credit failures, rate limits, unexpected responses and timeouts without exposing provider response bodies or keys.

## 7. What the report means

The original rule-based score and styling are preserved. Search results appear separately with clickable sources, snippets, and the actual search query. The backend never visits links from the email; only the fixed TinyFish endpoint is requested. Search results and snippets are untrusted and rendered as text, with HTTP(S)-only source links.

Search results are not verification, not an automated fraud verdict, and do not change the numeric score. No search result is treated as evidence sufficient to lower risk. Verified remains explicitly self-reported based on all three independent checks, and suspicious local signals override that label. Missing results or a failed search never imply safety. The provider searches the web; the integration does not read full result pages, check domain ownership, validate sender authentication, scan attachments or authenticate offers.

## 8. Deploy-and-test checklist

1. Open `/health` on the deployed website. Expect only `{"status":"ok"}`. This checks the server is running, not that the API key works.
2. On the website, paste an internship email and enter the company name. Enable web research; enter the site access password if configured; click Analyze Email.
3. Confirm the local risk score appears immediately. Real TinyFish source links and snippets should then appear in the existing Web Research section. No results should show an explicit empty-result message, not fabricated sources.
4. In browser developer tools, inspect the POST to `/api/research`: the request contains company/domain and optionally the site access password. It must not contain the email body, full sender email address or TinyFish API key. The response must contain only research data or a safe error.
5. On a private/staging deployment, temporarily remove TINYFISH_API_KEY and redeploy. Expect a clear missing-configuration error and a working local score. Restore the key and redeploy.
6. In staging, test an intentionally invalid API key. Expect a TinyFish authentication error, never the key or raw provider error body. Restore the valid key. Do not perform destructive tests on a live production deployment.
7. Use browser developer tools to block `/api/research` and submit another email. The local score must still work and a network error should appear in Web Research. Unblock the route and retry. Automated tests cover timeouts without needing to break the live service.

Troubleshooting:
- Backend unreachable / non-JSON page: use the deployed web-service URL, not the HTML preview or a static host.
- Missing configuration: add TINYFISH_API_KEY to the backend Environment settings and redeploy.
- Authentication failed: replace the backend API key with a valid TinyFish key and redeploy.
- Site password error: enter SITE_ACCESS_TOKEN in the website, NOT TINYFISH_API_KEY.
- Origin not allowed: open the assigned Render URL or set PUBLIC_ORIGIN to the exact custom origin and redeploy.
- Timeout: local results remain; retry the research later. No fake or cached research is substituted.
- Allowance/credits or rate limit: wait or check the TinyFish account; no automatic repeated billable retries occur.

## 9. Automated tests

```bash
python -m unittest -v test_app.py
```

Optional browser regression tests require Playwright/Chromium (test dependencies only):

```bash
pip install playwright
python -m playwright install chromium
python test_browser.py
```

Automated tests use mocked TinyFish responses or intercepted research requests to test application behavior without making real API calls. These test fixtures are used only during testing and are not used as production fallbacks.

The Flask backend is deployed on Render, and the `/health` endpoint confirms that the service is running. Real TinyFish research requires a valid API key, an enabled TinyFish account, and a successful API request. The live research feature should be tested separately to confirm that real search results are returned.
