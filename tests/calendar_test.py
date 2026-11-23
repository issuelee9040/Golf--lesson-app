#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""프로토타입에 실제로 들어 있는 외부 캘린더 연동 코드(아이폰 .ics · 구글 템플릿 링크)를
   quickjs로 그대로 실행해 시간 계산 · RFC 5545 형식 · URL 인코딩을 검사한다.

   - 25분 / 55분 레슨의 DTSTART·DTEND 가 KST 벽시계 그대로인지 (자정 넘김 포함)
   - 구글 캘린더 dates 파라미터가 같은 값이고 ctz=Asia/Seoul 로 붙는지
   - .ics 가 RFC 5545(줄바꿈 · 이스케이프 · 75옥텟 접기 · VTIMEZONE)를 지키는지
   - 설정(calendarSync) 기본값과 잘못된 값 보정
"""
import re, json, sys
import quickjs

HTML = open('/workspace/golf-lesson-app/prototype.html', encoding='utf-8').read()

start = HTML.index('var CAL_TARGETS =')
end = HTML.index('/* ---------- 상태 ---------- */')
# 필드 · 숏게임 헬퍼(isSep·sessionName·sepFee…)가 calSummary/calDescLines 안에서 쓰인다
hmark = HTML.index('필드 · 숏게임 (별도 결제) 레슨')
h0 = HTML.rindex('/* =========================================================', 0, hmark)
ENGINE = HTML[h0:start] + HTML[start:end]

HARNESS = r"""
/* ---------- 레슨/회원 스텁 (앱 본체의 조회 함수 자리에 끼움) ---------- */
var state = {
  members: [{ id:'m1', name:'김민준' }],
  packages: [{ id:'p1', memberId:'m1', durationMinutes:55, totalSessions:8, remainingSessions:5 }],
  sessions: []
};
function pad(n){ return n < 10 ? '0' + n : '' + n; }
function memberById(id){ for (var i=0;i<state.members.length;i++) if (state.members[i].id===id) return state.members[i]; return null; }
function pkgById(id){ for (var i=0;i<state.packages.length;i++) if (state.packages[i].id===id) return state.packages[i]; return null; }
function memberName(id){ var m = memberById(id); return m ? m.name : '(삭제된 회원)'; }
function totalRemaining(id){
  var s = 0;
  state.packages.forEach(function(p){ if (p.memberId===id && p.remainingSessions>0) s += p.remainingSessions; });
  return s;
}
function findSession(id){ for (var i=0;i<state.sessions.length;i++) if (state.sessions[i].id===id) return state.sessions[i]; return null; }
function fmtShort(s){ return s; }
function esc(s){ return String(s); }
function money(n){ return Number(n).toLocaleString('ko-KR') + '원'; }
var ICON = { chev: '' };
function toast(){}
function openSheet(){ return { close: function(){} }; }
function save(){}
function document_getElementById(){ return null; }

/* ====TESTS==== */
/* ---------- 검사 도우미 ---------- */
var RESULT = [];
function ok(name, cond, detail){ RESULT.push({ name:name, pass:!!cond, detail: detail || '' }); }
function eq(name, a, b){ ok(name, a === b, 'got=' + a + ' want=' + b); }
function contain(name, hay, needle){ ok(name, String(hay).indexOf(needle) >= 0, 'needle=' + needle); }
function unfold(t){ return t.replace(/\r\n /g, ''); }

var L55 = { id:'lsn_a1', memberId:'m1', packageId:'p1', date:'2026-11-24', startTime:'15:00',
            durationMinutes:55, location:'분당 실내연습장', memo:'드라이버 위주', status:'scheduled' };
var L25 = { id:'lsn_b2', memberId:'m1', packageId:'', date:'2026-11-24', startTime:'09:05',
            durationMinutes:25, location:'', memo:'', status:'scheduled' };
var LNIGHT = { id:'lsn_c3', memberId:'m1', packageId:'p1', date:'2026-12-31', startTime:'23:40',
               durationMinutes:55, location:'판교', memo:'', status:'scheduled' };

/* 1. 시간 계산 */
eq('55분 DTSTART', calStamp(L55.date, L55.startTime, 0), '20261124T150000');
eq('55분 DTEND', calStamp(L55.date, L55.startTime, 55), '20261124T155500');
eq('25분 DTSTART', calStamp(L25.date, L25.startTime, 0), '20261124T090500');
eq('25분 DTEND', calStamp(L25.date, L25.startTime, 25), '20261124T093000');
eq('자정 넘김 DTSTART', calStamp(LNIGHT.date, LNIGHT.startTime, 0), '20261231T234000');
eq('자정 넘김 DTEND(다음 해)', calStamp(LNIGHT.date, LNIGHT.startTime, 55), '20270101T003500');
eq('월말 넘김', calStamp('2026-11-30', '23:50', 25), '20261201T001500');

/* 2. .ics 본문 */
var ics = icsText(L55);
contain('VCALENDAR 시작', ics, 'BEGIN:VCALENDAR');
ok('VCALENDAR 끝', /\r\nEND:VCALENDAR\r\n$/.test(ics), JSON.stringify(ics.slice(-40)));
contain('VERSION', ics, 'VERSION:2.0');
contain('VTIMEZONE', ics, 'TZID:Asia/Seoul');
contain('KST 오프셋', ics, 'TZOFFSETTO:+0900');
contain('DTSTART', ics, 'DTSTART;TZID=Asia/Seoul:20261124T150000');
contain('DTEND', ics, 'DTEND;TZID=Asia/Seoul:20261124T155500');
contain('UID', ics, 'UID:lsn_a1@golf-lesson-app');
ok('DTSTAMP는 UTC(Z)', /DTSTAMP:\d{8}T\d{6}Z/.test(ics), '');
contain('SUMMARY', ics, 'SUMMARY:[골프 레슨] 김민준 · 55분');
contain('LOCATION', ics, 'LOCATION:분당 실내연습장');
contain('VEVENT 종료', ics, 'END:VEVENT');
var bare = ics.replace(/\r\n/g, '');
ok('CRLF만 사용', bare.indexOf('\n') < 0 && bare.indexOf('\r') < 0, '');

