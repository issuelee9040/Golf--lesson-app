#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""아이폰 사파리 입력칸 자동 확대 방지 검사 — 모든 <input>/<textarea> 글자 16px 통일.

아이폰 사파리(iOS)는 입력칸 글자 크기가 16px 미만이면 칸을 탭했을 때 화면을 자동으로
확대합니다. 그래서 이 프로토타입은 모든 입력칸을 16px 로 고정합니다.

- 입력칸에 걸리는 CSS 규칙 중 font-size 가 16px 미만인 것이 없는지
- 기본 규칙(input,select,textarea) · .input · 검색창 · 피커 줄 · 소요시간 칸이 16px 인지
- 인라인 style 로 입력칸 글자를 줄인 곳이 없는지
- .input 계열 클래스를 쓰지 않는(글자 크기를 놓치기 쉬운) 입력칸이 남아 있지 않은지
"""
import re, sys

HTML = open('/workspace/golf-lesson-app/prototype.html', encoding='utf-8').read()
OUT = []

def ok(name, cond, detail=''):
    OUT.append((name, bool(cond), detail))

# ── CSS 뽑기 ─────────────────────────────────────────────
css = re.search(r'<style>(.*?)</style>', HTML, re.S).group(1)
css = re.sub(r'/\*.*?\*/', '', css, flags=re.S)                     # 주석 제거
css = re.sub(r'@media[^{]*\{.*?\}\s*\}', '', css, flags=re.S)      # 중첩 블록은 검사 대상 아님

rules = []
for m in re.finditer(r'([^{}]+)\{([^{}]*)\}', css):
    sel = m.group(1).strip()
    if sel.startswith('@'):
        continue
    rules.append((sel, m.group(2)))

def targets_input(sel):
    """선택자가 실제 <input>/<textarea> 요소(또는 .input 클래스)에 걸리는지"""
    for part in sel.split(','):
        part = part.strip()
        if not part:
            continue
        if part.endswith('::placeholder') or part.endswith('::-webkit-input-placeholder'):
            continue                            # 안내 문구는 확대와 무관
        if re.search(r'(?<![\w.#-])(input|textarea)(?![\w-])', part):
            return True
        if re.search(r'\.input(?![\w-])', part):
            return True
    return False

def font_size(decl):
    m = re.search(r'font-size\s*:\s*([0-9.]+)px', decl)
    return float(m.group(1)) if m else None

# ── 1. 입력칸 규칙에 16px 미만이 없는지 ───────────────────
small = []
for sel, decl in rules:
    if not targets_input(sel):
        continue
    fs = font_size(decl)
    if fs is not None and fs < 16:
        small.append((sel, fs))
ok('1-1 입력칸에 걸리는 규칙 중 16px 미만 없음', not small,
   ' ; '.join('%s=%spx' % (s, f) for s, f in small))

def rule(sel_startswith):
    """해당 선택자로 시작하는 규칙의 font-size (선택자 목록 전체 또는 각 조각)"""
    for sel, decl in rules:
        hit = sel.strip().startswith(sel_startswith) or any(
            part.strip().startswith(sel_startswith) for part in sel.split(','))
        if not hit:
            continue
        fs = font_size(decl)
        if fs is not None:
            return fs
    return None

# ── 2. 핵심 규칙이 16px ──────────────────────────────────
ok('2-1 기본 규칙 input,select,textarea = 16px', rule('input,select,textarea') == 16,
   rule('input,select,textarea'))
ok('2-2 .input = 16px', rule('.input') == 16, rule('.input'))
ok('2-3 회원목록 검색창 = 16px', rule('.search input') == 16, rule('.search input'))
ok('2-4 피커 줄 글자(.pickfield .pv) = 16px', rule('.pickfield .pv') == 16, rule('.pickfield .pv'))
ok('2-5 소요시간 직접 입력(input.chipinp) = 16px', rule('input.chipinp') == 16, rule('input.chipinp'))
ok('2-6 textarea.input 도 .input 규칙을 그대로 씀', 'textarea.input{' in css)

# ── 3. 인라인 style 로 줄인 입력칸이 없는지 ─────────────────
inline_small = []
for m in re.finditer(r'<(input|textarea)\b[^>]*>', HTML, re.I):
    tag = m.group(0)
    if re.search(r'type=["\']hidden', tag, re.I):
        continue
    fm = re.search(r'font-size\s*:\s*([0-9.]+)px', tag)
    if fm:
        inline_small.append((tag[:70], fm.group(1)))
ok('3-1 인라인 style 로 글자를 줄인 입력칸 없음', not inline_small, str(inline_small[:3]))

# ── 4. 클래스 없이 만들어진 입력칸이 없는지 (규칙을 놓치기 쉬움) ──
unclassed = []
for m in re.finditer(r'<(input|textarea)\b[^>]*>', HTML, re.I):
    tag = m.group(0)
    if re.search(r'type=["\']hidden', tag, re.I):
        continue
    if 'class="input' in tag or 'class="chipinp' in tag or 'class="input chipinp' in tag:
        continue
    if 'id="mSearch"' in tag or "'mSearch'" in tag:
        continue                                # 회원목록 검색창은 .search input 규칙이 담당
    unclassed.append(tag[:80])
ok('4-1 클래스 없는 입력칸 없음 (검색창 제외)', not unclassed, str(unclassed[:3]))

# ── 5. 대표 입력칸이 실제로 16px 규칙을 타는지 (요소별) ──────
CASES = [
    ('회원목록 검색',        '<input id="mSearch"',                  '.search input'),
    ('빠른 추가 한 줄 입력', '<textarea class="input" id="qaLine"',  '.input'),
    ('회원 추가 이름',       '<input class="input" id="mfName"',     '.input'),
    ('회원 추가 연락처',     '<input class="input" id="mfPhone"',    '.input'),
    ('회원 메모',            '<textarea class="input" id="mfMemo"',  '.input'),
    ('예약 장소',            '<input class="input" id="bkLocation"', '.input'),
    ('예약 메모',            '<input class="input" id="bkMemo"',     '.input'),
    ('예약·수정 금액',       'class="input" id="\' + p + \'Fee"',    '.input'),
    ('별도결제 금액',        '<input class="input" id="sepFee"',     '.input'),
    ('소요시간 직접 입력',   'class="input chipinp"',                'input.chipinp'),
    ('차트 작성',            '<textarea class="input" id="noteText"', '.input'),
    ('차트 작성(간편)',      '<textarea class="input" id="quickLine"', '.input'),
    ('스윙 메모',            '<textarea class="input" id="swingMemo"', '.input'),
    ('레슨 세션 메모',       '<textarea class="input" id="smMemo"',  '.input'),
    ('프로 이름',            '<input class="input" id="setPro"',     '.input'),
    ('소속 / 레슨장',        '<input class="input" id="setAcademy"', '.input'),
    ('재등록 횟수',          '<input class="input" id="rqSessions"', '.input'),
    ('재등록 금액',          '<input class="input" id="rqAmount"',   '.input'),
    ('수강권 횟수',          '<input class="input" id="mfSessions"', '.input'),
    ('수강권 금액',          '<input class="input" id="mfPrice"',    '.input'),
]
for label, needle, sel in CASES:
    ok('5 %s → %s 규칙(16px)' % (label, sel), needle in HTML and rule(sel) == 16, needle)

# ── 6. 16px 로 커지며 생길 수 있는 줄임표 방지 ────────────
ok('6-1 시작일+유효기간 줄에서 날짜 칸이 넓음', '<div class="field wide"><label>시작일</label>' in HTML
   and HTML.count('class="field wide"') == 2)
ok('6-2 .row2>.wide 규칙', '.row2>.wide{flex:1.34}' in HTML)

# ── 7. 스펙 문서에 규칙이 적혀 있는지 ─────────────────────
SPEC = open('/workspace/golf-lesson-app/spec.md', encoding='utf-8').read()
ok('7-1 spec 10장에 입력칸 16px 규칙', '16px' in SPEC and '확대' in SPEC and '입력칸' in SPEC)

passed = sum(1 for n, c, d in OUT if c)
for n, c, d in OUT:
    print(('PASS ' if c else 'FAIL ') + n + ('' if c else '  <- ' + str(d)))
print('')
print('%d passed / %d total' % (passed, len(OUT)))
sys.exit(0 if passed == len(OUT) else 1)
