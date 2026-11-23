#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""ProPlan 브랜딩 · 5번 로고 · 체험판 시작 온보딩 검사.

정적 계약
  · <title>ProPlan</title> · apple-mobile-web-app-title · apple-touch-icon/icon/manifest 링크
  · 아이콘 PNG 실제 크기(180 · 192 · 512)와 manifest 내용
  · 스플래시가 5번 로고(깃발 엠블럼 + 워드마크)를 쓰고, 그린 화이트/시크 블랙에서 서로 다른 파일로 바뀌는지
  · 첫 실행 온보딩 마크업(프로 이름 · 소속/레슨장 · 내 레슨 관리 시작하기 · 샘플 데이터로 먼저 둘러보기)
  · 설정 탭의 샘플 데이터 채우기 / 내 데이터로 새로 시작 / ProPlan Trial 표기

실제 코드
  · hasSavedState: 저장본 유무
  · blankState: 이름만 있고 회원·레슨 0건인 깨끗한 시작
  · finishOnboarding(false): 자기 이름으로 빈 상태 시작 + 저장
  · finishOnboarding(true): 샘플 데이터로 둘러보기
  · 이름이 비면 시작하지 않음(필수)
  · 저장본이 있으면 init() 이 온보딩을 띄우지 않고 기존 데이터를 그대로 쓴다
  · resetFresh: 프로 이름·테마는 남기고 빈 상태로
