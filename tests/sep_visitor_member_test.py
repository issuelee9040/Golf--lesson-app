#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""별도 결제(필드 · 숏게임 · 원포인트)로 온 방문 회원을 회원목록에 보존하는지 검사한다.

- 이름만 적어 저장한 비회원 → state.members 에 수강권 없이 남고, 레슨이 그 회원에 연결되는지
- 이미 있는 회원이면 중복 생성 없이 그 회원으로 연결되는지 (수강권 잔여는 그대로)
- 팀 · 단체 이름은 회원으로 만들지 않는지
- 회원목록 줄: `수강권 없음 · 별도 N회`, 잔여 자리에 NaN/0 대신 `–`
- 정렬 3종에서 깨지지 않는지
- 회원 정보창: 별도 레슨 기록 · 안내, `+ 수강권 추가` 로 나중에 전환
- 데모 데이터에 수강권 없이 원포인트로만 다닌 회원이 있는지
"""
import re, sys, json
import quickjs

HTML = open('/workspace/golf-lesson-app/prototype.html', encoding='utf-8').read()

scripts = re.findall(r'<script>(.*?)</script>', HTML, re.S)
CODE = max(scripts, key=len)
CODE = CODE.replace("(function(){\n'use strict';\n", '', 1)
CODE = CODE.rstrip()
assert CODE.endswith('})();'), CODE[-40:]
CODE = CODE[:-len('})();')]

STUBS = r"""
var registry = {};
function makeEl(){
  var el = {
    innerHTML:'', textContent:'', value:'', hidden:false, disabled:false, style:{}, children:[],
    classList:{ add:function(){}, remove:function(){}, toggle:function(){}, contains:function(){ return false; } },
    setAttribute:function(){}, getAttribute:function(){ return null; }, removeAttribute:function(){},
    addEventListener:function(){}, appendChild:function(){}, removeChild:function(){},
    querySelector:function(){ return makeEl(); }, querySelectorAll:function(){ return []; },
    focus:function(){}, select:function(){}, click:function(){}, closest:function(){ return null; },
    parentNode:null, getBoundingClientRect:function(){ return { top:0, left:0, width:0, height:0 }; }
  };
  return el;
}
function resetDOM(){ registry = {}; }
var document = {
  getElementById:function(id){ if (!registry[id]) registry[id] = makeEl(); return registry[id]; },
  createElement:function(){ return makeEl(); },
  addEventListener:function(){},
  body:makeEl(),
  documentElement:makeEl(),
  querySelector:function(){ return makeEl(); }
};
var window = { addEventListener:function(){} };
var localStorage = { getItem:function(){ return null; }, setItem:function(){}, removeItem:function(){} };
function setTimeout(){ return 0; }
function clearTimeout(){}
"""

HARNESS = r"""
var RESULT = [];
function ok(name, cond, detail){ RESULT.push({ name:name, pass:!!cond, detail:detail || '' }); }
function eq(name, a, b){ ok(name, a === b, 'got=' + JSON.stringify(a) + ' want=' + JSON.stringify(b)); }
function contain(name, hay, needle){ ok(name, String(hay).indexOf(needle) >= 0, 'needle=' + needle); }
function notContain(name, hay, needle){ ok(name, String(hay).indexOf(needle) < 0, 'unexpected=' + needle); }

function blank(){
  return { version:2, pro:{ name:'테스트 프로', title:'KPGA', academy:'' }, templates:[],
    members:[], packages:[], sessions:[], settlements:[], notes:[], cancelLog:[], renewalLog:[],
    calendarSync:{ enabled:false, target:'both' } };
}
function baseState(){
  var st = blank();
  st.members.push({ id:'m1', name:'김민준', gender:'male', region:'분당', phone:'', level:'중급', memo:'', since:'2026-01-01' });
  st.packages.push({ id:'p1', memberId:'m1', durationMinutes:55, totalSessions:8, remainingSessions:5,
    startDate:'2026-01-01', expiryDate:'9999-12-31', price:800000, note:'' });
  return st;
}

/* ========== 1. 이름만 적어 온 방문 회원 ========== */
resetDOM(); state = baseState();
var g = ensureMemberForGuest('  최유진 ');
ok('1-1 새 회원으로 남음', !!g && g.name === '최유진');
eq('1-2 수강권은 만들지 않음', memberPkgs(g.id).length, 0);
eq('1-3 잔여 0', totalRemaining(g.id), 0);
eq('1-4 회원 수 2명', state.members.length, 2);
var g2 = ensureMemberForGuest('최유진');
eq('1-5 같은 이름은 중복 생성 없음', g2.id, g.id);
eq('1-6 회원 수 그대로', state.members.length, 2);
ok('1-7 팀 이름은 회원으로 만들지 않음', ensureMemberForGuest('한빛상사 팀') === null);
ok('1-8 ○○팀도 제외', ensureMemberForGuest('홍길동팀') === null);
eq('1-9 팀은 목록에 안 들어감', state.members.length, 2);

