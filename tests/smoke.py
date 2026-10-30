"""Быстрая проверка сайта. Запуск: python3 tests/smoke.py
Нужны: pip install playwright && playwright install chromium"""
import re, sys, threading, http.server, socketserver, functools, os
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
        pg.click("#cashone"); check(f"[{scheme}] товар добавляется в список кассира", pg.get_attribute("#cashone", "aria-pressed") == "true")
        pg.click("#cmpbtn"); pg.wait_for_selector("#cmp[open]")
        check(f"[{scheme}] сравнение открывается", pg.locator("#cmg .cmc").count() > 0)
        pg.click("#cmx"); pg.keyboard.press("Escape")
        pg.wait_for_timeout(300)
        check(f"[{scheme}] кнопка «Показать кассиру» появляется", not pg.eval_on_selector("#cashrow", "e=>e.hidden"))
        pg.click("#cashopen"); pg.wait_for_selector("#cash[open]")
        check(f"[{scheme}] кассир-экран показывает цену", "₸" in pg.inner_text("#cash") or "уточн" in pg.inner_text("#cash").lower())
        pg.click("#cashclr"); pg.wait_for_timeout(300)
        check(f"[{scheme}] список кассира очищается кнопкой", pg.eval_on_selector("#cashrow", "e=>e.hidden"))
        # «Что взять?»
        pg.click("#pickopen"); pg.wait_for_selector("#pk[open]"); pg.keyboard.press("Escape")
        # «Как это работает»
        pg.click("#hwopen"); pg.wait_for_selector("#hw[open]")
        check(f"[{scheme}] «Как это работает» показывает 3 шага", pg.locator("#hw .hwl li").count()==3)
        pg.keyboard.press("Escape")
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
    # самопроверка: отчёт уходит GET-запросом, повторно в тот же день не шлётся
    c = b.new_context(viewport={"width": 390, "height": 800}, service_workers="block"); pg = c.new_page()
    reqs = []
    pg.route("https://script.google.com/**", lambda r: (reqs.append(r.request.url), r.fulfill(status=200, body="{}"))[0])
    pg.goto(BASE + "index.html"); pg.wait_for_selector("#grid .card")
    probs = pg.evaluate("runCheck(true)")
    check("самопроверка: отчёт отправлен", len(reqs) == 1 and "c=1" in reqs[0], reqs[:1])
    check("самопроверка: проблем с фото нет", not any("фото" in x for x in (probs or [])), probs)
    pg.evaluate("localStorage.setItem('chk', new Intl.DateTimeFormat('en-CA',{timeZone:'Asia/Almaty'}).format(new Date()))")
    n0 = len(reqs); pg.evaluate("runCheck()"); pg.wait_for_timeout(300)
    check("самопроверка: в тот же день повторно не шлётся", len(reqs) == n0)
    c.close()
    # срок жизни: избранное хранится долго, список кассира 10 минут
    c = b.new_context(viewport={"width": 390, "height": 800}, service_workers="block"); pg = c.new_page()
    pg.goto(BASE + "index.html"); pg.wait_for_selector("#grid .card")
    nm = pg.evaluate("PRODUCTS.filter(p=>!p.hidden).slice(0,2).map(p=>p.name)")
    for mins, wf, wc in ((5, 2, 2), (11, 2, 0)):
        pg.evaluate("([n,m])=>{localStorage.setItem('favs',JSON.stringify(n));localStorage.setItem('cash',JSON.stringify(n));localStorage.setItem('cashSeen',String(Date.now()-m*60000))}", [nm, mins])
        p2 = c.new_page(); p2.goto(BASE + "index.html"); p2.wait_for_selector("#grid .card")
        gf = p2.evaluate("JSON.parse(localStorage.getItem('favs')||'[]').length"); gc = p2.evaluate("JSON.parse(localStorage.getItem('cash')||'[]').length")
        check(f"через {mins} мин: избранное {wf}, список кассира {wc}", (gf, gc) == (wf, wc), (gf, gc)); p2.close()
    c.close()
    # демо-версия
    c = b.new_context(viewport={"width": 390, "height": 800}, service_workers="block"); pg = c.new_page(); errs = []
    pg.on("pageerror", lambda e: errs.append(str(e))); pg.on("requestfailed", lambda r: errs.append("FAIL " + r.url))
    pg.goto(BASE + "demo/index.html"); pg.wait_for_selector("#grid .card")
    pg.eval_on_selector("#budrange", "e=>{e.value=2;e.dispatchEvent(new Event('input',{bubbles:true}))}"); pg.wait_for_timeout(300)
    nb = pg.locator("#grid .card").count()
    check("демо: фильтр бюджета сужает список", 0 < nb < 12, nb)
    pg.eval_on_selector("#budrange", "e=>{e.value=e.max;e.dispatchEvent(new Event('input',{bubbles:true}))}"); pg.wait_for_timeout(300)
    check("демо: «Любой» возвращает все товары", pg.locator("#grid .card").count() == 12)
    check("демо: 12 товаров", pg.locator("#grid .card").count() == 12, pg.locator("#grid .card").count())
    check("демо: внизу название демо-магазина, а не MolMart", "MolMart" not in pg.inner_text("#shop") and "Тёплый хлеб" in pg.inner_text("#shop"), pg.inner_text("#shop")[:40])
    check("демо: плашка «Демо-версия» видна", not pg.eval_on_selector("#demonote", "e=>e.hidden"))
    check("демо: нет ошибок и битых файлов", not errs, errs[:3])
    root_src = open(os.path.join(ROOT, "index.html"), encoding="utf-8").read()
    want = root_src.replace('<meta charset="utf-8">', '<meta charset="utf-8">\n<meta name="robots" content="noindex,nofollow">', 1)
    same = want == open(os.path.join(ROOT, "demo", "index.html"), encoding="utf-8").read()
    check("демо: код совпадает с основным сайтом (если нет, запусти tools/make_demo.py)", same)
    check("демо: закрыто от поисковиков (noindex)", pg.get_attribute('meta[name="robots"]', "content") == "noindex,nofollow")
    check("основной сайт не закрыт от поисковиков", "noindex" not in root_src)
    c.close()
    # демо кофейни: размеры одной карточкой
    c = b.new_context(viewport={"width": 390, "height": 800}, service_workers="block"); pg = c.new_page(); errs = []
    pg.on("pageerror", lambda e: errs.append(str(e))); pg.on("requestfailed", lambda r: errs.append("FAIL " + r.url))
    pg.goto(BASE + "demo-cafe/index.html"); pg.wait_for_selector("#grid .card")
    check("кафе: размеры собраны в карточки (13 карточек из 18 позиций)", pg.locator("#grid .card").count() == 13, pg.locator("#grid .card").count())
    pg.fill("#q", "капучино"); pg.wait_for_timeout(400)
    check("кафе: на карточке в списке видны цены всех размеров", "·" in pg.inner_text("#grid .card >> nth=0"), pg.inner_text("#grid .card >> nth=0"))
    check("кафе: поиск показывает одну карточку «Капучино»", pg.locator("#grid .card").count() == 1)
    pg.click("#grid .card >> nth=0"); pg.wait_for_selector("#dlg[open]")
    check("кафе: в карточке три размера", pg.locator("#dlg .sz").count() == 3, pg.locator("#dlg .sz").count())
    check("кафе: на кнопках размеров есть цены", all("₸" in x for x in pg.locator("#dlg .sz").all_inner_texts()), pg.locator("#dlg .sz").all_inner_texts())
    p1 = pg.inner_text("#dlg .price"); pg.click('#dlg .sz >> nth=1'); p2 = pg.inner_text("#dlg .price")
    check("кафе: смена размера меняет цену", p1 != p2, (p1, p2))
    check("кафе: нет ошибок", not errs, errs[:2])
    root_src = open(os.path.join(ROOT, "index.html"), encoding="utf-8").read()
    want = root_src.replace('<meta charset="utf-8">', '<meta charset="utf-8">\n<meta name="robots" content="noindex,nofollow">', 1)
    check("кафе: код совпадает с основным сайтом (запусти tools/make_demo.py)", want == open(os.path.join(ROOT, "demo-cafe", "index.html"), encoding="utf-8").read())
    c.close()
    # лист «Настройки»: значения из таблицы заменяют значения из config.js, пустые не трогают
    SET_CSV = "Параметр,Значение,Что это\nНазвание магазина,TestShop,x\nАдрес,Тестовая 1,x\nЧасы работы,,x\nОбъявление сверху,Сегодня до 22:00; приходите,x\nОсновной цвет,#336699,x\nЛоготип (ссылка на файл),icon-192.png,x\nTelegram для связи,test_dev,x\n"
    c = b.new_context(viewport={"width": 390, "height": 800}, service_workers="block"); pg = c.new_page(); errs = []
    pg.on("pageerror", lambda e: errs.append(str(e)))
    pg.route(re.compile(r"gid=777000444"), lambda r: r.fulfill(status=200, content_type="text/csv; charset=utf-8", body=SET_CSV))
    pg.goto(BASE + "index.html"); pg.wait_for_selector("#grid .card"); pg.wait_for_timeout(800)
    check("настройки: адрес из листа показан в блоке магазина", "Тестовая 1" in pg.inner_text("#shop"), pg.inner_text("#shop")[:60])
    check("настройки: пустые часы остаются из config.js", "8:00" in pg.inner_text("#shop"), pg.inner_text("#shop")[:80])
    check("настройки: объявление с «;» показано целиком", pg.inner_text("#annc") == "Сегодня до 22:00; приходите", pg.inner_text("#annc"))
    check("настройки: название магазина в заголовке вкладки", pg.title().startswith("TestShop"), pg.title())
    check("настройки: логотип-картинка в шапке", pg.locator("#title.logo img").count() == 1)
    check("настройки: основной цвет применён", pg.evaluate("getComputedStyle(document.documentElement).getPropertyValue('--b1').trim()") == "#336699")
    check("настройки: Telegram из листа попал в «О сайте»", pg.evaluate("abLink()") == "https://t.me/test_dev", pg.evaluate("abLink()"))
    p2 = c.new_page(); p2.route(re.compile(r"gid=777000444"), lambda r: r.abort())
    p2.goto(BASE + "index.html"); p2.wait_for_selector("#grid .card"); p2.wait_for_timeout(500)
    check("настройки: если лист не открылся, остаётся последняя сохранённая копия", "Тестовая 1" in p2.inner_text("#shop"), p2.inner_text("#shop")[:60]); p2.close()
    check("настройки: нет ошибок JavaScript", not errs, errs[:2])
    c.close()
    # лист «Настройки» недоступен: сайт работает на config.js, объявления нет
    c = b.new_context(viewport={"width": 390, "height": 800}, service_workers="block"); pg = c.new_page(); errs = []
    pg.on("pageerror", lambda e: errs.append(str(e)))
    pg.route(re.compile(r"gid=777000444"), lambda r: r.fulfill(status=404, body="no"))
    pg.goto(BASE + "index.html"); pg.wait_for_selector("#grid .card"); pg.wait_for_timeout(500)
    check("настройки недоступны: адрес из config.js", "Улы Дала" in pg.inner_text("#shop"), pg.inner_text("#shop")[:60])
    check("настройки недоступны: объявление скрыто", pg.eval_on_selector("#annc", "e=>e.hidden"))
    check("настройки недоступны: нет ошибок JavaScript", not errs, errs[:2])
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
