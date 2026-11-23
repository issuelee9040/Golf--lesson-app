#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""레슨 시간 범위(기본 06:00~23:00 · 설정 탭에서 변경) 검사.

- 기본값은 06:00~23:00 이고, 시작 시간 칩은 06:00부터 23:00까지 30분 단위(35칸)로 만들어지는지
- 설정 탭 '레슨 시간 범위' 카드에서 가장 이른/늦은 시작 시간을 앱 안 피커로 고르고 저장하는지
- 범위가 저장본에 없던 예전 데이터는 06:00~23:00 으로 채워지고, 데모 초기화해도 고른 범위는 남는지
- 시작 시간 시트 부제에 '현재 06:00~23:00 · 설정 탭에서 바꿀 수 있어요' 안내가 범위를 따라 바뀌는지
- 시간표(타임라인)가 설정 범위와 범위를 넘는 늦은 레슨(21:30~23:00 등)을 잘라내지 않고 끝까지 그리는지
"""
import json, re, sys
import quickjs

HTML = open('/workspace/golf-lesson-app/prototype.html', encoding='utf-8').read()

# ── 프로토타입에서 그대로 가져올 조각들 ──────────────────────────────
base_start = HTML.index("var KEY = 'golfLessonApp.v2';")
base_end = HTML.index('/* ---------- 상태 ---------- */')
BASE = HTML[base_start:base_end]

ap_start = HTML.index('function applyPick(fieldId, value){')
ap_end = HTML.index('\n}\n', ap_start) + 3
APPLY_PICK = HTML[ap_start:ap_end]

dt_start = HTML.index('function defaultTime(){')
dt_end = HTML.index('function openBookSheet(pre){', dt_start)
DEFAULT_TIME = HTML[dt_start:dt_end]

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

function slots(){ return daySlots(); }
function dayRangeFrom(f){ var keep = state.hours; state.hours = { fromMin:f, toMin:1380 }; var v = dayFromMin(); state.hours = keep; return v; }
function tlHeight(h){ var m = /style="height:([0-9.]+)px"/.exec(h); return m ? parseFloat(m[1]) : null; }
function geoBlock(html, id){
  var re = new RegExp('style="([^"]*)"[^>]*data-sid="' + id + '"');
  var m = html.match(re);
  if (!m) return null;
  var hh = /height:([0-9.]+)px/.exec(m[1]);
  var t = /top:([0-9.]+)px/.exec(m[1]);
  return { h: hh ? parseFloat(hh[1]) : null, top: t ? parseFloat(t[1]) : null };
}
function sess(id, t, dur, opt){
  opt = opt || {};
  return { id:id, memberId:'m1', packageId: opt.pkg === undefined ? 'p1' : opt.pkg, date:'2026-11-24', startTime:t,
           durationMinutes:dur, location:'분당 실내연습장', memo:'', status:'scheduled', lessonKind: opt.kind };
}
function day(list){
  state.packages = [{ id:'p1', memberId:'m1', durationMinutes:55, totalSessions:8, remainingSessions:5 }];
  state.sessions = list;
  return timelineHTML('2026-11-24');
}

/* 1. 기본 범위 */
state.hours = undefined;
var r = dayRange();
ok('1-1 저장본에 범위가 없으면 06:00~23:00', r.from === 360 && r.to === 1380, r.from + '~' + r.to);
ok('1-2 범위 표기 06:00~23:00', dayRangeLabel() === '06:00~23:00', dayRangeLabel());

var s = slots();
ok('1-3 시작 칩 35칸 (06:00~23:00, 30분 간격)', s.length === 35, 'n=' + s.length);
ok('1-4 첫 칸 06:00', s[0] === '06:00', s[0]);
ok('1-5 마지막 칸 23:00', s[s.length - 1] === '23:00', s[s.length - 1]);
var stepOk = true;
for (var i = 1; i < s.length; i++) if (minOf(s[i]) - minOf(s[i - 1]) !== 30) stepOk = false;
ok('1-6 모두 30분 간격', stepOk);
ok('1-7 옛 21:00 상한이 사라짐 (21:30·22:00·22:30 있음)',
   s.indexOf('21:30') >= 0 && s.indexOf('22:00') >= 0 && s.indexOf('22:30') >= 0);

/* 2. 설정에서 바꾼 범위 */
state.hours = { fromMin: 600, toMin: 1440 };   /* 10:00 ~ 24:00 */
s = slots();
ok('2-1 10:00~24:00 표기', dayRangeLabel() === '10:00~24:00', dayRangeLabel());
ok('2-2 첫 칸 10:00', s[0] === '10:00', s[0]);
ok('2-3 24:00 은 시작 시간이 되지 않음 (마지막 23:30)', s[s.length - 1] === '23:30', s[s.length - 1]);
ok('2-4 10:00~23:30 = 28칸', s.length === 28, 'n=' + s.length);

state.hours = { fromMin: 300, toMin: 1080 };   /* 05:00 ~ 18:00 */
ok('2-5 05:00~18:00 표기', dayRangeLabel() === '05:00~18:00', dayRangeLabel());
ok('2-6 첫 칸 05:00', slots()[0] === '05:00', slots()[0]);

/* 3. 범위 보정 */
state.hours = { fromMin: 0, toMin: 2000 };
r = dayRange();
ok('3-1 비어 있는 값(0)은 기본 06:00 으로', r.from === 360, r.from);
ok('3-1b 05:00 보다 이른 값은 05:00 으로', dayRangeFrom(240) === 300, dayRangeFrom(240));
ok('3-2 너무 늦은 값은 24:00 으로', r.to === 1440, r.to);
state.hours = { fromMin: 13 * 60, toMin: 17 * 60 };
r = dayRange();
ok('3-3 시작은 12:00 을 넘지 않음', r.from === 720, r.from);
ok('3-4 마감은 18:00 아래로 내려가지 않음', r.to === 1080, r.to);
state.hours = { fromMin: 720, toMin: 700 };
r = dayRange();
ok('3-5 마감이 시작보다 앞서면 최소 1시간 뒤로', r.to >= r.from + 60, r.from + '~' + r.to);
state.hours = { fromMin: 'abc', toMin: null };
r = dayRange();
ok('3-6 잘못된 저장값은 기본값으로', r.from === 360 && r.to === 1380, r.from + '~' + r.to);
ok('3-7 24:00 표기 helper', hourLabel(1440) === '24:00' && hourLabel(1380) === '23:00');

/* 4. 기본 시작 시간은 범위 안에서 (지금 시각이 범위 밖이면 범위 끝으로 붙음) */
state.hours = undefined;                          /* 06:00~23:00 */
ok('4-1 범위보다 이른 시각은 가장 이른 시작으로', dayClampTime(0) === '06:00', dayClampTime(0));
ok('4-2 범위보다 늦은 시각은 가장 늦은 시작으로', dayClampTime(23 * 60 + 30) === '23:00', dayClampTime(23 * 60 + 30));
state.hours = { fromMin: 600, toMin: 1440 };      /* 10:00~24:00 */
ok('4-3 늦은 범위에서도 24:00 은 시작이 되지 않음', dayClampTime(1440) === '23:30', dayClampTime(1440));
ok('4-4 범위 안 시각은 그대로', dayClampTime(12 * 60) === '12:00', dayClampTime(12 * 60));
var dIn = minOf(defaultTime());
ok('4-5 지금 시각 기준 기본 시간도 범위 안', dIn >= 600 && dIn <= 1440, defaultTime());

/* 5. 시간표 — 범위를 넘는 늦은 레슨도 끝까지 */
state.hours = undefined;   /* 설정은 기본 06:00~23:00 */
var h = day([ sess('a', '21:30', 120), sess('b', '19:00', 55) ]);
var H = tlHeight(h), ga = geoBlock(h, 'a'), gb = geoBlock(h, 'b');
ok('5-1 늦은 레슨 날 시간표가 그려짐', H !== null, h.slice(0, 60));
ok('5-2 21:30 블록이 시간표 안에 (top+height <= 높이)', ga && ga.top + ga.h <= H, ga ? (ga.top + ga.h) + '/' + H : 'no block');
ok('5-3 18:00 시작 기준 21:30 위치 = 252px (1시간 72px)', ga && ga.top === 252, ga ? ga.top : 'no block');
ok('5-4 21:30 블록 실제 길이 141px', ga && ga.h === 141, ga ? ga.h : 'no block');
ok('5-5 19:00 블록도 정상', gb && gb.top + gb.h <= H, gb ? (gb.top + gb.h) + '/' + H : 'no block');
ok('5-6 마지막 시간선 24:00 까지 그려짐', h.indexOf('>24:00<') >= 0);

/* 6. 22:10 + 90분 (23:40 종료) 도 잘리지 않음 */
h = day([ sess('c', '22:10', 90) ]);
H = tlHeight(h);
var gc = geoBlock(h, 'c');
ok('6-1 23:40 종료 레슨이 시간표 안에', gc && gc.top + gc.h <= H, gc ? (gc.top + gc.h) + '/' + H : 'no block');
ok('6-2 24:00 시간선 표시', h.indexOf('>24:00<') >= 0);

/* 7. 설정보다 이른 레슨도 자르지 않음 (설정 06:00 인데 05:30 레슨) */
h = day([ sess('d', '05:30', 55) ]);
H = tlHeight(h);
var gd = geoBlock(h, 'd');
ok('7-1 05:30 레슨이 0 위로 튀지 않음', gd && gd.top >= 0, gd ? gd.top : 'no block');
ok('7-2 05:30 레슨이 시간표 안에', gd && gd.top + gd.h <= H, gd ? (gd.top + gd.h) + '/' + H : 'no block');
ok('7-3 05:00 시간선부터 그려짐', h.indexOf('>05:00<') >= 0);

/* 8. 보통 날은 예전처럼 필요한 만큼만 (전체 하루를 늘어놓지 않음) */
h = day([ sess('e', '09:00', 55) ]);
H = tlHeight(h);
ok('8-1 09:00 하루 = 4시간 높이(288px)', H === 288, 'H=' + H);
ok('8-2 앞뒤 여백 한 시간씩 (08:00 ~ 12:00)', h.indexOf('>08:00<') >= 0 && h.indexOf('>12:00<') >= 0);

/* 9. 예약 없는 날 안내는 그대로 */
state.hours = undefined;
state.sessions = [];
ok('9-1 예약 없음 안내', timelineHTML('2026-11-24').indexOf('예약이 없어요') >= 0);
"""