/* ========== 2. 예약(별도 결제 · 비회원) → 회원으로 연결 ========== */
resetDOM(); state = baseState();
bookCtx = { sh:{ close:function(){} }, mode:'sep', kind:'onepoint', target:'guest', dur:55, sepDur:60,
  date:'2026-12-08', time:'19:00', memberId:'', guest:'', fee:'', location:'', memo:'' };
document.getElementById('bkDate').value = '2026-12-08';
document.getElementById('bkTime').value = '19:00';
document.getElementById('bkGuest').value = '최유진';
document.getElementById('bkFee').value = '90000';
document.getElementById('bkSepDur').value = '60';
saveBooking();
var s1 = state.sessions[state.sessions.length - 1];
var m1 = findMemberByName('최유진');
ok('2-1 회원이 만들어짐', !!m1);
eq('2-2 레슨이 그 회원에 연결', s1.memberId, m1.id);
eq('2-3 비회원 이름은 비움', s1.guestName, '');
eq('2-4 수강권 없음', memberPkgs(m1.id).length, 0);
var us1 = sepUsage(m1.id);
eq('2-5 별도 이용 1회', us1.count, 1);
eq('2-6 별도 금액', us1.fee, 90000);
eq('2-7 종류 onepoint', us1.kinds.onepoint, 1);

/* 두 번째 레슨도 같은 회원으로 */
bookCtx = { sh:{ close:function(){} }, mode:'sep', kind:'field', target:'guest', dur:55, sepDur:180,
  date:'2026-12-09', time:'08:00', memberId:'', guest:'', fee:'', location:'', memo:'' };
document.getElementById('bkDate').value = '2026-12-09';
document.getElementById('bkTime').value = '08:00';
document.getElementById('bkGuest').value = '최유진';
document.getElementById('bkFee').value = '300000';
document.getElementById('bkSepDur').value = '180';
saveBooking();
eq('2-8 회원이 또 생기지 않음', state.members.length, 2);
var us1b = sepUsage(m1.id);
eq('2-9 별도 이용 2회', us1b.count, 2);
eq('2-10 금액 합계', us1b.fee, 390000);

/* ========== 3. 빠른 추가에서도 ========== */
resetDOM(); state = baseState();
openQuickAddSheet();
document.getElementById('qaLine').value = '내일 저녁 7시 원포인트 이서연 60분 8만';
applyQuickParse();
document.getElementById('qaDate').value = '2026-12-10';
document.getElementById('qaTime').value = '19:00';
document.getElementById('qaGuest').value = '이서연';
document.getElementById('qaFee').value = '80000';
document.getElementById('qaSepDur').value = '60';
saveQuickLesson();
var s2 = state.sessions[state.sessions.length - 1];
var m2 = findMemberByName('이서연');
ok('3-1 빠른 추가도 회원으로 남김', !!m2);
eq('3-2 레슨 연결', s2.memberId, m2.id);
eq('3-3 별도 결제', s2.lessonKind, 'onepoint');

/* ========== 4. 이미 수강권이 있는 회원이면 잔여는 그대로 ========== */
resetDOM(); state = baseState();
bookCtx = { sh:{ close:function(){} }, mode:'sep', kind:'shortgame', target:'guest', dur:55, sepDur:90,
  date:'2026-12-11', time:'15:00', memberId:'', guest:'', fee:'', location:'', memo:'' };
document.getElementById('bkDate').value = '2026-12-11';
document.getElementById('bkTime').value = '15:00';
document.getElementById('bkGuest').value = '김민준';
document.getElementById('bkFee').value = '120000';
document.getElementById('bkSepDur').value = '90';
saveBooking();
eq('4-1 회원이 또 생기지 않음', state.members.length, 1);
eq('4-2 기존 수강권 잔여 그대로', totalRemaining('m1'), 5);
var s4 = state.sessions[state.sessions.length - 1];
eq('4-3 기존 회원에 연결', s4.memberId, 'm1');
eq('4-4 별도 이용 기록', sepUsage('m1').count, 1);

/* ========== 5. 회원목록 줄 ========== */
resetDOM(); state = baseState();
var v = ensureMemberForGuest('최유진');
state.sessions.push({ id:'x1', memberId:v.id, packageId:'', guestName:'', lessonKind:'onepoint', separatePay:true,
  fee:90000, date:'2026-12-01', startTime:'19:00', durationMinutes:60, location:'', status:'completed',
  deducted:false, charged:true, memo:'', settledAt:'' });
state.sessions.push({ id:'x2', memberId:v.id, packageId:'', guestName:'', lessonKind:'field', separatePay:true,
  fee:300000, date:'2026-12-02', startTime:'08:00', durationMinutes:180, location:'', status:'completed',
  deducted:false, charged:true, memo:'', settledAt:'' });
