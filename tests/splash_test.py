#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""앱 실행 스플래시(약 3.5초 · 탭하면 바로 넘어감)를 실제 코드로 검사한다.

- 스플래시는 3500ms 뒤 스스로 사라지고, 440ms 전환 뒤 hidden 으로 감춰지는지
- 탭(pointerdown/click)·Enter/Space 로 즉시 넘어가는지
- 두 번 눌러도 한 번만 전환되는지(idempotent)
- 요소가 없어도 예외 없이 지나가는지
- HTML/CSS 계약(전체 화면 덮기, 3.5초 상수, 420ms 페이드, reduced-motion)이 남아 있는지
"""
import sys, json
import quickjs

HTML = open('/workspace/golf-lesson-app/prototype.html', encoding='utf-8').read()

start = HTML.index('var SPLASH_MS = 3500;')
end = HTML.index('/* =========================================================\n   시작')
CODE = HTML[start:end]

HARNESS = r"""
/* ---------- 최소 DOM 스텁 ---------- */
var timers = [];
function setTimeout(fn, ms){ timers.push({ fn: fn, ms: ms, done: false }); return timers.length; }
function pending(ms){
  var n = 0;
  for (var i = 0; i < timers.length; i++) if (timers[i].ms === ms && !timers[i].done) n++;
  return n;
}
function fire(ms){
  for (var i = 0; i < timers.length; i++){
    if (timers[i].ms === ms && !timers[i].done){ timers[i].done = true; timers[i].fn(); return true; }
  }
  return false;
}
function makeEl(){
  var el = {
    hidden: false, attrs: {}, cls: {}, handlers: {},
    classList: {
      add: function(c){ el.cls[c] = true; },
      remove: function(c){ delete el.cls[c]; },
      contains: function(c){ return !!el.cls[c]; }
    },
    getAttribute: function(k){ return el.attrs[k] === undefined ? null : el.attrs[k]; },
    setAttribute: function(k, v){ el.attrs[k] = v; },
    removeAttribute: function(k){ delete el.attrs[k]; },
    addEventListener: function(t, fn){ (el.handlers[t] = el.handlers[t] || []).push(fn); },
    fire: function(t, e){ (el.handlers[t] || []).forEach(function(fn){ fn(e || {}); }); }
  };
  return el;
}
var registry = {};
var document = { getElementById: function(id){ return registry[id] || null; } };
""" + CODE + r"""

var fails = [], log = [];
function ok(c, n){ if (c) log.push('PASS ' + n); else fails.push('FAIL ' + n); }
function reset(){
  timers = []; registry = {};
  var el = makeEl(); registry['splash'] = el; return el;
}

/* 1. 시작하면 3.5초 타이머 + 탭/키 리스너가 붙는다 */
var el = reset();
startSplash();
ok(pending(3500) === 1, '1-1 시작하면 3500ms 타이머 1개');
ok((el.handlers.pointerdown || []).length === 1, '1-2 탭(pointerdown) 리스너');
ok((el.handlers.click || []).length === 1, '1-3 클릭 리스너');
ok((el.handlers.keydown || []).length === 1, '1-4 키보드 리스너');
ok(el.hidden === false && !el.cls.out, '1-5 처음에는 보이는 상태');

/* 2. 3.5초가 지나면 스스로 사라진다 (420ms 전환 + 여유 = 440ms 뒤 hidden) */
fire(3500);
ok(el.getAttribute('data-done') === '1', '2-1 3.5초 뒤 전환 시작');
ok(el.cls.out === true, '2-2 페이드 아웃 클래스(out)');
ok(el.getAttribute('aria-hidden') === 'true', '2-3 스크린리더에서 숨김');
ok(el.hidden === false, '2-4 전환 중에는 아직 hidden 아님');
ok(pending(440) === 1, '2-5 440ms 뒤 감추는 타이머');
fire(440);
ok(el.hidden === true, '2-6 440ms 뒤 hidden');

/* 3. 스플래시를 탭하면 기다리지 않고 바로 넘어간다 */
el = reset();
startSplash();
el.fire('pointerdown');
ok(el.getAttribute('data-done') === '1' && el.cls.out === true, '3-1 탭 즉시 전환');
ok(pending(3500) === 1, '3-2 자동 타이머는 그대로 남아 있어도 무해');
fire(3500);
ok(el.cls.out === true, '3-3 자동 타이머가 뒤늦게 와도 상태 그대로');
ok(pending(440) === 1, '3-4 감추는 타이머는 한 번만');

/* 4. 클릭 경로도 같은 동작, 두 번 눌러도 한 번만 */
el = reset();
startSplash();
el.fire('click');
el.fire('pointerdown');
el.fire('click');
ok(pending(440) === 1, '4-1 여러 번 눌러도 감추는 타이머 1개');

/* 5. Enter / Space 로도 넘어가고, 다른 키는 그대로 */
el = reset();
startSplash();
el.fire('keydown', { key: 'a' });
ok(!el.cls.out, '5-1 다른 키는 무시');
el.fire('keydown', { key: ' ' });
ok(el.cls.out === true, '5-2 Space 로 넘어감');

el = reset();
startSplash();
el.fire('keydown', { key: 'Enter' });
ok(el.cls.out === true, '5-3 Enter 로 넘어감');

/* 6. 요소가 없어도 예외 없이 지나간다 */
timers = []; registry = {};
var threw = false;
try { startSplash(); } catch (e) { threw = true; }
ok(!threw, '6-1 스플래시 요소가 없어도 안전');
ok(timers.length === 0, '6-2 요소가 없으면 타이머도 안 만든다');

JSON.stringify({ pass: log, fail: fails, ms: SPLASH_MS, fade: SPLASH_FADE });
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

ok(data['ms'] == 3500, '7-1 스플래시 표시 시간 3.5초')
ok(data['fade'] >= 420, '7-2 전환(420ms)보다 감추는 타이머가 늦다')
ok('id="splash"' in HTML and 'class="splash"' in HTML, '7-3 본문 맨 앞에 스플래시 마크업')
ok('role="status"' in HTML and '레슨 관리 앱을 여는 중' in HTML, '7-4 스크린리더용 상태 라벨')
ok(HTML.split('<body>')[1].lstrip().startswith('<div class="splash"'), '7-5 스플래시가 body 의 첫 요소')
ok(HTML.index('id="splash"') < HTML.index('id="app"'), '7-6 앱 본문보다 먼저 그려진다')
ok('position:fixed;inset:0;z-index:9999' in HTML, '7-7 화면 전체를 덮는 고정 레이어')
ok('height:100dvh' in HTML, '7-8 아이폰 동적 뷰포트(100dvh)')
ok('env(safe-area-inset-top)' in HTML and 'env(safe-area-inset-bottom)' in HTML, '7-9 안전 영역 패딩')
ok('152deg,#128A53 0%,#0C6B41 52%,#08492C 100%' in HTML, '7-10 히어로와 같은 에메랄드 그라데이션')
ok('transition:opacity 420ms ease' in HTML, '7-11 420ms 페이드 전환')
ok('prefers-reduced-motion:reduce' in HTML, '7-12 모션 줄이기 대응')

for c, n in checks:
    print(('PASS ' if c else 'FAIL ') + n)

failed = [n for c, n in checks if not c]
if failed:
    print('\n%d FAILED (HTML/CSS)' % len(failed))
    sys.exit(1)
print('\nALL %d PASSED' % (len(data['pass']) + len(checks)))
