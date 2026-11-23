#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""여러 줄 회원 일괄 등록 · 진행 중 횟수(4/10회 · 잔여 4회 · 회당 7만원) 검사.

- 파서: 남은 횟수·전체 횟수·총액·회당 단가를 실제 코드로 계산하는지
- parseMemberLines: 카톡·메모·엑셀 붙여넣기(줄바꿈·불릿·번호)를 한 명씩 나누는지
- saveMembersBulk: 미리보기에서 '등록'인 줄만 1탭에 회원 + 수강권으로 저장되는지
- saveMember: 한 줄 모드에서도 '남은 횟수'가 수강권 잔여로 들어가는지
- 화면: 16px textarea · 미리보기 목록 · 남은 횟수 칸 · 일괄 버튼 문구
"""
import re, sys, json
import quickjs

HTML = open('/workspace/golf-lesson-app/prototype.html', encoding='utf-8').read()
SPEC = open('/workspace/golf-lesson-app/spec.md', encoding='utf-8').read()
OUT = []

def ok(name, cond, detail=''):
    OUT.append((name, bool(cond), detail))

# ── 소스 구간 ────────────────────────────────────────────
PARSE = HTML[HTML.index('/* =========================================================\n   한 줄 간편 입력 파서'):
             HTML.index('/* =========================================================\n   화면 렌더')]
ADD = HTML[HTML.index('function quickValidRows('):
           HTML.index('/* =========================================================\n   수강권 추가')]

HARNESS = r"""
var TODAY = '2026-11-23';
function todayISO(){ return TODAY; }
function durName(d){ return d === 25 ? '25분' : '55분'; }
function money(n){
  if (n === '' || n === null || n === undefined) return '-';
  return String(Math.round(Number(n))).replace(/\B(?=(\d{3})+(?!\d))/g, ',') + '원';
}
function esc(s){ return String(s === null || s === undefined ? '' : s); }
function addMonths(s, n){ return '2027-05-23'; }
var uidSeq = 0;
function uid(p){ uidSeq++; return (p || 'id') + '_' + uidSeq; }
var state = { members: [], packages: [], sessions: [] };
function findMemberByName(name){
  for (var i = 0; i < state.members.length; i++) if (state.members[i].name === name) return state.members[i];
  return null;
}
function memberById(id){ for (var i = 0; i < state.members.length; i++) if (state.members[i].id === id) return state.members[i]; return null; }
var saved = 0, rendered = 0, toastMsg = '', openedMember = '';
function save(){ saved++; }
function render(){ rendered++; }
function toast(m){ toastMsg = m; }
function openMemberSheet(id){ openedMember = id; }
var addCtx = null;
var memberCtx = null;
var ui = { tab: 'today' };
var FIELDS = {};
var document = {
  getElementById: function(id){
    var el = FIELDS[id] || null;
    if (el && !el.focus) el.focus = function(){};
    return el;
  }
};
function setGenderUI(){}
function setDurUI(){}
function syncPickLabel(){}
function updateUnit(){}
""" + PARSE + ADD + r"""

var fails = [], log = [];
function ok(c, n){ if (c) log.push('PASS ' + n); else fails.push('FAIL ' + n); }
function eq(a, b, n){ ok(a === b, n + (a === b ? '' : '  got=[' + a + '] want=[' + b + ']')); }

/* ── 1. 진행 중 횟수 · 금액 파싱 ─────────────────────── */
function P(t){ return parseMemberLine(t); }
var p;

p = P('김민수 4/10회 80만원');
eq(p.name, '김민수', '1-1 4/10회 이름');
eq(p.total, 10, '1-2 4/10회 → 전체 10회');
eq(p.rem, 4, '1-3 4/10회 → 잔여 4회');
eq(p.price, 800000, '1-4 80만원 → 800,000원');
eq(p.perLesson, 80000, '1-5 회당 8만원 자동 계산');

p = P('김민수 10회중 4회남음 80만');
eq(p.total, 10, '2-1 10회중 4회남음 → 전체 10회');
eq(p.rem, 4, '2-2 10회중 4회남음 → 잔여 4회');
eq(p.price, 800000, '2-3 "80만" 도 금액으로');

