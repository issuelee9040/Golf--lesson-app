#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""아이폰 사파리 더블탭 · 핀치(두 손가락) 확대 방지 검사.

이시훈 님 요청: 홈 화면에 추가해 앱처럼 쓰는데, 화면을 한 번 톡 치고 다시 치면(더블탭)
또는 두 손가락으로 벌리면(핀치) 화면이 확대돼 앱이 아닌 웹페이지처럼 느껴진다.

넣은 방법 3가지
  1) <meta name="viewport"> 에 maximum-scale=1 · user-scalable=no
     (안드로이드 크롬 등은 이 값으로 확대를 막습니다. 아이폰 사파리는 접근성 때문에 이 값을
      무시하므로 2)·3) 이 실제로 막습니다)
  2) CSS touch-action:manipulation — 더블탭 확대를 끄고 세로·가로 스크롤은 그대로 허용
  3) <head> 스크립트의 gesturestart · gesturechange preventDefault — 핀치 확대 차단

이 검사가 지키는 것
  1) viewport 메타: 확대 금지 2값 + 기존 값(width·initial-scale·viewport-fit) 유지
  2) touch-action: html·body 와 모든 요소(*)에 manipulation
  3) 스크롤·밀어 닫기 규칙이 그대로 우선하는지 (.sheet · .quick textarea · .sheet .grab)
  4) gesturestart·gesturechange 리스너: passive:false + preventDefault, touch 이벤트와 분리
  5) 확대를 막으면서 스크롤을 막는 실수가 없는지 (touch-action:none·touchmove 전면 차단 없음)
  6) 설계서 기록
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
    """CSS 에서 해당 선택자 규칙의 선언부 (없으면 '')"""
    m = re.search(r'(^|\n)' + re.escape(sel) + r'\{([^}]*)\}', CSS)
    return m.group(2) if m else ''


def all_rules(sel):
    """같은 선택자로 여러 번 쓴 규칙 전부 (선언부 문자열 목록)"""
    return [m.group(2) for m in re.finditer(r'(^|\n)' + re.escape(sel) + r'\{([^}]*)\}', CSS)]


VP = (re.search(r'<meta name="viewport" content="([^"]+)"', HEAD) or [None, ''])[1]
VP_PARTS = [x.strip() for x in VP.split(',')]

# ══════════════════════════════════════════════════════════
# 1. viewport 메타
# ══════════════════════════════════════════════════════════
ok('1-1 maximum-scale=1 로 확대 상한을 막음', 'maximum-scale=1' in VP_PARTS, VP)
ok('1-2 user-scalable=no 로 손가락 확대를 막음', 'user-scalable=no' in VP_PARTS, VP)
ok('1-3 기존 값 유지 — width=device-width', 'width=device-width' in VP_PARTS, VP)
ok('1-4 기존 값 유지 — initial-scale=1', 'initial-scale=1' in VP_PARTS, VP)
ok('1-5 기존 값 유지 — viewport-fit=cover (상단 안전 여백)', 'viewport-fit=cover' in VP_PARTS, VP)
ok('1-6 viewport 메타는 <style> 보다 앞(첫 페인트에 적용)', HTML.index('name="viewport"') < HTML.index('<style>'))

# ══════════════════════════════════════════════════════════
# 2. touch-action:manipulation — 더블탭 확대 차단
# ══════════════════════════════════════════════════════════
ok('2-1 html·body 에 touch-action:manipulation',
   any('touch-action:manipulation' in r for r in all_rules('html,body')), str(all_rules('html,body')))
ok('2-2 모든 요소(*)에 touch-action:manipulation',
   'touch-action:manipulation' in rule('*'), rule('*'))
# 당겨서 새로고침 차단 규칙은 그대로 (같은 html,body 선택자를 두 규칙으로 나눠 씀)
ok('2-3 html·body 당겨서 새로고침 차단 규칙은 그대로',
   'html,body{margin:0;padding:0;height:100%;overscroll-behavior:none;overscroll-behavior-y:none}' in CSS)
ok('2-4 manipulation 은 스크롤을 막지 않는 값 (none·pan-y 단독으로 바꾸지 않음)',
   not any('touch-action:none' in r for r in all_rules('html,body')))

# ══════════════════════════════════════════════════════════
# 3. 스크롤·밀어 닫기 규칙이 그대로 우선하는지 (구체성 높은 규칙)
# ══════════════════════════════════════════════════════════
sw = rule('.sheetwrap')
sh = rule('.sheet')
sb = rule('.sheet .sb')
ok('3-1 시트 뒤 어둠(.sheetwrap)은 세로 스크롤 허용(touch-action:pan-y)',
   'touch-action:pan-y' in sw, sw)
ok('3-2 시트(.sheet)는 세로 스크롤 허용(touch-action:pan-y)', 'touch-action:pan-y' in sh, sh)
ok('3-3 시트 안에서 핀치 확대는 허용하지 않는다(pinch-zoom 없음)',
   'pinch-zoom' not in sw and 'pinch-zoom' not in sh, sw + ' | ' + sh)
