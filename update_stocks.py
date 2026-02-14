#!/usr/bin/env python3
"""
실시간 주식 모니터링 - 노션 자동 업데이트
한국 & 미국 주식의 가격, 기술적 지표, 밸류에이션을 자동으로 수집하여 노션 데이터베이스를 업데이트합니다.
"""

import os
import json
from datetime import datetime, timezone
from typing import Dict, List, Optional
import yfinance as yf
import numpy as np
import requests


# 노션 API 설정
NOTION_API_KEY = os.environ.get('NOTION_API_KEY')
NOTION_DATABASE_ID = os.environ.get('NOTION_DATABASE_ID', '2615eba7-9f12-4c2b-8bac-a64b28784005')
NOTION_HEADERS = {
    "Authorization": f"Bearer {NOTION_API_KEY}",
    "Content-Type": "application/json",
    "Notion-Version": "2022-06-28"
}


def calculate_rsi(prices: np.ndarray, period: int = 30) -> float:
    """RSI 계산"""
    if len(prices) < period + 1:
        return None
    
    deltas = np.diff(prices)
    gains = np.where(deltas > 0, deltas, 0)
    losses = np.where(deltas < 0, -deltas, 0)
    
    avg_gain = np.mean(gains[:period])
    avg_loss = np.mean(losses[:period])
    
    for i in range(period, len(deltas)):
        avg_gain = (avg_gain * (period - 1) + gains[i]) / period
        avg_loss = (avg_loss * (period - 1) + losses[i]) / period
    
    if avg_loss == 0:
        return 100
    
    rs = avg_gain / avg_loss
    rsi = 100 - (100 / (1 + rs))
    return round(rsi, 2)


def calculate_sma(prices: np.ndarray, period: int) -> Optional[float]:
    """단순 이동평균 계산"""
    if len(prices) < period:
        return None
    return round(np.mean(prices[-period:]), 2)


def determine_ma_signal(current_price: float, sma20: float, sma50: float, sma200: float) -> str:
    """이동평균선 배열 상태 판단"""
    if not all([sma20, sma50, sma200]):
        return "-"
    
    # 정배열: 단기 > 중기 > 장기
    if sma20 > sma50 > sma200:
        return "정배열"
    # 역배열: 단기 < 중기 < 장기
    elif sma20 < sma50 < sma200:
        return "역배열"
    # 골든크로스 (20일선이 50일선 돌파)
    elif sma20 > sma50:
        return "골든크로스 (20>50)"
    # 골든크로스 (50일선이 200일선 돌파)
    elif sma50 > sma200:
        return "골든크로스 (50>200)"
    # 데드크로스 (20일선이 50일선 하향 돌파)
    elif sma20 < sma50:
        return "데드크로스 (20<50)"
    # 데드크로스 (50일선이 200일선 하향 돌파)
    elif sma50 < sma200:
        return "데드크로스 (50<200)"
    else:
        return "-"


