# 📈 실시간 주식 모니터링 - 노션 자동화

한국 & 미국 주식의 실시간 가격, 기술적 지표, 밸류에이션을 자동으로 수집하여 노션 데이터베이스를 업데이트합니다.

## ✨ 기능

- ✅ **실시간 주가 수집** (5분마다 자동 업데이트)
- ✅ **기술적 지표 계산**: SMA20/50/200, RSI30, 골든크로스/데드크로스
- ✅ **밸류에이션**: PER, PBR, 시가총액
- ✅ **거래량 분석**: 5일 평균 대비 거래량 비율
- ✅ **52주 최고가/최저가** 추적
- ✅ **완전 무료** (GitHub Actions 무료 티어 사용)

## 🚀 설치 방법

### 1. GitHub 레포지토리 생성

1. GitHub에 새 레포지토리 생성 (Public 또는 Private)
2. 이 폴더의 모든 파일을 레포지토리에 업로드

### 2. 노션 API 키 발급

1. [Notion Integrations](https://www.notion.so/my-integrations) 접속
2. **"+ New integration"** 클릭
3. 이름 입력 (예: "Stock Monitor") 후 생성
4. **Internal Integration Token** 복사 (나중에 사용)

### 3. 노션 데이터베이스 연결

1. 노션에서 "📈 실시간 주식 모니터링" 데이터베이스 열기
2. 우측 상단 **"⋯" → "Connections"** 클릭
3. 방금 만든 Integration 선택하여 연결

### 4. GitHub Secrets 설정

GitHub 레포지토리 → **Settings** → **Secrets and variables** → **Actions** → **New repository secret**

다음 3개의 Secret 추가:

#### `NOTION_API_KEY`
- Value: 위에서 복사한 Integration Token

#### `NOTION_DATABASE_ID`
- Value: `2615eba7-9f12-4c2b-8bac-a64b28784005`

#### `STOCK_TICKERS` (선택사항)
추적할 종목을 JSON 형식으로 지정. 예:

```json
[
  {"ticker": "AAPL", "market": "미국"},
  {"ticker": "MSFT", "market": "미국"},
  {"ticker": "NVDA", "market": "미국"},
  {"ticker": "005930.KS", "market": "한국"},
  {"ticker": "000660.KS", "market": "한국"}
]
```

⚠️ **한국 주식은 반드시 `.KS` (코스피) 또는 `.KQ` (코스닥) 접미사 필요**

### 5. 자동 실행 활성화

1. GitHub 레포지토리 → **Actions** 탭
2. "📈 주식 데이터 자동 업데이트" 워크플로우 활성화
3. **"Run workflow"** 클릭하여 수동 실행으로 테스트

## ⚙️ 업데이트 주기 변경

`.github/workflows/update-stocks.yml` 파일에서 `cron` 수정:

```yaml
schedule:
  - cron: '*/5 * * * *'  # 5분마다
  # - cron: '*/15 * * * *'  # 15분마다
  # - cron: '0 * * * *'  # 매 시간
```

## 📊 노션 데이터베이스 구조

자동으로 수집되는 속성:

- **종목명**: 회사명
- **티커**: 종목 코드
- **시장**: 한국/미국
- **현재가**: 실시간 주가
- **등락률**: 전일 대비 %
- **거래량**: 당일 거래량
- **5일평균거래량대비**: 거래량 급증/감소 파악
- **SMA20/50/200**: 이동평균선
- **RSI30**: 과매수/과매도 지표
- **PER/PBR**: 밸류에이션
- **시가총액**: 억원/백만달러
- **52주 최고가/최저가**
- **골든크로스/데드크로스**: 추세 전환 신호
- **업데이트시각**: 마지막 업데이트 시간

## 🛠️ 로컬 테스트

```bash
# 의존성 설치
pip install -r requirements.txt

# 환경변수 설정
export NOTION_API_KEY="your_api_key"
export NOTION_DATABASE_ID="2615eba7-9f12-4c2b-8bac-a64b28784005"

# 실행
python update_stocks.py
```

## 📝 종목 추가/제거

### 방법 1: GitHub Secrets 수정
`STOCK_TICKERS` Secret을 수정하여 종목 추가/제거

### 방법 2: 코드 수정
`update_stocks.py` 파일의 `stocks` 리스트 직접 수정

## ⚠️ 주의사항

1. **Yahoo Finance API 제한**: 너무 많은 종목 (100개 이상)은 API 제한에 걸릴 수 있음
2. **한국 주식 티커**: 반드시 `.KS` (코스피) 또는 `.KQ` (코스닥) 붙이기
3. **시장 휴장일**: 주말/공휴일에도 스크립트는 실행되지만 데이터는 업데이트 안 됨
4. **GitHub Actions 무료 티어**: 퍼블릭 레포지토리는 무제한, 프라이빗은 월 2,000분

## 🔧 트러블슈팅

### "403 Forbidden" 오류
→ 노션 데이터베이스에 Integration이 연결되었는지 확인

### "404 Not Found" 오류  
→ `NOTION_DATABASE_ID`가 정확한지 확인

### 한국 주식 데이터 안 나옴
→ 티커에 `.KS` 또는 `.KQ` 붙였는지 확인

### GitHub Actions가 실행 안 됨
→ Actions 탭에서 워크플로우가 활성화되었는지 확인

## 📧 문의

문제가 있으면 GitHub Issues에 남겨주세요!

---

Made with ❤️ by Claude
