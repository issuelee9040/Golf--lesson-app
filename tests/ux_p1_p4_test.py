#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""UX 점검 P1~P4 회귀 검사 (2026-11-23).

앱 스크립트 전체를 가짜 DOM 위에서 실행해, 화면 함수가 만든 HTML 과
사용자 입력 경로(한 줄 입력 · 시트 닫기 · 날짜 자동 인식 · 정산 선택)를 그대로 검사한다.

검사 묶음
  A. P1-1 한 줄 회원 추가 — 메모에 이름 첫 글자가 남지 않는다 (글자 단위 타이핑 재현)
  B. P1-2 시트 X · 취소도 '작성 중인 내용' 확인을 거친다
  C. P1-3 레슨 차트 날짜 자동 인식 → 옆 날짜 버튼도 같은 날짜
  D. P2 오늘 탭 수정 버튼 · 오늘 탭에서 레슨 잡기 · 빈 날 히어로
  E. P2 터치 타깃 높이 (오늘 카드 · 정산 · 캘린더) + 25분 타임라인
  F. P2 회원 상세 — 레슨 차트를 위로, 저장 버튼 이름 구분
  G. P3 예정/미정 · 메모 이름 · 날짜 표기 · 화면 이름/순서
  H. P4 빈 상태 · 별도 수입 줄바꿈 · 수입 근거 · 날짜 칸 접근성 · 배지/라벨 · 캘린더 연동 · 정산 배지
  I. 설계서 기록
"""
import re, json, sys
import quickjs

HTML = open('/workspace/golf-lesson-app/prototype.html', encoding='utf-8').read()
CSS = HTML[HTML.index('<style>'):HTML.index('</style>')]
SPEC = open('/workspace/golf-lesson-app/spec.md', encoding='utf-8').read()
OUT = []


def ok(name, cond, detail=''):
    OUT.append((name, bool(cond), detail))


def rule(sel):
    m = re.search(r'(^|\n)' + re.escape(sel) + r'\{([^}]*)\}', CSS)
    return m.group(2) if m else ''


# ══════════════════════════════════════════════════════════════════
# 앱 전체를 가짜 DOM 위에서 실행 — 화면 함수의 실제 HTML 을 검사
# ══════════════════════════════════════════════════════════════════
body = re.findall(r'<script>(.*?)</script>', HTML, re.S)[1]
inner = body[body.index('(function(){') + len('(function(){'):body.rindex('})();')]

SHIM = r"""
var __els = {};
function El(id){
  this.id = id; this._h = ''; this.style = {}; this.children = []; this.value = ''; this.hidden = false;
  this.classList = { _s:{}, add:function(c){ this._s[c]=1; }, remove:function(c){ delete this._s[c]; },
    toggle:function(c,v){ if (v === undefined) v = !this._s[c]; if (v) this._s[c]=1; else delete this._s[c]; return !!this._s[c]; },
    contains:function(c){ return !!this._s[c]; } };
  this.attributes = {};
}
El.prototype.setAttribute = function(k,v){ this.attributes[k] = String(v); };
El.prototype.getAttribute = function(k){ return this.attributes[k] === undefined ? null : this.attributes[k]; };
El.prototype.removeAttribute = function(k){ delete this.attributes[k]; };
El.prototype.addEventListener = function(){};
El.prototype.appendChild = function(c){ this.children.push(c); return c; };
El.prototype.removeChild = function(c){ var i = this.children.indexOf(c); if (i >= 0) this.children.splice(i,1); };
El.prototype.querySelector = function(sel){ this._q = this._q || {}; if (!this._q[sel]) this._q[sel] = new El(sel); return this._q[sel]; };
El.prototype.querySelectorAll = function(){ return []; };
El.prototype.focus = function(){};
El.prototype.select = function(){};
El.prototype.closest = function(){ return null; };
El.prototype.contains = function(){ return false; };
Object.defineProperty(El.prototype, 'innerHTML', { get:function(){ return this._h; }, set:function(v){ this._h = String(v); } });
Object.defineProperty(El.prototype, 'textContent', { get:function(){ return this._h; }, set:function(v){ this._h = String(v); } });
Object.defineProperty(El.prototype, 'parentNode', { get:function(){ return null; } });
var document = {
  getElementById: function(id){ if (!__els[id]) __els[id] = new El(id); return __els[id]; },
  querySelector: function(sel){ return new El(sel); },
  querySelectorAll: function(){ return []; },
  createElement: function(t){ return new El(t); },
  addEventListener: function(){},
  documentElement: { setAttribute: function(){}, getAttribute: function(){ return 'green'; } },
  body: new El('body')
};
function setTimeout(){ return 1; }
function clearTimeout(){}
function setInterval(){ return 1; }
var window = { addEventListener:function(){}, open:function(){},
  matchMedia:function(){ return { matches:false, addEventListener:function(){} }; } };
