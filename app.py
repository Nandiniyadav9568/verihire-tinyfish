"""VeriHire same-origin TinyFish search proxy. No email content is accepted."""
import hmac
import os
import re
import threading
import time
from collections import defaultdict, deque
from urllib.parse import urlsplit
import requests
from flask import Flask, request, jsonify, send_from_directory

app = Flask(__name__, static_folder=None)
app.config['MAX_CONTENT_LENGTH'] = 2048
ROOT = os.path.dirname(os.path.abspath(__file__))
API_URL = 'https://api.search.tinyfish.ai'
PUBLIC_ORIGIN = os.environ.get('PUBLIC_ORIGIN', '').rstrip('/')
SITE_ACCESS_TOKEN = os.environ.get('SITE_ACCESS_TOKEN', '')
if not PUBLIC_ORIGIN and os.environ.get('RENDER_EXTERNAL_URL'):
    PUBLIC_ORIGIN = os.environ['RENDER_EXTERNAL_URL'].rstrip('/')
lock = threading.Lock()
recent = defaultdict(deque)
global_recent = deque()
inflight = threading.BoundedSemaphore(3)

@app.after_request
def headers(response):
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['X-Frame-Options'] = 'DENY'
    response.headers['Referrer-Policy'] = 'no-referrer'
    response.headers['Permissions-Policy'] = 'camera=(), microphone=(), geolocation=()'
    response.headers['Cache-Control'] = 'no-store'
    # Existing page uses inline styling/scripts; no third-party script execution is allowed.
    response.headers['Content-Security-Policy'] = "default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; font-src https://fonts.gstatic.com; connect-src 'self'; img-src 'self' data:; object-src 'none'; base-uri 'none'; frame-ancestors 'none'; form-action 'self'"
    if PUBLIC_ORIGIN.startswith('https://'):
        response.headers['Strict-Transport-Security'] = 'max-age=31536000'
    return response

@app.get('/')
def index():
    return send_from_directory(ROOT, 'index.html')

@app.get('/research.js')
def research_js():
    return send_from_directory(ROOT, 'research.js')

@app.get('/health')
def health():
    # Liveness only: do not disclose configuration or call the paid API.
    return jsonify(status='ok')

@app.errorhandler(413)
def too_large(_):
    return jsonify(error='Request too large.'), 413

@app.post('/api/research')
def research():
    # No CORS. Match browser origin; production pins it with PUBLIC_ORIGIN.
    origin = request.headers.get('Origin', '')
    allowed_origin = PUBLIC_ORIGIN or request.host_url.rstrip('/')
    if origin != allowed_origin:
        return jsonify(error='Request origin not allowed.'), 403
    if SITE_ACCESS_TOKEN:
        supplied = request.headers.get('Authorization', '')
        if not hmac.compare_digest(supplied.encode('utf-8'), ('Bearer ' + SITE_ACCESS_TOKEN).encode('utf-8')):
            return jsonify(error='Enter the site access password supplied by the site owner.'), 401
    if not request.is_json:
        return jsonify(error='JSON required.'), 415
    data = request.get_json(silent=True)
    if not isinstance(data, dict) or set(data) - {'company', 'domain'}:
        return jsonify(error='Send only company and domain. Email content is not accepted.'), 400
    company, domain = data.get('company', ''), data.get('domain', '')
    if not isinstance(company, str) or not isinstance(domain, str):
        return jsonify(error='Invalid search fields.'), 400
    company, domain = company.strip(), domain.strip().lower()
    # Restrict query syntax and prevent email addresses/full URLs from being submitted.
    if len(company) > 120 or (company and not re.fullmatch(r"[\w .&'’()\-]{2,120}", company, re.UNICODE)):
        return jsonify(error='Use a plain company name, not an email address, URL, or search operators.'), 400
    if domain and (len(domain) > 253 or not re.fullmatch(r'(?:[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.)+[a-z]{2,63}', domain)):
        return jsonify(error='Invalid sender domain.'), 400
    if not company and not domain:
        return jsonify(error='Enter an employer name or sender domain.'), 400
    key = os.environ.get('TINYFISH_API_KEY', '').strip()
    if not key:
        return jsonify(error='Web research is not configured. The site owner must add TINYFISH_API_KEY to the backend environment.'), 503
    now = time.monotonic()
    # Never trust arbitrary X-Forwarded-For values. Global limit also caps API spend.
    ip = request.remote_addr or 'unknown'
    with lock:
        for addr in list(recent):
            while recent[addr] and now - recent[addr][0] >= 60:
                recent[addr].popleft()
            if not recent[addr]: del recent[addr]
        while global_recent and now - global_recent[0] >= 60: global_recent.popleft()
        if len(global_recent) >= 20 or len(recent[ip]) >= 5:
            return jsonify(error='Too many searches. Wait a minute and try again.'), 429
        recent[ip].append(now); global_recent.append(now)
    query = ' '.join('"' + part + '"' for part in (company, domain) if part) + ' recruitment careers internship scam impersonation'
    if not inflight.acquire(blocking=False):
        return jsonify(error='Research is busy. Try again shortly.'), 429
    try:
        upstream = requests.get(API_URL,
            params={'query': query, 'purpose': 'Find public context about a claimed employer and hiring-related scam or impersonation reports. Search results do not authenticate an email.', 'location': 'US', 'language': 'en'},
            headers={'X-API-Key': key, 'Accept': 'application/json'}, timeout=(5, 15), allow_redirects=False)
        errors = {400: 'TinyFish rejected the research query. Check the employer name and retry.', 401: 'TinyFish authentication failed. The site owner must check or replace the server-side TINYFISH_API_KEY and redeploy.', 402: 'TinyFish allowance or credits are exhausted. Ask the site owner to check the account.', 403: 'TinyFish denied access. The site owner should check the API key permissions and account access.', 404: 'TinyFish Search is unavailable.', 429: 'TinyFish rate limit reached. Wait a minute and retry.'}
        if upstream.status_code != 200:
            code = 429 if upstream.status_code == 429 else 502
            return jsonify(error=errors.get(upstream.status_code, 'The search provider is temporarily unavailable.')), code
        payload = upstream.json()
        if not isinstance(payload, dict) or not isinstance(payload.get('results'), list):
            return jsonify(error='The search provider returned an unexpected response.'), 502
        results = []
        for row in payload['results'][:8]:
            if not isinstance(row, dict): continue
            url = row.get('url', '')
            if not isinstance(url, str) or len(url) > 4096: continue
            try:
                parsed = urlsplit(url)
                if parsed.scheme not in ('http', 'https') or not parsed.hostname or parsed.username or parsed.password: continue
            except ValueError: continue
            item = {k: str(row.get(k) or '')[:(2000 if k == 'snippet' else 500)] for k in ('title', 'snippet', 'site_name', 'date')}
            item['url'] = url; results.append(item)
        return jsonify(query=query, results=results, provider='TinyFish Search')
    except requests.Timeout:
        return jsonify(error='TinyFish timed out. Your local risk report is still available.'), 504
    except (requests.RequestException, ValueError):
        # Do not expose provider bodies, exceptions, request headers, or the secret.
        return jsonify(error='Could not retrieve web research. Please try again later.'), 502
    finally:
        inflight.release()

if __name__ == '__main__':
    app.run(host='127.0.0.1', port=int(os.environ.get('PORT', '8000')), debug=False)
