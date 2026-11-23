#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""상단 브랜드 바 · 오늘 레슨 메모 · 정산 차감색 · 회원 추가 다듬기(2026-11-23 6건) 검사.

1) 상단 브랜드 바 — 깃발 + ProPlan 워드마크를 인라인 SVG(벡터)로 그려 21px 에서도
   또렷한지, 바탕이 아래 헤더와 이어지는지. (예전 가로 락업 PNG 는 이제 쓰지 않는다)
2) 오늘 탭 [레슨 차트] → 오늘 차트 메모 시트: 열기·태그 미리보기·저장·같은 날 덮어쓰기·
   전체 차트는 회원 정보에 그대로.
3) 마감 정산 당일취소/노쇼의 옅은 차감색(두 테마).
4) '한 줄로 회원 추가' 카드 설명이 잘리지 않는지.
5) 회원 추가 시트의 선택형 음성 입력.
6) 횟수 프리셋 한 줄 · 빈 '횟수 입력' · 수강권 없이 등록 · 남/여 불투명 상자.
"""
import json
import re
import sys

import numpy as np
import quickjs
from PIL import Image

HTML = open('/workspace/golf-lesson-app/prototype.html', encoding='utf-8').read()
SPEC = open('/workspace/golf-lesson-app/spec.md', encoding='utf-8').read()
ASSETS = '/workspace/golf-lesson-app/assets/'
OUT = []


def ok(name, cond, detail=''):
    OUT.append((name, bool(cond), detail))


def section(text):
    return text in HTML


# ══════════════════════════════════════════════════════════
# 1. 상단 브랜드 바
# ══════════════════════════════════════════════════════════
ok('1-1 브랜드 바가 페이지 헤더보다 먼저',
   HTML.index('class="brandbar"') < HTML.index('<header class="hd" id="hd">'))
ok('1-2 .brandbar 가 프레임 안 첫 요소 줄',
   '<div id="app">\n  <div class="brandbar" id="brandbar">' in HTML)
ok('1-3 브랜드 바는 화면 바탕과 이어짐 (경계선·흐림 없음)',
   '.brandbar{flex:none;position:sticky;top:0;z-index:3;display:flex;align-items:center;justify-content:space-between' in HTML
   and 'padding:9px 16px 8px;background:var(--bg);border-bottom:0;' in HTML
   and 'padding-top:calc(9px + env(safe-area-inset-top, 0px))' in HTML)
ok('1-4 락업 높이 21px · SVG 로 그림', '.brandbar .bb-lockup{display:flex;align-items:center;height:21px;line-height:0}' in HTML
   and '.brandbar .bb-svg{display:block;height:21px;width:107px;overflow:visible}' in HTML)
ok('1-5 로고는 인라인 SVG (PNG 를 줄여 쓰지 않음)',
   'class="bb-svg"' in HTML and 'proplan-bar-green.png' not in HTML
   and 'proplan-bar-black.png' not in HTML and '<img class="bb-green"' not in HTML)
ok('1-5b 테마별 색만 바꿔 같은 벡터를 쓴다',
   '.brandbar .bb-flag{fill:#0F7B4A}' in HTML and '.brandbar .bb-word{fill:#0B0F14}' in HTML
   and 'html[data-theme="black"] .brandbar .bb-flag{fill:#34D399}' in HTML
   and 'html[data-theme="black"] .brandbar .bb-word{fill:#F4F6F8}' in HTML)
ok('1-6 시크 블랙도 같은 바탕으로 이어짐',
   'html[data-theme="black"] .brandbar{background:var(--bg)}' in HTML)
ok('1-7 깃발 + 워드마크 두 덩어리 벡터 경로', 'class="bb-flag"' in HTML and 'class="bb-word"' in HTML
   and 'fill-rule="evenodd"' in HTML and 'viewBox="-2 -2 758.92 149.00"' in HTML)
ok('1-8 헤더 위 여백을 줄여 자리 확보', 'padding:12px 16px 8px;background:linear-gradient(180deg,var(--bg) 72%' in HTML)
ok('1-9 워드마크가 읽어 주는 이름을 가짐', 'role="img" aria-label="ProPlan"' in HTML)

# ── 1b. 가로 락업 PNG 픽셀 ────────────────────────────────
def bar_check(fname, tag):
    im = Image.open(ASSETS + fname)
    a = np.array(im)
    al = a[:, :, 3]
    opaque = al > 24
    cols = opaque.sum(axis=0)
    rows = opaque.sum(axis=1)
    xs = np.where(cols > 0)[0]
    ys = np.where(rows > 0)[0]
    gap = [x for x in range(xs.min(), xs.max()) if cols[x] == 0]
    ok('1b-1 %s 가로 비율' % tag, 4.9 < im.width / float(im.height) < 5.6,
       '%dx%d' % (im.width, im.height))
    ok('1b-2 %s 깃발과 워드마크가 떨어져 두 덩어리' % tag, len(gap) > 4,
       'gap cols %d' % len(gap))
    # 깃발은 왼쪽 덩어리 — 초록 계열, 워드마크는 진한/흰 글자
    mark = a[:, :xs.min() + gap[0]]
    word = a[:, gap[-1] + 1:]
    mo = mark[:, :, 3] > 24
    mr, mg = mark[:, :, 0][mo].astype(int), mark[:, :, 1][mo].astype(int)
    wm = word[:, :, 3] > 24
    wr, wg = word[:, :, 0][wm].astype(int), word[:, :, 1][wm].astype(int)
    ok('1b-3 %s 왼쪽 덩어리는 에메랄드 깃발' % tag, (mg - mr).mean() > 30,
       'g-r %.1f' % ((mg - mr).mean() if len(mg) else 0))
    ok('1b-4 %s 오른쪽 덩어리는 무채색 워드마크' % tag, abs((wg - wr).mean()) < 6,
       'g-r %.1f' % (abs((wg - wr).mean()) if len(wr) else 99))
    # 밑선 정렬 — 깃발 컵의 맨 아래와 글자의 맨 아래가 같은 줄
    mark_bottom = np.where((mark[:, :, 3] > 24).any(axis=1))[0].max()
    word_bottom = np.where((word[:, :, 3] > 24).any(axis=1))[0].max()
    ok('1b-5 %s 깃발 컵과 워드마크 밑선 정렬' % tag, abs(int(mark_bottom) - int(word_bottom)) <= 2,
       'mark %d / word %d' % (mark_bottom, word_bottom))


bar_check('proplan-bar-green.png', '밝은 바탕')
bar_check('proplan-bar-black.png', '어두운 바탕')
im_g = np.array(Image.open(ASSETS + 'proplan-bar-green.png'))
im_b = np.array(Image.open(ASSETS + 'proplan-bar-black.png'))
op_g = im_g[:, :, 3] > 200
op_b = im_b[:, :, 3] > 200
ok('1c-1 밝은 바탕 워드마크는 진한 먹색', im_g[:, :, 0][op_g].max() < 60, str(im_g[:, :, 0][op_g].max()))
ok('1c-2 어두운 바탕 워드마크는 흰색', im_b[:, :, 0][op_b].max() > 240, str(im_b[:, :, 0][op_b].max()))
ok('1c-3 두 그림의 크기가 같다', im_g.shape == im_b.shape)

# ══════════════════════════════════════════════════════════
# 2. 오늘 탭 [레슨 차트] → 오늘 차트 메모 (코드 실행)
# ══════════════════════════════════════════════════════════
start = HTML.index("/* =========================================================\n   오늘 차트 메모")
end = HTML.index("/* =========================================================\n   캘린더 탭")
MEMO = HTML[start:end]

HARNESS = r"""
var TODAY = '2026-11-23';
function todayISO(){ return TODAY; }
function esc(s){ return String(s === null || s === undefined ? '' : s); }
function fmtDot(d){ return d.replace(/-/g, '.'); }
function fmtShort(d){ var p = d.split('-'); return (+p[1]) + '.' + (+p[2]); }
function nowLocalISO(){ return '2026-11-23T19:40:00'; }
var uidSeq = 0;
function uid(p){ uidSeq++; return (p || 'id') + '_' + uidSeq; }
var GOLF = { '드라이버':['드라이버','티샷'], '퍼팅':['퍼팅','그린'] };
function detectGolfTags(text){
  var src = String(text||'').toLowerCase(), out = [];
  for (var k in GOLF) for (var i=0;i<GOLF[k].length;i++) if (src.indexOf(GOLF[k][i])>=0) { out.push(k); break; }
  return out;
}
function noteTagHTML(n){ return '<span class="gtag">#' + n + '</span>'; }
var state = { members: [], packages: [], sessions: [], notes: [] };
function memberById(id){ for (var i=0;i<state.members.length;i++) if (state.members[i].id===id) return state.members[i]; return null; }
function findSession(id){ for (var i=0;i<state.sessions.length;i++) if (state.sessions[i].id===id) return state.sessions[i]; return null; }
function isSep(s){ return !!s.separatePay; }
var saved = 0, rendered = 0, toastMsg = '', closed = 0;
function save(){ saved++; }
function render(){ rendered++; }
function toast(m){ toastMsg = m; }
var FIELDS = {};
var document = { getElementById: function(id){
  var el = FIELDS[id] || null;
  if (el && !el.focus) el.focus = function(){};
  return el;
} };
var voice = { want: false, kind: null };
function vrStop(){ voice.want = false; voice.kind = null; }
var sheetBody = '', sheetFooter = '', sheetTitle = '', sheetSub = '';
function openSheet(o){
  sheetTitle = o.title || ''; sheetSub = o.sub || '';
  return { el: { setAttribute: function(){} },
    body: { innerHTML: '' }, footer: { style: {}, innerHTML: '' },
    close: function(){ closed++; } };
}
""" + MEMO + r"""

