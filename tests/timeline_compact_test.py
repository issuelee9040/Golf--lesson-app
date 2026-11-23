#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""캘린더 시간표(timelineHTML)의 낮은 블록 렌더링 검사.

25분 레슨처럼 블록 높이가 낮을 때 두 줄이 세로로 잘리지 않도록
한 줄(시간 · 이름 · 분)로 가운데 정렬해 그리는지, 그리고 짧은 블록의
최소 높이가 다음 블록을 덮지 않는지(겹침 없음) 확인한다.

프로토타입에 실제로 들어 있는 상수·헬퍼·timelineHTML 코드를 그대로 실행한다.
"""
import re, sys
import quickjs

HTML = open('/workspace/golf-lesson-app/prototype.html', encoding='utf-8').read()

# ── 프로토타입에서 그대로 가져올 조각들 ──────────────────────────────
base_start = HTML.index("var KEY = 'golfLessonApp.v2';")
base_end = HTML.index('/* ---------- 상태 ---------- */')
BASE = HTML[base_start:base_end]

tl_start = HTML.index('function timelineHTML(dateStr){')
tl_end = HTML.index('/* =========================================================\n   레슨 예약', tl_start)
TIMELINE = HTML[tl_start:tl_end]

HARNESS = r"""
var state = { members: [{ id:'m1', name:'이하늘' }], packages: [], sessions: [], settlements: [] };
function memberById(id){ for (var i=0;i<state.members.length;i++) if (state.members[i].id === id) return state.members[i]; return null; }
function memberName(id){ var m = memberById(id); return m ? m.name : '(삭제된 회원)'; }
function sessionsByDate(d){
  return state.sessions.filter(function(s){ return s.date === d; })
    .sort(function(a,b){ return minOf(a.startTime) - minOf(b.startTime); });
}
function pkgById(id){ for (var i=0;i<state.packages.length;i++) if (state.packages[i].id === id) return state.packages[i]; return null; }
function sessionEnd(s){ return minOf(s.startTime) + s.durationMinutes; }

/* ====TESTS==== */
var OUT = [];
function ok(name, cond, detail){ OUT.push({ name:name, pass:!!cond, detail:detail || '' }); }

function sess(id, t, dur, opt){
  opt = opt || {};
  return { id:id, memberId:'m1', packageId: opt.pkg || 'p1', date:'2026-11-24', startTime:t,
           durationMinutes:dur, location: opt.loc === undefined ? '분당 실내연습장' : opt.loc,
           memo:'', status: opt.status || 'scheduled', lessonKind: opt.kind };
}
function geoBlock(html, id){
  var re = new RegExp('style="([^"]*)"[^>]*data-sid="' + id + '"');
  var m = html.match(re);
  if (!m) return null;
  var h = /height:([0-9.]+)px/.exec(m[1]);
  var t = /top:([0-9.]+)px/.exec(m[1]);
  return { h: h ? parseFloat(h[1]) : null, top: t ? parseFloat(t[1]) : null, raw: m[1] };
}
function blockOf(html, id){
  var i = html.indexOf('data-sid="' + id + '"');
  if (i < 0) return '';
  var s = html.lastIndexOf('<button', i);
  var e = html.indexOf('</button>', i);
  return html.slice(s, e + 9);
}
function reset(list){ state.packages = [{ id:'p1', memberId:'m1', durationMinutes:55, totalSessions:8, remainingSessions:5 }];
                      state.sessions = list; }

/* 1. 25분 단독 */
reset([ sess('a', '06:30', 25, { loc:'' }) ]);
var h = timelineHTML('2026-11-24');
var b = blockOf(h, 'a'), g = geoBlock(h, 'a');
ok('1-1 25분 블록은 한 줄(compact) 렌더링', b.indexOf('ev-compact') >= 0, b.slice(0, 90));
ok('1-2 한 줄 클래스 사용', b.indexOf('ev-line') >= 0);
ok('1-3 두 줄 스팬(ev-t) 없음', b.indexOf('class="ev-t"') < 0);
ok('1-4 시간 표시', b.indexOf('06:30') >= 0);
ok('1-5 이름 표시', b.indexOf('이하늘') >= 0);
ok('1-6 분 표시', b.indexOf('25분') >= 0);
ok('1-7 25분 블록은 최소 높이 34px 로 키움 (누르기 쉽게)', g.h === TL_MIN_H, 'h=' + g.h);
ok('1-8 높이 34px 이상', g.h >= 34, 'h=' + g.h);
ok('1-9 위치는 06:30 (1시간 72px 기준)', g.top === 36, 'top=' + g.top);