ctx = quickjs.Context()
src = ('(function(){"use strict";\n' + BASE + '\n' + DEFAULT_TIME + '\n' + TIMELINE + '\n'
       + HARNESS + '\nreturn JSON.stringify(OUT);\n})()')
try:
    raw = ctx.eval(src)
except Exception as e:
    print('실행 오류:', e)
    sys.exit(1)

results = json.loads(raw)

# ── 정적 배선 검사 ───────────────────────────────────────────────
def ok(name, cond, detail=''):
    results.append({'name': name, 'pass': bool(cond), 'detail': detail})

ok('10-1 기본 상수 06:00~23:00', 'var DEF_FROM = 6 * 60, DEF_TO = 23 * 60;' in HTML)
ok('10-2 설정에서 고를 수 있는 시작 범위 05:00~12:00',
   'var FROM_MIN = 5 * 60, FROM_MAX = 12 * 60;' in HTML)
ok('10-3 설정에서 고를 수 있는 마감 범위 18:00~24:00',
   'var TO_MIN = 18 * 60, TO_MAX = 24 * 60;' in HTML)
ok('10-4 옛 DAY_START/DAY_END 사용처 정리', 'DAY_START' not in HTML and 'DAY_END' not in HTML)

ok('11-1 시작 시간 시트 부제가 범위를 읽음',
   "sub:'30분 단위로 고를 수 있어요.<span class=\"subnote\">현재 ' + dayRangeLabel()" in HTML)
