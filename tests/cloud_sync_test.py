#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""계정 · 클라우드 동기화(Supabase) 검사 (2026-11-26).

앱 스크립트 전체를 가짜 DOM + 가짜 Supabase 클라이언트 위에서 실행해
설정 탭 계정 카드 · 로그인/회원가입 시트 · 이메일 인증 안내 · 기기↔서버 기록 변환 ·
동기화 예약/실패/오프라인 · 이관(백업) 경로를 그대로 검사한다.

검사 묶음
  A. 설정 탭 계정 카드 — 맨 위 위치, 로그인 전/후 모양, 16px 입력 규칙
  B. 로그인 · 회원가입 시트 — 칸 구성, 입력 검사, 실패 문구
  C. 가입 결과 두 갈래 — 세션 있음(바로 로그인) / 없음(인증 메일 안내)
  D. 기기 상태 → 서버 백업 JSON — 회원·수강권·레슨·차트·정산·설정
  E. 서버 행 → 기기 상태 — 상태 이름·시간·별도결제·설정 복원
  F. 왕복 무손실 — 데모 기록을 올렸다 받아도 건수·잔여·상태가 같음
  G. 동기화 엔진 — 예약·순서·실패·오프라인·수동 동기화
  H. 이관·덮어쓰기 안전 — 로컬만 있을 때 자동으로 지우지 않음
  I. 계정 해제 · 정적 무결성 · 설계서 기록
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
  this.tagName = 'DIV';
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
  body: new El('body'), hidden: false
};
function setTimeout(){ return 1; }
function clearTimeout(){}
function setInterval(){ return 1; }
var window = { addEventListener:function(){}, open:function(){},
  matchMedia:function(){ return { matches:false, addEventListener:function(){} }; } };
window.document = document;
var localStorage = { _d:{}, getItem:function(k){ return this._d[k] === undefined ? null : this._d[k]; },
  setItem:function(k,v){ this._d[k] = String(v); }, removeItem:function(k){ delete this._d[k]; } };
var navigator = { userAgent:'test', onLine:true };
var location = { origin:'https://issuelee9040.github.io', pathname:'/Golf--lesson-app/',
  hash:'', search:'', href:'https://issuelee9040.github.io/Golf--lesson-app/' };

/* ---- 가짜 Supabase 클라이언트 ----
   실제 supabase-js 는 Promise 를 주지만, 검사 환경에는 microtask 큐가 없어
   .then(ok, err) 을 그 자리에서 실행하는 thenable 로 대신한다(앱은 항상 두 인자 형태만 씀). */
function Thenable(v, e){ this._v = v; this._e = e; }
function wrapThenable(r){ return (r instanceof Thenable) ? r : new Thenable(r, null); }
Thenable.prototype.then = function(ok, bad){
  if (this._e) {
    if (typeof bad === 'function') { try { return wrapThenable(bad(this._e)); } catch(e){ return new Thenable(null, e); } }
    return this;
  }
  if (typeof ok !== 'function') return this;
  try { return wrapThenable(ok(this._v)); } catch(e){ return new Thenable(null, e); }
};
Thenable.prototype.catch = function(bad){ return this.then(null, bad); };

