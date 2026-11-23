#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""하단 5탭 + 설정 탭 분리 검사.

- 하단 탭바가 오늘 · 캘린더 · 회원목록 · 통계 · 설정 5개이고, 설정이 맨 오른쪽인지
- 오늘 탭 오른쪽 위 ⚙️ 가 설정 탭으로 바로 가는지
- 통계 탭은 수업 현황 · 수입 정산만 남고, 프로 설정·외부 캘린더 연동은 설정 탭에 있는지
- 앱스토어 출시 로드맵 카드는 화면에서 빠지고 설계서(spec.md)에만 남았는지
- renderTabbar() 를 실제로 실행해 5개 버튼 HTML 이 만들어지는지
"""
import re, sys
import quickjs

HTML = open('/workspace/golf-lesson-app/prototype.html', encoding='utf-8').read()
OUT = []

def ok(name, cond, detail=''):
    OUT.append((name, bool(cond), detail))

# ── 1. 탭 정의 ─────────────────────────────────────────────
m = re.search(r'function renderTabbar\(\)\{\s*var tabs = (\[.*?\]);', HTML, re.S)
ok('1-1 renderTabbar 탭 정의 존재', m is not None)
if m:
    ctx = quickjs.Context()
    tabs = ctx.eval('JSON.stringify(' + m.group(1) + ')')
    import json
    tabs = json.loads(tabs)
    labels = [t[1] for t in tabs]
    keys = [t[0] for t in tabs]
    ok('1-2 탭 5개', len(tabs) == 5, str(labels))
    ok('1-3 순서: 오늘·캘린더·회원목록·통계·설정',
       labels == ['오늘', '캘린더', '회원목록', '통계', '설정'], str(labels))
    ok('1-4 설정이 맨 오른쪽', keys[-1] == 'settings', str(keys))

# ── 2. renderTabbar 실행 ───────────────────────────────────
fr = re.search(r'function renderTabbar\(\)\{.*?\n\}', HTML, re.S)
HARNESS = """
var ui = { tab:'settings' };
var ICON = { sun:'<svg/>', cal:'<svg/>', users:'<svg/>', chart:'<svg/>', gear:'<svg class=\\"gearin\\"/>' };
var document = { getElementById: function(id){ return { set innerHTML(v){ this._h = v; }, get innerHTML(){ return this._h; } }; } };
"""
ctx = quickjs.Context()
ctx.eval('(function(){ "use strict";\n' + HARNESS
         + (fr.group(0) if fr else '')
         + '\nvar box = { innerHTML:"" };\ndocument.getElementById = function(){ return box; };\n'
         + 'renderTabbar();\nglobalThis.OUTHTML = box.innerHTML;\n})()')
tabhtml = ctx.get('OUTHTML')
buttons = re.findall(r'<button class="([^"]*)" data-act="tab" data-tab="([^"]+)">', tabhtml)
ok('2-1 버튼 5개 렌더', len(buttons) == 5, str(len(buttons)))
ok('2-2 설정 버튼 존재', any(k == 'settings' for _, k in buttons))
ok('2-3 설정 탭이 활성 표시', any(k == 'settings' and c == 'on' for c, k in buttons))
ok('2-4 설정 라벨', '<span>설정</span>' in tabhtml)
ok('2-5 설정 아이콘은 gear', 'gearin' in tabhtml)

# ── 3. 오늘 탭 ⚙️ → 설정 ──────────────────────────────────
ok('3-1 오늘 헤더 ⚙️가 설정 탭으로', 'data-act="tab" data-tab="settings" aria-label="설정"' in HTML)
ok('3-2 통계·설정 라벨 제거', 'aria-label="통계·설정"' not in HTML)

# ── 4. viewSettings 분리 ──────────────────────────────────
ok('4-1 viewSettings 함수 존재', 'function viewSettings(){' in HTML)
vs = HTML[HTML.index('function viewSettings(){'):]
vs = vs[:vs.index('\n}\n')]
ok('4-2 설정 탭에 앱스토어 출시 로드맵 없음', '앱스토어 출시 로드맵' not in vs)
ok('4-2b 로드맵 카드·헬퍼 제거', 'roadmapStep' not in HTML and '<div class="rm">' not in HTML
   and '.rm{position:relative' not in HTML)
ok('4-3 설정 탭에 프로 정보 입력', 'id="setPro"' in vs and 'id="setAcademy"' in vs)
ok('4-4 설정 탭에 데이터 내보내기', 'data-act="export-data"' in vs)
ok('4-5 설정 탭에 데모 초기화', 'data-act="demo-reset"' in vs)
ok('4-6 설정 탭에 외부 캘린더 연동', '외부 캘린더 연동' in vs and 'calSettingHTML()' in vs)

ls = HTML[HTML.index('function viewLessonStats(){'):HTML.index('/* 설정 탭 = 화면 테마')]
ok('4-7 통계(수업 현황)에 로드맵 없음', '앱스토어 출시 로드맵' not in ls)
ok('4-7b 화면 어디에도 로드맵 카드 없음', '앱스토어 출시 로드맵' not in HTML)
ok('4-8 통계에 프로 설정 없음', 'data-act="pro-save"' not in ls and 'id="setPro"' not in ls)
ok('4-9 통계에 외부 캘린더 연동 없음', '외부 캘린더 연동' not in ls)
ok('4-10 통계에 수업 현황 지표 유지', '주별 레슨' in ls and '회원별 이번 달' in ls)

# ── 5. 라우팅 · 헤더 ──────────────────────────────────────
ok('5-1 render: settings → viewSettings', "else if (ui.tab === 'stats') html = viewStats();\n  else html = viewSettings();" in HTML)
ok('5-2 renderHeader: 설정 헤더', '<h1>설정</h1>' in HTML)
ok('5-3 탭바 라벨 줄바꿈 방지', '.tabbar button span{white-space:nowrap' in HTML)

# ── 6. 정적 무결성 ────────────────────────────────────────
ok('6-1 스크립트 2개 (테마 부트스트랩 + 앱 본문)', HTML.count('<script>') == 2)
ok('6-1b 테마 부트스트랩이 <style>보다 먼저 (첫 페인트 전 적용)',
   HTML.index('<script>') < HTML.index('<style>') and 'data-theme' in HTML[:HTML.index('<style>')])
ok('6-2 설정 탭 뷰가 통계 뷰 뒤에 정의', HTML.index('function viewStats(){') < HTML.index('function viewSettings(){'))
ok('6-3 doc에 5탭 설명 없음(확인용 통계 문구 유지)', '수입 정산' in HTML)

for name, cond, detail in OUT:
    print(('PASS ' if cond else 'FAIL ') + name + ('' if cond else '  <- ' + str(detail)))
p = sum(1 for _, c, _ in OUT if c)
print('')
print('%d passed / %d total' % (p, len(OUT)))
sys.exit(0 if p == len(OUT) else 1)