ok('11-2 부제에 설정 탭 안내', '시간 범위는 <b>설정</b> 탭에서 바꿀 수 있어요' in HTML)
ok('11-3 시간 칩은 daySlots() 사용', 'var list = daySlots();' in HTML)
ok('11-4 기본 시간이 설정 범위로 제한', 'if (m < r.from) m = r.from;' in HTML and 'if (m > r.to) m = r.to;' in HTML)

ok('12-1 설정 탭에 레슨 시간 범위 카드', '<h2>레슨 시간 범위</h2>' in HTML)
ok('12-2 두 칸이 앱 안 피커', "pickFieldHTML('hourFrom'" in HTML and "pickFieldHTML('hourTo'" in HTML)
ok('12-3 라벨 가장 이른/늦은 시작', '가장 이른 시작' in HTML and '가장 늦은 시작' in HTML)
ok('12-4 피커 제목 안내', "hourFrom: { title:'가장 이른 시작 시간'" in HTML
   and "hourTo:   { title:'가장 늦은 시작 시간'" in HTML)
ok('12-5 고르면 state.hours 저장 + save()',
   "if (fieldId === 'hourFrom' || fieldId === 'hourTo')" in HTML
   and 'state.hours = { fromMin: r.from, toMin: r.to };' in HTML)