var fails = [], log = [];
function ok(c, n){ if (c) log.push('PASS ' + n); else fails.push('FAIL ' + n); }
function eq(a, b, n){ ok(a === b, n + (a === b ? '' : '  got=[' + a + '] want=[' + b + ']')); }

/* ── 시트 열기 ── */
state.members = [{ id:'m1', name:'김민수' }];
state.sessions = [{ id:'s1', memberId:'m1', date:'2026-11-23', startTime:'08:00', durationMinutes:55, status:'scheduled' }];
openTodayMemoSheet('s1');
eq(sheetTitle, '오늘 차트 메모', '2-1 시트 제목');
ok(sheetSub.indexOf('김민수') >= 0 && sheetSub.indexOf('08:00') >= 0, '2-2 회원·시간이 부제에');
ok(tmCtx && tmCtx.memberId === 'm1' && tmCtx.date === '2026-11-23', '2-3 오늘 날짜로 컨텍스트');
var body = tmCtx.sh.body.innerHTML;
ok(body.indexOf('id="tmText"') >= 0, '2-4 큰 입력칸 하나');
ok(body.indexOf('id="tmVoiceBtn"') >= 0 && body.indexOf('data-act="tm-voice"') >= 0, '2-5 음성 버튼');
ok(body.indexOf('id="tmTags"') >= 0, '2-6 태그 미리보기 자리');
ok(body.indexOf('전체 레슨 차트는 회원 정보에서') >= 0, '2-7 전체 차트는 회원 정보 안내');
ok(tmCtx.sh.footer.innerHTML.indexOf('tm-save') >= 0, '2-8 저장 버튼');
ok(tmCtx.sh.footer.innerHTML.indexOf('tm-kakao') >= 0, '2-9 카톡 요약 버튼');

