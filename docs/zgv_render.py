# ZEUS GUARD - renderizador de video estilo Animalex (PIL -> ffmpeg)
import math, subprocess, sys, time
from PIL import Image, ImageDraw, ImageFont

W, H, FPS = 1280, 720, 12
TOTAL = 185  # segundos
F = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
def font(sz): return ImageFont.truetype(F, sz)
FB = font(30); FBIG = font(64); FMID = font(44); FEMB = font(40); FSM = font(26)

SKY=(126,200,240); GND=(122,199,79); NAVY=(12,20,44); GOLD=(245,185,66); GOLD2=(184,134,11)
RED=(224,68,68); SHIRT=(255,210,63); PANTS=(42,77,143); SKIN=(255,207,158); HAIR=(20,20,20)
WHITE=(255,255,255); BLACK=(15,15,15); OUT=(4,4,4)

def wrap(d, txt, f, maxw):
    words, lines, cur = txt.split(), [], ""
    for w_ in words:
        t = (cur+" "+w_).strip()
        if d.textlength(t, font=f) <= maxw: cur = t
        else: lines.append(cur); cur = w_
    if cur: lines.append(cur)
    return lines

def caption(d, txt):
    lines = wrap(d, txt, FB, 1100)
    bh = 52 + len(lines)*40
    y0 = H - bh - 18
    d.rounded_rectangle([90,y0,W-90,y0+bh], 24, fill=(255,250,235), outline=OUT, width=5)
    y = y0+22
    for ln in lines:
        tw = d.textlength(ln, font=FB)
        d.text(((W-tw)/2, y), ln, font=FB, fill=BLACK); y += 40

def burst(d, cx, cy, txt, col=RED, s=1.0, rot=0):
    n, r1, r2 = 14, 86*s, 52*s
    pts=[]
    for i in range(n*2):
        ang = math.pi*i/n + rot
        r = r1 if i%2==0 else r2
        pts.append((cx+r*math.sin(ang), cy+r*math.cos(ang)))
    d.polygon(pts, fill=GOLD, outline=OUT)
    d.polygon([(p[0]*0.94+(cx*0.06), p[1]*0.94+(cy*0.06)) for p in pts], fill=(255,225,120))
    tw = d.textlength(txt, font=FEMB)
    d.text((cx-tw/2, cy-24), txt, font=FEMB, fill=col)

def sun(d, t):
    d.ellipse([1080,60,1180,160], fill=(255,220,80), outline=OUT, width=5)
    for i in range(8):
        a = t*0.4 + i*math.pi/4
        x1,y1 = 1130+70*math.cos(a), 110+70*math.sin(a)
        d.line([x1,y1,x1+26*math.cos(a),y1+26*math.sin(a)], fill=GOLD, width=6)

def cloud(d, x, y, s=1.0):
    d.ellipse([x,y,x+120*s,y+50*s], fill=WHITE, outline=OUT, width=4)
    d.ellipse([x+70*s,y-30*s,x+180*s,y+40*s], fill=WHITE, outline=OUT, width=4)
    d.ellipse([x-60*s,y+8*s,x+60*s,y+58*s], fill=WHITE, outline=OUT, width=4)

def ground(d):
    d.rectangle([0,600,W,H], fill=GND, outline=None)
    d.line([0,600,W,600], fill=OUT, width=6)
    for x in range(40, W, 130): d.ellipse([x,596,x+26,604], fill=(90,160,55))

