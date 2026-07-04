# Notion API 개요

Notion API는 Notion 워크스페이스의 페이지, 데이터베이스, 블록에 프로그램으로
접근할 수 있게 해주는 공식 REST API다.

## Integration과 인증

- API를 쓰려면 먼저 **Integration**을 만들어야 한다 (notion.so/my-integrations).
- Integration을 만들면 `ntn_`으로 시작하는 시크릿 토큰이 발급된다.
- 중요: Integration은 기본적으로 아무 페이지에도 접근할 수 없다.
  접근할 데이터베이스/페이지에서 **연결(Connections)** 메뉴로 해당 Integration을
  명시적으로 추가해야 한다. 이 단계를 빼먹으면 404 오류가 난다.

## 데이터 구조

- **Database**: 데이터 소스(data source)들의 컨테이너. 2025-09-03 API부터
  페이지 조회는 데이터 소스 단위로 한다 (`data_sources.query`).
- **Data source**: 행(row)들의 모음. 각 행은 하나의 페이지다.
- **Page**: 속성(properties)과 본문(블록 트리)을 가진다.
- **Block**: 본문을 구성하는 단위. paragraph, heading, bulleted_list_item,
  code, quote 등 다양한 타입이 있으며 블록 안에 자식 블록이 중첩될 수 있다.

## API 사용 시 주의점

- 모든 목록 조회는 **페이지네이션**된다. `has_more`와 `next_cursor`를 확인해
  끝까지 반복 조회해야 한다.
- 블록 본문 텍스트는 `rich_text` 배열 안에 조각으로 나뉘어 있으므로
  `plain_text`를 이어 붙여야 전체 문장이 된다.
- 요청 속도 제한(rate limit)은 평균 초당 3회 수준이다.
