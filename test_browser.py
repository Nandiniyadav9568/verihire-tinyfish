"""Browser-only regression fixtures. Never imported or served by the application."""
import asyncio
import json
import os
import threading
from unittest.mock import patch

from playwright.async_api import async_playwright, expect
from werkzeug.serving import make_server
import app as module


async def main():
    # Real local Flask server, no real API key and no live TinyFish calls.
    module.PUBLIC_ORIGIN = ''
    module.SITE_ACCESS_TOKEN = ''
    server = make_server('127.0.0.1', 0, module.app, threaded=True)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    url = f'http://127.0.0.1:{server.server_port}'
    passed = []
    try:
        async with async_playwright() as pw:
            browser = await pw.chromium.launch(headless=True, args=['--no-sandbox'])
            page = await browser.new_page(viewport={'width': 1280, 'height': 900})
            js_errors = []
            page.on('pageerror', lambda error: js_errors.append(str(error)))

            async def reset(consent=True):
                await page.unroute_all(behavior='ignoreErrors')
                await page.goto(url, wait_until='domcontentloaded')
                await page.locator('#sample').click()
                await page.locator('#company').fill('Example Employer')
                if consent:
                    await page.locator('#research-consent').check()

            async def submit():
                await page.locator('#scan-btn').click()
                await expect(page.locator('.score-num')).to_have_text('100')

            async def finished():
                await expect(page.locator('#scan-btn')).to_be_enabled()
                await expect(page.locator('#scan-btn')).to_contain_text('Analyze email')

            await reset()
            await submit()
            await expect(page.locator('.research-state')).to_contain_text('TINYFISH_API_KEY')
            await finished()
            passed.append('Actual server missing-key error preserves local score')

            await reset(consent=False)
            await submit()
            await expect(page.locator('.research-card')).to_contain_text('Web research is off')
            await finished()
            passed.append('Consent-off local analysis remains unchanged')

            async def success(route):
                body = route.request.post_data_json
                assert body == {'company': 'Example Employer', 'domain': ''}
                await route.fulfill(status=200, content_type='application/json', body=json.dumps({
                    'query': 'Example Employer recruitment',
                    'results': [{'title': 'TEST FIXTURE — not live research',
                                 'url': 'https://example.com/careers',
                                 'snippet': '<script>never execute third-party text</script>',
                                 'site_name': 'example.com'}]
                }))

            await reset()
            await page.route('**/api/research', success)
            await submit()
            await expect(page.locator('.research-source a')).to_have_text('TEST FIXTURE — not live research')
            await expect(page.locator('.research-source')).to_contain_text('<script>')
            assert await page.locator('.research-source script').count() == 0
            await finished()
            passed.append('Successful results render as safe text in existing research section')

            async def html_error(route):
                await route.fulfill(status=404, content_type='text/html', body='<h1>Not Found</h1>')
            await reset()
            await page.route('**/api/research', html_error)
            await submit()
            await expect(page.locator('.research-state')).to_contain_text('chat/HTML preview')
            await finished()
            passed.append('Missing backend or HTML route produces actionable error')

            async def malformed(route):
                await route.fulfill(status=200, content_type='application/json', body='{"broken":true}')
            await reset()
            await page.route('**/api/research', malformed)
            await submit()
            await expect(page.locator('.research-state')).to_contain_text('unexpected research response')
            assert await page.locator('.research-source').count() == 0
            await finished()
            passed.append('Malformed success never fabricates research')

            async def invalid_json(route):
                await route.fulfill(status=200, content_type='application/json', body='{')
            await reset()
            await page.route('**/api/research', invalid_json)
            await submit()
            await expect(page.locator('.research-state')).to_contain_text('invalid JSON')
            await finished()
            passed.append('Invalid JSON produces clear error and restores button')

            async def auth_error(route):
                await route.fulfill(status=502, content_type='application/json', body=json.dumps({
                    'error':'TinyFish authentication failed. Check the server-side TINYFISH_API_KEY.'}))
            await reset()
            await page.route('**/api/research', auth_error)
            await submit()
            await expect(page.locator('.research-state')).to_contain_text('authentication failed')
            await finished()
            passed.append('Provider authentication error remains visible beside local report')

            async def network_error(route):
                await route.abort('failed')
            await reset()
            await page.route('**/api/research', network_error)
            await submit()
            await expect(page.locator('.research-state')).to_contain_text('Network request failed')
            await finished()
            passed.append('Network failure preserves local analysis')

            await reset()
            await page.clock.install()
            waiting = asyncio.Event()
            async def timeout_route(route):
                await waiting.wait()
                try: await route.abort('failed')
                except Exception: pass
            await page.route('**/api/research', timeout_route)
            await submit()
            await expect(page.locator('.research-state')).to_contain_text('Searching')
            await page.clock.fast_forward(26000)
            await expect(page.locator('.research-state')).to_contain_text('timed out after 25 seconds')
            await finished()
            waiting.set()
            passed.append('Timeout restores button and keeps local score')

            await reset()
            pending = asyncio.Event()
            async def held_success(route):
                await pending.wait()
                try:
                    await route.fulfill(status=200, content_type='application/json', body='{"query":"test","results":[]}')
                except Exception: pass
            await page.route('**/api/research', held_success)
            await submit()
            await expect(page.locator('#scan-btn')).to_be_disabled()
            # An invalid programmatic submission used to invalidate the active cleanup.
            await page.locator('#email').fill('Too short')
            await page.locator('#scan-form').dispatch_event('submit')
            await expect(page.locator('#error')).to_contain_text('at least 40')
            pending.set()
            await finished()
            passed.append('Invalid overlapping submission no longer strands disabled button')

            await reset()
            cancelled = asyncio.Event()
            async def held_cancelled(route):
                await cancelled.wait()
                try: await route.abort('failed')
                except Exception: pass
            await page.route('**/api/research', held_cancelled)
            await submit()
            await expect(page.locator('#scan-btn')).to_be_disabled()
            await page.locator('#research-consent').uncheck()
            await page.locator('#scan-form').dispatch_event('submit')
            await expect(page.locator('.research-card')).to_contain_text('Web research is off')
            await finished()
            cancelled.set()
            passed.append('New consent-off analysis cancels stale research and resets button')

            assert not js_errors, js_errors
            await browser.close()
    finally:
        server.shutdown()
    for finding in passed:
        print('PASS:', finding)
    print(f'{len(passed)} browser regression checks passed. Provider responses were test fixtures, not live research.')


if __name__ == '__main__':
    with patch.dict(os.environ, {'TINYFISH_API_KEY': ''}):
        asyncio.run(main())
