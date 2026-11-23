#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""레슨 상태 시트 바닥 버튼 순서 · 카톡 버튼 반투명 노랑 검사.

- 버튼 순서: {회원} 정보·레슨 차트 열기 → 카톡 요약 복사 → 내용 수정 → 내 캘린더에 추가
- 카톡 버튼: 진한 형광 노랑(#FEE500 그라데이션)이 아니라 반투명 노랑 유리
  (바탕 rgba(250,204,21,.16~.22) · 테두리 rgba(250,204,21,.42~.55))
- 두 테마 모두에서 글자가 읽히는지 대비(contrast) 계산
- 레슨 차트의 작은 카톡 알약은 그대로 진한 노랑인지(바뀌면 안 되는 부분)
"""
import re, sys

HTML = open('/workspace/golf-lesson-app/prototype.html', encoding='utf-8').read()
SPEC = open('/workspace/golf-lesson-app/spec.md', encoding='utf-8').read()
CSS = HTML[HTML.index('<style>'):HTML.index('</style>')]
OUT = []

def ok(name, cond, detail=''):
    OUT.append((name, bool(cond), detail))

# ── 1. 레슨 상태 시트 바닥 버튼 순서 ─────────────────────
start = HTML.index('function openStatusSheet(')
end = HTML.index('/* =========================================================\n   오늘 마감 정산')
SHEET = HTML[start:end]
FOOT = SHEET[SHEET.index('footer:'):]

pos = {}
for key in ['member-open', 'kakao-copy', 'lesson-edit', 'cal-sheet']:
    pos[key] = FOOT.index('data-act="%s"' % key)
ok('1-1 회원 정보 CTA 가 맨 위', pos['member-open'] < pos['kakao-copy'] < pos['lesson-edit'] < pos['cal-sheet'],
   str(pos))
ok('1-2 카톡 버튼이 두 번째', pos['kakao-copy'] < pos['lesson-edit'])
ok('1-3 내용 수정이 세 번째', pos['lesson-edit'] < pos['cal-sheet'])
ok('1-4 내 캘린더에 추가가 맨 아래', pos['cal-sheet'] == max(pos.values()))
cta_i = FOOT.index('data-act="member-open"')
cta = FOOT[FOOT.rindex("'<button", 0, cta_i):cta_i + 40]
ok('1-5 CTA 는 에메랄드 cta-hero 버튼', 'class="cta-hero"' in cta, cta)
ok('1-6 CTA 가 사라지지 않게 위 버튼에도 아래 여백', 'cta-hero' in FOOT and 'style="margin-bottom:8px"' in FOOT)
cal_i = FOOT.index('data-act="cal-sheet"')
CAL = FOOT[FOOT.rindex("'<button", 0, cal_i):FOOT.index('</button>', cal_i)]
ok('1-7 맨 아래 버튼은 아래 여백 없음(여백 중복 방지)', 'margin-bottom:8px' not in CAL, CAL)
ok('1-8 회원 없는 레슨은 카톡이 맨 위 (CTA 조건부)',
   "s.memberId ?" in FOOT and FOOT.index('s.memberId ?') < pos['kakao-copy'])

# ── 2. 카톡 버튼 반투명 노랑 ─────────────────────────────
def rule(sel):
    m = re.search(r'(^|\n)' + re.escape(sel) + r'\{([^}]*)\}', CSS)
    return m.group(2) if m else ''

base = rule('.btn.btn-kakao')
ok('2-1 .btn.btn-kakao 규칙 존재', base != '')
m = re.search(r'background:rgba\(250,204,21,\.(\d+)\)', base)
ok('2-2 바탕이 반투명 노랑 rgba(250,204,21,.18)', m is not None and m.group(1) == '18', base)
alpha = int(m.group(1)) / 100.0 if m else 0
ok('2-3 투명도가 .16~.22 사이', 0.16 <= alpha <= 0.22, str(alpha))
ok('2-4 진한 노랑 그라데이션 제거', '#FEE500' not in base and '#FFEF62' not in base, base)
mb = re.search(r'border:1px solid rgba\(250,204,21,\.(\d+)\)', base)
ok('2-5 노란 테두리 rgba(250,204,21,.42~.55)', mb is not None and 0.42 <= int(mb.group(1)) / 100.0 <= 0.55, base)
ok('2-6 그린 화이트 글자 #5C4300', '#5C4300' in base, base)
ok('2-7 누를 때 조금 더 진해짐', rule('.btn.btn-kakao:active') != '' and 'rgba(250,204,21,.30)' in rule('.btn.btn-kakao:active'))
ok('2-8 유리 느낌(blur)', 'backdrop-filter' in base)

dark = rule('html[data-theme="black"] .btn.btn-kakao')
ok('2-9 시크 블랙 전용 규칙', dark != '', dark)
md = re.search(r'background:rgba\(250,204,21,\.(\d+)\)', dark)
ok('2-10 시크 블랙 바탕 rgba(250,204,21,.16)', md is not None and md.group(1) == '16', dark)
ok('2-11 시크 블랙 테두리 노랑 .42', 'border-color:rgba(250,204,21,.42)' in dark, dark)
ok('2-12 시크 블랙 글자 #FDE68A', '#FDE68A' in dark, dark)
ok('2-13 아이콘 배지 두 테마', 'background:rgba(250,204,21,.26)' in rule('.kakao-cta .kko-ic')
   and 'background:rgba(250,204,21,.20)' in rule('html[data-theme="black"] .kakao-cta .kko-ic'))
ok('2-14 설명·복사 배지 두 테마', '#7A5F16' in rule('.kakao-cta .kko-s')
   and 'rgba(253,230,138,.75)' in rule('html[data-theme="black"] .kakao-cta .kko-s')
   and '#FDE68A' in rule('html[data-theme="black"] .kakao-cta .kko-go'))
ok('2-15 높이 54px · 두 줄 설명 유지', 'height:54px' in rule('.kakao-cta')
   and '<b>카톡 요약 복사</b>' in FOOT and 'kko-go' in FOOT)

# ── 3. 대비(contrast) 계산 ───────────────────────────────
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

Y = (250, 204, 21)
light_bg = blend(Y, 0.18, (255, 255, 255))     # 그린 화이트 시트(흰 카드)
dark_bg = blend(Y, 0.16, (28, 28, 32))         # 시크 블랙 시트 바탕
ok('3-1 그린 화이트 본문 대비 4.5 이상', ratio(light_bg, (0x5C, 0x43, 0x00)) >= 4.5,
   '%.2f' % ratio(light_bg, (0x5C, 0x43, 0x00)))
ok('3-2 그린 화이트 설명 대비 4.5 이상', ratio(light_bg, (0x7A, 0x5F, 0x16)) >= 4.5,
   '%.2f' % ratio(light_bg, (0x7A, 0x5F, 0x16)))
ok('3-3 시크 블랙 본문 대비 4.5 이상', ratio(dark_bg, (0xFD, 0xE6, 0x8A)) >= 4.5,
   '%.2f' % ratio(dark_bg, (0xFD, 0xE6, 0x8A)))
sub_dark = blend((253, 230, 138), 0.75, dark_bg)
ok('3-4 시크 블랙 설명 대비 4.5 이상', ratio(dark_bg, sub_dark) >= 4.5, '%.2f' % ratio(dark_bg, sub_dark))

# ── 4. 바뀌면 안 되는 곳 ─────────────────────────────────
chip = rule('.kakaochip')
ok('4-1 레슨 차트 카톡 알약은 그대로 진한 노랑', 'linear-gradient(180deg,#FFEF62,#FEE500)' in chip, chip)
ok('4-2 레슨 상태 카톡 버튼에 반투명 클래스 유지', 'class="btn btn-kakao kakao-cta btn-block"' in FOOT)
ok('4-3 복사 동작 그대로', 'data-act="kakao-copy"' in FOOT)
ok('4-4 spec 에 버튼 순서 기록', '카톡 요약 복사`(반투명 노랑) → `내용 수정` → `내 캘린더에 추가`' in SPEC
   or ('반투명 노랑' in SPEC and '내 캘린더에 추가' in SPEC and '위에서부터' in SPEC))

failed = [n for n, c, d in OUT if not c]
for n, c, d in OUT:
    print(('PASS ' if c else 'FAIL ') + n + ('' if c else '  <- ' + str(d)))
if failed:
    print('\n%d FAILED / %d passed' % (len(failed), len(OUT) - len(failed)))
    sys.exit(1)
print('\nALL %d PASSED' % len(OUT))
