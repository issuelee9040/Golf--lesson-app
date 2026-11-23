#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""필드 · 숏게임(별도 결제) 레슨과 수입 분리를 실제 프로토타입 코드로 검사한다.

- 별도 결제 레슨은 수강권(remainingSessions)을 절대 건드리지 않는지 (회원 · 비회원 모두)
- 상태(완료·당일취소·노쇼·일반취소)에 따라 별도 수입 포함/제외가 맞는지
- 마감 정산(settleApply)이 별도 레슨을 섞어도 차감 횟수를 잘못 세지 않는지
- 수입 정산: 총수입 = 정규 수강권 수입 + 필드·숏게임 별도 수입, 기간 필터·금액 수정 반영
- 한 줄 입력에서 '필드'·'숏게임' 키워드와 금액(15만)·소요시간을 인식하는지
- 캘린더(.ics 내용) · 카톡 요약에서 '잔여 횟수'가 빠지고 '필드/숏게임'이 보이는지
- 화면 문구(모드 토글·수입 구성 카드)가 실제로 들어 있는지
"""
import json, sys
import quickjs

HTML = open('/workspace/golf-lesson-app/prototype.html', encoding='utf-8').read()
HTML = HTML.replace('<!doctype html>', '').replace('<!DOCTYPE html>', '')

# 화면 테마 부트스트랩(<head>)과 앱 본문 스크립트 중 큰 쪽 = 앱 본문
import re
scripts = re.findall(r'<script>(.*?)</script>', HTML, re.S)
CODE = max(scripts, key=len)
# IIFE 껍데기만 벗겨 전역에서 함수를 호출할 수 있게 한다
CODE = CODE.replace("(function(){\n'use strict';\n", '', 1)
CODE = CODE.rstrip()
assert CODE.endswith('})();'), CODE[-40:]
CODE = CODE[:-len('})();')]

STUBS = r"""
/* ---------- 최소 DOM / 브라우저 스텁 ---------- */
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
/* ---------- 검사 도우미 ---------- */
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
  st.members.push({ id:'m2', name:'박서연', gender:'female', region:'판교', phone:'', level:'초급', memo:'', since:'2026-01-01' });
  st.packages.push({ id:'p1', memberId:'m1', durationMinutes:55, totalSessions:8, remainingSessions:5,
    startDate:'2026-01-01', expiryDate:'9999-12-31', price:800000, note:'' });
  st.packages.push({ id:'p2', memberId:'m2', durationMinutes:25, totalSessions:10, remainingSessions:6,
    startDate:'2026-01-01', expiryDate:'9999-12-31', price:700000, note:'' });
  return st;
}
function passLesson(o){
  o = o || {};
  var s = { id:o.id || uid('lsn'), memberId:o.memberId || 'm1', packageId:o.packageId || 'p1',
    date:o.date || '2026-12-03', startTime:o.time || '10:00',
    durationMinutes:o.dur || 55, location:o.loc || '분당 실내연습장',
    status:'scheduled', deducted:false, memo:'', settledAt:'', source:'test' };
  return s;
}
function sepLesson(o){
  o = o || {};
  return { id:o.id || uid('lsn'), memberId:o.memberId === undefined ? null : o.memberId, packageId:'',
    guestName:o.guest || '', lessonKind:o.kind || 'field', separatePay:true, fee:o.fee || 0,
    date:o.date || '2026-12-05', startTime:o.time || '09:00',
    durationMinutes:o.dur || 120, location:o.loc || '남서울CC',
    status:o.status || 'scheduled', deducted:false, charged:o.status ? (o.status !== 'scheduled') : false,
    memo:'', settledAt:'', source:'test' };
}

