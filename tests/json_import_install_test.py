#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""데이터 가져오기(JSON 복원) + 홈 화면에 앱 추가 검사 (2026-11-24).

앱 스크립트 전체를 가짜 DOM 위에서 실행해, 화면 함수가 만든 HTML 과
파일 검사·확인 시트·복원·설치 안내 경로를 그대로 검사한다.

검사 묶음
  A. 설정 탭 화면 — 가져오기 버튼 위치, 숨은 파일칸, 홈 화면 카드 순서
  B. 백업 파일 검사·다듬기 — 형식 오류 4종, 항목별 보정·제외, 별도 결제, 빈 백업
  C. 확인 시트 · 복원 실행 — 확인 전 저장 안 됨, 취소·X, 복원 뒤 저장/토스트
  D. 홈 화면에 앱 추가 — standalone 숨김 두 조건, 아이폰/그 밖 안내, 설치 창
  E. 정적 무결성 — 파일 입력 속성, CSS 규칙, 이벤트 이름
  F. 설계서 기록 — 26장·27장·3.5장
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
# 앱 전체를 가짜 DOM 위에서 실행
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
  viewSettings: viewSettings, sheetStack: function(){ return sheetStack; },
  installCardHTML: installCardHTML, installApp: installApp, openInstallGuide: openInstallGuide,
  handleBeforeInstall: handleBeforeInstall, handleInstalled: handleInstalled,
  isStandalone: isStandalone, isIOS: isIOS,
  installEvt: function(){ return installEvt; }, setInstallEvt: function(e){ installEvt = e; },
  parseImportText: parseImportText, normalizeImported: normalizeImported, importCounts: importCounts,
  openImportConfirm: openImportConfirm, applyImport: applyImport, importSummaryHTML: importSummaryHTML,
  pickImportFile: pickImportFile, onImportFilePicked: onImportFilePicked,
  importCtx: function(){ return importCtx; }, setImportCtx: function(v){ importCtx = v; },
  closeSheetEl: closeSheetEl, requestSheetClose: requestSheetClose, closeAllSheets: closeAllSheets,
  onClick: onClick, setState: function(s){ state = s; }, state: function(){ return state; },
  buildDemo: buildDemo, blankState: blankState, ui: function(){ return ui; },
  save: save, setObWaiting: function(v){ obWaiting = v; }, KEY: KEY,
  todayISO: todayISO, doc: document
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
function clearToast(){ EL('toast').textContent = ''; EL('toast').innerHTML = ''; }
function toastText(){ return EL('toast').innerHTML; }
function lastSheet(){ var r = EL('sheetRoot'); return r.children[r.children.length - 1]; }
function sheetPart(wrap, sel){ return wrap.children[0].querySelector(sel).innerHTML; }
function clickAct(act, wrap){
  A.onClick({ target: { closest: function(){
    return { getAttribute: function(){ return act; }, closest: function(){ return wrap; } };
  } } });
}
function newSheetCount(before){ return A.sheetStack().length - before; }

