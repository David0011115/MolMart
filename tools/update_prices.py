#!/usr/bin/env python3
"""Обновляет запасной файл prices.csv из опубликованной Google Таблицы.

Запускается раз в сутки из .github/workflows/update-prices.yml.
Ссылка на таблицу берётся из config.js (pricesSheet), чтобы нигде не дублировать её.

Защита от плохих данных: если таблица недоступна, вернула не CSV, потеряла колонки
или товаров стало заметно меньше, prices.csv не трогаем, а шаг завершается ошибкой
(GitHub пришлёт письмо о неудачном запуске). Обойти защиту: FORCE=1.

Переменные окружения:
  PRICES_SOURCE  ссылка или путь к файлу вместо pricesSheet из config.js (нужно для тестов)
  FORCE          1 = пропустить проверку «товаров стало намного меньше»
  GITHUB_OUTPUT  сюда пишется changed=true|false
"""
import csv
import io
import os
import re
import sys
import time
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TARGET = os.path.join(ROOT, "prices.csv")
MIN_KEEP = 0.8          # новых товаров не меньше 80% от прежнего числа
MIN_KEEP_PRICED = 0.6   # товаров с ценой не меньше 60% от прежнего числа


def fail(msg):
    print("ОШИБКА: " + msg, file=sys.stderr)
    sys.exit(1)


def sheet_url():
    src = os.environ.get("PRICES_SOURCE", "").strip()
    if src:
        return src
    cfg = open(os.path.join(ROOT, "config.js"), encoding="utf-8").read()
    m = re.search(r'pricesSheet\s*:\s*"([^"]+)"', cfg)
    if not m:
        fail("в config.js не найден pricesSheet")
    return m.group(1)


def fetch(src):
    if not re.match(r"https?://", src):
        return open(src, "rb").read().decode("utf-8-sig")
    last = None
    for attempt in range(1, 5):
        try:
            req = urllib.request.Request(src + ("&" if "?" in src else "?") + "v=%d" % time.time(),
                                         headers={"User-Agent": "molmart-prices-sync"})
            with urllib.request.urlopen(req, timeout=30) as r:
                return r.read().decode("utf-8-sig")
        except Exception as e:  # сеть, 5xx, таймаут
            last = e
            print("попытка %d не удалась: %s" % (attempt, e))
            time.sleep(attempt * 5)
    fail("таблица недоступна: %s" % last)


def read_rows(text):
    return list(csv.reader(io.StringIO(text)))


def norm_price(v):
    """«1 300 ₸» -> 1300. Если значение не похоже на число, оставляем как есть."""
    s = v.replace(" ", "").replace(" ", "").replace(" ", "").replace("₸", "").strip()
    if re.fullmatch(r"\d+", s):
        return str(int(s))
    if re.fullmatch(r"\d+[.,]\d+", s):
        return s.replace(",", ".")
    return v.strip()


def norm_bool(v):
    return "TRUE" if re.fullmatch(r"(true|истина|да|1|x|х|✓|v)", v.strip(), re.I) else ""


def build(old_rows, text):
    old_header = old_rows[0]
    rows = read_rows(text)
    if len(rows) < 2:
        fail("в таблице нет строк")
    head = [h.strip().lower() for h in rows[0]]
    if "товар" not in head or "цена" not in head:
        fail("в ответе нет колонок «Товар» и «Цена» (пришло не то, что нужно): %r" % rows[0][:6])
    idx = {h: i for i, h in enumerate(head)}
    out = [old_header]
    for r in rows[1:]:
        name = r[idx["товар"]].strip() if idx["товар"] < len(r) else ""
        if not name:
            continue
        line = []
        for col in old_header:
            key = col.strip().lower()
            v = r[idx[key]] if key in idx and idx[key] < len(r) else ""
            if key in ("цена", "акционная цена"):
                v = norm_price(v)
            elif key == "нет в наличии":
                v = norm_bool(v)
            else:
                v = v.strip()
            line.append(v)
        out.append(line)
    return out


def priced(rows):
    i = [c.strip().lower() for c in rows[0]].index("цена")
    return sum(1 for r in rows[1:] if r[i].strip())


def serialize(rows):
    o = io.StringIO()
    csv.writer(o, lineterminator="\n").writerows(rows)
    return ("﻿" + o.getvalue()).encode("utf-8")


def summary(old, new):
    names = lambda rows: {r[1]: r for r in rows[1:]}
    a, b = names(old), names(new)
    lines = []
    for n in b:
        if n not in a:
            lines.append("+ добавлен: %s" % n)
    for n in a:
        if n not in b:
            lines.append("- убран: %s" % n)
    pi = [c.strip().lower() for c in new[0]].index("цена")
    for n in b:
        if n in a and a[n][pi] != b[n][pi]:
            lines.append("~ %s: %s -> %s" % (n, a[n][pi] or "нет", b[n][pi] or "нет"))
    return lines


def set_output(changed):
    path = os.environ.get("GITHUB_OUTPUT")
    if path:
        with open(path, "a", encoding="utf-8") as f:
            f.write("changed=%s\n" % ("true" if changed else "false"))


def main():
    old_raw = open(TARGET, "rb").read()
    old_rows = read_rows(old_raw.decode("utf-8-sig"))
    new_rows = build(old_rows, fetch(sheet_url()))

    old_n, new_n = len(old_rows) - 1, len(new_rows) - 1
    old_p, new_p = priced(old_rows), priced(new_rows)
    print("товаров: было %d, стало %d; с ценой: было %d, стало %d" % (old_n, new_n, old_p, new_p))
    if os.environ.get("FORCE", "").strip() not in ("1", "true"):
        if old_n >= 10 and new_n < old_n * MIN_KEEP:
            fail("товаров стало слишком мало (%d из %d), файл не обновлён. Если так и задумано, запустите вручную с force" % (new_n, old_n))
        if old_p >= 10 and new_p < old_p * MIN_KEEP_PRICED:
            fail("цен стало слишком мало (%d из %d), файл не обновлён. Если так и задумано, запустите вручную с force" % (new_p, old_p))

    new_raw = serialize(new_rows)
    if new_raw == old_raw:
        print("Изменений нет, prices.csv не трогаем.")
        set_output(False)
        return
    with open(TARGET, "wb") as f:
        f.write(new_raw)
    print("prices.csv обновлён. Что изменилось:")
    for line in summary(old_rows, new_rows) or ["(только порядок строк или служебные колонки)"]:
        print("  " + line)
    set_output(True)


if __name__ == "__main__":
    main()