var FAKE = {
  rpcCalls: [], signUpCalls: [], signInCalls: [], selectCalls: [], signOutCalls: 0,
  authCb: null,
  rpcResult: { data: { ok:true }, error: null },
  signUpResult: { data: { user: { email:'a@b.c' }, session: null }, error: null },
  signInResult: { data: { session: null }, error: null },
  sessionResult: null,
  tables: {},
  reset: function(){
    FAKE.rpcCalls = []; FAKE.signUpCalls = []; FAKE.signInCalls = []; FAKE.selectCalls = [];
    FAKE.signOutCalls = 0; FAKE.authCb = null;
    FAKE.rpcResult = { data: { ok:true }, error: null };
    FAKE.tables = {}; FAKE.sessionResult = null;
    FAKE.signUpResult = { data: { user: { email:'a@b.c' }, session: null }, error: null };
    FAKE.signInResult = { data: { session: null }, error: null };
  }
};
function fakeClient(){
  return {
    auth: {
      onAuthStateChange: function(cb){ FAKE.authCb = cb; return { data: { subscription: { unsubscribe: function(){} } } }; },
      getSession: function(){ return new Thenable({ data: { session: FAKE.sessionResult } }, null); },
      signUp: function(p){ FAKE.signUpCalls.push(p); return new Thenable(FAKE.signUpResult, null); },
      signInWithPassword: function(p){ FAKE.signInCalls.push(p); return new Thenable(FAKE.signInResult, null); },
      signOut: function(){ FAKE.signOutCalls++; return new Thenable({ error: null }, null); }
    },
    rpc: function(name, args){ FAKE.rpcCalls.push({ name:name, args:args }); return new Thenable(FAKE.rpcResult, null); },
    from: function(t){ return { select: function(cols){
      FAKE.selectCalls.push(t);
      return new Thenable({ data: FAKE.tables[t] || [], error: null }, null);
    } }; }
  };
}
window.supabase = { createClient: function(){ return fakeClient(); } };
var CSSRULE = __CSSRULE__;
"""

EXPORT = r"""
globalThis.__api = {
  /* 화면 */
  viewSettings: viewSettings, cloudCardHTML: cloudCardHTML,
  openAuthSheet: openAuthSheet, paintAuthSheet: paintAuthSheet, closeAuthSheet: closeAuthSheet,
  authBodyHTML: authBodyHTML, authFootHTML: authFootHTML,
  openCloudChoiceSheet: openCloudChoiceSheet, openCloudAuth: openCloudAuth,
  sheetStack: function(){ return sheetStack; }, closeSheetEl: closeSheetEl, closeAllSheets: closeAllSheets,
  onClick: onClick, openSheet: openSheet, authCtx: function(){ return authCtx; },
  /* 로그인 · 가입 */
  cloudSubmit: cloudSubmit, cloudOnSignUp: cloudOnSignUp, cloudOnSignIn: cloudOnSignIn,
  cloudOnAuthFail: cloudOnAuthFail, cloudSignedIn: cloudSignedIn, cloudSignedOut: cloudLogout,
  cloudLogoutAsk: cloudLogoutAsk, cloudLogout: cloudLogout, cloudAuthEvent: cloudAuthEvent,
  cloudAfterSignIn: cloudAfterSignIn, cloudRestore: cloudRestore,
  /* 동기화 */
  cloudBoot: cloudBoot, cloudTouch: cloudTouch, cloudFlush: cloudFlush, cloudPush: cloudPush,
  cloudPull: cloudPull, cloudPullQuiet: cloudPullQuiet, cloudSyncNow: cloudSyncNow,
  cloudPlan: cloudPlan, cloudHydrate: cloudHydrate, cloudNormalizeState: cloudNormalizeState,
  cloudAbsorb: cloudAbsorb,
  cloudPrepareMigrate: cloudPrepareMigrate, cloudUploadNow: cloudUploadNow, cloudTakeServer: cloudTakeServer,
  cloudPayload: cloudPayload, cloudStateFromRows: cloudStateFromRows,
  cloudStamp: cloudStamp, cloudLocalStamp: cloudLocalStamp,
  cloudStatusText: cloudStatusText, cloudPhase: cloudPhase, cloudAgo: cloudAgo,
  CLOUD: function(){ return CLOUD; },
  resetCloud: function(){
    CLOUD.client = null; CLOUD.booted = false; CLOUD.libState = 'idle'; CLOUD.user = null;
    CLOUD.busy = false; CLOUD.pending = false; CLOUD.dirty = false; CLOUD.offerUpload = false;
    CLOUD.lastOk = 0; CLOUD.lastErr = ''; CLOUD.rev = 0; CLOUD.timer = null;
    CLOUD.applying = false; CLOUD.afterFor = ''; CLOUD.owner = '';
    authCtx = null;
  },
  /* 상태 */
  state: function(){ return state; }, setState: function(s){ state = s; },
  save: save, buildDemo: buildDemo, blankState: blankState, ui: function(){ return ui; },
  setObWaiting: function(v){ obWaiting = v; }, todayISO: todayISO, uid: uid,
  isSep: isSep, sepFee: sepFee, detectGolfTags: detectGolfTags, KEY: KEY,
  doc: document, fake: function(){ return FAKE; }
};
"""

CSSMAP = {'.input': rule('.input'), '.hint': rule('.hint'), '.authtab': rule('.authtab')}
SHIM = SHIM.replace('__CSSRULE__', json.dumps(CSSMAP))

ctx = quickjs.Context()
try:
    ctx.eval(SHIM + inner + EXPORT)
except Exception as e:
    print('앱 실행 오류:', e)
    sys.exit(1)

JS = r"""
var A = globalThis.__api, D = A.doc, F = A.fake(), C = A.CLOUD();
function EL(id){ return D.getElementById(id); }
var log = [], fails = [];
function ok(c, n, d){ if (c) log.push('PASS ' + n); else fails.push('FAIL ' + n + (d === undefined ? '' : '  <- ' + d)); }
function eq(a, b, n){ ok(a === b, n + (a === b ? '' : '  got=[' + a + '] want=[' + b + ']')); }
function has(s, t, n){ ok(String(s).indexOf(t) >= 0, n, 'missing: ' + t); }
function hasNot(s, t, n){ ok(String(s).indexOf(t) < 0, n, 'found: ' + t); }
function toastText(){ var e = EL('toast'); return e.innerHTML; }
function clearToast(){ EL('toast').innerHTML = ''; EL('toast').textContent = ''; }
function lastSheet(){ var r = EL('sheetRoot'); return r.children[r.children.length - 1]; }
function sheetTitle(w){ return w.children[0].querySelector('h3').textContent; }
function sheetPart(w, sel){ return w.children[0].querySelector(sel).innerHTML; }

