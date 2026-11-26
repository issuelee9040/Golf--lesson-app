#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""바텀시트를 아래로 밀어 닫기 + 아이폰 사파리 '당겨서 새로고침' 막기를 실제 코드로 검사한다.

- 손잡이/제목줄을 잡고 내리면 시트가 손가락을 따라 내려오는지 (transform)
- 76px 넘게 내리면 그 시트 하나만 닫히고 이전 시트가 그대로 남는지 (중첩 시트)
- 모자라게 놓으면 제자리로 돌아오는지 (snap back)
- 짧고 빠르게 튕겨도 닫히는지 (flick)
- 내용이 맨 위일 때 본문을 내리면 닫히고, 내용 중간(scrollTop > 0)에서는 손대지 않는지
- 위로 끄는 동작·입력칸에서 시작한 끌기·바깥 여백에서의 끌기는 시트를 움직이지 않는지
- 끌어내리는 동안 touchmove preventDefault 로 사파리 당겨서 새로고침을 막는지
- 가장 위 시트만 반응하는지 (아래 시트는 그대로)
- HTML/CSS 계약: overscroll-behavior, closing, passive:false 등
"""
import sys, json, re
import quickjs

HTML = open('/workspace/golf-lesson-app/prototype.html', encoding='utf-8').read()

start = HTML.index('var sheetStack = [];')
end = HTML.index('function findSession(id){')
CODE = HTML[start:end]

HARNESS = r"""
/* ---------- 최소 DOM 스텁 ---------- */
var timers = [];
function setTimeout(fn, ms){ timers.push({ fn: fn, ms: ms, done: false }); return timers.length; }
function fireTimer(ms){
  for (var i = 0; i < timers.length; i++){
    if (timers[i].ms === ms && !timers[i].done){ timers[i].done = true; timers[i].fn(); return true; }
  }
  return false;
}

function FakeEl(tag){
  this.tagName = tag || 'div';
  this.className = '';
  this.innerHTML = '';
  this.textContent = '';
  this.style = {};
  this.children = [];
  this.parentNode = null;
  this.handlers = {};
  this._q = {};
  this.scrollTop = 0;
  this._cls = {};
  var self = this;
  this.classList = {
    add: function(c){ self._cls[c] = true; },
    remove: function(c){ delete self._cls[c]; },
    toggle: function(c, f){ if (f) self._cls[c] = true; else delete self._cls[c]; },
    contains: function(c){ return !!self._cls[c]; }
  };
}
FakeEl.prototype.querySelector = function(sel){
  if (!this._q[sel]) { var e = new FakeEl('div'); e.parentNode = this; this._q[sel] = e; }
  return this._q[sel];
};
FakeEl.prototype.querySelectorAll = function(){ return []; };
FakeEl.prototype.appendChild = function(c){ this.children.push(c); c.parentNode = this; return c; };
FakeEl.prototype.removeChild = function(c){
  var i = this.children.indexOf(c);
  if (i >= 0) this.children.splice(i, 1);
  c.parentNode = null;
  return c;
};
FakeEl.prototype.addEventListener = function(t, fn, opt){
  (this.handlers[t] = this.handlers[t] || []).push({ fn: fn, opt: opt });
};
FakeEl.prototype.removeEventListener = function(){};
FakeEl.prototype.fire = function(t, e){
  var list = this.handlers[t] || [];
  for (var i = 0; i < list.length; i++) list[i].fn(e || {});
};
FakeEl.prototype.contains = function(n){
  if (!n) return false;
  if (n === this) return true;
  for (var i = 0; i < this.children.length; i++) if (this.children[i].contains(n)) return true;
  return false;
};
FakeEl.prototype.closest = function(){ return null; };
FakeEl.prototype.setAttribute = function(){};
FakeEl.prototype.getAttribute = function(){ return ''; };
FakeEl.prototype.getBoundingClientRect = function(){ return { top:0, left:0, width:400, height:800 }; };

