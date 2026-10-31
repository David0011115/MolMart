#!/usr/bin/env python3
"""Раскладывает общий код сайта по папкам заказчиков. Запуск: python3 tools/sync_clients.py

Общий код (index.html, sw.js, шрифты) лежит в корне репозитория и копируется в каждую папку из tools/clients.json.
Свои файлы заказчика (config.js, products.js, prices.csv, products.csv, manifest.json, img/, иконки) остаются как есть и руками правятся в его папке.
Поле "noindex": true добавляет в страницу запрет индексации поисковиками (для демо). Для настоящего заказчика ставьте false.

Новый заказчик в этом же репозитории:
  1) создать папку, положить в неё config.js, products.js, prices.csv, manifest.json, img/ (удобно скопировать demo/ и заменить данные);
  2) добавить строку с папкой в tools/clients.json;
  3) python3 tools/sync_clients.py, затем python3 tests/smoke.py (он проверяет каждую папку из clients.json).
Исправление общего кода делается один раз в корне, после чего этот скрипт обновляет всех заказчиков, а тест сразу покажет, если чья-то папка разошлась с корнем.
"""
import json, os, shutil, sys

R = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
NOINDEX = '<meta name="robots" content="noindex,nofollow">'


def clients():
    return json.load(open(os.path.join(R, "tools", "clients.json"), encoding="utf-8"))


def client_html(src, noindex):
    """Страница заказчика = основной index.html (+ запрет индексации для демо)."""
    return src.replace('<meta charset="utf-8">', '<meta charset="utf-8">\n' + NOINDEX, 1) if noindex else src


def main():
    src = open(os.path.join(R, "index.html"), encoding="utf-8").read()
    done = []
    for c in clients():
        d = os.path.join(R, c["dir"])
        if not os.path.isdir(d):
            print("ПРОПУЩЕНА (нет папки): " + c["dir"], file=sys.stderr)
            continue
        shutil.copy2(os.path.join(R, "sw.js"), os.path.join(d, "sw.js"))
        open(os.path.join(d, "index.html"), "w", encoding="utf-8").write(client_html(src, c.get("noindex", False)))
        shutil.copytree(os.path.join(R, "fonts"), os.path.join(d, "fonts"), dirs_exist_ok=True)
        done.append(c["dir"])
    print("обновлено из корня: " + ", ".join(done))


if __name__ == "__main__":
    main()
