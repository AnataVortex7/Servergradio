import os
import sys
import subprocess
import asyncio
import urllib.parse
import uuid

# ==========================================
# Auto-Install Missing Dependencies
# ==========================================
try:
    import aiohttp
    from aiohttp import web
    from playwright.async_api import async_playwright
except ImportError as e:
    import os
    if os.environ.get("INSTALL_RETRY") == "1":
        print(f"❌ वारंवार इन्स्टॉलेशन फेल होत आहे. कृपया मॅन्युअली चेक करा. Error: {e}")
        sys.exit(1)
        
    print(f"⏳ काही आवश्यक packages मिळत नाहीत. (Error: {e})\nइन्स्टॉल करत आहे...")
    subprocess.check_call([sys.executable, "-m", "pip", "install", "aiohttp", "playwright", "playwright-stealth"])
    print("⏳ Browser binaries डाऊनलोड करत आहे (हे फक्त एकदाच होईल)...")
    subprocess.check_call([sys.executable, "-m", "playwright", "install", "chromium"])
    print("⏳ OS dependencies इन्स्टॉल करत आहे (विशेषतः Linux साठी)...")
    subprocess.check_call([sys.executable, "-m", "playwright", "install-deps", "chromium"])
    print("✅ इन्स्टॉलेशन पूर्ण झाले. स्क्रिप्ट पुन्हा चालू करत आहे...\n")
    os.environ["INSTALL_RETRY"] = "1"
    os.execv(sys.executable, [sys.executable] + sys.argv)

try:
    from playwright_stealth import stealth_async
    HAS_STEALTH = True
except ImportError:
    HAS_STEALTH = False
    print("⚠️ Warning: 'playwright-stealth' module not found. Advanced bot protection is disabled.")


# ==========================================
# Main Script Logic (Multi-Tab)
# ==========================================
browser = None
tabs = {}  # { tab_id: {"page": Page, "context": Context, "url": str, "title": str} }

async def dashboard(request):
    """Main dashboard to list all active background tabs and add new ones."""
    tabs_html = ""
    for tab_id, tab_info in tabs.items():
        title = tab_info.get("title", "Loading...")
        url = tab_info.get("url", "")
        tabs_html += f"""
        <div class="tab-card">
            <h3>{title}</h3>
            <p><small>{url}</small></p>
            <a class="btn" href="/view/{tab_id}">👁️ View Live</a>
            <a class="btn btn-danger" href="/close/{tab_id}" onclick="return confirm('Close this tab?');">❌ Close</a>
        </div>
        """
        
    if not tabs_html:
        tabs_html = "<p style='color: #aaa;'>No sites running. Add one below!</p>"
        
    html = f"""
    <html>
    <head>
        <title>Multi-Tab Live Proxy Dashboard</title>
        <style>
            body {{ background: #1a1a1a; color: white; font-family: sans-serif; padding: 20px; }}
            .header {{ text-align: center; margin-bottom: 30px; }}
            .container {{ max-width: 900px; margin: 0 auto; }}
            .add-box {{ background: #2a2a2a; padding: 20px; border-radius: 8px; margin-bottom: 30px; }}
            input[type="text"] {{ width: 70%; padding: 10px; border-radius: 4px; border: 1px solid #444; background: #111; color: white; }}
            button {{ padding: 10px 20px; border: none; background: #28a745; color: white; border-radius: 4px; cursor: pointer; font-weight: bold; }}
            button:hover {{ background: #218838; }}
            .tabs-grid {{ display: grid; grid-template-columns: repeat(auto-fill, minmax(250px, 1fr)); gap: 15px; }}
            .tab-card {{ background: #333; padding: 15px; border-radius: 8px; border-left: 5px solid #007bff; }}
            .tab-card h3 {{ margin-top: 0; font-size: 16px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }}
            .btn {{ display: inline-block; background: #007bff; color: white; text-decoration: none; padding: 6px 12px; border-radius: 4px; font-size: 14px; margin-right: 5px; }}
            .btn:hover {{ background: #0056b3; }}
            .btn-danger {{ background: #dc3545; }}
            .btn-danger:hover {{ background: #c82333; }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>🌐 Multi-Tab Background Proxy</h1>
                <p>Run multiple graphical websites securely in the background.</p>
            </div>
            
            <div class="add-box">
                <form action="/add" method="POST">
                    <label><strong>Add New Site:</strong></label><br><br>
                    <input type="text" name="url" placeholder="https://example.com (or https://user:pass@example.com)" required />
                    <button type="submit">➕ Launch Background Tab</button>
                </form>
            </div>
            
            <h2>Active Tabs</h2>
            <div class="tabs-grid">
                {tabs_html}
            </div>
        </div>
    </body>
    </html>
    """
    return web.Response(text=html, content_type='text/html')

