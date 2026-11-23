#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""통계 → 수입 정산의 2칸 카드(.rvsplit)가 좌우 대칭인지 검사한다.

검사 항목
- 두 칸 제목이 390px(좁은 화면 375·320px 포함)에서 한 줄에 들어가는지
- 두 칸 카드 높이·금액(.v) 위쪽 위치가 같은지 (라이트/검정 테마 모두)
- 제목이 다시 길어져 줄바꿈되지 않도록 nowrap 규칙이 있는지
- 제목에서 빠진 '필드·숏게임·원포인트' 안내가 카드 안에 남아 있는지

레이아웃 검사는 헤드리스 크로미움(playwright)이 있을 때만 돌고,
없으면 건너뛴 뒤 글자 폭 추정으로 제목 길이만 검사한다.
"""
import os
import re
import sys

HTML = open('/workspace/golf-lesson-app/prototype.html', encoding='utf-8').read()

fails, log = [], []


def ok(cond, name):
    if cond:
        log.append('PASS ' + name)
    else:
        fails.append('FAIL ' + name)


def eq(a, b, name):
    ok(a == b, name + ('' if a == b else '\n  got=[' + str(a) + ']\n  want=[' + str(b) + ']'))


def rule(sel):
    """선택자 하나의 선언 블록을 이어 붙여 돌려준다 (같은 선택자 여러 번이면 마지막이 이김)."""
    out = ''
    for m in re.finditer(re.escape(sel) + r'\s*\{([^}]*)\}', HTML):
        out += m.group(1) + ';'
    return out.replace('\n', ' ')


def has(css, prop, name):
    ok(re.search(re.escape(prop) + r'\s*[:;]', css) is not None, name)


# ---------------------------------------------------------------- 카드 마크업
split = HTML[HTML.index("h += '<div class=\"rvsplit\">'"):]
split = split[:split.index("</div>';")]
labels = re.findall(r'<span class="k">([^<]+)</span>', split)
eq(len(labels), 2, '1-1 두 칸 카드 제목 2개')
eq(labels[0], '정규 수강권 수입', '1-2 왼쪽 제목')
eq(labels[1], '필드·별도 수입', '1-3 오른쪽 제목')
ok(all('⛳' not in lab for lab in labels) and max(len(lab) for lab in labels) <= 10,
   '1-4 제목이 짧고 좌우 같은 형식 (이모지·긴 문구 없음)')
contain_m = re.search(r"<span class=\"m\">' \+ \(cur\.sepCount(.*?)\+ '</span></div>' \+", split, re.S)
ok(contain_m is not None, '1-5 별도 카드 아래 설명 줄')
if contain_m:
    ok('필드·숏게임·원포인트' in contain_m.group(1), '1-6 설명 줄에 필드·숏게임·원포인트 유지')
ok("'이번 달 없음'" in split, '1-7 별도 0건일 때 문구')

# ---------------------------------------------------------------- CSS 규칙
grid = rule('.rvsplit')
has(grid, 'grid', '2-1 .rvsplit 그리드')
ok('1fr 1fr' in grid, '2-2 두 칸 폭이 같음 (1fr 1fr)')

kcss = rule('.rvsplit .k')
has(kcss, 'white-space:nowrap', '2-3 제목 한 줄 고정 (nowrap)')
ok('word-break:keep-all' in kcss, '2-4 제목 단어 중간 줄바꿈 방지 유지')
has(kcss, 'text-overflow:ellipsis', '2-5 넘칠 때 말줄임 (줄바꿈 대신)')

sicss = rule('.rvsplit .si')
has(sicss, 'display:flex', '2-6 카드 안 세로 정렬')
has(sicss, 'flex-direction:column', '2-7 카드 안 세로 정렬 방향')
has(rule('.rvsplit .m'), 'margin-top:auto', '2-8 아래 설명 줄을 카드 바닥에 붙임')

# 글자 폭 추정: 한글 1em, 숫자 0.55em, 가운뎃점 0.35em, 공백 0.28em (11.5px · 자간 -0.2px)
def est_width(text, size=11.5):
    w = 0.0
    for ch in text:
        if ch == ' ':
            w += 0.28
        elif ch in '·':
            w += 0.35
        elif ch.isdigit():
            w += 0.55
        elif ord(ch) > 0x1100:
            w += 1.0
        else:
            w += 0.5
    return w * size - 0.2 * max(0, len(text) - 1)

# 360px 화면에서 카드 안쪽 폭 ≈ 135px → 여유를 두고 128px 이하
for i, lab in enumerate(labels):
    w = est_width(lab)
    ok(w <= 128, '3-%d 제목 폭 추정 %.1fpx ≤ 128px (%s)' % (i + 1, w, lab))

# ---------------------------------------------------------------- 실제 레이아웃
JS_METRICS = """
() => {
  const rv = document.querySelector('.rvsplit');
  if (!rv) return { err: 'no-rvsplit' };
  return { vw: window.innerWidth, cards: [...rv.querySelectorAll('.si')].map(c => {
    const k = c.querySelector('.k'), v = c.querySelector('.v'), m = c.querySelector('.m');
    const lineH = el => parseFloat(getComputedStyle(el).lineHeight) || parseFloat(getComputedStyle(el).fontSize) * 1.3;
    const kb = k.getBoundingClientRect(), vb = v.getBoundingClientRect(), mb = m.getBoundingClientRect();
    return {
      card: { top: +c.getBoundingClientRect().top.toFixed(2), h: +c.getBoundingClientRect().height.toFixed(2) },
      k: { text: k.textContent, h: +kb.height.toFixed(2), lines: Math.round(kb.height / lineH(k)) },
      v: { top: +vb.top.toFixed(2) },
      m: { h: +mb.height.toFixed(2), lines: Math.round(mb.height / lineH(m)) }
    };
  })};
}
"""


def layout_checks():
    try:
        from playwright.sync_api import sync_playwright
    except Exception:
        return 'playwright 없음'

    libdir = '/workspace/tmp/chlibs/root'
    if os.path.isdir(libdir):
        os.environ['LD_LIBRARY_PATH'] = libdir + (':' + os.environ['LD_LIBRARY_PATH'] if os.environ.get('LD_LIBRARY_PATH') else '')

    url = 'file:///workspace/golf-lesson-app/prototype.html'
    try:
        pw = sync_playwright().start()
        browser = pw.chromium.launch()
    except Exception as e:
        return '크로미움 실행 불가 (%s)' % str(e).splitlines()[0][:80]

    try:
        for theme in ('light', 'black'):
            for width in (390, 375, 320):
                pg = browser.new_page(viewport={'width': width, 'height': 844}, device_scale_factor=2)
                pg.goto(url)
                pg.wait_for_timeout(1200)
                if pg.locator('button.ob-demo').count():
                    pg.locator('button.ob-demo').first.click()
                    pg.wait_for_timeout(700)
                if theme == 'black':
                    pg.evaluate("document.documentElement.setAttribute('data-theme','black')")
                    pg.wait_for_timeout(200)
                pg.get_by_role('button', name='통계').first.click()
                pg.wait_for_timeout(500)
                pg.locator('button[data-act="stats-view"][data-v="revenue"]').first.click()
                pg.wait_for_timeout(500)
                d = pg.evaluate(JS_METRICS)
                tag = '%dpx %s' % (width, '검정' if theme == 'black' else '라이트')
                if d.get('err'):
                    ok(False, '4-%s 카드 없음' % tag)
                    pg.close()
                    continue
                a, b = d['cards']
                ok(d['vw'] == width, '4-%s 화면 폭 %d' % (tag, width))
                eq(a['k']['lines'], 1, '4-%s 왼쪽 제목 한 줄' % tag)
                eq(b['k']['lines'], 1, '4-%s 오른쪽 제목 한 줄' % tag)
                ok(abs(a['k']['h'] - b['k']['h']) <= 0.5,
                   '4-%s 제목 높이 같음 (%.2f/%.2f)' % (tag, a['k']['h'], b['k']['h']))
                ok(abs(a['v']['top'] - b['v']['top']) <= 0.5,
                   '4-%s 금액 위쪽 정렬 (%.2f/%.2f)' % (tag, a['v']['top'], b['v']['top']))
                ok(abs(a['card']['h'] - b['card']['h']) <= 0.5,
                   '4-%s 카드 높이 같음 (%.2f/%.2f)' % (tag, a['card']['h'], b['card']['h']))
                ok(abs(a['card']['top'] - b['card']['top']) <= 0.5, '4-%s 카드 위쪽 정렬' % tag)
                eq(a['m']['lines'], 1, '4-%s 왼쪽 설명 한 줄' % tag)
                eq(b['m']['lines'], 1, '4-%s 오른쪽 설명 한 줄' % tag)
                pg.close()
    finally:
        browser.close()
        pw.stop()
    return None


skipped = layout_checks()
if skipped:
    log.append('SKIP 실제 레이아웃 검사 — ' + skipped)

print('\n'.join(log))
if fails:
    print('\n'.join(fails))
    print('\n%d FAILED / %d total' % (len(fails), len(fails) + len(log) - (1 if skipped else 0)))
    sys.exit(1)
print('\nALL %d PASSED' % len(log))
