# -*- coding: utf-8 -*-
"""상단 브랜드 바용 가로 락업 — 깃발 마크 + ProPlan 워드마크 (테마별 2종).

세로 락업(proplan-lockup-*.png)은 스플래시·온보딩처럼 넓은 자리용입니다.
상단 바처럼 한 줄 높이에 들어가는 자리에는 마크가 왼쪽, 워드마크가 오른쪽인
가로 락업이 필요합니다. 이미 다듬어 둔 세로 락업을 깃발/워드마크로 잘라
다시 앉히므로 글자 모양·색은 브랜드와 똑같습니다.

  proplan-bar-green.png : 밝은 바탕용 — 브랜드 에메랄드 깃발 + 진한 워드마크
  proplan-bar-black.png : 어두운 바탕용 — 밝은 에메랄드 깃발 + 흰 워드마크

깃발은 컵(맨 아래 타원)이 워드마크 밑선에 닿도록 내려 앉히고, 마크 높이는
워드마크 글자 높이의 1.45배로 두어 한 줄에서도 깃발이 먼저 보이게 합니다.
"""
from PIL import Image
import numpy as np

OUT = 'golf-lesson-app/assets/'
H = 132          # 출력 높이(px) — 화면에서 22px 로 보여도 6배라 또렷합니다
MARK_RATIO = 1.45
GAP_RATIO = 0.34


def split_lockup(name):
    """세로 락업을 위(깃발) / 아래(워드마크) 덩어리로 나눕니다."""
    im = Image.open(OUT + name)
    al = np.array(im)[:, :, 3]
    rows = np.where((al > 20).sum(axis=1) > 0)[0]
    empty = [r for r in range(rows.min(), rows.max() + 1) if (al[r] > 20).sum() == 0]
    mid = empty[len(empty) // 2]
    top = im.crop((0, rows.min(), im.width, mid))
    bot = im.crop((0, mid + 1, im.width, rows.max() + 1))
    top = top.crop(top.split()[3].getbbox())
    bot = bot.crop(bot.split()[3].getbbox())
    return top, bot


def compose(name, out_name):
    mk, wd = split_lockup(name)
    wh = int(round((H - 12) / MARK_RATIO))
    mh = int(round(wh * MARK_RATIO))
    mw = int(round(mk.width * (mh / float(mk.height))))
    ww = int(round(wd.width * (wh / float(wd.height))))
    gap = int(round(wh * GAP_RATIO))
    mr = mk.resize((mw, mh), Image.LANCZOS)
    wr = wd.resize((ww, wh), Image.LANCZOS)

    canvas = Image.new('RGBA', (mw + gap + ww, mh + 12), (0, 0, 0, 0))
    canvas.alpha_composite(mr, (0, 6))
    canvas.alpha_composite(wr, (mw + gap, 6 + mh - wh))     # 밑선 맞춤
    bb = canvas.split()[3].getbbox()
    canvas = canvas.crop(bb)
    canvas.save(OUT + out_name)
    print('%s  %dx%d  (%.2f:1)  mark %dx%d word %dx%d' % (
        out_name, canvas.width, canvas.height, canvas.width / float(canvas.height),
        mw, mh, ww, wh))
    return canvas


compose('proplan-lockup-light.png', 'proplan-bar-green.png')   # 밝은 바탕
compose('proplan-lockup-black.png', 'proplan-bar-black.png')   # 어두운 바탕
