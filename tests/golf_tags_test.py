#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""골프 클럽/영역 자동 태그 분류·필터를 실제 코드로 검사한다."""
import sys, json
import quickjs

HTML = open('/workspace/golf-lesson-app/prototype.html', encoding='utf-8').read()
start = HTML.index("var GOLF_TAGS = [")
end = HTML.index("/* =========================================================\n   카톡 복사용 1초 리포트")
CODE = HTML[start:end]

HARNESS = r"""
var state = { members: [], packages: [], sessions: [], notes: [] };
var memberCtx = null;
function esc(s){ return String(s === null || s === undefined ? '' : s); }
function document(){ return { getElementById: function(){ return null; } }; }
""" + CODE + r"""

var fails = [], log = [];
function ok(c, n){ if (c) log.push('PASS ' + n); else fails.push('FAIL ' + n); }
function eq(a, b, n){ ok(a === b, n + (a === b ? '' : '\n  got=[' + a + ']\n  want=[' + b + ']')); }
function tags(t){ return detectGolfTags(t).join(','); }

/* 1. 다섯 분류 키워드 (브리프 목록 전부) */
eq(tags('드라이버 티샷'), '드라이버', '1-1 드라이버');
eq(tags('우드 샷'), '드라이버', '1-2 우드');
eq(tags('유틸 하이브리드'), '드라이버', '1-3 유틸');
eq(tags('비거리 늘리기, 슬라이스 교정, 훅 방지'), '드라이버', '1-4 비거리·슬라이스·훅');
eq(tags('7번 아이언'), '아이언', '2-1 아이언');
eq(tags('8번'), '아이언', '2-2 8번');
eq(tags('9번 클럽'), '아이언', '2-3 9번');
eq(tags('피칭웨지'), '아이언,어프로치', '2-4 피칭(두 분류)');
eq(tags('다운블로 임팩트'), '아이언', '2-5 다운블로·임팩트');
eq(tags('핸드퍼스트 유지'), '아이언', '2-6 핸드퍼스트');
eq(tags('어프로치 30m'), '어프로치', '3-1 어프로치');
eq(tags('웨지 거리감'), '어프로치', '3-2 웨지·거리감');
eq(tags('칩샷'), '어프로치', '3-3 칩샷');
eq(tags('피치샷'), '어프로치', '3-4 피치샷');
eq(tags('벙커 탈출'), '어프로치', '3-5 벙커');
eq(tags('로브샷'), '어프로치', '3-6 로브');
eq(tags('퍼팅 스트로크'), '퍼팅', '4-1 퍼팅');
eq(tags('퍼터 그립'), '퍼팅', '4-2 퍼터');
eq(tags('그린 위 라인 읽기'), '퍼팅', '4-3 그린·라인');
eq(tags('숏퍼트'), '퍼팅', '4-4 숏퍼트');
eq(tags('필드 라운딩'), '필드', '5-1 필드·라운딩');
eq(tags('코스 공략, 트러블 샷'), '필드', '5-2 코스·트러블');
eq(tags('파3 티샷'), '드라이버,필드', '5-3 파3+티샷(두 분류, 순서 고정)');

/* 2. 여러 태그는 항상 정해진 순서 (드라이버→아이언→어프로치→퍼팅→필드) */
eq(tags('퍼팅 연습 후 드라이버, 벙커, 필드'), '드라이버,어프로치,퍼팅,필드', '6-1 정규 순서');
eq(tags('필드 나가기 전 퍼팅과 어프로치'), '어프로치,퍼팅,필드', '6-2 정규 순서 2');

/* 3. 골프 키워드가 없으면 빈 배열 */
eq(tags('오늘 컨디션 좋음. 다음 주 예약'), '', '7-1 태그 없음');
eq(tags(''), '', '7-2 빈 문자열');
eq(tags(null), '', '7-3 null 안전');

/* 4. 기록에 붙은 태그 읽기 */
eq(noteTags({ text:'드라이버 교정', tags:['드라이버'] }).join(','), '드라이버', '8-1 저장된 태그 사용');
eq(noteTags({ text:'드라이버 교정', tags:[] }).join(','), '', '8-2 직접 다 지운 태그는 존중');
eq(noteTags({ text:'벙커 연습' }).join(','), '어프로치', '8-3 태그 없는 옛 기록은 본문에서 계산');
eq(noteTags(null).join(','), '', '8-4 null 기록');

/* 5. 필터 카운트 */
var notes = [
  { text:'드라이버 티샷', tags:['드라이버'] },
  { text:'7번 아이언', tags:['아이언'] },
  { text:'드라이버 비거리 + 벙커', tags:['드라이버','어프로치'] },
  { text:'퍼팅', tags:[] }
];
var c = tagFilterCounts(notes);
eq(c['드라이버'], 2, '9-1 드라이버 2건');
eq(c['아이언'], 1, '9-2 아이언 1건');
eq(c['어프로치'], 1, '9-3 어프로치 1건');
eq(c['퍼팅'], 0, '9-4 퍼팅 0건');
eq(c['필드'], 0, '9-5 필드 0건');

/* 6. 태그 칩 HTML */
ok(noteTagHTML('드라이버').indexOf('#드라이버') > 0, '10-1 알약 문구');
ok(noteTagHTML('드라이버').indexOf('t-driver') > 0, '10-2 색 클래스');
eq(noteTagHTML('없는태그'), '', '10-3 모르는 태그는 빈 값');

/* 7. 정렬 도우미 */
eq(sortTags(['퍼팅','드라이버','필드']).join(','), '드라이버,퍼팅,필드', '11-1 sortTags');
eq(sortTags([]).length, 0, '11-2 빈 배열');

/* 8. 대소문자·공백이 섞여도 동작 */
eq(tags('  파3   라운딩  '), '필드', '12-1 공백 여러 개');

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