p = P('김민수 10회 중 4회 남음');
eq(p.total, 10, '3-1 띄어 쓴 10회 중 4회 남음 · 전체');
eq(p.rem, 4, '3-2 띄어 쓴 10회 중 4회 남음 · 잔여');

p = P('박영희 잔여 4회');
eq(p.total, 4, '4-1 잔여 4회만 적으면 전체 4회');
eq(p.rem, 4, '4-2 잔여 4회만 적으면 잔여 4회');
eq(p.price, 0, '4-3 금액은 비워 둠');

p = P('박영희 4회 남음');
eq(p.total, 4, '5-1 "4회 남음" 전체');
eq(p.rem, 4, '5-2 "4회 남음" 잔여');

p = P('김민수 4회남음');
eq(p.total, 4, '6-1 붙여 쓴 4회남음');

p = P('정민재 회당 7만원 8회');
eq(p.perLesson, 70000, '7-1 회당 7만원 단가');
eq(p.total, 8, '7-2 횟수 8회');
eq(p.price, 560000, '7-3 총액 = 회당 × 횟수');
eq(p.rem, 8, '7-4 잔여는 전체와 같음');

p = P('정민재 회당 70000 8회');
eq(p.perLesson, 70000, '8-1 회당 70000(단위 없이)');
eq(p.price, 560000, '8-2 단가만으로 총액 계산');

p = P('한지민 8회 560,000원 여 수원');
eq(p.price, 560000, '9-1 쉼표 금액');
eq(p.perLesson, 70000, '9-2 회당 자동 계산');
eq(p.gender, 'female', '9-3 성별');
eq(p.region, '수원', '9-4 지역');

p = P('오세훈 3/20회 1,200,000원 남');
eq(p.total, 20, '10-1 3/20회 전체 20회');
eq(p.rem, 3, '10-2 3/20회 잔여 3회');
eq(p.price, 1200000, '10-3 1,200,000원');

p = P('김민수 4/10회');
eq(p.total, 10, '11-1 금액 없이도 4/10회');
eq(p.rem, 4, '11-2 금액 없이도 잔여 4회');
eq(p.price, 0, '11-3 금액 비어 있으면 0');

p = P('김민수 11/24 예약');
ok(!(p.total === 24 && p.rem === 11), '12-1 날짜처럼 보이는 11/24 는 횟수로 읽지 않음');

/* ── 2. 기존 한 줄 입력 회귀 ─────────────────────────── */
p = P('김민준 55분 10회 남 분당');
eq(p.name, '김민준', '13-1 기존 예시 이름');
eq(p.duration, 55, '13-2 기존 예시 55분');
eq(p.total, 10, '13-3 기존 예시 10회');
eq(p.rem, 10, '13-4 그냥 10회면 잔여 10회');
eq(p.gender, 'male', '13-5 기존 예시 남');
eq(p.region, '분당', '13-6 기존 예시 분당');
eq(p.price, 0, '13-7 금액 없음');

p = P('이서연, 25분 8회권, 여, 판교');
eq(p.duration, 25, '14-1 25분');
eq(p.total, 8, '14-2 8회권');
eq(p.price, 0, '14-3 금액 없음');

p = P('최윤아 12회 55분 여성 잠실 초급');
eq(p.level, '초급', '15-1 레벨');
eq(p.total, 12, '15-2 12회');