/* 깨끗한 출발점: 데모 기록 + 로그인 안 됨 */
function fresh(){
  F.reset();
  A.closeAllSheets();
  A.resetCloud();
  localStorage.removeItem('golfLessonApp.cloud');
  A.setObWaiting(false);
  var demo = A.buildDemo();
  if (!demo.renewalLog) demo.renewalLog = [];
  if (!demo.cancelLog) demo.cancelLog = [];
  A.setState(demo);
  EL('onboard').hidden = true;     /* 온보딩은 첫 실행에서만 (앱과 같은 기본값) */
  A.cloudBoot();          /* 앱을 켠 것과 같은 상태 (로그인 안 됨) */
  A.ui().tab = 'settings'; A.ui().date = A.todayISO();
  navigator.onLine = true;
  clearToast();
}
function session(email){
  return { access_token:'t', user: { id:'u-1', email: email || 'pro@example.com' } };
}
function signedIn(email){
  A.cloudBoot();
  A.cloudSignedIn(session(email));
  return C;
}
/* 서버 행 모양 (schema.sql 의 컬럼 이름 그대로) */
function dbRows(){
  return {
    profiles: [{ id:'u-1', pro_name:'이시훈', pro_title:'KPGA 투어프로', academy:'그린필드',
      theme:'black', lesson_start_hour:7, lesson_end_hour:22,
      calendar_sync_enabled:true, calendar_target:'apple' }],
    members: [
      { id:'m-1', name:'김도현', phone:'010-1111-2222', gender:'male', region:'분당', level:'중급',
        memo:'드라이버', is_visitor:false, from_separate:false, since:'2026-01-05',
        pass_history:[{ date:'2026-10-01', sessions:8 }] },
      { id:'m-2', name:'박서연', phone:'', gender:'female', region:'판교', level:'초급', memo:'',
        is_visitor:false, from_separate:false, since:'2026-03-01', pass_history:[] }
    ],
    passes: [
      { id:'p-1', member_id:'m-1', duration_min:55, total_count:8, remaining_count:3,
        total_price:800000, status:'active', started_at:'2026-10-01', expires_at:'2027-03-01',
        note:'', renewal:false }
    ],
    lessons: [
      { id:'l-1', member_id:'m-1', pass_id:'p-1', lesson_date:'2026-11-24', start_time:'07:00:00',
        duration_min:55, kind:'regular', separate_price:0, status:'done', memo:'드라이버 교정',
        location:'분당 실내연습장', guest_name:'', deducted:true, charged:false,
        settled_at:'2026-11-24T21:00:00+09:00' },
      { id:'l-2', member_id:'m-1', pass_id:'p-1', lesson_date:'2026-11-25', start_time:'10:30:00',
        duration_min:55, kind:'regular', separate_price:0, status:'noshow', memo:'',
        location:'', guest_name:'', deducted:true, charged:false, settled_at:null },
      { id:'l-3', member_id:null, pass_id:null, lesson_date:'2026-11-20', start_time:'09:30:00',
        duration_min:180, kind:'field', separate_price:450000, status:'done', memo:'',
        location:'', guest_name:'한빛상사 팀', deducted:false, charged:true, settled_at:null }
    ],
    lesson_charts: [
      { id:'c-1', member_id:'m-1', lesson_id:'l-1', chart_date:'2026-11-24',
        content:'드라이버 백스윙 톱 교정', tags:['드라이버'], source:'voice',
        created_at:'2026-11-24T20:10:00+09:00' }
    ],
    cancel_logs: [
      { id:'x-1', member_id:'m-2', lesson_date:'2026-11-10', reason:'excused_cancel',
        created_at:'2026-11-10T20:00:00+09:00' }
    ],
    settlements: [
      { id:'s-1', settle_date:'2026-11-24', settled_at:'2026-11-24T21:05:00+09:00',
        counts:{ done:1, no_show:0 }, deducted:1 }
    ],
    renewal_logs: [
      { id:'r-1', member_id:'m-1', pass_id:'p-1', kind:'renewal', renewed_on:'2026-10-01',
        total_count:8, duration_min:55, amount:800000, created_at:'2026-10-01T09:00:00+09:00' }
    ],
    lesson_templates: [
      { id:'t-2', name:'55분 정규', duration_min:55, total_count:8, price:800000, sort_order:1 },
      { id:'t-1', name:'25분 집중', duration_min:25, total_count:10, price:600000, sort_order:0 }
    ]
  };
}
/* import_prototype_json 이 하는 컬럼 변환을 그대로 흉내 (왕복 검사용) */
function payloadToRows(p){
  var memMap = {}, pkgMap = {}, k = 0;
  var rows = { profiles: [{ id:'u-1', pro_name:p.pro.name, pro_title:p.pro.title, academy:p.pro.academy,
      theme:p.theme, lesson_start_hour:Math.floor(p.hours.fromMin/60), lesson_end_hour:Math.floor(p.hours.toMin/60),
      calendar_sync_enabled:p.calendarSync.enabled, calendar_target:p.calendarSync.target }],
    members:[], passes:[], lessons:[], lesson_charts:[], cancel_logs:[], settlements:[], renewal_logs:[], lesson_templates:[] };
  p.members.forEach(function(m){ var id = 'M' + (++k); memMap[m.id] = id;
    rows.members.push({ id:id, name:m.name, phone:m.phone, gender:m.gender, region:m.region, level:m.level,
      memo:m.memo, is_visitor:m.isVisitor, from_separate:m.fromSeparate, since:m.since, pass_history:m.passHistory }); });
  p.packages.forEach(function(x){ if (!memMap[x.memberId]) return; var id = 'P' + (++k); pkgMap[x.id] = id;
    rows.passes.push({ id:id, member_id:memMap[x.memberId], duration_min:x.durationMinutes,
      total_count:x.totalSessions, remaining_count:x.remainingSessions, total_price:x.price,
      status: x.remainingSessions > 0 ? 'active' : 'completed', started_at:x.startDate,
      expires_at:x.expiryDate || null, note:x.note, renewal:x.renewal }); });
  p.sessions.forEach(function(s){ var sep = s.separatePay === true;
    var mid = memMap[s.memberId] || null;
    if (!mid && !sep && !s.guestName) return;
    var st = s.status === 'completed' ? 'done' : s.status === 'no_show' ? 'noshow' : s.status;
    rows.lessons.push({ id:'L' + (++k), member_id:mid, pass_id: sep ? null : (pkgMap[s.packageId] || null),
      lesson_date:s.date, start_time:s.startTime + ':00', duration_min:s.durationMinutes,
      kind: sep ? s.lessonKind : 'regular', separate_price: sep ? s.fee : 0, status:st,
      memo:s.memo, location:s.location, guest_name:s.guestName || '',
      deducted: sep ? false : (st === 'done' || st === 'same_day_cancel' || st === 'noshow'),
      charged: sep ? (st === 'done' || st === 'same_day_cancel' || st === 'noshow') : false,
      settled_at: s.settledAt || null }); });
  p.notes.forEach(function(n){ if (!memMap[n.memberId]) return;
    rows.lesson_charts.push({ id:'C' + (++k), member_id:memMap[n.memberId], lesson_id:null,
      chart_date:n.date, content:n.text, tags:n.tags, source:n.source, created_at:n.createdAt }); });
  p.cancelLog.forEach(function(c){ rows.cancel_logs.push({ id:'X' + (++k), member_id:memMap[c.memberId] || null,
    lesson_date:c.date, reason:'excused_cancel', created_at:c.at || c.date + 'T00:00:00+00:00' }); });
  p.settlements.forEach(function(s){ rows.settlements.push({ id:'S' + (++k), settle_date:s.date,
    settled_at:s.settledAt, counts:s.counts, deducted:s.deducted }); });
  p.renewalLog.forEach(function(r){ rows.renewal_logs.push({ id:'R' + (++k), member_id:memMap[r.memberId] || null,
    pass_id:pkgMap[r.pkgId] || null, kind:r.kind, renewed_on:r.date, total_count:r.sessions,
    duration_min:r.durationMinutes, amount:r.amount, created_at:r.at }); });
  p.templates.forEach(function(t, i){ rows.lesson_templates.push({ id:'T' + (++k), name:t.name,
    duration_min:t.durationMinutes, total_count:t.sessions, price:t.price, sort_order:i }); });
  return rows;
}

/* ══════════ A. 설정 탭 계정 카드 ══════════ */
fresh();
var vs = A.viewSettings();
has(vs, '내 계정 · 클라우드 동기화', 'A-1 설정에 계정 카드 제목');
ok(vs.indexOf('내 계정 · 클라우드 동기화') < vs.indexOf('화면 테마'),
   'A-2 계정 카드가 설정 탭 맨 위', vs.slice(0, 120));
has(vs, 'data-act="cloud-auth"', 'A-3 로그인 / 회원가입 버튼');
has(vs, '로그인 / 회원가입', 'A-4 버튼 글자');
has(vs, '카드 정보는 받지 않아요', 'A-5 안내 문구');
has(vs, '계정 없이 지금처럼 이 기기에만 써도', 'A-6 계정 없이 쓰는 길 안내');
has(vs, 'data-act="export-data"', 'A-7 기존 데이터 기능 그대로');
/* 16px — 사파리 확대 방지 */
ok(CSSRULE['.input'].indexOf('font-size:16px') >= 0, 'A-8 입력칸 16px 규칙', CSSRULE['.input'])

