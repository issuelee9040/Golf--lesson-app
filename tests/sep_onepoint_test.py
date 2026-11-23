#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""별도 결제 종류 3가지(필드 · 숏게임 · 원포인트)를 실제 프로토타입 코드로 검사한다.

- `lessonKind: 'onepoint'` 도 별도 결제 레슨으로 인식 · 수강권 미차감
- 예약 시트 · 빠른 추가 시트에 3칸 종류 선택(필드 / 숏게임 / 원포인트)
- 저장 · 카드 배지 · 캘린더 · 카톡 · 수입 정산까지 원포인트가 그대로 흐르는지
- 한 줄 입력에서 `원포인트` 키워드 인식
- 390px 아이폰에서 세 칸이 줄바꿈 없이 들어가는 CSS
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
var RESULT = [];
function ok(name, cond, detail){ RESULT.push({ name:name, pass:!!cond, detail:detail || '' }); }
function eq(name, a, b){ ok(name, a === b, 'got=' + JSON.stringify(a) + ' want=' + JSON.stringify(b)); }
function contain(name, hay, needle){ ok(name, String(hay).indexOf(needle) >= 0, 'needle=' + needle); }

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
  return st;
}

/* ========== 1. 모델 — 원포인트도 별도 결제 ========== */
resetDOM(); state = baseState();
var one = { id:'o1', memberId:'m1', packageId:'', guestName:'', lessonKind:'onepoint', separatePay:true,
  fee:90000, date:'2026-12-05', startTime:'19:00', durationMinutes:60, location:'분당 실내연습장',
  status:'scheduled', deducted:false, charged:false, memo:'', settledAt:'' };
ok('1-1 원포인트도 isSep', isSep(one) === true);
eq('1-2 종류 키', sepKind(one), 'onepoint');
eq('1-3 종류 이름', sepKindName('onepoint'), '원포인트 레슨');
eq('1-4 짧은 이름', sepKindShort('onepoint'), '원포인트');
eq('1-5 배지', sepBadge(one), '💡 원포인트');
eq('1-6 아이콘', sepIcon(one), '💡');
eq('1-7 별도 레슨 상태 4개', statusKeysFor(one).length, 4);
eq('1-8 모르는 종류는 필드로', sepKindName('기타'), '필드 레슨');
eq('1-9 세 종류 순서', SEP_KIND_ORDER.join(','), 'field,shortgame,onepoint');

/* 수강권 잔여는 절대 줄지 않는다 */
state.sessions.push(one);
applyStatus(one, 'completed');
eq('1-10 완료해도 수강권 잔여 그대로', state.packages[0].remainingSessions, 5);
eq('1-11 수입에는 잡힘', one.charged, true);
eq('1-12 차감은 안 됨', one.deducted, false);

/* ========== 2. 예약 시트에서 원포인트 저장 ========== */
resetDOM(); state = baseState();
bookCtx = { sh:{ close:function(){} }, mode:'sep', kind:'onepoint', target:'member', dur:55, sepDur:60,
  date:'2026-12-06', time:'19:00', memberId:'m1', guest:'', fee:'', location:'', memo:'' };
document.getElementById('bkDate').value = '2026-12-06';
document.getElementById('bkTime').value = '19:00';
document.getElementById('bkMember').value = 'm1';
document.getElementById('bkFee').value = '90000';
document.getElementById('bkLocation').value = '분당 실내연습장';
document.getElementById('bkSepDur').value = '60';
saveBooking();
var made = state.sessions[state.sessions.length - 1];
eq('2-1 저장된 종류 onepoint', made.lessonKind, 'onepoint');
eq('2-2 별도 결제', made.separatePay, true);
eq('2-3 금액', made.fee, 90000);
eq('2-4 회원 연결', made.memberId, 'm1');
eq('2-5 수강권 연결 없음', made.packageId, '');
var card = lessonCard(made);
contain('2-6 카드에 원포인트 배지', card, '💡 원포인트');
contain('2-7 카드에 별도 결제 금액', card, '별도 결제');