var registry = {};
var document = {
  getElementById: function(id){ return registry[id] || null; },
  createElement: function(tag){ return new FakeEl(tag); }
};
var ICON = { x: '<svg></svg>' };
function esc(s){ return String(s); }
function toast(){}

/* 앱 본체의 시트 컨텍스트 변수들 (closeSheetEl 이 만지작거림) */
var memberCtx = null, settleCtx = null, addCtx = null, bookCtx = null, pkgCtx = null,
    qaCtx = null, priceCtx = null, renewCtx = null, pickCtx = null, dpCtx = null, tpCtx = null,
    tmCtx = null;
/* 계정 · 클라우드 동기화 시트 컨텍스트 (closeSheetEl 이 함께 정리) */
var authCtx = null;

var voice = { kind: null };
function stopVoice(){}
function stopQaVoice(){}
""" + CODE + r"""

var fails = [], log = [];
function ok(c, n){ if (c) log.push('PASS ' + n); else fails.push('FAIL ' + n); }

function setup(){
  timers = [];
  registry = {};
  registry['sheetRoot'] = new FakeEl('div');
  sheetStack.length = 0;
  return registry['sheetRoot'];
}

/* 터치 이벤트 하나 만들기 — moves 는 [{y, t}] 목록 */
function touchEvt(target, y, t, opt){
  var e = {
    target: target,
    timeStamp: t,
    cancelable: true,
    prevented: 0,
    touches: [{ clientX: 100, clientY: y }],
    changedTouches: [{ clientX: 100, clientY: y }],
    preventDefault: function(){ e.prevented++; }
  };
  if (opt && opt.noTouches) e.touches = [];
  if (opt && opt.x !== undefined){ e.touches[0].clientX = opt.x; e.changedTouches[0].clientX = opt.x; }
  if (opt && opt.noCancel) e.cancelable = false;
  return e;
}
/* 손가락 여정: start(t=0) → moves → end. 반환: {movePrevented, endTransformed} */
function gesture(wrap, target, startY, path, opt){
  opt = opt || {};
  var t = 1000;
  wrap.fire('touchstart', touchEvt(target, startY, t));
  var prevented = 0;
  for (var i = 0; i < path.length; i++){
    t = path[i][1] === undefined ? t + 16 : path[i][1];
    var ev = touchEvt(target, path[i][0], t, opt.evt);
    wrap.fire('touchmove', ev);
    prevented += ev.prevented;
  }
  var last = path.length ? path[path.length - 1][0] : startY;
  wrap.fire('touchend', touchEvt(target, last, t + 10, opt.evt));
  return prevented;
}

/* ---------- 1. 손잡이를 잡고 120px 내리면 그 시트만 닫힌다 ---------- */
setup();
var lower = openSheet({ title: '레슨 예약' });
var upper = openSheet({ title: '시작 시간' });
ok(sheetStack.length === 2, '1-1 시트 두 장이 쌓임');
ok(registry['sheetRoot'].children.length === 2, '1-2 화면에도 두 장');
var grab = upper.sheet.querySelector('.grab');
gesture(upper.el, grab, 400, [[430, 1020], [480, 1080], [520, 1120]]);
ok(sheetStack[sheetStack.length - 1] === upper.el, '1-3 touchend 직후에는 아직 스택 맨 위(닫히는 애니메이션 중)');
ok(upper.sheet.style.transform.indexOf('translateY') === 0, '1-4 끄는 동안 시트가 손가락 따라 내려옴 (' + upper.sheet.style.transform + ')');
ok(upper.el.classList.contains('closing'), '1-5 닫히는 클래스');
ok(fireTimer(200), '1-6 200ms 뒤 스택에서 빼는 타이머');
ok(sheetStack.length === 1 && sheetStack[0] === lower.el, '1-7 위 시트만 닫히고 아래 시트는 그대로');
ok(registry['sheetRoot'].children.length === 1, '1-8 화면에서도 위 시트만 사라짐');
ok(lower.sheet.style.transform === undefined || lower.sheet.style.transform === '', '1-9 아래(이전) 시트는 움직이지 않음');