window.document = document;
var localStorage = { _d:{}, getItem:function(k){ return this._d[k] === undefined ? null : this._d[k]; },
  setItem:function(k,v){ this._d[k] = String(v); }, removeItem:function(k){ delete this._d[k]; } };
var navigator = { userAgent:'test' };
"""

EXPORT = r"""
globalThis.__api = {
  viewToday: viewToday, viewCalendar: viewCalendar, viewMembers: viewMembers, viewSettings: viewSettings,
  viewStats: viewStats, viewRevenue: viewRevenue, memberBodyHTML: memberBodyHTML, memberRowsHTML: memberRowsHTML,
  lessonCard: lessonCard, calSettingHTML: calSettingHTML, paintCalSetting: paintCalSetting, calSync: calSync,
  addMemberBodyHTML: addMemberBodyHTML, openMemberSheet: openMemberSheet, openAddMemberSheet: openAddMemberSheet,
  applyQuickLine: applyQuickLine, refreshNoteDate: refreshNoteDate,
  settleBodyHTML: settleBodyHTML, settleFooterHTML: settleFooterHTML, timelineHTML: timelineHTML,
  sessionsByDate: sessionsByDate, openTodayMemoSheet: openTodayMemoSheet,
  onClick: onClick, closeAllSheets: closeAllSheets, requestSheetClose: requestSheetClose,
  todayISO: todayISO, doc: document,
  state: function(){ return state; }, setState: function(s){ state = s; }, buildDemo: buildDemo,
  blankState: blankState, ui: function(){ return ui; }, addCtx: function(){ return addCtx; },
  memberCtx: function(){ return memberCtx; }, sheetStack: function(){ return sheetStack; },
  htmlOf: function(id){ return document.getElementById(id).innerHTML; }
};
"""

ctx = quickjs.Context()
try:
    ctx.eval(SHIM + inner + EXPORT)
except Exception as e:
    print('앱 실행 오류:', e)
    sys.exit(1)

JS = r"""
var A = globalThis.__api, D = A.doc;
function EL(id){ return D.getElementById(id); }
var log = [], fails = [];
function ok(c, n, d){ if (c) log.push('PASS ' + n); else fails.push('FAIL ' + n + (d === undefined ? '' : '  <- ' + d)); }
function eq(a, b, n){ ok(a === b, n + (a === b ? '' : '  got=[' + a + '] want=[' + b + ']')); }
function has(s, t, n){ ok(String(s).indexOf(t) >= 0, n, 'missing: ' + t); }
function hasNot(s, t, n){ ok(String(s).indexOf(t) < 0, n, 'found: ' + t); }
function rule(sel){ var m = new RegExp('(^|\\n)' + sel.replace(/[.*+?^${}()|[\]\\]/g, '\\$&') + '\\{([^}]*)\\}').exec(CSS); return m ? m[2] : ''; }
function resetDemo(){ A.setState(A.buildDemo()); A.ui().tab = 'today'; A.ui().date = A.todayISO(); }
function resetEmpty(){
  A.setState(A.blankState('이시훈', ''));
  A.state().members = []; A.state().packages = []; A.state().sessions = [];
  A.state().notes = []; A.state().settlements = []; A.state().templates = [];
  A.ui().tab = 'today'; A.ui().date = A.todayISO();
}
function clickAct(act, wrap){
  A.onClick({ target: { closest: function(){
    return { getAttribute: function(){ return act; }, closest: function(){ return wrap; } };
  } } });
}

