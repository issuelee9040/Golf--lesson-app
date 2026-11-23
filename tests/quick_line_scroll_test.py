#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""한 줄 간편입력 칸의 스크롤 · 실수로 닫힐 때 글 보호를 실제 코드로 검사한다.

- 여러 줄이 넘친 textarea 안에서는 시트가 안 따라 내려오고, 입력칸이 스크롤된다
  (touchmove preventDefault 를 하지 않아야 사파리에서 입력칸 스크롤이 살아 있음)
- 입력칸 맨 위에서 더 내리는 동작만 '당겨서 새로고침'을 막는다
- 한 줄짜리 input / 넘치지 않는 칸은 예전처럼 시트를 끌지 않고 새로고침만 막는다
- 적어 둔 글이 있으면 바깥을 눌러도 / 밀어도 바로 닫히지 않고 한 번 물어본다
- CSS 계약(max-height · overflow-y · touch-action · overscroll-behavior)
"""
import json, sys
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
  this.style = {};
  this.children = [];
  this.parentNode = null;
  this.handlers = {};
  this._q = {};
  this.scrollTop = 0;
  this.scrollHeight = 100;
  this.clientHeight = 100;
  this.value = '';
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
  if (!this._q[sel]) {
    var e = new FakeEl(sel === '.grab' ? 'div' : 'div');
    e.parentNode = this;
    this._q[sel] = e;
  }
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

var memberCtx = null, settleCtx = null, addCtx = null, bookCtx = null, pkgCtx = null,
    qaCtx = null, priceCtx = null, renewCtx = null, pickCtx = null, dpCtx = null, tpCtx = null,
    tmCtx = null;
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
  discardTarget = null;
  return registry['sheetRoot'];
}

/* 입력칸 흉내 — closest('textarea') 로 자기 자신을 돌려준다 */
function fieldEl(tag, sh, ch, top){
  var el = new FakeEl(tag);
  el.scrollHeight = sh; el.clientHeight = ch; el.scrollTop = top || 0;
  el.closest = function(sel){ return sel.indexOf('textarea') >= 0 || sel.indexOf('input') >= 0 ? el : null; };
  return el;
}

function touchEvt(target, y, t){
  var e = {
    target: target, timeStamp: t, cancelable: true, prevented: 0,
    touches: [{ clientX: 100, clientY: y }],
    changedTouches: [{ clientX: 100, clientY: y }],
    preventDefault: function(){ e.prevented++; }
  };
  return e;
}
function gesture(wrap, target, startY, path){
  var t = 1000, prevented = 0;
  wrap.fire('touchstart', touchEvt(target, startY, t));
  for (var i = 0; i < path.length; i++){
    t += 16;
    var ev = touchEvt(target, path[i], t);
    wrap.fire('touchmove', ev);
    prevented += ev.prevented;
  }
  var last = path.length ? path[path.length - 1] : startY;
  wrap.fire('touchend', touchEvt(target, last, t + 10));
  return prevented;
}

/* ---------- 1. 넘치는 textarea 안에서는 입력칸이 스크롤된다 ---------- */
setup();
var sh1 = openSheet({ title: '회원 추가' });
var ta1 = fieldEl('textarea', 320, 96, 60);          /* 3줄 넘게 적어 스크롤 여지 있음 */
var p1 = gesture(sh1.el, ta1, 400, [380, 360, 340]);  /* 위로 = 아래 내용 보기 */
ok(p1 === 0, '1-1 넘치는 입력칸에서 위로 끌면 preventDefault 없음 (입력칸 스크롤 살아 있음) — ' + p1 + '회');
ok(!sh1.sheet.style.transform, '1-2 시트는 따라 내려오지 않음');
ok(!sh1.el.classList.contains('closing'), '1-3 시트도 닫히지 않음');

var p1b = gesture(sh1.el, ta1, 300, [340, 380]);      /* 아래로 = 위 내용 보기 (스크롤 여지 있음) */
ok(p1b === 0, '1-4 스크롤 여지가 있으면 아래로 끌어도 입력칸이 스크롤 — ' + p1b + '회');

/* ---------- 2. 맨 위에서 더 내리면 새로고침만 막는다 ---------- */
setup();
var sh2 = openSheet({ title: '회원 추가' });
var ta2 = fieldEl('textarea', 320, 96, 0);            /* 맨 위 */
var p2 = gesture(sh2.el, ta2, 300, [340, 390, 450]);
ok(p2 >= 2, '2-1 맨 위에서 더 내리면 touchmove preventDefault (사파리 당겨서 새로고침 차단) — ' + p2 + '회');
ok(!sh2.sheet.style.transform, '2-2 그래도 시트는 끌려 내려오지 않음');
ok(!sh2.el.classList.contains('closing'), '2-3 시트가 닫히지 않음');

/* ---------- 3. 한 줄 입력 · 넘치지 않는 칸은 예전 그대로 ---------- */
setup();
var sh3 = openSheet({ title: '레슨 빠른 추가' });
var inp = fieldEl('input', 40, 40, 0);
var p3 = gesture(sh3.el, inp, 300, [340, 400]);
ok(p3 >= 2, '3-1 한 줄 입력칸에서 끌면 새로고침만 막음');
ok(!sh3.sheet.style.transform, '3-2 시트는 안 움직임');

/* ---------- 4. 적어 둔 글이 있으면 바깥을 눌러도 바로 안 닫힌다 ---------- */
setup();
var sh4 = openSheet({ title: '회원 추가' });
registry['quickLine'] = new FakeEl('textarea');
registry['quickLine'].value = '김민수 4/10회\n박영희 잔여 4회\n이서연 55회 여 판교';
sh4.el.__guardClose = function(){
  return registry['quickLine'].value.trim() ? '한 줄 간편 입력에 적은 내용이 아직 저장되지 않았어요.' : '';
};
var before = sheetStack.length;
sh4.el.fire('click', { target: sh4.el });
ok(sheetStack.length === before + 1, '4-1 바깥을 눌러도 원래 시트는 남고 확인 시트가 위에 뜸');
var confirm = sheetStack[sheetStack.length - 1];
ok(confirm !== sh4.el, '4-2 맨 위는 확인 시트');
ok(confirm.children[0].querySelector('h3').textContent === '작성 중인 내용이 있어요', '4-3 확인 시트 제목');
var foot = confirm.children[0].querySelector('.sf');
ok(String(foot.innerHTML).indexOf('계속 작성') >= 0 && String(foot.innerHTML).indexOf('그래도 닫기') >= 0,
   '4-4 계속 작성 · 그래도 닫기 두 버튼');
discardStay();
closeSheetEl(confirm);
ok(sheetStack.indexOf(sh4.el) >= 0, '4-5 계속 작성 → 원래 시트 유지 (적은 글 그대로)');

/* ---------- 5. '그래도 닫기'는 둘 다 닫는다 ---------- */
setup();
var sh5 = openSheet({ title: '회원 추가' });
sh5.el.__guardClose = function(){ return '적은 내용이 있어요'; };
sh5.el.fire('click', { target: sh5.el });
var conf5 = sheetStack[sheetStack.length - 1];
discardAndClose(conf5);
ok(sheetStack.length === 0, '5-1 그래도 닫기 → 확인 시트와 원래 시트 모두 닫힘');

/* ---------- 6. 적은 글이 없으면 그냥 닫힌다 ---------- */
setup();
var sh6 = openSheet({ title: '회원 추가' });
registry['quickLine'] = new FakeEl('textarea');
registry['quickLine'].value = '   ';
sh6.el.__guardClose = function(){ return registry['quickLine'].value.trim() ? 'x' : ''; };
sh6.el.fire('click', { target: sh6.el });
ok(sheetStack.length === 0, '6-1 빈 칸이면 확인 없이 바로 닫힘');

/* ---------- 7. 밀어서 닫을 때도 확인 ---------- */
setup();
var sh7 = openSheet({ title: '회원 추가' });
sh7.el.__guardClose = function(){ return '적은 내용이 있어요'; };
var grab = sh7.sheet.querySelector('.grab');
gesture(sh7.el, grab, 400, [460, 540]);
ok(!sh7.el.classList.contains('closing'), '7-1 글이 있으면 밀어도 닫히지 않음');
ok(sh7.sheet.style.transform === 'translateY(0)', '7-2 제자리로 돌아옴');
ok(sheetStack.length === 2, '7-3 대신 확인 시트가 뜸');

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

# ---------- CSS / HTML 계약 ----------
CSS = HTML[HTML.index('<style>'):HTML.index('</style>')]
checks = []
def ok(c, n):
    checks.append((bool(c), n))

ok('.quick textarea{min-height:78px;max-height:150px;background:var(--field);overflow-y:auto;' in CSS,
   '8-1 한 줄 입력 칸은 최대 150px 에서 안에서 스크롤')
ok('-webkit-overflow-scrolling:touch;touch-action:pan-y;overscroll-behavior:contain;resize:none}' in CSS,
   '8-2 아이폰 부드러운 스크롤 · 당겨서 새로고침 차단')
ok('id="quickLine" rows="3" placeholder="김민수' in HTML, '8-3 회원 추가 한 줄 입력은 3줄 높이')
ok("sh.el.__guardClose = function(){" in HTML, '8-4 회원 추가 시트에 글 보호 장치')
ok("document.getElementById('quickLine')" in HTML and "document.getElementById('qaLine')" in HTML,
   '8-5 두 한 줄 입력(회원·레슨) 모두 보호')
ok('function fieldCanScroll(el, dy){' in HTML, '8-6 입력칸 스크롤 여지 판단 함수')
ok('fieldCanScroll(st.fieldEl, dy)' in HTML, '8-7 스크롤 여지가 있으면 손대지 않음')
ok('if (st.backdrop){' in HTML, '8-8 바깥 여백은 예전처럼 새로고침만 막음')

for c, n in checks:
    print(('PASS ' if c else 'FAIL ') + n)

failed = [n for c, n in checks if not c]
if failed:
    print('\n%d FAILED (CSS/HTML)' % len(failed))
    sys.exit(1)
print('\nALL %d PASSED' % (len(data['pass']) + len(checks)))