def head(d, cx, cy, mood, ph=0.0, s=1.0):
    r = 46*s
    d.ellipse([cx-r,cy-r,cx+r,cy+r], fill=SKIN, outline=OUT, width=5)
    if mood=="panic":  # cabelo espetado
        for i in range(9):
            a = -math.pi + i*math.pi/8
            x2,y2 = cx+math.cos(a)*r*1.55, cy+math.sin(a)*r*1.55
            x1,y1 = cx+math.cos(a)*r*0.9, cy+math.sin(a)*r*0.9
            d.line([x1,y1,x2,y2], fill=HAIR, width=9)
    else:
        d.pieslice([cx-r-4,cy-r-6,cx+r+4,cy+r*0.35], 180, 360, fill=HAIR, outline=OUT, width=4)
        d.ellipse([cx-r*0.55,cy-r*1.05,cx+r*0.55,cy-r*0.25], fill=HAIR)  # topo
    ey = cy-6
    if mood=="panic":
        d.ellipse([cx-26,ey-14,cx-2,ey+12], fill=WHITE, outline=OUT, width=3)
        d.ellipse([cx+2,ey-14,cx+26,ey+12], fill=WHITE, outline=OUT, width=3)
        d.ellipse([cx-17,ey-5,cx-10,ey+2], fill=BLACK); d.ellipse([cx+10,ey-5,cx+17,ey+2], fill=BLACK)
        d.ellipse([cx-10,cy+14,cx+10,cy+34], fill=(120,30,30), outline=OUT, width=3)  # grito
        d.line([cx-30,cy-26,cx-14,cy-20], fill=OUT, width=4); d.line([cx+30,cy-26,cx+14,cy-20], fill=OUT, width=4)
    else:
        d.ellipse([cx-24,ey-12,cx-4,ey+10], fill=WHITE, outline=OUT, width=3)
        d.ellipse([cx+4,ey-12,cx+24,ey+10], fill=WHITE, outline=OUT, width=3)
        d.ellipse([cx-16,ey-4,cx-8,ey+4], fill=BLACK); d.ellipse([cx+8,ey-4,cx+16,ey+4], fill=BLACK)
        d.arc([cx-12,cy+6,cx+12,cy+26], 20, 160, fill=OUT, width=4)

def body(d, cx, cy, mood, ph=0.0, s=1.0):
    bob = abs(math.sin(ph))*7
    hy = cy+bob
    if mood=="panic":
        head(d, cx, hy-70, "panic", s)
        d.rounded_rectangle([cx-34,hy-30,cx+34,hy+52], 14, fill=SHIRT, outline=OUT, width=5)
        d.line([cx-34,hy-20,cx-66,hy-66], fill=SHIRT, width=18)  # braco p/ cima
        d.line([cx-66,hy-66,cx-74,hy-72], fill=SKIN, width=14)
        d.line([cx+34,hy-20,cx+66,hy-66], fill=SHIRT, width=18)
        d.line([cx+66,hy-66,cx+74,hy-72], fill=SKIN, width=14)
        d.line([cx-14,hy+52,cx-18,hy+96], fill=PANTS, width=20)
        d.line([cx+14,hy+52,cx+18,hy+96], fill=PANTS, width=20)
        d.ellipse([cx-24,hy+90,cx-6,hy+104], fill=WHITE, outline=OUT, width=4)
        d.ellipse([cx+6,hy+90,cx+24,hy+104], fill=WHITE, outline=OUT, width=4)
    else:
        head(d, cx, hy-70, "smile", ph, s)
        d.rounded_rectangle([cx-34,hy-30,cx+34,hy+52], 14, fill=SHIRT, outline=OUT, width=5)
        sw = math.sin(ph)*16
        d.line([cx-34,hy-16,cx-58,hy+26+sw], fill=SHIRT, width=16)
        d.line([cx+34,hy-16,cx+58,hy+26-sw], fill=SHIRT, width=16)
        d.ellipse([cx-64,hy+20+sw,cx-48,hy+36+sw], fill=SKIN, outline=OUT, width=3)
        d.ellipse([cx+48,hy+20-sw,cx+64,hy+36-sw], fill=SKIN, outline=OUT, width=3)
        d.line([cx-14,hy+52,cx-16+sw*0.3,hy+92], fill=PANTS, width=20)
        d.line([cx+14,hy+52,cx+16-sw*0.3,hy+92], fill=PANTS, width=20)
        d.ellipse([cx-28+sw*3,hy+88,cx-6+sw*3,hy+102], fill=WHITE, outline=OUT, width=4)
        d.ellipse([cx+6-sw*3,hy+88,cx+28-sw*3,hy+102], fill=WHITE, outline=OUT, width=4)
    # logo escudo na camiseta
    d.polygon([(cx-12,hy-16),(cx+12,hy-16),(cx+12,hy+2),(cx,hy+12),(cx-12,hy+2)], fill=GOLD, outline=GOLD2, width=2)
    d.polygon([(cx-2,hy-12),(cx+6,hy-12),(cx+1,hy-4),(cx+6,hy-4),(cx-3,hy+8),(cx,hy+0),(cx-5,hy+0)], fill=NAVY)