/* ── 검사용 백업 한 부 (정상 + 일부러 망가뜨린 항목) ── */
function backup(){
  return {
    version: 2,
    pro: { name:'이시훈', title:'KPGA 투어 프로', academy:'그린필드 골프 아카데미' },
    members: [
      { id:'m1', name:'김도현', gender:'male', region:'분당', phone:'010-2451-7782', level:'중급', since:'2026-01-05', memo:'드라이버 헤드 스피드 46m/s' },
      { id:'m2', name:'박서연', gender:'female', region:'판교', since:'2026-03-01' },
      { id:'m1', name:'정민재', gender:'male', region:'강남', since:'2026-04-02' },
      { id:'m4', name:'   ', gender:'female' }
    ],
    packages: [
      { id:'p1', memberId:'m1', durationMinutes:55, totalSessions:8, remainingSessions:20,
        startDate:'2026-10-01', expiryDate:'2027-03-01', price:800000, note:'' },
      { id:'p2', memberId:'ghost', totalSessions:10, remainingSessions:4 },
      { id:'p3', memberId:'m2', durationMinutes:25, totalSessions:0, remainingSessions:0 }
    ],
    sessions: [
      { id:'s1', memberId:'m1', packageId:'p1', date:'2026-11-24', startTime:'7:00', durationMinutes:0,
        location:'분당 실내연습장', status:'completed', memo:'드라이버 교정' },
      { id:'s2', memberId:'m1', packageId:'p1', date:'2026-11-25', startTime:'07:00', durationMinutes:55, status:'이상한값' },
      { id:'s3', memberId:null, packageId:'', guestName:'한빛상사 팀', lessonKind:'field', separatePay:true,
        fee:'450000', date:'2026-11-20', startTime:'09:30', durationMinutes:180, status:'completed' },
      { id:'s4', memberId:'ghost', packageId:'', date:'2026-11-19', startTime:'10:00', durationMinutes:55, status:'completed' },
      { id:'s5', memberId:'m1', packageId:'p1', date:'2026-11-XX', startTime:'10:00', durationMinutes:55 }
    ],
    notes: [
      { memberId:'m1', date:'2026-11-23', text:'드라이버 백스윙 톱 교정' },
      { memberId:'ghost', text:'회원이 없어 버려짐' }
    ],
    settlements: [
      { date:'2026-11-23', settledAt:'2026-11-23T21:00:00', counts:{ completed:3, no_show:0 }, deducted:3 },
      { date:'망가진날짜', deducted:1 }
    ],
    templates: [],
    hours: { fromMin:100, toMin:9000 },
    theme: 'black',
    calendarSync: { enabled:'yes', target:'nope' },
    renewalLog: [ { memberId:'m1', name:'김도현', kind:'renewal' } ],
    cancelLog: [ { date:'2026-11-10', memberId:'m1', at:'2026-11-10T20:00:00' }, 'not-object' ]
  };
}
function parseBackup(){ return A.parseImportText(JSON.stringify(backup())); }
function freshDemo(){
  A.setObWaiting(false);
  A.setState(A.buildDemo());
  A.ui().tab = 'settings'; A.ui().date = A.todayISO();
  A.closeAllSheets(); A.setImportCtx(null); A.setInstallEvt(null);
  clearToast();
}

/* ══════════ A. 설정 탭 화면 ══════════ */
freshDemo();
navigator.userAgent = 'test'; navigator.standalone = false;
window.matchMedia = function(){ return { matches:false }; };
var vs = A.viewSettings();
has(vs, 'data-act="import-data"', 'A-1 설정 탭에 데이터 가져오기(복원) 버튼');
has(vs, '데이터 가져오기 (복원)', 'A-2 버튼 글자');
ok(vs.indexOf('export-data') < vs.indexOf('import-data'), 'A-3 내보내기 다음에 가져오기');
ok(vs.indexOf('import-data') - vs.indexOf('export-data') < 220, 'A-4 두 버튼이 붙어 있음 (바로 아래)');
has(vs, 'data-act="export-data"', 'A-5 내보내기는 그대로');
has(vs, '이 기기의 데이터는 파일 내용으로 바뀌고', 'A-6 가져오기 아래 안내');
has(vs, 'data-act="install-app"', 'A-7 홈 화면에 앱 추가 버튼');
has(vs, 'ProPlan을 앱처럼 열기', 'A-8 설치 카드 문구');
has(vs, '홈 화면에 앱 추가', 'A-9 설치 카드 제목/버튼');
var iTheme = vs.indexOf('화면 테마'), iHour = vs.indexOf('레슨 시간 범위'),
    iCal = vs.indexOf('외부 캘린더 연동'), iIns = vs.indexOf('홈 화면에 앱 추가'),
    iPro = vs.indexOf('프로 정보 · 데이터');
ok(iTheme >= 0 && iTheme < iHour && iHour < iCal && iCal < iIns && iIns < iPro,
   'A-10 설정 순서: 테마 → 시간 → 캘린더 → 홈 화면 → 프로 정보',
   [iTheme, iHour, iCal, iIns, iPro].join(','));