/* ── 태그 미리보기 ── */
FIELDS.tmTags = { innerHTML: '' };
FIELDS.tmText = { value: '드라이버 백스윙 교정' };
paintTodayMemoTags();
ok(FIELDS.tmTags.innerHTML.indexOf('#드라이버') >= 0, '2-10 본문에서 태그가 붙음');
FIELDS.tmText.value = '가볍게 몸풀기';
paintTodayMemoTags();
ok(FIELDS.tmTags.innerHTML.indexOf('태그 자동') >= 0, '2-11 태그가 없으면 안내');

/* ── 저장 ── */
FIELDS.tmText.value = '  드라이버 백스윙 교정, 오른팔 펴기  ';
saveTodayMemo();
eq(state.notes.length, 1, '2-12 차트 기록 1건');
eq(state.notes[0].memberId, 'm1', '2-13 회원');
eq(state.notes[0].date, '2026-11-23', '2-14 레슨 날짜');
eq(state.notes[0].text, '드라이버 백스윙 교정, 오른팔 펴기', '2-15 앞뒤 공백 제거');
eq(state.notes[0].tags.join(','), '드라이버', '2-16 태그 저장');
eq(state.notes[0].source, 'text', '2-17 입력 방식');
ok(saved === 1 && rendered === 1 && closed === 1, '2-18 저장·화면 갱신·시트 닫기');
ok(toastMsg.indexOf('레슨 차트에 저장했어요') >= 0, '2-19 토스트');