def villain(d, x, y, zap=False, cry=False):
    d.line([x+40,y,x+300,y], fill=(60,50,60), width=34)
    d.ellipse([x-40,y-40,x+46,y+46], fill=(80,65,80), outline=OUT, width=5)
    for i in range(3):
        d.line([x-20+i*22,y+18,x-32+i*26,y+52], fill=(80,65,80), width=12)
    if zap:
        for i in range(5):
            d.line([x-10+i*10,y-46,x-16+i*12,y-8], fill=(255,240,80), width=5)
    if cry:
        for i in range(3):
            d.ellipse([x-26+i*20,y+58+((i*13)%20),x-14+i*20,y+74+((i*13)%20)], fill=(120,190,255))

def approve_btn(d, cx, cy, pulse):
    r = 54+pulse*8
    d.ellipse([cx-r,cy-r,cx+r,cy+r], fill=RED, outline=OUT, width=6)
    d.ellipse([cx-r*0.72,cy-r*0.72,cx+r*0.72,cy+r*0.72], fill=(255,120,110))
    tw = d.textlength("APPROVE", font=FSM)
    d.text((cx-tw/2, cy-14), "APPROVE", font=FSM, fill=WHITE)

def coins_fly(d, t01, x0,y0, x1,y1, n=8):
    for i in range(n):
        p = min(1.0, max(0.0, (t01 - i*0.04)/(0.5)))
        if p<=0 or p>=1: continue
        e = p*p*(3-2*p)
        x = x0+(x1-x0)*e + math.sin(p*math.pi*3)*40
        y = y0+(y1-y0)*e - math.sin(p*math.pi)*120
        d.ellipse([x-14,y-14,x+14,y+14], fill=GOLD, outline=GOLD2, width=3)
        tw = d.textlength("G", font=FSM); d.text((x-tw/2,y-13), "G", font=FSM, fill=NAVY)

def big_shield(d, cx, cy, s, glow=False):
    if glow:
        d.ellipse([cx-110*s,cy-130*s,cx+110*s,cy+130*s], fill=(255,225,120))
    d.polygon([(cx-90*s,cy-110*s),(cx+90*s,cy-110*s),(cx+90*s,cy+20*s),(cx,cy+110*s),(cx-90*s,cy+20*s)],
              fill=GOLD, outline=OUT, width=6)
    d.polygon([(cx-60*s,cy-80*s),(cx+60*s,cy-80*s),(cx+60*s,cy+5*s),(cx,cy+75*s),(cx-60*s,cy+5*s)], fill=(255,215,110))
    bolt=[(cx-12*s,cy-70*s),(cx+18*s,cy-70*s),(cx+2*s,cy-18*s),(cx+26*s,cy-18*s),(cx-14*s,cy+62*s),(cx+2*s,cy-2*s),(cx-24*s,cy-2*s)]
    d.polygon(bolt, fill=NAVY)

