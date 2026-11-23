#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""회원목록 정렬(잔여 많은 순 / 이름순 / 잔여 적은 순)을 실제 코드로 검사한다."""
import sys, json
import quickjs

HTML = open('/workspace/golf-lesson-app/prototype.html', encoding='utf-8').read()
start = HTML.index("var MEMBER_SORTS = [")
end = HTML.index("function memberRowsHTML(list){")
CODE = HTML[start:end]

HARNESS = r"""
var ui = { search: '' };
var state = { members: [] };
var REM = {};
var pickerFields = {};
function totalRemaining(id){ return REM[id] || 0; }
""" + CODE + r"""

var fails = [], log = [];
function ok(c, n){ if (c) log.push('PASS ' + n); else fails.push('FAIL ' + n); }
function names(){ return filteredMembers().map(function(m){ return m.name; }).join(','); }

function setup(list, sort){
  state.members = list.map(function(x){ return { id:x[0], name:x[1], region:x[2] || '', phone:'', level:'', memo:'' }; });
  list.forEach(function(x){ REM[x[0]] = x[3]; });
  state.memberSort = sort;
  ui.search = '';
}
var BASE = [
  ['m1','김민준','분당',7],
  ['m2','이서연','판교',3],
  ['m3','박지훈','강남',10],
  ['m4','강하늘','',0]
];

/* 1. 기본 = 잔여 많은 순 */
setup(BASE, undefined);
ok(memberSortMode() === 'remaining', '1-1 기본값은 잔여 많은 순');
ok(names() === '박지훈,김민준,이서연,강하늘', '1-2 잔여 많은 순 정렬: ' + names());

/* 2. 이름순 (가나다) */
setup(BASE, 'name');
ok(memberSortMode() === 'name', '2-1 이름순 선택');
ok(names() === '강하늘,김민준,박지훈,이서연', '2-2 가나다순 정렬: ' + names());

/* 3. 잔여 적은 순 */
setup(BASE, 'remaining-asc');
ok(names() === '강하늘,이서연,김민준,박지훈', '3-1 잔여 적은 순 정렬: ' + names());

/* 4. 잔여가 같으면 이름순 */
setup([['a','정하윤','',5],['b','김도윤','',5],['c','서지우','',9]], 'remaining');
ok(names() === '서지우,김도윤,정하윤', '4-1 동률이면 이름순: ' + names());

/* 5. 잘못된 값은 기본으로 */
setup(BASE, 'garbage');
ok(memberSortMode() === 'remaining', '5-1 알 수 없는 값은 잔여 많은 순');
ok(memberSortLabel('garbage') === '잔여 많은 순', '5-2 라벨도 기본');

/* 6. 검색 + 정렬 동시 */
setup(BASE, 'name');
ui.search = '분당';
ok(names() === '김민준', '6-1 검색 결과에도 정렬 유지: ' + names());
ui.search = '';

/* 7. 원본 배열 보존 */
setup(BASE, 'name');
var orig = state.members.map(function(m){ return m.name; }).join(',');
filteredMembers();
ok(state.members.map(function(m){ return m.name; }).join(',') === orig, '7-1 state.members 순서 안 바뀜');

/* 8. 회원이 없을 때 */
setup([], 'name');
ok(filteredMembers().length === 0, '8-1 빈 목록 안전');

/* 9. 멤버 객체에 totalRemaining이 없어도 동작 */
ok(MEMBER_SORTS.length === 3 && MEMBER_SORTS[1].v === 'name', '9-1 정렬 선택지 3개');

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
