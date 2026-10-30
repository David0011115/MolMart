"""Быстрая проверка сайта. Запуск: python3 tests/smoke.py
Нужны: pip install playwright && playwright install chromium"""
import sys, threading, http.server, socketserver, functools, os
from playwright.sync_api import sync_playwright

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
class Quiet(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *a, **k): pass
H = functools.partial(Quiet, directory=ROOT)
srv = socketserver.TCPServer(("127.0.0.1", 0), H); PORT = srv.server_address[1]
threading.Thread(target=srv.serve_forever, daemon=True).start()
BASE = f"http://127.0.0.1:{PORT}/"
fails = []
def check(name, ok, info=""):
    print(("OK   " if ok else "FAIL ") + name + (f"  [{info}]" if info and not ok else ""))
    if not ok: fails.append(name)

with sync_playwright() as p:
    b = p.chromium.launch()
    for scheme in ("light", "dark"):
        c = b.new_context(viewport={"width": 390, "height": 800}, color_scheme=scheme, service_workers="block")
        pg = c.new_page(); errs = []
        pg.on("pageerror", lambda e: errs.append(str(e)))
        pg.goto(BASE + "index.html"); pg.wait_for_selector("#grid .card", timeout=8000)
        n = pg.locator("#grid .card").count()
        check(f"[{scheme}] каталог показывает товары", n > 0, n)
        check(f"[{scheme}] нет горизонтальной прокрутки", pg.evaluate("document.documentElement.scrollWidth<=innerWidth+1"))
        # поиск
        pg.fill("#q", "кимпаб"); pg.wait_for_timeout(400)
        m = pg.locator("#grid .card").count(); check(f"[{scheme}] поиск сужает список", 0 < m < n, (m, n))
        pg.fill("#q", "zzzzqqq"); pg.wait_for_timeout(400)
        check(f"[{scheme}] пустой поиск показывает «ничего не найдено»", not pg.eval_on_selector("#empty", "e=>e.hidden"))
        pg.fill("#q", ""); pg.wait_for_timeout(300)
        # карточка + избранное + кассир + сравнение
        pg.click("#grid .card >> nth=0"); pg.wait_for_selector("#dlg[open]")
        pg.click("#fav"); check(f"[{scheme}] избранное ставится", pg.get_attribute("#fav", "aria-pressed") == "true")
        pg.click("#cashone"); pg.wait_for_selector("#cash[open]")
        check(f"[{scheme}] кассир-экран показывает цену", "₸" in pg.inner_text("#cash") or "уточн" in pg.inner_text("#cash").lower())
        pg.click("#cashx"); pg.click("#cmpbtn"); pg.wait_for_selector("#cmp[open]")
        check(f"[{scheme}] сравнение открывается", pg.locator("#cmg .cmc").count() > 0)
        pg.click("#cmx"); pg.keyboard.press("Escape")
        pg.click('.chip[data-t="fav"]'); pg.wait_for_timeout(300)
        check(f"[{scheme}] кнопка «Показать кассиру» в избранном", not pg.eval_on_selector("#cashrow", "e=>e.hidden"))
        pg.click("#cashopen"); pg.wait_for_selector("#cash[open]"); pg.click("#cashx")
        # «Что взять?»
        pg.click("#pickopen"); pg.wait_for_selector("#pk[open]"); pg.keyboard.press("Escape")
        # тема
        before = pg.evaluate("document.documentElement.getAttribute('data-theme')")
        pg.click("#thbtn"); after = pg.evaluate("document.documentElement.getAttribute('data-theme')")
        check(f"[{scheme}] кнопка темы переключает тему", before != after, (before, after))
        # язык
        pg.click('.lb[data-l="kk"]'); pg.wait_for_timeout(300)
        check(f"[{scheme}] казахский язык включается", "Жабу" in pg.content() or "Таңдаулы" in pg.content())
        pg.click('.lb[data-l="ru"]')
        # нет сети
        c.set_offline(True); pg.wait_for_timeout(400)
        check(f"[{scheme}] баннер «Нет сети» появляется", not pg.eval_on_selector("#offline", "e=>e.hidden"))
        c.set_offline(False); pg.wait_for_timeout(1200)
        check(f"[{scheme}] баннер исчезает при возврате сети", pg.eval_on_selector("#offline", "e=>e.hidden"))
        check(f"[{scheme}] нет ошибок JavaScript", not errs, errs[:2])
        c.close()
    # срок жизни избранного
    c = b.new_context(viewport={"width": 390, "height": 800}, service_workers="block"); pg = c.new_page()
    pg.goto(BASE + "index.html"); pg.wait_for_selector("#grid .card")
    nm = pg.evaluate("PRODUCTS.filter(p=>!p.hidden).slice(0,2).map(p=>p.name)")
    for mins, want in ((5, 2), (11, 0)):
        pg.evaluate("([n,m])=>{localStorage.setItem('favs',JSON.stringify(n));localStorage.setItem('favsSeen',String(Date.now()-m*60000))}", [nm, mins])
        p2 = c.new_page(); p2.goto(BASE + "index.html"); p2.wait_for_selector("#grid .card")
        got = p2.evaluate("JSON.parse(localStorage.getItem('favs')||'[]').length")
        check(f"избранное: через {mins} мин после закрытия остаётся {want}", got == want, got); p2.close()
    c.close()
    # калькулятор
    c = b.new_context(viewport={"width": 390, "height": 800}); pg = c.new_page(); errs = []
    pg.on("pageerror", lambda e: errs.append(str(e)))
    pg.goto(BASE + "calc-k7x2q9.html")
    pg.fill("#np", "40"); pg.fill("#nf", "40"); pg.fill("#nr", "2"); pg.fill("#mo", "0")
    t = pg.inner_text("#res").replace("\xa0", " ")
    check("калькулятор: 40 товаров и 40 фото = 68 000 ₸", "68 000 ₸" in t and "7 000 ₸" in t, t[:80])
    pg.fill("#mo", "12"); t = pg.inner_text("#res").replace("\xa0", " ")
    check("калькулятор: 12 месяцев со скидкой 15%", "скидка 15%" in t and "71 400 ₸" in t)
    check("калькулятор: noindex на месте", pg.get_attribute('meta[name="robots"]', "content") == "noindex,nofollow")
    check("калькулятор: нет ошибок JavaScript", not errs, errs[:2])
    b.close()

print("\nИтог:", "всё в порядке" if not fails else f"упало {len(fails)}: " + "; ".join(fails))
sys.exit(1 if fails else 0)