def panel(d, x, y, w, h, title, kind, t):
    d.rounded_rectangle([x,y,x+w,y+h], 16, fill=(255,250,235), outline=OUT, width=6)
    tw = d.textlength(title, font=FSM); d.text((x+(w-tw)/2, y+14), title, font=FSM, fill=NAVY)
    cx, cy = x+w/2, y+h/2+22
    if kind=="block":
        r=44; d.ellipse([cx-r,cy-r,cx+r,cy+r], fill=RED, outline=OUT, width=5)
        d.line([cx-22,cy-22,cx+22,cy+22], fill=WHITE, width=10)
        d.line([cx+22,cy-22,cx-22,cy+22], fill=WHITE, width=10)
        s=1+0.08*math.sin(t*8);
        d.polygon([(cx-70*s,cy-40*s),(cx+70*s,cy-40*s),(cx+70*s,cy+40*s),(cx-70*s,cy+40*s)], outline=RED, width=6)
    if kind=="revoke":
        d.rectangle([cx-70,cy-40,cx+50,cy+30], fill=(250,245,230), outline=OUT, width=4)
        d.line([cx-55,cy-20,cx+30,cy-20], fill=(150,150,150), width=4)
        d.line([cx-55,cy,cx+30,cy], fill=(150,150,150), width=4)
        d.line([cx+30,cy-34,cx+72,cy+44], fill=RED, width=12)
        d.line([cx+72,cy-34,cx+30,cy+44], fill=RED, width=12)
    if kind=="vault":
        d.rectangle([cx-60,cy-46,cx+60,cy+46], fill=(90,80,110), outline=OUT, width=5)
        d.ellipse([cx-16,cy-10,cx+16,cy+22], fill=GOLD, outline=OUT, width=4)
        for i in range(4): d.line([cx-60+i*20,cy-46,cx-60+i*20,cy+46], fill=OUT, width=3)
        cd = 30-int(t*4)%30
        t2 = f"T-{cd}s"; tw2=d.textlength(t2,font=FSM); d.text((cx-tw2/2, y+h-42), t2, font=FSM, fill=RED)

def landscape(d, t):
    d.rectangle([0,0,W,H], fill=NAVY)
    for i in range(7):
        yb = 140+i*80
        d.line([0,yb,W,yb], fill=(40,60,110), width=3)
    for i in range(9):
        x0 = 80+i*130
        d.line([x0, 620, x0+60-140*((i%2)*2-1)*0.3, 140+ (i%5)*80], fill=(60,90,150), width=4)
    gx = 300+ (t%4)*160
    d.line([gx,620,gx+40,300], fill=GOLD, width=8)
    d.ellipse([gx+20,270,gx+70,320], fill=GOLD, outline=(255,240,150), width=4)
    tw = d.textlength("~1 ms", font=FBIG); d.text(((W-tw)/2, 80), "~1 ms", font=FBIG, fill=GOLD)
    tw = d.textlength("selecao dissipativa da ameaca dominante", font=FSM)
    d.text(((W-tw)/2, 160), "selecao dissipativa da ameaca dominante", font=FSM, fill=(180,200,255))

