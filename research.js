(() => {
  const form = document.getElementById('scan-form');
  let generation = 0;
  let activeController = null;
  const button = document.getElementById('scan-btn');
  const originalButton = button.innerHTML;
  const unavailable = 'Web research cannot reach the backend. The chat/HTML preview cannot run the Python server. Open the deployed VeriHire web service or start the included server locally. Your local analysis is still available.';
  function restoreButton() {
    button.disabled = false;
    button.innerHTML = originalButton;
  }
  function textNode(tag, text, cls) {
    const el = document.createElement(tag); el.textContent = text;
    if (cls) el.className = cls; return el;
  }
  form.addEventListener('submit', async () => {
    if (document.getElementById('error').textContent) return;
    const id = ++generation;
    if (activeController) activeController.abort();
    activeController = null;
    restoreButton();
    const report = document.getElementById('report');
    const section = document.createElement('section'); section.className = 'research-card';
    section.append(textNode('h3', '03  Web research · TinyFish'));
    report.append(section);
    if (!document.getElementById('research-consent').checked) {
      section.append(textNode('p', 'Web research is off. Enable the consent option to search for the employer. Your local screening is shown above.')); return;
    }
    const company = document.getElementById('company').value.trim();
    const address = document.getElementById('sender').value.trim();
    const domain = address.includes('@') ? address.split('@').pop().toLowerCase() : '';
    const publicProvider = /^(gmail|yahoo|outlook|hotmail|protonmail|aol)\./i.test(domain);
    const payload = {company, domain: publicProvider ? '' : domain};
    if (!payload.company && !payload.domain) {
      section.append(textNode('p', 'Enter an employer name or a non-public sender domain to research. The local risk score is unchanged.')); return;
    }
    const queryPreview = textNode('p', 'Research subject: ' + [payload.company, payload.domain].filter(Boolean).join(' · '));
    section.append(queryPreview);
    const state = textNode('p', 'Searching public web sources…', 'research-state'); section.append(state);
    button.disabled = true;
    button.textContent = 'Researching…';
    const controller = new AbortController();
    activeController = controller;
    const timer = setTimeout(() => controller.abort(), 25000);
    try {
      if (!['http:', 'https:'].includes(window.location.protocol)) throw new Error(unavailable);
      const token = document.getElementById('access-token').value;
      const response = await fetch('/api/research', {
        method: 'POST', headers: {'Content-Type':'application/json', ...(token ? {'Authorization':'Bearer ' + token} : {})},
        body: JSON.stringify(payload), signal: controller.signal, credentials: 'same-origin'
      });
      if (!response.headers.get('content-type')?.includes('application/json')) {
        if ([502, 503, 504].includes(response.status)) {
          throw new Error('The backend is starting up or unavailable. Wait a moment and try again. Your local analysis is still available.');
        }
        throw new Error(unavailable);
      }
      let data;
      try { data = await response.json(); }
      catch { throw new Error('The backend returned invalid JSON. Please retry or ask the site owner to check the server. Your local analysis is still available.'); }
      if (!response.ok) throw new Error(typeof data?.error === 'string' ? data.error : 'Web research request failed (HTTP ' + response.status + '). Your local analysis is still available.');
      if (!data || !Array.isArray(data.results) || typeof data.query !== 'string') {
        throw new Error('The backend returned an unexpected research response. No research results were displayed. Your local analysis is still available.');
      }
      if (generation !== id) return;
      let displayed = 0;
      section.append(textNode('p', 'Search: ' + data.query));
      data.results.forEach(source => {
        if (!source || typeof source.url !== 'string') return;
        let url; try { url = new URL(source.url); } catch { return; }
        if (!['https:', 'http:'].includes(url.protocol) || url.username || url.password) return;
        const item = document.createElement('div'); item.className = 'research-source';
        const a = textNode('a', source.title || url.hostname); a.href = url.href;
        a.target = '_blank'; a.rel = 'noopener noreferrer'; item.append(a);
        item.append(textNode('p', [source.site_name || url.hostname, source.date].filter(Boolean).join(' · ')));
        if (source.snippet) item.append(textNode('p', source.snippet));
        section.append(item);
        displayed++;
      });
      state.textContent = displayed ? 'Public search results — review the sources yourself.' : 'No usable search results returned. No results does not mean the employer is safe or fraudulent.';
      section.append(textNode('p', 'Search snippets are unverified third-party content. A matching name, search ranking, or lack of scam reports does not authenticate an offer. Results do not automatically change the risk score or mark an employer Verified. Never enter credentials or pay fees through untrusted links.'));
    } catch (err) {
      if (generation === id) {
        state.textContent = err.name === 'AbortError'
          ? 'Web research timed out after 25 seconds. Your local report is still available. Try again.'
          : err instanceof TypeError
            ? 'Network request failed. Check your internet connection and that the Python backend is running. Your local report is still available.'
            : err.message;
      }
    } finally {
      clearTimeout(timer);
      if (generation === id) { activeController = null; restoreButton(); }
    }
  });
})();