/* ── 같은 날 다시 적으면 덮어쓰기 (중복 없음) ── */
openTodayMemoSheet('s1');
ok(tmCtx.sh.body.innerHTML.indexOf('드라이버 백스윙 교정') >= 0, '2-20 그 날짜 메모를 불러옴');
FIELDS.tmText.value = '퍼팅 스트로크 연습';
saveTodayMemo();
eq(state.notes.length, 1, '2-21 같은 날은 새 기록을 만들지 않음');
eq(state.notes[0].text, '퍼팅 스트로크 연습', '2-22 고친 내용으로 바뀜');
eq(state.notes[0].tags.join(','), '퍼팅', '2-23 태그도 다시 계산');

/* ── 빈 내용은 저장하지 않음 ── */
openTodayMemoSheet('s1');
FIELDS.tmText.value = '   ';
saveTodayMemo();
eq(state.notes.length, 1, '2-24 빈 내용은 저장 안 함');
ok(toastMsg.indexOf('먼저 적어주세요') >= 0, '2-25 안내 토스트');

/* ── 음성으로 적었으면 source=voice ── */
FIELDS.tmText.value = '아이언 다운블로';
voice.want = true; voice.kind = 'tm';
saveTodayMemo();
eq(state.notes.length, 1, '2-26 음성 저장도 같은 기록');
eq(state.notes[0].source, 'voice', '2-27 음성 표시');
ok(voice.want === false, '2-28 저장하면 듣기를 멈춤');

/* ── 비회원 레슨은 열지 않음 ── */
state.sessions.push({ id:'s2', memberId:null, date:'2026-11-23', startTime:'10:00', durationMinutes:55, status:'scheduled' });
toastMsg = '';
openTodayMemoSheet('s2');
ok(toastMsg.indexOf('비회원') >= 0, '2-29 비회원은 레슨 메모로');