/* ---------- 2. 모자라게 내리면 제자리로 돌아온다 ---------- */
setup();
var sh = openSheet({ title: '레슨 예약' });
gesture(sh.el, sh.sheet.querySelector('.sh'), 400, [[420, 1200], [440, 1400]]);
ok(sheetStack.length === 1, '2-1 40px 는 닫히지 않음');
ok(!sh.el.classList.contains('closing'), '2-2 닫히는 클래스 없음');
ok(sh.sheet.style.transform === 'translateY(0)', '2-3 제자리로 스냅백');
ok(sh.sheet.style.transition.indexOf('.26s') > 0, '2-4 부드러운 복귀 전환');
ok(sh.el.style.background === 'rgba(9,13,18,.4)', '2-5 어둠도 원래대로');

/* ---------- 3. 짧지만 빠른 튕김은 닫힌다 ---------- */
setup();
var sh3 = openSheet({ title: '회원 상세' });
gesture(sh3.el, sh3.sheet.querySelector('.grab'), 400, [[410, 1010], [440, 1030]]);   /* 40px / 30ms = 1.33px/ms */
ok(sh3.el.classList.contains('closing'), '3-1 40px 라도 빠르게 튕기면 닫힘');
fireTimer(200);
ok(sheetStack.length === 0, '3-2 스택에서 빠짐');

/* 3-3. 느린 40px 는 안 닫힘 (이미 2번에서 확인) — 속도 기준만 따로 */
setup();
var sh3b = openSheet({ title: '회원 상세' });
gesture(sh3b.el, sh3b.sheet.querySelector('.grab'), 400, [[420, 1200], [440, 1800]]);  /* 40px / 800ms */
ok(!sh3b.el.classList.contains('closing'), '3-3 같은 40px 라도 천천히면 안 닫힘');

/* ---------- 4. 내용이 맨 위일 때 본문을 내리면 닫힌다 (사파리 새로고침 차단 포함) ---------- */
setup();
var sh4 = openSheet({ title: '레슨 예약' });
var body = sh4.sheet.querySelector('.sb');
body.scrollTop = 0;
var prev = gesture(sh4.el, body, 400, [[420, 1020], [460, 1060], [520, 1120]]);
ok(sh4.sheet.style.transform !== '' && sh4.sheet.style.transform !== undefined, '4-1 맨 위 본문을 내리면 시트가 따라 내려옴');
ok(prev >= 2, '4-2 끌어내리는 동안 touchmove preventDefault (사파리 당겨서 새로고침 차단) — ' + prev + '회');
ok(sh4.el.classList.contains('closing'), '4-3 120px 내리면 닫힘');

/* ---------- 5. 내용 중간(scrollTop > 0)에서 내리면 그냥 스크롤 ---------- */
setup();
var sh5 = openSheet({ title: '레슨 예약' });
var body5 = sh5.sheet.querySelector('.sb');
body5.scrollTop = 60;
var p5 = gesture(sh5.el, body5, 400, [[420, 1020], [500, 1060]]);
ok(p5 === 0, '5-1 스크롤 중에는 preventDefault 하지 않음 (부드러운 스크롤 유지)');
ok(!sh5.sheet.style.transform, '5-2 시트도 움직이지 않음');
ok(!sh5.el.classList.contains('closing') && sheetStack.length === 1, '5-3 닫히지 않음');