/* 2. 55분 단독 — 기존 두 줄 유지 */
reset([ sess('b', '15:00', 55) ]);
h = timelineHTML('2026-11-24'); b = blockOf(h, 'b'); g = geoBlock(h, 'b');
ok('2-1 55분 블록은 compact 아님', b.indexOf('ev-compact') < 0);
ok('2-2 55분은 두 줄(시간 · 이름)', b.indexOf('class="ev-t"') >= 0 && b.indexOf('class="ev-n"') >= 0);
ok('2-3 55분 높이 63px (1시간 72px 기준)', g.h === 63, 'h=' + g.h);
ok('2-4 55분 블록이 25분보다 충분히 큼', true);

/* 3. 백투백 25분 (06:00 · 06:30) — 겹치지 않아야 함 */
reset([ sess('c1', '06:00', 25), sess('c2', '06:30', 25) ]);
h = timelineHTML('2026-11-24');
var g1 = geoBlock(h, 'c1'), g2 = geoBlock(h, 'c2');
ok('3-1 두 블록 모두 compact', blockOf(h, 'c1').indexOf('ev-compact') >= 0 && blockOf(h, 'c2').indexOf('ev-compact') >= 0);
ok('3-2 위 블록이 아래 블록을 덮지 않음', g1.top + g1.h <= g2.top, 'end=' + (g1.top + g1.h) + ' next=' + g2.top);
ok('3-3 사이 간격 확보(1px 이상)', g2.top - (g1.top + g1.h) >= 1, 'gap=' + (g2.top - (g1.top + g1.h)));

/* 4. 25분 + 55분 + 필드 180분 */
reset([ sess('d1', '09:00', 25, { loc:'' }), sess('d2', '09:30', 55), 
        sess('d3', '14:00', 180, { kind:'field', pkg:'' }) ]);
h = timelineHTML('2026-11-24');
var d1 = geoBlock(h, 'd1'), d2 = geoBlock(h, 'd2'), d3 = geoBlock(h, 'd3');
ok('4-1 25분 compact', blockOf(h, 'd1').indexOf('ev-compact') >= 0);
ok('4-2 55분 두 줄', blockOf(h, 'd2').indexOf('class="ev-t"') >= 0);
ok('4-3 180분 필드는 세 줄(장소/금액)', blockOf(h, 'd3').indexOf('class="ev-m"') >= 0);
ok('4-4 높이 비율 25 < 55 < 180', d1.h < d2.h && d2.h < d3.h, d1.h + '/' + d2.h + '/' + d3.h);
ok('4-5 25분·55분 백투백 겹침 없음', d1.top + d1.h <= d2.top, 'end=' + (d1.top + d1.h) + ' next=' + d2.top);

/* 5. 40분(경계) — 한 줄, 45분 — 두 줄 */
reset([ sess('e1', '10:00', 40), sess('e2', '12:00', 45) ]);
h = timelineHTML('2026-11-24');
ok('5-1 40분은 48px 라 두 줄로 보여 줄 수 있음', blockOf(h, 'e1').indexOf('ev-compact') < 0);
ok('5-2 45분은 두 줄', blockOf(h, 'e2').indexOf('ev-compact') < 0);
ok('5-3 45분 높이 51px', geoBlock(h, 'e2').h === 51, 'h=' + geoBlock(h, 'e2').h);

/* 6. 상태별 색 클래스 유지 */
reset([ sess('f1', '08:00', 25, { status:'no_show' }) ]);
h = timelineHTML('2026-11-24');
ok('6-1 노쇼 색 클래스 유지', blockOf(h, 'f1').indexOf('ev-no_show') >= 0);
ok('6-2 상태 변경 액션 유지', blockOf(h, 'f1').indexOf('data-act="status-sheet"') >= 0);

/* 7. 빈 날 */
reset([]);
ok('7-1 예약 없음 안내', timelineHTML('2026-11-24').indexOf('예약이 없어요') >= 0);

JSON.stringify(OUT);
"""

ctx = quickjs.Context()
src = '(function(){"use strict";\n' + BASE + '\n' + TIMELINE + '\n' + HARNESS.replace('JSON.stringify(OUT);', 'return JSON.stringify(OUT);') + '\n})()'
try:
    raw = ctx.eval(src)
except Exception as e:
    print('실행 오류:', e)
    sys.exit(1)

import json
results = json.loads(raw)
passed = sum(1 for r in results if r['pass'])
for r in results:
    print(('PASS ' if r['pass'] else 'FAIL ') + r['name'] + ('' if r['pass'] else '  <- ' + r['detail']))
print('')
print('%d passed / %d total' % (passed, len(results)))
sys.exit(0 if passed == len(results) else 1)
