#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""프로토타입에 실제로 들어 있는 음성 입력 엔진을 quickjs로 실행해
   시작 → 취소 → 재시도 → 결과 반영 흐름을 검사한다."""
import re, sys, json
import quickjs

HTML = open('/workspace/golf-lesson-app/prototype.html', encoding='utf-8').read()

start = HTML.index("var voice = {")
end = HTML.index("function stopVoice(){ vrStop(); }") + len("function stopVoice(){ vrStop(); }")
ENGINE = HTML[start:end]
qstart = HTML.index("function toggleQaVoice(){")
qend = HTML.index("function stopQaVoice(){ vrStop(); }") + len("function stopQaVoice(){ vrStop(); }")
ENGINE += "\n" + HTML[qstart:qend]
# 회원 추가 시트(am) · 오늘 레슨 메모(tm)도 같은 엔진을 쓴다
astart = HTML.index("function toggleAmVoice(){")
aend = HTML.index("function stopAmVoice(){ vrStop(); }") + len("function stopAmVoice(){ vrStop(); }")
ENGINE += "\n" + HTML[astart:aend]
tstart = HTML.index("function toggleTmVoice(){")
tend = HTML.index("function saveTodayMemo(){")
ENGINE += "\n" + HTML[tstart:tend]

HARNESS = r"""
/* ---------- 가상 시계 ---------- */
var VNOW = 1700000000000;
var Date = { now: function(){ return VNOW; } };
var timers = [], tid = 1;
function setTimeout(fn, ms){ var id = tid++; timers.push({id:id, at: VNOW + (ms||0), fn:fn}); return id; }
function clearTimeout(id){ for (var i=0;i<timers.length;i++) if (timers[i].id===id) { timers.splice(i,1); break; } }
function tick(ms){
  var target = VNOW + (ms||0), guard = 0;
  while (guard++ < 500) {
    var due = null;
    for (var i=0;i<timers.length;i++) if (timers[i].at <= target && (!due || timers[i].at < due.at)) due = timers[i];
    if (!due) break;
    VNOW = due.at;
    for (var j=0;j<timers.length;j++) if (timers[j].id === due.id) { timers.splice(j,1); break; }
    due.fn();
  }
  VNOW = target;
}
function pendingTimers(){ return timers.length; }

/* ---------- 가상 DOM ---------- */
function El(id){
  this.id = id; this.value = ''; this.disabled = false; this.readOnly = false;
  this.textContent = ''; this.innerHTML = ''; this._cls = {};
}
El.prototype.classList = null;
function makeCls(el){
  return {
    add: function(c){ el._cls[c] = true; },
    remove: function(c){ delete el._cls[c]; },
    toggle: function(c, force){ if (force === undefined) { if (el._cls[c]) delete el._cls[c]; else el._cls[c] = true; } else if (force) el._cls[c] = true; else delete el._cls[c]; },
    contains: function(c){ return !!el._cls[c]; }
  };
}
var ELS = {};
function mkEl(id){ var e = new El(id); e.classList = makeCls(e); ELS[id] = e; return e; }
var document = { getElementById: function(id){ return ELS[id] || null; } };
var window = {};
var toasts = [];
function toast(m){ toasts.push(m); }
function esc(s){ return String(s); }
var refreshCount = 0, parseCount = 0, quickCount = 0, tagPaintCount = 0;
function refreshNoteDate(){ refreshCount++; }
function applyQuickParse(){ parseCount++; }
function applyQuickLine(){ quickCount++; }
function paintTodayMemoTags(){ tagPaintCount++; }
var memberCtx = { voiceUsed: false };
var tmCtx = { voiceUsed: false };

/* ---------- 가상 SpeechRecognition ---------- */
function MockSR(){ this.state='new'; this.startCalls=0; MockSR.made.push(this); }
MockSR.made = [];
MockSR.prototype.start = function(){
  this.startCalls++;
  if (MockSR.startThrows > 0) { MockSR.startThrows--; throw new Error('InvalidStateError'); }
  this.state = 'started';
  var self = this;
  setTimeout(function(){ if (self.onstart && self.state === 'started') self.onstart({}); }, 5);
};
MockSR.prototype.stop = function(){ this.stopCalls = (this.stopCalls||0)+1; this.state='idle'; };
MockSR.prototype.abort = function(){ this.aborted = true; this.state='idle'; };
MockSR.prototype._result = function(text, isFinal, index){
  var res = [];
  for (var i=0;i<(index||0);i++) res.push({ 0:{transcript:'x'}, isFinal:true });
  res.push({ 0:{transcript:text}, isFinal:!!isFinal });
  this.onresult && this.onresult({ resultIndex: index||0, results: res });
};
MockSR.prototype._error = function(err){ this.onerror && this.onerror({ error: err }); };
MockSR.prototype._end = function(){ this.onend && this.onend({}); };
window.SpeechRecognition = MockSR;