/* 5-4. 내용 중간이어도 머리·바닥 버튼줄을 끌면 닫힌다 (사파리 새로고침 차단) */
var sh5b = sh5;
var foot = sh5b.sheet.querySelector('.sf');
var prev5b = gesture(sh5b.el, foot, 400, [[420, 1020], [460, 1060], [520, 1120]]);
ok(sh5b.el.classList.contains('closing'), '5-4 본문이 스크롤된 상태라도 바닥 버튼줄을 끌면 닫힘');
ok(prev5b >= 2, '5-5 그때도 preventDefault');

/* ---------- 6. 위로 끄는 동작은 시트를 닫지 않는다 ---------- */
setup();
var sh6 = openSheet({ title: '레슨 예약' });
var body6 = sh6.sheet.querySelector('.sb');
body6.scrollTop = 0;
var p6 = gesture(sh6.el, body6, 500, [[460, 1020], [400, 1060]]);
ok(p6 === 0, '6-1 위로 끌면 preventDefault 없음');
ok(!sh6.sheet.style.transform, '6-2 시트가 안 따라옴');
ok(sheetStack.length === 1, '6-3 닫히지 않음');

/* ---------- 7. 입력칸에서 시작한 끌기는 시트를 움직이지 않되 새로고침은 막는다 ---------- */
setup();
var sh7 = openSheet({ title: '레슨 예약' });
var field = new FakeEl('textarea');
field.closest = function(sel){ return sel.indexOf('textarea') >= 0 ? field : null; };
var p7 = gesture(sh7.el, field, 400, [[430, 1020], [520, 1060]]);
ok(p7 >= 1, '7-1 입력칸에서도 당겨서 새로고침은 막음');
ok(!sh7.sheet.style.transform, '7-2 시트는 따라 내려오지 않음');
ok(sheetStack.length === 1, '7-3 닫히지 않음');

/* ---------- 8. 가장 위 시트만 반응한다 ---------- */
setup();
var a = openSheet({ title: '아래' });
var b = openSheet({ title: '위' });
gesture(a.el, a.sheet.querySelector('.grab'), 400, [[430, 1020], [560, 1080]]);
ok(!a.sheet.style.transform, '8-1 아래 시트는 끌려도 움직이지 않음');
ok(sheetStack.length === 2, '8-2 아래 시트가 닫히지 않음');
ok(!a.el.classList.contains('closing'), '8-3 닫히는 클래스도 없음');

/* ---------- 9. 위 시트를 닫은 뒤에는 아래 시트를 밀어 닫을 수 있다 ---------- */
gesture(b.el, b.sheet.querySelector('.grab'), 400, [[430, 1020], [560, 1080]]);
fireTimer(200);
ok(sheetStack.length === 1 && sheetStack[0] === a.el, '9-1 위 시트 닫힘');
gesture(a.el, a.sheet.querySelector('.grab'), 400, [[440, 1020], [580, 1080]]);
ok(a.el.classList.contains('closing'), '9-2 이제 아래 시트가 반응');
fireTimer(200);
ok(sheetStack.length === 0, '9-3 마지막 시트까지 닫힘');

/* ---------- 10. 빈 시트/바깥 여백에서의 끌기는 시트를 움직이지 않는다 ---------- */
setup();
var sh10 = openSheet({ title: '레슨 예약' });
var p10 = gesture(sh10.el, sh10.el, 300, [[340, 1020], [430, 1060]]);
ok(!sh10.sheet.style.transform, '10-1 바깥 여백을 끌어도 시트는 안 따라옴');
ok(p10 >= 1, '10-2 바깥 여백에서도 새로고침은 막음');
ok(sheetStack.length === 1, '10-3 닫히지 않음');