JSON.stringify({ pass: log, fail: fails });
"""

ctx = quickjs.Context()
data = json.loads(ctx.eval(HARNESS))
OUT.extend([(p[5:], True, '') for p in data['pass']])
OUT.extend([(f[5:], False, '') for f in data['fail']])

# 정적 계약 — 카드 버튼과 시트 연결
ok('2-30 오늘 카드의 [레슨 차트]가 tm-open', 'data-act="tm-open" data-sid="' in HTML)
ok('2-31 회원 이름은 여전히 회원 정보창', 'data-act="member-open" data-id="' in HTML)
ok('2-32 디스패처에 tm-open', "case 'tm-open':" in HTML)
ok('2-33 디스패처에 tm-save·tm-voice·tm-kakao',
   "case 'tm-save':" in HTML and "case 'tm-voice':" in HTML and "case 'tm-kakao':" in HTML)
ok('2-34 시트를 닫으면 음성 반납',
   "if (tmCtx && tmCtx.sh && tmCtx.sh.el === wrap) { if (voice.kind === 'tm') vrStop(); tmCtx = null; }" in HTML)
ok('2-35 음성 엔진이 tm 입력칸을 씀',
   "if (kind === 'tm') return { ta: document.getElementById('tmText')" in HTML)
ok('2-36 spec 3.1 에 오늘 차트 메모', '오늘 차트 메모 시트' in SPEC)
ok('2-37 spec 20.2 정리', '## 20. 상단 브랜드 바' in SPEC and '20.2 오늘 탭' in SPEC)

# ══════════════════════════════════════════════════════════
# 3. 마감 정산 — 옅은 차감색
# ══════════════════════════════════════════════════════════
ok('3-1 정산 버튼에 상태 클래스', "class=\"sopt sopt-' + k" in HTML)
ok('3-2 당일취소 옅은 호박(밝은 테마)',
   '.sopt.sopt-same_day_cancel:not(.on){background:var(--amber-soft);color:var(--amber-ink);' in HTML)
ok('3-3 노쇼 옅은 빨강(밝은 테마)',
   '.sopt.sopt-no_show:not(.on){background:var(--red-soft);color:var(--red-ink);' in HTML)
ok('3-4 선택 전에만 차감색 (선택하면 진한 상태색)',
   ':not(.on)' in HTML and '.sopt.on{background:#111820;color:#fff' in HTML)
ok('3-5 시크 블랙 당일취소 반투명 호박',
   'html[data-theme="black"] .sopt.sopt-same_day_cancel:not(.on){background:rgba(240,168,60,.14)' in HTML)
ok('3-6 시크 블랙 노쇼 반투명 빨강',
   'html[data-theme="black"] .sopt.sopt-no_show:not(.on){background:rgba(242,106,90,.15)' in HTML)
ok('3-7 테두리는 inset 그림자 (칸 크기 안 흔들림)',
   '.sopt.sopt-same_day_cancel:not(.on)' in HTML and 'box-shadow:inset 0 0 0 1px var(--amber-line)' in HTML)
ok('3-8 spec 5장에 차감색 설명', '아주 옅은 호박색' in SPEC and '아주 옅은 빨간색' in SPEC)

# ══════════════════════════════════════════════════════════
# 4. '한 줄로 회원 추가' 카드 — 설명이 잘리지 않음
# ══════════════════════════════════════════════════════════
qa = HTML[HTML.index('.quickadd .qa-d{'):]
qa = qa[:qa.index('}') + 1]
ok('4-1 예시 줄은 여러 줄로 접힘', 'white-space:normal' in qa)
ok('4-2 줄임표·클리핑 없음', 'text-overflow:ellipsis' not in qa and '-webkit-line-clamp' not in qa and 'white-space:nowrap' not in qa)
ok('4-3 줄 높이로 읽기 편하게', 'line-height:1.5' in qa)
ok('4-3b 한글 단어가 중간에서 끊기지 않게', 'word-break:keep-all' in qa)
ok('4-4 카드 안쪽 여백을 조금 늘림', 'padding:15px 14px' in HTML)
ok('4-5 설명 문구는 그대로', '여러 줄 붙여넣기 가능' in HTML)
ok('4-6 spec 3.3 반영', '줄임표로 자르지 않고' in SPEC)

# ══════════════════════════════════════════════════════════
# 5. 회원 추가 시트 — 선택형 음성 입력
# ══════════════════════════════════════════════════════════
ok('5-1 한 줄 입력 상자 아래 음성 버튼',
   'id="amVoiceBtn" data-act="am-voice"' in HTML)
ok('5-2 버튼은 음성 엔진의 am 입력칸과 연결',
   "if (kind === 'am') return { ta: document.getElementById('quickLine')" in HTML)
ok('5-3 토글 함수가 am 으로 시작', 'function toggleAmVoice()' in HTML and "vrStart('am');" in HTML)
ok('5-4 디스패처에 am-voice', "case 'am-voice':" in HTML)
ok('5-5 인식되면 바로 파싱', "else if (kind === 'am') applyQuickLine();" in HTML)
ok('5-6 버튼도 듣는 중 표시',
   "vrPaintBtn(document.getElementById('amVoiceBtn'), on && kind === 'am');" in HTML)
ok('5-7 회원 시트를 닫으면 음성 반납',
   "if (addCtx && addCtx.sh && addCtx.sh.el === wrap) { if (voice.kind === 'am') vrStop(); addCtx = null; }" in HTML)
ok('5-8 spec 6장에 선택형 음성', '🎤 음성 입력' in SPEC.split('## 7.')[0])

# ══════════════════════════════════════════════════════════
# 6. 횟수 한 줄 · 빈 입력칸 · 남/여 상자 (코드 실행)
# ══════════════════════════════════════════════════════════
PARSE = HTML[HTML.index('/* =========================================================\n   한 줄 간편 입력 파서'):
             HTML.index('/* =========================================================\n   화면 렌더')]
SETCH = HTML[HTML.index('function setCountChips('):HTML.index('function quickValidRows(')]
ADD = HTML[HTML.index('function quickValidRows('):
           HTML.index('/* =========================================================\n   수강권 추가')]

H2 = r"""
var TODAY = '2026-11-23';
function todayISO(){ return TODAY; }
function durName(d){ return d === 25 ? '25분' : '55분'; }
function money(n){ return n === '' || n === null ? '-' : String(n); }
function esc(s){ return String(s === null || s === undefined ? '' : s); }
function addMonths(s, n){ return '2027-05-23'; }
var uidSeq = 0;
function uid(p){ uidSeq++; return (p || 'id') + '_' + uidSeq; }
var state = { members: [], packages: [], sessions: [], notes: [] };
function findMemberByName(name){ for (var i=0;i<state.members.length;i++) if (state.members[i].name===name) return state.members[i]; return null; }
function memberById(id){ for (var i=0;i<state.members.length;i++) if (state.members[i].id===id) return state.members[i]; return null; }
var saved = 0, rendered = 0, toastMsg = '', openedMember = '';
function save(){ saved++; }
function render(){ rendered++; }
function toast(m){ toastMsg = m; }
function openMemberSheet(id){ openedMember = id; }
var addCtx = null, memberCtx = null, ui = { tab: 'today' };
var FIELDS = {};
var document = { getElementById: function(id){
  var el = FIELDS[id] || null;
  if (el && !el.focus) el.focus = function(){};
  return el;
} };
function setGenderUI(){}
function setDurUI(){}
function syncPickLabel(){}
""" + PARSE + SETCH + ADD + r"""