"""
import re, sys, json, struct
import quickjs

HTML = open('/workspace/golf-lesson-app/prototype.html', encoding='utf-8').read()
ASSETS = '/workspace/golf-lesson-app/assets/'
OUT = []

def ok(name, cond, detail=''):
    OUT.append((name, bool(cond), detail))

def png_size(path):
    with open(path, 'rb') as f:
        head = f.read(26)
    assert head[:8] == b'\x89PNG\r\n\x1a\n', path
    w, h = struct.unpack('>II', head[16:24])
    return w, h

# ── 1. 앱 이름 · 홈화면 아이콘 ─===============================
HEAD = HTML[:HTML.index('<style>')]
ok('1-1 <title>ProPlan</title>', '<title>ProPlan</title>' in HEAD)
ok('1-2 홈화면 이름 apple-mobile-web-app-title=ProPlan',
   '<meta name="apple-mobile-web-app-title" content="ProPlan">' in HEAD)
ok('1-3 apple-mobile-web-app-capable 유지', 'apple-mobile-web-app-capable' in HEAD)
ok('1-4 apple-touch-icon 링크', '<link rel="apple-touch-icon" sizes="180x180" href="assets/apple-touch-icon.png">' in HEAD)
ok('1-5 favicon 32 링크', 'rel="icon" type="image/png" sizes="32x32" href="assets/favicon-32.png"' in HEAD)
ok('1-6 안드로이드 192 아이콘 링크', 'sizes="192x192" href="assets/icon-192.png"' in HEAD)
ok('1-7 홈화면 앱 manifest 링크', '<link rel="manifest" href="manifest.webmanifest">' in HEAD)
ok('1-8 theme-color 메타 유지', '<meta name="theme-color"' in HEAD)

ok('1-9 apple-touch-icon 180×180 실제 PNG', png_size(ASSETS + 'apple-touch-icon.png') == (180, 180))
ok('1-10 아이콘 192 실제 PNG', png_size(ASSETS + 'icon-192.png') == (192, 192))
ok('1-11 아이콘 512 실제 PNG', png_size(ASSETS + 'icon-512.png') == (512, 512))
ok('1-12 파비콘 32 실제 PNG', png_size(ASSETS + 'favicon-32.png') == (32, 32))

man = json.load(open('/workspace/golf-lesson-app/manifest.webmanifest', encoding='utf-8'))
ok('1-13 manifest 이름 ProPlan', man.get('name') == 'ProPlan' and man.get('short_name') == 'ProPlan')
ok('1-14 manifest 독립 앱(standalone)', man.get('display') == 'standalone')
ok('1-15 manifest 아이콘 192·512', {i['sizes'] for i in man.get('icons', [])} >= {'192x192', '512x512'})

# ── 2. 5번 로고 락업 (스플래시 · 온보딩) ─====================
ok('2-1 스플래시에 그린 락업', 'assets/proplan-lockup-green.png' in HTML)
ok('2-2 스플래시에 블랙 락업', 'assets/proplan-lockup-black.png' in HTML)
ok('2-3 스플래시에 설정용(밝은 바탕) 락업', 'assets/proplan-lockup-light.png' in HTML)
ok('2-4 옛 sp-badge 스플래시 제거', 'sp-badge' not in HTML)
ok('2-5 스플래시 브랜드 락업 클래스', 'class="sp-lockup"' in HTML and 'class="ob-lockup"' in HTML)
ok('2-6 시크 블랙에서 블랙 락업으로 교체',
   'html[data-theme="black"] .sp-lockup .lk-green{display:none}' in HTML and
   'html[data-theme="black"] .sp-lockup .lk-black{display:block}' in HTML)
ok('2-7 온보딩도 두 테마 락업', 'html[data-theme="black"] .ob-lockup .lk-black{display:block}' in HTML)
ok('2-8 그린 화이트 스플래시 = 에메랄드 그라데이션 유지',
   '152deg,#128A53 0%,#0C6B41 52%,#08492C 100%' in HTML)
ok('2-9 시크 블랙 스플래시 = 무광 차콜',
   'html[data-theme="black"] .splash{background:linear-gradient(165deg,#1C1C20 0%,#161618 52%,#0F0F11 100%)}' in HTML)
ok('2-10 스플래시 스크린리더 라벨에 ProPlan', 'aria-label="ProPlan · 레슨 관리 앱을 여는 중"' in HTML)
ok('2-11 락업 PNG 존재(864×491)',
   png_size(ASSETS + 'proplan-lockup-green.png') == (864, 491))

# ── 3. 첫 실행 온보딩 마크업 ─===============================
ob = HTML[HTML.index('<div class="onboard"'):HTML.index('<div id="app">')]
ok('3-1 온보딩 레이어 존재 + 처음엔 숨김', 'id="onboard"' in ob and 'hidden' in ob)
ok('3-2 모달 역할 · 제목 연결', 'role="dialog"' in ob and 'aria-labelledby="obTitle"' in ob)
ok('3-3 인사 문구', '반가워요 프로님!' in ob and '이름으로 바로 시작해 보세요' in ob)
ok('3-4 프로 이름 입력 (16px · 필수)',
   'id="ozPro"' in ob and 'placeholder="예: 김프로 또는 홍길동"' in ob)
ok('3-5 소속 / 레슨장 입력 (선택)',
   'id="ozAcademy"' in ob and 'placeholder="예: 판교 인도어연습장 (선택)"' in ob)
ok('3-6 기본 버튼 = 내 레슨 관리 시작하기',
   'data-act="onboard-start">내 레슨 관리 시작하기</button>' in ob)
ok('3-7 보조 링크 = 샘플 데이터로 먼저 둘러보기',
   'data-act="onboard-demo"' in ob and '샘플 데이터로 먼저 둘러보기' in ob)
ok('3-8 체험판 표기', 'ProPlan Trial' in ob)
ok('3-9 이름 오류 안내', 'id="ozErr"' in ob and '이름을 먼저 적어 주세요' in ob)
ok('3-10 온보딩 CSS: 그린 그라데이션 · 차콜 오버라이드',
   '.onboard{position:fixed;inset:0;z-index:9500' in HTML and
   'html[data-theme="black"] .onboard{background:linear-gradient(165deg,#1C1C20 0%,#161618 52%,#0F0F11 100%)}' in HTML)
ok('3-11 온보딩 입력칸 16px (아이폰 자동 확대 방지)',
   'input,select,textarea{font:inherit;color:inherit;border-radius:0;font-size:16px}' in HTML)

# ── 4. 설정 탭 (체험판 관리) ─===============================
vs = HTML[HTML.index('function viewSettings(){'):]
vs = vs[:vs.index('\n}\n')]
ok('4-1 샘플 데이터 채우기', 'data-act="demo-reset">샘플 데이터 채우기</button>' in vs)
ok('4-2 내 데이터로 새로 시작 (초기화)', 'data-act="fresh-start">내 데이터로 새로 시작 (초기화)</button>' in vs)
ok('4-3 데이터 내보내기 유지', 'data-act="export-data"' in vs)
ok('4-4 프로 이름 · 소속 유지', 'id="setPro"' in vs and 'id="setAcademy"' in vs)
ok('4-5 설정 하단 ProPlan Trial 로고', 'class="brandfoot"' in vs and 'ProPlan Trial' in vs)
ok('4-6 빈 상태에서 첫 회원 추가 CTA', 'id="firstMemberCard"' in HTML and 'data-act="member-add"' in HTML)

# ── 5. 실제 코드 (quickjs) ─================================
scripts = [m.group(1) for m in re.finditer(r'<script>(.*?)</script>', HTML, re.S)]
BIG = max(scripts, key=len)
BODY = BIG[BIG.index('(function(){') + len('(function(){'):BIG.rindex('})();')]

HARNESS = r"""
function El(id){
  this.id = id; this.value = ''; this.disabled = false; this.textContent = ''; this.innerHTML = '';
  this.style = {}; this._cls = {}; this.hidden = true; this.scrollTop = 0; this.children = [];
  var self = this;
  this.classList = {
    add: function(c){ self._cls[c] = true; },
    remove: function(c){ delete self._cls[c]; },
    toggle: function(c, f){ if (f) self._cls[c] = true; else delete self._cls[c]; },
    contains: function(c){ return !!self._cls[c]; }
  };
  this.addEventListener = function(){}; this.removeEventListener = function(){};
  this.setAttribute = function(k, v){ if (!this._attrs) this._attrs = {}; this._attrs[k] = v; };
  this.getAttribute = function(k){ return (this._attrs && this._attrs[k]) || ''; };
  this.appendChild = function(c){ this.children.push(c); return c; };
  this.removeChild = function(){};
  this.querySelector = function(){ return null; };
  this.querySelectorAll = function(){ return []; };
  this.closest = function(){ return null; };
  this.focus = function(){ this.focused = true; };
  this.getBoundingClientRect = function(){ return { top:0, left:0, width:0, height:0 }; };
}
var ELS = {};
function mkEl(id){ var e = new El(id); ELS[id] = e; return e; }
var document = {
  getElementById: function(id){ return ELS[id] || null; },
  createElement: function(){ return new El('new'); },
  addEventListener: function(){},
  body: new El('body'), documentElement: new El('html'),
  querySelector: function(){ return null; }, querySelectorAll: function(){ return []; }
};
var window = { addEventListener: function(){}, SpeechRecognition: null, webkitSpeechRecognition: null };
var navigator = { userAgent: 'test' };
var localStorage = {
  _d: {},
  getItem: function(k){ return this._d[k] === undefined ? null : this._d[k]; },
  setItem: function(k, v){ this._d[k] = String(v); },
  removeItem: function(k){ delete this._d[k]; }
};
var timers = [];
function setTimeout(fn, ms){ timers.push(fn); return timers.length; }
function clearTimeout(){}
mkEl('main'); mkEl('hd'); mkEl('tabbar'); mkEl('fab'); mkEl('toast');
mkEl('onboard'); mkEl('ozPro'); mkEl('ozAcademy'); mkEl('ozErr');
"""

TEST = r"""
var fails = [], log = [];
function ok(c, n){ if (c) log.push('PASS ' + n); else fails.push('FAIL ' + n); }
var KEY = 'golfLessonApp.v2';