state.sessions.push({ id:'x3', memberId:v.id, packageId:'', guestName:'', lessonKind:'field', separatePay:true,
  fee:300000, date:'2026-12-03', startTime:'08:00', durationMinutes:180, location:'', status:'excused_cancel',
  deducted:false, charged:false, memo:'', settledAt:'' });
eq('5-1 일반취소는 이용 횟수에서 빠짐', sepUsage(v.id).count, 2);
var rows = memberRowsHTML(state.members);
contain('5-2 수강권 없음 표시', rows, '수강권 없음');
contain('5-3 별도 이용 횟수 배지', rows, '별도 2회');
contain('5-4 줄 요약에 별도 레슨', rows, '별도 레슨 2회');
notContain('5-5 NaN 없음', rows, 'NaN');
notContain('5-6 undefined 없음', rows, 'undefined');
/* 수강권 있는 회원 줄은 그대로 잔여/전체 */
contain('5-7 기존 회원 잔여 표시', rows, '5<small>/8회</small>');

/* 정렬 3종 모두 안전 */
ui.search = '';
['remaining', 'name', 'remaining-asc'].forEach(function(mode){
  state.memberSort = mode;
  var list = filteredMembers();
  var names = list.map(function(x){ return x.name; }).join(',');
  ok('5-8 정렬 ' + mode + ' 에서 전원 유지', list.length === 2, names);
  notContain('5-9 정렬 ' + mode + ' NaN 없음', memberRowsHTML(list), 'NaN');
});

/* ========== 6. 회원 정보창 ========== */
resetDOM(); state = baseState();
var v6 = ensureMemberForGuest('최유진');
state.sessions.push({ id:'y1', memberId:v6.id, packageId:'', guestName:'', lessonKind:'onepoint', separatePay:true,
  fee:90000, date:'2026-12-04', startTime:'19:00', durationMinutes:60, location:'분당 실내연습장',
  status:'completed', deducted:false, charged:true, memo:'', settledAt:'' });
memberCtx = { memberId:v6.id, noteDate:'2026-12-04', draft:'', tagFilter:'전체' };
var body = memberBodyHTML(v6);
contain('6-1 별도 레슨 섹션', body, '별도 레슨');
contain('6-2 이용 횟수·금액', body, '1회');
contain('6-3 종류 표시', body, '원포인트');
contain('6-4 수강권 없음 안내 + 전환', body, '+ 수강권 추가');
contain('6-5 기록은 그대로 남는다는 안내', body, '수강권을 추가해도 이 기록은 그대로');
notContain('6-6 NaN 없음', body, 'NaN');

/* 수강권을 나중에 끊어도 별도 기록 유지 */
state.packages.push({ id:'p9', memberId:v6.id, durationMinutes:55, totalSessions:8, remainingSessions:8,
  startDate:'2026-12-05', expiryDate:'9999-12-31', price:800000, note:'' });
eq('6-7 수강권 추가 후 잔여', totalRemaining(v6.id), 8);
eq('6-8 별도 기록 그대로', sepUsage(v6.id).count, 1);
var body2 = memberBodyHTML(v6);
contain('6-9 수강권과 별도 레슨이 함께', body2, '별도 레슨');

/* ========== 7. 데모 데이터 ========== */
resetDOM(); state = buildDemo();
var demo = findMemberByName('최유진');
ok('7-1 수강권 없이 원포인트로 다닌 데모 회원', !!demo && memberPkgs(demo.id).length === 0);
eq('7-2 별도 이용 1회', demo ? sepUsage(demo.id).count : -1, 1);
notContain('7-3 데모 회원목록에 NaN 없음', memberRowsHTML(state.members), 'NaN');

JSON.stringify(RESULT);
"""

ctx = quickjs.Context()
data = json.loads(ctx.eval(STUBS + CODE + HARNESS))
fails = [r for r in data if not r['pass']]
for r in data:
    print(('PASS ' if r['pass'] else 'FAIL ') + r['name'] + ('' if r['pass'] else '  [' + r['detail'] + ']'))
print('%d passed / %d total' % (len(data) - len(fails), len(data)))
if fails:
    sys.exit(1)

checks = []
def ok(c, n):
    checks.append((bool(c), n))
ok('function ensureMemberForGuest(name){' in HTML, '8-1 방문 회원 보존 함수')
ok('function sepUsage(memberId){' in HTML, '8-2 별도 이용 집계 함수')
ok("'<span class=\"tagsep\">별도 ' + us.count + '회</span>'" in HTML, '8-3 회원목록 배지')
ok('별도 레슨 <b>' in HTML, '8-4 회원 정보창 안내')
ok('+ 수강권 추가</button>' in HTML, '8-5 수강권 추가 버튼 이름')
for c, n in checks:
    print(('PASS ' if c else 'FAIL ') + n)
failed = [n for c, n in checks if not c]
if failed:
    print('\n%d FAILED (HTML)' % len(failed))
    sys.exit(1)
print('\nALL %d PASSED' % (len(data) + len(checks)))
