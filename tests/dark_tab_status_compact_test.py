#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""시크 블랙 탭바 활성 표시 · 레슨 상태 시트 절반 높이 타일을 검사한다.

탭바 (시크 블랙):
- 지금 메뉴 = 밝은 민트 아이콘 + 흰 글자 + 민트 알약 + 위쪽 액센트 줄
- 나머지 메뉴는 rgba(255,255,255,.45) 로 확실히 죽이고, 누가 봐도 대비가 서는지 계산
- 그린 화이트 탭바는 그대로

레슨 상태 시트:
- 5가지가 2열 · 46px 타일(점 + 이름 + 차감/미차감)로 바뀌고 세로 높이가 절반 이하
- 별도 결제 레슨은 4가지 · 수입 포함/수입 없음
- 예전처럼 긴 설명 줄을 쌓지 않고 아래 한 줄 안내로 옮겼는지
"""
import re, sys

HTML = open('/workspace/golf-lesson-app/prototype.html', encoding='utf-8').read()
CSS = HTML[HTML.index('<style>'):HTML.index('</style>')]
OUT = []

def ok(name, cond, detail=''):
    OUT.append((name, bool(cond), detail))

def rule(sel):
    m = re.search(r'(^|\n)' + re.escape(sel) + r'\{([^}]*)\}', CSS)
    return m.group(2) if m else ''

# ── 1. 탭바 (시크 블랙) ──────────────────────────────────
dark_btn = rule('html[data-theme="black"] .tabbar button')
on = rule('html[data-theme="black"] .tabbar button.on')
ok('1-1 비활성 탭은 확실히 죽임 rgba(255,255,255,.45)', 'color:rgba(255,255,255,.45)' in dark_btn, dark_btn)
ok('1-2 활성 탭은 밝은 민트 글자', 'color:#9BF0C9' in on, on)
ok('1-3 활성 탭에 민트 알약 바탕', 'background:rgba(70,214,156,.15)' in on, on)
ok('1-4 활성 탭 테두리로 한 번 더 구분', 'inset 0 0 0 1px rgba(70,214,156,.34)' in on, on)
ok('1-5 위쪽 액센트 줄 (:before)', 'html[data-theme="black"] .tabbar button.on:before{content:""' in CSS
   and 'background:#46D69C' in rule('html[data-theme="black"] .tabbar button.on:before'))
ok('1-6 활성 아이콘을 조금 더 두껍게 + 빛', 'stroke-width:2.4' in rule('html[data-theme="black"] .tabbar button.on svg')
   and 'drop-shadow' in rule('html[data-theme="black"] .tabbar button.on svg'))
ok('1-7 활성 글자는 흰색으로 또렷하게', '#F2FBF6' in rule('html[data-theme="black"] .tabbar button.on span'))
ok('1-8 그린 화이트 활성색은 그대로', '.tabbar button.on{color:var(--green)}' in CSS)
ok('1-9 탭바 자체도 시크 블랙 바탕', 'html[data-theme="black"] .tabbar{background:rgba(16,16,19,.97)' in CSS)

# ── 1b. 대비 계산 ───────────────────────────────────────
def lum(c):
    def f(v):
        v /= 255.0
        return v / 12.92 if v <= 0.03928 else ((v + 0.055) / 1.055) ** 2.4
    r, g, b = [f(x) for x in c]
    return 0.2126 * r + 0.7152 * g + 0.0722 * b

def ratio(a, b):
    la, lb = lum(a), lum(b)
    hi, lo = max(la, lb), min(la, lb)
    return (hi + 0.05) / (lo + 0.05)

def blend(fg, al, bg):
    return tuple(fg[i] * al + bg[i] * (1 - al) for i in range(3))

bar_bg = (16, 16, 19)
pill = blend((70, 214, 156), 0.15, bar_bg)
inactive = blend((255, 255, 255), 0.45, bar_bg)
active = (0x9B, 0xF0, 0xC9)
ok('2-1 활성 탭 대비 7 이상', ratio(pill, active) >= 7, '%.1f:1' % ratio(pill, active))
ok('2-2 비활성 탭도 4.5 이상 (읽히되 죽어 보임)', ratio(bar_bg, inactive) >= 4.5,
   '%.1f:1' % ratio(bar_bg, inactive))
ok('2-3 활성/비활성 차이가 2배 이상', ratio(pill, active) / ratio(bar_bg, inactive) >= 2.0,
   '%.1f vs %.1f' % (ratio(pill, active), ratio(bar_bg, inactive)))

# ── 3. 레슨 상태 시트 — 구조 ────────────────────────────
grid = rule('.statusgrid')
tile = rule('.stopt')
ok('3-1 두 열 격자', 'display:grid' in grid and 'grid-template-columns:1fr 1fr' in grid, grid)
ok('3-2 타일 높이 46px (누르기 편함)', 'height:46px' in tile, tile)
ok('3-3 5개면 마지막 칸은 가로로 꽉', ':last-child:nth-child(odd){grid-column:1 / -1}' in CSS.replace('\n', ''))
ok('3-4 예전 5줄 statusrow 규칙 제거', '.statusrow{' not in CSS)
ok('3-5 점 + 이름 + 차감 표시', '.so-dot' in CSS and '.so-t' in CSS and '.so-k' in CSS)
ok('3-6 상태별 점 색', '.stopt.stopt-completed .so-dot{background:var(--green)}' in CSS
   and '.stopt.stopt-no_show .so-dot{background:var(--red)}' in CSS)
ok('3-7 선택된 타일 강조 (두 테마)', '.stopt.on{border-color:var(--green)' in CSS
   and 'html[data-theme="black"] .stopt.on{background:rgba(70,214,156,.16)' in CSS)

# 예전 5줄 높이 vs 지금 3줄(2열) 높이
old_h = 5 * (46 + 6)
new_h = 3 * 46 + 2 * 7
ok('4-1 세로 높이가 절반 이하 (%.0fpx → %.0fpx)' % (old_h, new_h), new_h <= old_h * 0.62,
   '%.2f배' % (new_h / float(old_h)))

# ── 5. 실제 시트 내용 ───────────────────────────────────
start = HTML.index('function openStatusSheet(')
end = HTML.index('/* =========================================================\n   오늘 마감 정산')
SHEET = HTML[start:end]
ok('5-1 상태 타일을 반복 생성', 'statusgrid' in SHEET and 'class="stopt stopt-' in SHEET)
ok('5-2 상태 5가지 순서 유지', "STATUS_KEYS = ['completed','same_day_cancel','no_show','excused_cancel','makeup']" in HTML)
ok('5-3 차감/미차감 꼬리표', "STATUS[k].deducted ? '차감' : '미차감'" in SHEET)
ok('5-4 별도 레슨은 수입 포함/없음', "CHARGED[k] ? '수입 포함' : '수입 없음'" in SHEET)
ok('5-5 긴 설명은 아래 한 줄 안내로', 'stophint' in SHEET)
ok('5-6 스크린리더용 설명 유지', 'aria-label=' in SHEET and 'desc' in SHEET)
ok('5-7 예전 아이콘 배지 코드 제거', 'statusrow' not in SHEET)

failed = [n for n, c, d in OUT if not c]
for n, c, d in OUT:
    print(('PASS ' if c else 'FAIL ') + n + ('' if c else '  <- ' + str(d)))
if failed:
    print('\n%d FAILED / %d passed' % (len(failed), len(OUT) - len(failed)))
    sys.exit(1)
print('\nALL %d PASSED' % len(OUT))