/* 첫 실행(모듈 로드)에서 init 이 온보딩을 띄웠고, 아직 아무것도 저장하지 않아야 한다 */
ok(ELS.onboard.hidden === false, '5-1 저장본이 없으면 첫 실행에 온보딩이 뜬다');
ok(localStorage.getItem(KEY) === null, '5-2 시작 방식을 고르기 전에는 저장하지 않는다');
ok(hasSavedState() === false, '5-3 저장본 없음');

/* 빈 상태 */
var b = blankState('김프로', '판교 인도어연습장');
ok(b.pro.name === '김프로' && b.pro.academy === '판교 인도어연습장', '5-4 이름 · 소속이 그대로');
ok(b.members.length === 0 && b.sessions.length === 0 && b.packages.length === 0 && b.notes.length === 0,
   '5-5 회원 · 레슨 · 수강권 · 기록 0건');
ok(b.templates.length === 3 && b.templates.some(function(t){ return t.durationMinutes === 25; }) &&
   b.templates.some(function(t){ return t.durationMinutes === 55; }), '5-6 25분 · 55분 기본 수강권 틀은 준비');
ok(b.theme === 'green', '5-7 새 시작의 기본 테마 = 그린 화이트');

/* 이름 없이 시작은 막힌다 */
ELS.ozPro.value = ''; ELS.ozAcademy.value = '';
var blocked = finishOnboarding(false);
ok(blocked === false, '5-8 이름이 비면 시작하지 않는다');
ok(ELS.onboard.hidden === false, '5-9 온보딩은 그대로 남는다');
ok(ELS.ozErr.classList.contains('on'), '5-10 빨간 안내 표시');
ok(localStorage.getItem(KEY) === null, '5-11 이름 없이 저장하지 않는다');

