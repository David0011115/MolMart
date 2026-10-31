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
    # Тест не должен зависеть от Google: настоящую таблицу цен подменяем локальным prices.csv
    PRICES_LOCAL = open(os.path.join(ROOT, "prices.csv"), encoding="utf-8-sig").read()
    _new_context = b.new_context
    def new_context(**kw):
        ctx = _new_context(**kw)
        ctx.route(re.compile(r"docs\.google\.com/.*gid=392017231"), lambda r: r.fulfill(status=200, content_type="text/csv; charset=utf-8", body=PRICES_LOCAL))
        ctx.route(re.compile(r"docs\.google\.com/.*gid=777000555"), lambda r: r.abort())   # лист «Товары» недоступен: берётся products.csv
        return ctx
    b.new_context = new_context
    for scheme in ("light", "dark"):
        c = b.new_context(viewport={"width": 390, "height": 800}, color_scheme=scheme, service_workers="block")
        pg = c.new_page(); errs = []
        pg.on("pageerror", lambda e: errs.append(str(e)))
        pg.goto(BASE + "index.html"); pg.wait_for_selector("#grid .card:not(.sk)", timeout=8000)
        n = pg.locator("#grid .card").count()
        check(f"[{scheme}] каталог показывает товары", n > 0, n)
        check(f"[{scheme}] нет горизонтальной прокрутки", pg.evaluate("document.documentElement.scrollWidth<=innerWidth+1"))
        # разбор цен
        check(f"[{scheme}] цена «1 300,00 ₸» читается как 1300", pg.evaluate("[num('1 300 ₸'),num('1 300,00 ₸'),num('1300.00'),num('')]") == [1300, 1300, 1300, None])
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
    pg.goto(BASE + "index.html"); pg.wait_for_selector("#grid .card:not(.sk)")
    probs = pg.evaluate("runCheck(true)")
    check("самопроверка: отчёт отправлен", len(reqs) == 1 and "c=1" in reqs[0], reqs[:1])
    check("самопроверка: проблем с фото нет", not any("фото" in x for x in (probs or [])), probs)
    pg.evaluate("localStorage.setItem('chk', new Intl.DateTimeFormat('en-CA',{timeZone:'Asia/Almaty'}).format(new Date()))")
    n0 = len(reqs); pg.evaluate("runCheck()"); pg.wait_for_timeout(300)
    check("самопроверка: в тот же день повторно не шлётся", len(reqs) == n0)
    c.close()
    # срок жизни: избранное хранится долго, список кассира 10 минут
    c = b.new_context(viewport={"width": 390, "height": 800}, service_workers="block"); pg = c.new_page()
    pg.goto(BASE + "index.html"); pg.wait_for_selector("#grid .card:not(.sk)")
    nm = pg.evaluate("PRODUCTS.filter(p=>!p.hidden).slice(0,2).map(p=>p.name)")
    for mins, wf, wc in ((5, 2, 2), (11, 2, 0)):
        pg.evaluate("([n,m])=>{localStorage.setItem('favs',JSON.stringify(n));localStorage.setItem('cash',JSON.stringify(n));localStorage.setItem('cashSeen',String(Date.now()-m*60000))}", [nm, mins])
        p2 = c.new_page(); p2.goto(BASE + "index.html"); p2.wait_for_selector("#grid .card:not(.sk)")
        gf = p2.evaluate("JSON.parse(localStorage.getItem('favs')||'[]').length"); gc = p2.evaluate("JSON.parse(localStorage.getItem('cash')||'[]').length")
        check(f"через {mins} мин: избранное {wf}, список кассира {wc}", (gf, gc) == (wf, wc), (gf, gc)); p2.close()
    c.close()
    # демо-версия
    c = b.new_context(viewport={"width": 390, "height": 800}, service_workers="block"); pg = c.new_page(); errs = []
    pg.on("pageerror", lambda e: errs.append(str(e))); pg.on("requestfailed", lambda r: errs.append("FAIL " + r.url))
    pg.goto(BASE + "demo/index.html"); pg.wait_for_selector("#grid .card:not(.sk)")
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
    pg.goto(BASE + "demo-cafe/index.html"); pg.wait_for_selector("#grid .card:not(.sk)")
    check("кафе: размеры собраны в карточки (22 карточки из 27 позиций)", pg.locator("#grid .card").count() == 22, pg.locator("#grid .card").count())
    pg.fill("#q", "капучино"); pg.wait_for_timeout(400)
    check("кафе: на карточке в списке видны цены всех размеров", "·" in pg.inner_text("#grid .card >> nth=0"), pg.inner_text("#grid .card >> nth=0"))
    check("кафе: поиск показывает одну карточку «Капучино»", pg.locator("#grid .card").count() == 1)
    pg.click("#grid .card >> nth=0"); pg.wait_for_selector("#dlg[open]")
    check("кафе: в карточке три размера", pg.locator("#dlg .sz").count() == 3, pg.locator("#dlg .sz").count())
    check("кафе: на кнопках размеров есть цены", all("₸" in x for x in pg.locator("#dlg .sz").all_inner_texts()), pg.locator("#dlg .sz").all_inner_texts())
    p1 = pg.inner_text("#dlg .price"); pg.click('#dlg .sz >> nth=1'); p2 = pg.inner_text("#dlg .price")
    check("кафе: смена размера меняет цену", p1 != p2, (p1, p2))
    check("кафе: нет ошибок", not errs, errs[:2])
    pg.click("#x") if pg.locator("#x").count() else None
    # аллергены, калории, добавки, столик
    pg.goto(BASE + "demo-cafe/index.html?table=5"); pg.wait_for_selector("#grid .card:not(.sk)")
    check("кафе: столик показан на странице", "5" in pg.inner_text("#tblbar") and not pg.eval_on_selector("#tblbar", "e=>e.hidden"), pg.inner_text("#tblbar"))
    check("кафе: раздел «Добавки» есть", pg.evaluate("PRODUCTS.some(p=>p.category==='Добавки')"))
    pg.fill("#q", "круассан"); pg.wait_for_timeout(400); pg.click("#grid .card >> nth=0"); pg.wait_for_selector("#dlg[open]")
    check("кафе: в карточке блок «Аллергены»", "Глютен" in pg.inner_text("#dlg .alg"), pg.inner_text("#dlg"))
    check("кафе: в карточке калории", "ккал" in pg.inner_text("#dlg"))
    pg.click("#cashone"); pg.keyboard.press("Escape"); pg.wait_for_timeout(300); pg.click("#cashopen"); pg.wait_for_selector("#cash[open]")
    check("кафе: номер столика на экране кассира", "Столик 5" in pg.inner_text("#cash"), pg.inner_text("#cash")[:60])
    pg.keyboard.press("Escape"); pg.click('.lb[data-l="kk"]'); pg.wait_for_timeout(200)
    check("кафе: столик на казахском", "Үстел 5" in pg.inner_text("#tblbar"), pg.inner_text("#tblbar"))
    # меню по времени (часы Алматы = UTC+5): утро 09:00 и вечер 20:00
    for hh, iso, early_late, eve_late in ((9, "2026-10-30T04:00:00Z", False, True), (20, "2026-10-30T15:00:00Z", True, False)):
        pc = c.new_page(); pc.clock.set_fixed_time(iso); pc.goto(BASE + "demo-cafe/index.html"); pc.wait_for_selector("#grid .card:not(.sk)")
        pc.fill("#q", "сырники"); pc.wait_for_timeout(400)
        check(f"кафе {hh}:00: завтрак {'недоступен' if early_late else 'доступен'}", (pc.locator("#grid .card.late").count() == 1) == early_late)
        pc.fill("#q", "паста"); pc.wait_for_timeout(400)
        check(f"кафе {hh}:00: вечернее меню {'недоступно' if eve_late else 'доступно'}", (pc.locator("#grid .card.late").count() == 1) == eve_late)
        if eve_late: check(f"кафе {hh}:00: подпись «с 17:00»", "17:00" in pc.inner_text("#grid .card .oos.lt"), pc.inner_text("#grid .card"))
        pc.close()
    pg.evaluate("sessionStorage.clear()"); pg.goto(BASE + "demo-cafe/index.html?table=%3Cb%3E"); pg.wait_for_selector("#grid .card:not(.sk)")
    check("кафе: мусор в ?table= игнорируется", pg.eval_on_selector("#tblbar", "e=>e.hidden"))
    root_src = open(os.path.join(ROOT, "index.html"), encoding="utf-8").read()
    want = root_src.replace('<meta charset="utf-8">', '<meta charset="utf-8">\n<meta name="robots" content="noindex,nofollow">', 1)
    check("кафе: код совпадает с основным сайтом (запусти tools/make_demo.py)", want == open(os.path.join(ROOT, "demo-cafe", "index.html"), encoding="utf-8").read())
    c.close()
    # лист «Настройки»: значения из таблицы заменяют значения из config.js, пустые не трогают
    SET_CSV = "Параметр,Значение,Что это\nНазвание магазина,TestShop,x\nАдрес,Тестовая 1,x\nЧасы работы,,x\nОбъявление сверху,Сегодня до 22:00; приходите,x\nОсновной цвет,#336699,x\nЛоготип (ссылка на файл),icon-192.png,x\nTelegram для связи,test_dev,x\n"
    c = b.new_context(viewport={"width": 390, "height": 800}, service_workers="block"); pg = c.new_page(); errs = []
    pg.on("pageerror", lambda e: errs.append(str(e)))
    pg.route(re.compile(r"gid=777000444"), lambda r: r.fulfill(status=200, content_type="text/csv; charset=utf-8", body=SET_CSV))
    pg.goto(BASE + "index.html"); pg.wait_for_selector("#grid .card:not(.sk)"); pg.wait_for_timeout(800)
    check("настройки: адрес из листа показан в блоке магазина", "Тестовая 1" in pg.inner_text("#shop"), pg.inner_text("#shop")[:60])
    check("настройки: пустые часы остаются из config.js", "8:00" in pg.inner_text("#shop"), pg.inner_text("#shop")[:80])
    check("настройки: объявление с «;» показано целиком", pg.inner_text("#annc") == "Сегодня до 22:00; приходите", pg.inner_text("#annc"))
    check("настройки: название магазина в заголовке вкладки", pg.title().startswith("TestShop"), pg.title())
    check("настройки: логотип-картинка в шапке", pg.locator("#title.logo img").count() == 1)
    check("настройки: основной цвет применён", pg.evaluate("getComputedStyle(document.documentElement).getPropertyValue('--b1').trim()") == "#336699")
    check("настройки: Telegram из листа попал в «О сайте»", pg.evaluate("abLink()") == "https://t.me/test_dev", pg.evaluate("abLink()"))
    # блик на логотипе: галочка в листе «Настройки» (нет строки или TRUE = есть, FALSE = нет)
    for val, want in (("", "block"), ("TRUE", "block"), ("FALSE", "none")):
        body = SET_CSV + ("Блик на логотипе," + val + ",x\n" if val else "")
        pb = c.new_page(); pb.route(re.compile(r"gid=777000444"), (lambda bb: (lambda r: r.fulfill(status=200, content_type="text/csv; charset=utf-8", body=bb)))(body))
        pb.goto(BASE + "index.html"); pb.wait_for_selector("#title.logo .lg"); pb.wait_for_timeout(300)
        d = pb.evaluate("getComputedStyle(document.querySelector('#title .lg'),'::after').display")
        check("настройки: блик на логотипе " + (val or "(строки нет)") + " -> " + want, d == want, d); pb.close()
    p2 = c.new_page(); p2.route(re.compile(r"gid=777000444"), lambda r: r.abort())
    p2.goto(BASE + "index.html"); p2.wait_for_selector("#grid .card:not(.sk)"); p2.wait_for_timeout(500)
    check("настройки: если лист не открылся, остаётся последняя сохранённая копия", "Тестовая 1" in p2.inner_text("#shop"), p2.inner_text("#shop")[:60]); p2.close()
    check("настройки: нет ошибок JavaScript", not errs, errs[:2])
    c.close()
    # лист «Настройки» недоступен: сайт работает на config.js, объявления нет
    c = b.new_context(viewport={"width": 390, "height": 800}, service_workers="block"); pg = c.new_page(); errs = []
    pg.on("pageerror", lambda e: errs.append(str(e)))
    pg.route(re.compile(r"gid=777000444"), lambda r: r.fulfill(status=404, body="no"))
    pg.goto(BASE + "index.html"); pg.wait_for_selector("#grid .card:not(.sk)"); pg.wait_for_timeout(500)
    check("настройки недоступны: адрес из config.js", "Улы Дала" in pg.inner_text("#shop"), pg.inner_text("#shop")[:60])
    check("настройки недоступны: объявление скрыто", pg.eval_on_selector("#annc", "e=>e.hidden"))
    check("настройки недоступны: нет ошибок JavaScript", not errs, errs[:2])
    c.close()
    # --- панель «Фильтры» ---
    for scheme in ("light", "dark"):
        c = b.new_context(viewport={"width": 390, "height": 800}, color_scheme=scheme, service_workers="block"); pg = c.new_page(); errs = []
        pg.on("pageerror", lambda e: errs.append(str(e)))
        pg.goto(BASE + "index.html"); pg.wait_for_selector("#grid .card:not(.sk)")
        check(f"[{scheme}] фильтры: панель по умолчанию закрыта", pg.eval_on_selector("#flt", "e=>e.hidden"))
        check(f"[{scheme}] фильтры: липкая панель компактная (до 80 px)", pg.eval_on_selector("#bar", "e=>e.getBoundingClientRect().height") <= 80, pg.eval_on_selector("#bar", "e=>e.getBoundingClientRect().height"))
        n0 = pg.locator("#grid .card").count()
        pg.click("#fbtn"); check(f"[{scheme}] фильтры: кнопка открывает панель", not pg.eval_on_selector("#flt", "e=>e.hidden") and pg.get_attribute("#fbtn", "aria-expanded") == "true")
        pg.click('#tags .chip >> nth=0'); pg.wait_for_timeout(300)
        n1 = pg.locator("#grid .card").count()
        check(f"[{scheme}] фильтры: метка сужает список и на кнопке цифра 1", 0 < n1 < n0 and pg.inner_text("#fbtn").strip().endswith("1"), (n0, n1, pg.inner_text("#fbtn")))
        pg.click("#freset"); pg.wait_for_timeout(300)
        check(f"[{scheme}] фильтры: «Сбросить» возвращает всё", pg.locator("#grid .card").count() == n0 and pg.locator("#fbtn b").count() == 0)
        pg.keyboard.press("Escape"); check(f"[{scheme}] фильтры: Escape закрывает панель", pg.eval_on_selector("#flt", "e=>e.hidden"))
        pg.click("#fbtn"); pg.mouse.click(195, 790)
        check(f"[{scheme}] фильтры: клик вне панели закрывает её", pg.eval_on_selector("#flt", "e=>e.hidden"))
        pg.evaluate("window.scrollTo(0,600)"); pg.wait_for_timeout(200); pg.click("#fbtn")
        check(f"[{scheme}] фильтры: панель открывается и при прокрутке", pg.is_visible("#flt") and pg.eval_on_selector("#flt", "e=>e.getBoundingClientRect().top") >= 0)
        pg.click("#fdone"); pg.click('.lb[data-l="kk"]'); pg.click("#fbtn")
        check(f"[{scheme}] фильтры: на казахском подпись есть", "Сүзгілер" in pg.inner_text("#fbtn") and "Көрсету" in pg.inner_text("#fdone"))
        check(f"[{scheme}] фильтры: нет ошибок JavaScript", not errs, errs[:2])
        c.close()
    # --- метки, подпись и цвет темы из config.js ---
    CFG = open(os.path.join(ROOT, "config.js"), encoding="utf-8").read()
    c = b.new_context(viewport={"width": 390, "height": 800}, service_workers="block"); pg = c.new_page(); errs = []
    pg.on("pageerror", lambda e: errs.append(str(e)))
    CFG2 = CFG + '\nconst LABELS_CFG = {vegan:{ru:"Веган",kk:"Вегандық",color:"#2e7d32",icon:"V"}, bad:{ru:""}, "Плохой Ключ":{ru:"x"}, fav:{ru:"взлом"}};\n'
    CFG2 = CFG2.replace('const FOOTER_SIGN = "Made by Рурак Д. · 2026";', 'const FOOTER_SIGN = "Сделано для кафе «Тест»";').replace('const THEME_COLORS = ["#fbf4e6", "#0c1a1f"];', 'const THEME_COLORS = ["#ffffff", "#000000"];')
    pg.route("**/config.js", lambda r: r.fulfill(status=200, content_type="application/javascript", body=CFG2))
    pg.goto(BASE + "index.html"); pg.wait_for_selector("#grid .card:not(.sk)"); pg.wait_for_function("PRICES_SRC!=='none'")
    names = pg.evaluate("PRODUCTS.map(p=>p.name)")
    pg.evaluate("t=>applyPrices(t)", "Товар,Цена,Метки\n\"%s\",600,\"Веган, Хит\"\n" % names[0]); pg.evaluate("applyLang()")
    check("метки: своя метка «Веган» читается из таблицы", pg.evaluate("PRODUCTS[0].labels") == ["vegan", "hit"], pg.evaluate("PRODUCTS[0].labels"))
    check("метки: служебные и неправильные ключи из config.js игнорируются", pg.evaluate("Object.keys(LABELS)") == ["halal", "new", "hit", "sale", "spicy", "vegan", "fav", "stock"], pg.evaluate("Object.keys(LABELS)"))
    check("метки: служебную «Избранное» подменить нельзя", pg.evaluate("LABELS.fav.ru") != "взлом")
    rib = pg.locator("#grid .card >> nth=0").locator(".rib.r-vegan")
    check("метки: лента «Веган» с цветом и значком на карточке", rib.count() == 1 and rib.evaluate("e=>getComputedStyle(e,'::before').content") == '"V"' and "rgb(46, 125, 50)" in rib.evaluate("e=>getComputedStyle(e).backgroundColor"), (rib.count(), rib.inner_text(), rib.evaluate("e=>getComputedStyle(e).backgroundColor")))
    pg.click("#fbtn")
    check("метки: «Веган» есть среди фильтров", "Веган" in pg.inner_text("#tags"))
    check("подпись: берётся из config.js", "Сделано для кафе «Тест»" in pg.inner_text("#footer") and "Рурак" not in pg.inner_text("#footer"))
    check("цвет темы: берётся из config.js", pg.evaluate("[...document.querySelectorAll('meta[name=theme-color]')].map(m=>m.content)") == ["#ffffff", "#000000"])
    check("метки: нет ошибок JavaScript", not errs, errs[:2])
    c.close()
    # --- разбор таблицы без внешней сети: цены, акции, даты, самопроверка ---
    c = b.new_context(viewport={"width": 390, "height": 800}, service_workers="block"); pg = c.new_page(); errs = []
    pg.on("pageerror", lambda e: errs.append(str(e)))
    pg.goto(BASE + "index.html"); pg.wait_for_selector("#grid .card:not(.sk)"); pg.wait_for_function("PRICES_SRC!=='none'")
    names = pg.evaluate("PRODUCTS.map(p=>p.name)")
    def table(rows):
        return "Товар,Цена,Акционная цена,Акция до,Метки,Изменено,Нет в наличии\n" + "\n".join(",".join('"%s"' % x for x in r) for r in rows) + "\n"
    rows = [
        [names[0], "1 300,00 ₸", "", "", "", "30.10.2026", ""],
        [names[1], "1000", "800", "31.12.2099", "", "", ""],
        [names[2], "1000", "800", "01.01.2020", "", "", ""],
        [names[3], "1000", "1200", "", "", "", ""],
        [names[4], "1000", "800", "до пятницы", "", "", ""],
        [names[5], "", "", "", "", "", "TRUE"],
        ["Такого товара нет на сайте", "500", "", "", "", "", ""],
        ["", "", "", "", "", "", "FALSE"],
    ]
    pg.evaluate("t=>applyPrices(t)", table(rows))
    got = pg.evaluate("PRODUCTS.slice(0,6).map(p=>({price:p.price,old:p.oldPrice||null,out:!!p.out}))")
    check("разбор: «1 300,00 ₸» = 1300", got[0]["price"] == 1300, got[0])
    check("разбор: акция до 31.12.2099 действует", got[1]["price"] == 800 and got[1]["old"] == 1000, got[1])
    check("разбор: просроченная акция не действует", got[2]["price"] == 1000 and got[2]["old"] is None, got[2])
    check("разбор: акция дороже обычной не действует", got[3]["price"] == 1000 and got[3]["old"] is None, got[3])
    check("разбор: непонятная дата не включает акцию", got[4]["price"] == 1000 and got[4]["old"] is None, got[4])
    check("разбор: пустая цена и «Нет в наличии»", got[5]["price"] is None and got[5]["out"], got[5])
    check("самопроверка: непонятная дата названа", pg.evaluate("BAD_PROMO") == [names[4]])
    check("самопроверка: бесполезная акция названа", pg.evaluate("DEAD_PROMO") == [names[3]])
    check("самопроверка: лишняя строка таблицы названа", pg.evaluate("UNKNOWN_ROWS") == ["Такого товара нет на сайте"])
    check("самопроверка: товары без строки в таблице названы", len(pg.evaluate("NOT_IN_TABLE")) == len(names) - 6 and names[6] in pg.evaluate("NOT_IN_TABLE"))
    check("разбор: нет ошибок JavaScript", not errs, errs[:2])
    c.close()
    # --- лист «Товары»: описания из таблицы и запасной products.csv ---
    CFG = open(os.path.join(ROOT, "config.js"), encoding="utf-8").read()
    def desc_csv(rows):
        return "Товар,Вес,Состав,КБЖУ,Аллергены,Название (каз),Состав (каз),КБЖУ (каз),Аллергены (каз)\n" + "\n".join(",".join('"%s"' % x for x in r) for r in rows) + "\n"
    c = b.new_context(viewport={"width": 390, "height": 800}, service_workers="block"); pg = c.new_page(); errs = []
    pg.on("pageerror", lambda e: errs.append(str(e)))
    pg.route("**/products.csv*", lambda r: r.fulfill(status=200, content_type="text/csv; charset=utf-8", body=desc_csv([["__N0__", "123 г", "Тестовый состав из файла", "", "Молоко", "", "", "", ""]])))
    pg.goto(BASE + "index.html"); pg.wait_for_selector("#grid .card:not(.sk)"); pg.wait_for_function("DESC_SRC!=='none'")
    n0, n1 = pg.evaluate("[PRODUCTS[0].name, PRODUCTS[1].name]")
    pg.unroute("**/products.csv*")
    pg.route("**/products.csv*", lambda r: r.fulfill(status=200, content_type="text/csv; charset=utf-8", body=desc_csv([[n0, "123 г", "Тестовый состав из файла", "", "Молоко", "Қазақша атау", "", "", ""], ["Нет такого товара", "1 г", "", "", "", "", "", "", ""]])))
    pg.reload(); pg.wait_for_selector("#grid .card:not(.sk)"); pg.wait_for_function("DESC_SRC==='file'")
    got = pg.evaluate("(()=>{const p=PRODUCTS[0],q=PRODUCTS[1];return {w:p.weight,c:p.composition,a:p.allergens,kn:p.kk.name,kc:p.kk.composition,qc:q.composition}})()")
    check("«Товары»: запасной products.csv подставляет вес, состав, аллергены", got["w"] == "123 г" and got["c"] == "Тестовый состав из файла" and got["a"] == "Молоко", got)
    check("«Товары»: казахское название из файла", got["kn"] == "Қазақша атау", got)
    check("«Товары»: пустые ячейки оставляют значения из products.js", got["kc"] and got["qc"] != "Тестовый состав из файла", got)
    check("«Товары»: строка с неизвестным названием названа", pg.evaluate("DESC_UNKNOWN") == ["Нет такого товара"])
    pg.click("#grid .card >> nth=0"); pg.wait_for_selector("#dlg[open]")
    t = pg.inner_text("#dlg")
    check("«Товары»: в карточке видны состав и блок «Аллергены»", "Тестовый состав из файла" in t and "Аллергены" in t and "Молоко" in t and "123 г" in t, t[:200])
    pg.evaluate("t=>applyDescriptions(t)", desc_csv([[n0, "", "", "", "", "", "", "", ""]]))
    check("«Товары»: очищенная ячейка возвращает текст из products.js", pg.evaluate("PRODUCTS[0].composition") != "Тестовый состав из файла" and pg.evaluate("PRODUCTS[0].weight") != "123 г")
    check("«Товары»: нет ошибок JavaScript", not errs, errs[:2])
    c.close()
    c = b.new_context(viewport={"width": 390, "height": 800}, service_workers="block"); pg = c.new_page(); held = []
    pg.route("**/config.js", lambda r: r.fulfill(status=200, content_type="application/javascript", body=re.sub(r'productsGid:\s*"\d*"', 'productsGid: "999"', CFG)))
    pg.route(re.compile(r"docs\.google\.com/.*gid=999"), lambda r: held.append(r))
    pg.goto(BASE + "index.html"); pg.wait_for_selector("#grid .card:not(.sk)", timeout=5000)
    n0 = pg.evaluate("PRODUCTS[0].name")
    held[0].fulfill(status=200, content_type="text/csv; charset=utf-8", body=desc_csv([[n0, "999 г", "Состав из таблицы", "", "", "", "", "", ""]]))
    pg.wait_for_function("DESC_SRC==='sheet'", timeout=5000)
    check("«Товары»: лист из Google обновляет описание после показа каталога", pg.evaluate("PRODUCTS[0].weight") == "999 г" and pg.evaluate("PRODUCTS[0].composition") == "Состав из таблицы")
    c.close()
    # --- порядок загрузки: цены из запасного файла сразу, таблица Google позже ---
    c = b.new_context(viewport={"width": 390, "height": 800}, service_workers="block"); pg = c.new_page(); held = []
    pg.route(re.compile(r"docs\.google\.com/.*gid=392017231"), lambda r: held.append(r))   # таблица «зависла»
    pg.goto(BASE + "index.html"); pg.wait_for_selector("#grid .card:not(.sk)", timeout=5000)
    check("загрузка: каталог показан, пока таблица ещё не ответила", pg.evaluate("PRICES_SRC") == "file" and len(held) == 1)
    n0 = pg.evaluate("PRODUCTS[0].name")
    held[0].fulfill(status=200, content_type="text/csv; charset=utf-8", body=table([[n0, "777", "", "", "", "", ""]]))
    pg.wait_for_function("PRICES_SRC==='sheet'", timeout=5000)
    check("загрузка: ответ таблицы обновляет цены", pg.evaluate("PRODUCTS[0].price") == 777 and "777" in pg.inner_text("#grid"))
    check("загрузка: плашки «цены устарели» нет", pg.eval_on_selector("#offline", "e=>e.hidden"))
    c.close()
    c = b.new_context(viewport={"width": 390, "height": 800}, service_workers="block"); pg = c.new_page()
    pg.route(re.compile(r"docs\.google\.com/.*gid=392017231"), lambda r: r.fulfill(status=503, body="no"))
    pg.goto(BASE + "index.html"); pg.wait_for_selector("#grid .card:not(.sk)"); pg.wait_for_function("PRICES_STALE===true", timeout=5000)
    check("загрузка: таблица недоступна — плашка и причина", not pg.eval_on_selector("#offline", "e=>e.hidden") and "503" in pg.evaluate("PRICES_WHY"), pg.evaluate("PRICES_WHY"))
    c.close()
    # --- все папки заказчиков из tools/clients.json: код совпадает с корнем и страница открывается ---
    import json
    root_src = open(os.path.join(ROOT, "index.html"), encoding="utf-8").read()
    root_sw = open(os.path.join(ROOT, "sw.js"), encoding="utf-8").read()
    for cl in json.load(open(os.path.join(ROOT, "tools", "clients.json"), encoding="utf-8")):
        d = cl["dir"]; want = root_src.replace('<meta charset="utf-8">', '<meta charset="utf-8">\n<meta name="robots" content="noindex,nofollow">', 1) if cl.get("noindex") else root_src
        check(f"заказчик {d}: index.html совпадает с корнем (запусти tools/sync_clients.py)", want == open(os.path.join(ROOT, d, "index.html"), encoding="utf-8").read())
        check(f"заказчик {d}: sw.js совпадает с корнем", root_sw == open(os.path.join(ROOT, d, "sw.js"), encoding="utf-8").read())
        check(f"заказчик {d}: свои файлы на месте", all(os.path.exists(os.path.join(ROOT, d, f)) for f in ("config.js", "products.js", "manifest.json")))
        c = b.new_context(viewport={"width": 390, "height": 800}, service_workers="block"); pg = c.new_page(); errs = []
        pg.on("pageerror", lambda e: errs.append(str(e)))
        pg.goto(BASE + d + "/index.html"); pg.wait_for_selector("#grid .card:not(.sk)", timeout=8000)
        check(f"заказчик {d}: каталог открывается без ошибок", pg.locator("#grid .card").count() > 0 and not errs, errs[:2])
        c.close()
    b.close()

print("\nИтог:", "всё в порядке" if not fails else f"упало {len(fails)}: " + "; ".join(fails))
sys.exit(1 if fails else 0)