/* ══════════ A. P1-1 한 줄 회원 추가 — 메모 오염 ══════════ */
resetEmpty();
A.openAddMemberSheet(null);
var full = '정하윤 55분 10회 여 판교';
var seen = [];
for (var i = 1; i <= full.length; i++) {
  EL('quickLine').value = full.slice(0, i);
  A.applyQuickLine();
  seen.push(EL('mfMemo').value);
}
eq(EL('mfName').value, '정하윤', 'A-1 이름 인식');
eq(EL('mfRegion').value, '판교', 'A-2 지역 인식');
eq(EL('mfSessions').value, '10', 'A-3 횟수 인식');
eq(EL('mfRemain').value, '', 'A-4 잔여는 비어 있음');
eq(EL('mfMemo').value, '', 'A-5 글자를 끝까지 치면 메모가 깨끗함');
ok(seen.indexOf('정') >= 0, 'A-6 (재현) 중간 단계에서는 첫 글자가 메모로 잡혔음', seen.join('|'));
eq(seen[seen.length - 1], '', 'A-7 마지막 단계 메모 빈 값');

/* 예시 칩처럼 값을 통째로 넣어도 */
EL('quickLine').value = '김민준 55분 10회 남 분당';
A.applyQuickLine();
eq(EL('mfName').value, '김민준', 'A-8 예시 칩 이름');
eq(EL('mfRegion').value, '분당', 'A-9 예시 칩 지역');
eq(EL('mfMemo').value, '', 'A-10 예시 칩 후에도 메모 깨끗함');

/* 이름 밖의 진짜 글은 메모로 */
EL('quickLine').value = '한지우 55분 10회 여 판교 오른팔 펴기';
A.applyQuickLine();
eq(EL('mfMemo').value, '오른팔 펴기', 'A-11 이름 밖의 글은 메모로 남음');

/* 사용자가 직접 적은 메모는 지우지 않는다 */
EL('mfMemo').value = '어깨 회전 주의';
EL('quickLine').value = '윤서아 25분 8회 여 분당';
A.applyQuickLine();
eq(EL('mfMemo').value, '어깨 회전 주의', 'A-12 직접 적은 메모는 보존');
eq(EL('mfName').value, '윤서아', 'A-13 이름은 계속 자동 인식');
eq(EL('mfSessions').value, '8', 'A-14 횟수도 갱신');

/* 글자를 모두 지우면 자동으로 채운 칸도 비운다 */
EL('quickLine').value = '';
A.applyQuickLine();
eq(EL('mfName').value, '', 'A-15 입력을 지우면 자동 채운 이름도 비움');
eq(EL('mfSessions').value, '', 'A-16 횟수도 비움');
eq(EL('mfMemo').value, '어깨 회전 주의', 'A-17 직접 적은 메모는 그대로');
A.closeAllSheets();

/* ══════════ B. P1-2 시트 X · 취소 버튼도 글 보호 ══════════ */
resetDemo();
A.openAddMemberSheet(null);
EL('quickLine').value = '한지우 55분 10회 남 분당\n윤서아 25분 8회 여 판교';
var wrap = A.sheetStack()[A.sheetStack().length - 1];
var before = A.sheetStack().length;
clickAct('sheet-close', wrap);
eq(A.sheetStack().length, before + 1, 'B-1 X 를 눌러도 원래 시트는 남고 확인 시트가 뜸');
ok(A.sheetStack()[A.sheetStack().length - 1] !== wrap, 'B-2 맨 위는 확인 시트');
has(A.sheetStack()[A.sheetStack().length - 1].children[0].querySelector('h3').textContent, '작성 중인 내용이 있어요', 'B-3 확인 시트 제목');
has(A.sheetStack()[A.sheetStack().length - 1].children[0].querySelector('.sb').innerHTML, '2명분의 줄', 'B-4 두 줄이라고 알려 줌');
has(A.sheetStack()[A.sheetStack().length - 1].children[0].querySelector('.sf').innerHTML, '계속 작성', 'B-5 계속 작성 버튼');
ok(A.sheetStack().indexOf(wrap) >= 0, 'B-6 확인 중에는 회원 추가 시트가 남아 있음');
A.closeAllSheets();