/* 아이폰이면 공유 버튼 안내 */
navigator.userAgent = 'Mozilla/5.0 (iPhone; CPU iPhone OS 18_1 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.0 Mobile/15E148 Safari/604.1';
var vsIos = A.viewSettings();
has(vsIos, '아이폰 사파리', 'A-11 아이폰이면 카드 옆에 아이폰 사파리');
has(vsIos, '공유(□↑)', 'A-12 아이폰이면 공유 버튼 안내');
has(vsIos, '카카오톡', 'A-13 앱 안 브라우저 주의 문구');

/* ══════════ B. 백업 파일 검사·다듬기 ══════════ */
var res = parseBackup();
ok(res.ok, 'B-1 정상 백업은 통과', res.msg || '');
var st = res.state;
eq(st.members.length, 3, 'B-2 회원 3명 (이름 없는 1명 제외)');
eq(res.skipped.members, 1, 'B-3 제외한 회원 1명');
eq(st.members[0].name, '김도현', 'B-4 첫 회원 이름');
ok(st.members[2].id !== 'm1', 'B-5 겹친 회원 id 는 새로 발급', st.members[2].id);
eq(st.members[0].id, 'm1', 'B-6 첫 회원 id 는 그대로');
eq(st.packages.length, 1, 'B-7 수강권 1건 (없는 회원·0회 제외)');
eq(res.skipped.packages, 2, 'B-8 제외한 수강권 2건');
eq(st.packages[0].remainingSessions, 8, 'B-9 잔여 횟수는 총 횟수로 자름 (20 → 8)');
eq(st.packages[0].memberId, 'm1', 'B-10 수강권 회원 연결');
eq(st.sessions.length, 3, 'B-11 레슨 3건 (회원 없음·날짜 깨짐 제외)');
eq(res.skipped.sessions, 2, 'B-12 제외한 레슨 2건');
eq(st.sessions[0].startTime, '07:00', 'B-13 7:00 → 07:00');
eq(st.sessions[0].durationMinutes, 55, 'B-14 분이 비면 수강권 55분');
eq(st.sessions[0].deducted, true, 'B-15 완료는 차감');
eq(st.sessions[1].status, 'scheduled', 'B-16 모르는 상태는 예정');
eq(st.sessions[1].deducted, false, 'B-17 예정은 미차감');
ok(st.sessions[2].separatePay === true, 'B-18 별도 결제 레슨 유지');
eq(st.sessions[2].lessonKind, 'field', 'B-19 별도 결제 종류 field');
eq(st.sessions[2].guestName, '한빛상사 팀', 'B-20 비회원 이름 유지');
eq(st.sessions[2].fee, 450000, 'B-21 금액 문자열 → 숫자');
eq(st.sessions[2].charged, true, 'B-22 별도 결제 수입 포함');
eq(st.sessions[2].deducted, false, 'B-23 별도 결제는 수강권 미차감');
eq(st.sessions[2].packageId, '', 'B-24 별도 결제는 수강권 연결 없음');
eq(st.notes.length, 1, 'B-25 회원 있는 차트 메모만');
eq(st.notes[0].date, '2026-11-23', 'B-26 메모 날짜 유지');
ok(st.notes[0].tags && st.notes[0].tags.length > 0, 'B-27 메모 태그 다시 계산');
eq(st.settlements.length, 1, 'B-28 정산 기록 1건 (날짜 깨짐 제외)');
eq(st.settlements[0].deducted, 3, 'B-29 정산 차감 3');
ok(st.settlements[0].counts.completed === 3 && !st.settlements[0].counts.no_show, 'B-30 정산 counts 양수만');
eq(st.templates.length, 3, 'B-31 템플릿이 비면 기본 3종');
eq(st.hours.fromMin, 300, 'B-32 시작 범위 아래로 자름 (100 → 300)');
eq(st.hours.toMin, 1440, 'B-33 마감 범위 위로 자름 (9000 → 1440)');
eq(st.theme, 'black', 'B-34 테마 유지');
eq(st.calendarSync.enabled, false, 'B-35 캘린더 enabled 는 true 만 인정');
eq(st.calendarSync.target, 'both', 'B-36 캘린더 대상 보정');
eq(st.pro.name, '이시훈', 'B-37 프로 이름');
eq(st.pro.academy, '그린필드 골프 아카데미', 'B-38 소속');
eq(st.renewalLog.length, 1, 'B-39 재등록 기록 유지');
eq(st.renewalLog[0].memberId, 'm1', 'B-40 재등록 기록 회원 연결');
eq(st.cancelLog.length, 1, 'B-41 일반취소 기록은 객체만');
eq(st.migExcused, 1, 'B-42 예전 일반취소 정리 표시');
ok(!st.freshStart, 'B-43 복원본은 새 시작 표시 없음');

