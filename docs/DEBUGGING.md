# POI 디버깅 (v1.1)

코드를 고치지 않고도 흐름과 값을 들여다본다. 세 갈래.

## 1. 코드 안에서 — `inspect` · `watch` · `pause`

이 셋은 import 없이 바로 쓴다.

### `inspect(x)`
값의 **타입 · 크기 · 속** 을 예쁘게 출력하고, `x` 를 **그대로 반환**한다.

```poi
user = { name: "시원", age: 16, tags: ["a", "b"] }
inspect(user)
```
```
객체  3개 항목
  .name: Text = '시원'
  .age: Int = 16
  .tags: List (2개)
```

### `watch(x)`
`inspect` 하면서 `x` 를 **흘려보낸다**. 한 줄도 안 끊긴다.

```poi
final = watch(price_with_tax(total, 0.1))   # 값도 보고, final 에 담기도 하고
nums |> watch |> filter("> 0")              # 파이프라인 중간 점검
```

### `pause()`
그 줄에서 **멈춘다**. 지역 변수를 보여주고, 식을 쳐보게 하고, 계속.

```poi
fn price_with_tax(base, rate) {
    tax = base * rate
    pause()                 # ← 여기서 멈춤
    return base + tax
}
```
```
⏸  일시정지  (줄 3)
│ tax = base * rate
│ 지역 변수: base, rate, tax
│ 식을 입력하면 계산해 봅니다.  vars=전체보기  c/Enter=계속  q=중단
(pause) base * rate
  550.0
(pause)                     ← Enter 로 계속
```

`pause("라벨")` 로 이름을 붙일 수 있다.

## 2. 실행할 때 — `--trace` · `--vars` · `--explain`

### `poi run 파일.poi --trace`
문장이 실행될 때마다 **줄번호 + 소스** 를 stderr 에 찍는다.

```
╎  10 │ for item in cart {
╎  11 │ total = total + item
╎  11 │ total = total + item
```

### `--vars`  (자동으로 `--trace` 포함)
값이 바뀌면 그 변수도 같이.

```
╎  11 │ total = total + item
╎      → total = 4600
╎      → item  = 900
```

### `--explain`
오류가 났을 때, POI 오류 메시지 **아래에** 그 순간의 지역 변수까지.

```
POI Error P103
  숫자와 문자를 함께 계산할 수 없습니다.
  ...
── 자세히 (--explain) ──
      3 │ money = "1000"
  >   4 │ total = money + 500
      5 │ show total
  그때 값들:
    money: Text = '1000'
```

## 3. 한 번에 — `poi debug`

```bash
poi debug 파일.poi
```

`--trace --vars --explain` 을 모두 켠 것. "왜 이렇게 되지?" 싶을 때 이거 하나.

## 끄기

자동 새 버전 확인만 끄려면 `POI_NO_UPDATE_CHECK=1`.
디버깅 출력은 플래그를 안 주면 안 나온다 (기본은 조용함).