/* ---------- 11. 상수·리스너 계약 ---------- */
ok(SHEET_DISMISS_PX === 76, '11-1 닫힘 기준 76px');
ok(SHEET_FLICK_V > 0 && SHEET_FLICK_DY > 0, '11-2 튕김 기준값');
setup();
var sh11 = openSheet({ title: 'x' });
var hs = sh11.el.handlers;
ok((hs.touchstart || []).length === 1, '11-3 touchstart 리스너');
ok((hs.touchmove || []).length === 1, '11-4 touchmove 리스너');
ok(hs.touchmove[0].opt && hs.touchmove[0].opt.passive === false, '11-5 touchmove 는 passive:false (preventDefault 가능)');
ok((hs.touchend || []).length === 1 && (hs.touchcancel || []).length === 1, '11-6 touchend · touchcancel 리스너');

/* 취소(전화 수신 등) 되면 제자리로 */
setup();
var sh12 = openSheet({ title: 'y' });
sh12.el.fire('touchstart', touchEvt(sh12.sheet.querySelector('.grab'), 400, 0));
sh12.el.fire('touchmove', touchEvt(sh12.sheet.querySelector('.grab'), 480, 40));
sh12.el.fire('touchcancel', {});
ok(sh12.sheet.style.transform === 'translateY(0)' && sheetStack.length === 1, '11-7 touchcancel 이면 제자리로');

JSON.stringify({ pass: log, fail: fails });
"""

ctx = quickjs.Context()
data = json.loads(ctx.eval(HARNESS))
for l in data['pass']:
    print(l)
if data['fail']:
    print()
    for l in data['fail']:
        print(l)
    print('\n%d FAILED / %d passed' % (len(data['fail']), len(data['pass'])))
    sys.exit(1)

# ---------- HTML / CSS 계약 ----------
checks = []
def ok(c, n):
    checks.append((bool(c), n))

head = HTML[:HTML.index('</style>')]
ok('html,body{margin:0;padding:0;height:100%;overscroll-behavior:none;overscroll-behavior-y:none}' in head,
   '12-1 html·body 당겨서 새로고침 차단 (overscroll-behavior)')
ok('overflow:hidden;overscroll-behavior:none;' in head, '12-2 #app 에도 overscroll-behavior:none')
sw = re.search(r'\.sheetwrap\{[^}]*\}', head).group(0)
ok('overscroll-behavior:none' in sw, '12-3 시트 뒤 어둠(.sheetwrap)에도 적용')
ok('.sheetwrap.closing{pointer-events:none}' in head, '12-4 닫히는 동안 뒤 화면 탭 차단')
sh_rule = re.search(r'\.sheet\{[^}]*\}', head).group(0)
ok('overscroll-behavior:contain' in sh_rule, '12-5 시트 자체는 contain')
sb_rule = re.search(r'\.sheet \.sb\{[^}]*\}', head).group(0)
ok('overscroll-behavior:contain' in sb_rule, '12-6 스크롤 영역(.sb)은 contain — 바깥으로 새지 않음')
ok('touch-action:pan-y' in sw or 'touch-action:pan-y' in sh_rule, '12-7 세로 스크롤은 그대로 허용(touch-action)')

ok('function attachSheetGestures' in HTML, '12-8 제스처 함수 존재')
ok('attachSheetGestures(wrap, sheet);' in HTML, '12-9 openSheet 이 모든 시트에 적용')
ok('closeSheetEl(w); }, 200);' in HTML, '12-10 닫힘 애니메이션 뒤 정리')
ok("wrap.addEventListener('touchmove', move, { passive: false });" in HTML, '12-11 비수동 touchmove 로 preventDefault')
ok('sheetStack[sheetStack.length - 1] === wrap' in HTML, '12-12 맨 위 시트만 반응')
ok('var SHEET_DISMISS_PX = 76;' in HTML and 'var SHEET_FLICK_V = 0.5;' in HTML, '12-13 판정 기준값이 코드에 상수로 있음')

for c, n in checks:
    print(('PASS ' if c else 'FAIL ') + n)

failed = [n for c, n in checks if not c]
if failed:
    print('\n%d FAILED (HTML/CSS)' % len(failed))
    sys.exit(1)
print('\nALL %d PASSED' % (len(data['pass']) + len(checks)))