/* 형식 오류 4종 */
var e1 = A.parseImportText('');
ok(!e1.ok && e1.msg.indexOf('비어') >= 0, 'B-44 빈 파일 거부', e1.msg);
var e2 = A.parseImportText('이건 JSON 이 아님');
ok(!e2.ok && e2.msg.indexOf('JSON') >= 0, 'B-45 JSON 아님 거부', e2.msg);
var e3 = A.parseImportText('[1,2,3]');
ok(!e3.ok && e3.msg.indexOf('앱 데이터') >= 0, 'B-46 최상위 배열 거부', e3.msg);
var e4 = A.parseImportText(JSON.stringify({ members:{}, packages:[], sessions:[] }));
ok(!e4.ok && e4.msg.indexOf('ProPlan') >= 0, 'B-47 배열이 아니면 거부', e4.msg);
var e5 = A.parseImportText(JSON.stringify({ members:[], packages:[] }));
ok(!e5.ok, 'B-48 필수 목록이 빠지면 거부');
var e6 = A.parseImportText('\uFEFF' + JSON.stringify(backup()));
ok(e6.ok, 'B-49 BOM 이 붙은 파일도 읽음');
/* 빈 상태 백업은 그대로 복원 가능 */
var e7 = A.parseImportText(JSON.stringify({ members:[], packages:[], sessions:[] }));
ok(e7.ok && e7.state.members.length === 0 && e7.state.sessions.length === 0, 'B-50 빈 백업도 복원 가능');

/* ══════════ C. 확인 시트 · 복원 실행 ══════════ */
freshDemo();
var demoCount = A.state().members.length;
var demoJson = localStorage.getItem(A.KEY);
var before = A.sheetStack().length;
var sh = A.openImportConfirm(JSON.stringify(backup()), 'golf-lesson-data-2026-11-24.json');
ok(sh !== null, 'C-1 확인 시트가 열림');
eq(newSheetCount(before), 1, 'C-2 시트 1장 추가');
var wrap = lastSheet();
eq(sheetPart(wrap, 'h3'), '이 데이터로 복원할까요?', 'C-3 시트 제목');
var body = sheetPart(wrap, '.sb');
has(body, 'golf-lesson-data-2026-11-24.json', 'C-4 파일 이름 표시');
has(body, '회원', 'C-5 회원 칸');
has(body, '<div class="n">3<small>명</small>', 'C-6 회원 3명 요약');
has(body, '수강권', 'C-7 수강권 칸');
has(body, '레슨', 'C-8 레슨 칸');
has(body, '레슨 차트', 'C-9 레슨 차트 칸');
has(body, '지금 이 기기의 데이터가 파일 내용으로 바뀝니다', 'C-10 경고 문구');
has(body, '되돌릴 수 없어요', 'C-11 되돌릴 수 없음 안내');
has(body, '데이터 내보내기 (JSON)', 'C-12 먼저 내보내기 권장');
has(body, '빼고 복원해요', 'C-13 빼고 복원하는 건수 안내');
var foot = sheetPart(wrap, '.sf');
has(foot, 'data-act="import-cancel"', 'C-14 취소 버튼');
has(foot, '취소', 'C-15 취소 글자');
has(foot, 'data-act="import-confirm"', 'C-16 복원 버튼');
has(foot, '이 데이터로 복원하기', 'C-17 복원 버튼 글자');
eq(A.state().members.length, demoCount, 'C-18 확인 전에는 상태 그대로');
eq(localStorage.getItem(A.KEY), demoJson, 'C-19 확인 전에는 저장도 그대로');
ok(A.importCtx() !== null, 'C-20 복원 후보 대기');

