#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""일반취소(excused_cancel) 처리 = 차감 복구 + 일정에서 삭제 를 실제 코드로 검사한다.
   - 레슨 상태 시트/빠른 버튼 경로: cancelExcused()
   - 오늘 마감 정산 경로: settleApply()
   - 되돌리기: undoCancelExcused()
   - 예전 데이터 정리(migExcused), 통계 집계(cancelLog)
"""
import sys, json
import quickjs

HTML = open('/workspace/golf-lesson-app/prototype.html', encoding='utf-8').read()

scripts = []
import re
for m in re.finditer(r'<script>(.*?)</script>', HTML, re.S):
    scripts.append(m.group(1))
BIG = max(scripts, key=len)

start = BIG.index('(function(){') + len('(function(){')
end = BIG.rindex('})();')
BODY = BIG[start:end]

HARNESS = r"""
/* ---------- 가상 DOM ---------- */
function El(id){
  this.id = id; this.value = ''; this.disabled = false; this.readOnly = false;
  this.textContent = ''; this.innerHTML = ''; this.style = {}; this._cls = {};
  this.children = []; this.scrollTop = 0;
  var self = this;
  this.classList = {
    add: function(c){ self._cls[c] = true; },
    remove: function(c){ delete self._cls[c]; },
    toggle: function(c, f){ if (f === undefined) { if (self._cls[c]) delete self._cls[c]; else self._cls[c] = true; }
                            else if (f) self._cls[c] = true; else delete self._cls[c]; },
    contains: function(c){ return !!self._cls[c]; }
  };
  this.addEventListener = function(){}; this.removeEventListener = function(){};
  this.setAttribute = function(k, v){ if (!this._attrs) this._attrs = {}; this._attrs[k] = v; };
  this.getAttribute = function(k){ return (this._attrs && this._attrs[k]) || ''; };
  this.appendChild = function(c){ this.children.push(c); return c; };
  this.removeChild = function(){};
  this.querySelector = function(){ return null; };
  this.querySelectorAll = function(){ return []; };
  this.closest = function(){ return null; };
  this.focus = function(){};
  this.getBoundingClientRect = function(){ return { top:0, left:0, width:0, height:0 }; };
}
var ELS = {};
function mkEl(id){ var e = new El(id); ELS[id] = e; return e; }
var document = {
  getElementById: function(id){ return ELS[id] || null; },
  createElement: function(){ return new El('new'); },
  addEventListener: function(){},
  body: new El('body'), documentElement: new El('html'),
  querySelector: function(){ return null; }, querySelectorAll: function(){ return []; }
};
var window = { addEventListener: function(){}, SpeechRecognition: null, webkitSpeechRecognition: null };
var navigator = { userAgent: 'test' };
var localStorage = {
  _d: {},
  getItem: function(k){ return this._d[k] === undefined ? null : this._d[k]; },
  setItem: function(k, v){ this._d[k] = String(v); },
  removeItem: function(k){ delete this._d[k]; }
};
var timers = [];
function setTimeout(fn, ms){ timers.push(fn); return timers.length; }
function clearTimeout(){}
mkEl('main'); mkEl('hd'); mkEl('tabbar'); mkEl('fab'); mkEl('toast');
"""

TEST = r"""

/* ================= 테스트 ================= */
/* 첫 실행에는 온보딩이 뜨고 저장본이 아직 없을 수 있으니, 여기서는 데모 데이터를 기준 상태로 직접 만든다 */
obWaiting = false; state = null; localStorage._d = {}; load();
var fails = [], log = [];
function ok(cond, name){ if (cond) log.push('PASS ' + name); else fails.push('FAIL ' + name); }
var today = todayISO();
function todayCount(){ return sessionsByDate(today).length; }
function noNaN(html, name){ ok(String(html).indexOf('NaN') < 0, name); }

