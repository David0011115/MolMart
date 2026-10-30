"""Собирает папку demo/ из общего кода сайта. Запуск: python3 tools/make_demo.py
Общий код (index.html, sw.js, шрифты, иконки) копируется из корня, а свои файлы демо
(config.js, products.js, prices.csv, manifest.json, img/) остаются как есть."""
import shutil, os
R = os.path.dirname(os.path.dirname(os.path.abspath(__file__))); D = os.path.join(R, "demo")
for f in ("index.html", "sw.js"):
    shutil.copy2(os.path.join(R, f), os.path.join(D, f))
shutil.copytree(os.path.join(R, "fonts"), os.path.join(D, "fonts"), dirs_exist_ok=True)
print("demo обновлено из корня")
