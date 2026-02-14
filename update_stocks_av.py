#!/usr/bin/env python3
"""
실시간 주식 모니터링 - 노션 자동 업데이트 (Alpha Vantage API)
GitHub Actions 환경에서 안정적으로 작동하도록 최적화되었습니다.
"""

import os
import json
import time
from datetime import datetime, timezone
from typing import Dict, List, Optional
import requests
import numpy as np


# API 설정
NOTION_API_KEY = os.environ.get('NOTION_API_KEY')
NOTION_DATABASE_ID = os.environ.get('NOTION_DATABASE_ID', '42c8793f07f84faf96ef46a1ed45579a')
ALPHA_VANTAGE_API_KEY = os.environ.get('ALPHA_VANTAGE_API_KEY', 'demo')  # 무료 키로 교체 필요

NOTION_HEADERS = {
    "Authorization": f"Bearer {NOTION_API_KEY}",
    "Content-Type": "application/json",
    "Notion-Version": "2022-06-28"
}


def calculate_rsi(prices: List[float], period: int = 30) -> float:
    """RSI 계산"""
    if len(prices) < period + 1:
        return None
    
    prices = np.array(prices)
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


def calculate_sma(prices: List[float], period: int) -> Optional[float]:
    """단순 이동평균 계산"""
    if len(prices) < period:
        return None
    return round(np.mean(prices[-period:]), 2)


def determine_ma_signal(sma20: float, sma50: float, sma200: float) -> str:
    """이동평균선 배열 상태 판단"""
    if not all([sma20, sma50, sma200]):
        return "-"
    
    if sma20 > sma50 > sma200:
        return "정배열"
    elif sma20 < sma50 < sma200:
        return "역배열"
    elif sma20 > sma50:
        return "골든크로스 (20>50)"
    elif sma50 > sma200:
        return "골든크로스 (50>200)"
    elif sma20 < sma50:
        return "데드크로스 (20<50)"
    elif sma50 < sma200:
        return "데드크로스 (50<200)"
    else:
        return "-"


def get_stock_data_av(ticker: str, market: str) -> Optional[Dict]:
    """Alpha Vantage API로 주식 데이터 수집"""
    
    # 한국 주식은 티커 변환
    if market == "한국":
        # .KS 또는 .KQ 제거
        base_ticker = ticker.replace('.KS', '').replace('.KQ', '')
        # Alpha Vantage는 한국 주식을 지원하지 않으므로 다른 API 사용 필요
        print(f"⚠️  {ticker}: Alpha Vantage는 한국 주식 미지원 (임시 스킵)")
        return None
    
    try:
        # 1. 일일 가격 데이터 (최근 100일)
        daily_url = f"https://www.alphavantage.co/query?function=TIME_SERIES_DAILY&symbol={ticker}&apikey={ALPHA_VANTAGE_API_KEY}"
        response = requests.get(daily_url, timeout=10)
        
        if response.status_code != 200:
            print(f"❌ {ticker}: API 호출 실패 ({response.status_code})")
            return None
        
        data = response.json()
        
        if "Error Message" in data:
            print(f"❌ {ticker}: {data['Error Message']}")
            return None
        
        if "Note" in data:
            print(f"⚠️  {ticker}: API 호출 제한 도달")
            return None
        
        time_series = data.get("Time Series (Daily)", {})
        if not time_series:
            print(f"❌ {ticker}: 데이터 없음")
            return None
        
        # 날짜순 정렬
        dates = sorted(time_series.keys())
        if len(dates) < 2:
            print(f"❌ {ticker}: 데이터 부족")
            return None
        
        # 최신 데이터
        latest_date = dates[-1]
        latest = time_series[latest_date]
        current_price = float(latest['4. close'])
        current_volume = int(float(latest['5. volume']))
        
        # 이전일 종가 (등락률 계산용)
        prev_date = dates[-2]
        prev_close = float(time_series[prev_date]['4. close'])
        change_pct = (current_price / prev_close - 1) if prev_close > 0 else 0
        
        # 종가 리스트 (이동평균 계산용)
        closes = [float(time_series[d]['4. close']) for d in dates]
        volumes = [int(float(time_series[d]['5. volume'])) for d in dates[-5:]]
        
        # 거래량 분석
        avg_volume_5d = np.mean(volumes)
        volume_ratio = (current_volume / avg_volume_5d - 1) if avg_volume_5d > 0 else 0
        
        # 이동평균 계산
        sma20 = calculate_sma(closes, 20)
        sma50 = calculate_sma(closes, 50)
        sma200 = calculate_sma(closes, 200) if len(closes) >= 200 else None
        
        # RSI 계산
        rsi30 = calculate_rsi(closes, 30)
        
        # 52주 최고/최저 (최근 1년 = 252 거래일)
        recent_prices = closes[-252:] if len(closes) >= 252 else closes
        high_52w = max(recent_prices)
        low_52w = min(recent_prices)
        
        # 골든크로스/데드크로스
        ma_signal = determine_ma_signal(sma20, sma50, sma200)
        
        # 2. 기업 개요 (PER, PBR, 시가총액)
        overview_url = f"https://www.alphavantage.co/query?function=OVERVIEW&symbol={ticker}&apikey={ALPHA_VANTAGE_API_KEY}"
        overview_response = requests.get(overview_url, timeout=10)
        
        per = None
        pbr = None
        market_cap = None
        company_name = ticker
        
        if overview_response.status_code == 200:
            overview = overview_response.json()
            company_name = overview.get('Name', ticker)
            
            # PER
            pe_ratio = overview.get('PERatio')
            if pe_ratio and pe_ratio != 'None':
                try:
                    per = float(pe_ratio)
                except:
                    pass
            
            # PBR
            pb_ratio = overview.get('PriceToBookRatio')
            if pb_ratio and pb_ratio != 'None':
                try:
                    pbr = float(pb_ratio)
                except:
                    pass
            
            # 시가총액 (백만달러)
            mkt_cap = overview.get('MarketCapitalization')
            if mkt_cap and mkt_cap != 'None':
                try:
                    market_cap = float(mkt_cap) / 1_000_000  # 백만달러로 변환
                except:
                    pass
        
        data_dict = {
            "종목명": company_name,
            "티커": ticker,
            "시장": market,
            "현재가": round(current_price, 2),
            "등락률": round(change_pct, 4),
            "거래량": current_volume,
            "5일평균거래량대비": round(volume_ratio, 4),
            "SMA20": sma20,
            "SMA50": sma50,
            "SMA200": sma200,
            "RSI30": rsi30,
            "PER": per,
            "PBR": pbr,
            "시가총액": round(market_cap, 2) if market_cap else None,
            "52주최고가": round(high_52w, 2),
            "52주최저가": round(low_52w, 2),
            "골든크로스데드크로스": ma_signal,
            "업데이트시각": datetime.now(timezone.utc).isoformat()
        }
        
        print(f"✅ {ticker} ({company_name}): ${current_price:,.2f} ({change_pct*100:+.2f}%)")
        return data_dict
        
    except Exception as e:
        print(f"❌ {ticker} 오류: {str(e)}")
        return None