/* 취소 → 아무것도 바뀌지 않음 */
clearToast();
clickAct('import-cancel', wrap);
eq(A.sheetStack().length, 0, 'C-21 취소하면 시트 닫힘');
ok(A.importCtx() === null, 'C-22 취소하면 후보 버림');
eq(A.state().members.length, demoCount, 'C-23 취소하면 상태 그대로');
eq(localStorage.getItem(A.KEY), demoJson, 'C-24 취소하면 저장 그대로');

/* X 로 닫아도 후보가 풀린다 */
A.openImportConfirm(JSON.stringify(backup()), 'b.json');
var w2 = lastSheet();
A.requestSheetClose(w2);
ok(A.importCtx() === null, 'C-25 X 로 닫으면 후보 버림');
var stateBefore = A.state().members.length;
clickAct('import-confirm', w2);
eq(A.state().members.length, stateBefore, 'C-26 닫힌 뒤 복원 클릭은 아무 일 없음');
eq(A.sheetStack().length, 0, 'C-27 시트도 그대로 닫힘');

/* 다시 열고 복원 */
freshDemo();
A.openImportConfirm(JSON.stringify(backup()), 'golf-lesson-data-2026-11-24.json');
var w3 = lastSheet();
clearToast();
clickAct('import-confirm', w3);
eq(A.sheetStack().length, 0, 'C-28 복원하면 시트 닫힘');
eq(A.state().members.length, 3, 'C-29 회원이 백업 내용으로 교체');
eq(A.state().sessions.length, 3, 'C-30 레슨도 교체');
eq(A.state().pro.name, '이시훈', 'C-31 프로 정보 복원');
ok(A.importCtx() === null, 'C-32 후보 비움');
var saved = JSON.parse(localStorage.getItem(A.KEY));
eq(saved.members.length, 3, 'C-33 localStorage 에 저장됨');
eq(saved.sessions.length, 3, 'C-34 저장된 레슨 3건');
eq(saved.theme, 'black', 'C-35 테마도 함께 복원');
has(toastText(), '데이터를 복원했어요', 'C-36 복원 토스트');
has(toastText(), '회원 3명', 'C-37 토스트에 회원 수');
has(toastText(), '레슨 3건', 'C-38 토스트에 레슨 수');
eq(A.ui().tab, 'today', 'C-39 복원 뒤 오늘 탭으로');
document.documentElement.setAttribute('data-theme', 'black');
ok(EL('main').innerHTML.indexOf('오늘') >= 0, 'C-40 복원 뒤 화면을 다시 그림');

/* 잘못된 파일은 시트 없이 토스트만 */
freshDemo();
var n0 = A.sheetStack().length;
var bad = A.openImportConfirm('그냥 글자', 'x.json');
ok(bad === null, 'C-41 잘못된 파일은 시트를 열지 않음');
eq(A.sheetStack().length, n0, 'C-42 시트 0장');
has(toastText(), 'JSON 파일이 아니에요', 'C-43 이유를 토스트로');
eq(A.state().members.length, demoCount, 'C-44 상태 그대로');

/* 파일 고르기 · 파일 읽기 */
freshDemo();
var picked = 0;
EL('importFile').click = function(){ picked++; };
EL('importFile').value = 'C:\\fakepath\\old.json';
A.pickImportFile();
eq(picked, 1, 'C-45 파일 선택칸을 누름');
eq(EL('importFile').value, '', 'C-46 같은 파일을 다시 고를 수 있게 비움');
/* 크기 제한 */
clearToast();
A.onImportFilePicked({ target: { files: [ { name:'huge.json', size: 9 * 1024 * 1024 } ], value:'' } });
has(toastText(), '파일이 너무 커요', 'C-47 8MB 넘는 파일 거부');
/* 읽기 성공 → 확인 시트 */
globalThis.FileReader = function(){
  var self = this;
  this.readAsText = function(f){ self.result = f._text; self.onload(); };
};
clearToast();
var n1 = A.sheetStack().length;
A.onImportFilePicked({ target: { files: [ { name:'golf-lesson-data-2026-11-24.json', size: 2048,
  _text: JSON.stringify(backup()) } ], value:'' } });