def get_stock_data(ticker: str, market: str) -> Optional[Dict]:
    """주식 데이터 수집"""
    try:
        stock = yf.Ticker(ticker)
        
        # 히스토리 데이터 가져오기 (최대 1년)
        hist = stock.history(period="1y")
        if hist.empty:
            print(f"❌ {ticker}: 데이터 없음")
            return None
        
        info = stock.info
        current_price = hist['Close'].iloc[-1]
        
        # 5일 평균 거래량
        avg_volume_5d = hist['Volume'].tail(5).mean()
        current_volume = hist['Volume'].iloc[-1]
        volume_ratio = (current_volume / avg_volume_5d - 1) if avg_volume_5d > 0 else 0
        
        # 이동평균 계산
        closes = hist['Close'].values
        sma20 = calculate_sma(closes, 20)
        sma50 = calculate_sma(closes, 50)
        sma200 = calculate_sma(closes, 200)
        
        # RSI 계산
        rsi30 = calculate_rsi(closes, 30)
        
        # 52주 최고/최저
        high_52w = hist['High'].max()
        low_52w = hist['Low'].min()
        
        # 등락률 계산
        prev_close = hist['Close'].iloc[-2] if len(hist) > 1 else current_price
        change_pct = (current_price / prev_close - 1) if prev_close > 0 else 0
        
        # 골든크로스/데드크로스 판단
        ma_signal = determine_ma_signal(current_price, sma20, sma50, sma200)
        
        # 시가총액 (억원/백만달러)
        market_cap = info.get('marketCap')
        if market_cap:
            if market == "한국":
                market_cap = market_cap / 100_000_000  # 억원
            else:
                market_cap = market_cap / 1_000_000  # 백만달러
        
        data = {
            "종목명": info.get('longName') or info.get('shortName') or ticker,
            "티커": ticker,
            "시장": market,
            "현재가": round(current_price, 2),
            "등락률": round(change_pct, 4),  # 0.0123 형식 (1.23%)
            "거래량": int(current_volume),
            "5일평균거래량대비": round(volume_ratio, 4),
            "SMA20": sma20,
            "SMA50": sma50,
            "SMA200": sma200,
            "RSI30": rsi30,
            "PER": info.get('trailingPE'),
            "PBR": info.get('priceToBook'),
            "시가총액": round(market_cap, 2) if market_cap else None,
            "52주최고가": round(high_52w, 2),
            "52주최저가": round(low_52w, 2),
            "골든크로스데드크로스": ma_signal,
            "업데이트시각": datetime.now(timezone.utc).isoformat()
        }
        
        print(f"✅ {ticker} ({data['종목명']}): {current_price:,.2f} ({change_pct*100:+.2f}%)")
        return data
        
    except Exception as e:
        print(f"❌ {ticker} 오류: {str(e)}")
        return None


def get_existing_pages() -> Dict[str, str]:
    """노션 DB의 기존 페이지 조회 (티커 -> page_id 매핑)"""
    url = f"https://api.notion.com/v1/databases/{NOTION_DATABASE_ID}/query"
    all_pages = {}
    has_more = True
    start_cursor = None
    
    while has_more:
        payload = {"page_size": 100}
        if start_cursor:
            payload["start_cursor"] = start_cursor
        
        response = requests.post(url, headers=NOTION_HEADERS, json=payload)
        
        if response.status_code != 200:
            print(f"❌ 노션 조회 실패: {response.status_code}")
            print(response.text)
            return {}
        
        data = response.json()
        
        for page in data.get('results', []):
            props = page.get('properties', {})
            ticker_prop = props.get('티커', {})
            
            # 티커 값 추출
            ticker = None
            if ticker_prop.get('type') == 'rich_text':
                rich_texts = ticker_prop.get('rich_text', [])
                if rich_texts:
                    ticker = rich_texts[0].get('plain_text', '').strip()
            
            if ticker:
                all_pages[ticker] = page['id']
        
        has_more = data.get('has_more', False)
        start_cursor = data.get('next_cursor')
    
    print(f"📊 기존 페이지 {len(all_pages)}개 발견")
    return all_pages