/* ══════════ B. 로그인 · 회원가입 시트 ══════════ */
fresh();
var before = A.sheetStack().length;
A.openAuthSheet('login');
eq(A.sheetStack().length - before, 1, 'B-1 시트가 하나 열림');
var sh = lastSheet(), bd = sheetPart(sh, '.sb'), ft = sheetPart(sh, '.sf');
eq(sheetTitle(sh), '로그인', 'B-2 로그인 제목');
has(bd, 'id="auEmail"', 'B-3 이메일 칸');
has(bd, 'type="email"', 'B-4 이메일 타입');
has(bd, 'inputmode="email"', 'B-5 이메일 키보드');
has(bd, 'id="auPw"', 'B-6 비밀번호 칸');
has(bd, 'type="password"', 'B-7 비밀번호 가림');
has(bd, 'class="input"', 'B-8 16px 입력 클래스');
hasNot(bd, 'id="auName"', 'B-9 로그인에는 프로 이름 없음');
has(bd, 'autocomplete="email"', 'B-10 이메일 자동완성');
has(bd, 'autocomplete="current-password"', 'B-11 로그인 비밀번호 자동완성');
has(ft, 'data-act="cloud-submit"', 'B-12 제출 버튼');
eq(lastSheet().children[0].querySelector('.sf').style.display, '', 'B-12b 제출 칸이 보임');
has(ft, '로그인', 'B-13 제출 버튼 글자');
hasNot(bd, 'font-size', 'B-14 입력칸에 임의 글자 크기 없음');
/* 회원가입 탭 */
A.onClick({ target:{ closest: function(){ return { getAttribute:function(n){ return n === 'data-act' ? 'cloud-mode' : (n === 'data-v' ? 'signup' : null); }, closest:function(){ return null; } }; } } });
bd = sheetPart(lastSheet(), '.sb');
has(bd, 'id="auName"', 'B-15 회원가입에 프로 이름 칸');
has(bd, 'autocomplete="new-password"', 'B-16 가입 비밀번호 자동완성');
has(bd, '인증 메일', 'B-17 인증 메일 안내');
eq(A.authCtx().mode, 'signup', 'B-18 회원가입 모드로 바뀜');
ok(sheetPart(lastSheet(), '.sb').indexOf('id="auMsg"') >= 0, 'B-18b 오류·안내 자리(#auMsg)');
/* 입력 검사 — 서버를 부르지 않음 */
A.cloudSubmit();
has(EL('auMsg').innerHTML, '이메일 주소를 다시 확인', 'B-19 빈 이메일 거절');
eq(F.signUpCalls.length, 0, 'B-20 빈 이메일이면 호출 없음');
EL('auEmail').value = 'pro@example.com'; EL('auPw').value = '123'; EL('auName').value = '이시훈';
A.cloudSubmit();
has(EL('auMsg').innerHTML, '6자 이상', 'B-21 짧은 비밀번호 거절');
eq(F.signUpCalls.length, 0, 'B-22 짧은 비밀번호면 호출 없음');
EL('auPw').value = 'secret123'; EL('auName').value = '   ';
A.cloudSubmit();
has(EL('auMsg').innerHTML, '프로 이름', 'B-23 이름 없는 가입 거절');
eq(F.signUpCalls.length, 0, 'B-24 이름 없으면 호출 없음');
EL('auName').value = '이시훈';
/* 정상 가입 → 인증 메일 안내(세션 없음) */
F.signUpResult = { data: { user: { email:'pro@example.com' }, session: null }, error: null };
A.cloudSubmit();
eq(F.signUpCalls.length, 1, 'B-25 가입 호출 1회');
eq(F.signUpCalls[0].email, 'pro@example.com', 'B-26 이메일 전달');
eq(F.signUpCalls[0].options.data.pro_name, '이시훈', 'B-27 프로 이름을 메타데이터로');
has(String(F.signUpCalls[0].options.emailRedirectTo), '/Golf--lesson-app/', 'B-28 인증 링크가 이 앱으로 돌아옴');
has(sheetPart(lastSheet(), '.sb'), '인증 메일을 보냈어요', 'B-29 인증 메일 안내 표시');
has(sheetPart(lastSheet(), '.sb'), 'pro@example.com', 'B-30 받을 주소 표시');
has(sheetPart(lastSheet(), '.sb'), '스팸함', 'B-31 메일이 없을 때 안내');
eq(A.authCtx().mode, 'login', 'B-32 인증 뒤엔 로그인 칸');
ok(!C.user, 'B-33 아직 로그인 아님');
eq(EL('auEmail').value, 'pro@example.com', 'B-34 이메일 남아 있음');

/* ══════════ C. 로그인 성공 · 실패 문구 ══════════ */
fresh();
A.openAuthSheet('login');
EL('auEmail').value = 'pro@example.com'; EL('auPw').value = 'secret123';
F.signInResult = { data: null, error: { code:'email_not_confirmed', message:'Email not confirmed' } };
A.cloudSubmit();
has(EL('auMsg').innerHTML, '이메일 인증이 아직이에요', 'C-1 인증 전 로그인 안내');
ok(!C.user, 'C-2 실패하면 로그인 아님');
F.signInResult = { data: null, error: { code:'invalid_credentials', message:'Invalid login credentials' } };
A.cloudSubmit();
has(EL('auMsg').innerHTML, '이메일이나 비밀번호가 맞지 않아요', 'C-3 비밀번호 오류 문구');
F.signInResult = { data: { session: session('pro@example.com') }, error: null };
F.tables = dbRows();
A.cloudSubmit();
ok(!!C.user, 'C-4 로그인됨');
eq(C.user.email, 'pro@example.com', 'C-5 이메일 보관');
has(sheetTitle(lastSheet()), '어느 기록으로', 'C-6 로그인하면 서버 기록과 맞출지 물음');
has(String(toastText()), '로그인했어요', 'C-7 로그인 토스트');
ok(F.selectCalls.length > 0, 'C-8 로그인 직후 서버 기록 확인');
/* 이 기기(데모 5명)와 서버(2명) 기록이 달라 자동으로 덮어쓰지 않음 */
eq(A.state().members.length, 5, 'C-9 로그인만으로 기기 기록을 지우지 않음');
A.onClick({ target:{ closest: function(){ return { getAttribute:function(){ return 'cloud-take-server'; }, closest:function(){ return lastSheet(); } }; } } });
eq(A.state().members.length, 2, 'C-10 서버 기록을 고르면 그 기록으로');