eq(A.sheetStack().length, n1 + 1, 'C-48 파일을 읽으면 확인 시트');
has(sheetPart(lastSheet(), '.sb'), 'golf-lesson-data-2026-11-24.json', 'C-49 고른 파일 이름');
A.closeAllSheets(); A.setImportCtx(null);
/* 읽기 실패(JSON 아님) → 토스트만 */
clearToast();
var n2 = A.sheetStack().length;
A.onImportFilePicked({ target: { files: [ { name:'x.json', size: 10, _text:'hello' } ], value:'' } });
eq(A.sheetStack().length, n2, 'C-50 JSON 아닌 파일은 시트 없음');
has(toastText(), 'JSON', 'C-51 이유 안내');

/* ══════════ D. 홈 화면에 앱 추가 ══════════ */
freshDemo();
navigator.userAgent = 'test'; navigator.standalone = false;
window.matchMedia = function(){ return { matches:false }; };
ok(!A.isStandalone(), 'D-1 보통 브라우저는 standalone 아님');
window.matchMedia = function(){ return { matches:true }; };
ok(A.isStandalone(), 'D-2 display-mode standalone 감지');
eq(A.viewSettings().indexOf('install-app'), -1, 'D-3 standalone 이면 카드 숨김');
hasNot(A.viewSettings(), '홈 화면에 앱 추가', 'D-4 standalone 이면 문구도 없음');
eq(A.installCardHTML(), '', 'D-5 standalone 이면 카드 HTML 빈 값');
window.matchMedia = function(){ return { matches:false }; };
navigator.standalone = true;
ok(A.isStandalone(), 'D-6 navigator.standalone 감지 (아이폰)');
eq(A.viewSettings().indexOf('install-app'), -1, 'D-7 아이폰 standalone 도 숨김');
navigator.standalone = false;
has(A.viewSettings(), 'data-act="install-app"', 'D-8 다시 보통 브라우저면 카드 보임');

ok(A.isIOS() === false, 'D-9 테스트 UA 는 아이폰 아님');
navigator.userAgent = 'Mozilla/5.0 (iPhone; CPU iPhone OS 18_1 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.0 Mobile/15E148 Safari/604.1';
ok(A.isIOS(), 'D-10 아이폰 UA 감지');
navigator.userAgent = 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.0 Safari/605.1.15';
navigator.maxTouchPoints = 5;
ok(A.isIOS(), 'D-11 아이패드 사파리(맥 + 터치) 감지');
navigator.maxTouchPoints = 0;
ok(A.isIOS() === false, 'D-12 맥 데스크톱은 아이폰 아님');

/* 아이폰 안내 시트 */
navigator.userAgent = 'Mozilla/5.0 (iPhone; CPU iPhone OS 18_1 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.0 Mobile/15E148 Safari/604.1';
A.closeAllSheets();
var sh1 = A.openInstallGuide();
var b1 = sheetPart(lastSheet(), '.sb');
has(b1, '화면 아래 공유(□↑) 버튼 누르기', 'D-13 1단계: 공유 버튼');
has(b1, '‘홈 화면에 추가’ 누르기', 'D-14 2단계: 홈 화면에 추가');
eq((b1.match(/class="num"/g) || []).length, 2, 'D-15 단계 번호 2개');
has(b1, 'ProPlan 아이콘', 'D-16 ProPlan 아이콘 안내');
has(b1, '주소창 없이 전체 화면', 'D-17 전체 화면 안내');
has(sheetPart(lastSheet(), '.sf'), '알겠어요', 'D-18 닫기 버튼');
eq(sheetPart(lastSheet(), 'h3'), '홈 화면에 앱 추가', 'D-19 시트 제목');
A.closeAllSheets();

/* 그 밖의 브라우저 안내 시트 */
navigator.userAgent = 'Mozilla/5.0 (Linux; Android 14) AppleWebKit/537.36 Chrome/126 Mobile Safari/537.36';
A.openInstallGuide();
var b2 = sheetPart(lastSheet(), '.sb');
has(b2, '브라우저 메뉴 열기', 'D-20 안드로이드/기타는 메뉴 안내');
hasNot(b2, '공유(□↑)', 'D-21 공유 버튼 문구는 없음');
A.closeAllSheets();