var fails = [], log = [];
function ok(c, n){ if (c) log.push('PASS ' + n); else fails.push('FAIL ' + n); }
function eq(a, b, n){ ok(a === b, n + (a === b ? '' : '  got=[' + a + '] want=[' + b + ']')); }

/* ── 횟수를 비우면 수강권 없이 회원만 ── */
state.members = []; state.packages = [];
addCtx = { sh: { close: function(){} }, editing: false, duration: 55, gender: 'female', rows: [], bulk: false };
FIELDS = { mfName: { value: '김민수' }, mfRegion: { value: '분당' }, mfPhone: { value: '' },
  mfLevel: { value: '' }, mfMemo: { value: '' }, mfSessions: { value: '' },
  mfRemain: { value: '' }, mfStart: { value: '2026-11-23' }, mfMonths: { value: '6' }, mfPrice: { value: '' } };
saveMember();
eq(state.members.length, 1, '6-1 회원은 등록');
eq(state.members[0].name, '김민수', '6-2 이름');
eq(state.members[0].gender, 'female', '6-3 성별');
eq(state.packages.length, 0, '6-4 수강권은 만들지 않음');
ok(toastMsg.indexOf('수강권 없이') >= 0, '6-5 토스트 안내');
ok(openedMember.length > 0, '6-6 회원 정보창으로 이어짐');

/* ── 횟수를 넣으면 예전처럼 수강권 ── */
state.members = []; state.packages = [];
addCtx = { sh: { close: function(){} }, editing: false, duration: 55, gender: 'male', rows: [], bulk: false };
FIELDS = { mfName: { value: '박영희' }, mfRegion: { value: '' }, mfPhone: { value: '' },
  mfLevel: { value: '' }, mfMemo: { value: '' }, mfSessions: { value: '10' },
  mfRemain: { value: '4' }, mfStart: { value: '2026-11-23' }, mfMonths: { value: '6' }, mfPrice: { value: '' } };