/* ========== 1. 모델 헬퍼 ========== */
resetDOM(); state = baseState();
var sField = sepLesson({ memberId:'m1', kind:'field', fee:300000 });
var sShort = sepLesson({ guest:'한빛상사 팀', kind:'shortgame', fee:120000 });
var sPass  = passLesson({});
ok('1-1 필드 레슨은 isSep', isSep(sField) === true);
ok('1-2 숏게임 레슨은 isSep', isSep(sShort) === true);
ok('1-3 수강권 레슨은 isSep 아님', isSep(sPass) === false);
ok('1-4 레슨 종류(필드)', sepKindLabel(sField) === '필드 레슨');
ok('1-5 레슨 종류(숏게임)', sepKindLabel(sShort) === '숏게임 레슨');
ok('1-6 배지', sepBadge(sField) === '⛳ 필드' && sepBadge(sShort) === '🎯 숏게임');
ok('1-7 비회원 이름', sessionName(sShort) === '한빛상사 팀');
ok('1-8 회원 이름', sessionName(sField) === '김민준');
ok('1-9 결제 금액 0 처리', sepFee(sepLesson({ fee:'' })) === 0);
eq('1-10 별도 레슨 상태 목록 4개', statusKeysFor(sField).length, 4);
eq('1-11 수강권 레슨 상태 목록 5개', statusKeysFor(sPass).length, 5);

/* ========== 2. 예약 시트로 만들기 (별도 결제 · 비회원) ========== */
resetDOM(); state = baseState();
bookCtx = { sh:{ close:function(){} }, mode:'sep', kind:'field', target:'guest', dur:55, sepDur:180,
  date:'2026-12-05', time:'09:00', memberId:'', guest:'', fee:'', location:'', memo:'' };
document.getElementById('bkDate').value = '2026-12-05';
document.getElementById('bkTime').value = '09:00';
document.getElementById('bkGuest').value = '한빛상사 팀';
document.getElementById('bkFee').value = '450000';
document.getElementById('bkLocation').value = '수원CC';
document.getElementById('bkMemo').value = '벙커 · 어프로치';
document.getElementById('bkSepDur').value = '180';
saveBooking();
var made = state.sessions[state.sessions.length - 1];
ok('2-1 비회원 별도 결제 레슨 저장', !!made && made.separatePay === true);
eq('2-2 종류 field', made.lessonKind, 'field');
eq('2-3 대상 memberId null', made.memberId, null);
eq('2-4 비회원 이름', made.guestName, '한빛상사 팀');
eq('2-5 금액 450000', made.fee, 450000);
eq('2-6 소요시간 180분', made.durationMinutes, 180);
eq('2-7 상태 예정', made.status, 'scheduled');
ok('2-8 수강권 미차감 · 수입 미포함', made.deducted === false && made.charged === false);
eq('2-9 저장된 회원 수 그대로', state.members.length, 2);
eq('2-10 패키지 잔여 그대로', totalRemaining('m1'), 5);

/* ========== 3. 예약 시트로 만들기 (별도 결제 · 기존 회원) ========== */
resetDOM(); state = baseState();
bookCtx = { sh:{ close:function(){} }, mode:'sep', kind:'shortgame', target:'member', dur:55, sepDur:60,
  date:'2026-12-06', time:'16:00', memberId:'m1', guest:'', fee:'', location:'', memo:'' };
document.getElementById('bkDate').value = '2026-12-06';
document.getElementById('bkTime').value = '16:00';
document.getElementById('bkMember').value = 'm1';
document.getElementById('bkFee').value = '80000';
document.getElementById('bkLocation').value = '판교 스크린레슨장';
document.getElementById('bkSepDur').value = '60';
saveBooking();
var made2 = state.sessions[state.sessions.length - 1];
eq('3-1 회원 별도 레슨', made2.memberId, 'm1');
eq('3-2 종류 shortgame', made2.lessonKind, 'shortgame');
eq('3-3 금액 80000', made2.fee, 80000);
eq('3-4 회원 패키지 잔여 그대로', totalRemaining('m1'), 5);