/* 3. 펼친 본문 확인 (RFC 5545 접기 되돌리기) */
var flat = unfold(ics);
contain('DESCRIPTION 회원·잔여', flat, '회원: 김민준 · 잔여 5/8회');
contain('DESCRIPTION 레슨', flat, '레슨: 55분');
contain('DESCRIPTION 장소', flat, '장소: 분당 실내연습장');
contain('DESCRIPTION 메모', flat, '메모: 드라이버 위주');
ok('DESCRIPTION 줄바꿈 이스케이프', flat.indexOf('메모: 드라이버 위주\\n레슨 관리 앱에서 추가') >= 0, '');

/* 4. 75옥텟 접기 */
function octets(s){ var n=0; for (var i=0;i<s.length;i++){ var c=s.charCodeAt(i); n += c<0x80?1:(c<0x800?2:(c<0x10000?3:4)); } return n; }
var lines = ics.split('\r\n');
var over = [], badFold = [];
lines.forEach(function(l){
  if (octets(l) > 75) over.push(l);
  if (/^ /.test(l) === false && false) badFold.push(l);
});
ok('모든 물리적 줄 75옥텟 이하', over.length === 0, over.slice(0,2).join(' | '));
ok('한글 포함 SUMMARY도 접힘', octets('SUMMARY:[골프 레슨] 김민준 · 55분') > 30, '');
/* 접힘이 글자 중간에서 끊기지 않았는지: 펼치면 원래 값과 같아야 함 */
contain('펼친 SUMMARY 정상', unfold(ics), 'SUMMARY:[골프 레슨] 김민준 · 55분');

/* 5. 이스케이프 */
var LES = { id:'lsn_d4', memberId:'m1', packageId:'p1', date:'2026-11-25', startTime:'10:00',
            durationMinutes:55, location:'분당, 3번 타석; 실내', memo:'오전 \\ 스윙', status:'scheduled' };
var ics2 = unfold(icsText(LES));
contain('쉼표 이스케이프', ics2, 'LOCATION:분당\\, 3번 타석\\; 실내');
contain('역슬래시 이스케이프', ics2, '메모: 오전 \\\\ 스윙');
ok('이스케이프되지 않은 쉼표 없음', ics2.indexOf('LOCATION:분당, ') < 0, '');

/* 6. 구글 캘린더 URL */
var url = gcalUrl(L55);
contain('구글 TEMPLATE', url, 'https://calendar.google.com/calendar/render?action=TEMPLATE');
contain('구글 dates', url, '&dates=20261124T150000/20261124T155500');
contain('구글 ctz', url, '&ctz=Asia/Seoul');
ok('구글 dates에 Z 없음(현지시각+ctz)', url.indexOf('/20261124T155500Z') < 0, url);
var text = decodeURIComponent(url.split('&text=')[1].split('&dates=')[0]);
eq('구글 text', text, '[골프 레슨] 김민준 · 55분');
contain('구글 location', url, 'location=' + encodeURIComponent('분당 실내연습장'));
contain('구글 details 줄바꿈', url, 'details=' + encodeURIComponent(calDescText(L55)));
var urlNight = gcalUrl(LNIGHT);
contain('구글 자정 넘김', urlNight, '&dates=20261231T234000/20270101T003500');
var url25 = gcalUrl(L25);
contain('구글 25분', url25, '&dates=20261124T090500/20261124T093000');
ok('장소 없으면 location 파라미터 없음', url25.indexOf('&location=') < 0, '');

/* 7. 파일 이름 · UID */
eq('ics 파일 이름', icsFileName(L55), 'golf-lesson-20261124-1500.ics');
eq('같은 레슨은 같은 UID', icsUid(L55), icsUid(L55));

/* 8. 설정 기본값 */
eq('기본 꺼짐', calSync().enabled, false);
eq('기본 대상 둘 다', calSync().target, 'both');
state.calendarSync = { enabled:true, target:'apple' };
eq('아이폰 선택 유지', calSync().target, 'apple');
eq('켜짐 유지', calSync().enabled, true);
state.calendarSync.target = 'naver';
eq('잘못된 대상 보정', calSync().target, 'both');
state.calendarSync.enabled = 'yes';
eq('문자열 켜짐은 꺼짐으로', calSync().enabled, false);
eq('대상 라벨', calTargetLabel('google'), '구글 캘린더');

JSON.stringify(RESULT);
"""

PRE, TESTS = HARNESS.split('/* ====TESTS==== */')
ctx = quickjs.Context()
try:
    out = ctx.eval(PRE + '\n' + ENGINE + '\n' + TESTS + '\nJSON.stringify(RESULT);')
except Exception as e:
    print('실행 오류:', e)
    sys.exit(1)

results = json.loads(out)
failed = [r for r in results if not r['pass']]
for r in results:
    print(('PASS  ' if r['pass'] else 'FAIL  ') + r['name'] + ('' if r['pass'] else '  → ' + str(r['detail'])))
print('\n%d/%d 통과' % (len(results) - len(failed), len(results)))
sys.exit(1 if failed else 0)