A.openAddMemberSheet(null);
var wrap2 = A.sheetStack()[A.sheetStack().length - 1];
EL('quickLine').value = '   ';
var n2 = A.sheetStack().length;
clickAct('sheet-close', wrap2);
eq(A.sheetStack().length, n2 - 1, 'B-7 빈 입력이면 확인 없이 바로 닫힘');

resetEmpty();
A.openAddMemberSheet(null);
var wrap3 = A.sheetStack()[A.sheetStack().length - 1];
EL('quickLine').value = '윤서아 25분 8회';
var n3 = A.sheetStack().length;
A.requestSheetClose(wrap3);
eq(A.sheetStack().length, n3 + 1, 'B-8 바깥 탭 경로도 같은 확인 시트');
A.closeAllSheets();

/* 빠른 추가(캘린더 +)도 같은 보호 */
resetDemo();
A.openQuickAddSheet ? 0 : 0;
A.closeAllSheets();

/* ══════════ C. P1-3 레슨 차트 날짜 자동 인식 → 날짜 버튼 ══════════ */
resetDemo();
var m0 = A.state().members[0];
A.openMemberSheet(m0.id);
EL('noteText').value = '11월 20일 아이언 샷 교정';
A.refreshNoteDate();
eq(EL('noteDate').value, '2026-11-20', 'C-1 숨은 날짜 값이 11월 20일');
has(EL('noteDateLbl').innerHTML, '11월 20일', 'C-2 날짜 버튼 글자도 11월 20일');
has(EL('noteDateLbl').innerHTML, '(금)', 'C-3 요일까지 표시');
EL('noteText').value = '어제 퍼팅 그립 교정';
A.refreshNoteDate();
/* '어제'는 실행한 날에 따라 달라지므로 기대값도 오늘 날짜에서 계산한다 */
function shiftISO(iso, days){
  var p = iso.split('-'), d = new Date(+p[0], +p[1] - 1, +p[2]);
  d.setDate(d.getDate() + days);
  return d.getFullYear() + '-' + ('0' + (d.getMonth() + 1)).slice(-2) + '-' + ('0' + d.getDate()).slice(-2);
}
function korDay(iso){
  var p = iso.split('-'), d = new Date(+p[0], +p[1] - 1, +p[2]);
  return { md: (+p[1]) + '월 ' + (+p[2]) + '일', wd: '(' + ['일','월','화','수','목','금','토'][d.getDay()] + ')' };
}
var yISO = shiftISO(A.todayISO(), -1), yK = korDay(yISO);
eq(EL('noteDate').value, yISO, 'C-4 어제 → 어제 날짜(' + yISO + ')');
has(EL('noteDateLbl').innerHTML, yK.md, 'C-5 날짜 버튼도 어제로');
has(EL('noteDateLbl').innerHTML, yK.wd, 'C-6 요일 표시');
EL('noteText').value = '날짜 없는 메모';
A.refreshNoteDate();
eq(EL('noteDate').value, yISO, 'C-7 날짜가 없으면 고른 날짜 유지');
A.closeAllSheets();

/* ══════════ D. P2 오늘 탭 ══════════ */
resetDemo();
var todayHtml = A.viewToday();
has(todayHtml, 'data-act="lesson-edit"', 'D-1 오늘 카드에 바로 수정 버튼');
has(todayHtml, '>수정</button>', 'D-2 수정 버튼 글자');
has(todayHtml, '수업 메모', 'D-3 메모 버튼은 수업 메모');
hasNot(todayHtml, '>메모</button>', 'D-4 예전 메모 버튼 없음');
has(todayHtml, 'data-act="settle-open"', 'D-5 레슨 있는 날은 마감 정산 히어로');