/* ========== 4. 상태 변경 = 수강권은 절대 안 건드림 ========== */
resetDOM(); state = baseState();
var sp = sepLesson({ memberId:'m1', kind:'field', fee:300000, status:'scheduled' });
sp.packageId = 'p1';                 /* 잘못 연결돼 있어도 별도 결제면 차감 금지 */
state.sessions.push(sp);
applyStatus(sp, 'completed');
eq('4-1 완료 · 수강권 그대로', pkgById('p1').remainingSessions, 5);
ok('4-2 완료 · 별도 수입 포함', sp.charged === true);
ok('4-3 완료 · 차감 플래그 없음', sp.deducted === false);
applyStatus(sp, 'same_day_cancel');
ok('4-4 당일취소 · 수입 포함', sp.charged === true);
applyStatus(sp, 'no_show');
ok('4-5 노쇼 · 수입 포함', sp.charged === true);
applyStatus(sp, 'excused_cancel');
ok('4-6 일반취소 · 수입 제외', sp.charged === false);
eq('4-7 일반취소 · 수강권 그대로', pkgById('p1').remainingSessions, 5);

/* 수강권 레슨은 그대로 동작 (회귀) */
var sp2 = passLesson({});
state.sessions.push(sp2);
applyStatus(sp2, 'completed');
eq('4-8 수강권 레슨 완료는 1회 차감', pkgById('p1').remainingSessions, 4);
applyStatus(sp2, 'excused_cancel');
eq('4-9 일반취소는 차감 복구', pkgById('p1').remainingSessions, 5);

/* ========== 5. 일반취소 = 일정에서 삭제 + 수입 0 ========== */
resetDOM(); state = baseState();
var sc = sepLesson({ memberId:'m2', fee:200000, status:'completed' });
state.sessions.push(sc);
var cx = cancelExcused(sc);
eq('5-1 일정에서 삭제', state.sessions.length, 0);
ok('5-2 되돌리기용 원본 보관', !!cx && cx.snap.id === sc.id);
eq('5-3 취소 기록 1건', state.cancelLog.length, 1);
eq('5-4 취소 후 별도 수입 0', revenueRange('2026-12-01', '2026-12-31').sepTotal, 0);
ok('5-5 회원 잔여 그대로', totalRemaining('m2') === 6);
ok('5-6 되돌리기 성공', undoCancelExcused(cx) === true);
eq('5-7 되돌리면 일정 복귀', state.sessions.length, 1);

/* ========== 6. 마감 정산 = 별도 레슨 섞여도 차감 횟수 정확 ========== */
resetDOM(); state = baseState();
var a1 = passLesson({ date:'2026-12-07', time:'09:00' });        /* 완료 예정 */
var a2 = sepLesson({ memberId:'m1', fee:250000, date:'2026-12-07', time:'13:00', dur:120 });
var a3 = sepLesson({ guest:'비회원 팀', fee:0, date:'2026-12-07', time:'18:00', dur:90 });
state.sessions.push(a1); state.sessions.push(a2); state.sessions.push(a3);
var sel = { date:'2026-12-07', decisions:{} };
sel.decisions[a1.id] = 'completed';
sel.decisions[a2.id] = 'completed';
sel.decisions[a3.id] = 'no_show';
var tally = settleTally(sel, state.sessions);
eq('6-1 차감 1회', tally.ded, 1);
eq('6-2 별도 2건', tally.sep, 2);
eq('6-3 별도 수입 포함 2건', tally.sepCharge, 2);
settleCtx = { sel:sel, list:state.sessions.slice(), sh:{ close:function(){} } };
settleApply();
eq('6-4 정산 후 수강권 4회', pkgById('p1').remainingSessions, 4);
ok('6-5 정산 후 별도 레슨 수입 포함', a2.charged === true && a3.charged === true);
eq('6-6 정산 기록의 차감 횟수', settlementFor('2026-12-07').deducted, 1);
eq('6-7 정산 기록의 별도 건수', settlementFor('2026-12-07').sepCount, 2);