/* ══════════ D. 기기 상태 → 백업 JSON ══════════ */
fresh();
var st0 = A.state();
var pay = A.cloudPayload(st0);
eq(pay.members.length, st0.members.length, 'D-1 회원 수 그대로');
eq(pay.packages.length, st0.packages.length, 'D-2 수강권 수 그대로');
ok(pay.sessions.length > 0, 'D-3 레슨 포함', pay.sessions.length);
eq(pay.pro.name, st0.pro.name, 'D-4 프로 이름');
eq(pay.theme, 'green', 'D-5 테마');
ok(pay.hours.fromMin > 0 && pay.hours.toMin > pay.hours.fromMin, 'D-6 레슨 시간 범위', JSON.stringify(pay.hours));
eq(typeof pay.calendarSync.enabled, 'boolean', 'D-7 캘린더 연동');
var m0 = pay.members[0];
ok(m0.id && m0.name && m0.since, 'D-8 회원 필수 칸', JSON.stringify(m0));
ok(Object.prototype.toString.call(m0.passHistory) === '[object Array]', 'D-9 재등록 이력 배열');
var s0 = pay.sessions[0];
ok(/^\d{4}-\d{2}-\d{2}$/.test(s0.date), 'D-10 레슨 날짜', s0.date);
ok(/^\d{2}:\d{2}$/.test(s0.startTime), 'D-11 시작 시간 hh:mm', s0.startTime);
ok(['scheduled','completed','same_day_cancel','no_show','makeup','excused_cancel'].indexOf(s0.status) >= 0,
   'D-12 앱 상태 이름 그대로', s0.status);
hasNot(JSON.stringify(pay.sessions.filter(function(x){ return !x.separatePay; })), 'separatePay',
   'D-13 일반 레슨에는 별도결제 표시 없음');
/* 별도 결제 레슨 */
var sep = pay.sessions.filter(function(x){ return x.separatePay === true; })[0];
ok(!!sep, 'D-14 별도 결제 레슨 포함');
if (sep) {
  eq(sep.separatePay, true, 'D-15 별도 결제 표시');
  ok(sep.lessonKind === 'field' || sep.lessonKind === 'shortgame' || sep.lessonKind === 'onepoint',
     'D-16 별도 결제 종류', sep.lessonKind);
  var guestSep = pay.sessions.filter(function(x){ return x.separatePay === true && x.guestName; })[0];
  ok(guestSep && guestSep.guestName, 'D-17 비회원 이름', guestSep && guestSep.guestName);
  ok(sep.fee > 0, 'D-18 별도 결제 금액', sep.fee);
}
/* 정산 시각은 오프셋을 붙여 보낸다 (기기 시각이 그대로 돌아오게) */
var withSettle = pay.sessions.filter(function(x){ return x.settledAt; })[0];
ok(withSettle && /T\d{2}:\d{2}:\d{2}[+-]\d{2}:\d{2}$/.test(withSettle.settledAt),
   'D-19 정산 시각에 시간대 표기', withSettle && withSettle.settledAt);
/* 차트 · 정산 · 템플릿 */
var nBefore = A.state().notes.length, setBefore = A.state().settlements.length;
A.state().notes.push({ id:'n1', memberId:st0.members[0].id, date:A.todayISO(), text:'드라이버 백스윙 교정',
  createdAt:A.todayISO() + 'T20:00:00', source:'voice', tags:['드라이버'] });
A.state().settlements.push({ date:A.todayISO(), settledAt:A.todayISO() + 'T21:00:00', counts:{ done:2 }, deducted:2 });
A.state().cancelLog.push({ date:A.todayISO(), memberId:st0.members[1].id, at:A.todayISO() + 'T09:00:00' });
A.state().renewalLog.push({ memberId:st0.members[0].id, name:st0.members[0].name, kind:'renewal',
  pkgId:st0.packages[0].id, date:A.todayISO(), at:A.todayISO() + 'T10:00:00', sessions:8, durationMinutes:55, amount:800000 });
pay = A.cloudPayload(A.state());
eq(pay.notes.length, nBefore + 1, 'D-20 차트 포함');
var voiceNote = pay.notes.filter(function(n){ return n.id === 'n1'; })[0];
eq(voiceNote.source, 'voice', 'D-21 차트 음성 표시 유지');
eq(voiceNote.tags[0], '드라이버', 'D-22 차트 태그');
eq(pay.settlements.length, setBefore + 1, 'D-23 마감 정산 포함');
eq(pay.cancelLog.length, 1, 'D-24 일반취소 기록 포함');
eq(pay.renewalLog.length, 1, 'D-25 재등록 기록 포함');
eq(pay.templates.length, A.state().templates.length, 'D-26 상품 템플릿 포함');

/* 범위를 벗어난 값도 서버 표의 검사 범위 안으로 (한 건 때문에 동기화가 멈추지 않게) */
var odd = A.buildDemo();
odd.packages[0].durationMinutes = 3;
odd.packages[0].totalSessions = 5000;
odd.sessions[0].durationMinutes = 2;
odd.sessions[1].durationMinutes = 900;
var oddPay = A.cloudPayload(odd);
ok(oddPay.packages[0].durationMinutes >= 10 && oddPay.packages[0].durationMinutes <= 600,
   'D-27 수강권 소요시간 범위 보정', oddPay.packages[0].durationMinutes);
ok(oddPay.packages[0].totalSessions === 1000, 'D-28 총 횟수 상한 보정', oddPay.packages[0].totalSessions);
ok(oddPay.sessions[0].durationMinutes === 5, 'D-29 레슨 소요시간 하한 보정', oddPay.sessions[0].durationMinutes);
ok(oddPay.sessions[1].durationMinutes === 600, 'D-30 레슨 소요시간 상한 보정', oddPay.sessions[1].durationMinutes);

