"""Создаёт demo-cafe/: демо кофейни «Кофе и корица» с размерами напитков. Запуск: python3 tools/make_cafe.py
Размеры: у товаров поля group и size; в таблице каждый размер отдельной строкой (своя цена и наличие)."""
import os, io, json, shutil
from playwright.sync_api import sync_playwright
from PIL import Image
R = os.path.dirname(os.path.dirname(os.path.abspath(__file__))); D = os.path.join(R, "demo-cafe"); os.makedirs(D + "/img", exist_ok=True)
def q(x): return json.dumps(x, ensure_ascii=False)
# (имя, kk, раздел, вес, метки, состав, состав kk, цена, group, size, size_kk, картинка)
P = [
("Капучино 200 мл","Капучино 200 мл","Кофе","200 мл",["hit"],"Эспрессо, молоко.","Эспрессо, сүт.",900,"Капучино","200 мл","200 мл","cap"),
("Капучино 300 мл","Капучино 300 мл","Кофе","300 мл",["hit"],"Эспрессо, молоко.","Эспрессо, сүт.",1100,"Капучино","300 мл","300 мл","cap"),
("Капучино 400 мл","Капучино 400 мл","Кофе","400 мл",["hit"],"Эспрессо, молоко.","Эспрессо, сүт.",1300,"Капучино","400 мл","400 мл","cap"),
("Латте 300 мл","Латте 300 мл","Кофе","300 мл",[],"Эспрессо, молоко.","Эспрессо, сүт.",1200,"Латте","300 мл","300 мл","lat"),
("Латте 400 мл","Латте 400 мл","Кофе","400 мл",[],"Эспрессо, молоко.","Эспрессо, сүт.",1400,"Латте","400 мл","400 мл","lat"),
("Американо 200 мл","Американо 200 мл","Кофе","200 мл",[],"Эспрессо, вода.","Эспрессо, су.",700,"Американо","200 мл","200 мл","ame"),
("Американо 300 мл","Американо 300 мл","Кофе","300 мл",[],"Эспрессо, вода.","Эспрессо, су.",850,"Американо","300 мл","300 мл","ame"),
("Эспрессо","Эспрессо","Кофе","30 мл",[],"Эспрессо.","Эспрессо.",600,None,None,None,"esp"),
("Чай чёрный с лимоном","Лимонды қара шай","Чай и напитки","350 мл",[],"Чай чёрный, вода, лимон.","Қара шай, су, лимон.",800,None,None,None,"tea"),
("Какао","Какао","Чай и напитки","300 мл",[],"Какао, молоко, сахар.","Какао, сүт, қант.",1000,None,None,None,"coc"),
("Лимонад домашний","Үйдегі лимонад","Чай и напитки","400 мл",[],"Вода, лимон, мята, сахар.","Су, лимон, жалбыз, қант.",900,None,None,None,"lem"),
("Круассан сливочный","Сары майлы круассан","Десерты","80 г",["hit"],"Мука пшеничная, масло сливочное, молоко, сахар.","Бидай ұны, сары май, сүт, қант.",650,None,None,None,"cro"),
("Чизкейк Нью-Йорк","Нью-Йорк чизкейкі","Десерты","140 г",[],"Сыр сливочный, печенье песочное, сливки, сахар.","Кілегейлі ірімшік, құмды печенье, кілегей, қант.",1650,None,None,None,"che"),
("Эклер ванильный","Ваниль экленері","Десерты","90 г",[],"Мука пшеничная, молоко, яйца, сахар, ваниль.","Бидай ұны, сүт, жұмыртқа, қант, ваниль.",780,None,None,None,"ecl"),
("Овсяное печенье","Сұлы печеньесі","Десерты","60 г",[],"Хлопья овсяные, мука, сахар, масло, изюм.","Сұлы жармасы, ұн, қант, май, мейіз.",320,None,None,None,"coo"),
("Тыквенный латте 300 мл","Асқабақты латте 300 мл","Сезонное","300 мл",["new"],"Эспрессо, молоко, тыквенное пюре, корица.","Эспрессо, сүт, асқабақ езбесі, даршын.",1500,"Тыквенный латте","300 мл","300 мл","pum"),
("Тыквенный латте 400 мл","Асқабақты латте 400 мл","Сезонное","400 мл",["new"],"Эспрессо, молоко, тыквенное пюре, корица.","Эспрессо, сүт, асқабақ езбесі, даршын.",1700,"Тыквенный латте","400 мл","400 мл","pum"),
("Бизнес-ланч: суп и кофе","Бизнес-ланч: сорпа және кофе","Сезонное","",[],"Суп дня и американо 200 мл.","Күн сорпасы және американо 200 мл.",2400,None,None,None,"lun"),
]
CAT_KK = {"Кофе":"Кофе","Чай и напитки":"Шай және сусындар","Десерты":"Десерттер","Сезонное":"Маусымдық"}
def cup(bg, liquid, foam=None, steam=False, small=False, extra=""):
    s = 0.62 if small else 1
    f = f'<path d="M0 0 h200 l-24 190 q-76 24 -152 0 z" fill="#fff" stroke="#8a5a3b" stroke-width="7"/><path d="M8 28 h184 l-12 120 q-80 18 -160 0z" fill="{liquid}"/>'
    if foam: f += f'<path d="M12 28 h176 l-5 40 q-83 14 -166 0z" fill="{foam}"/>'
    f += '<path d="M205 50 q55 10 40 60 q-10 30 -48 30" fill="none" stroke="#8a5a3b" stroke-width="12" stroke-linecap="round"/>'
    st = '<path d="M60 -30 q-14 -22 0 -44 M100 -30 q-14 -22 0 -44 M140 -30 q-14 -22 0 -44" fill="none" stroke="#b9a58f" stroke-width="7" stroke-linecap="round"/>' if steam else ""
    return f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 560 560" width="560" height="560"><rect width="560" height="560" fill="{bg}"/><ellipse cx="280" cy="470" rx="170" ry="20" fill="#000" opacity=".08"/><g transform="translate({140 if not small else 170} {230 if not small else 280}) scale({s})">{st}{f}{extra}</g></svg>'
