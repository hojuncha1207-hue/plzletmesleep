# QR 주문 데모 (사용자 지정 경로 버전)

## 경로
- 주문하기(장바구니/주문 생성) 페이지: **/launch/order**
- 내 QR코드 확인 페이지: **/launch/view-order**

## 요약 동작
- /launch/order 에서 user_id를 (쿼리파라미터 또는 쿠키)로 자동 인식 → `/api/create-order` 저장 → 서버는 `qr`에 `/launch/view-order?user_id=...`를 저장
- /launch/view-order 에서 `/api/order?user_id=...` 조회 → 있으면 서버가 저장한 `qr` 내용으로 QR 이미지 즉시 렌더

## 서버 API
- POST `/api/create-order`  { userId, items[], orderTimestamp } → { success, orderId, qr }
- GET  `/api/order?user_id=...` → { success, data: { orderId, userId, items[], orderTimestamp, qr } }

## 배포
- Start Command (Required): `gunicorn app:app`
- (옵션) 환경변수 `REDIS_URL` 설정 시 Redis 저장 사용, 미설정 시 인메모리 저장(재시작 시 유실)