/* 0. 상태 설명 문구 */
ok(STATUS.excused_cancel.desc === '사전 취소 · 미차감 · 일정에서 삭제', '0-1 일반취소 설명: ' + STATUS.excused_cancel.desc);
ok(STATUS.excused_cancel.deducted === false, '0-2 일반취소는 미차감');
ok(todayCount() === 4, '0-3 데모 오늘 레슨 4건 (' + todayCount() + ')');
ok(state.sessions.filter(function(s){ return s.status === 'excused_cancel'; }).length === 0, '0-4 로드 직후 일반취소 레슨은 일정에 없음');

/* 1. 예정 레슨 → 일반취소 : 메인·캘린더에서 사라짐 */
var s1 = sessionsByDate(today)[0];
var sid1 = s1.id, nm1 = memberName(s1.memberId), pkg1 = pkgById(s1.packageId), rem1 = pkg1.remainingSessions;
var cx1 = cancelExcused(s1); save();
ok(todayCount() === 3, '1-1 오늘 목록에서 제거 (' + todayCount() + ')');
ok(findSession(sid1) === null, '1-2 state.sessions 에서 제거');
ok(pkg1.remainingSessions === rem1, '1-3 예정 취소는 차감 변화 없음 (' + rem1 + '→' + pkg1.remainingSessions + ')');
var hToday = viewToday();
ok(hToday.indexOf('오늘 레슨 3건') >= 0, '1-4 오늘 히어로 재계산');
ok(hToday.indexOf('data-sid="' + sid1 + '"') < 0, '1-5 오늘 카드에 안 보임');
noNaN(hToday, '1-6 오늘 화면에 NaN 없음');
var hCal = viewCalendar();
ok(hCal.indexOf('data-sid="' + sid1 + '"') < 0, '1-7 캘린더(목록·시간표)에서 안 보임');
ok(hCal.indexOf('레슨 3건') >= 0, '1-8 캘린더 날짜 요약 재계산');
noNaN(hCal, '1-9 캘린더 화면에 NaN 없음');

/* 2. 되돌리기 */
var und = undoCancelExcused(cx1);
ok(und === true, '2-1 되돌리기 성공');
ok(todayCount() === 4 && findSession(sid1), '2-2 레슨 복구');
ok(pkgById(s1.packageId).remainingSessions === rem1, '2-3 잔여 횟수 원상복구');
ok(state.cancelLog.length === 0, '2-4 취소 기록도 되돌림');

/* 3. 완료 레슨 → 일반취소 : +1 복구 + 일정 삭제 */
var done = state.sessions.filter(function(x){ return x.status === 'completed' && x.deducted; })[0];
var dpkg = pkgById(done.packageId), drem = dpkg.remainingSessions, did = done.id, ddate = done.date;
var dmonth = ddate.slice(0, 7);
var beforeExc = monthStats(dmonth).excused_cancel;
var cx3 = cancelExcused(done); save();
ok(dpkg.remainingSessions === drem + 1, '3-1 차감 1회 복구 (' + drem + '→' + dpkg.remainingSessions + ')');
ok(findSession(did) === null, '3-2 일정에서 제거');
ok(cx3.wasDeducted === true, '3-3 차감됐던 레슨으로 기록');
var sessAfter = state.sessions.filter(function(x){ return x.date === ddate; }).length;
ok(monthStats(dmonth).excused_cancel === beforeExc + 1, '3-4 통계 일반취소 집계 +1');
ok((state.cancelLog || []).length === 1, '3-5 취소 기록 1건 남음');
ok(undoCancelExcused(cx3) === true, '3-6 되돌리기 성공');
ok(pkgById(done.packageId).remainingSessions === drem, '3-7 되돌리면 잔여 횟수도 원래대로 (' + pkgById(done.packageId).remainingSessions + ')');
ok(monthStats(dmonth).excused_cancel === beforeExc, '3-8 되돌리면 통계도 원래대로');