/* 버튼 → 설치 창이 없으면 안내 시트 */
clearToast();
var n3 = A.sheetStack().length;
A.setInstallEvt(null);
A.installApp();
eq(A.sheetStack().length, n3 + 1, 'D-22 설치 창이 없으면 안내 시트');
has(sheetPart(lastSheet(), 'h3'), '홈 화면에 앱 추가', 'D-23 안내 시트 제목');
A.closeAllSheets();

/* beforeinstallprompt 잡기 */
var prevented = 0;
var fakeEvt = { preventDefault: function(){ prevented++; }, prompt: function(){ this.prompted = (this.prompted || 0) + 1; },
  userChoice: { then: function(cb){ cb({ outcome:'accepted' }); return { catch:function(){} }; } } };
A.handleBeforeInstall(fakeEvt);
eq(prevented, 1, 'D-24 기본 배너를 막고 잡아 둠');
ok(A.installEvt() === fakeEvt, 'D-25 설치 요청 보관');
clearToast();
navigator.userAgent = 'Mozilla/5.0 (Linux; Android 14) AppleWebKit/537.36 Chrome/126 Mobile Safari/537.36';
A.installApp();
eq(fakeEvt.prompted, 1, 'D-26 버튼에서 설치 창 한 번 띄움');
has(toastText(), '홈 화면에 추가하는 중', 'D-27 수락 토스트');
ok(A.installEvt() === null, 'D-28 설치 요청은 한 번 쓰면 사라짐');
eq(A.sheetStack().length, 0, 'D-29 설치 창이 뜨면 안내 시트는 열지 않음');

/* 취소 선택 */
var fakeEvt2 = { preventDefault: function(){}, prompt: function(){ this.prompted = 1; },
  userChoice: { then: function(cb){ cb({ outcome:'dismissed' }); return { catch:function(){} }; } } };
A.handleBeforeInstall(fakeEvt2);
clearToast();
A.installApp();
has(toastText(), '설치를 취소했어요', 'D-30 취소 토스트');
ok(A.installEvt() === null, 'D-31 취소해도 요청 소진');

/* 설치 완료 */
A.handleBeforeInstall(fakeEvt2);
clearToast();
A.ui().tab = 'settings';
A.handleInstalled();
ok(A.installEvt() === null, 'D-32 설치 완료 뒤 요청 비움');
has(toastText(), '홈 화면에 앱을 추가했어요', 'D-33 설치 완료 토스트');

