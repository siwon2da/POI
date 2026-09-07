# POI 랜딩 페이지

**라이브: https://hagora.kr/poi/**  (Claude Artifact 사본도 있음)

- `landing.html` — Claude Artifact 형식의 **조각(fragment)**. `<!doctype>`/`<html>`/`<head>`/`<body>` 없이
  `<title>` + `<style>` + 본문만. Artifact 로 게시하면 호스트가 감싼다.
- `hagora/index.html` — 위 조각을 감싼 **독립 실행본**. hagora.kr 의 `/poi/` 에 배포된 것과 동일.
- `hagora/.htaccess` — 루트 `.htaccess` 의 rewrite/404 상속을 끊는 빈 `RewriteEngine On` + `DirectorySlash On`
  (하위 정적앱 함정 회피).

## hagora.kr 재배포

`E:\boardhub` 의 `poi/` 폴더에 두 파일을 두고:

```bash
cd E:\boardhub
python _deploy_files.py --go poi/index.html poi/.htaccess
```

(비번 인증 `.env` → `Administrator@125.133.21.128:C:/hansaeng`, SHA-256 검증 포함)

## 조각을 다른 웹서버에 올릴 때

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
