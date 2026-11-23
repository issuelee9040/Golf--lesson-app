#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""로고·앱 아이콘의 깃대(깃발 기둥) 가운데 정렬 검사.

깃발은 기둥 오른쪽으로 뻗어 있어 마크 bbox만 가운데 두면 기둥이 왼쪽으로 밀립니다.
그래서 생성된 PNG의 픽셀을 다시 재어
- 사각 앱 아이콘: 깃발 기둥·컵의 x 중심이 캔버스 한가운데이고, ProPlan 워드마크가
  그 아래 정중앙에 있는지 (2026-11-23 아이콘 변경)
- 락업: 기둥 x 중심이 `ProPlan` 워드마크 가로 중심과 맞는지
- 잘림 없음 · 크기 규격 · 작은 아이콘이 같은 그림의 축소본인지
를 확인합니다.
"""
import sys
import numpy as np
from PIL import Image

ASSETS = '/workspace/golf-lesson-app/assets/'
OUT = []

def ok(name, cond, detail=''):
    OUT.append((name, bool(cond), detail))

# ── 측정 도구 ────────────────────────────────────────────
def mark_mask(im):
    """초록 아이콘은 아주 밝은 흰 마크, 차콜 아이콘은 에메랄드 마크."""
    a = np.array(im.convert('RGB')).astype(np.float32)
    r, g, b = a[:,:,0], a[:,:,1], a[:,:,2]
    lum = 0.299 * r + 0.587 * g + 0.114 * b
    return (lum > 210) | ((g > 140) & (g - r > 50) & (g - b > 20))

def pole_and_cup(mask, width):
    """기둥 x 중심과 컵(바닥 타원) x 중심."""
    ys, xs = np.where(mask)
    top, bot = ys.min(), ys.max()
    h = bot - top + 1
    band = bot - int(h * 0.15)
    widths = mask[band:bot + 1].sum(axis=1)
    cup_y = band + int(np.argmax(widths))
    cx = np.where(mask[cup_y])[0]
    cup = (cx.min() + cx.max()) / 2.0
    narrow = max(3, int(round(width * 0.06)))     # 이보다 좁은 행 = 기둥
    centers, weights = [], []
    for y in range(top, cup_y - 2):
        xr = np.where(mask[y])[0]
        if len(xr) == 0 or len(xr) > narrow:
            continue
        centers.append((xr.min() + xr.max()) / 2.0)
        weights.append(len(xr))
    pole = float(np.average(centers, weights=weights)) if centers else cup
    return pole, cup, (int(xs.min()), int(xs.max()), int(ys.min()), int(ys.max()))

# ── 1. 앱 아이콘 ────────────────────────────────────────
ICONS = [
    ('icon-512.png', 512, 0.01),
    ('icon-black-512.png', 512, 0.01),
    ('icon-192.png', 192, 0.02),
    ('apple-touch-icon.png', 180, 0.02),
    ('icon-64.png', 64, 0.05),
    ('favicon-32.png', 32, 0.05),
]
def split_flag_word(m):
    """아이콘 안에서 위(깃발) / 아래(워드마크) 덩어리를 가장 큰 빈 줄로 나눈다."""
    rows = m.any(axis=1)
    ys = np.where(rows)[0]
    gaps = [y for y in range(ys.min(), ys.max()) if not rows[y]]
    split = int(np.median(gaps)) if gaps else int((ys.min() + ys.max()) / 2)
    return m[:split], m[split:], (ys.min(), ys.max()), split

for name, size, tol in ICONS:
    im = Image.open(ASSETS + name)
    ok('1 %s 크기 %d×%d' % (name, size, size), im.size == (size, size), str(im.size))
    m = mark_mask(im)
    flag, word, (top, bot), split = split_flag_word(m)
    pole, cup, bb = pole_and_cup(flag, size)
    err_pole = abs(pole - size / 2.0) / size
    err_cup = abs(cup - size / 2.0) / size
    ok('1 %s 깃발 기둥이 가운데 (%.1fpx, %.2f%%)' % (name, pole, err_pole * 100), err_pole <= tol,
       'pole=%.2f center=%.2f' % (pole, size / 2.0))
    ok('1 %s 깃발 컵이 가운데 (%.1fpx, %.2f%%)' % (name, cup, err_cup * 100), err_cup <= tol,
       'cup=%.2f center=%.2f' % (cup, size / 2.0))
    wys, wxs = np.where(word)
    wc = (wxs.min() + wxs.max()) / 2.0
    err_word = abs(wc - size / 2.0) / size
    ok('1 %s ProPlan 이 깃발 아래 정중앙 (%.1fpx, %.2f%%)' % (name, wc, err_word * 100), err_word <= tol,
       'word=%.2f center=%.2f' % (wc, size / 2.0))
    ok('1 %s 깃발이 워드마크 위에 있음' % name, np.where(flag.any(axis=1))[0].max() < split + wys.min(),
       'flag bottom %d / word top %d' % (np.where(flag.any(axis=1))[0].max(), split + wys.min()))
    # iOS 둥근 모서리에서 잘리지 않게 내용은 가운데 76% 안에
    ok('1 %s 안전 여백 (좌우 12%% 이상)' % name,
       wxs.min() >= size * 0.12 and wxs.max() <= size * 0.88,
       'x %d..%d / %d' % (wxs.min(), wxs.max(), size))
    ok('1 %s 위아래 여백 (각 8%% 이상)' % name, top >= size * 0.08 and bot <= size * 0.92,
       'y %d..%d / %d' % (top, bot, size))

# 작은 아이콘은 512 아이콘의 축소본과 같아야 합니다(같은 그림 → 같은 정렬)
big = Image.open(ASSETS + 'icon-512.png').convert('RGB')
for name, size in [('icon-192.png', 192), ('apple-touch-icon.png', 180), ('icon-64.png', 64), ('favicon-32.png', 32)]:
    small = np.array(Image.open(ASSETS + name).convert('RGB')).astype(np.float32)
    ds = np.array(big.resize((size, size), Image.LANCZOS)).astype(np.float32)
    ok('2 %s 는 512 아이콘과 같은 그림' % name, np.abs(small - ds).max() <= 12,
       'max diff %.1f' % np.abs(small - ds).max())

# ── 3. 락업 — 기둥 = 워드마크 가운데 ─────────────────────
LOCKUPS = ['proplan-lockup-green.png', 'proplan-lockup-black.png', 'proplan-lockup-light.png']
for name in LOCKUPS:
    im = Image.open(ASSETS + name).convert('RGBA')
    ok('3 %s 규격 864×491' % name, im.size == (864, 491), str(im.size))
    al = np.array(im)[:,:,3]
    rowsum = al.sum(axis=1)
    ys = np.where(rowsum > 0)[0]
    gaps = [y for y in range(ys.min(), ys.max()) if rowsum[y] == 0]
    split = int(np.median(gaps)) if gaps else int((ys.min() + ys.max()) / 2)
    mark = al[:split] > 128
    word = al[split:] > 128
    pole, cup, bb = pole_and_cup(mark, mark.shape[1])
    wys, wxs = np.where(word)
    wc = (wxs.min() + wxs.max()) / 2.0
    ok('3 %s 기둥 = 워드마크 중심 (차이 %.1fpx)' % (name, abs(pole - wc)), abs(pole - wc) <= 3.0,
       'pole=%.1f word=%.1f' % (pole, wc))
    ok('3 %s 컵도 워드마크 중심 (차이 %.1fpx)' % (name, abs(cup - wc)), abs(cup - wc) <= 4.0,
       'cup=%.1f word=%.1f' % (cup, wc))
    ok('3 %s 마크가 워드마크 위에 있음' % name, bb[3] < split)

    # 예전처럼 마크 bbox만 가운데 두었을 때(기둥이 왼쪽으로 밀린 상태)가 아님
    ok('3 %s 마크 오른쪽 끝이 잘리지 않음' % name, bb[1] < 864 - 20, str(bb))

# ── 4. 생성기 규칙이 남아 있는지 ─────────────────────────
GEN = open(ASSETS + '_gen.py', encoding='utf-8').read()
ok('4-1 생성기가 깃대 중심을 계산', 'def pole_center_x(' in GEN and 'POLE_X' in GEN)
ok('4-2 아이콘을 기둥 기준으로 배치', 'S / 2 - MARK_POLE_LOCAL * sc' in GEN)
ok('4-2b 아이콘에 워드마크를 깃발 아래로 넣음', 'ICON_WORD_W' in GEN and 'top + mh + gap' in GEN)
ok('4-3 락업을 워드마크 중심에 맞춤', 'WORD_CENTER - POLE_X' in GEN)

SPEC = open('/workspace/golf-lesson-app/spec.md', encoding='utf-8').read()
ok('4-4 spec 에 깃대 정렬 기록', '깃대' in SPEC and '깃발 위 · `ProPlan` 아래 정중앙' in SPEC and 'logo_center_test' in SPEC)

failed = [n for n, c, d in OUT if not c]
for n, c, d in OUT:
    print(('PASS ' if c else 'FAIL ') + n + ('' if c else '  <- ' + str(d)))
if failed:
    print('\n%d FAILED / %d passed' % (len(failed), len(OUT) - len(failed)))
    sys.exit(1)
print('\nALL %d PASSED' % len(OUT))