/* standalone 에서 누르면 안내만 */
window.matchMedia = function(){ return { matches:true }; };
clearToast();
var n4 = A.sheetStack().length;
A.installApp();
has(toastText(), '이미 홈 화면 앱으로', 'D-34 이미 앱이면 토스트만');
eq(A.sheetStack().length, n4, 'D-35 시트는 열지 않음');
window.matchMedia = function(){ return { matches:false }; };
"""

result = ctx.eval("(function(){ " + JS + "\n return JSON.stringify({ log: log, fails: fails }); })()")
data = json.loads(result)

for line in data['log']:
    print(line)
for line in data['fails']:
    print(line)
passed = len(data['log'])
total = passed + len(data['fails'])

# ── E. 정적 무결성 ────────────────────────────────────────
static = []


def sok(name, cond, detail=''):
    static.append((name, bool(cond), detail))


m = re.search(r'<input type="file" id="importFile"[^>]*>', HTML)
sok('E-1 숨은 파일 선택칸 존재', m is not None)
if m:
    tag = m.group(0)
    sok('E-2 .json 만 받기', 'accept=".json,application/json"' in tag, tag)
    sok('E-3 화면에 보이지 않음 (hidden)', ' hidden' in tag, tag)
    sok('E-4 탭 순서에서 빠짐', 'tabindex="-1"' in tag, tag)
sok('E-5 파일 선택칸이 시트 루트 옆(화면 밖)', HTML.index('id="importFile"') > HTML.index('id="sheetRoot"'))
sok('E-6 확인 시트 복원 버튼 액션', "case 'import-confirm':" in HTML)
sok('E-7 취소 액션', "case 'import-cancel':" in HTML)
sok('E-8 가져오기 액션', "case 'import-data':" in HTML)
sok('E-9 설치 액션', "case 'install-app':" in HTML)
sok('E-10 beforeinstallprompt 구독', "window.addEventListener('beforeinstallprompt', handleBeforeInstall)" in HTML)
sok('E-11 appinstalled 구독', "window.addEventListener('appinstalled', handleInstalled)" in HTML)
sok('E-12 파일 change 구독', "importInput.addEventListener('change', onImportFilePicked)" in HTML)
sok('E-13 importCtx 시트 닫힘 정리', "typeof importCtx !== 'undefined'" in HTML and 'importCtx.sh.el === wrap' in HTML)
sok('E-14 확인 전 저장 없음 (applyImport 에서만 state 교체)',
    'function applyImport(){' in HTML and 'state = ctx.state;' in HTML)
sok('E-15 8MB 제한', 'IMPORT_MAX = 8 * 1024 * 1024' in HTML)
sok('E-16 .impk 요약 그리드 CSS', '.impk{' in CSS and '.impk .kpi{' in CSS)
sok('E-17 경고 노란 상자 CSS', '.impwarn{' in CSS and 'var(--amber-soft)' in rule('.impwarn'))
sok('E-18 블랙 테마 경고 보정', 'html[data-theme="black"] .impwarn{' in CSS)
sok('E-19 설치 카드 CSS', '.inscard{' in CSS and '.inscard .ic{' in CSS)
sok('E-20 안내 단계 CSS', '.insstep{' in CSS and '.insstep .num{' in CSS and '.insnote{' in CSS)
sok('E-21 단계 번호는 초록 알약', 'background:var(--green-soft)' in rule('.insstep .num'))
sok('E-22 파일 이름 줄 CSS', '.impfile{' in CSS)
sok('E-23 버튼 44px 터치 높이 유지', 'height:44px' in rule('.btn'))
sok('E-24 설정 화면 홈 화면 카드 호출', 'h += installCardHTML();' in HTML)
sok('E-25 카드 숨김 조건 두 가지', "matchMedia('(display-mode: standalone)')" in HTML and 'standalone === true' in HTML)

for name, cond, detail in static:
    print(('PASS ' if cond else 'FAIL ') + name + ('' if cond else '  <- ' + str(detail)))
    if cond:
        passed += 1
    else:
        data['fails'].append(name)
    total += 1

# ── F. 설계서 ─────────────────────────────────────────────
spec_checks = [
    ('F-1 설계서 26장 데이터 가져오기', '## 26. 데이터 가져오기 (JSON 복원)' in SPEC),
    ('F-2 설계서 27장 홈 화면에 앱 추가', '## 27. 홈 화면에 앱 추가' in SPEC),
    ('F-3 3.5장에 가져오기 버튼', '`데이터 가져오기 (복원)`' in SPEC),
    ('F-4 3.5장 설정 순서', '화면 테마 → 레슨 시간 범위 → 외부 캘린더 연동 → 홈 화면에 앱 추가 → 프로 정보 · 데이터' in SPEC),
    ('F-5 확인 시트 문구 기록', '이 데이터로 복원할까요?' in SPEC and '이 데이터로 복원하기' in SPEC),
    ('F-6 검사 규칙 기록', '8MB' in SPEC and 'remainingSessions' in SPEC),
    ('F-7 아이폰 안내 기록', '화면 아래 공유(□↑) 버튼 누르기' in SPEC),
    ('F-8 standalone 숨김 기록', 'display-mode: standalone' in SPEC and 'navigator.standalone' in SPEC),
    ('F-9 검증 스위트 이름', 'tests/json_import_install_test.py' in SPEC),
    ('F-10 사용법 11장에 복원 안내', '백업 되살리기' in SPEC),
]
for name, cond in spec_checks:
    print(('PASS ' if cond else 'FAIL ') + name)
    if cond:
        passed += 1
    else:
        data['fails'].append(name)
    total += 1

print('')
print('%d passed / %d total' % (passed, total))
sys.exit(0 if not data['fails'] else 1)