""" + ENGINE + r"""

/* ================= 테스트 ================= */
var fails = [], log = [];
function ok(cond, name){ if (cond) log.push('PASS ' + name); else fails.push('FAIL ' + name); }

function fresh(){
  ELS = {};
  mkEl('noteText'); mkEl('noteHint'); mkEl('voiceBtn');
  mkEl('qaLine'); mkEl('qaBar'); mkEl('qaVoiceBtn');
  mkEl('quickLine'); mkEl('parseBar'); mkEl('amVoiceBtn');
  mkEl('tmText'); mkEl('tmHint'); mkEl('tmVoiceBtn');
  MockSR.made = []; MockSR.startThrows = 0;
  memberCtx = { voiceUsed:false };
  tmCtx = { voiceUsed:false };
  quickCount = 0; tagPaintCount = 0;
  voice.want=false; voice.kind=null; voice.inst=null; voice.started=false;
  voice.base=''; voice.committed=''; voice.lastWritten='';
  voice.fails=0; voice.pauses=0; voice.quietUntil=0;
  timers = []; VNOW = 1700000000000;
  toasts = [];
}

/* 1. 시작 → 결과 반영 */
fresh();
toggleVoice();
ok(MockSR.made.length === 1, '1-1 시작 시 인식기 1개 생성');
ok(voice.want === true && voice.kind === 'note', '1-2 듣기 상태 켜짐');
ok(ELS.voiceBtn.classList.contains('rec'), '1-3 버튼 듣는 중 표시');
var first = MockSR.made[0];
tick(10);
ok(first.state === 'started', '1-4 start() 호출됨');
first._result('드라이버 백스윙', false, 0);
ok(ELS.noteText.value.indexOf('드라이버') === 0, '1-5 중간 결과가 입력칸에 반영: ' + JSON.stringify(ELS.noteText.value));
first._result('드라이버 백스윙 교정', true, 0);
ok(ELS.noteText.value === '드라이버 백스윙 교정', '1-6 확정 결과 반영: ' + JSON.stringify(ELS.noteText.value));
first._result('오른팔 펴기', true, 1);
ok(ELS.noteText.value === '드라이버 백스윙 교정 오른팔 펴기', '1-7 다음 확정 문장 이어 붙음: ' + JSON.stringify(ELS.noteText.value));
ok(memberCtx.voiceUsed === true, '1-8 음성 사용 표시');
ok(refreshCount > 0, '1-9 날짜 인식 갱신 호출');

/* 2. 취소 → 상태 정리 */
toggleVoice();
ok(voice.want === false, '2-1 취소 후 듣기 꺼짐');
ok(first.aborted === true, '2-2 이전 인식기 abort()로 반납');
ok(first.onend === null && first.onresult === null, '2-3 이전 인식기 콜백 떼어냄');
ok(!ELS.voiceBtn.classList.contains('rec'), '2-4 버튼 원상복구');
ok(ELS.voiceBtn.textContent === '🎤 음성 입력', '2-5 버튼 문구 원상복구 (' + ELS.voiceBtn.textContent + ')');
ok(ELS.noteText.disabled === false && ELS.noteText.readOnly === false, '2-6 입력칸 잠기지 않음');
var before = ELS.noteText.value;

/* 3. 취소 직후 재시도 → 새 객체 → 결과 반영 */
toggleVoice();
tick(400);   /* iOS가 마이크를 놓을 틈(250ms) 뒤 새 객체 생성 */
ok(MockSR.made.length === 2, '3-1 재시도 때 완전히 새 인식기 생성');
var second = MockSR.made[1];
ok(second !== first, '3-2 이전 객체 재사용 안 함');
ok(second.state === 'started', '3-3 새 인식기 정상 시작');
second._result('퍼팅 스트로크 연습', true, 0);
ok(ELS.noteText.value === before + ' 퍼팅 스트로크 연습', '3-4 이어서 입력됨: ' + JSON.stringify(ELS.noteText.value));

