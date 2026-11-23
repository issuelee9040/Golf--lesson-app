#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""상단 바 로고가 '진짜 벡터'인지, 원래 로고 모양 그대로인지 검사한다.

- PNG(<img>) 대신 인라인 SVG 경로(M/L/Z)로 그리는지
- 경로를 직접 래스터화해 예전 가로 락업 PNG(proplan-bar-*.png)와 모양을 비교 (IoU)
- 깃발·워드마크 비율, 밑선 정렬, viewBox 와 CSS 크기 비율이 맞는지
- 두 테마에서 색만 바뀌는지
"""
import math
import re
import sys

import numpy as np
from PIL import Image, ImageDraw

HTML = open('/workspace/golf-lesson-app/prototype.html', encoding='utf-8').read()
ASSETS = '/workspace/golf-lesson-app/assets/'
OUT = []

def ok(name, cond, detail=''):
    OUT.append((name, bool(cond), detail))

# ── 1. 마크업 · 스타일 ─────────────────────────────────
m = re.search(r'<svg class="bb-svg" viewBox="([^"]+)"[^>]*>(.*?)</svg>', HTML, re.S)
ok('1-1 인라인 SVG 락업', m is not None)
body = m.group(2) if m else ''
vb = [float(x) for x in m.group(1).split()] if m else [0, 0, 0, 0]
groups = re.findall(r'<g class="bb-(flag|word)" transform="([^"]+)"><path fill-rule="evenodd" d="([^"]+)"/></g>', body)
ok('1-2 깃발 · 워드마크 두 그룹', [g[0] for g in groups] == ['flag', 'word'], str([g[0] for g in groups]))
ok('1-3 PNG 를 쓰지 않는다', '<img class="bb-green"' not in HTML and 'proplan-bar-green.png' not in HTML)
ok('1-4 경로는 직선(M/L/Z)만 — 스케일해도 뭉개지지 않음', all(set(re.findall('[A-Za-z]', g[2])) <= set('MLZ') for g in groups))
ok('1-5 잘림 방지 여백', vb[0] <= 0 and vb[1] <= 0 and vb[2] > 700 and vb[3] > 140, str(vb))
ok('1-6 CSS 높이 21px · 폭 비율 유지', '.brandbar .bb-svg{display:block;height:21px;width:107px' in HTML)

# ── 2. 경로 파싱 ───────────────────────────────────────
def parse_d(d):
    """M/L/Z 만 있는 경로 → 폴리곤 목록"""
    polys, cur = [], []
    for tok in re.findall(r'[MLZ]|-?\d+(?:\.\d+)?', d):
        if tok == 'M':
            if cur:
                polys.append(cur)
            cur = []
        elif tok == 'L':
            continue
        elif tok == 'Z':
            if cur:
                polys.append(cur)
            cur = []
        else:
            cur.append(float(tok))
    pts = []
    for p in polys:
        pts.append([(p[i], p[i + 1]) for i in range(0, len(p) - 1, 2)])
    return pts

def transform_of(t):
    sc = re.search(r'scale\(([\d.]+)\)', t)
    tr = re.search(r'translate\(([-\d.]+) ([-\d.]+)\)', t)
    s = float(sc.group(1)) if sc else 1.0
    dx, dy = (float(tr.group(1)), float(tr.group(2))) if tr else (0.0, 0.0)
    return lambda p: (p[0] * s + dx, p[1] * s + dy)

layers = {}
for name, tr, d in groups:
    fn = transform_of(tr)
    layers[name] = [[fn(p) for p in poly] for poly in parse_d(d)]

ok('2-1 깃발 경로 존재', len(layers.get('flag', [])) >= 1)
ok('2-2 워드마크 경로 7글자 이상', len(layers.get('word', [])) >= 7, str(len(layers.get('word', []))))
ok('2-3 좌표가 유한값', all(math.isfinite(x) and math.isfinite(y)
                          for ls in layers.values() for poly in ls for x, y in poly))

def bbox(polys):
    xs = [x for poly in polys for x, y in poly]
    ys = [y for poly in polys for x, y in poly]
    return min(xs), min(ys), max(xs), max(ys)

fb = bbox(layers['flag'])
wb = bbox(layers['word'])
ok('2-4 깃발이 워드마크 왼쪽', fb[2] <= wb[0], 'flag right %.1f / word left %.1f' % (fb[2], wb[0]))
ok('2-5 밑선 정렬 (컵 바닥 = 글자 바닥)', abs(fb[3] - wb[3]) <= 1.0,
   'flag %.1f / word %.1f' % (fb[3], wb[3]))
ratio_flag = (fb[2] - fb[0]) / (fb[3] - fb[1])
ratio_word = (wb[2] - wb[0]) / (wb[3] - wb[1])
ok('2-6 깃발 비율 0.75~0.78', 0.74 <= ratio_flag <= 0.79, '%.3f' % ratio_flag)
ok('2-7 워드마크 비율 6.0~6.2 (원본 847×139)', 5.95 <= ratio_word <= 6.25, '%.3f' % ratio_word)
ok('2-8 깃발 높이가 글자 높이의 1.4~1.5배',
   1.38 <= (fb[3] - fb[1]) / (wb[3] - wb[1]) <= 1.52,
   '%.2f' % ((fb[3] - fb[1]) / (wb[3] - wb[1])))

# ── 3. 실제 모양 비교 (래스터화 → IoU) ─────────────────
def raster(polys, scale=4):
    x0, y0, x1, y1 = bbox(polys)
    w = max(1, int(round((x1 - x0) * scale)))
    h = max(1, int(round((y1 - y0) * scale)))
    acc = np.zeros((h, w), bool)
    for poly in polys:
        img = Image.new('L', (w, h), 0)
        ImageDraw.Draw(img).polygon([((x - x0) * scale, (y - y0) * scale) for x, y in poly], fill=255)
        acc ^= np.array(img) > 127
    return acc

def png_masks(name):
    a = np.array(Image.open(ASSETS + name).convert('RGBA'))
    al = a[:, :, 3] > 60
    cols = al.sum(axis=0)
    xs = np.where(cols > 0)[0]
    gap = [x for x in range(xs.min(), xs.max()) if cols[x] == 0]
    # 가장 넓은 빈 구간 = 깃발과 워드마크 사이
    runs, s0, prev = [], gap[0], gap[0]
    for x in gap[1:]:
        if x != prev + 1:
            runs.append((s0, prev))
            s0 = x
        prev = x
    runs.append((s0, prev))
    cut = max(runs, key=lambda r: r[1] - r[0])
    def crop_ink(mask):
        ys, xs = np.where(mask)
        return mask[ys.min():ys.max() + 1, xs.min():xs.max() + 1]
    return crop_ink(al[:, :cut[0]]), crop_ink(al[:, cut[1] + 1:])

def iou(a, b):
    b2 = np.array(Image.fromarray(b.astype(np.uint8) * 255).resize((a.shape[1], a.shape[0]), Image.BILINEAR)) > 127
    return (a & b2).sum() / float((a | b2).sum())

for png in ['proplan-bar-green.png', 'proplan-bar-black.png']:
    fm, wm = png_masks(png)
    ok('3-1 %s 깃발 모양 일치 (IoU)' % png, iou(raster(layers['flag']), fm) >= 0.93,
       '%.3f' % iou(raster(layers['flag']), fm))
    ok('3-2 %s 워드마크 모양 일치 (IoU)' % png, iou(raster(layers['word']), wm) >= 0.93,
       '%.3f' % iou(raster(layers['word']), wm))

# ── 4. 두 테마 색 ─────────────────────────────────────
ok('4-1 그린 화이트 깃발 #0F7B4A · 글자 #0B0F14',
   '.brandbar .bb-flag{fill:#0F7B4A}' in HTML and '.brandbar .bb-word{fill:#0B0F14}' in HTML)
ok('4-2 시크 블랙 깃발 #34D399 · 글자 #F4F6F8',
   'html[data-theme="black"] .brandbar .bb-flag{fill:#34D399}' in HTML
   and 'html[data-theme="black"] .brandbar .bb-word{fill:#F4F6F8}' in HTML)
ok('4-3 바탕은 .hd 와 같은 --bg 로 이어짐', '.brandbar{' in HTML and 'background:var(--bg);border-bottom:0' in HTML)
ok('4-4 바 아래 구분선 제거', 'border-bottom-color:rgba(255,255,255,.08)}' not in HTML)

# ── 5. 21px 로 그렸을 때 실제 크기 ──────────────────────
css_w = 107.0
css_h = 21.0
ink_h = (wb[3] - wb[1]) / (vb[3]) * css_h
ok('5-1 글자 높이 13~16px (읽히는 크기)', 12.5 <= ink_h <= 16.5, '%.1fpx' % ink_h)
ok('5-2 전체 폭이 viewBox 비율과 맞음', abs(css_w / css_h - vb[2] / vb[3]) / (vb[2] / vb[3]) < 0.02,
   'css %.2f / vb %.2f' % (css_w / css_h, vb[2] / vb[3]))

failed = [n for n, c, d in OUT if not c]
for n, c, d in OUT:
    print(('PASS ' if c else 'FAIL ') + n + ('' if c else '  <- ' + str(d)))
if failed:
    print('\n%d FAILED / %d passed' % (len(failed), len(OUT) - len(failed)))
    sys.exit(1)
print('\nALL %d PASSED' % len(OUT))