saveMember();
eq(state.packages.length, 1, '6-7 수강권 1개');
eq(state.packages[0].totalSessions, 10, '6-8 총 10회');
eq(state.packages[0].remainingSessions, 4, '6-9 잔여 4회');

/* ── 남은 횟수 칸은 횟수를 넣었을 때만 안내 ── */
FIELDS.mfSessions = { value: '' }; FIELDS.mfRemain = { value: '' };
FIELDS.mfPrice = { value: '' }; FIELDS.mfUnit = { innerHTML: '' };
FIELDS.mfRemainHint = { innerHTML: '', style: {} };
FIELDS.mfCountChips = { querySelectorAll: function(){ return []; } };
updateUnit();
eq(FIELDS.mfRemainHint.style.display, 'none', '6-10 횟수가 비면 남은 횟수 안내 숨김');
FIELDS.mfSessions = { value: '8' };
updateUnit();
eq(FIELDS.mfRemainHint.style.display, '', '6-11 횟수를 넣으면 안내 다시 보임');

JSON.stringify({ pass: log, fail: fails });
"""
ctx2 = quickjs.Context()
data2 = json.loads(ctx2.eval(H2))
OUT.extend([(p[5:], True, '') for p in data2['pass']])
OUT.extend([(f[5:], False, '') for f in data2['fail']])

# 정적 계약
ok('6-12 횟수 칸은 비어 있고 흐린 "횟수 입력"',
   'id="mfSessions" type="number" inputmode="numeric" min="1" step="1" placeholder="횟수 입력"' in HTML)
chip_src = HTML[HTML.index('id="mfCountChips"'):]
chip_src = chip_src[:chip_src.index('</div>')]
ok('6-13 회원 추가 프리셋은 다섯 개(30회 없음)',
   "'<div class=\"chips countrow mt10\" id=\"mfCountChips\">' + [1,5,8,10,20].map" in HTML and '30' not in chip_src,
   chip_src[:120])
ok('6-14 다섯 칩이 한 줄 grid', '.chips.countrow{display:grid;grid-template-columns:repeat(5,1fr);gap:6px}' in HTML)
ok('6-15 칩 묶음에 id', 'class="chips countrow mt10" id="mfCountChips"' in HTML)
ok('6-16 칩 강조가 이 묶음을 봄', "var wrap = document.getElementById('mfCountChips');" in HTML)
ok('6-17 횟수는 선택이라고 라벨에 표시', '<label>횟수 (선택)</label>' in HTML)
ok('6-18 비우면 수강권 없이 등록된다는 안내', '수강권 없이 회원만' in HTML)
ok('6-19 남/여가 boxed 상자', 'class="seg mini boxed" id="mfGender"' in HTML)
seg = HTML[HTML.index('/* 남/여 — 반투명 회색 띠'):]
seg = seg[:seg.index('.statsseg')]
ok('6-20 boxed 는 반투명 띠가 아니라 상자', 'background:transparent;border:0;padding:0;gap:8px' in seg)
ok('6-21 상자 높이 45px · 테두리 · 둥근 모서리',
   'height:45px;border-radius:12px;background:var(--field);border:1px solid #D3D8DF' in seg)
ok('6-22 고른 칸은 에메랄드로 꽉 채움', '.seg.boxed button.on{background:var(--green)' in seg)
ok('6-23 시크 블랙 상자 색', 'html[data-theme="black"] .seg.boxed button{background:#202026' in seg)
ok('6-24 spec 20.6 정리', '30회` 프리셋은 삭제' in SPEC or '30회`를 빼고' in SPEC)

# ══════════════════════════════════════════════════════════
for name, cond, detail in OUT:
    print(('PASS ' if cond else 'FAIL ') + name + ('' if cond else '  <- ' + str(detail)))
p = sum(1 for _, c, _ in OUT if c)
print('')
print('%d passed / %d total' % (p, len(OUT)))
if p != len(OUT):
    sys.exit(1)
