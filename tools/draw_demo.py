"""Рисует иллюстрации для демо (demo/img/NN.webp и иконки). Запуск: python3 tools/draw_demo.py"""
import os, io
from playwright.sync_api import sync_playwright
from PIL import Image
R=os.path.dirname(os.path.dirname(os.path.abspath(__file__))); D=os.path.join(R,"demo")
def svg(bg,body): return f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 560 560" width="560" height="560"><rect width="560" height="560" fill="{bg}"/><ellipse cx="280" cy="470" rx="170" ry="20" fill="#000" opacity=".08"/>{body}</svg>'
BR,BR2,CR="#d9a05b","#b97a35","#f6e3c0"
A={}
A[1]=svg("#fbeed6",f'<g transform="rotate(-18 280 300)"><rect x="70" y="230" width="420" height="120" rx="60" fill="{BR}" stroke="{BR2}" stroke-width="6"/>'+"".join(f'<path d="M{110+i*80} 250 l36 -4 l-14 56 z" fill="{CR}" stroke="{BR2}" stroke-width="3" transform="translate(0 20)"/>' for i in range(5))+'</g>')
A[2]=svg("#f1e4d3",'<rect x="110" y="190" width="340" height="190" rx="70" fill="#7a4f2a" stroke="#4e3119" stroke-width="6"/><path d="M110 270 q170 -50 340 0" fill="none" stroke="#4e3119" stroke-width="5"/>'+"".join(f'<circle cx="{170+i*55}" cy="{235+(i%2)*40}" r="6" fill="#e2c28f"/>' for i in range(5)))
A[3]=svg("#eef0dc",f'<path d="M90 360 q-10 -140 120 -170 q120 -40 250 20 q20 120 -20 150 z" fill="{BR}" stroke="{BR2}" stroke-width="6"/>'+"".join(f'<ellipse cx="{200+i*70}" cy="{270+(i%2)*30}" rx="22" ry="14" fill="#4f5f2a"/><circle cx="{200+i*70}" cy="{270+(i%2)*30}" r="5" fill="#e8d98c"/>' for i in range(4)))
A[4]=svg("#fbe9d0",f'<path d="M80 340 q10 -190 200 -190 q190 0 200 190 q-100 40 -200 10 q-100 30 -200 -10z" fill="{BR}" stroke="{BR2}" stroke-width="6"/>'+"".join(f'<path d="M{150+i*65} 180 q-30 80 {-10+i*8} 160" fill="none" stroke="{BR2}" stroke-width="7" stroke-linecap="round"/>' for i in range(5)))
import math
_pts=" ".join(f"{280+r*math.cos(t):.1f},{270+r*math.sin(t):.1f}" for t in [k*0.25 for k in range(0,90)] for r in [4+t*3.6])
A[5]=svg("#f6e2d0",f'<circle cx="280" cy="270" r="150" fill="#d9954a" stroke="#8a5224" stroke-width="6"/><polyline points="{_pts}" fill="none" stroke="#7a3f1a" stroke-width="14" stroke-linecap="round" stroke-linejoin="round"/><circle cx="280" cy="270" r="150" fill="none" stroke="#f5d9b0" stroke-width="8" opacity=".4"/>')
A[6]=svg("#f3e6d0",f'<path d="M80 360 Q280 80 480 360 Z" fill="{BR}" stroke="{BR2}" stroke-width="6"/><path d="M130 330 Q280 160 430 330" fill="none" stroke="{CR}" stroke-width="8" stroke-dasharray="4 18" stroke-linecap="round"/><circle cx="280" cy="260" r="16" fill="{CR}"/><circle cx="240" cy="300" r="10" fill="{CR}"/><circle cx="320" cy="300" r="10" fill="{CR}"/>')
A[7]=svg("#fbe6ee",'<path d="M120 380 L280 150 L440 380 Z" fill="#f7e3b0" stroke="#d3a85a" stroke-width="6"/><rect x="120" y="360" width="320" height="30" fill="#b9793d" stroke="#8a5224" stroke-width="5" rx="6"/><path d="M200 255 q40 20 80 -5 q40 20 80 10" fill="none" stroke="#e9576f" stroke-width="12" stroke-linecap="round"/><circle cx="280" cy="140" r="16" fill="#e9576f"/>')
A[8]=svg("#eadff0",'<rect x="90" y="250" width="380" height="110" rx="55" fill="#d9a05b" stroke="#b97a35" stroke-width="6"/><path d="M95 275 q185 -50 370 0 q-10 40 -60 40 q-60 -30 -125 0 q-60 -30 -120 0 q-55 5 -65 -40z" fill="#6b4226"/><path d="M110 262 q170 -30 340 0" fill="none" stroke="#f6e3c0" stroke-width="8" stroke-linecap="round" opacity=".7"/>')
A[9]=svg("#f7ebcf","".join(f'<circle cx="{x}" cy="{y}" r="86" fill="#d9a05b" stroke="#a8692b" stroke-width="6"/>'+"".join(f'<circle cx="{x+dx}" cy="{y+dy}" r="9" fill="#6b4226"/>' for dx,dy in((-30,-24),(26,-34),(-8,14),(34,22),(-40,32))) for x,y in((200,300),(350,250),(350,380))))
A[10]=svg("#efe3d6",'<path d="M180 230 h200 l-24 190 q-76 24 -152 0 z" fill="#fff" stroke="#8a5a3b" stroke-width="7"/><path d="M174 230 h212 v-24 h-212 z" fill="#f4efe6" stroke="#8a5a3b" stroke-width="7" rx="6"/><path d="M184 250 h192 l-12 56 h-168 z" fill="#c78a56"/><path d="M215 270 q35 -22 65 0 q35 -22 65 0" fill="none" stroke="#fff" stroke-width="8" stroke-linecap="round"/><path d="M386 270 q55 10 40 60 q-10 30 -48 30" fill="none" stroke="#8a5a3b" stroke-width="12" stroke-linecap="round"/>'.replace('rx="6"',''))
A[11]=svg("#f8e8d2",'<path d="M200 230 h160 l-18 190 h-124 z" fill="#f6ede0" stroke="#8a5a3b" stroke-width="7"/><path d="M206 260 h148 l-14 150 h-120z" fill="#b5541f" opacity=".92"/><circle cx="330" cy="205" r="52" fill="#f4d34a" stroke="#c9a41f" stroke-width="6"/><circle cx="330" cy="205" r="28" fill="#fbe98a"/><rect x="266" y="130" width="12" height="100" rx="6" fill="#d9d2c4" transform="rotate(18 272 180)"/>')
A[12]=svg("#e4f1dc",'<path d="M190 180 h180 l-16 250 h-148 z" fill="#f4fbe6" stroke="#6f9a4a" stroke-width="7" opacity=".95"/><path d="M200 230 h160 l-12 190 h-136z" fill="#f2e56a" opacity=".9"/><circle cx="260" cy="290" r="14" fill="#fff" opacity=".6"/><circle cx="305" cy="340" r="10" fill="#fff" opacity=".6"/><path d="M290 190 q-10 -55 30 -80 q30 50 -30 80z" fill="#4f9a3a"/><path d="M320 185 q40 -40 70 -20 q-10 40 -70 20z" fill="#6bb54a"/><circle cx="170" cy="400" r="40" fill="#f4d34a" stroke="#c9a41f" stroke-width="6"/>')
icon=svg("#e8a23c",f'<g transform="translate(0 20) scale(1)"><path d="M80 380 q10 -190 200 -190 q190 0 200 190 q-100 40 -200 10 q-100 30 -200 -10z" fill="#fff4dc" stroke="#8a5224" stroke-width="14"/>'+"".join(f'<path d="M{150+i*65} 220 q-30 80 {-10+i*8} 160" fill="none" stroke="#c9833f" stroke-width="14" stroke-linecap="round"/>' for i in range(5))+'</g>')
with sync_playwright() as p:
    b=p.chromium.launch(); pg=b.new_page(viewport={"width":560,"height":560})
    for k,v in A.items():
        pg.set_content(f"<style>*{{margin:0}}</style>{v}"); png=pg.screenshot()
        Image.open(io.BytesIO(png)).convert("RGB").save(os.path.join(D,"img",f"{k:02d}.webp"),quality=88)
    pg.set_content(f"<style>*{{margin:0}}</style>{icon}"); png=Image.open(io.BytesIO(pg.screenshot())).convert("RGB")
    png.resize((512,512)).save(os.path.join(D,"icon-512.png")); png.resize((192,192)).save(os.path.join(D,"icon-192.png")); png.resize((180,180)).save(os.path.join(D,"apple-touch-icon.png"))
    b.close()
print("нарисовано")