/* 4. iOS처럼 onend만 먼저 와도 계속 듣기 */
second._end();
ok(voice.want === true, '4-1 문장 끝나도 듣기 유지');
tick(400);
ok(MockSR.made.length === 3, '4-2 새 인식기로 이어 듣기');
var third = MockSR.made[2];
tick(10);
third._result('그립 확인', true, 0);
ok(ELS.noteText.value.slice(-5) === '그립 확인', '4-3 이어 듣기 결과 반영: ' + JSON.stringify(ELS.noteText.value));

/* 5. start()가 InvalidStateError를 내도 재시도로 살아남기 */
fresh();
MockSR.startThrows = 1;
toggleVoice();
ok(voice.want === true, '5-1 첫 start 실패해도 듣기 의사 유지');
tick(1000);
ok(MockSR.made.length >= 2, '5-2 새 객체로 재시도 (' + MockSR.made.length + '개)');
var rec5 = voice.inst;
ok(rec5 && rec5.state === 'started', '5-3 재시도로 실제 시작됨');
tick(10);
rec5._result('아이언 샷', true, 0);
ok(ELS.noteText.value === '아이언 샷', '5-4 결과 정상 반영');

/* 6. start()가 조용히 실패(이벤트 없음)해도 감지 후 재시도 */
fresh();
var silentMode = true;
var OrigSR = MockSR;
function SilentSR(){ this.state='new'; MockSR.made.push(this); }
SilentSR.prototype.start = function(){ this.state='started'; };   /* onstart 없음 = iOS 먹통 재현 */
SilentSR.prototype.stop = function(){ this.state='idle'; };
SilentSR.prototype.abort = function(){ this.aborted = true; this.state='idle'; };
window.SpeechRecognition = SilentSR;
var quietUntil = 0;
toggleVoice();
tick(15000);   /* 2.5초 감시 × 4회 시도 */
ok(voice.want === false, '6-1 계속 안 되면 반복 대신 멈추고 안내');
ok(ELS.noteHint.innerHTML.indexOf('다시 켜지 못했어요') >= 0, '6-2 안내 문구 표시: ' + ELS.noteHint.innerHTML);
ok(ELS.voiceBtn.classList.contains('rec') === false, '6-3 버튼 원상복구');
window.SpeechRecognition = OrigSR;

/* 7. no-speech는 계속 듣기 */
fresh();
toggleVoice();
tick(10);
var r7 = voice.inst;
r7._error('no-speech');
ok(voice.want === true, '7-1 no-speech 후에도 듣기 유지');
tick(500);
ok(MockSR.made.length === 2 && voice.inst !== r7, '7-2 새 객체로 이어 듣기');

/* 8. not-allowed는 안내 후 중지 */
fresh();
toggleVoice();
tick(10);
voice.inst._error('not-allowed');
ok(voice.want === false, '8-1 권한 거부 시 중지');
ok(ELS.noteHint.innerHTML.indexOf('마이크 사용이 허용되지 않았어요') >= 0, '8-2 안내 표시');

/* 9. 창 닫기(stopVoice) 후 다시 열어 재시도 */
fresh();
toggleVoice(); tick(10);
var r9 = voice.inst;
r9._result('세팅', true, 0);
stopVoice();
ok(voice.want === false && r9.aborted === true, '9-1 시트 닫으면 반납');
ELS.noteText.value = '';          /* 새로 연 시트 */
toggleVoice();
tick(400);
ok(MockSR.made.length === 2, '9-2 다시 열어 새로 시작');
voice.inst._result('오늘 레슨', true, 0);
ok(ELS.noteText.value === '오늘 레슨', '9-3 결과 반영');

/* 10. 듣는 중 사용자가 직접 타이핑하면 덮어쓰지 않음 */
fresh();
ELS.noteText.value = '메모';
toggleVoice(); tick(10);
var r10 = voice.inst;
r10._result('첫 문장', true, 0);
ok(ELS.noteText.value === '메모 첫 문장', '10-1 기존 글 뒤에 붙음');
ELS.noteText.value = '메모 첫 문장 (직접 수정)';
r10._result('둘째', true, 1);
ok(ELS.noteText.value === '메모 첫 문장 (직접 수정) 둘째', '10-2 직접 고친 글 유지: ' + JSON.stringify(ELS.noteText.value));

