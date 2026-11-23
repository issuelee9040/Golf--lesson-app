#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""캘린더 레슨 카드 '수정' 버튼과 레슨 수정(편집) 흐름 검사.

- 캘린더 날짜별 일정 카드에 [수정] 버튼이 상태 배지 옆에 있고, 상태 배지도 그대로 눌린다
- 수정을 누르면 '레슨 수정' 폼이 기존 값(모드 · 회원/비회원 · 종류 · 날짜 · 시간 · 소요시간 · 장소 · 금액 · 메모)으로 열린다
- 저장하면 state.sessions 의 같은 레슨을 그 자리에서 고친다 (새 레슨이 생기지 않는다)
- 상태(예정·완료 …)와 차감/수입 표시는 그대로 유지된다 (두 번 차감되지 않는다)
- 이미 정산된 레슨은 모드 · 회원 · 수강권을 바꾸려 하면 막고 안내한다
- 상태 시트에서도 '내용 수정' 으로 같은 폼을 열 수 있다
- 두 테마 모두에서 읽히는 색 토큰만 쓴다
"""
import json, re, sys
import quickjs

HTML = open('/workspace/golf-lesson-app/prototype.html', encoding='utf-8').read()
_raw = HTML.replace('<!doctype html>', '').replace('<!DOCTYPE html>', '')
scripts = re.findall(r'<script>(.*?)</script>', _raw, re.S)
CODE = max(scripts, key=len)
CODE = CODE.replace("(function(){\n'use strict';\n", '', 1).rstrip()
assert CODE.endswith('})();')
CODE = CODE[:-len('})();')]

STUBS = r"""
/* ---------- DOM 스텁 ---------- */
var registry = {};
function mkEl(tag, attrs){
  var set = {};
  var q = {};
  var e = {
    tagName:(tag || 'div').toUpperCase(), _attrs: attrs || {}, id:'', value:'', innerHTML:'', textContent:'',
    children:[], parentNode:null, disabled:false, hidden:false, style:{}, scrollTop:0,
    classList:{
      add:function(n){ set[n] = 1; }, remove:function(n){ delete set[n]; },
      toggle:function(n, f){
        if (f === undefined) { if (set[n]) delete set[n]; else set[n] = 1; }
        else if (f) set[n] = 1; else delete set[n];
      },
      contains:function(n){ return !!set[n]; }
    },
    setAttribute:function(k, v){ e._attrs[k] = v; },
    getAttribute:function(k){ return e._attrs[k] === undefined ? null : e._attrs[k]; },
    removeAttribute:function(k){ delete e._attrs[k]; },
    querySelector:function(sel){ if (!q[sel]) q[sel] = mkEl('div'); return q[sel]; },
    querySelectorAll:function(){ return []; },
    closest:function(){ return e; },
    addEventListener:function(){}, appendChild:function(c){ c.parentNode = e; e.children.push(c); },
    removeChild:function(){}, focus:function(){}, select:function(){}, click:function(){},
    getBoundingClientRect:function(){ return { top:0, left:0, width:0, height:0, right:0 }; }
  };
  return e;
}
function makeEl(){ return mkEl('div'); }
function resetDOM(){ registry = {}; }
var document = {
  getElementById:function(id){ if (!registry[id]) registry[id] = makeEl(); return registry[id]; },
  createElement:function(t){ return mkEl(t); },
  addEventListener:function(){}, body:makeEl(), documentElement:makeEl(),
  querySelector:function(){ return makeEl(); }, querySelectorAll:function(){ return []; }
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

function baseState(){
  var st = { version:2, pro:{ name:'테스트 프로', title:'KPGA', academy:'' }, templates:[],
    members:[], packages:[], sessions:[], settlements:[], notes:[], cancelLog:[], renewalLog:[],
    calendarSync:{ enabled:false, target:'both' } };
  st.members.push({ id:'m1', name:'김민준', gender:'male', region:'분당', phone:'', level:'중급', memo:'', since:'2026-01-01' });
  st.members.push({ id:'m2', name:'박서연', gender:'female', region:'판교', phone:'', level:'초급', memo:'', since:'2026-01-01' });
  st.packages.push({ id:'p1', memberId:'m1', durationMinutes:55, totalSessions:8, remainingSessions:5,
    startDate:'2026-01-01', expiryDate:'9999-12-31', price:800000, note:'' });
  st.packages.push({ id:'p2', memberId:'m1', durationMinutes:25, totalSessions:10, remainingSessions:7,
    startDate:'2026-01-01', expiryDate:'9999-12-31', price:700000, note:'' });
  return st;
}
function sess(o){
  var s = { id:o.id, memberId:o.memberId === undefined ? null : o.memberId, packageId:o.packageId || '',
    date:o.date || '2026-12-03', startTime:o.time || '10:00', durationMinutes:o.dur || 55,
    location:o.loc || '', status:o.status || 'scheduled', deducted:!!o.deducted,
    memo:o.memo || '', settledAt:'', source:'test' };
  if (o.sep) { s.separatePay = true; s.lessonKind = o.kind || 'field'; s.fee = o.fee || 0; s.charged = !!o.charged; s.guestName = o.guest || ''; }
  return s;
}
function world(){
  resetDOM();
  state = baseState();
  state.sessions.push(sess({ id:'sA', memberId:'m1', packageId:'p1', date:'2026-12-03', time:'10:00',
    dur:55, loc:'분당 실내연습장', memo:'드라이버 위주' }));
  state.sessions.push(sess({ id:'sB', memberId:'m1', packageId:'p1', date:'2026-12-04', time:'11:00',
    dur:55, status:'completed', deducted:true }));
  state.sessions.push(sess({ id:'sC', sep:true, kind:'field', guest:'한빛상사 팀', fee:350000,
    date:'2026-12-05', time:'09:00', dur:180, loc:'남서울CC', status:'completed', charged:true }));
  ui.tab = 'calendar'; ui.date = '2026-12-03';
}
function setVal(id, v){ document.getElementById(id).value = v; }
function toastText(){ return document.getElementById('toast').textContent; }

/* ========== 1. 카드에 수정 버튼 ========== */
world();
var cards = dayListHTML('2026-12-03');
contain('1-1 날짜별 카드에 수정 버튼', cards, 'data-act="lesson-edit"');
contain('1-2 버튼 글자는 수정', cards, '>수정<');
contain('1-3 상태 배지는 그대로 상태 시트로', cards, 'class="st st-scheduled"');
contain('1-4 상태 배지도 누를 수 있다', cards, 'class="statetap" data-act="status-sheet"');
ok('1-5 카드 전체가 버튼 하나로 뭉쳐 있지 않다', cards.indexOf('<button class="drow" data-act="status-sheet"') < 0);
contain('1-6 수정 버튼에 레슨 id', cards, 'data-act="lesson-edit" data-sid="sA"');

/* ========== 2. 수정 폼이 기존 값으로 열린다 (수강권 레슨) ========== */
world();
openBookSheet({ edit: 'sA' });
ok('2-1 편집 모드로 열린다', !!bookCtx && bookCtx.editing === 'sA');
eq('2-2 모드 pass', bookCtx.mode, 'pass');
eq('2-3 날짜 유지', bookCtx.date, '2026-12-03');
eq('2-4 시작 시간 유지', bookCtx.time, '10:00');
eq('2-5 회원 유지', bookCtx.memberId, 'm1');
eq('2-6 수강권 유지', bookCtx.pkgId, 'p1');
eq('2-7 소요시간 55분', bookCtx.dur, 55);
eq('2-8 장소 유지', bookCtx.location, '분당 실내연습장');
eq('2-9 메모 유지', bookCtx.memo, '드라이버 위주');
contain('2-10 폼에 회원 수강권이 미리 골라져 있다', bookCtx.sh.body.innerHTML, 'id="bkPkg" value="p1"');
contain('2-11 저장 버튼은 수정 저장', bookCtx.sh.footer.innerHTML, '수정 저장');
eq('2-12 시트 제목은 레슨 수정', bookCtx.sh.sheet.querySelector('h3').textContent, '레슨 수정');
contain('2-13 55분 세그가 켜져 있다', bookCtx.sh.body.innerHTML, 'data-v="55"');
contain('2-14 장소 칸 미리 채움', bookCtx.sh.body.innerHTML, 'value="분당 실내연습장"');

/* ========== 2b. 검사: 수정 중인 레슨 자신과는 겹치지 않는다 ========== */
setVal('bkDate', '2026-12-03'); setVal('bkTime', '10:00');
setVal('bkMember', 'm1'); setVal('bkPkg', 'p1');
validateBook();
notContain('2b-1 자기 자신은 겹침으로 잡지 않는다', document.getElementById('bkWarn').innerHTML, '레슨이 있어요');
ok('2b-2 그래서 수정 저장이 열린다', bookCtx.sh.footer.querySelector('[data-act="book-save"]').disabled === false);
state.sessions.push(sess({ id:'sD', memberId:'m1', packageId:'p1', date:'2026-12-03', time:'10:30', dur:55 }));
validateBook();
contain('2b-3 다른 레슨과 겹치면 그때는 알려 준다', document.getElementById('bkWarn').innerHTML, '레슨이 있어요');
state.sessions.pop();

/* ========== 3. 저장 = 같은 레슨을 그 자리에서 고친다 ========== */
var before = state.sessions.length;
var remainBefore = pkgById('p1').remainingSessions;
setVal('bkDate', '2026-12-10'); setVal('bkTime', '14:30');
setVal('bkLocation', '판교 실내연습장'); setVal('bkMemo', '아이언 · 어프로치');
setVal('bkMember', 'm1'); setVal('bkPkg', 'p1');
saveBooking();
eq('3-1 레슨이 늘지 않는다', state.sessions.length, before);
var a = findSession('sA');
eq('3-2 같은 id 그대로', a.id, 'sA');
eq('3-3 날짜 수정', a.date, '2026-12-10');
eq('3-4 시간 수정', a.startTime, '14:30');
eq('3-5 장소 수정', a.location, '판교 실내연습장');
eq('3-6 메모 수정', a.memo, '아이언 · 어프로치');
eq('3-7 상태는 예정 그대로', a.status, 'scheduled');
ok('3-8 차감 없음 그대로', a.deducted === false);
eq('3-9 수강권 잔여 그대로 (두 번 차감 없음)', pkgById('p1').remainingSessions, remainBefore);
contain('3-10 토스트는 추가가 아니라 수정', toastText(), '수정');
eq('3-11 중복된 옛 레슨이 없다', state.sessions.filter(function(x){ return x.id === 'sA'; }).length, 1);
eq('3-12 수정할 때는 보던 탭(캘린더) 그대로', ui.tab, 'calendar');

/* ========== 4. 소요시간 · 수강권 변경 (아직 차감 전이면 자유) ========== */
world();
openBookSheet({ edit: 'sA' });
bookCtx.dur = 25;
setVal('bkDate', '2026-12-03'); setVal('bkTime', '10:00');
setVal('bkMember', 'm1'); setVal('bkPkg', 'p2');
saveBooking();
var a2 = findSession('sA');
eq('4-1 25분으로 수정', a2.durationMinutes, 25);
eq('4-2 수강권도 25분권으로', a2.packageId, 'p2');
eq('4-3 예정 상태 유지', a2.status, 'scheduled');
eq('4-4 25분권 잔여 그대로', pkgById('p2').remainingSessions, 7);
eq('4-5 55분권 잔여도 그대로', pkgById('p1').remainingSessions, 5);

/* ========== 5. 별도 결제 레슨 수정 ========== */
world();
openBookSheet({ edit: 'sC' });
eq('5-1 별도 결제 모드로 열린다', bookCtx.mode, 'sep');
eq('5-2 종류 field', bookCtx.kind, 'field');
eq('5-3 대상 비회원', bookCtx.target, 'guest');
eq('5-4 팀명 유지', bookCtx.guest, '한빛상사 팀');
eq('5-5 소요시간 180분', bookCtx.sepDur, 180);
eq('5-6 레슨비 유지', bookCtx.fee, '350000');
eq('5-7 장소 유지', bookCtx.location, '남서울CC');
contain('5-8 180분 프리셋 칩이 켜져 있다', bookCtx.sh.body.innerHTML, 'chip on" data-act="bk-sepdur" data-v="180"');
contain('5-9 직접 입력칸은 다시 비어 있다', bookCtx.sh.body.innerHTML, 'value="" placeholder="직접 입력"');
contain('5-10 비회원 이름 미리 채움', bookCtx.sh.body.innerHTML, 'value="한빛상사 팀"');
contain('5-11 레슨비 미리 채움', bookCtx.sh.body.innerHTML, 'value="350000"');

setVal('bkDate', '2026-12-06'); setVal('bkTime', '13:00');
setVal('bkSepDur', '210'); setVal('bkFee', '400000'); setVal('bkLocation', '수원CC');
setVal('bkGuest', '한빛상사 팀');
saveBooking();
var c = findSession('sC');
eq('5-12 날짜 수정', c.date, '2026-12-06');
eq('5-13 소요시간 210분', c.durationMinutes, 210);
eq('5-14 레슨비 400,000', c.fee, 400000);
eq('5-15 상태(완료) 유지', c.status, 'completed');
ok('5-16 수입 포함 표시 유지', c.charged === true);
ok('5-17 별도 결제로 남는다', isSep(c) === true);
eq('5-18 레슨이 늘지 않는다', state.sessions.length, 3);

/* ========== 6. 이미 정산된 레슨: 회원 · 수강권 · 모드 변경은 막는다 ========== */
world();
openBookSheet({ edit: 'sB' });
setVal('bkDate', '2026-12-04'); setVal('bkTime', '11:00');
setVal('bkMember', 'm2'); setVal('bkPkg', 'p1');
saveBooking();
contain('6-1 회원 변경은 안내하고 막는다', toastText(), '회원은 바꿀 수 없어요');
eq('6-2 회원 그대로', findSession('sB').memberId, 'm1');
eq('6-3 상태 그대로', findSession('sB').status, 'completed');
ok('6-4 차감 표시 그대로', findSession('sB').deducted === true);
eq('6-5 잔여 그대로', pkgById('p1').remainingSessions, 5);

world();
openBookSheet({ edit: 'sB' });
setVal('bkDate', '2026-12-04'); setVal('bkTime', '11:00');
setVal('bkMember', 'm1'); setVal('bkPkg', 'p2');
saveBooking();
contain('6-6 수강권 변경도 안내', toastText(), '수강권은 바꿀 수 없어요');
eq('6-7 수강권 그대로', findSession('sB').packageId, 'p1');

/* 정산된 레슨도 날짜 · 시간 · 메모는 고칠 수 있다 */
world();
openBookSheet({ edit: 'sB' });
setVal('bkDate', '2026-12-11'); setVal('bkTime', '18:00'); setVal('bkMemo', '재예약');
setVal('bkMember', 'm1'); setVal('bkPkg', 'p1');
saveBooking();
var b2 = findSession('sB');
eq('6-8 정산된 레슨도 날짜 수정 가능', b2.date, '2026-12-11');
eq('6-9 상태 · 차감 유지', b2.status + '/' + b2.deducted, 'completed/true');
eq('6-10 잔여 그대로', pkgById('p1').remainingSessions, 5);

/* 별도 결제 완료 레슨을 수강권 레슨으로 바꾸는 것도 막는다 */
world();
openBookSheet({ edit: 'sC' });
bookCtx.mode = 'pass';
setVal('bkDate', '2026-12-05'); setVal('bkTime', '09:00');
setVal('bkMember', 'm1'); setVal('bkPkg', 'p1');
saveBooking();
contain('6-11 모드 변경 안내', toastText(), '모드는 바꿀 수 없어요');
ok('6-12 별도 결제 그대로', isSep(findSession('sC')) === true);

/* ========== 7. 새 예약은 그대로 (회귀) ========== */
world();
openBookSheet({});
ok('7-1 새 예약 폼에는 editing 이 없다', !bookCtx.editing);
contain('7-2 저장 버튼은 예약 추가', bookCtx.sh.footer.innerHTML, '예약 추가');
setVal('bkDate', '2026-12-20'); setVal('bkTime', '08:00');
setVal('bkMember', 'm1'); setVal('bkPkg', 'p1'); setVal('bkMemo', '신규');
saveBooking();
eq('7-3 새 레슨이 하나 늘어난다', state.sessions.length, 4);
eq('7-4 새 레슨 상태는 예정', state.sessions[3].status, 'scheduled');
eq('7-5 잔여는 아직 그대로', pkgById('p1').remainingSessions, 5);

/* ========== 8. 상태 시트에서도 내용 수정 ========== */
world();
var stSh = openStatusSheet('sA');
contain('8-1 상태 시트에 내용 수정 버튼', stSh.footer.innerHTML, '✏️ 내용 수정');
contain('8-2 같은 수정 액션', stSh.footer.innerHTML, 'data-act="lesson-edit" data-sid="sA"');

/* ========== 9. 없는 레슨은 조용히 실패 ========== */
world();
var n0 = state.sessions.length;
openBookSheet({ edit: 'nope' });
ok('9-1 없는 레슨이면 폼을 열지 않는다', !bookCtx);
contain('9-2 이유를 알려 준다', toastText(), '찾지 못했어요');
eq('9-3 세션 수 그대로', state.sessions.length, n0);

JSON.stringify(RESULT);
"""

ctx = quickjs.Context()
out = ctx.eval(STUBS + CODE + HARNESS)
data = json.loads(out)
fails = [r for r in data if not r['pass']]
for r in data:
    if not r['pass']:
        print('FAIL ' + r['name'] + ('  [' + r['detail'] + ']' if r['detail'] else ''))
print('%d passed / %d total' % (len(data) - len(fails), len(data)))

# ---------- CSS · 문구 계약 ----------
checks = []
def ck(cond, name):
    checks.append((bool(cond), name))

ck("title: cur ? '레슨 수정' : '레슨 예약'" in HTML, 'C-1 제목은 레슨 수정')
ck("bookCtx.editing ? '수정 저장'" in HTML, 'C-2 저장 버튼 문구')
ck('.drow-main{flex:1;min-width:0' in HTML and '.drow-acts{flex:none' in HTML, 'C-3 카드 구조 (누르는 본문 + 오른쪽 버튼들)')
ck('.editbtn{' in HTML and 'background:var(--field)' in HTML and 'border:1px solid var(--line)' in HTML, 'C-4 수정 버튼은 테마 토큰만 사용')
ck('.statetap{' in HTML, 'C-5 상태 배지도 누를 수 있게')
ck("case 'lesson-edit'" in HTML, 'C-6 수정 액션 처리')
ck("openBookSheet({ edit: eid })" in HTML, 'C-7 수정 액션이 편집 모드로 폼을 연다')
ck('이미 정산된 레슨이라' in HTML, 'C-8 정산된 레슨 안내 문구')
ck("calendarAfterAdd(s);" in HTML and 'if (isNew) {' in HTML, 'C-9 새 예약에만 캘린더 추가 창')
ck(HTML.count('--field:#FFFFFF') >= 1 and HTML.count('--field:#232328') >= 1, 'C-10 두 테마 모두 --field 정의')
ck(HTML.count('--line:#E3E6EB') >= 1 and HTML.count('--line:#2F2F36') >= 1, 'C-11 두 테마 모두 --line 정의')

for c, n in checks:
    if not c:
        print('FAIL ' + n)
print('%d passed / %d total (CSS)' % (sum(1 for c, _ in checks if c), len(checks)))

if fails or any(not c for c, _ in checks):
    sys.exit(1)
print('\nALL PASSED')
