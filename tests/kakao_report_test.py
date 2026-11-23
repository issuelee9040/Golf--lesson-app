#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""카톡 복사용 1초 리포트의 문구 형식을 실제 코드로 검사한다."""
import sys, json
import quickjs

HTML = open('/workspace/golf-lesson-app/prototype.html', encoding='utf-8').read()
start = HTML.index("function kakaoMD(date){")
end = HTML.index("/* =========================================================\n   회원 정보창 (레슨 차트 포함)")
# 카톡 리포트가 쓰는 필드 · 숏게임 헬퍼(isSep·sessionName·sepFee…)를 실제 코드에서 함께 가져온다
hmark = HTML.index('필드 · 숏게임 (별도 결제) 레슨')
h0 = HTML.rindex('/* =========================================================', 0, hmark)
h1 = HTML.index('/* =========================================================\n   외부 캘린더 연동')
CODE = HTML[h0:h1] + HTML[start:end]

HARNESS = r"""
var WEEK = ['일','월','화','수','목','금','토'];
var TODAY = '2026-11-23';
function todayISO(){ return TODAY; }
function parseISO(s){ var p = String(s).split('-'); return new Date(+p[0], (+p[1]) - 1, +p[2]); }
function minOf(t){ var p = String(t || '00:00').split(':'); return (+p[0]) * 60 + (+p[1] || 0); }
function esc(s){ return String(s === null || s === undefined ? '' : s); }
function pkgById(id){ for (var i=0;i<state.packages.length;i++) if (state.packages[i].id === id) return state.packages[i]; return null; }
function memberName(id){ var m = memberById(id); return m ? m.name : '(삭제된 회원)'; }
function money(n){ return Number(n).toLocaleString('ko-KR') + '원'; }
function memberById(id){ for (var i=0;i<state.members.length;i++) if (state.members[i].id === id) return state.members[i]; return null; }
function findSession(id){ for (var i=0;i<state.sessions.length;i++) if (state.sessions[i].id === id) return state.sessions[i]; return null; }
function memberPkgs(id){ return state.packages.filter(function(p){ return p.memberId === id; }); }
function activePkgs(id){ return memberPkgs(id).filter(function(p){ return p.remainingSessions > 0; }); }
function notesByMember(mid){
  return state.notes.filter(function(n){ return n.memberId === mid; }).sort(function(a, b){
    if (a.date === b.date) return a.createdAt < b.createdAt ? 1 : -1;
    return a.date < b.date ? 1 : -1;
  });
}
function lastPkgOf(mid){
  var list = memberPkgs(mid);
  return list.length ? list[list.length - 1] : null;
}
var state = { pro: { name: '이시훈' }, members: [], packages: [], sessions: [], notes: [] };
""" + CODE + r"""

var fails = [], log = [];
function ok(c, n){ if (c) log.push('PASS ' + n); else fails.push('FAIL ' + n); }
function eq(a, b, n){ ok(a === b, n + (a === b ? '' : '\n  got=[' + a + ']\n  want=[' + b + ']')); }

function reset(){
  state.members = [{ id:'m1', name:'김도현' }];
  state.packages = [{ id:'p1', memberId:'m1', durationMinutes:55, totalSessions:10, remainingSessions:4 }];
  state.sessions = [{ id:'s1', memberId:'m1', packageId:'p1', date:'2026-11-21', startTime:'07:00',
    durationMinutes:55, memo:'' }];
  state.notes = [];
}
reset();

/* 1. 기본 4줄 형식 */
state.notes = [{ id:'n1', memberId:'m1', date:'2026-11-21', text:'드라이버 백스윙 교정. 오른팔 펴기 유지.', createdAt:'2026-11-21T20:00:00' }];
eq(kakaoReportForSession('s1'),
  '[이시훈 프로 레슨 노트]\n' +
  '김도현님 · 11/21(토) 07:00 (55분)\n' +
  '잔여 횟수: 4/10회\n' +
  '오늘 포인트: 드라이버 백스윙 교정. 오른팔 펴기 유지.',
  '1-1 4줄 리포트 형식');

/* 2. 요일 계산 (2026-11-22 = 일, 2026-11-23 = 월) */
state.sessions[0].date = '2026-11-22';
state.notes[0].date = '2026-11-22';
ok(kakaoReportForSession('s1').indexOf('11/22(일)') > 0, '2-1 일요일 표기');
state.sessions[0].date = '2026-11-23';
state.notes[0].date = '2026-11-23';
ok(kakaoReportForSession('s1').indexOf('11/23(월)') > 0, '2-2 월요일 표기');

/* 3. 25분 레슨 표기 */
state.sessions[0].durationMinutes = 25;
ok(kakaoReportForSession('s1').indexOf('07:00 (25분)') > 0, '3-1 25분 표기');

/* 4. 그 날짜 기록이 없으면 레슨 메모 */
reset();
state.sessions[0].memo = '어프로치 거리감 위주';
eq(kakaoReportForSession('s1'),
  '[이시훈 프로 레슨 노트]\n김도현님 · 11/21(토) 07:00 (55분)\n잔여 횟수: 4/10회\n오늘 포인트: 어프로치 거리감 위주',
  '4-1 기록 없음 → 레슨 메모');

/* 5. 기록도 메모도 없으면 회원의 최근 기록 */
reset();
state.notes = [{ id:'n9', memberId:'m1', date:'2026-11-10', text:'퍼팅 스트로크 교정', createdAt:'2026-11-10T20:00:00' }];
eq(kakaoReportForSession('s1'),
  '[이시훈 프로 레슨 노트]\n김도현님 · 11/21(토) 07:00 (55분)\n잔여 횟수: 4/10회\n오늘 포인트: 퍼팅 스트로크 교정',
  '5-1 없으면 회원 최근 기록');

/* 6. 포인트가 전혀 없으면 그 줄은 빠진다 */
reset();
ok(kakaoReportForSession('s1').indexOf('오늘 포인트') < 0, '6-1 포인트 없으면 줄 생략');
eq(kakaoReportForSession('s1').split('\n').length, 3, '6-2 세 줄만');

/* 7. 수강권이 없으면 잔여 줄은 빠진다 */
reset();
state.sessions[0].packageId = '';
state.packages = [];
eq(kakaoReportForSession('s1'),
  '[이시훈 프로 레슨 노트]\n김도현님 · 11/21(토) 07:00 (55분)',
  '7-1 수강권 없으면 잔여 줄 생략');

/* 8. 긴 포인트는 160자로 줄이고 말줄임 */
reset();
state.notes = [{ id:'n2', memberId:'m1', date:'2026-11-21', text: new Array(300).join('가'), createdAt:'2026-11-21T21:00:00' }];
var rep = kakaoReportForSession('s1');
var pl = rep.split('\n')[3];
eq(pl.slice(0, 8), '오늘 포인트: ', '8-1 접두어');
ok(pl.length <= '오늘 포인트: '.length + 161, '8-2 길이 제한: ' + pl.length);
ok(pl.slice(-1) === '…', '8-3 말줄임');

/* 9. 줄바꿈·연속 공백은 한 줄로 정리 */
reset();
state.notes = [{ id:'n3', memberId:'m1', date:'2026-11-21', text:'드라이버  교정\n\n오른팔 유지', createdAt:'2026-11-21T21:00:00' }];
ok(kakaoReportForSession('s1').indexOf('오늘 포인트: 드라이버 교정 오른팔 유지') > 0, '9-1 공백 정리');

/* 10. 프로 이름은 설정값을 따른다 */
reset();
state.pro.name = '박프로';
ok(kakaoReportForSession('s1').indexOf('[박프로 프로 레슨 노트]') === 0, '10-1 프로 이름 반영');
state.pro.name = '이시훈';

/* 11. 회원 단위 복사 = 가장 최근 지난 레슨 */
reset();
state.sessions.push({ id:'s2', memberId:'m1', packageId:'p1', date:'2026-11-23', startTime:'19:00', durationMinutes:55, memo:'오늘 레슨' });
state.sessions.push({ id:'s3', memberId:'m1', packageId:'p1', date:'2026-11-30', startTime:'07:00', durationMinutes:55, memo:'미래 레슨' });
ok(kakaoReportForMember('m1').indexOf('11/23(월) 19:00') > 0, '11-1 오늘 레슨을 고름');
ok(kakaoReportForMember('m1').indexOf('오늘 레슨') > 0, '11-2 오늘 메모 사용');

/* 12. 지난 레슨이 없으면 가장 가까운 예정 레슨 */
reset();
state.sessions = [{ id:'s4', memberId:'m1', packageId:'p1', date:'2026-11-30', startTime:'07:00', durationMinutes:55, memo:'예정' }];
ok(kakaoReportForMember('m1').indexOf('11/30(월) 07:00') > 0, '12-1 예정 레슨 사용');

/* 13. 레슨이 아예 없으면 오늘 날짜·최근 기록으로 */
state.sessions = [];
state.notes = [{ id:'n4', memberId:'m1', date:'2026-11-20', text:'칩샷 연습', createdAt:'2026-11-20T20:00:00' }];
eq(kakaoReportForMember('m1'),
  '[이시훈 프로 레슨 노트]\n김도현님 · 11/23(월) (55분)\n잔여 횟수: 4/10회\n오늘 포인트: 칩샷 연습',
  '13-1 레슨 없음 → 오늘 날짜');

/* 14. 없는 레슨/회원은 빈 문자열 */
eq(kakaoReportForSession('nope'), '', '14-1 없는 레슨');
eq(kakaoReportForMember('nope'), '', '14-2 없는 회원');

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