/* ── 3. 여러 줄 나누기 ───────────────────────────────── */
var rows = parseMemberLines('김민수 4/10회 80만원\n박영희 잔여 4회\n\n- 이서연 55분 8회 여 판교\n1) 정민재 회당 7만원 8회\n  \n');
eq(rows.length, 4, '16-1 빈 줄·불릿·번호를 걷어내고 4명');
eq(rows[0].name, '김민수', '16-2 첫 줄 이름');
eq(rows[0].rem, 4, '16-3 첫 줄 잔여');
eq(rows[1].total, 4, '16-4 둘째 줄 잔여만');
eq(rows[2].name, '이서연', '16-5 불릿 줄 이름');
eq(rows[2].region, '판교', '16-6 불릿 줄 지역');
eq(rows[3].price, 560000, '16-7 번호 줄 회당 계산');
eq(parseMemberLines('회원 명단\n김민수 4/10회').length, 2, '17-1 제목 줄은 남고 이름 없는 줄은 배치에서 제외');
eq(parseMemberLines('').length, 0, '17-2 빈 입력');
eq(parseMemberLines('김민수 4/10회\r\n박영희 4회 남음').length, 2, '17-3 CRLF 줄바꿈');

/* ── 4. 일괄 저장 ────────────────────────────────────── */
state.members = []; state.packages = []; toastMsg = ''; FIELDS = {};
addCtx = { sh: { close: function(){ addCtx = null; } }, editing: false,
  rows: parseMemberLines('김민수 4/10회 80만원\n박영희 잔여 4회\n김민수 10회\n이서연 55분 8회 여 판교'), bulk: true };
saveMembersBulk();
eq(state.members.length, 3, '18-1 중복 이름 1줄 제외 → 3명');
eq(state.members[0].name, '김민수', '18-2 첫 회원 이름');
eq(state.packages[0].totalSessions, 10, '18-3 첫 수강권 전체 10회');
eq(state.packages[0].remainingSessions, 4, '18-4 첫 수강권 잔여 4회');
eq(state.packages[0].price, 800000, '18-5 첫 수강권 금액');
eq(state.packages[1].remainingSessions, 4, '18-6 잔여만 적은 회원도 4회');
eq(state.packages[1].price, 0, '18-7 금액 없는 회원은 0원');
eq(state.members[1].region, '', '18-8 지역 없으면 비움');
eq(state.members[2].region, '판교', '18-9 셋째 회원 지역');
eq(state.members[2].gender, 'female', '18-10 셋째 회원 성별');
eq(state.packages[2].durationMinutes, 55, '18-11 기본 55분');
ok(toastMsg.indexOf('3명') >= 0 && toastMsg.indexOf('건너뜀') >= 0, '18-12 토스트에 등록 수·건너뛴 수');

state.members = []; state.packages = []; toastMsg = '';
addCtx = { sh: { close: function(){ addCtx = null; } }, editing: false,
  rows: parseMemberLines('김민수 4/10회\n박영희 4회 남음'), bulk: true };
saveMembersBulk();
eq(state.members.length, 2, '19-1 두 명 일괄 등록');
eq(state.packages[0].remainingSessions, 4, '19-2 잔여 반영');
eq(state.packages[0].totalSessions, 10, '19-3 총 횟수 반영');

state.members = []; state.packages = []; toastMsg = '';
addCtx = { sh: { close: function(){ addCtx = null; } }, editing: false, rows: parseMemberLines('김민수'), bulk: true };
saveMembersBulk();
eq(state.members.length, 1, '20-1 횟수 없이 이름만 → 기본 10회');
eq(state.packages[0].totalSessions, 10, '20-2 기본 10회');
eq(state.packages[0].remainingSessions, 10, '20-3 잔여 10회');

state.members = [{ id: 'm1', name: '김민수' }]; state.packages = []; toastMsg = '';
addCtx = { sh: { close: function(){} }, editing: false, rows: parseMemberLines('김민수 4/10회'), bulk: true };
saveMembersBulk();
eq(state.members.length, 1, '21-1 이미 있는 이름만 있으면 아무것도 안 늘어남');
ok(toastMsg.indexOf('없어요') >= 0, '21-2 안내 토스트');

