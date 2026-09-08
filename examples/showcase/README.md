# POI 쇼케이스 — POI 로만 작성한 웹사이트

`app.poi` 한 파일 + `views/*.html` 템플릿으로 만든 완전한 웹 애플리케이션입니다.
POI 의 웹 기능을 전부 씁니다:

| 기능 | 쓰인 곳 |
|---|---|
| `server { get/post }` | 8개 라우트 |
| `render(name, data)` + 템플릿 엔진 | `views/` (`{% include %}` 로 head/foot 공유) |
| `respond.json` / `redirect` | `/api/run` · `/api/stats` · `/login` |
| `auth` (서명 쿠키 로그인) | `/login` · `/dashboard` · `/logout` |
| `on_request` 미들웨어 | 방문 기록 + `auth.guard("/login", only: ["/dashboard"])` |
| `database(":memory:")` | 회원 · 방문 로그 실시간 집계 |
| `python { }` 상호운용 | `/api/run` 이 `run_source(코드, safe=true)` 로 **POI 가 POI 를 실행** |

## 실행

```bash
poi run examples/showcase/app.poi
# → http://127.0.0.1:8080
```

- `/` — 랜딩 페이지
- `/play` — 브라우저에서 POI 코드를 쳐서 `--safe` 로 실행
- `/dashboard` — 로그인 필요 (`siwon` / `1234` 또는 `admin` / `poi`)

바탕화면의 **`POI 쇼케이스.bat`** 를 더블클릭하면 서버가 뜨고 브라우저가 열립니다.