def frame(t):
    img = Image.new("RGB",(W,H),SKY); d = ImageDraw.Draw(img)
    ph = t*6.0
    if t < 22:   # CENA 1 - passeio feliz
        sun(d,t); cloud(d, 150+((t*12)%1400), 90, 0.9); cloud(d, 700-((t*8)%500), 150, 0.7); ground(d)
        x = 120 + (t/22)*760
        body(d, x, 460, "smile", ph)
        for i in range(3): d.ellipse([x-8, 446-i*24, x+16, 470-i*24], fill=GOLD, outline=GOLD2, width=2)
        caption(d, "Todo dia, o Clebson entra na chain todo feliz...")
    elif t < 48:  # CENA 2 - botao APPROVE
        sun(d,t); ground(d); cloud(d, 180, 90)
        vx = W - 40 - max(0,(t-22))*22
        villain(d, vx, 300)
        approve_btn(d, vx-90, 380, 0.5+0.5*math.sin(t*6))
        body(d, 120+(t-22)/26*560, 460, "smile", ph)
        caption(d, "Aí aparece UM botãozinho 'APPROVE', docinho assim, ofertando renda...")
    elif t < 72:  # CENA 3 - TOCOU!
        sun(d,t); ground(d)
        villain(d, W-160, 300, cry=True)
        coins_fly(d, (t-48)/10, 420, 440, W-200, 320, 10)
        body(d, 420, 450, "panic", ph*0.3)
        if 50 < t < 60: burst(d, 640, 180, "NÃO TOCA!!", RED, 1.0, 0.2)
        caption(d, "ELE TOCOU. Bilhões somem por ano com drainer, endereço falso e approval envenenado.")
    elif t < 102:  # CENA 4 - trovao + escudo
        d.rectangle([0,0,W,H], fill=(60,70,110))
        for i in range(5): cloud(d, 60+i*260, 40+((i*37)%60), 1.3)
        ground(d)
        drop = min(1.0, (t-72)/8)
        sy = -150 + drop*320
        if (t-72) < 8 and int(t*6)%2==0:
            d.line([640,0,600,300], fill=(255,240,80), width=10)
            d.line([600,300,660,480], fill=(255,240,80), width=10)
        big_shield(d, 640, 320, 1.0, glow=True)
        villain(d, 1080, 300, zap=True, cry=True)
        if 80 < t < 92: burst(d, 400, 150, "BOOM!", NAVY, 1.1, 0.4)
        body(d, 300, 470, "panic" if t<80 else "smile", ph*0.4)
        caption(d, "Mas o universo tinha um plano: ZEUS GUARD, o firewall pré-transação.")
    elif t < 142:  # CENA 5 - modulos em paineis
        d.rectangle([0,0,W,H], fill=(150,210,245)); d.rectangle([0,560,W,H], fill=GND)
        big_shield(d, 640, 90, 0.55, glow=True)
        sl = [(t-102)/4,(t-106)/4,(t-110)/4]
        for i,(p, ttl, kind) in enumerate(zip(sl, ["FIREWALL","AUTO-REVOCACAO","COFRE USDG"], ["block","revoke","vault"])):
            if p>0:
                e=min(1,p); off=(1-e)*80
                panel(d, 60+i*410, 190+off, 340, 330, ttl, kind, t)
        caption(d, "Approval perigoso? BLOQUEADO. Revogado na hora. E o USDG fica no cofre com trava temporal.")
    elif t < 162:  # CENA 6 - motor
        landscape(d, t)
        caption(d, "Motor validado em hardware quântico da IBM: a ameaça dominante em ~1 milissegundo.")
    else:  # CENA 7 - outro
        d.rectangle([0,0,W,H], fill=NAVY)
        for i in range(30): d.ellipse([ (i*173)%W, (i*97)%500, (i*173)%W+4, (i*97)%500+4], fill=(220,230,255))
        d.rectangle([0,560,W,H], fill=(30,45,80))
        body(d, 380, 470, "smile", ph*0.5)
        big_shield(d, 820, 300, 1.1, glow=True)
        tw = d.textlength("ZEUS GUARD", font=FBIG); d.text(((W-tw)/2, 40), "ZEUS GUARD", font=FBIG, fill=GOLD)
        tw = d.textlength("O GUARDA-COSTAS ON-CHAIN", font=FMID); d.text(((W-tw)/2, 120), "O GUARDA-COSTAS ON-CHAIN", font=FMID, fill=WHITE)
        n = int((t-162)*470)
        txt = f"AMEAÇAS BLOQUEADAS: {n}"
        tw = d.textlength(txt, font=FMID); d.text(((W-tw)/2, 185), txt, font=FMID, fill=GOLD)
        caption(d, "Clebson Campos de Araújo · Arbitrum Open House Singapura 2026 · Robinhood Chain")
    return img

def main(mode):
    if mode=="smoke":
        for i in range(24): frame(i/12).save(f"smoke_{i:04d}.png")
        print("SMOKE OK"); return
    proc = subprocess.Popen(["ffmpeg","-y","-f","rawvideo","-pix_fmt","rgb24","-s",f"{W}x{H}",
        "-r",str(FPS),"-i","-","-c:v","libx264","-preset","veryfast","-crf","25","-pix_fmt","yuv420p",
        "ZEUS_GUARD_explainer.mp4"], stdin=subprocess.PIPE, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    n = int(TOTAL*FPS); t0=time.time()
    for i in range(n):
        img = frame(i/FPS)
        proc.stdin.write(img.tobytes())
        if i % 240 == 0: print(f"{i}/{n} frames ({time.time()-t0:.0f}s)", flush=True)
    proc.stdin.close(); proc.wait()
    print(f"DONE {n} frames em {time.time()-t0:.0f}s -> ZEUS_GUARD_explainer.mp4", flush=True)

main(sys.argv[1])