/* ══════════ E. 서버 행 → 기기 상태 ══════════ */
var remote = A.cloudStateFromRows(dbRows());
eq(remote.pro.name, '이시훈', 'E-1 프로 이름');
eq(remote.theme, 'black', 'E-2 테마');
eq(remote.hours.fromMin, 420, 'E-3 시작 시간(분)');
eq(remote.hours.toMin, 1320, 'E-4 종료 시간(분)');
eq(remote.calendarSync.enabled, true, 'E-5 캘린더 연동');
eq(remote.calendarSync.target, 'apple', 'E-6 캘린더 대상');
eq(remote.members.length, 2, 'E-7 회원 수');
eq(remote.members[0].since, '2026-01-05', 'E-8 등록일');
eq(remote.members[0].passHistory.length, 1, 'E-9 재등록 이력');
eq(remote.packages.length, 1, 'E-10 수강권 수');
eq(remote.packages[0].remainingSessions, 3, 'E-11 잔여 횟수');
eq(remote.packages[0].price, 800000, 'E-12 결제 금액');
eq(remote.sessions.length, 3, 'E-13 레슨 수');
var done = remote.sessions.filter(function(x){ return x.id === 'l-1'; })[0];
eq(done.status, 'completed', 'E-14 done → 완료');
eq(done.startTime, '07:00', 'E-15 시간 hh:mm');
eq(done.deducted, true, 'E-16 차감 표시');
has(done.settledAt, '2026-11-24T', 'E-17 정산 시각 복원');
var noShow = remote.sessions.filter(function(x){ return x.id === 'l-2'; })[0];
eq(noShow.status, 'no_show', 'E-18 noshow → 노쇼');
var field = remote.sessions.filter(function(x){ return x.id === 'l-3'; })[0];
eq(field.lessonKind, 'field', 'E-19 필드 레슨');
eq(field.fee, 450000, 'E-20 별도 결제 금액');
eq(field.charged, true, 'E-21 별도 수입 확정');
eq(field.guestName, '한빛상사 팀', 'E-22 비회원 이름');
eq(remote.notes.length, 1, 'E-23 차트 수');
eq(remote.notes[0].text, '드라이버 백스윙 톱 교정', 'E-24 차트 내용');
has(remote.notes[0].createdAt, '2026-11-24T', 'E-25 차트 작성 시각');
eq(remote.settlements.length, 1, 'E-26 정산 수');
eq(remote.settlements[0].counts.done, 1, 'E-27 정산 건수');
eq(remote.renewalLog.length, 1, 'E-28 재등록 수');
eq(remote.renewalLog[0].name, '김도현', 'E-29 재등록 회원 이름');
eq(remote.cancelLog.length, 1, 'E-30 일반취소 수');
eq(remote.templates.length, 2, 'E-31 템플릿 수');
eq(remote.templates[0].name, '25분 집중', 'E-32 템플릿 정렬 순서');
eq(remote.templates[0].sessions, 10, 'E-33 템플릿 횟수');

/* ══════════ F. 왕복 무손실 ══════════ */
fresh();
var local = A.state();
var back = A.cloudStateFromRows(payloadToRows(A.cloudPayload(local)));
eq(back.members.length, local.members.length, 'F-1 회원 수 왕복');
eq(back.packages.length, local.packages.length, 'F-2 수강권 수 왕복');
eq(back.sessions.length, local.sessions.length, 'F-3 레슨 수 왕복');
var remSum = function(list){ var s = 0; list.forEach(function(p){ s += p.remainingSessions; }); return s; };
eq(remSum(back.packages), remSum(local.packages), 'F-4 잔여 횟수 합 왕복');
var stCount = function(list, k){ var c = 0; list.forEach(function(x){ if (x.status === k) c++; }); return c; };
eq(stCount(back.sessions, 'completed'), stCount(local.sessions, 'completed'), 'F-5 완료 건수 왕복');
eq(stCount(back.sessions, 'no_show'), stCount(local.sessions, 'no_show'), 'F-6 노쇼 건수 왕복');
eq(stCount(back.sessions, 'scheduled'), stCount(local.sessions, 'scheduled'), 'F-7 예정 건수 왕복');
var sepBack = back.sessions.filter(function(x){ return x.separatePay; });
var sepLoc = local.sessions.filter(function(x){ return A.isSep(x); });
eq(sepBack.length, sepLoc.length, 'F-8 별도 결제 건수 왕복');
eq(sepBack[0].fee, A.sepFee(sepLoc[0]), 'F-9 별도 결제 금액 왕복');
eq(back.pro.name, local.pro.name, 'F-10 프로 이름 왕복');
eq(back.theme, local.theme === 'black' ? 'black' : 'green', 'F-11 테마 왕복');

/* ══════════ G. 동기화 엔진 ══════════ */
fresh();
signedIn();
eq(F.rpcCalls.length, 0, 'G-1 로그인 직후엔 저절로 올리지 않음');
A.cloudFlush();
eq(F.rpcCalls.length, 0, 'G-1b 바뀐 게 없으면 올릴 것도 없음');
A.save();
ok(C.pending, 'G-2 저장하면 서버에 올릴 표시');
ok(C.timer !== null, 'G-3 바로 올리지 않고 잠시 모음');
A.cloudFlush();
eq(F.rpcCalls.length, 1, 'G-4 동기화 한 번 호출');
eq(F.rpcCalls[0].name, 'import_prototype_json', 'G-5 이관 함수 호출');
eq(F.rpcCalls[0].args.p_mode, 'replace', 'G-6 계속 동기화는 replace');
ok(F.rpcCalls[0].args.payload.members.length > 0, 'G-7 회원 담김');
ok(!C.pending, 'G-8 성공하면 대기 해제');
ok(C.lastOk > 0, 'G-9 마지막 성공 시각 기록');
/* 연달아 저장해도 한 번만 */
A.save(); A.save(); A.save();
A.cloudFlush();
eq(F.rpcCalls.length, 2, 'G-10 몰아서 한 번');
/* 동기화 중에 또 저장 → 끝난 뒤 한 번 더 */
A.save();
C.busy = true;
A.cloudPush('replace');
C.busy = false;
ok(C.dirty, 'G-11 진행 중이면 다시 올릴 표시만');
/* 실패 */
F.rpcCalls = [];
F.rpcResult = { data: null, error: { message: 'boom' } };
A.cloudPush('replace');
ok(C.pending, 'G-12 실패하면 대기 유지');
eq(C.lastErr, 'boom', 'G-13 실패 이유 보관');
has(A.cloudStatusText(), '오프라인 대기', 'G-14 대기 문구');
/* 성공하면 풀림 */
F.rpcResult = { data: { ok:true }, error: null };
A.cloudPush('replace');
ok(!C.pending, 'G-15 다시 성공하면 해제');
has(A.cloudStatusText(), '동기화됨', 'G-16 완료 문구');
/* 오프라인 */
navigator.onLine = false;
F.rpcCalls = [];
A.save();
A.cloudFlush();
eq(F.rpcCalls.length, 0, 'G-17 오프라인이면 서버를 부르지 않음');
ok(C.pending, 'G-18 오프라인 대기로 남김');
navigator.onLine = true;
/* 기기에 남는 표시 */
ok(String(localStorage.getItem('golfLessonApp.cloud')).indexOf('"pending":true') >= 0,
   'G-19 다시 열어도 대기 상태를 앎');
