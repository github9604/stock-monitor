# 🚀 빠른 시작 가이드

## 5분 안에 설정 완료하기

### 1️⃣ 노션 API 키 발급 (1분)

1. https://www.notion.so/my-integrations 접속
2. "+ New integration" 클릭
3. 이름: "Stock Monitor" 입력
4. Submit → **토큰 복사** (secret_... 형식)

### 2️⃣ 노션 데이터베이스 연결 (30초)

1. 노션에서 "📈 실시간 주식 모니터링" 페이지 열기
2. 우측 상단 **⋯ → Connections** 클릭  
3. "Stock Monitor" 선택

### 3️⃣ GitHub 레포지토리 생성 (1분)

1. GitHub.com → "+ New repository"
2. 이름: `stock-monitor` (Public 권장)
3. Create repository

### 4️⃣ 코드 업로드 (1분)

```bash
cd stock-monitor
git init
git add .
git commit -m "Initial commit"
git remote add origin https://github.com/YOUR_USERNAME/stock-monitor.git
git push -u origin main
```

또는 **GitHub 웹에서 직접 업로드**:
- "Add file" → "Upload files"
- 모든 파일 드래그 앤 드롭

### 5️⃣ GitHub Secrets 설정 (2분)

레포지토리 → **Settings** → **Secrets and variables** → **Actions**

**New repository secret** 클릭하여 3개 추가:

#### Secret 1: `NOTION_API_KEY`
```
secret_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
```
(1단계에서 복사한 토큰)

#### Secret 2: `NOTION_DATABASE_ID`  
```
2615eba7-9f12-4c2b-8bac-a64b28784005
```

#### Secret 3: `STOCK_TICKERS`
```json
[
  {"ticker": "AAPL", "market": "미국"},
  {"ticker": "MSFT", "market": "미국"},
  {"ticker": "TSLA", "market": "미국"},
  {"ticker": "005930.KS", "market": "한국"},
  {"ticker": "035720.KS", "market": "한국"}
]
```

### 6️⃣ 테스트 실행 (30초)

1. 레포지토리 → **Actions** 탭
2. "📈 주식 데이터 자동 업데이트" 클릭
3. **"Run workflow"** → "Run workflow" 확인

### ✅ 완료!

- 5분마다 자동으로 주가 업데이트됨
- 노션 데이터베이스에서 실시간 확인 가능

---

## 💡 자주 묻는 질문

**Q: 무료인가요?**  
A: 네! 완전 무료입니다. GitHub Actions 퍼블릭 레포지토리는 무제한.

**Q: 몇 개 종목까지 가능한가요?**  
A: 이론적으로 제한 없지만, 100개 이하 권장 (API 제한 방지)

**Q: 한국 주식도 되나요?**  
A: 네! 티커에 `.KS` (코스피) 또는 `.KQ` (코스닥) 붙이면 됩니다.

**Q: 업데이트 주기를 바꿀 수 있나요?**  
A: 네! `.github/workflows/update-stocks.yml`에서 `cron` 값 수정하세요.

---

## 📞 도움이 필요하면?

GitHub Issues에 질문 남겨주세요!