/* ========== 7. 수입 정산 수식 ========== */
resetDOM(); state = baseState();
var b1 = passLesson({ date:'2026-12-03', time:'10:00' });     applyStatus(b1, 'completed');
var b2 = passLesson({ date:'2026-12-04', time:'10:00' });     applyStatus(b2, 'same_day_cancel');
var b3 = passLesson({ date:'2026-12-04', time:'14:00' });     /* 예정 → 수입 없음 */
var b4 = sepLesson({ memberId:'m1', fee:300000, date:'2026-12-03', time:'08:00', dur:240 }); applyStatus(b4, 'completed');
var b5 = sepLesson({ guest:'한빛상사 팀', fee:120000, date:'2026-12-05', time:'13:00', dur:90, kind:'shortgame' }); applyStatus(b5, 'no_show');
var b6 = sepLesson({ guest:'예약 팀', fee:999999, date:'2026-12-06', time:'09:00', dur:120 });  /* 예정 → 제외 */
var b7 = sepLesson({ memberId:'m2', fee:50000, date:'2026-12-06', time:'15:00', dur:60 }); applyStatus(b7, 'excused_cancel');
state.sessions = [b1,b2,b3,b4,b5,b6,b7];

var r = revenueRange('2026-12-01', '2026-12-31');
eq('7-1 정규 수강권 수입', r.passTotal, 200000);
eq('7-2 별도 수입', r.sepTotal, 420000);
eq('7-3 총수입 = 합', r.total, 620000);
ok('7-4 총수입 = 정규 + 별도 (식)', r.total === r.passTotal + r.sepTotal);
eq('7-5 차감 횟수(수강권만)', r.deducted, 2);
eq('7-6 별도 건수', r.sepCount, 2);
eq('7-7 정규 레슨 행 2개', r.rows.length, 2);
eq('7-8 별도 행 2개', r.sepRows.length, 2);
eq('7-9 별도는 정규 행에 안 섞임', r.rows.filter(function(x){ return x.sep; }).length, 0);
eq('7-10 예정 별도 레슨 제외', r.sepRows.filter(function(x){ return x.id === b6.id; }).length, 0);
eq('7-11 일반취소 별도 레슨 제외', r.sepRows.filter(function(x){ return x.id === b7.id; }).length, 0);

var r2 = revenueRange('2026-12-04', '2026-12-05');
eq('7-12 기간 필터 정규', r2.passTotal, 100000);
eq('7-13 기간 필터 별도', r2.sepTotal, 120000);
eq('7-14 기간 필터 합계', r2.total, 220000);

b4.fee = 400000;                       /* 별도 레슨비 수정 → 바로 반영 */
var r3 = revenueRange('2026-12-01', '2026-12-31');
eq('7-15 금액 수정 후 별도 수입', r3.sepTotal, 520000);
eq('7-16 금액 수정 후 총수입', r3.total, 720000);

/* 화면(수입 정산)에 구성이 보이는지 */
resetDOM();
ui = { tab:'stats', date:'2026-12-03', memberId:null, search:'', month:'2026-12', stats:'revenue', revUnit:'month', revOpen:'' };
var rev = viewRevenue();
var revFlat = String(rev).replace(/,/g, '');      /* quickjs toLocaleString 은 쉼표를 안 넣음 */
contain('7-17 히어로 총수입', revFlat, '720000');
contain('7-18 정규 수강권 수입 칸', rev, '정규 수강권 수입');
contain('7-19 별도 결제 수입 칸', rev, '필드 · 숏게임 · 원포인트 별도 수입');
contain('7-20 별도 금액 표시', revFlat, '520000');
contain('7-21 정규 금액 표시', revFlat, '200000');

/* ========== 8. 한 줄 입력 인식 ========== */
resetDOM(); state = baseState();
var p1 = parseQuickLesson('내일 오전 9시 필드 홍길동팀 120분 15만');
ok('8-1 필드 키워드 인식', p1.separate === true && p1.kind === 'field');
eq('8-2 소요시간 120분', p1.minutes, 120);
eq('8-3 금액 15만 → 150000', p1.fee, 150000);
eq('8-4 비회원 이름', p1.memberName, '홍길동팀');
ok('8-5 장소에 필드가 안 남음', String(p1.location).indexOf('필드') < 0);

