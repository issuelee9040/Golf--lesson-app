#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""1탭 수강권 연장(재등록)의 계산·기록을 실제 코드로 검사한다."""
import sys, json
import quickjs

HTML = open('/workspace/golf-lesson-app/prototype.html', encoding='utf-8').read()
start = HTML.index("var RENEW_PRESETS = [8, 10, 20];")
end = HTML.index("/* =========================================================\n   통계 탭")
CODE = HTML[start:end]

HARNESS = r"""
var TODAY = '2026-11-23';
function todayISO(){ return TODAY; }
function nowLocalISO(){ return TODAY + 'T14:30:00'; }
function parseISO(s){ var p = String(s).split('-'); return new Date(+p[0], (+p[1]) - 1, +p[2]); }
function iso(d){ function pad(n){ return n < 10 ? '0' + n : '' + n; } return d.getFullYear() + '-' + pad(d.getMonth()+1) + '-' + pad(d.getDate()); }
function addMonths(s, n){
  var d = parseISO(s), day = d.getDate();
  d.setDate(1); d.setMonth(d.getMonth() + n);
  var last = new Date(d.getFullYear(), d.getMonth() + 1, 0).getDate();
  d.setDate(Math.min(day, last));
  return iso(d);
}
var uidSeq = 0;
function uid(p){ uidSeq++; return (p || 'id') + '_' + uidSeq; }
function esc(s){ return String(s === null || s === undefined ? '' : s); }
function money(n){
  if (n === '' || n === null || n === undefined) return '-';
  return String(Math.round(Number(n))).replace(/\B(?=(\d{3})+(?!\d))/g, ',') + '원';
}
function toast(){}
function save(){}
function render(){}
function paintMemberSheet(){}
function openSheet(){ return { body:{}, footer:{}, el:{ setAttribute:function(){} }, close:function(){} }; }
function pickFieldHTML(){ return ''; }
function monthPickOptions(){ return []; }
function perSessionPrice(p){
  if (!p) return 0;
  var price = +p.price || 0, n = +p.totalSessions || 0;
  return (price > 0 && n > 0) ? Math.round(price / n) : 0;
}
function memberById(id){ for (var i=0;i<state.members.length;i++) if (state.members[i].id === id) return state.members[i]; return null; }
function memberPkgs(id){ return state.packages.filter(function(p){ return p.memberId === id; }); }
function activePkgs(id){ return memberPkgs(id).filter(function(p){ return p.remainingSessions > 0; }); }
function totalRemaining(id){ var s = 0; activePkgs(id).forEach(function(p){ s += p.remainingSessions; }); return s; }
function isArr(v){ return Object.prototype.toString.call(v) === '[object Array]'; }
var FIELDS = {};
var document = {
  getElementById: function(id){
    var el = FIELDS[id] || null;
    if (el && !el.focus) el.focus = function(){};
    return el;
  },
  createElement: function(){ return {}; }
};
var memberCtx = null;
var state = { members: [], packages: [], sessions: [], notes: [], renewalLog: [] };
""" + CODE + r"""

var fails = [], log = [];
function ok(c, n){ if (c) log.push('PASS ' + n); else fails.push('FAIL ' + n); }
function eq(a, b, n){ ok(a === b, n + (a === b ? '' : '\n  got=[' + a + ']\n  want=[' + b + ']')); }

/* 기준 데이터: 55분 10회 100만원 (잔여 4), 25분 20회 140만원 (잔여 2) */
function base(){
  state.members = [{ id:'m1', name:'박서연', passHistory: [] }];
  state.packages = [
    { id:'p1', memberId:'m1', durationMinutes:55, totalSessions:10, remainingSessions:4,
      startDate:'2026-09-01', expiryDate:'2027-03-01', price:1000000 },
    { id:'p2', memberId:'m1', durationMinutes:25, totalSessions:20, remainingSessions:2,
      startDate:'2026-10-11', expiryDate:'2027-04-11', price:1400000 }
  ];
  state.sessions = [{ id:'s1', memberId:'m1', packageId:'p1', date:'2026-11-20', startTime:'10:00', durationMinutes:55, status:'completed', deducted:true }];
  state.notes = [{ id:'n1', memberId:'m1', date:'2026-11-20', text:'아이언 페이스 열림 교정', tags:['아이언'] }];
  state.renewalLog = [];
  renewCtx = null;
  FIELDS = {};
}
function pkg(id){ for (var i=0;i<state.packages.length;i++) if (state.packages[i].id === id) return state.packages[i]; return null; }

/* 1. 금액 기본값 = 지난 수강권 회당 금액 × 추가 횟수 */
base();
eq(renewalDefaultAmount('m1', 8, 55), 800000, '1-1 55분 회당 10만 × 8회');
eq(renewalDefaultAmount('m1', 10, 25), 700000, '1-2 25분 회당 7만 × 10회');
eq(renewalDefaultAmount('m1', 8, 55) + '', '800000', '1-3 숫자형');

/* 2. 같은 시간대 수강권이 없으면 다른 수강권 기준 */
base();
eq(renewalDefaultAmount('m1', 5, 40), 350000, '2-1 40분 없음 → 가장 최근 25분권 기준');

/* 3. 금액이 하나도 없으면 빈 값 */
base();
state.packages.forEach(function(p){ p.price = 0; });
eq(renewalDefaultAmount('m1', 8, 55), '', '3-1 금액 미입력이면 비워 둠');

/* 4. 가장 최근에 산 수강권을 기준으로 (같은 55분) */
base();
state.packages.push({ id:'p3', memberId:'m1', durationMinutes:55, totalSessions:8, remainingSessions:8,
  startDate:'2026-11-01', expiryDate:'2027-05-01', price:920000 });
eq(renewalDefaultAmount('m1', 8, 55), 920000, '4-1 최신 55분권 회당 11.5만 × 8회');
eq(lastPkgOf('m1').id, 'p3', '4-2 lastPkgOf = 최신');

/* 5. 1탭 연장: +8회, 55분, 금액은 기본값, 6개월 */
base();
renewCtx = { sh:{ body:{}, footer:{}, el:{ setAttribute:function(){} }, close:function(){} },
  memberId:'m1', duration:55, sessions:8, amount:800000, amountTouched:false, months:'6' };
FIELDS = { rqSessions:{ value:'8' }, rqAmount:{ value:'800000' }, rqMonths:{ value:'6' } };
var beforeTotal = totalRemaining('m1');
saveRenewal();
eq(state.packages.length, 3, '5-1 새 수강권 1개 추가');
var np = state.packages[2];
eq(np.totalSessions, 8, '5-2 총 8회');
eq(np.remainingSessions, 8, '5-3 잔여 8회');
eq(np.durationMinutes, 55, '5-4 55분');
eq(np.price, 800000, '5-5 금액 80만원');
eq(np.startDate, '2026-11-23', '5-6 오늘 시작');
eq(np.expiryDate, '2027-05-23', '5-7 6개월 뒤 만료');
eq(totalRemaining('m1'), beforeTotal + 8, '5-8 잔여 합계 +8');

/* 6. 기존 수강권·레슨·차트 기록은 그대로 */
eq(pkg('p1').remainingSessions, 4, '6-1 기존 55분권 잔여 유지');
eq(pkg('p2').remainingSessions, 2, '6-2 기존 25분권 잔여 유지');
eq(state.sessions.length, 1, '6-3 레슨 기록 유지');
eq(state.notes.length, 1, '6-4 레슨 차트 유지');
eq(state.notes[0].tags.join(','), '아이언', '6-5 차트 태그 유지');
eq(perSessionPrice(pkg('p1')), 100000, '6-6 지난 수강권 회당 금액 그대로(과거 수입 왜곡 없음)');

/* 7. 이력 기록 */
var m = state.members[0];
eq(m.passHistory.length, 1, '7-1 passHistory 1건');
eq(m.passHistory[0].sessions, 8, '7-2 이력 횟수');
eq(m.passHistory[0].amount, 800000, '7-3 이력 금액');
eq(m.passHistory[0].pkgId, np.id, '7-4 새 수강권 연결');
eq(state.renewalLog.length, 1, '7-5 renewalLog 1건');
eq(state.renewalLog[0].memberId, 'm1', '7-6 renewalLog 회원');
eq(state.renewalLog[0].date, '2026-11-23', '7-7 renewalLog 날짜');
eq(state.renewalLog[0].kind, 'renewal', '7-8 renewalLog 종류');

/* 8. 직접 입력한 금액·기간·시간대 */
base();
renewCtx = { sh:{ body:{}, footer:{}, el:{ setAttribute:function(){} }, close:function(){} },
  memberId:'m1', duration:25, sessions:12, amount:'', amountTouched:true, months:'12' };
FIELDS = { rqSessions:{ value:'12' }, rqAmount:{ value:'900000' }, rqMonths:{ value:'12' } };
saveRenewal();
var np2 = state.packages[2];
eq(np2.totalSessions, 12, '8-1 직접 입력 12회');
eq(np2.durationMinutes, 25, '8-2 25분');
eq(np2.price, 900000, '8-3 직접 입력 금액');
eq(np2.expiryDate, '2027-11-23', '8-4 12개월');
eq(perSessionPrice(np2), 75000, '8-5 새 수강권 회당 7.5만');

/* 9. 무기한(유효기간 0) */
base();
renewCtx = { sh:{ body:{}, footer:{}, el:{ setAttribute:function(){} }, close:function(){} },
  memberId:'m1', duration:55, sessions:10, amount:'', amountTouched:true, months:'0' };
FIELDS = { rqSessions:{ value:'10' }, rqAmount:{ value:'0' }, rqMonths:{ value:'0' } };
saveRenewal();
eq(state.packages[2].expiryDate, '9999-12-31', '9-1 무기한');
eq(state.packages[2].price, 0, '9-2 금액 0');

/* 10. 잘못된 횟수는 아무것도 바꾸지 않는다 */
base();
renewCtx = { sh:{ body:{}, footer:{}, el:{ setAttribute:function(){} }, close:function(){} },
  memberId:'m1', duration:55, sessions:0, amount:0, amountTouched:true, months:'6' };
FIELDS = { rqSessions:{ value:'0' }, rqAmount:{ value:'' }, rqMonths:{ value:'6' } };
saveRenewal();
eq(state.packages.length, 2, '10-1 0회는 추가 안 됨');
eq(state.members[0].passHistory.length, 0, '10-2 이력도 없음');

/* 11. 잔여 0인 회원도 연장 가능 (0 → n) */
base();
state.packages.forEach(function(p){ p.remainingSessions = 0; });
renewCtx = { sh:{ body:{}, footer:{}, el:{ setAttribute:function(){} }, close:function(){} },
  memberId:'m1', duration:55, sessions:8, amount:'', amountTouched:true, months:'6' };
FIELDS = { rqSessions:{ value:'8' }, rqAmount:{ value:'' }, rqMonths:{ value:'6' } };
saveRenewal();
eq(totalRemaining('m1'), 8, '11-1 잔여 0 → 8회');
eq(state.packages[2].price, 0, '11-2 금액 비우면 0');

/* 12. 요약 문구: 잔여 6 → 14회 */
base();
renewCtx = { sh:{ body:{}, footer:{}, el:{ setAttribute:function(){} }, close:function(){} },
  memberId:'m1', duration:55, sessions:8, amount:800000, amountTouched:false, months:'6' };
var sum = renewSummaryHTML(state.members[0]);
ok(sum.indexOf('6회') > 0, '12-1 연장 전 잔여 6회');
ok(sum.indexOf('14회') > 0, '12-2 연장 후 잔여 14회');
ok(sum.indexOf('회당 100,000원') > 0, '12-3 회당 금액 표시');
ok(sum.indexOf('8회') > 0, '12-4 새 수강권 8회');

/* 13. 금액을 직접 고치면 그 값이 회당 계산에 쓰인다 */
renewCtx.amount = 760000;
renewCtx.amountTouched = true;
ok(renewSummaryHTML(state.members[0]).indexOf('회당 95,000원') > 0, '13-1 직접 금액 회당 계산');

/* 14. 다음 연장도 이력이 쌓인다 */
base();
var n0 = 0;
for (var k = 0; k < 2; k++) {
  renewCtx = { sh:{ body:{}, footer:{}, el:{ setAttribute:function(){} }, close:function(){} },
    memberId:'m1', duration:55, sessions:8, amount:'', amountTouched:true, months:'6' };
  FIELDS = { rqSessions:{ value:'8' }, rqAmount:{ value:'' }, rqMonths:{ value:'6' } };
  saveRenewal();
}
eq(state.members[0].passHistory.length, 2, '14-1 두 번 연장 이력 2건');
eq(state.renewalLog.length, 2, '14-2 renewalLog 2건');
eq(totalRemaining('m1'), 22, '14-3 잔여 6 + 8 + 8 = 22');
eq(state.packages.length, 4, '14-4 수강권 4개');

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
print('\nALL %d PASSED' % len(data['pass']))
