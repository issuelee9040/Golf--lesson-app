from PIL import Image, ImageDraw, ImageFilter
import numpy as np

SRC = 'downloads/proplan-logos/logo-5-wordmark-dark.png'
OUT = 'golf-lesson-app/assets/'
BG = 17.0

im = Image.open(SRC).convert('RGB')
a = np.array(im).astype(np.float32)
r, g = a[:,:,0], a[:,:,1]
mx = a.max(axis=2)
emerald = (g - r) > 25
alpha = np.where(emerald, (g - BG) / (252.0 - BG), (mx - BG) / (255.0 - BG))
alpha = np.clip(alpha, 0.0, 1.0)
alpha[alpha < 0.06] = 0.0

def apply_color(color, mask):
    rgba = np.zeros((a.shape[0], a.shape[1], 4), dtype=np.uint8)
    rgba[:,:,0], rgba[:,:,1], rgba[:,:,2] = color
    rgba[:,:,3] = (np.where(mask, alpha, 0.0) * 255).astype(np.uint8)
    return Image.fromarray(rgba, 'RGBA')

# ── 깃발 엠블럼의 '깃대(기둥) 중심' 찾기 ─────────────────────────
# 깃발은 오른쪽으로 뻗어 있어 bbox만 가운데 두면 기둥이 왼쪽으로 밀려 보입니다.
# 그래서 기둥(폭이 좁은 세로획)의 x 중심과 컵(맨 아래 넓은 타원)의 중심을 기준으로 삼습니다.
def pole_center_x(mask):
    rows, cols = mask.shape
    ys, xs = np.where(mask)
    top, bot = ys.min(), ys.max()
    heights = bot - top + 1
    # 컵: 바닥에서 위로 15% 안에서 가장 넓은 행
    band = mask[bot - int(heights * 0.15):bot + 1]
    widths = band.sum(axis=1)
    cup_row = int(np.argmax(widths))
    cup_y = bot - int(heights * 0.15) + cup_row
    cup_xs = np.where(mask[cup_y])[0]
    cup_center = (cup_xs.min() + cup_xs.max()) / 2.0
    # 기둥: 컵 바로 위 ~ 깃발 아래쪽에서 폭이 좁은(<= 30px) 행들
    pole_centers, weights = [], []
    for y in range(top, cup_y - 2):
        xs_row = np.where(mask[y])[0]
        if len(xs_row) == 0 or len(xs_row) > 30:
            continue
        pole_centers.append((xs_row.min() + xs_row.max()) / 2.0)
        weights.append(len(xs_row))
    pole_center = float(np.average(pole_centers, weights=weights)) if pole_centers else cup_center
    return pole_center, cup_center

mark_mask = emerald & (alpha > 0.5)
word_mask = (~emerald) & (alpha > 0.5)
POLE_X, CUP_X = pole_center_x(mark_mask)
MARK_BB = apply_color((255,255,255), emerald).split()[3].getbbox()
_wys, _wxs = np.where(word_mask)
WORD_CENTER = (_wxs.min() + _wxs.max()) / 2.0
print('pole x %.1f / cup x %.1f / wordmark center %.1f' % (POLE_X, CUP_X, WORD_CENTER))

def shift_layer(layer, dx):
    if not dx:
        return layer
    out = Image.new('RGBA', layer.size, (0,0,0,0))
    out.paste(layer, (int(round(dx)), 0), layer)
    return out

def build(mark_rgb, word_rgb, name, pad=8):
    mk = apply_color(mark_rgb, emerald)
    wd = apply_color(word_rgb, ~emerald)
    mk = shift_layer(mk, WORD_CENTER - POLE_X)   # 워드마크 가운데에 깃대를 맞춤
    comp = Image.alpha_composite(Image.new('RGBA', mk.size, (0,0,0,0)), wd)
    comp = Image.alpha_composite(comp, mk)
    bb = comp.split()[3].getbbox()
    comp = comp.crop((max(0,bb[0]-pad), max(0,bb[1]-pad), min(comp.width,bb[2]+pad), min(comp.height,bb[3]+pad)))
    comp.save(OUT + name)
    return comp

lock_green = build((203, 249, 222), (255,255,255), 'proplan-lockup-green.png')
lock_black = build((52, 211, 153), (255,255,255), 'proplan-lockup-black.png')
# 밝은 바탕(그린 화이트 설정 탭 등)에 얹는 버전 — 진한 워드마크 + 브랜드 에메랄드 깃발
lock_light = build((15, 123, 74), (11,15,20), 'proplan-lockup-light.png')

def gradient(size, stops):
    base = Image.new('RGB', (size, size)); px = base.load()
    for y in range(size):
        for x in range(size):
            t = (x * 0.38 + y * 0.62) / size
            for i in range(len(stops)-1):
                t0, c0 = stops[i]; t1, c1 = stops[i+1]
                if t0 <= t <= t1:
                    f = (t - t0) / (t1 - t0)
                    px[x, y] = tuple(int(c0[k] + (c1[k]-c0[k])*f) for k in range(3)); break
    return base

S = 1024
bb = MARK_BB
mark_full = apply_color((255,255,255), emerald)
MARK_POLE_LOCAL = POLE_X - bb[0]          # 잘라낸 마크 안에서의 기둥 위치

def make_icon(stops, mark_rgb, scale_ratio, out_names, glow_alpha=(255,255,255,22)):
    bgimg = gradient(S, stops).convert('RGBA')
    m = apply_color(mark_rgb, emerald).crop(bb)
    sc = (S * scale_ratio) / m.width
    mw, mh = int(m.width*sc), int(m.height*sc)
    mr = m.resize((mw, mh), Image.LANCZOS)
    icon = bgimg.copy()
    glow = Image.new('RGBA', (S,S), (0,0,0,0))
    d = ImageDraw.Draw(glow)
    d.ellipse([S*0.10, S*0.04, S*0.90, S*0.80], fill=glow_alpha)
    glow = glow.filter(ImageFilter.GaussianBlur(90))
    icon = Image.alpha_composite(icon, glow)
    # 사각 아이콘 안에서도 기둥이 정확히 가운데
    x = int(round(S/2 - MARK_POLE_LOCAL * sc))
    icon.alpha_composite(mr, (x, (S-mh)//2))
    icon = icon.convert('RGB')
    for sz, nm in out_names:
        icon.resize((sz, sz), Image.LANCZOS).save(OUT + nm)
    return icon

make_icon([(0.0,(18,138,83)),(0.62,(12,107,65)),(1.0,(8,73,44))], (255,255,255), 0.455,
          [(512,'icon-512.png'),(192,'icon-192.png'),(180,'apple-touch-icon.png'),(64,'icon-64.png'),(32,'favicon-32.png')])
make_icon([(0.0,(28,28,32)),(0.55,(22,22,24)),(1.0,(15,15,17))], (52,211,153), 0.455,
          [(512,'icon-black-512.png')], glow_alpha=(70,214,156,20))
print('assets rebuilt')