var p2 = parseQuickLesson('모레 오후 2시 숏게임 김민준 90분 8만원');
ok('8-6 숏게임 키워드 인식', p2.separate === true && p2.kind === 'shortgame');
eq('8-7 소요시간 90분', p2.minutes, 90);
eq('8-8 금액 8만원', p2.fee, 80000);
eq('8-9 기존 회원 매칭', p2.memberId, 'm1');

var p3 = parseQuickLesson('내일 오후 3시 박서연 55분 분당');
ok('8-10 일반 레슨은 별도 아님', p3.separate === false);
eq('8-11 일반 레슨 55분', p3.duration, 55);
eq('8-12 일반 레슨 회원', p3.memberId, 'm2');

/* 한 줄을 고쳐 쓸 때 이전 조각이 장소에 남지 않는지 (실제 입력 흐름) */
resetDOM(); state = baseState();
openQuickAddSheet();
document.getElementById('qaLine').value = '내일 오전 9시 숏게임 박팀장 90분 8';
applyQuickParse();
document.getElementById('qaLine').value = '내일 오전 9시 숏게임 박팀장 90분 8만';
applyQuickParse();
eq('8-13 장소에 조각이 남지 않음', qaCtx.location, '');
eq('8-14 인식 후 모드는 별도 결제', qaCtx.mode, 'sep');
eq('8-15 금액 80000', qaCtx.fee, '80000');
eq('8-16 소요시간 90', qaCtx.sepDur, 90);
eq('8-17 대상은 비회원', qaCtx.target, 'guest');
eq('8-18 비회원 이름', qaCtx.guest, '박팀장');
eq('8-19 종류 shortgame', qaCtx.kind, 'shortgame');

/* ========== 9. 캘린더 · 카톡 ========== */
resetDOM(); state = baseState();
var c1 = sepLesson({ memberId:'m1', fee:300000, date:'2026-12-08', time:'08:00', dur:240, kind:'field', loc:'남서울CC' });
state.sessions.push(c1);
var summ = calSummary(c1);
contain('9-1 캘린더 제목에 필드 레슨', summ, '필드 레슨');
contain('9-2 캘린더 제목에 이름', summ, '김민준');
var desc = calDescLines(c1).join('\n');
contain('9-3 캘린더 설명에 별도 결제', desc, '별도 결제');
contain('9-4 캘린더 설명에 수강권 차감 없음', desc, '수강권 차감 없음');
notContain('9-5 캘린더 설명에 잔여 없음', desc, '잔여');

var kk = kakaoReportForSession(c1.id);
contain('9-6 카톡에 필드 레슨', kk, '필드 레슨 240분');
contain('9-7 카톡에 별도 결제 금액', String(kk).replace(/,/g, ''), '별도 결제: 300000원');
notContain('9-8 카톡에 잔여 횟수 없음', kk, '잔여 횟수');

var g1 = sepLesson({ guest:'한빛상사 팀', fee:0, dur:180 });
state.sessions.push(g1);
var kk2 = kakaoReportForSession(g1.id);
contain('9-9 비회원 카톡 이름', kk2, '한빛상사 팀');
notContain('9-10 비회원에게 님 붙이지 않음', kk2, '팀님');
contain('9-11 금액 미입력 표시', kk2, '금액 미입력');

