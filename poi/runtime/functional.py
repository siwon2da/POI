"""함수형 데이터 처리 (v1.3).

전부 목록을 **첫 인자**로 받는다 → 파이프라인과 자연스럽게 이어진다.

    nums
        |> filter(x => x > 0)
        |> map(x => x * 2)
        |> sum_of
"""
from __future__ import annotations

from functools import reduce as _reduce

from ..errors import POIError
from .boxes import boxify


def _seq(xs):
    if isinstance(xs, (list, tuple)):
        return list(xs)
    try:
        return list(xs)
    except TypeError:
        raise POIError("목록이 아닌 값에는 이 기능을 쓸 수 없습니다.", "P150")


def poi_map(xs, fn):
    return [fn(x) for x in _seq(xs)]


def poi_filter(xs, fn):
    return [x for x in _seq(xs) if fn(x)]


def poi_reject(xs, fn):
    return [x for x in _seq(xs) if not fn(x)]


def poi_reduce(xs, fn, init=None):
    s = _seq(xs)
    return _reduce(fn, s) if init is None else _reduce(fn, s, init)


def poi_each(xs, fn):
    for x in _seq(xs):
        fn(x)
    return xs


def poi_find(xs, fn):
    for x in _seq(xs):
        if fn(x):
            return x
    return None


def poi_find_index(xs, fn):
    for i, x in enumerate(_seq(xs)):
        if fn(x):
            return i
    return -1


def poi_count_where(xs, fn):
    return sum(1 for x in _seq(xs) if fn(x))


def poi_any_of(xs, fn):
    return any(fn(x) for x in _seq(xs))


def poi_all_of(xs, fn):
    return all(fn(x) for x in _seq(xs))


def poi_sort_by(xs, fn, desc=False):
    return sorted(_seq(xs), key=fn, reverse=desc)


def poi_sort_desc(xs):
    return sorted(_seq(xs), reverse=True)


def poi_group_by(xs, fn):
    out: dict = {}
    for x in _seq(xs):
        out.setdefault(fn(x), []).append(x)
    return boxify(out)


def poi_partition(xs, fn):
    yes, no = [], []
    for x in _seq(xs):
        (yes if fn(x) else no).append(x)
    return [yes, no]


def poi_take(xs, n):
    return _seq(xs)[:max(0, int(n))]


def poi_drop(xs, n):
    return _seq(xs)[max(0, int(n)):]


def poi_take_while(xs, fn):
    out = []
    for x in _seq(xs):
        if not fn(x):
            break
        out.append(x)
    return out


def poi_drop_while(xs, fn):
    s = _seq(xs)
    i = 0
    while i < len(s) and fn(s[i]):
        i += 1
    return s[i:]


def poi_unique(xs):
    seen = []
    out = []
    for x in _seq(xs):
        if x not in seen:
            seen.append(x)
            out.append(x)
    return out


def poi_flatten(xs):
    out = []
    for x in _seq(xs):
        if isinstance(x, (list, tuple)):
            out.extend(x)
        else:
            out.append(x)
    return out


def poi_chunk(xs, n):
    s = _seq(xs)
    n = max(1, int(n))
    return [s[i:i + n] for i in range(0, len(s), n)]


def poi_zip_with(a, b):
    return [[x, y] for x, y in zip(_seq(a), _seq(b))]


def poi_sum_of(xs):
    return sum(_seq(xs))


def poi_avg(xs):
    s = _seq(xs)
    if not s:
        return 0
    return sum(s) / len(s)


def poi_min_of(xs):
    s = _seq(xs)
    return min(s) if s else None


def poi_max_of(xs):
    s = _seq(xs)
    return max(s) if s else None


def poi_count_of(xs):
    return len(_seq(xs))


def poi_reverse_of(xs):
    return list(reversed(_seq(xs)))


def poi_range_list(n, start=0, step=1):
    return list(range(int(start), int(n), int(step)))


def poi_repeat_list(value, n):
    return [value for _ in range(int(n))]


EXPORTS = {
    "map": poi_map, "filter": poi_filter, "reject": poi_reject,
    "reduce": poi_reduce, "each": poi_each, "find": poi_find,
    "find_index": poi_find_index, "count_where": poi_count_where,
    "any_of": poi_any_of, "all_of": poi_all_of,
    "sort_by": poi_sort_by, "sort_desc": poi_sort_desc,
    "group_by": poi_group_by, "partition": poi_partition,
    "take": poi_take, "drop": poi_drop,
    "take_while": poi_take_while, "drop_while": poi_drop_while,
    "unique": poi_unique, "flatten": poi_flatten, "chunk": poi_chunk,
    "zip_with": poi_zip_with,
    "sum_of": poi_sum_of, "avg": poi_avg, "min_of": poi_min_of,
    "max_of": poi_max_of, "count_of": poi_count_of, "reverse_of": poi_reverse_of,
    "range_list": poi_range_list, "repeat_list": poi_repeat_list,
}
