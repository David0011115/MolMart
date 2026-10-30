"""QR-коды для столиков кафе (печать на A4, по 6 штук на лист).
Запуск: python3 tools/make_table_qr.py <адрес сайта> <число столиков> <выходной.pdf> [название заведения]
Пример: python3 tools/make_table_qr.py https://david0011115.github.io/MolMart/demo-cafe/ 10 qr-stoliki.pdf "Кофе и корица"
Адрес в QR: <сайт>?table=N. Номер столика видно на сайте и на экране для кассира, он попадает в статистику Метрики."""
import sys, glob
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.graphics.barcode import qr
from reportlab.graphics.shapes import Drawing
from reportlab.graphics import renderPDF
site, n, out = sys.argv[1].rstrip("/") + "/", int(sys.argv[2]), sys.argv[3]
name = sys.argv[4] if len(sys.argv) > 4 else ""
reg = (glob.glob("/usr/share/fonts/**/DejaVuSans.ttf", recursive=True) or [None])[0]
bold = (glob.glob("/usr/share/fonts/**/DejaVuSans-Bold.ttf", recursive=True) or [None])[0]
pdfmetrics.registerFont(TTFont("R", reg)); pdfmetrics.registerFont(TTFont("B", bold))
W, H = A4; c = canvas.Canvas(out, pagesize=A4); cw, ch = W / 2, H / 3
for i in range(n):
    k = i % 6
    if i and k == 0: c.showPage()
    x0, y0 = (k % 2) * cw, H - (k // 2 + 1) * ch
    c.setDash(3, 3); c.setStrokeColorRGB(.7, .7, .7); c.rect(x0 + 8, y0 + 8, cw - 16, ch - 16)
    c.setDash(); c.setFillColorRGB(.17, .13, .09)
    if name: c.setFont("R", 11); c.drawCentredString(x0 + cw / 2, y0 + ch - 34, name)
    c.setFont("B", 26); c.drawCentredString(x0 + cw / 2, y0 + ch - 66, f"Столик {i + 1}")
    w = qr.QrCodeWidget(f"{site}?table={i + 1}", barLevel="M"); b = w.getBounds(); size = 150
    d = Drawing(size, size, transform=[size / (b[2] - b[0]), 0, 0, size / (b[3] - b[1]), 0, 0]); d.add(w)
    renderPDF.draw(d, c, x0 + cw / 2 - size / 2, y0 + 62)
    c.setFont("R", 11); c.drawCentredString(x0 + cw / 2, y0 + 40, "Наведите камеру: меню, состав, цены")
    c.setFont("R", 9); c.setFillColorRGB(.45, .4, .35); c.drawCentredString(x0 + cw / 2, y0 + 24, "Мәзір, құрамы, бағалары")
c.save(); print("готово:", out)