/* ========== 3. 한 줄 입력에서 '원포인트' 인식 ========== */
resetDOM(); state = baseState();
var p = parseQuickLesson('내일 저녁 7시 원포인트 김민준 60분 9만');
ok('3-1 별도 결제로 인식', p.separate === true);
eq('3-2 종류 onepoint', p.kind, 'onepoint');
eq('3-3 시간', p.time, '19:00');
eq('3-4 소요시간', p.minutes, 60);
eq('3-5 금액 9만', p.fee, 90000);
eq('3-6 회원 이름', p.memberName, '김민준');
ok('3-7 장소에 키워드 안 남음', String(p.location).indexOf('포인트') < 0);

/* 빠른 추가 시트 흐름 전체 */
resetDOM(); state = baseState();
openQuickAddSheet();
document.getElementById('qaLine').value = '내일 저녁 7시 원포인트 김민준 60분 9만';
applyQuickParse();
eq('3-8 모드 별도 결제', qaCtx.mode, 'sep');
eq('3-9 종류 onepoint', qaCtx.kind, 'onepoint');
eq('3-10 금액', qaCtx.fee, '90000');
eq('3-11 소요시간', qaCtx.sepDur, 60);

/* ========== 4. 수입 정산에 원포인트가 따로 잡힌다 ========== */
resetDOM(); state = baseState();
state.sessions.push({ id:'o2', memberId:'m1', packageId:'', guestName:'', lessonKind:'onepoint',
  separatePay:true, fee:90000, date:'2026-12-07', startTime:'19:00', durationMinutes:60,
  location:'', status:'completed', deducted:false, charged:true, memo:'', settledAt:'' });
var r = revenueRange('2026-12-01', '2026-12-31');
eq('4-1 별도 수입 합계', r.sepTotal, 90000);
eq('4-2 별도 건수', r.sepCount, 1);
eq('4-3 종류가 onepoint 로 남음', r.sepRows[0].kind, 'onepoint');
eq('4-4 수강권 수입에는 없음', r.passTotal, 0);
ui = { tab:'stats', date:'2026-12-07', memberId:null, search:'', month:'2026-12', stats:'revenue', revUnit:'month', revOpen:'' };
var rev = viewRevenue();
contain('4-5 화면 구성 카드 문구', rev, '필드 · 숏게임 · 원포인트 별도 수입');
contain('4-6 원포인트 이름', rev, '💡 김민준');

/* ========== 5. 화면 문구 · 배지 클래스 ========== */
contain('5-1 캘린더 제목', calSummary({ lessonKind:'onepoint', memberId:'m1', durationMinutes:60 }), '원포인트 레슨');
var kk = kakaoReportForSession('o2');
contain('5-2 카톡 리포트', kk, '원포인트 레슨 60분');

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

# ---------- HTML / CSS 계약 ----------
checks = []
def ok(c, n):
    checks.append((bool(c), n))

ok('field, shortgame, onepoint 세 종류 정의' in HTML or "'field', 'shortgame', 'onepoint'" in HTML,
   '6-1 SEP_KIND_ORDER 세 종류')
ok('SEP_KIND_ORDER.map(function(k){' in HTML and 'SEP_KINDS[k].short' in HTML,
   '6-2 종류 버튼을 세 칸으로 생성')
ok('class="seg kind3"' in HTML, '6-3 종류 선택 3칸 세그')
ok('.seg.kind3 button{font-size:12.5px;letter-spacing:-.4px;white-space:nowrap}' in HTML,
   '6-4 390px 에서 줄바꿈 없이 한 줄')
ok('.lkind.lk-onepoint{' in HTML and 'html[data-theme="black"] .lkind.lk-onepoint{' in HTML,
   '6-5 원포인트 배지 스타일 두 테마')
ok('>별도 결제</button>' in HTML, '6-6 예약·빠른 추가 모드 토글 문구')
ok('필드 · 숏게임 · 원포인트' in HTML, '6-7 안내 문구에 세 종류')
ok("res.kind = 'onepoint'" in HTML, '6-8 한 줄 입력 파서가 원포인트 인식')
ok('💡 원포인트' in HTML, '6-9 배지 문구')

for c, n in checks:
    print(('PASS ' if c else 'FAIL ') + n)

failed = [n for c, n in checks if not c]
if failed:
    print('\n%d FAILED (HTML/CSS)' % len(failed))
    sys.exit(1)
print('\nALL %d PASSED' % (len(data) + len(checks)))