/* 4. 같은 레슨을 두 번 일반취소해도 횟수가 두 번 복구되지 않음 */
var twice = sessionsByDate(today)[0];
var tpk = pkgById(twice.packageId), trem = tpk.remainingSessions;
applyStatus(twice, 'completed');           /* 먼저 차감 상태로 */
trem = tpk.remainingSessions;
var cxa = cancelExcused(twice);
var remA = tpk.remainingSessions;
var cxb = cancelExcused(twice);            /* 이미 빠진 레슨 */
ok(remA === trem + 1, '4-1 첫 취소에서 1회만 복구 (' + trem + '→' + remA + ')');
ok(tpk.remainingSessions === remA, '4-2 두 번째 호출은 횟수 변화 없음');
ok(cxb.removed === false, '4-3 이미 빠진 레슨은 재삭제 없음');

/* 5. 마감 정산에서 일반취소 → 일정에서 지워짐 */
localStorage._d = {}; state = null; load();       /* 데모로 초기화 */
var list5 = sessionsByDate(today);
var keepName = memberName(list5[1].memberId);
var cutName = memberName(list5[0].memberId);
var cutPkg = pkgById(list5[0].packageId), cutRem = cutPkg.remainingSessions;
settleCtx = {
  sel: { date: today, decisions: {} },
  list: list5.slice(),
  sh: { close: function(){}, body: new El('b'), footer: new El('f') }
};
list5.forEach(function(x, i){
  settleCtx.sel.decisions[x.id] = (i === 0) ? 'excused_cancel' : (i === 1 ? 'completed' : 'makeup');
});
var n0 = todayCount();
settleApply();
ok(todayCount() === n0 - 1, '5-1 정산 후 오늘 목록에서 1건 제거 (' + n0 + '→' + todayCount() + ')');
ok(findSession(list5[0].id) === null, '5-2 일반취소 레슨은 state.sessions 에서 제거');
ok(cutPkg.remainingSessions === cutRem, '5-3 일반취소는 차감 없음');
var rec5 = settlementFor(today);
ok(!!rec5 && rec5.counts.excused_cancel === 1, '5-4 정산 기록에 일반취소 1건');
ok(!!rec5 && rec5.counts.completed === 1, '5-5 정산 기록에 완료 1건');
var lastToast = ELS.toast.innerHTML + ELS.toast.textContent;
ok(lastToast.indexOf('일반취소 1건 일정에서 지움') >= 0, '5-6 토스트에 안내: ' + lastToast);
var h5 = viewToday();
ok(h5.indexOf('일반취소 1</span>') >= 0 || h5.indexOf('일반취소 1') >= 0, '5-7 오늘 정산 카드에 일반취소 1건');
noNaN(h5, '5-8 정산 후 오늘 화면 NaN 없음');

/* 6. 오늘 레슨 전부 일반취소 → 빈 하루에서도 화면이 깨지지 않음 */
localStorage._d = {}; state = null; load();
var list6 = sessionsByDate(today);
settleCtx = {
  sel: { date: today, decisions: {} },
  list: list6.slice(),
  sh: { close: function(){}, body: new El('b'), footer: new El('f') }
};
list6.forEach(function(x){ settleCtx.sel.decisions[x.id] = 'excused_cancel'; });
settleApply();
ok(todayCount() === 0, '6-1 오늘 레슨 0건');
var h6 = viewToday();
ok(h6.indexOf('오늘 레슨 0건') >= 0, '6-2 히어로 0건 표시');
ok(h6.indexOf('레슨 없음') >= 0, '6-3 상태 pill = 레슨 없음');
ok(h6.indexOf('오늘은 예약이 없어요') >= 0, '6-4 빈 상태 카드');
ok(h6.indexOf('일반취소 4</span>') >= 0 || h6.indexOf('일반취소 4') >= 0, '6-5 정산 요약에 일반취소 4건');
noNaN(h6, '6-6 빈 하루 화면 NaN 없음');
var hc6 = viewCalendar();
ok(hc6.indexOf('예약 없음') >= 0 || hc6.indexOf('이 날은 예약이 없어요') >= 0, '6-7 캘린더 빈 상태');
noNaN(hc6, '6-8 캘린더 NaN 없음');
var saved6 = JSON.parse(localStorage.getItem('golfLessonApp.v2'));
ok(saved6.sessions.filter(function(x){ return x.date === today; }).length === 0, '6-9 저장 데이터에도 오늘 레슨 없음');

