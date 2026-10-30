"""Собирает папку demo/ из общего кода сайта. Запуск: python3 tools/make_demo.py
Общий код (index.html, sw.js, шрифты, иконки) копируется из корня, а свои файлы демо
(config.js, products.js, prices.csv, manifest.json, img/) остаются как есть."""
import shutil, os
R = os.path.dirname(os.path.dirname(os.path.abspath(__file__))); D = os.path.join(R, "demo")
NOINDEX = '<meta name="robots" content="noindex,nofollow">'
def demo_html(src):
    """Страница демо = основной index.html + запрет индексации поисковиками."""
    return src.replace('<meta charset="utf-8">', '<meta charset="utf-8">\n' + NOINDEX, 1)
for _d in ("demo", "demo-cafe"):
    _D = os.path.join(R, _d)
    if os.path.isdir(_D):
        shutil.copy2(os.path.join(R, "sw.js"), os.path.join(_D, "sw.js"))
        open(os.path.join(_D, "index.html"), "w", encoding="utf-8").write(demo_html(open(os.path.join(R, "index.html"), encoding="utf-8").read()))
for _d in ("demo", "demo-cafe"):
    if os.path.isdir(os.path.join(R, _d)): shutil.copytree(os.path.join(R, "fonts"), os.path.join(R, _d, "fonts"), dirs_exist_ok=True)
print("demo обновлено из корня")