/* 자기 이름으로 바로 시작 */
ELS.ozPro.value = '  김프로  '; ELS.ozAcademy.value = ' 판교 인도어연습장 ';
var started = finishOnboarding(false);
ok(started === true, '5-12 이름으로 시작 성공');
ok(state.pro.name === '김프로', '5-13 앞뒤 공백을 지운 이름으로 시작');
ok(state.pro.academy === '판교 인도어연습장', '5-14 소속도 저장');
ok(state.members.length === 0 && state.sessions.length === 0, '5-15 빈 상태로 시작 (회원 0 · 레슨 0)');
ok(ELS.onboard.hidden === true, '5-16 온보딩이 닫힌다');
ok(ui.tab === 'today', '5-17 시작 후 오늘 탭');
ok(ELS.ozErr.classList.contains('on') === false, '5-18 오류 안내 해제');
ok(hasSavedState() === true, '5-19 이제 저장본이 생긴다');
var saved = JSON.parse(localStorage.getItem(KEY));
ok(saved.pro.name === '김프로' && saved.members.length === 0, '5-20 저장된 데이터도 빈 상태 + 내 이름');
var hToday = viewToday();
renderHeader();
ok(ELS.hd.innerHTML.indexOf('김프로') >= 0, '5-21 오늘 화면에 내 이름');
ok(hToday.indexOf('첫 회원을 추가해 볼까요?') >= 0, '5-22 첫 회원 추가 안내');

/* 샘플 데이터로 둘러보기 */
ELS.ozPro.value = '박프로'; ELS.ozAcademy.value = '';
var demoed = finishOnboarding(true);
ok(demoed === true, '5-23 샘플 둘러보기 시작 성공');
ok(state.members.length >= 4 && state.sessions.length > 0, '5-24 샘플 회원 · 레슨이 채워진다');
ok(state.pro.name === '박프로', '5-25 샘플이어도 내가 적은 이름 사용');
ok(hasSavedState() === true, '5-26 샘플도 저장');

/* 저장본이 있으면 온보딩을 띄우지 않고 기존 데이터를 지킨다 */
var keep = JSON.parse(localStorage.getItem(KEY));
keep.pro.name = '이시훈'; keep.pro.academy = '그린필드 골프 아카데미';
localStorage._d = {}; localStorage.setItem(KEY, JSON.stringify(keep));
ELS.onboard.hidden = true; state = null;
init();
ok(ELS.onboard.hidden === true, '5-27 저장본이 있으면 온보딩을 띄우지 않는다');
ok(state.pro.name === '이시훈', '5-28 기존 프로 이름이 그대로');
ok(state.members.length === keep.members.length, '5-29 기존 회원 데이터가 그대로');

/* 내 데이터로 새로 시작 */
var beforeName = state.pro.name, beforeTheme = state.theme;
resetFresh();
ok(state.members.length === 0 && state.sessions.length === 0, '5-30 내 데이터로 새로 시작 = 빈 상태');
ok(state.pro.name === beforeName, '5-31 프로 이름은 남는다');
ok(state.theme === beforeTheme, '5-32 고른 테마는 남는다');

/* 샘플 채우기도 그대로 동작 */
resetDemo();
ok(state.members.length >= 4, '5-33 샘플 데이터 채우기 동작');

globalThis.RESULT = JSON.stringify({ pass: log, fail: fails });
"""

ctx = quickjs.Context()
ctx.eval(HARNESS + "\n" + BODY + "\n" + TEST)
data = json.loads(ctx.eval('RESULT'))
for l in data['pass']:
    print(l)
if data['fail']:
    print()
    for l in data['fail']:
        print(l)

# 정적 체크 출력
for name, cond, detail in OUT:
    print(('PASS ' if cond else 'FAIL ') + name + ('' if cond else '  <- ' + str(detail)))

fails = [n for n, c, _ in OUT if not c]
total = len(data['pass']) + len(OUT)
passed = len(data['pass']) + (len(OUT) - len(fails))
print('')
print('%d passed / %d total' % (passed, total))
sys.exit(0 if (not fails and not data['fail']) else 1)