/* 7. 빠진 자리에 새 예약이 다시 들어갈 수 있음 */
ok(sessionsByDate(today).filter(function(x){ return minOf(x.startTime) === minOf(list6[0].startTime); }).length === 0,
   '7-1 비운 시간대 재예약 가능');

/* 8. 예전 데이터 정리(마이그레이션): 남아 있던 일반취소 레슨은 한 번만 제거 */
localStorage._d = {}; state = null; load();
var seed = JSON.parse(JSON.stringify(state));
var sp = seed.packages[0];
var oldRem = sp.remainingSessions;
seed.sessions.push({
  id: 'lsn_old_excused', memberId: seed.members[0].id, packageId: sp.id,
  date: today, startTime: '08:00', durationMinutes: 25, location: '',
  status: 'excused_cancel', deducted: false, memo: '', settledAt: '', source: 'demo'
});
delete seed.migExcused;
localStorage.setItem('golfLessonApp.v2', JSON.stringify(seed));
state = null; load();
ok(findSession('lsn_old_excused') === null, '8-1 예전 일반취소 레슨 정리됨');
ok(pkgById(sp.id).remainingSessions === oldRem, '8-2 정리해도 잔여 횟수 그대로');
ok(state.migExcused === 1, '8-3 마이그레이션 표시');
var saved8 = JSON.parse(localStorage.getItem('golfLessonApp.v2'));
ok(saved8.migExcused === 1, '8-4 저장됨');

/* 9. 실제 클릭 경로(onClick)로 상태 변경 → 일반취소 */
localStorage._d = {}; state = null; load();
var s9 = sessionsByDate(today)[0], sid9 = s9.id;
ELS.toast.innerHTML = ''; ELS.toast.textContent = ''; ELS.toast.classList.remove('act');
var btn9 = new El('btn');
btn9.setAttribute('data-act', 'status-set');
btn9.setAttribute('data-sid', sid9);
btn9.setAttribute('data-status', 'excused_cancel');
onClick({ target: { closest: function(){ return btn9; } } });
ok(findSession(sid9) === null && todayCount() === 3, '9-1 상태 변경 경로에서도 일정 삭제');
ok(ELS.toast.innerHTML.indexOf('일정에서 지웠어요') >= 0, '9-2 토스트 문구: ' + ELS.toast.innerHTML);
ok(ELS.toast.innerHTML.indexOf('data-act="status-undo"') >= 0, '9-3 토스트에 되돌리기 버튼');
ok(ELS.toast.classList.contains('act'), '9-4 토스트가 버튼형으로 표시');
ok(!!lastCancel, '9-5 되돌리기용 스냅샷 보관');
/* 되돌리기 버튼 클릭 */
var btn9u = new El('btn');
btn9u.setAttribute('data-act', 'status-undo');
onClick({ target: { closest: function(){ return btn9u; } } });
ok(!!findSession(sid9) && todayCount() === 4, '9-6 되돌리기 버튼으로 복구');
ok(ELS.toast.textContent.indexOf('되돌렸어요') >= 0, '9-7 되돌림 안내: ' + ELS.toast.textContent);
ok(!ELS.toast.classList.contains('act'), '9-8 되돌린 뒤 토스트는 버튼형 해제');

/* 결과 */
JSON.stringify({ pass: log, fail: fails });
"""

CODE = HARNESS + "\n" + BODY + "\n" + TEST

ctx = quickjs.Context()
try:
    out = ctx.eval(CODE)
except Exception as e:
    print("EVAL ERROR:", e)
    sys.exit(2)

if not isinstance(out, str):
    print("UNEXPECTED RESULT:", out)
    sys.exit(2)

res = json.loads(out)
for line in res['pass']:
    print(line)
for line in res['fail']:
    print(line)
print("\n통과 %d · 실패 %d" % (len(res['pass']), len(res['fail'])))
sys.exit(1 if res['fail'] else 0)