ok('12-6 저장 뒤 화면의 두 칸만 갱신', 'function syncHourRows()' in HTML and 'syncHourRows();' in HTML)
ok('12-7 토스트로 바뀐 범위 안내', "toast('레슨 시간 범위 · ' + dayRangeLabel());" in HTML)

ok('13-1 예전 저장본은 기본 범위로 채움',
   'if (!state.hours) state.hours = { fromMin: DEF_FROM, toMin: DEF_TO };' in HTML)
ok('13-2 저장값은 항상 보정해서 보관', 'state.hours = { fromMin: drange.from, toMin: drange.to };' in HTML)
ok('13-3 데모 초기화해도 고른 범위 유지', 'var keepHours = dayRange();' in HTML
   and 'state.hours = { fromMin: keepHours.from, toMin: keepHours.to };' in HTML)
ok('13-4 데모 데이터 기본 범위', 'hours: { fromMin: DEF_FROM, toMin: DEF_TO }' in HTML)

ok('14-1 시간표가 설정 범위를 읽음',
   'var rFrom = Math.floor(dayFromMin() / 60), rTo = Math.ceil(dayToMin() / 60);' in HTML)
ok('14-2 범위를 넘는 레슨은 자르지 않음', 'var firstH = startH, lastH = endH;' in HTML)

ok('15-1 부제 안내 스타일', '.sheet .sub .subnote{display:block' in HTML)

# ── 스스로: 설정 피커에서 고른 값이 저장되는지 (applyPick 실행) ──────────
AP_STUB = r"""
var log = [], vals = {};
var document = { getElementById:function(id){ if (!vals[id]) vals[id] = { value:'' }; return vals[id]; } };
function syncPickLabel(id){ log.push('label:' + id); }
function save(){ log.push('save'); }
function render(){ log.push('render'); }
function toast(t){ log.push('toast:' + t); }
function memberSortLabel(v){ return v; }
var bookCtx = null, qaCtx = null;
function refreshBkPkgs(){} function validateBook(){} function validateQuick(){}
function syncHourRows(){ log.push('hours'); }
var state = { hours: { fromMin: 360, toMin: 1380 } };
applyPick('hourFrom', '660');
var A = { from: state.hours.fromMin, to: state.hours.toMin, log: log.join('|') };
applyPick('hourFrom', '1200');          /* 시작으로 고를 수 없는 값 (12:00 초과) */
var B = { from: state.hours.fromMin, to: state.hours.toMin };
applyPick('hourTo', '1440');            /* 24:00 마감 */
var C = { from: state.hours.fromMin, to: state.hours.toMin, log: log.join('|') };
applyPick('hourTo', '600');             /* 마감으로 고를 수 없는 값 */
var D = { from: state.hours.fromMin, to: state.hours.toMin };
globalThis.AP = [A, B, C, D];
"""
ctx3 = quickjs.Context()
ctx3.eval('(function(){"use strict";\n' + BASE + '\n' + DEFAULT_TIME + '\n' + APPLY_PICK + '\n' + AP_STUB + '\n})()')
A, B, C, D = json.loads(ctx3.eval('JSON.stringify(AP)'))
ok('16-1 11:00 을 가장 이른 시작으로 저장', A['from'] == 660 and A['to'] == 1380, str(A))
ok('16-2 저장 후 save · 칸 갱신 · 토스트', 'save' in A['log'] and 'hours' in A['log']
   and 'toast:레슨 시간 범위 · 11:00~23:00' in A['log'], A['log'])
ok('16-3 고를 수 없는 시작값은 무시', B['from'] == 660, str(B))
ok('16-4 마감 24:00 저장', C['to'] == 1440 and C['from'] == 660, str(C))
ok('16-5 토스트가 바뀐 범위를 알려줌', 'toast:레슨 시간 범위 · 11:00~24:00' in C['log'], C['log'])
ok('16-6 고를 수 없는 마감값은 무시', D['to'] == 1440, str(D))

passed = sum(1 for r in results if r['pass'])
for r in results:
    print(('PASS ' if r['pass'] else 'FAIL ') + r['name'] + ('' if r['pass'] else '  <- ' + str(r['detail'])))
print('')
print('%d passed / %d total' % (passed, len(results)))
sys.exit(0 if passed == len(results) else 1)