IMG = {
 "cap": cup("#efe3d6","#c78a56","#fff"), "lat": cup("#f3e6d8","#d9b48a","#fff"), "ame": cup("#e8ddd2","#4a2e1a",None,True),
 "esp": cup("#eadccc","#3a2212",None,True,True), "coc": cup("#f1e1d8","#7a4a32","#f6e3c0",True), "pum": cup("#f9e4cf","#d98a3a","#fff3de",True,False),
 "lun": '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 560 560" width="560" height="560"><rect width="560" height="560" fill="#f4ead8"/><ellipse cx="280" cy="470" rx="170" ry="20" fill="#000" opacity=".08"/><ellipse cx="280" cy="330" rx="190" ry="60" fill="#fff" stroke="#8a5a3b" stroke-width="7"/><path d="M110 320 q170 -90 340 0 q-30 70 -170 70 q-140 0 -170 -70z" fill="#d98a3a"/><circle cx="240" cy="310" r="12" fill="#6bb54a"/><circle cx="310" cy="300" r="12" fill="#6bb54a"/><circle cx="280" cy="330" r="10" fill="#f6e3c0"/></svg>',
}
SRC = {"tea": "11", "lem": "12", "cro": "04", "che": "07", "ecl": "08", "coo": "09"}
out = ["/* products.js — ДЕМО кофейни «Кофе и корица». Размеры: group и size, каждый размер отдельной строкой в таблице. */", "const PRODUCTS = ["]
names = {}
for i, (n, nk, c, w, l, cp, ck, pr, g, sz, szk, im) in enumerate(P, 1):
    names[im] = names.get(im) or f"{i:02d}"
    kk = {"name": nk, "composition": ck}
    if g: kk["group"] = {"Капучино": "Капучино", "Латте": "Латте", "Американо": "Американо", "Тыквенный латте": "Асқабақты латте"}[g]; kk["size"] = szk
    extra = f' group:{q(g)}, size:{q(sz)},' if g else ""
    out.append(f'  {{name:{q(n)}, brand:"", category:{q(c)}, weight:{q(w)}, price:null, labels:{q(l)},{extra} image:"img/{names[im]}.webp",\n   composition:{q(cp)}, shelfLife:"", nutrition:"",\n   kk:{q(kk)}}},')
