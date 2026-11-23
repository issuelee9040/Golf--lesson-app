#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""홈 화면에 추가한 앱(standalone)의 상단 안전 여백 · 상태 바 검사.

이시훈 님 신고: "사파리에서는 상단 바가 선명한데, 홈 화면에 추가해서 열면
아이폰 상태 바가 상단 바 위에 흐릿하게 겹쳐 보인다."

원인: `viewport-fit=cover` + `apple-mobile-web-app-capable=yes` 라 홈 화면 앱은
화면이 상태 바 밑까지 올라갑니다. `.brandbar` 에 위쪽 안전 여백이 없어서
로고가 시계·배터리 뒤로 비치고, 상태 바가 반투명 재질로 그 위를 덮어 흐려 보입니다.

이 검사가 지키는 것
  1) <head>: viewport-fit=cover · standalone 선언 · 상태 바 글자색 메타(테마별 default / black)
  2) 부트스트랩: 첫 페인트 전에 저장된 테마로 상태 바 글자색까지 맞추는지
  3) theme-color == 상단 바 바탕(--bg): 상태 바 자리와 바탕 사이에 이음매(색 단차)가 없는지
  4) CSS: .brandbar 위쪽 env(safe-area-inset-top) 여백 + 예전 브라우저용 9px 기본값
  5) 아래쪽(탭바·시트 바닥·토스트·FAB) 홈 인디케이터 여백이 살아 있는지
  6) 여백이 두 번 들어가지 않는지(#app 에 또 safe-area-inset-top 패딩이 없는지)
"""
import re
import sys

import quickjs

HTML = open('/workspace/golf-lesson-app/prototype.html', encoding='utf-8').read()
HEAD = HTML[:HTML.index('<style>')]
CSS = HTML[HTML.index('<style>'):HTML.index('</style>')]
OUT = []


def ok(name, cond, detail=''):
    OUT.append((name, bool(cond), detail))


def rule(sel):
    m = re.search(r'(^|\n)' + re.escape(sel) + r'\{([^}]*)\}', CSS)
    return m.group(2) if m else ''


# ══════════════════════════════════════════════════════════
# 1. <head> — 홈 화면 앱 · 상태 바
# ══════════════════════════════════════════════════════════
ok('1-1 viewport-fit=cover 유지',
   (re.search(r'<meta name="viewport" content="([^"]+)"', HEAD) or [None, ''])[1].find('viewport-fit=cover') >= 0
   and 'width=device-width' in (re.search(r'<meta name="viewport" content="([^"]+)"', HEAD) or [None, ''])[1]
   and 'initial-scale=1' in (re.search(r'<meta name="viewport" content="([^"]+)"', HEAD) or [None, ''])[1])
ok('1-2 홈 화면 앱(apple) · 모바일 웹앱 선언',
   '<meta name="apple-mobile-web-app-capable" content="yes">' in HEAD
   and '<meta name="mobile-web-app-capable" content="yes">' in HEAD)
ok('1-3 상태 바 글자색 메타가 있다',
   '<meta name="apple-mobile-web-app-status-bar-style" content="default">' in HEAD)
ok('1-4 기본값은 그린 화이트용 어두운 글자(default)',
   (re.search(r'<meta name="apple-mobile-web-app-status-bar-style" content="([^"]+)"', HEAD) or [None, ''])[1] == 'default')
ok('1-5 상태 바 글자색 메타는 첫 페인트 부트스트랩보다 앞',
   HTML.index('apple-mobile-web-app-status-bar-style') < HTML.index('<script>'))

boot = re.search(r'<script>(.*?)</script>', HEAD, re.S)
bootjs = boot.group(1) if boot else ''
ok('1-6 부트스트랩이 <style> 앞에 있다', boot is not None and HTML.index('<script>') < HTML.index('<style>'))
ok('1-7 부트스트랩이 상태 바 메타를 찾는다', 'apple-mobile-web-app-status-bar-style' in bootjs)
ok('1-8 부트스트랩: 시크 블랙이면 상태 바도 밝은 글자(black)', "'black'" in bootjs)
ok('1-9 부트스트랩: 그 외에는 default', "'default'" in bootjs)
ok('1-10 부트스트랩이 저장본(golfLessonApp.v2)을 먼저 본다', 'golfLessonApp.v2' in bootjs)

# ══════════════════════════════════════════════════════════
# 2. theme-color == 상단 바 바탕(--bg) — 이음매 없음
# ══════════════════════════════════════════════════════════
ok('2-1 기본 theme-color = 그린 화이트 --bg(#F2F2F7)',
   '<meta name="theme-color" content="#F2F2F7">' in HEAD)
ok('2-2 그린 화이트 --bg 가 #F2F2F7', '--bg:#F2F2F7' in CSS)
ok('2-3 시크 블랙 --bg 가 #131316', '--bg:#131316' in CSS)
themes = re.search(r'var THEMES = \{(.*?)\};', HTML, re.S)
tj = themes.group(1) if themes else ''
ok('2-4 THEMES.green.meta == #F2F2F7', "meta:'#F2F2F7'" in tj, tj[:120])
ok('2-5 THEMES.black.meta == #131316', "meta:'#131316'" in tj, tj[:120])
ok('2-6 예전 값(#F6F7F8 · #141416)이 남아 있지 않다', '#F6F7F8' not in HTML and '#141416' not in HTML)
man = open('/workspace/golf-lesson-app/manifest.webmanifest', encoding='utf-8').read()
ok('2-7 manifest theme_color 도 #F2F2F7', '"theme_color": "#F2F2F7"' in man, man)

# ══════════════════════════════════════════════════════════
# 3. .brandbar 위쪽 안전 여백
# ══════════════════════════════════════════════════════════
bar = rule('.brandbar')
bar_decl = re.sub(r'/\*.*?\*/', '', bar, flags=re.S)   # 주석은 검사 대상이 아님
ok('3-1 .brandbar 에 env(safe-area-inset-top) 패딩',
   'padding-top:calc(9px + env(safe-area-inset-top, 0px))' in bar, bar)
ok('3-2 예전 브라우저용 기본 패딩 9px 이 먼저 선언됨',
   'padding:9px 16px 8px' in bar and bar.index('padding:9px 16px 8px') < bar.index('padding-top:calc('))
ok('3-3 env() 값이 없으면 0px 로 떨어짐', 'env(safe-area-inset-top, 0px)' in bar)
ok('3-4 .brandbar 바탕이 --bg 로 상태 바 자리까지 채운다',
   'background:var(--bg)' in bar and 'border-bottom:0' in bar)
ok('3-5 시크 블랙도 같은 바탕', 'html[data-theme="black"] .brandbar{background:var(--bg)}' in CSS)
ok('3-6 로고 높이 21px 은 그대로', '.brandbar .bb-svg{display:block;height:21px;width:107px' in HTML)
ok('3-7 상단 바는 fixed 가 아니라 화면 맨 위에 붙은 sticky — 패딩이 자리를 밀어냄',
   'position:sticky' in bar and 'top:0' in bar and 'position:fixed' not in bar)
ok('3-9 상단 바 바탕은 100% 불투명 (뒤가 비치지 않음 — 확대 시 흐림 방지)',
   'background:var(--bg)' in bar_decl and 'background-color:var(--bg)' in bar_decl
   and 'backdrop-filter' not in bar_decl and 'opacity' not in bar_decl)
ok('3-10 상단 바에 투명도 있는 색을 쓰지 않는다(rgba·gradient 없음)',
   'rgba(' not in bar_decl and 'gradient' not in bar_decl, bar_decl)
ok('3-11 상태 바 글자색 메타는 불투명 값만 쓴다(black-translucent 금지)',
   'black-translucent' not in HEAD)
ok('3-8 #app 에 또 위쪽 안전 여백을 주지 않는다(이중 여백 방지)',
   'safe-area-inset-top' not in rule('#app'))

# ══════════════════════════════════════════════════════════
# 4. 아래쪽 · 전체 화면 안전 여백 (홈 인디케이터 · 노치)
# ══════════════════════════════════════════════════════════
ok('4-1 탭바 아래 여백', 'env(safe-area-inset-bottom)' in rule('.tabbar'))
ok('4-2 시트 바닥줄 아래 여백', 'env(safe-area-inset-bottom)' in rule('.sheet .sf'))
ok('4-3 토스트 위치 보정', 'env(safe-area-inset-bottom)' in rule('.toast'))
ok('4-4 빠른추가 FAB 위치 보정', 'env(safe-area-inset-bottom)' in rule('.fab'))
ok('4-5 스플래시 위·아래 여백', 'env(safe-area-inset-top)' in rule('.splash')
   and 'env(safe-area-inset-bottom)' in rule('.splash'))
ok('4-6 체험판 온보딩 위·아래 여백', 'env(safe-area-inset-top)' in rule('.onboard')
   and 'env(safe-area-inset-bottom)' in rule('.onboard'))

# ══════════════════════════════════════════════════════════
# 5. 실제 코드 실행 — applyTheme 이 상태 바 메타까지 바꾸는지
# ══════════════════════════════════════════════════════════
start = HTML.index('var THEMES = {')
end = HTML.index('function save(){')
CODE = HTML[start:end]
STUBS = r"""
var __store = {}, __el = {}, __log = [];
var localStorage = {
  getItem:function(k){ return Object.prototype.hasOwnProperty.call(__store, k) ? __store[k] : null; },
  setItem:function(k, v){ __store[k] = String(v); },
  removeItem:function(k){ delete __store[k]; }
};
var document = {
  documentElement: { attrs:{}, setAttribute:function(k,v){ this.attrs[k]=v; }, getAttribute:function(k){ return this.attrs[k]; } },
  querySelector:function(sel){
    var key = sel.indexOf('status-bar-style') >= 0 ? 'sb' : 'meta';
    if (!__el[key]) { __el[key] = { attrs:{}, setAttribute:function(k,v){ this.attrs[k]=v; } }; }
    return __el[key];
  }
};
var state = { theme:'green' };
function save(){ __log.push('save'); }
function render(){ __log.push('render'); }
function toast(m){ __log.push('toast:' + m); }
"""
ctx = quickjs.Context()
ctx.eval(STUBS + CODE + '\nglobalThis.T = { applyTheme:applyTheme, setTheme:setTheme };')

ctx.eval("T.applyTheme('green')")
ok('5-1 그린: 상태 바 글자 어둡게(default)', ctx.eval("__el.sb.attrs.content") == 'default')
ok('5-2 그린: theme-color #F2F2F7', ctx.eval("__el.meta.attrs.content") == '#F2F2F7')

ctx.eval("T.applyTheme('black')")
ok('5-3 블랙: 상태 바 글자 밝게(black)', ctx.eval("__el.sb.attrs.content") == 'black')
ok('5-4 블랙: theme-color #131316', ctx.eval("__el.meta.attrs.content") == '#131316')

ctx.eval("state.theme = 'green'; T.setTheme('black')")
ok('5-5 설정에서 테마를 바꾸면 상태 바 글자색도 같이 바뀜',
   ctx.eval("__el.sb.attrs.content") == 'black' and ctx.eval("state.theme") == 'black')

ctx.eval("T.setTheme('green')")
ok('5-6 되돌리면 다시 default', ctx.eval("__el.sb.attrs.content") == 'default')

# ══════════════════════════════════════════════════════════
# 6. 설계서 기록
# ══════════════════════════════════════════════════════════
SPEC = open('/workspace/golf-lesson-app/spec.md', encoding='utf-8').read()
ok('6-1 설계서에 상단 안전 여백 항목', 'env(safe-area-inset-top)' in SPEC)
ok('6-2 설계서에 상태 바 글자색 규칙', 'apple-mobile-web-app-status-bar-style' in SPEC)
ok('6-3 설계서에 이 검사 파일 이름', 'tests/safe_area_test.py' in SPEC)

# ══════════════════════════════════════════════════════════
fails = [x for x in OUT if not x[1]]
for n, c, d in OUT:
    print(('PASS ' if c else 'FAIL ') + n + (('  <- ' + str(d)) if (d and not c) else ''))
print('\n%d passed / %d total' % (len(OUT) - len(fails), len(OUT)))
sys.exit(1 if fails else 0)
