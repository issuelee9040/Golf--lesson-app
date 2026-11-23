#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""소요시간 직접 입력칸(플레이스홀더) 검사 — 필드·숏게임(별도 결제) 폼.

- 프리셋(60·90·120·180·240)을 고른 상태에서는 직접 입력칸이 비어 있고 '직접 입력' 반투명 안내만 보인다
- 직접 입력칸에 숫자를 넣으면 프리셋 강조가 풀리고 그 값(15~720분)이 소요시간이 된다
- 같은 값을 넣으면 그 프리셋 칩이 켜지고, 프리셋을 누르면 직접 입력칸은 다시 비워진다
- 칸을 지우면 기본 120분으로 돌아와 화면과 값이 어긋나지 않는다
- 프리셋만 골라도 저장되는 소요시간이 0이 되지 않는다 (예약 시트 · 빠른 추가 시트 모두)
- 두 테마 모두에서 읽히는 색(--muted)으로 안내 문구를 그린다
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
/* ---------- DOM 스텁: 칩 행 · 입력칸의 classList 까지 실제로 동작 ---------- */
var registry = {};
function mkEl(tag, attrs){
  var set = {};
  var e = {
    tagName:(tag || 'div').toUpperCase(), _attrs: attrs || {}, id:'', value:'', innerHTML:'', textContent:'',
    children:[], parentNode:null, disabled:false, hidden:false, style:{},
    classList:{
      add:function(n){ set[n] = 1; },
      remove:function(n){ delete set[n]; },
      toggle:function(n, f){
        if (f === undefined) { if (set[n]) delete set[n]; else set[n] = 1; }
        else if (f) set[n] = 1; else delete set[n];
      },
      contains:function(n){ return !!set[n]; }
    },
    setAttribute:function(k, v){ e._attrs[k] = v; },
    getAttribute:function(k){ return e._attrs[k] === undefined ? null : e._attrs[k]; },
    removeAttribute:function(k){ delete e._attrs[k]; },
    querySelector:function(){ return null; },
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

/* 실제 폼과 같은 칩 행 + 직접 입력칸을 만들어 DOM 스텁에 꽂는다 */
function mountDurRow(p, presetChip){
  var row = mkEl('div', { 'class':'chips durchips' });
  for (var i = 0; i < SEP_DURS.length; i++) {
    var d = SEP_DURS[i];
    var b = mkEl('button', { 'data-act': p + '-sepdur', 'data-v': String(d) });
    b.textContent = d + '분' + (d === 180 ? ' (반일)' : '');
    if (presetChip === d) b.classList.add('on');
    row.appendChild(b);
  }
  var inp = mkEl('input', { 'class':'input chipinp', 'placeholder':'직접 입력' });
  inp.id = p + 'SepDur';
  row.appendChild(inp);
  registry[p + 'SepDur'] = inp;
  var btn = mkEl('button', { 'data-act': p + '-save' });
  document.getElementById(p + 'Warn');
  return { row:row, inp:inp, chips:row.children.slice(0, SEP_DURS.length), saveBtn:btn };
}
function chipOn(row){
  var out = [];
  for (var i = 0; i < SEP_DURS.length; i++) if (row.children[i].classList.contains('on')) out.push(SEP_DURS[i]);
  return out;
}

/* ========== 1. 폼 HTML: 비어 있는 칸 + 반투명 안내 ========== */
var h240 = sepFormHTML('bk', { sepDur:240, target:'guest', date:'2026-12-05', time:'09:00' });
contain('1-1 직접 입력칸에 placeholder 가 있다', h240, 'placeholder="직접 입력"');
contain('1-2 친절한 숫자 키패드 (inputmode numeric)', h240, 'inputmode="numeric"');
ok('1-3 프리셋을 고르면 칸은 비어 있다', h240.indexOf('value=""') >= 0, h240.slice(h240.indexOf('SepDur') - 60, h240.indexOf('SepDur') + 120));
notContain('1-4 240 이 미리 채워지지 않는다', h240, 'value="240"');
contain('1-5 고른 프리셋 칩이 켜져 있다', h240, 'class="chip on" data-act="bk-sepdur" data-v="240"');
contain('1-6 칩 5개 + 반일 표기', h240, '180분 (반일)');
contain('1-7 접두사별 id (예약 시트)', h240, 'id="bkSepDur"');
contain('1-8 접두사별 id (빠른 추가 시트)', sepFormHTML('qa', { sepDur:120 }), 'id="qaSepDur"');
contain('1-9 칩 행 전용 클래스', h240, 'class="chips durchips"');
contain('1-10 안내 문구(aria-label)에 분 단위', h240, 'aria-label="소요시간 직접 입력 (분)"');

var h150 = sepFormHTML('bk', { sepDur:150, target:'guest' });
contain('1-11 직접 입력값은 칸에 그대로 보인다', h150, 'value="150"');
ok('1-12 프리셋에 없는 값이면 켜진 칩이 없다', h150.indexOf('class="chip on"') < 0);

var hd = sepFormHTML('bk', { target:'guest' });
kw = 'value=""';
ok('1-13 처음 열면 기본 120분 칩만 켜지고 칸은 빈다',
   hd.indexOf('value=""') >= 0 && hd.indexOf('class="chip on" data-act="bk-sepdur" data-v="120"') >= 0);

/* ========== 2. 읽는 값: 빈 칸이면 고른 프리셋, 숫자가 있으면 직접 입력 ========== */
resetDOM(); state = baseState();
var m = mountDurRow('bk', 180);
bookCtx = { sh:{ close:function(){}, footer:{ querySelector:function(){ return m.saveBtn; } } },
  mode:'sep', kind:'field', target:'guest', dur:55, sepDur:180,
  date:'', time:'', memberId:'', guest:'', fee:'', location:'', memo:'' };
eq('2-1 빈 칸 + 프리셋 180 → 180분', bookSepDurNow(), 180);
m.inp.value = '95';
eq('2-2 직접 입력 95 → 95분', bookSepDurNow(), 95);
m.inp.value = '';
bookCtx.sepDur = 0;
eq('2-3 아무것도 없으면 0 (검사에서 걸러짐)', bookSepDurNow(), 0);

/* ========== 3. 프리셋을 누르면 직접 입력칸이 다시 빈다 ========== */
resetDOM(); state = baseState();
m = mountDurRow('bk', 0);
bookCtx = { sh:{ close:function(){}, footer:{ querySelector:function(){ return m.saveBtn; } } },
  mode:'sep', kind:'field', target:'guest', dur:55, sepDur:150,
  date:'', time:'', memberId:'', guest:'', fee:'', location:'', memo:'' };
m.inp.value = '150';
chipOn(m.row);
onClick({ target: m.chips[2] });                 /* 120분 */
eq('3-1 프리셋 120 으로 바뀐다', bookCtx.sepDur, 120);
eq('3-2 입력칸은 비워져 안내 문구가 보인다', m.inp.value, '');
eq('3-3 켜진 칩은 120 하나', JSON.stringify(chipOn(m.row)), '[120]');
notContain('3-4 비운 뒤에도 칸에 150 이 남지 않는다', m.inp.value, '150');

onClick({ target: m.chips[3] });                 /* 180분 (반일) */
eq('3-5 반일 칩도 같은 방식', JSON.stringify(chipOn(m.row)), '[180]');
eq('3-6 180분으로 읽힌다', bookSepDurNow(), 180);

/* ========== 4. 직접 입력하면 프리셋 강조가 풀린다 ========== */
resetDOM(); state = baseState();
m = mountDurRow('bk', 240);
bookCtx = { sh:{ close:function(){}, footer:{ querySelector:function(){ return m.saveBtn; } } },
  mode:'sep', kind:'field', target:'guest', dur:55, sepDur:240,
  date:'', time:'', memberId:'', guest:'', fee:'', location:'', memo:'' };
eq('4-1 시작: 240 켜짐', JSON.stringify(chipOn(m.row)), '[240]');
m.inp.value = '150';
onFieldChange({ target: m.inp });
eq('4-2 150 을 넣으면 켜진 칩 없음', JSON.stringify(chipOn(m.row)), '[]');
eq('4-3 값은 150', bookCtx.sepDur, 150);
eq('4-4 읽는 값도 150', bookSepDurNow(), 150);
m.inp.value = '90';
onFieldChange({ target: m.inp });
eq('4-5 프리셋과 같은 90 을 넣으면 그 칩만 켜짐', JSON.stringify(chipOn(m.row)), '[90]');
m.inp.value = '';
onFieldChange({ target: m.inp });
eq('4-6 칸을 지우면 기본 120 으로 돌아온다', bookCtx.sepDur, 120);
eq('4-7 화면도 120 칩 하나로 맞춰진다', JSON.stringify(chipOn(m.row)), '[120]');

/* ========== 5. 검사: 15~720분 ========== */
function durWarn(dur){
  resetDOM(); state = baseState();
  var mm = mountDurRow('bk', 0);
  bookCtx = { sh:{ close:function(){}, footer:{ querySelector:function(){ return mm.saveBtn; } } },
    mode:'sep', kind:'field', target:'member', dur:55, sepDur:dur,
    date:'2026-12-09', time:'10:00', memberId:'m1', guest:'', fee:'', location:'', memo:'' };
  document.getElementById('bkDate').value = '2026-12-09';
  document.getElementById('bkTime').value = '10:00';
  document.getElementById('bkMember').value = 'm1';
  mm.inp.value = String(dur);
  validateBook();
  return { warn:document.getElementById('bkWarn').innerHTML, disabled:mm.saveBtn.disabled };
}
var w14 = durWarn(14);
contain('5-1 14분은 안내 + 저장 막힘', w14.warn, '15분 이상');
ok('5-2 14분 저장 버튼 잠김', w14.disabled === true, String(w14.disabled));
var w150 = durWarn(150);
contain('5-3 직접 입력 150분은 통과', w150.warn, '150분');
ok('5-4 150분 저장 가능', w150.disabled === false, String(w150.disabled));
var w720 = durWarn(720);
ok('5-5 720분은 통과', w720.disabled === false, w720.warn);
var w999 = durWarn(999);
contain('5-6 720분 초과는 안내', w999.warn, '720분 이하');
ok('5-7 720분 초과 저장 버튼 잠김', w999.disabled === true, String(w999.disabled));

/* ========== 6. 프리셋만 골라도 저장되는 소요시간이 0 이 아니다 ========== */
resetDOM(); state = baseState();
m = mountDurRow('bk', 240);
bookCtx = { sh:{ close:function(){}, footer:{ querySelector:function(){ return m.saveBtn; } } },
  mode:'sep', kind:'field', target:'guest', dur:55, sepDur:240,
  date:'2026-12-05', time:'09:00', memberId:'', guest:'한빛상사 팀', fee:'350000', location:'남서울CC', memo:'' };
document.getElementById('bkDate').value = '2026-12-05';
document.getElementById('bkTime').value = '09:00';
document.getElementById('bkGuest').value = '한빛상사 팀';
document.getElementById('bkFee').value = '350000';
saveBooking();
var saved = state.sessions[state.sessions.length - 1];
eq('6-1 240분 프리셋으로 저장', saved.durationMinutes, 240);
ok('6-2 별도 결제 레슨으로 남는다', saved.separatePay === true);

resetDOM(); state = baseState();
m = mountDurRow('qa', 60);
qaCtx = { sh:{ close:function(){}, footer:{ querySelector:function(){ return m.saveBtn; } } },
  mode:'sep', kind:'shortgame', target:'guest', duration:55, sepDur:60,
  date:'2026-12-07', time:'15:00', memberId:'', guest:'주말 팀', fee:'90000', location:'판교', parsedName:'', parsed:null };
document.getElementById('qaDate').value = '2026-12-07';
document.getElementById('qaTime').value = '15:00';
document.getElementById('qaGuest').value = '주말 팀';
document.getElementById('qaFee').value = '90000';
saveQuickLesson();
var qs = state.sessions[state.sessions.length - 1];
eq('6-3 빠른 추가도 60분 프리셋으로 저장', qs.durationMinutes, 60);

/* ========== 7. 빠른 추가 시트에서도 직접 입력이 프리셋을 푼다 ========== */
resetDOM(); state = baseState();
m = mountDurRow('qa', 180);
qaCtx = { sh:{ close:function(){}, footer:{ querySelector:function(){ return m.saveBtn; } } },
  mode:'sep', kind:'field', target:'guest', duration:55, sepDur:180,
  date:'2026-12-08', time:'11:00', memberId:'', guest:'테스트', fee:'', location:'', parsedName:'', parsed:null };
m.inp.value = '200';
onFieldChange({ target: m.inp });
eq('7-1 빠른 추가도 직접 입력값을 쓴다', qaSepDurNow(), 200);
eq('7-2 프리셋 강조는 꺼진다', JSON.stringify(chipOn(m.row)), '[]');
onClick({ target: m.chips[1] });                 /* 90분 */
eq('7-3 칩을 누르면 값이 90 으로', qaCtx.sepDur, 90);
eq('7-4 칸은 다시 빈다', m.inp.value, '');

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

# ---------- CSS 계약: 두 테마에서 읽히는 안내 문구 · 아이폰 확대 방지 · 390px 한 줄 ----------
checks = []
def ck(cond, name):
    checks.append((bool(cond), name))

ck('input.chipinp{flex:none;width:104px;height:33px' in HTML, 'C-1 직접 입력칸은 칩과 같은 알약 모양(고정 폭 104px)')
ck('font-size:16px;font-weight:800;letter-spacing:-.3px}' in HTML, 'C-2 입력칸 글자 16px (아이폰이 탭할 때 화면을 확대하지 않음)')
ck('input.chipinp::placeholder{' in HTML and 'color:var(--muted)' in HTML, 'C-3 안내 문구는 테마 공통 반투명 회색(--muted)')
ck('opacity:.8' in HTML, 'C-4 안내 문구 반투명 처리')
ck('.chips.durchips{gap:5px}' in HTML, 'C-5 칩 간격 5px (한 줄에 다 들어가게)')
ck('.chips.durchips .chip{padding:7px 11px}' in HTML, 'C-6 칩 좌우 여백 11px')
ck('style="width:92px;height:33px;border-radius:999px' not in HTML, 'C-7 예전 인라인 스타일 제거')
ck("inputmode=\"numeric\" pattern=\"[0-9]*\" maxlength=\"3\"" in HTML, 'C-8 숫자 키패드 · 세 자리까지')
# 두 테마 모두 --muted 를 정의한다 (그린 화이트 · 시크 블랙)
ck(HTML.count('--muted:#8A9099') >= 1 and HTML.count('--muted:#8B9099') >= 1, 'C-9 두 테마 모두 --muted 정의')

for c, n in checks:
    if not c:
        print('FAIL ' + n)
print('%d passed / %d total (CSS)' % (sum(1 for c, _ in checks if c), len(checks)))

if fails or any(not c for c, _ in checks):
    sys.exit(1)
print('\nALL PASSED')