out.append("];")
open(D + "/products.js", "w", encoding="utf-8").write("\n".join(out) + "\n")
rows = ["Раздел,Товар,Бренд,Цена,Акционная цена,Акция до,Метки,Изменено,Новинка с,Нет в наличии"]
for (n, nk, c, w, l, cp, ck, pr, g, sz, szk, im) in P:
    lab = ",".join({"hit": "Хит", "new": "Новинка"}[x] for x in l)
    ap, un, nc, ou = "", "", ("28.10.2026" if "new" in l else ""), ""
    if n == "Бизнес-ланч: суп и кофе": ap, un = "1900", "31.12.2026"
    if n == "Капучино 400 мл": ou = "да"
    rows.append(f"{c},{n},,{pr},{ap},{un},{lab},30.10.2026,{nc},{ou}")
open(D + "/prices.csv", "w", encoding="utf-8").write("\n".join(rows) + "\n")
cfg = open(os.path.join(R, "demo", "config.js"), encoding="utf-8").read()
cfg = cfg.replace("Тёплый хлеб", "Кофе и корица").replace('part1:"Тёплый ", part2:"хлеб"', 'part1:"Кофе и ", part2:"корица"').replace("наубайханасының", "кофейнясының")
cfg = cfg.replace('colors:{c1:"#d98a2b", c2:"#e8a23c", c3:"#c96a3a", c4:"#8a5a2b"}', 'colors:{c1:"#8a5a3b", c2:"#b9793d", c3:"#d98a3a", c4:"#6b4226"}')
import re
cfg = re.sub(r"const CAT_KK = .*\n", "const CAT_KK = " + q(CAT_KK) + ";\n", cfg)
cfg = re.sub(r"const CAT_WORD = .*\n", 'const CAT_WORD = {"Кофе":"Кофе","Чай и напитки":"Чай","Десерты":"Десерт","Сезонное":"Сезонное"};\n', cfg)
cfg = cfg.replace("вымышленной пекарни «Тёплый хлеб»", "вымышленной кофейни «Кофе и корица»").replace('address:"Астана, ул. Примерная, 1"', 'address:"Астана, ул. Примерная, 2"')
open(D + "/config.js", "w", encoding="utf-8").write(cfg)
m = open(os.path.join(R, "demo", "manifest.json"), encoding="utf-8").read().replace("Тёплый хлеб — демо каталога", "Кофе и корица — демо каталога").replace("Тёплый хлеб", "Кофе и корица").replace("вымышленной пекарни", "вымышленной кофейни")
open(D + "/manifest.json", "w", encoding="utf-8").write(m)
for f in ("icon-192.png", "icon-512.png", "apple-touch-icon.png"): shutil.copy2(os.path.join(R, "demo", f), os.path.join(D, f))
for k, v in SRC.items(): shutil.copy2(os.path.join(R, "demo", "img", v + ".webp"), os.path.join(D, "img", names[k] + ".webp"))
with sync_playwright() as p:
    b = p.chromium.launch(); pg = b.new_page(viewport={"width": 560, "height": 560})
    for k, v in IMG.items():
        pg.set_content(f"<style>*{{margin:0}}</style>{v}"); Image.open(io.BytesIO(pg.screenshot())).convert("RGB").save(os.path.join(D, "img", names[k] + ".webp"), quality=88)
    b.close()
# общий код
NOINDEX = '<meta name="robots" content="noindex,nofollow">'
shutil.copy2(os.path.join(R, "sw.js"), os.path.join(D, "sw.js"))
open(D + "/index.html", "w", encoding="utf-8").write(open(os.path.join(R, "index.html"), encoding="utf-8").read().replace('<meta charset="utf-8">', '<meta charset="utf-8">\n' + NOINDEX, 1))
shutil.copytree(os.path.join(R, "fonts"), D + "/fonts", dirs_exist_ok=True)
print("demo-cafe готово")
