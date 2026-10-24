# 오늘 뭐 먹지

세종·반포·여의도·서울역 근무지별로 점심 메뉴와 가까운 식당, 저녁 회식 장소를 고르고 동료들과 함께 투표·예약 표시·후기를 남기는 웹앱입니다. 가입 없이 닉네임만 정하면 되고, 휴대폰에서 ‘홈 화면에 추가’를 하면 앱처럼 쓸 수 있습니다.

## 구성

| 파일 | 하는 일 |
|---|---|
| `index.html` | 화면 전체 (식당 데이터 포함) |
| `api/state.js` | 투표·후기·추가한 집·폐업 신고를 저장하는 서버 함수 |
| `manifest.webmanifest`, `icons/`, `sw.js` | 홈 화면 추가(앱처럼 쓰기)용 |
| `data/places.json` | 식당·카페 원본 데이터 |
| `tools/build_index.py` | 템플릿과 데이터로 `index.html`을 다시 만드는 스크립트 |

## Vercel에 배포하기

1. [vercel.com](https://vercel.com)에 로그인 → **Add New… → Project** → 이 저장소(`lunch-today`) **Import** → 설정은 그대로 두고 **Deploy**.
2. 배포가 끝나면 프로젝트 화면에서 **Storage** 탭 → **Create Database** → **Upstash for Redis**(무료 플랜) 선택 → 이 프로젝트에 **Connect**.
3. **Deployments** 탭에서 가장 최근 배포의 ⋯ 메뉴 → **Redeploy**. 저장소 연결 정보(환경변수)는 다시 배포해야 적용됩니다.
4. `https://<프로젝트이름>.vercel.app` 주소를 동료들에게 공유합니다. 근무지별 바로가기: 주소 뒤에 `#sejong`, `#banpo`, `#yeouido`, `#seoul`.

2번을 하기 전에는 화면은 열리지만 투표·후기가 각자 기기에만 저장됩니다(화면에 안내 문구가 보여요).

## 데이터와 개인정보

- 저장하는 것: 닉네임, 투표, 후기, 직접 추가한 집, 폐업 신고. 이름·전화번호·부서 등은 받지 않습니다.
- 기기마다 임의의 아이디와 비밀키를 만들어 본인 투표만 고칠 수 있게 합니다. 다른 기기에서 열면 새 참여자로 시작합니다.
- 식당 위치·영업시간·전화·평점은 Google 지도 장소 정보(2026년 10월 조회)이며 자동으로 갱신되지 않습니다. 없어진 집은 상세 화면의 ‘없어진 집이에요’로 신고하면 모두의 목록에서 숨겨집니다.

## 식당 데이터 고치기

`data/places.json`을 고친 뒤 아래 명령으로 `index.html`을 다시 만들고 커밋하면 Vercel이 자동으로 다시 배포합니다.

```
python3 tools/build_index.py tools/template.html data/places.json index.html
```