/* 서버에서 받기 — 9개 표 전부 */
F.reset(); signedIn(); F.tables = dbRows();
var got = null;
A.cloudPull(function(rows){ got = rows; });
eq(F.selectCalls.length, 9, 'G-20 표 9개를 모두 읽음');
ok(got && got.members.length === 2, 'G-21 받은 행');
/* 표 판단 */
eq(A.cloudPlan({ members:[] }, { members:[{}] }), 'upload', 'G-22 로컬만 → 올리기');
eq(A.cloudPlan({ members:[{}] }, { members:[] }), 'pull', 'G-23 서버만 → 받기');
eq(A.cloudPlan({ members:[{}] }, { members:[{}] }), 'choose', 'G-24 둘 다 → 고르기');
eq(A.cloudPlan({ members:[] }, { members:[] }), 'none', 'G-25 둘 다 없음');
/* 서버 기록으로 화면 맞추기 */
F.tables = dbRows();
A.cloudPull(function(rows){ A.cloudHydrate(rows, false); });
eq(A.state().members.length, 2, 'G-26 서버 기록으로 바뀜');
eq(A.state().members[0].name, '김도현', 'G-27 회원 이름');
eq(A.state().theme, 'black', 'G-28 테마도 서버 값으로');
/* 수동 동기화 — 대기 없으면 서버 확인 */
C.pending = false;
F.selectCalls = [];
A.cloudSyncNow();
ok(F.selectCalls.length === 9, 'G-29 지금 동기화는 서버를 먼저 확인', F.selectCalls.length);
/* 수동 동기화 — 대기 있으면 올리기 */
F.rpcCalls = [];
A.save();
A.cloudSyncNow();
eq(F.rpcCalls.length, 1, 'G-30 대기가 있으면 올리기');

/* ══════════ H. 이관 · 덮어쓰기 안전 ══════════ */
/* 서버가 비었는데 이 기기에 기록이 있으면 지우지 않는다 */
fresh(); signedIn();
F.tables = {};   /* 서버 0건 */
var beforeCount = A.state().members.length;
A.closeAllSheets();
A.cloudPullQuiet();
eq(A.state().members.length, beforeCount, 'H-1 서버가 비었다고 기기 기록을 지우지 않음');
ok(C.offerUpload, 'H-2 올리기 안내 표시');
has(A.cloudCardHTML(), '아직 서버에 없어요', 'H-3 카드에 백업 안내');
/* 양쪽에 기록이 있으면 자동으로 덮어쓰지 않는다 */
fresh(); signedIn();
F.tables = dbRows();
A.closeAllSheets();
ok(A.state().members.length > 2, 'H-4a 시작은 기기 기록(데모)');
A.cloudPullQuiet();
eq(A.state().members.length, 2, 'H-4b 앱을 열면 서버 기록을 따라감(다른 기기와 같아짐)');
eq(A.state().members[0].name, '김도현', 'H-4c 서버 회원 이름');
/* 로그인 직후 — 서버 비었으면 올리기 선택 시트 */
fresh();
F.tables = {};
A.cloudSignedIn(session('me@example.com'));
A.cloudAfterSignIn();
var ws = lastSheet();
has(sheetTitle(ws), '올릴까요', 'H-5 이 기기 기록 올리기 제안');
has(sheetPart(ws, '.sf'), 'data-act="cloud-upload"', 'H-6 한 번에 올리기 버튼');
has(sheetPart(ws, '.sb'), '이 기기 회원', 'H-7 기기 건수 보여줌');
has(sheetPart(ws, '.sb'), '서버 회원', 'H-8 서버 건수 보여줌');
/* 올리기 = merge */
F.rpcCalls = [];
A.onClick({ target:{ closest: function(){ return { getAttribute:function(){ return 'cloud-upload'; }, closest:function(){ return lastSheet(); } }; } } });
eq(F.rpcCalls.length, 1, 'H-9 올리기 실행');
eq(F.rpcCalls[0].args.p_mode, 'merge', 'H-10 이관은 merge');
has(String(toastText()), '서버에 백업했어요', 'H-11 백업 토스트');
/* 로그인 직후 — 서버에 기록이 있으면 고르기 */
fresh();
F.tables = dbRows();
A.cloudSignedIn(session('me@example.com'));
A.cloudAfterSignIn();
has(sheetTitle(lastSheet()), '어느 기록으로', 'H-12 어느 기록으로 맞출지 물음');
has(sheetPart(lastSheet(), '.sf'), 'cloud-take-server', 'H-13 서버 기록 가져오기 버튼');
F.selectCalls = [];
A.onClick({ target:{ closest: function(){ return { getAttribute:function(){ return 'cloud-take-server'; }, closest:function(){ return lastSheet(); } }; } } });
ok(F.selectCalls.length === 9, 'H-14 서버 기록을 읽어 옴');
eq(A.state().members.length, 2, 'H-15 서버 기록으로 바뀜');
/* 이관 버튼(설정) */
fresh(); signedIn();
F.tables = dbRows(); F.selectCalls = [];
A.cloudPrepareMigrate();
eq(F.selectCalls.length, 9, 'H-16 이관 전에 서버 확인');
has(sheetTitle(lastSheet()), '어느 기록으로', 'H-17 이관 확인 시트');

/* 다른 계정으로 로그인 — 남의 기기 기록을 내 계정에 올리지 않게 경고 */
fresh();
A.cloudSignedIn(session('first@example.com'));
A.save();
A.cloudFlush();                     /* first 계정으로 올림 → 기기 기록 주인 = first */
eq(C.owner, 'first@example.com', 'H-18 올린 계정을 기기에 기록');
A.cloudLogout();
A.cloudSignedIn(session('second@example.com'));
F.tables = dbRows();
A.cloudAfterSignIn();
var mm = lastSheet();
has(sheetPart(mm, '.sb'), 'first@example.com 계정 때', 'H-19 다른 계정이면 경고');
var mfoot = sheetPart(mm, '.sf');
ok(mfoot.indexOf('cloud-take-server') < mfoot.indexOf('cloud-upload'), 'H-20 서버 기록 가져오기가 먼저');