/* ── 5. 한 줄 모드 저장 (남은 횟수) ──────────────────── */
state.members = []; state.packages = []; FIELDS = {};
addCtx = { sh: { close: function(){ addCtx = null; } }, editing: false, duration: 55, gender: 'male', rows: [], bulk: false };
FIELDS = {
  mfName: { value: '김민수' }, mfRegion: { value: '분당' }, mfPhone: { value: '' },
  mfLevel: { value: '' }, mfMemo: { value: '' }, mfSessions: { value: '10' },
  mfRemain: { value: '4' }, mfStart: { value: '2026-11-23' }, mfMonths: { value: '6' },
  mfPrice: { value: '800000' }
};
saveMember();
eq(state.members.length, 1, '22-1 한 줄 모드 회원 1명');
eq(state.packages[0].totalSessions, 10, '22-2 총 10회');
eq(state.packages[0].remainingSessions, 4, '22-3 남은 횟수 4회로 등록');
eq(state.packages[0].price, 800000, '22-4 금액 저장');
eq(state.members[0].gender, 'male', '22-5 성별 저장');

state.members = []; state.packages = []; FIELDS = {};
addCtx = { sh: { close: function(){ addCtx = null; } }, editing: false, duration: 55, gender: '', rows: [], bulk: false };
FIELDS = {
  mfName: { value: '박영희' }, mfRegion: { value: '' }, mfPhone: { value: '' },
  mfLevel: { value: '' }, mfMemo: { value: '' }, mfSessions: { value: '8' },
  mfRemain: { value: '' }, mfStart: { value: '' }, mfMonths: { value: '6' }, mfPrice: { value: '' }
};
saveMember();
eq(state.packages[0].remainingSessions, 8, '23-1 남은 횟수를 비우면 전체 8회');
eq(state.packages[0].price, 0, '23-2 금액 비우면 0');

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

# ── 6. 화면 구조 (문자열 검사) ───────────────────────────
def chk(name, cond, detail=''):
    OUT.append((name, bool(cond), detail))

chk('24-1 한 줄 입력이 16px textarea', re.search(r'<textarea class="input" id="quickLine" rows="3"', HTML) is not None)
chk('24-2 textarea 가 .input 16px 규칙을 탐', 'input,select,textarea{font:inherit;color:inherit;border-radius:0;font-size:16px}' in HTML)
chk('24-3 미리보기 목록 자리', 'id="quickList"' in HTML and '.quicklist{' in HTML)
chk('24-4 미리보기 줄 스타일', '.qlrow{' in HTML and '.qlb.on{' in HTML)
chk('24-5 남은 횟수 입력칸', 'id="mfRemain"' in HTML)
chk('24-6 남은 횟수 안내', 'id="mfRemainHint"' in HTML)
chk('24-7 폼을 감싸 일괄일 때 숨김', HTML.count('<div id="addForm">') == 1 and "form.style.display = bulk ? 'none' : ''" in HTML)
chk('24-8 버튼 문구가 일괄 인원수로 바뀜', "'명 한꺼번에 추가'" in HTML and '새로 등록할 줄이 없어요' in HTML)
chk('24-9 여러 줄 예시 칩', 'QUICK_BULK_EXAMPLE' in HTML and '3명 한꺼번에' in HTML)
chk('24-10 placeholder 가 여러 줄 예시', '김민수 4/10회 80만원&#10;박영희 잔여 4회' in HTML)
chk('24-11 회원목록 카드 문구', '여러 줄 붙여넣기 가능' in HTML)
chk('24-12 일괄 저장은 중복 이름을 건너뜀', 'findMemberByName(p.name)' in ADD and 'skipped++' in ADD)
chk('24-13 인식 결과 요약에 잔여·회당', "' 중 잔여 '" in HTML and "' · 회당 '" in HTML)
chk('24-14 spec 에 일괄 등록 규칙', '4/10회' in SPEC and '여러 줄' in SPEC)

for name, cond, detail in OUT:
    print(('PASS ' if cond else 'FAIL ') + name + ('' if cond else '  <- ' + str(detail)))

fails = data['fail'] + ['FAIL ' + n for n, c, d in OUT if not c]
passed = data['pass'] + ['PASS ' + n for n, c, d in OUT if c]
if fails:
    print()
    for l in fails:
        print(l)
    print('\n%d FAILED / %d passed' % (len(fails), len(passed)))
    sys.exit(1)
print('\nALL %d PASSED' % len(passed))
