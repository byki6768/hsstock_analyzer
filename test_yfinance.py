"""yfinance로 삼성전자(005930.KS) 데이터 조회 테스트."""

import yfinance as yf


def main() -> None:
    ticker = yf.Ticker("005930.KS")
    info = ticker.info

    company_name = info.get("longName") or info.get("shortName") or "N/A"
    current_price = info.get("currentPrice") or info.get("regularMarketPrice")
    change_pct = info.get("regularMarketChangePercent")

    print("=== 삼성전자 시세 정보 ===")
    print(f"회사명: {company_name}")
    if current_price is not None:
        print(f"현재가: {current_price:,.0f}원")
    else:
        print("현재가: N/A")
    if change_pct is not None:
        print(f"전일 대비 등락률: {change_pct:+.2f}%")
    else:
        print("전일 대비 등락률: N/A")

    print("\n=== 최근 1개월 역사적 데이터 (처음 5행) ===")
    hist = ticker.history(period="1mo")
    if hist.empty:
        print("역사적 데이터를 가져오지 못했습니다.")
    else:
        print(hist.head())


if __name__ == "__main__":
    main()