/* 11. 캘린더 빠른 추가 경로 */
fresh();
toggleQaVoice();
tick(10);
ok(voice.kind === 'qa', '11-1 빠른 추가 음성 켜짐');
ok(ELS.qaVoiceBtn.classList.contains('rec'), '11-2 빠른 추가 버튼 표시');
voice.inst._result('내일 오후 3시 김민준', true, 0);
ok(ELS.qaLine.value === '내일 오후 3시 김민준', '11-3 빠른 추가 입력칸 반영');
ok(parseCount > 0, '11-4 자동 정리 실행');
toggleQaVoice();
ok(voice.want === false && ELS.qaBar.innerHTML.indexOf('멈췄어요') >= 0, '11-5 취소 안내');
toggleQaVoice();
tick(400);
ok(MockSR.made.length === 2, '11-6 취소 후 재시도 성공');
voice.inst._result('모레 오전 10시 이서연', true, 0);
ok(ELS.qaLine.value === '내일 오후 3시 김민준 모레 오전 10시 이서연', '11-7 이어서 인식: ' + JSON.stringify(ELS.qaLine.value));

/* 12. 연속 취소→재시도 5회 */
fresh();
for (var k=0;k<5;k++){
  toggleVoice(); tick(400);
  var rk = voice.inst;
  rk._result('문장' + k, true, 0);
  toggleVoice();          /* 취소 */
  tick(100);
}
toggleVoice(); tick(400);
ok(voice.want === true && MockSR.made.length === 6, '12-1 5회 취소 후에도 마지막 시작 성공');
voice.inst._result('마지막', true, 0);
ok(ELS.noteText.value.slice(-3) === '마지막', '12-2 마지막 결과 반영: ' + JSON.stringify(ELS.noteText.value));

/* 13. 회원 추가 시트의 한 줄 입력 (am) */
fresh();
toggleAmVoice();
tick(10);
ok(voice.kind === 'am', '13-1 회원 추가 음성 켜짐');
ok(ELS.amVoiceBtn.classList.contains('rec'), '13-2 회원 추가 버튼에 듣는 중 표시');
voice.inst._result('김민수 10회 남 분당', true, 0);
ok(ELS.quickLine.value === '김민수 10회 남 분당', '13-3 한 줄 입력칸 반영');
ok(quickCount > 0, '13-4 바로 파싱 실행');
toggleAmVoice();
ok(voice.want === false && ELS.parseBar.innerHTML.indexOf('멈췄어요') >= 0, '13-5 취소 안내');
toggleAmVoice();
tick(400);
ok(MockSR.made.length === 2, '13-6 취소 후 다시 시작');
voice.inst._result('박영희 55분 8회 여 판교', true, 0);
ok(ELS.quickLine.value === '김민수 10회 남 분당 박영희 55분 8회 여 판교', '13-7 이어서 인식');
stopVoice();
ok(voice.want === false, '13-8 시트를 닫으면 반납');

/* 14. 오늘 레슨 메모 (tm) */
fresh();
toggleTmVoice();
tick(10);
ok(voice.kind === 'tm' && tmCtx.voiceUsed === false, '14-1 오늘 레슨 메모 음성 켜짐');
ok(ELS.tmVoiceBtn.classList.contains('rec'), '14-2 메모 버튼에 듣는 중 표시');
voice.inst._result('드라이버 백스윙 교정', true, 0);
ok(ELS.tmText.value === '드라이버 백스윙 교정', '14-3 입력칸 반영');
ok(tagPaintCount > 0, '14-4 태그 미리보기 갱신');
ok(tmCtx.voiceUsed === true, '14-5 음성으로 적은 것으로 표시');
toggleTmVoice();
ok(voice.want === false && ELS.tmHint.innerHTML.indexOf('멈췄어요') >= 0, '14-6 취소 안내');

/* 결과 */
JSON.stringify({ pass: log, fail: fails });
"""

ctx = quickjs.Context()
out = ctx.eval(HARNESS)
data = json.loads(out)
for line in data['pass']:
    print(line)
print()
if data['fail']:
    for line in data['fail']:
        print(line)
    print('\n%d FAILED / %d passed' % (len(data['fail']), len(data['pass'])))
    sys.exit(1)
print('ALL %d PASSED' % len(data['pass']))
