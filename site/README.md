# POI 랜딩 페이지

`landing.html` 은 Claude Artifact 형식의 **조각(fragment)** 입니다 — `<!doctype>` / `<html>` /
`<head>` / `<body>` 없이 `<title>` + `<style>` + 본문만 들어 있습니다. Artifact 로 게시하면
호스트가 감싸줍니다.

일반 웹서버에 올리려면 아래처럼 감싸면 됩니다:

```html
<!doctype html>
<html lang="ko">
<head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"></head>
<body>
  <!-- landing.html 내용 붙여넣기 -->
</body>
</html>
```

게시된 아티팩트: 대화에서 `/artifacts` 로 확인.