def get_existing_pages() -> Dict[str, str]:
    """노션 DB의 기존 페이지 조회"""
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
            return {}
        
        data = response.json()
        
        for page in data.get('results', []):
            props = page.get('properties', {})
            ticker_prop = props.get('티커', {})
            
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
    
    for key, notion_key in [
        ('SMA20', 'SMA20'), ('SMA50', 'SMA50'), ('SMA200', 'SMA200'),
        ('RSI30', 'RSI30'), ('PER', 'PER'), ('PBR', 'PBR'),
        ('시가총액', '시가총액'), ('52주최고가', '52주최고가'), ('52주최저가', '52주최저가')
    ]:
        if stock_data.get(key) is not None:
            properties[notion_key] = {"number": stock_data[key]}
    
    try:
        if page_id:
            url = f"https://api.notion.com/v1/pages/{page_id}"
            response = requests.patch(url, headers=NOTION_HEADERS, json={"properties": properties})
        else:
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
    print("🚀 주식 데이터 수집 시작 (Alpha Vantage API)")
    print(f"⏰ {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)
    
    # 미국 주식만 (Alpha Vantage 제한)
    stocks = [
        {"ticker": "AAPL", "market": "미국"},
        {"ticker": "MSFT", "market": "미국"},
        {"ticker": "GOOGL", "market": "미국"},
        {"ticker": "NVDA", "market": "미국"},
        {"ticker": "TSLA", "market": "미국"},
    ]
    
    # 환경변수에서 종목 로드
    stocks_env = os.environ.get('STOCK_TICKERS')
    if stocks_env:
        try:
            stocks = json.loads(stocks_env)
            # 한국 주식 필터링
            stocks = [s for s in stocks if s['market'] == '미국']
            print(f"📋 환경변수에서 미국 주식 {len(stocks)}개 로드")
        except:
            print("⚠️  환경변수 파싱 실패, 기본 종목 사용")
    
    existing_pages = get_existing_pages()
    
    success_count = 0
    fail_count = 0
    
    for i, stock_info in enumerate(stocks):
        ticker = stock_info['ticker']
        market = stock_info['market']
        
        # API 호출 제한 방지 (무료: 분당 5회)
        if i > 0:
            time.sleep(12)  # 12초 대기
        
        stock_data = get_stock_data_av(ticker, market)
        
        if stock_data:
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
