# -*- coding: utf-8 -*-
"""ProPlan 로고 자산 생성기 — 세로 락업 3종 + 홈화면 아이콘.

원본: downloads/proplan-logos/logo-5-wordmark-dark.png (깃발 엠블럼 + ProPlan 워드마크)

- 락업(proplan-lockup-*.png): 스플래시 · 온보딩 · 설정 하단용 세로 배치.
  깃발은 기둥(pole)이 워드마크 가로 중심에 오도록 옮겨 합성합니다.
- 아이콘(apple-touch-icon · icon-*): 깃발을 위쪽 가운데에, `ProPlan` 워드마크를
  그 아래 정중앙에 놓습니다 (2026-11-23 사용자 요청).
  iOS 가 모서리를 둥글게 깎으므로 내용은 가운데 60% 폭 안에만 둡니다.
"""
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
word_mask[:660, :] = False          # 깃발 컵의 반투명 가장자리가 섞이지 않게 워드마크만
POLE_X, CUP_X = pole_center_x(mark_mask)
MARK_BB = apply_color((255, 255, 255), emerald).split()[3].getbbox()
_wys, _wxs = np.where(word_mask)
WORD_BB = (int(_wxs.min()), int(_wys.min()), int(_wxs.max()) + 1, int(_wys.max()) + 1)
WORD_CENTER = (_wxs.min() + _wxs.max()) / 2.0
print('pole x %.1f / cup x %.1f / wordmark center %.1f' % (POLE_X, CUP_X, WORD_CENTER))


def shift_layer(layer, dx):
    if not dx:
        return layer
    out = Image.new('RGBA', layer.size, (0, 0, 0, 0))
    out.paste(layer, (int(round(dx)), 0), layer)
    return out


def build(mark_rgb, word_rgb, name, pad=8):
    mk = apply_color(mark_rgb, emerald)
    wd = apply_color(word_rgb, ~emerald)
    mk = shift_layer(mk, WORD_CENTER - POLE_X)   # 워드마크 가운데에 깃대를 맞춤
    comp = Image.alpha_composite(Image.new('RGBA', mk.size, (0, 0, 0, 0)), wd)
    comp = Image.alpha_composite(comp, mk)
    bb = comp.split()[3].getbbox()
    comp = comp.crop((max(0, bb[0] - pad), max(0, bb[1] - pad), min(comp.width, bb[2] + pad), min(comp.height, bb[3] + pad)))
    comp.save(OUT + name)
    return comp


lock_green = build((203, 249, 222), (255, 255, 255), 'proplan-lockup-green.png')
lock_black = build((52, 211, 153), (255, 255, 255), 'proplan-lockup-black.png')
# 밝은 바탕(그린 화이트 설정 탭 등)에 얹는 버전 — 진한 워드마크 + 브랜드 에메랄드 깃발
lock_light = build((15, 123, 74), (11, 15, 20), 'proplan-lockup-light.png')


def gradient(size, stops):
    base = Image.new('RGB', (size, size))
    px = base.load()
    for y in range(size):
        for x in range(size):
            t = (x * 0.38 + y * 0.62) / size
            for i in range(len(stops) - 1):
                t0, c0 = stops[i]
                t1, c1 = stops[i + 1]
                if t0 <= t <= t1:
                    f = (t - t0) / (t1 - t0)
                    px[x, y] = tuple(int(c0[k] + (c1[k] - c0[k]) * f) for k in range(3))
                    break
    return base


S = 1024
MARK_POLE_LOCAL = POLE_X - MARK_BB[0]        # 잘라낸 마크 안에서의 기둥 위치
MARK_W = MARK_BB[2] - MARK_BB[0]
MARK_H = MARK_BB[3] - MARK_BB[1]
WORD_W = WORD_BB[2] - WORD_BB[0]
WORD_H = WORD_BB[3] - WORD_BB[1]

# 아이콘 안 배치 — iOS 둥근 모서리에서 잘리지 않는 가운데 영역만 사용
ICON_WORD_W = 0.600      # 워드마크 가로 = 캔버스의 60%
ICON_FLAG_H = 0.232      # 깃발 세로 = 캔버스의 23.2%
ICON_GAP = 0.056         # 깃발과 워드마크 사이


def make_icon(stops, mark_rgb, word_rgb, scale_ratio, out_names, glow_alpha=(255, 255, 255, 22)):
    """깃발은 위쪽 가운데, ProPlan 워드마크는 그 아래 가운데.

    scale_ratio 는 예전 호출부와의 호환을 위해 남겨 둡니다(지금은 쓰지 않음).
    """
    bgimg = gradient(S, stops).convert('RGBA')
    glow = Image.new('RGBA', (S, S), (0, 0, 0, 0))
    d = ImageDraw.Draw(glow)
    d.ellipse([S * 0.10, S * 0.04, S * 0.90, S * 0.80], fill=glow_alpha)
    glow = glow.filter(ImageFilter.GaussianBlur(90))
    icon = Image.alpha_composite(bgimg, glow)

    mh = int(round(S * ICON_FLAG_H))
    mw = int(round(mh * MARK_W / float(MARK_H)))
    ww = int(round(S * ICON_WORD_W))
    wh = int(round(ww * WORD_H / float(WORD_W)))
    gap = int(round(S * ICON_GAP))
    top = int(round((S - (mh + gap + wh)) / 2.0))

    # ① 깃발 — 기둥이 캔버스 한가운데
    m = apply_color(mark_rgb, emerald).crop(MARK_BB)
    sc = mh / float(m.height)
    mr = m.resize((mw, mh), Image.LANCZOS)
    x = int(round(S / 2 - MARK_POLE_LOCAL * sc))
    icon.alpha_composite(mr, (x, top))

    # ② 워드마크 — 깃발 바로 아래 정중앙, 폭은 안전 영역 안
    wd = apply_color(word_rgb, word_mask).crop(WORD_BB)
    wr = wd.resize((ww, wh), Image.LANCZOS)
    icon.alpha_composite(wr, (int(round((S - ww) / 2.0)), top + mh + gap))

    icon = icon.convert('RGB')
    for sz, nm in out_names:
        icon.resize((sz, sz), Image.LANCZOS).save(OUT + nm)
    return icon


make_icon([(0.0, (18, 138, 83)), (0.62, (12, 107, 65)), (1.0, (8, 73, 44))],
          (255, 255, 255), (255, 255, 255), 0.455,
          [(512, 'icon-512.png'), (192, 'icon-192.png'), (180, 'apple-touch-icon.png'),
           (64, 'icon-64.png'), (32, 'favicon-32.png')])
make_icon([(0.0, (28, 28, 32)), (0.55, (22, 22, 24)), (1.0, (15, 15, 17))],
          (52, 211, 153), (255, 255, 255), 0.455,
          [(512, 'icon-black-512.png')], glow_alpha=(70, 214, 156, 20))
print('assets rebuilt · icon %dpx · flag %.0f%% · word %.0f%% (가운데 정렬)' % (S, ICON_FLAG_H*100, ICON_WORD_W*100))