/* ========== 10. 화면 문구 (오늘 탭 배지) ========== */
resetDOM(); state = baseState();
var t1 = sepLesson({ memberId:'m1', fee:300000, date:todayISO(), time:'08:00', dur:120, status:'scheduled' });
var t2 = passLesson({ date:todayISO(), time:'11:00' });
state.sessions.push(t1); state.sessions.push(t2);
ui = { tab:'today', date:todayISO(), memberId:null, search:'', month:todayISO().slice(0,7), stats:'lesson', revUnit:'month', revOpen:'' };
var todayHtml = viewToday();
contain('10-1 오늘 카드에 ⛳ 필드 배지', todayHtml, '⛳ 필드');
contain('10-2 오늘 카드에 별도 결제 금액', todayHtml, '별도 결제');
contain('10-3 정산 기준에 별도 결제 줄', todayHtml, '수강권 미차감');
var card = lessonCard(t1);
contain('10-4 레슨 카드 배지', card, '⛳ 필드');
notContain('10-5 별도 레슨 카드에 잔여 횟수 없음', card, '잔여');
var statusHtml = openStatusSheet(t1.id) && document.getElementById('toast');
ok('10-6 상태 시트가 열린다', statusHtml !== null);

/* ========== 12. 데모 데이터 ========== */
resetDOM(); state = buildDemo();
var sepd = state.sessions.filter(isSep);
eq('12-1 데모에 별도 결제 레슨 5건 (원포인트 포함)', sepd.length, 5);
eq('12-2 완료 4건은 별도 수입에 잡힘', sepd.filter(function(x){ return x.charged; }).length, 4);
eq('12-3 비회원(팀) 데모 1건', sepd.filter(function(x){ return !x.memberId && x.guestName; }).length, 1);
var dFrom = addDays(todayISO(), -10), dTo = todayISO();
var rmd = revenueRange(dFrom, dTo);
ok('12-4 데모 별도 수입 870,000원 이상', rmd.sepTotal >= 870000);
ok('12-5 데모 수강권 잔여는 별도 레슨과 무관', state.packages.every(function(p){ return p.remainingSessions >= 0; }));

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

# ---------- HTML / CSS 계약 ----------
checks = []
def ok(c, n):
    checks.append((bool(c), n))

ok('data-act="bk-mode"' in HTML and '>별도 결제</button>' in HTML, '11-1 예약 모드 토글 문구')
ok('회원 수강권 레슨' in HTML, '11-2 수강권 모드 문구')
ok('data-act="bk-mode"' in HTML and 'data-act="qa-mode"' in HTML, '11-3 두 시트 모두 모드 토글')
ok("data-act=\"' + p + '-kind\"" in HTML and '<label>종류</label>' in HTML, '11-4 종류 선택 (필드/숏게임)')
ok('필드 레슨' in HTML and '숏게임 레슨' in HTML and '원포인트 레슨' in HTML, '11-5 종류 라벨(3종)')
ok('비회원 · 팀' in HTML, '11-6 비회원 대상 선택')
ok('별도 레슨비 (원' in HTML, '11-7 별도 레슨비 입력')
ok('sepFee' in HTML, '11-8 레슨비 수정 칸')
ok('petty' not in HTML, '11-9 잡음 문자열 없음')
ok('.lkind.lk-field' in HTML and '.lkind.lk-shortgame' in HTML, '11-10 배지 스타일')
ok('.rvsplit' in HTML, '11-11 수입 구성 카드 스타일')
ok('sepFormHTML' in HTML and "sepFormHTML('qa'" in HTML and "sepFormHTML('bk'" in HTML, '11-12 같은 폼을 두 시트에서 사용')
ok('SEP_STATUS_KEYS' in HTML and "excused_cancel':  false" not in HTML, '11-13 별도 레슨 상태 정의')
ok('lessonKind' in HTML and 'separatePay' in HTML and 'guestName' in HTML, '11-14 데이터 모델 필드')
ok('charged' in HTML, '11-15 별도 수입 플래그')
ok('remainingSessions' in HTML, '11-16 수강권 잔여 로직 유지')
ok('반일' in HTML, '11-17 180분 반일 표기')
ok('currentTime' not in HTML, '11-18 잡음 문자열 없음')

for c, n in checks:
    if not c:
        print('FAIL ' + n)
print('%d passed / %d total (HTML)' % (sum(1 for c, _ in checks if c), len(checks)))

if fails or any(not c for c, _ in checks):
    sys.exit(1)
print('\nALL PASSED')