ok('3-4 시트 스크롤 영역(.sb)은 그대로 스크롤', 'overscroll-behavior:contain' in sb and 'overflow-y:auto' in sb, sb)
ok('3-5 손잡이(.sheet .grab)는 끌기용 touch-action:none 유지',
   'touch-action:none' in rule('.sheet .grab'), rule('.sheet .grab'))
ok('3-6 한 줄 간편 입력 textarea 는 칸 안 스크롤 유지(touch-action:pan-y)',
   '-webkit-overflow-scrolling:touch;touch-action:pan-y;overscroll-behavior:contain;resize:none}' in CSS)
ok('3-7 입력칸·textarea 에 touch-action:none 을 걸지 않았다',
   not re.search(r'[^{}]*textarea[^{}]*\{[^}]*touch-action:none', CSS))
ok('3-8 * 규칙보다 시트 규칙이 뒤에 있어 우선한다',
   CSS.index('*{touch-action:manipulation}') < CSS.index('.sheetwrap{'))

# ══════════════════════════════════════════════════════════
# 4. gesturestart · gesturechange 차단 (<head> 스크립트)
# ══════════════════════════════════════════════════════════
BOOT = HEAD[HEAD.index('<script>'):HEAD.index('</script>')]
ok('4-1 gesturestart 리스너가 있다', "addEventListener('gesturestart'" in BOOT)
ok('4-2 gesturechange 도 막는다(확대가 이어지는 동안)', "addEventListener('gesturechange'" in BOOT)
ok('4-3 passive:false 로 단다 (그래야 preventDefault 가 먹는다)', 'passive: false' in BOOT)
ok('4-4 핸들러가 e.preventDefault() 를 부른다', 'e.preventDefault()' in BOOT)
ok('4-5 한 손가락 touch 이벤트는 건드리지 않는다(시트 밀어 닫기와 분리)',
   "'touchstart'" not in BOOT and "'touchmove'" not in BOOT and "'touchend'" not in BOOT)
ok('4-6 제스처 차단은 시트를 닫거나 화면을 다시 그리지 않는다',
   'closeSheet' not in BOOT and 'render(' not in BOOT)
ok('4-7 <head> 라 첫 터치 전에 걸린다', HTML.index("'gesturestart'") < HTML.index('<style>'))

# ══════════════════════════════════════════════════════════
# 5. 실제 코드 실행 — 핸들러가 preventDefault 를 부르는지
# ══════════════════════════════════════════════════════════
ZOOMJS = BOOT[BOOT.index('/* 아이폰 사파리 두 손가락'):]   # 확대 차단 스크립트만 실행
STUBS = r"""
var __l = {}, __called = 0;
var document = {
  addEventListener:function(t, f, o){ __l[t] = { f:f, o:o }; },
  documentElement:{ setAttribute:function(){}, },
  querySelector:function(){ return null; }
};
var localStorage = { getItem:function(){ return null; }, setItem:function(){}, removeItem:function(){} };
"""
ctx = quickjs.Context()
ctx.eval(STUBS + ZOOMJS)
ok('5-1 gesturestart 리스너가 등록됨', ctx.eval("!!__l.gesturestart"))
ok('5-2 gesturechange 리스너가 등록됨', ctx.eval("!!__l.gesturechange"))
ok('5-3 옵션이 { passive:false }', ctx.eval("__l.gesturestart.o && __l.gesturestart.o.passive === false"))
ctx.eval("""
var __pd = 0;
__l.gesturestart.f({ cancelable:true, preventDefault:function(){ __pd++; } });
__l.gesturechange.f({ cancelable:true, preventDefault:function(){ __pd++; } });
""")
ok('5-4 두 제스처 이벤트 모두 preventDefault 를 부름', ctx.eval("__pd") == 2, ctx.eval("__pd"))
ctx.eval("""
var __pd2 = 0;
__l.gesturestart.f({ cancelable:false, preventDefault:function(){ __pd2++; } });
""")
ok('5-5 취소할 수 없는 이벤트에서는 조용히 넘어감(오류 없음)', ctx.eval("__pd2") == 0)

# ══════════════════════════════════════════════════════════
# 6. 설계서 기록
# ══════════════════════════════════════════════════════════
SPEC = open('/workspace/golf-lesson-app/spec.md', encoding='utf-8').read()
ok('6-1 설계서에 더블탭·핀치 확대 방지 항목', '핀치' in SPEC and '더블탭' in SPEC)
ok('6-2 설계서에 touch-action:manipulation 규칙', 'touch-action:manipulation' in SPEC)
ok('6-3 설계서에 gesturestart 규칙', 'gesturestart' in SPEC)
ok('6-4 설계서에 이 검사 파일 이름', 'tests/zoom_lock_test.py' in SPEC)

# ══════════════════════════════════════════════════════════
fails = [x for x in OUT if not x[1]]
for n, c, d in OUT:
    print(('PASS ' if c else 'FAIL ') + n + (('  <- ' + str(d)) if (d and not c) else ''))
print('\n%d passed / %d total' % (len(OUT) - len(fails), len(OUT)))
sys.exit(1 if fails else 0)