async def add_tab(request):
    global browser
    data = await request.post()
    raw_url = data.get('url', '').strip()
    
    if not raw_url:
        return web.Response(text="Invalid URL", status=400)
    if not raw_url.startswith('http'):
        raw_url = 'https://' + raw_url
        
    tab_id = str(uuid.uuid4())[:8]
    parsed_url = urllib.parse.urlparse(raw_url)
    display_url = raw_url
    
    # Create isolated context
    context_options = {
        'viewport': {'width': 1280, 'height': 720},
        'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    }
    
    if parsed_url.username and parsed_url.password:
        context_options['http_credentials'] = {
            'username': urllib.parse.unquote(parsed_url.username),
            'password': urllib.parse.unquote(parsed_url.password)
        }
        display_url = parsed_url._replace(netloc=parsed_url.hostname + (f":{parsed_url.port}" if parsed_url.port else "")).geturl()
    
    tab_context = await browser.new_context(**context_options)
    await tab_context.add_init_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
    
    page = await tab_context.new_page()
    if HAS_STEALTH:
        await stealth_async(page)
        
    await page.set_extra_http_headers({
        'Accept-Language': 'en-US,en;q=0.9',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8'
    })
    
    tabs[tab_id] = {"page": page, "context": tab_context, "url": display_url, "title": "Loading..."}
    
    # Trigger load in background
    asyncio.create_task(load_page_bg(tab_id, display_url))
    
    raise web.HTTPFound('/')

async def load_page_bg(tab_id, url):
    page = tabs[tab_id]["page"]
    try:
        await page.goto(url, wait_until='load', timeout=60000)
        tabs[tab_id]["title"] = await page.title()
    except Exception as e:
        print(f"[Tab {tab_id}] Load warning: {e}")
        try:
            tabs[tab_id]["title"] = await page.title() or "Loaded (with warnings)"
        except:
            tabs[tab_id]["title"] = "Error Loading"

async def close_tab(request):
    tab_id = request.match_info['id']
    if tab_id in tabs:
        page = tabs[tab_id]["page"]
        tab_context = tabs[tab_id]["context"]
        await page.close()
        await tab_context.close()
        del tabs[tab_id]
    raise web.HTTPFound('/')

async def view_tab(request):
    tab_id = request.match_info['id']
    if tab_id not in tabs:
        return web.Response(text="Tab not found", status=404)
        
    html = f"""
    <html>
    <head>
        <title>Live Tab: {tab_id}</title>
        <meta name="viewport" content="width=device-width, initial-scale=1, maximum-scale=5.0, user-scalable=yes">
        <style>
            body {{ margin: 0; padding: 0; background: #222; color: white; font-family: sans-serif; text-align: center; overflow: hidden; }}
            .container {{ display: flex; flex-direction: column; height: 100vh; overflow: hidden; }}
            .toolbar {{ background: #111; padding: 5px; display: flex; justify-content: center; gap: 8px; align-items: center; flex-wrap: wrap; }}
            .stream-container {{ flex: 1; display: flex; justify-content: center; align-items: flex-start; overflow: auto; background: #000; }}
            img {{ max-width: 100%; height: auto; box-shadow: 0 0 10px rgba(0,0,0,0.5); cursor: crosshair; }}
            a.btn, button.btn {{ background: #007bff; color: white; text-decoration: none; padding: 6px 12px; border-radius: 4px; font-weight: bold; border: none; cursor: pointer; font-size: 13px; }}
            a.btn:hover, button.btn:hover {{ background: #0056b3; }}
            a.btn-back {{ background: #6c757d; }}
            .status {{ color: #4CAF50; font-weight: bold; font-size: 13px; }}
            .virtual-kbd {{ background: #1a1a1a; padding: 6px; display: flex; flex-wrap: wrap; justify-content: center; gap: 4px; border-bottom: 2px solid #333; }}
            .virtual-kbd button {{ background: #444; color: white; border: none; padding: 8px 10px; border-radius: 4px; font-weight: bold; cursor: pointer; font-size: 12px; }}
            .virtual-kbd button:active {{ background: #666; }}
            .mod-btn {{ background: #444; }}
        </style>
        <script>
            let modifiers = {{ 'Control': false, 'Alt': false, 'Shift': false }};

            function toggleMod(mod, btn) {{
                modifiers[mod] = !modifiers[mod];
                btn.style.backgroundColor = modifiers[mod] ? '#dc3545' : '#444';
            }}

            function sendKey(key) {{
                let parts = [];
                if (modifiers['Control']) parts.push('Control');
                if (modifiers['Alt']) parts.push('Alt');
                if (modifiers['Shift']) parts.push('Shift');
                parts.push(key);
                
                fetch('/key/{tab_id}?k=' + encodeURIComponent(parts.join('+')));
                
                // Reset modifiers after sending
                modifiers = {{ 'Control': false, 'Alt': false, 'Shift': false }};
                document.querySelectorAll('.mod-btn').forEach(b => b.style.backgroundColor = '#444');
            }}

            function onClick(event) {{
                openKeyboard();
                const img = event.target;
                const rect = img.getBoundingClientRect();
                const scaleX = 1280 / rect.width;
                const scaleY = 720 / rect.height;
                const x = (event.clientX - rect.left) * scaleX;
                const y = (event.clientY - rect.top) * scaleY;
                fetch('/click/{tab_id}?x=' + Math.round(x) + '&y=' + Math.round(y));
            }}
            
            function onKeyDown(event) {{
                if (event.repeat) return;
                
                let key = event.key;
                if (key === 'Enter') key = 'Enter';
                else if (key === 'Backspace') key = 'Backspace';
                else if (key === 'Escape') key = 'Escape';
                else if (key === 'Tab') key = 'Tab';
                
                sendKey(key);
                if(key !== 'F5' && key !== 'F12') event.preventDefault();
            }}
            
            function openKeyboard() {{
                const input = document.getElementById('hidden-input');
                input.focus();
            }}
            
            function promptPaste() {{
                let text = prompt("Paste your text here to send it to the terminal:");
                if (text !== null && text !== "") {{
                    fetch('/paste/{tab_id}', {{
                        method: 'POST',
                        body: text
                    }});
                }}
            }}
            
            function onInput(event) {{
                const val = event.data;
                if (val) {{
                    sendKey(val);
                }}
                document.getElementById('hidden-input').value = '';
            }}
            
            document.addEventListener('DOMContentLoaded', () => {{
                document.addEventListener('keydown', onKeyDown);
            }});
        </script>
    </head>
    <body>
        <input type="text" id="hidden-input" style="opacity:0; position:absolute; top:-1000px;" oninput="onInput(event)" autocomplete="off" autocorrect="off" autocapitalize="off" spellcheck="false" />
        <div class="container">
            <div class="toolbar">
                <a class="btn btn-back" href="/">⬅️ Back</a>
                <span class="status">🔴 LIVE</span>
                <button class="btn" style="background:#28a745;" onclick="openKeyboard()">⌨️ Type</button>
                <button class="btn" style="background:#17a2b8;" onclick="promptPaste()">📋 Paste</button>
                <a class="btn" href="/refresh/{tab_id}" onclick="return confirm('Refresh this tab?');">🔄 Refresh</a>
            </div>
            <div class="virtual-kbd">
                <button class="mod-btn" onclick="toggleMod('Control', this)">Ctrl</button>
                <button class="mod-btn" onclick="toggleMod('Alt', this)">Alt</button>
                <button class="mod-btn" onclick="toggleMod('Shift', this)">Shift</button>
                <button onclick="sendKey('Escape')">Esc</button>
                <button onclick="sendKey('Tab')">Tab</button>
                <button onclick="sendKey('ArrowUp')">⬆</button>
                <button onclick="sendKey('ArrowDown')">⬇</button>
                <button onclick="sendKey('ArrowLeft')">⬅</button>
                <button onclick="sendKey('ArrowRight')">➡</button>
                <button onclick="sendKey('Enter')">Enter ↵</button>
                <button onclick="sendKey('Backspace')">⌫ Back</button>
            </div>
            <div class="stream-container">
                <img src="/stream/{tab_id}" onclick="onClick(event)" alt="Live Stream" />
            </div>
        </div>
    </body>
    </html>
    """
    return web.Response(text=html, content_type='text/html')

async def stream(request):
    tab_id = request.match_info['id']
    if tab_id not in tabs:
        return web.Response(text="Not found", status=404)
        
    page = tabs[tab_id]["page"]
    response = web.StreamResponse(status=200, reason='OK', headers={'Content-Type': 'multipart/x-mixed-replace; boundary=frame'})
    await response.prepare(request)
    
    try:
        while True:
            if page and not page.is_closed():
                try:
                    screenshot = await page.screenshot(type='jpeg', quality=20, timeout=2000)
                    await response.write(
                        b'--frame\r\n'
                        b'Content-Type: image/jpeg\r\n\r\n' + screenshot + b'\r\n'
                    )
                except Exception as e:
                    pass # Ignore screenshot timeouts to keep stream alive
            await asyncio.sleep(14)
    except asyncio.CancelledError:
        pass
    except ConnectionResetError:
        pass
    except Exception as e:
        if "Cannot write to closing transport" not in str(e):
            print(f"[Tab {tab_id}] Stream error: {e}")
            
    return response

async def click_handler(request):
    tab_id = request.match_info['id']
    if tab_id in tabs:
        x = int(request.query.get('x', 0))
        y = int(request.query.get('y', 0))
        page = tabs[tab_id]["page"]
        if not page.is_closed():
            await page.mouse.click(x, y)
    return web.Response(text="Clicked")

async def key_handler(request):
    tab_id = request.match_info['id']
    if tab_id in tabs:
        key = request.query.get('k', '')
        page = tabs[tab_id]["page"]
        if not page.is_closed() and key:
            try:
                await page.keyboard.press(key)
            except Exception as e:
                print(f"[Tab {tab_id}] Key press error: {e}")
    return web.Response(text="Key pressed")

async def paste_handler(request):
    tab_id = request.match_info['id']
    if tab_id in tabs:
        text = await request.text()
        page = tabs[tab_id]["page"]
        if not page.is_closed() and text:
            try:
                await page.keyboard.insert_text(text)
            except Exception as e:
                print(f"[Tab {tab_id}] Paste error: {e}")
    return web.Response(text="Pasted")

async def refresh_tab(request):
    tab_id = request.match_info['id']
    if tab_id in tabs:
        page = tabs[tab_id]["page"]
        if not page.is_closed():
            print(f"Refreshing tab {tab_id}...")
            await page.reload()
    return web.Response(text=f"<script>window.location.href='/view/{tab_id}';</script>", content_type='text/html')

async def run_server():
    app = web.Application()
    app.add_routes([
        web.get('/', dashboard),
        web.post('/add', add_tab),
        web.get('/view/{id}', view_tab),
        web.get('/stream/{id}', stream),
        web.get('/click/{id}', click_handler),
        web.get('/key/{id}', key_handler),
        web.post('/paste/{id}', paste_handler),
        web.get('/refresh/{id}', refresh_tab),
        web.get('/close/{id}', close_tab)
    ])
    
    runner = web.AppRunner(app)
    await runner.setup()
    port = 8080
    while port < 8090:
        try:
            site = web.TCPSite(runner, '0.0.0.0', port)
            await site.start()
            print(f"✅ Multi-Tab Live Proxy ready at: http://localhost:{port}")
            break
        except OSError:
            port += 1
    else:
        print("❌ All ports from 8080 to 8089 are busy. Could not start server.")
        sys.exit(1)

async def main():
    global browser
    print("="*60)
    print("🌐 MULTI-TAB BACKGROUND BROWSER SCRIPT")
    print("="*60)
    
    print("\n⏳ Starting background headless browser Engine... (Please wait)")
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True, args=[
            '--disable-blink-features=AutomationControlled',
            '--remote-debugging-port=9222',
            '--remote-debugging-address=0.0.0.0'
        ])
        
        print("\n🎉 SUCCESS! Engine is running.")
        print("="*60)
        print(f"👉 Open http://localhost:8080 in your real browser to access the Dashboard!")
        print("="*60)
        print("Press Ctrl+C in this terminal to completely close the engine.")
        
        await run_server()
        
        while True:
            await asyncio.sleep(3600)

if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nExiting and closing all background tabs...")