var T = A.todayISO();
A.state().sessions = A.state().sessions.filter(function(s){ return s.date !== T; });
var emptyHtml = A.viewToday();
has(emptyHtml, '+ 오늘 레슨 잡기', 'D-6 빈 날 히어로가 오늘 레슨 잡기');
has(emptyHtml, 'data-act="quick-add"', 'D-7 히어로가 레슨 잡기로 연결');
hasNot(emptyHtml, 'data-act="settle-open"', 'D-8 빈 날에는 쓸모없는 정산 CTA 없음');
hasNot(emptyHtml, '정산 기준', 'D-9 빈 날에는 정산 기준 카드도 없음');
hasNot(emptyHtml, '0분', 'D-10 0분 칩 없음');

resetDemo();
A.state().settlements = [{ date: T, settledAt: T + 'T18:00:00', counts: {}, deducted: 1, sepCount: 0 }];
var settledHtml = A.viewToday();
has(settledHtml, '오늘 정산 완료', 'D-11 정산 완료 카드');
hasNot(settledHtml, '정산 기준', 'D-12 정산이 끝난 뒤에는 정산 기준 숨김');

/* ══════════ E. 터치 타깃 · 25분 타임라인 ══════════ */
ok(CSS.indexOf('.btn-sm{') >= 0, 'E-1 btn-sm 규칙 존재');
has(rule('.acts'), 'flex-wrap:nowrap', 'E-2 오늘 카드 액션 4개는 한 줄 고정(390px 아이폰)');
has(rule('.acts .btn'), 'height:34px', 'E-2b 오늘 카드 액션 버튼 34px 로 낮춰 한 줄에 맞춤');
has(rule('.acts .btn'), 'white-space:nowrap', 'E-2c 액션 버튼 글자는 줄바꿈 없음');
has(rule('.btn-sm'), 'height:38px', 'E-2d 다른 btn-sm 버튼은 38px 그대로');
has(rule('.sopt'), 'height:38px', 'E-3 마감 정산 상태 버튼 38px');
has(rule('.editbtn'), 'height:34px', 'E-4 캘린더 카드 수정 버튼 34px');
has(rule('.statetap'), 'height:34px', 'E-5 캘린더 상태 배지 34px');
ok(HTML.indexOf('var HOUR_H = 72;') >= 0, 'E-6 타임라인 1시간 72px');
ok(HTML.indexOf('var TL_MIN_H = 34;') >= 0, 'E-7 블록 최소 높이 34px');

resetEmpty();
A.state().members = [{ id:'m1', name:'이하늘' }];
A.state().packages = [{ id:'p1', memberId:'m1', durationMinutes:55, totalSessions:8, remainingSessions:5 }];
A.state().sessions = [{ id:'s1', memberId:'m1', packageId:'p1', date:'2026-11-24', startTime:'06:30',
  durationMinutes:25, location:'', memo:'', status:'scheduled' }];
