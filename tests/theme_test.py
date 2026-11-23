#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""화면 테마 2종(그린 화이트 · 시크 블랙) 검사.

- 설정 탭 맨 위에 두 테마 카드가 있고, 누르면 data-act="theme" 로 바뀌는지
- <head> 부트스트랩이 첫 페인트 전에 localStorage 를 읽어 data-theme 을 맞추는지(흰 화면 깜빡임 없음)
- applyTheme: <html data-theme>, <meta theme-color>(#F2F2F7 / #131316 — 상단 바 바탕과 같은 값), 짧은 키 저장
- 홈 화면 앱 상태 바 글자색(apple-mobile-web-app-status-bar-style)도 테마를 따라가는지
- setTheme: state.theme 저장 · 다시 그리기 · 같은 테마 재선택은 조용히 넘어가는지
- 시크 블랙 CSS 가 스플래시·카드·시트·탭바까지 덮는지 (그린 화이트 기본값은 그대로)
"""
import re, sys, json
import quickjs

HTML = open('/workspace/golf-lesson-app/prototype.html', encoding='utf-8').read()
HEAD = HTML[:HTML.index('<style>')]
OUT = []

def ok(name, cond, detail=''):
    OUT.append((name, bool(cond), detail))

# ── 1. <head> 부트스트랩 ─────────────────────────────────
ok('1-1 theme-color 메타 기본값 #F2F2F7', '<meta name="theme-color" content="#F2F2F7">' in HEAD)
boot = re.search(r'<script>(.*?)</script>', HEAD, re.S)
ok('1-2 <style> 앞에 부트스트랩 스크립트', boot is not None)
bootjs = boot.group(1) if boot else ''
ok('1-3 부트스트랩이 저장본(golfLessonApp.v2)을 읽음', "golfLessonApp.v2" in bootjs)
ok('1-4 부트스트랩이 짧은 키도 확인', "golfLessonApp.theme" in bootjs)
ok('1-5 부트스트랩이 첫 페인트 전에 data-theme 설정', "setAttribute('data-theme'" in bootjs)
ok('1-6 부트스트랩이 검정일 때 theme-color #131316', "'#131316'" in bootjs and "'#F2F2F7'" in bootjs)
ok('1-7 부트스트랩이 JSON.parse 실패에 안전(try/catch)', 'try {' in bootjs and 'catch' in bootjs)

# ── 2. 설정 탭 테마 카드 ─────────────────────────────────
ok('2-1 viewSettings 맨 위가 화면 테마', HTML.index('function viewSettings(){')
   < HTML.index('<h2>화면 테마</h2>') < HTML.index('<h2>레슨 시간 범위</h2>'))
ok('2-2 그린 화이트 · 시크 블랙 두 카드', "themeCardHTML('green')" in HTML and "themeCardHTML('black')" in HTML)
ok('2-3 테마 카드 이름', '🌿 그린 화이트' in HTML and '🖤 시크 블랙' in HTML)
ok('2-4 카드가 data-act="theme" 로 동작', 'data-act="theme" data-v="' in HTML)
ok('2-5 onClick 에 theme 분기', "case 'theme':\n      setTheme(el.getAttribute('data-v'));" in HTML)

# ── 3. 시크 블랙 CSS ─────────────────────────────────────
css = HTML[HTML.index('<style>'):HTML.index('</style>')]
dark = css[css.index('html[data-theme="black"]{'):]
ok('3-1 다크 팔레트 블록 존재', 'html[data-theme="black"]{' in css)
ok('3-2 다크에서 무광 차콜 바탕(#131316)', '--bg:#131316' in dark and '--page:#08090A' in dark)
ok('3-3 다크에서 밝은 글자', '--ink:#F3F4F6' in dark)
ok('3-4 다크 에메랄드 포인트 + 솔리드 버튼색 분리', '--green:#46D69C' in dark and '--green-solid:#0C7A52' in dark)
for sel, label in [
    ('.splash', '스플래시'), ('.hero{', '오늘 히어로'), ('.card', '카드'),
    ('.sheetwrap', '바텀시트'), ('.tabbar button', '탭바'), ('.input', '입력'),
    ('.pcard', '수강권 카드'), ('.kpi', '통계 카드'), ('.golden', '골든타임'),
    ('.srow', '마감 정산'), ('.quickadd', '빠른 추가'), ('.calopt', '캘린더 연동'),
]:
    ok('3-5 다크: ' + label, ('html[data-theme="black"] ' + sel) in dark)
ok('3-6 다크 스플래시는 차콜 그라데이션', 'linear-gradient(165deg,#1C1C20' in dark)
ok('3-7 다크 스플래시 진행 바 실버→에메랄드', '#9BF0C9' in dark)
ok('3-8 그린 화이트 기본값 유지', '--bg:#F2F2F7; --card:#FFFFFF' in css)
ok('3-9 흰 바탕은 --field 토큰으로', '--field:#FFFFFF' in css and '--field:#232328' in dark)
ok('3-10 다크에서 color-scheme:dark', 'color-scheme:dark' in dark)

# ── 4. 실제 함수 실행 (applyTheme · setTheme) ─────────────
start = HTML.index('var THEMES = {')
end = HTML.index('function save(){')
CODE = HTML[start:end]

STUBS = r"""
var __store = {}, __meta = null, __sb = null, __log = [];
var localStorage = {
  getItem:function(k){ return Object.prototype.hasOwnProperty.call(__store, k) ? __store[k] : null; },
  setItem:function(k, v){ __store[k] = String(v); },
  removeItem:function(k){ delete __store[k]; }
};
var document = {
  documentElement: { attrs:{}, setAttribute:function(k,v){ this.attrs[k]=v; }, getAttribute:function(k){ return this.attrs[k]; } },
  querySelector:function(sel){
    /* 테마색 메타와 상태 바 스타일 메타는 서로 다른 태그입니다 */
    if (sel.indexOf('status-bar-style') >= 0) {
      if (!__sb) { __sb = { attrs:{}, setAttribute:function(k,v){ this.attrs[k]=v; } }; }
      return __sb;
    }
    if (!__meta) { __meta = { attrs:{}, setAttribute:function(k,v){ this.attrs[k]=v; } }; }
    return __meta;
  }
};
var state = { theme:'green' };
function save(){ __log.push('save'); }
function render(){ __log.push('render'); }
function toast(m){ __log.push('toast:' + m); }
"""

ctx = quickjs.Context()
ctx.eval(STUBS + CODE + '\nglobalThis.T = { applyTheme:applyTheme, setTheme:setTheme, themeOf:themeOf, themeCardHTML:themeCardHTML };')

ok('4-1 themeOf 기본 green', ctx.eval('T.themeOf()') == 'green')
ctx.eval("state.theme = 'black'")
ok('4-2 themeOf black', ctx.eval('T.themeOf()') == 'black')
ctx.eval("state.theme = undefined")
ok('4-3 저장값이 없으면 green', ctx.eval('T.themeOf()') == 'green')

ctx.eval("T.applyTheme('black')")
ok('4-4 applyTheme(black) → html[data-theme]', ctx.eval('document.documentElement.attrs["data-theme"]') == 'black')
ok('4-5 applyTheme(black) → theme-color #131316', ctx.eval('__meta.attrs.content') == '#131316')
ok('4-5b applyTheme(black) → 상태 바 글자색 black', ctx.eval('__sb.attrs.content') == 'black')
ok('4-6 applyTheme(black) → 짧은 키 저장', ctx.eval("localStorage.getItem('golfLessonApp.theme')") == 'black')

ctx.eval("T.applyTheme('green')")
ok('4-7 applyTheme(green) → html[data-theme]', ctx.eval('document.documentElement.attrs["data-theme"]') == 'green')
ok('4-8 applyTheme(green) → theme-color #F2F2F7', ctx.eval('__meta.attrs.content') == '#F2F2F7')
ok('4-8b applyTheme(green) → 상태 바 글자색 default', ctx.eval('__sb.attrs.content') == 'default')
ctx.eval("T.applyTheme('엉뚱한값')")
ok('4-9 알 수 없는 값은 green 으로', ctx.eval('document.documentElement.attrs["data-theme"]') == 'green')

ctx.eval("state.theme = 'green'; __log.length = 0; T.setTheme('black')")
ok('4-10 setTheme(black) → state.theme 저장', ctx.eval('state.theme') == 'black')
ok('4-11 setTheme(black) → data-theme 적용', ctx.eval('document.documentElement.attrs["data-theme"]') == 'black')
ok('4-12 setTheme(black) → save + render + toast',
   ctx.eval('__log.join("|")') == 'save|render|toast:🖤 시크 블랙 테마로 바뀌었어요',
   ctx.eval('__log.join("|")'))
ctx.eval('__log.length = 0; T.setTheme("black")')
ok('4-13 같은 테마 다시 누르면 조용함', ctx.eval('__log.length') == 0 and ctx.eval('document.documentElement.attrs["data-theme"]') == 'black')

ctx.eval("T.setTheme('green')")
ok('4-14 그린 화이트로 되돌아감', ctx.eval('state.theme') == 'green'
   and ctx.eval('document.documentElement.attrs["data-theme"]') == 'green'
   and ctx.eval('__meta.attrs.content') == '#F2F2F7')

ctx.eval("state.theme = 'black'")
html_on = ctx.eval("T.themeCardHTML('black')")
html_off = ctx.eval("T.themeCardHTML('green')")
ok('4-15 선택 카드에 on·aria-pressed', 'class="themecard on"' in html_on and 'aria-pressed="true"' in html_on)
ok('4-16 비선택 카드는 on 아님', 'themecard"' in html_off.replace("themecard on", "themecard\""))
ok('4-17 카드마다 미리보기 그린/블랙', 'tprev black' in html_on and 'tprev green' in html_off)
ok('4-18 카드 데이터 속성', 'data-act="theme" data-v="black"' in html_on)

# ── 5. 설정 화면 실제 렌더 (문자열 이어붙임 오류 방지) ────────
mainjs = max(re.findall(r'<script>(.*?)</script>', HTML, re.S), key=len)
ok('5-0-1 문자열에 "+ +" 이중 연결 없음', re.search(r"\+\s*\+\s*(r|t|')|'\s*\+\s*\+", mainjs) is None)

vs_start = mainjs.index('/* 설정 탭 = 화면 테마')
vs_end = mainjs.index('/* ---------- 수입 정산', vs_start)
VS = mainjs[vs_start:vs_end]
STUB2 = r"""
var state = { theme:'black', pro:{ name:'이시훈', academy:'그린필드 골프 아카데미' },
  calendarSync:{ enabled:false, target:'both' } };
function esc(s){ return String(s == null ? '' : s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;'); }
function calSettingHTML(){ return '<div id="calStub"></div>'; }
function dayRangeLabel(){ return '06:00~23:00'; }
function dayFromMin(){ return 6 * 60; }
function dayToMin(){ return 23 * 60; }
function fromSlotOptions(){ return [{ v:'360', label:'06:00' }, { v:'720', label:'12:00' }]; }
function toSlotOptions(){ return [{ v:'1080', label:'18:00' }, { v:'1440', label:'24:00' }]; }
function pickFieldHTML(id, opts, value){
  return '<button class="input pickfield" id="' + id + 'Btn" data-field="' + id + '">' + esc(value) + '</button>';
}
"""
ctx2 = quickjs.Context()
ctx2.eval(STUB2 + CODE + '\n' + VS + '\nglobalThis.OUT = viewSettings();')
vshtml = ctx2.eval('OUT')
ok('5-0-2 설정 화면에 NaN 없음', 'NaN' not in vshtml, vshtml[:200])
ok('5-0-3 설정 화면에 출시 로드맵 없음', '앱스토어 출시 로드맵' not in vshtml and '1단계 · MVP 프로토타입' not in vshtml)
ok('5-0-4 설정 첫 섹션이 화면 테마', vshtml.index('<h2>화면 테마</h2>') < vshtml.index('레슨 시간 범위'))
ok('5-0-5 설정 화면에 두 테마 카드', 'data-v="black"' in vshtml and 'data-v="green"' in vshtml)
ok('5-0-6 저장된 테마가 선택 표시', 'class="themecard on"' in vshtml and 'data-v="black"' in vshtml[
    vshtml.index('class="themecard on"'):vshtml.index('class="themecard on"') + 60])

# ── 5. init 동기화 ───────────────────────────────────────
ok('5-1 init 에서 저장본 테마를 <html> 에 반영', 'applyTheme(state.theme)' in HTML)
ok('5-2 잘못된 저장값은 green 으로 보정', "if (state.theme !== 'black' && state.theme !== 'green') state.theme = 'green';" in HTML)
ok('5-3 데모 초기화해도 고른 테마는 유지', 'var keepTheme = themeOf();' in HTML and 'state.theme = keepTheme;' in HTML)

for name, cond, detail in OUT:
    print(('PASS ' if cond else 'FAIL ') + name + ('' if cond else '  <- ' + str(detail)))
p = sum(1 for _, c, _ in OUT if c)
print('')
print('%d passed / %d total' % (p, len(OUT)))
sys.exit(0 if p == len(OUT) else 1)