def create_or_update_page(stock_data: Dict, existing_pages: Dict[str, str]) -> bool:
    """노션 페이지 생성 또는 업데이트"""
    ticker = stock_data['티커']
    page_id = existing_pages.get(ticker)
    
    # 노션 properties 포맷으로 변환
    properties = {
        "종목명": {"title": [{"text": {"content": stock_data['종목명']}}]},
        "티커": {"rich_text": [{"text": {"content": stock_data['티커']}}]},
        "시장": {"select": {"name": stock_data['시장']}},
        "현재가": {"number": stock_data['현재가']},
        "등락률": {"number": stock_data['등락률']},
        "거래량": {"number": stock_data['거래량']},
        "5일평균거래량대비": {"number": stock_data['5일평균거래량대비']},
        "골든크로스데드크로스": {"select": {"name": stock_data['골든크로스데드크로스']}},
        "date:업데이트시각:start": datetime.now(timezone.utc).isoformat(),
        "date:업데이트시각:is_datetime": 1
    }
    
    # Optional 값들 추가
    for key, notion_key in [
        ('SMA20', 'SMA20'), ('SMA50', 'SMA50'), ('SMA200', 'SMA200'),
        ('RSI30', 'RSI30'), ('PER', 'PER'), ('PBR', 'PBR'),
        ('시가총액', '시가총액'), ('52주최고가', '52주최고가'), ('52주최저가', '52주최저가')
    ]:
        if stock_data.get(key) is not None:
            properties[notion_key] = {"number": stock_data[key]}
    
    try:
        if page_id:
            # 업데이트
            url = f"https://api.notion.com/v1/pages/{page_id}"
            response = requests.patch(url, headers=NOTION_HEADERS, json={"properties": properties})
        else:
            # 생성
            url = "https://api.notion.com/v1/pages"
            payload = {
                "parent": {"type": "database_id", "database_id": NOTION_DATABASE_ID},
                "properties": properties
            }
            response = requests.post(url, headers=NOTION_HEADERS, json=payload)
        
        if response.status_code in [200, 201]:
            action = "업데이트" if page_id else "생성"
            print(f"✅ {ticker} {action} 완료")
            return True
        else:
            print(f"❌ {ticker} 노션 저장 실패: {response.status_code}")
            print(response.text)
            return False
            
    except Exception as e:
        print(f"❌ {ticker} 노션 처리 중 오류: {str(e)}")
        return False


def main():
    """메인 실행 함수"""
    print("=" * 60)
    print("🚀 주식 데이터 수집 시작")
    print(f"⏰ {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)
    
    # 추적할 종목 목록 (예시)
    # 실제 사용시 여기에 원하는 종목을 추가하세요
    stocks = [
        # 미국 주식
        {"ticker": "AAPL", "market": "미국"},
        {"ticker": "MSFT", "market": "미국"},
        {"ticker": "GOOGL", "market": "미국"},
        {"ticker": "NVDA", "market": "미국"},
        {"ticker": "TSLA", "market": "미국"},
        
        # 한국 주식 (Yahoo Finance는 .KS 또는 .KQ 필요)
        {"ticker": "005930.KS", "market": "한국"},  # 삼성전자
        {"ticker": "000660.KS", "market": "한국"},  # SK하이닉스
        {"ticker": "035720.KS", "market": "한국"},  # 카카오
        {"ticker": "035420.KS", "market": "한국"},  # NAVER
        {"ticker": "207940.KS", "market": "한국"},  # 삼성바이오로직스
    ]
    
    # 환경변수에서 종목 목록 읽기 (선택사항)
    stocks_env = os.environ.get('STOCK_TICKERS')
    if stocks_env:
        try:
            stocks = json.loads(stocks_env)
            print(f"📋 환경변수에서 {len(stocks)}개 종목 로드")
        except:
            print("⚠️  환경변수 파싱 실패, 기본 종목 사용")
    
    # 기존 페이지 조회
    existing_pages = get_existing_pages()
    
    # 각 종목 처리
    success_count = 0
    fail_count = 0
    
    for stock_info in stocks:
        ticker = stock_info['ticker']
        market = stock_info['market']
        
        # 데이터 수집
        stock_data = get_stock_data(ticker, market)
        
        if stock_data:
            # 노션에 저장
            if create_or_update_page(stock_data, existing_pages):
                success_count += 1
            else:
                fail_count += 1
        else:
            fail_count += 1
    
    print("=" * 60)
    print(f"✅ 성공: {success_count}개 | ❌ 실패: {fail_count}개")
    print("=" * 60)


if __name__ == "__main__":
    main()