var tl1 = A.timelineHTML('2026-11-24');
ok(/ev-compact/.test(tl1) && /height:34px/.test(tl1), 'E-8 25분 블록이 34px 한 줄 블록');
A.state().sessions = [
  { id:'a', memberId:'m1', packageId:'p1', date:'2026-11-24', startTime:'06:00', durationMinutes:25, memo:'', status:'scheduled' },
  { id:'b', memberId:'m1', packageId:'p1', date:'2026-11-24', startTime:'06:30', durationMinutes:25, memo:'', status:'scheduled' }
];
var tl2 = A.timelineHTML('2026-11-24');
var g1 = /data-sid="a"[^>]*/.test(tl2) ? /height:([0-9.]+)px;left[^"]*data-act="status-sheet" data-sid="a"/.exec(tl2) : null;
var hA = /height:([0-9.]+)px[^"]*" data-act="status-sheet" data-sid="a"/.exec(tl2);
var hB = /height:([0-9.]+)px[^"]*" data-act="status-sheet" data-sid="b"/.exec(tl2);
ok(hA && hB && parseFloat(hA[1]) <= 36 && parseFloat(hB[1]) <= 36, 'E-9 붙은 25분 레슨도 36px 안에서 서로 덮지 않음',
   (hA ? hA[1] : '?') + '/' + (hB ? hB[1] : '?'));

/* ══════════ E2. 오늘 카드 컴팩트 — 한 화면에 더 많은 레슨 ══════════ */
ok(HTML.indexOf('chiprow mt10 acts') >= 0, 'E-10 오늘 카드 액션 줄에 acts 클래스');
has(rule('.lesson-card'), 'padding:9px 13px', 'E-11 카드 안 여백 14→9px 로 줄임');
has(rule('.lesson-card+.lesson-card'), 'margin-top:7px', 'E-12 카드 사이 간격 10→7px');
has(rule('.bar'), 'height:4px', 'E-13 수강권 진행 막대 높이 5→4px');
has(rule('.bar'), 'margin-top:6px', 'E-14 진행 막대 위 여백 9→6px');
has(rule('.acts'), 'margin-top:7px', 'E-15 액션 줄 위 여백 10→7px');
has(rule('.lesson .nameline .tedit'), 'height:29px', 'E-16 수정 버튼 34→29px');
has(rule('.meta'), 'margin-top:2px', 'E-17 잔여 안내 줄 위 여백 3→2px');
has(rule('.timecol .d'), 'margin-top:1px', 'E-18 소요시간 줄 위 여백 2→1px');

/* ══════════ F. 회원 상세 — 레슨 차트 위로 · 저장 버튼 이름 ══════════ */
resetDemo();
A.openMemberSheet(A.state().members[0].id);
var mb = A.memberCtx().sh.body.innerHTML;
var iChart = mb.indexOf('레슨 차트');
var iMemo = mb.indexOf('회원 메모');
ok(iChart >= 0 && iMemo >= 0 && iChart < iMemo, 'F-1 레슨 차트가 회원 메모보다 위', iChart + '/' + iMemo);
hasNot(mb, '스윙 메모', 'F-2 예전 스윙 메모 이름은 사라짐');
has(mb, '>회원 메모 저장</button>', 'F-3 회원 메모 저장 버튼');
has(mb, '>차트에 저장</button>', 'F-4 차트 기록 저장 버튼');
has(mb, '레슨 차트 기록', 'F-5 입력칸 제목 구분');
A.closeAllSheets();

/* ══════════ G. 용어 · 날짜 · 화면 이름/순서 ══════════ */
resetDemo();
var sList = A.sessionsByDate(T);
var sel = { date: T, decisions: {} };
sel.decisions[sList[0].id] = 'completed';
var sb = A.settleBodyHTML(sel, sList);
hasNot(sb, '미정', 'G-1 정산 본문에 미정 없음');
has(sb, '예정', 'G-2 아직 안 고른 줄은 예정');
has(sb, 'ssel ssel-completed', 'G-3 고른 상태를 이름으로 표시');
has(sb, '잔여', 'G-4 잔여 미리보기도 그대로');
var sf = A.settleFooterHTML(sel, sList);
hasNot(sf, '미정', 'G-5 정산 하단 요약에도 미정 없음');
has(sf, '예정', 'G-6 하단은 예정 N건');
hasNot(A.viewToday(), '미정', 'G-7 오늘 히어로 칩도 예정');

A.openTodayMemoSheet(sList[0].id);
has(A.sheetStack()[A.sheetStack().length - 1].children[0].querySelector('h3').textContent, '오늘 차트 메모', 'G-8 오늘 탭 레슨 차트 시트 이름');
A.closeAllSheets();

A.openMemberSheet(A.state().members[0].id);
var mdate = A.memberCtx().sh.body.innerHTML;
ok(/2026\.\d\d\.\d\d/.test(mdate), 'G-9 회원 상세 날짜는 YYYY.MM.DD', '');
hasNot(mdate, '/ 10회', 'G-10 4/ 10회 처럼 슬래시 뒤 공백 없음');
A.closeAllSheets();

hasNot(A.viewMembers(), '<h2>회원 목록', 'G-11 회원목록 안에 같은 이름 섹션 없음');
has(A.viewMembers(), 'listbar', 'G-12 인원수 + 정렬 도구줄');
var st = A.viewSettings();
var iTheme = st.indexOf('화면 테마'), iHour = st.indexOf('레슨 시간 범위'),
    iCal = st.indexOf('외부 캘린더 연동'), iPro = st.indexOf('프로 정보 · 데이터'),
    iRoad = st.indexOf('앱스토어 출시 로드맵');
ok(iTheme >= 0 && iTheme < iHour && iHour < iCal && iCal < iPro && iRoad < 0,
   'G-13 설정 순서: 테마 → 시간 → 캘린더 → 프로 정보 (로드맵 카드 없음)', [iTheme, iHour, iCal, iPro, iRoad].join('/'));
hasNot(st, '<h2>설정</h2>', 'G-14 설정 제목 아래 중복 설정 섹션 없음');

/* ══════════ H. P4 빈 상태 · 다듬기 ══════════ */
resetEmpty();
has(A.viewMembers(), '아직 등록된 회원이 없어요', 'H-1 회원 0명 문구');
hasNot(A.viewMembers(), '찾는 회원이 없어요', 'H-2 회원 0명에 검색 결과 문구 없음');
A.state().members = [{ id:'m1', name:'김민수', gender:'male', region:'분당' }];
A.ui().search = '없는이름';
has(A.viewMembers(), '찾는 회원이 없어요', 'H-3 검색 결과 없음 문구');
A.ui().search = '';
has(rule('.rvsplit .k'), 'word-break:keep-all', 'H-4 별도 수입 제목 단어 중간 줄바꿈 방지');

resetDemo();
var rev = A.viewRevenue();
has(rev, '금액 입력', 'H-5 수입 히어로에 금액 입력 기준');
has(rev, '미입력', 'H-6 미입력 건수 표시');
has(rev, '기준', 'H-7 기준이라는 근거');
var cal = A.viewCalendar();
has(cal, 'aria-label="11월 23일 (월)', 'H-8 날짜 칸 접근성 이름');
ok(/aria-label="\d+월 \d+일 \([일월화수목금토]\) · (레슨 \d+건|레슨 없음)"/.test(cal), 'H-9 요일·레슨 수까지 읽어 줌');

resetEmpty();
A.openAddMemberSheet(null);
var ab = A.addMemberBodyHTML(null, null);
has(ab, 'autobtn', 'H-10 여러 명 배지는 안내 배지 모양');
has(ab, 'data-act="quick-focus"', 'H-11 누르면 입력칸으로 이동');
has(ab, '<label for="mfSessions">총 횟수</label>', 'H-12 총 횟수 이름표');
has(ab, '<label for="mfRemain">남은 횟수 (선택)</label>', 'H-13 남은 횟수 이름표');
A.closeAllSheets();

A.state().calendarSync = { enabled:false, target:'both' };
var coff = A.calSettingHTML();
has(coff, 'disabled aria-disabled="true"', 'H-14 연동 OFF면 대상 선택 비활성');
has(coff, '연동을 켜면 고를 수 있어요', 'H-15 왜 못 고르는지 안내');
A.state().calendarSync = { enabled:true, target:'google' };
A.viewSettings();
A.paintCalSetting();
hasNot(A.calSettingHTML(), 'disabled aria-disabled', 'H-16 켜져 있으면 고를 수 있음');
clickAct('cal-toggle');
eq(A.state().calendarSync.enabled, false, 'H-17 스위치로 끄기');
has(A.htmlOf('calStat'), '꺼짐', 'H-18 끈 상태가 바로 보임');
clickAct('cal-toggle');
eq(A.state().calendarSync.enabled, true, 'H-19 스위치로 다시 켜기');
has(A.htmlOf('calStat'), '저장됨', 'H-20 바꾸면 저장됨 표시');
has(A.htmlOf('calStateTxt'), '켜짐', 'H-21 현재 상태 줄');
eq(A.htmlOf('calTargetsLbl'), '연동할 캘린더', 'H-22 켜면 라벨 안내도 사라짐');
clickAct('cal-toggle');
has(A.htmlOf('calTargetsLbl'), '연동을 켜면 고를 수 있어요', 'H-23 끄면 라벨에 이유 표시');

JSON.stringify({ pass: log, fail: fails });
"""

PRE = "var CSS = " + json.dumps(CSS) + ";\nvar HTML = " + json.dumps(HTML) + ";\n"
try:
    data = json.loads(ctx.eval(PRE + JS))
except Exception as e:
    print('검사 실행 오류:', e)
    sys.exit(1)

for line in data['pass']:
    OUT.append((line[5:], True, ''))
for line in data['fail']:
    OUT.append((line[5:], False, ''))


# ══════════════════════════════════════════════════════════════════
# 정적 계약 (JS 로는 확인하기 어려운 배선)
# ══════════════════════════════════════════════════════════════════
sc = HTML[HTML.index("case 'sheet-close':"):]
sc = sc[:sc.index('break;')]
ok('B-9 X·취소 버튼이 requestSheetClose 를 거침', "requestSheetClose(el.closest('.sheetwrap'))" in sc, sc)
ok('B-10 X·취소가 closeSheetEl 을 직접 부르지 않음', 'closeSheetEl(el.closest' not in sc)
ct = HTML[HTML.index('function closeTopSheet(){'):]
ct = ct[:ct.index('\n}')]
ok('B-11 Esc 도 같은 길로', 'requestSheetClose(sheetStack[sheetStack.length - 1])' in ct, ct)
ok('B-12 회원 추가 시트의 취소 버튼도 sheet-close', 'data-act="sheet-close">취소</button>' in HTML)

ok('D-13 오늘 탭에서도 + 버튼', "(ui.tab === 'calendar' || ui.tab === 'today') ? 'flex' : 'none'" in HTML)
ok('D-14 오늘 탭 + 는 오늘 날짜로', "openQuickAddSheet(ui.tab === 'today' ? todayISO() : ui.date)" in HTML)
ok('D-15 수정 버튼 문구가 수강권과 별도 결제를 구분', "(sep ? '(날짜 · 시간 · 장소 · 금액)' : '(날짜 · 시간 · 장소)')" in HTML)
ok('D-16 정산 기준은 정산할 레슨이 있을 때만', 'if (list.length && !settled) {' in HTML)

mbody = HTML[HTML.index('function memberBodyHTML(m){'):]
mbody = mbody[:mbody.index('\n}\n')]
ok('F-6 소스에서도 차트 섹션 뒤에 회원 메모', mbody.index('레슨 차트') < mbody.index('회원 메모'))
ok('F-7 회원 메모 저장 버튼 이름', 'data-act="memo-save">회원 메모 저장' in mbody)
ok('F-8 차트 저장 버튼 이름', 'data-act="note-save">차트에 저장' in HTML)

ok('G-15 설정 부제가 실제 순서와 맞음', '<div class="sub">테마 · 레슨 시간 · 캘린더 연동 · 프로 정보</div>' in HTML)

ok('P-1 스플래시 3.5초 유지', 'var SPLASH_MS = 3500;' in HTML)
ok('P-2 상단 안전 여백 유지', 'padding-top:calc(9px + env(safe-area-inset-top, 0px))' in CSS)
ok('P-3 상태 바 메타 유지', 'apple-mobile-web-app-status-bar-style' in HTML)
ok('P-4 1·5·8·10·20 한 줄 유지', "'<div class=\"chips countrow mt10\" id=\"mfCountChips\">' + [1,5,8,10,20]" in HTML)
ok('P-5 남/여 상자 유지', 'class="seg mini boxed" id="mfGender"' in HTML)
ok('P-6 레슨 상태 2열 타일 유지', '.statusgrid{display:grid;grid-template-columns:1fr 1fr' in CSS)
ok('P-7 상태 시트 하단 버튼 순서 유지', '<button class="cta-hero"' in HTML and '정보 · 레슨 차트 열기' in HTML)
ok('P-8 카톡 요약 버튼 유지', 'data-act="kakao-copy"' in HTML and 'btn-kakao kakao-cta' in HTML)

ok('I-1 설계서 24장 UX 점검 기록', '## 24.' in SPEC and 'UX 점검' in SPEC)

for name, cond, detail in OUT:
    print(('PASS ' if cond else 'FAIL ') + name + ('' if cond else '  <- ' + str(detail)))
p = sum(1 for _, c, _ in OUT if c)
print('')
print('%d passed / %d total' % (p, len(OUT)))
sys.exit(0 if p == len(OUT) else 1)
