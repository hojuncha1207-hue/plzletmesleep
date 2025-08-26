# Kakao OAuth 연동 버전 (링크에 {변수} 없이 사용자 ID 확보)

## 핵심
- 링크에 `{user_id}` 같은 변수를 못 넣어도 OK.
- 유저는 `/launch/order` 또는 `/launch/view-order` 같은 **고정 URL**을 누른다.
- 페이지가 로드되면 **쿠키에 user_id가 없으면 Kakao OAuth로 이동** → 동의 후 콜백에서 `k_uid` 쿠키로 저장 → 다시 원래 페이지로 복귀.

## 필요한 설정
- 환경변수 설정
  - `KAKAO_REST_API_KEY`: (카카오 개발자 콘솔 REST API 키)
  - `KAKAO_REDIRECT_URI`: 예) `https://plzletmesleep.onrender.com/oauth/kakao/callback`
- 카카오 개발자 콘솔
  - 로그인 Redirect URI에 위 `KAKAO_REDIRECT_URI` 등록

## 라우트
- 주문하기(장바구니): `/launch/order`
- 내 QR코드 확인: `/launch/view-order`
- Kakao OAuth:
  - 시작: `/oauth/kakao/start`
  - 콜백: `/oauth/kakao/callback`
- API:
  - `POST /api/create-order`  → {success, orderId, qr}
  - `GET  /api/order`         → cookie 또는 `?user_id`로 조회
  - `GET  /api/whoami`        → cookie에 저장된 user_id 반환

## 배포
- Start Command (Required): `gunicorn app:app`
- Build Command: `pip install -r requirements.txt`
- (옵션) `REDIS_URL` 지정 시 재시작 이후에도 주문 유지
