# 주식 데이터 분석기

yfinance와 Streamlit으로 만든 주식 시세 조회·차트·비교 웹 앱입니다.

## 주요 기능

- **단일 종목 분석**: 종목 코드·기간 조회, 회사명/현재가/등락률, 역사적 데이터 테이블
- **차트**: 종가 선 차트, 캔들스틱 + 거래량, 20일/60일 이동평균선(표시 토글)
- **종목 비교**: 여러 종목을 시작일 기준 수익률로 정규화해 비교
- **수익률 계산기**: 매수일·매수 금액 기준 현재 가치와 수익률 계산 (모바일 탭 지원)

## 요구 사항

- Python 3.10 이상 권장
- 인터넷 연결 (Yahoo Finance 데이터 조회)

## 설치

```bash
# 저장소 클론
git clone <repository-url>
cd hsstock_analyzer

# 가상환경 생성 및 활성화 (Windows)
python -m venv venv
venv\Scripts\activate

# 가상환경 생성 및 활성화 (macOS / Linux)
python -m venv venv
source venv/bin/activate

# 의존성 설치
pip install -r requirements.txt
```

## 실행

```bash
streamlit run app.py
```

브라우저에서 `http://localhost:8501` 로 접속합니다.

## 사용 방법

### 단일 종목

1. **단일 종목** 탭에서 종목 코드 입력 (예: `005930.KS`, `AAPL`)
2. 기간 선택 후 **데이터 조회**
3. 선 차트 / 캔들스틱 탭에서 차트 확인
4. 이동평균선 체크박스로 MA20(주황)·MA60(초록) 표시 여부 선택

### 종목 비교

1. **종목 비교** 탭에서 종목 코드를 쉼표로 구분해 입력  
   예: `005930.KS, 000660.KS`
2. 기간 선택 후 **비교 조회**
3. 시작일 기준 수익률(%) 차트로 비교

### 수익률 계산기

1. **수익률 계산기** 탭에서 종목 코드, 매수 날짜, 매수 금액 입력
2. **수익률 계산** 클릭
3. 현재 가치·수익/손실·수익률 확인 (수익: 파랑, 손실: 빨강)

## 프로젝트 구조

```
hsstock_analyzer/
├── app.py                  # Streamlit 메인 앱
├── test_yfinance.py        # 삼성전자(005930.KS) 조회 테스트
├── test_yfinance_aapl.py   # 애플(AAPL) 조회 테스트
├── requirements.txt
├── .gitignore
└── README.md
```

## 테스트 스크립트

```bash
python test_yfinance.py
python test_yfinance_aapl.py
```

## 참고

- 시세 데이터는 [yfinance](https://github.com/ranaroussi/yfinance)를 통해 Yahoo Finance에서 가져옵니다.
- 데이터 지연·누락이 있을 수 있으며, 투자 판단의 근거로 사용하지 마세요.