/* 다른 계정 기록은 저절로 올라가지 않는다 (시트에서 고른 뒤에만) */
A.closeAllSheets();
F.rpcCalls = [];
A.save();
eq(F.rpcCalls.length, 0, 'H-26a 다른 계정 기록은 서버로 안 올림');
ok(!C.pending, 'H-26b 대기 표시도 만들지 않음');
has(A.cloudStatusText(), '계정 확인 필요', 'H-26c 카드 상태 문구');
has(A.cloudCardHTML(), '계정 때 만든 것이에요', 'H-26d 카드 안내');
A.cloudUploadNow();                      /* 이 기기 기록을 지금 계정 것으로 올리기 */
eq(F.rpcCalls.length, 1, 'H-27a 올리기 버튼이면 올라감');
eq(F.rpcCalls[0].args.p_mode, 'merge', 'H-27b 이관은 merge');
eq(C.owner, 'second@example.com', 'H-27c 이제 이 계정 기록');
ok(!A.CLOUD().owner || !(A.CLOUD().owner === 'first@example.com'), 'H-27d 이전 계정 표시 해제');
A.save();
A.cloudFlush();
ok(F.rpcCalls.length >= 2, 'H-28 확인 뒤에는 정상 동기화');

/* 서버 연결 파일(CDN)을 못 받은 상태 — 앱은 그대로, 계정만 안내 */
fresh();
A.resetCloud();
window.supabase = undefined;         /* CDN 을 못 받은 것과 같은 상태 */
A.cloudBoot();
has(A.cloudCardHTML(), '지금은 서버에 연결하지 못했어요', 'H-21 연결 파일이 없으면 카드에 안내');
A.openAuthSheet('login');
EL('auEmail').value = 'pro@example.com'; EL('auPw').value = 'secret123';
A.cloudSubmit();
has(EL('auMsg').innerHTML, '연결할 수 없어요', 'H-22 연결 없이 제출하면 안내만');
ok(!C.user, 'H-23 로그인되지 않음');
A.closeAuthSheet();
/* 오프라인이어도 저장·화면은 그대로 */
navigator.onLine = false;
var beforeLocal = A.state().members.length;
A.state().members.push({ id:'m-off', name:'오프라인회원', since: A.todayISO(), passHistory:[] });
A.save();
eq(A.state().members.length, beforeLocal + 1, 'H-24 오프라인에서도 기기 기록은 저장');
eq(JSON.parse(localStorage.getItem(A.KEY)).members.length, beforeLocal + 1, 'H-25 localStorage 에 바로 저장');
navigator.onLine = true;
window.supabase = { createClient: function(){ return fakeClient(); } };   /* 연결 파일이 돌아온 상태 */

/* ══════════ I. 계정 해제 · 정적 무결성 ══════════ */
/* 로그아웃 — 기기 기록은 그대로 */
fresh(); signedIn('pro@example.com');
var keepCount = A.state().members.length;
A.cloudLogout();
ok(!C.user, 'I-1 로그아웃됨');
eq(F.signOutCalls, 1, 'I-2 세션 정리 호출');
eq(A.state().members.length, keepCount, 'I-3 기기 기록은 남음');
has(A.cloudCardHTML(), '로그인 / 회원가입', 'I-4 카드가 로그인 전으로');
/* 로그아웃 확인 시트 */
fresh(); signedIn();
A.cloudLogoutAsk();
has(sheetTitle(lastSheet()), '로그아웃', 'I-5 로그아웃 확인');
has(sheetPart(lastSheet(), '.sb'), '서버에 백업된 기록은 그대로', 'I-6 안내 문구');
/* 세션 복원 — 대기 중이면 먼저 올림 */
fresh();
A.resetCloud();
F.sessionResult = session('pro@example.com');
F.rpcCalls = [];
localStorage.setItem('golfLessonApp.cloud', JSON.stringify({ pending:true, lastOk:0 }));
A.cloudBoot();
eq(F.rpcCalls.length, 1, 'I-7 앱을 다시 열면 대기분을 먼저 올림');
/* 인증 링크로 돌아온 경우 */
fresh();
A.cloudAuthEvent('SIGNED_IN', session('new@example.com'));
ok(!!C.user, 'I-8 인증 링크 복귀로 로그인');
/* ── 결과 ── */
globalThis.__RESULT = JSON.stringify({ log: log, fails: fails });
"""

ctx.eval(JS)
res = json.loads(ctx.eval('__RESULT'))

# ── 정적 검사 (파일 글자 그대로) ────────────────────────────
def sok(name, cond, detail=''):
    (res['log'] if cond else res['fails']).append(('PASS ' if cond else 'FAIL ') + name + ('' if cond else '  <- ' + str(detail)))

sok('I-9 Supabase 주소', 'vqhwinjyiiqocvrglfqu.supabase.co' in HTML)
sok('I-10 anon 키 포함', 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9' in HTML)
sok('I-11 service_role 키 없음', 'service_role' not in HTML)
sok('I-12 CDN 버전 고정', '@supabase/supabase-js@2.45.4' in HTML)
sok('I-13 이관 함수 사용', "rpc('import_prototype_json'" in HTML)
sok('I-14 save() 가 동기화 예약', 'cloudTouch();                     /* 로그인했다면' in HTML)
sok('I-15 시트 닫을 때 정리', 'if (authCtx && authCtx.sh && authCtx.sh.el === wrap) authCtx = null;' in HTML)
sok('I-16 온보딩 로그인 링크', 'data-act="ob-login"' in HTML)
sok('I-17 온보딩 안내 문구', '계정 없이 쓰면 이 기기에만 저장돼요' in HTML)
sok('I-18 온라인·복귀 감지 연결', 'bindCloudEvents();' in HTML)
sok('I-19 인증 링크 세션 감지', 'detectSessionInUrl: true' in HTML)
sok('I-20 기존 안내 문구 규칙 유지', 'font-size:11px' in rule('.hint'), rule('.hint'))
sok('I-25 탭 글자가 가운데 정렬', 'text-align:center' in rule('.authtab'), rule('.authtab'))
sok('I-24 설정 안내가 계정과 어긋나지 않음', '모든 데이터는 이 기기에만 저장돼요' not in HTML and '계정을 만들면 서버에도 함께 백업돼요' in HTML)
sok('I-21 설계서에 계정 · 동기화 장', '클라우드 동기화' in SPEC)
sok('I-22 설계서에 이관 함수', 'import_prototype_json' in SPEC)
sok('I-23 설계서에 인증 메일 안내', '이메일 인증' in SPEC)

for line in res['log']:
    print(line)
for line in res['fails']:
    print(line)
print()
print('ALL %d PASSED' % len(res['log']) if not res['fails']
      else '%d passed / %d FAILED' % (len(res['log']), len(res['fails'])))
sys.exit(0 if not res['fails'] else 1)
