# 00. Notion 셋업 가이드

Notion 데이터베이스를 지식 소스로 연결하기 위한 준비 과정입니다.
소요 시간: 약 5분.

## 1단계. Integration 생성

1. 브라우저에서 https://www.notion.so/my-integrations 접속 (Notion 로그인 필요)
2. **[+ New integration]** 클릭
3. 설정:
   - **Name**: `rag-agent` (아무 이름이나 가능)
   - **Associated workspace**: 대상 DB가 있는 워크스페이스 선택
   - **Type**: Internal
4. **[Submit]** 클릭
5. 생성된 Integration 페이지에서 **Internal Integration Secret** 을 확인
   → **[Show]** → 복사. `ntn_` 으로 시작하는 문자열입니다.

> ⚠️ 이 토큰은 비밀번호와 같습니다. 절대 git에 커밋하지 마세요.
> (이 프로젝트의 `.gitignore`가 `.env`를 제외하도록 이미 설정되어 있습니다)

## 2단계. 데이터베이스에 Integration 연결

**가장 자주 빼먹는 단계입니다.** Integration은 만들기만 하면 아무 페이지에도 접근할 수 없습니다.

1. Notion에서 지식 소스로 쓸 **데이터베이스 페이지**를 엽니다
   (풀 페이지 데이터베이스 기준. 인라인 DB라면 상위 페이지에서 진행)
2. 우측 상단 **`⋯`(더보기) 메뉴** 클릭
3. **연결(Connections)** → **연결 검색** 에서 1단계에서 만든 `rag-agent` 선택
4. 확인 팝업에서 승인

> 이 단계를 건너뛰면 API 호출 시 `404 object_not_found` 오류가 발생합니다.

## 3단계. 데이터베이스 ID 설정

### 방법 A: 자동 발견 (권장) ✨

```
NOTION_DATABASE_ID=auto
```

`auto`로 설정하면 수집 시 **Integration에 연결된 모든 데이터베이스를 API로 자동 발견**하여
수집합니다. ID를 복사할 필요가 없어 실수 여지가 없습니다.

> URL에서 ID를 손으로 복사하면 실제 데이터 소스 ID가 아닌 값(링크된 뷰의 ID 등)을
> 집는 실수가 흔합니다. 이 경우 연결이 되어 있어도 404가 나므로 `auto`를 권장합니다.

### 방법 B: 특정 DB만 지정

1. 데이터베이스를 **풀 페이지로** 연 상태에서 브라우저 주소창의 URL 확인:

   ```
   https://www.notion.so/myworkspace/8935f9d140a04f95a2cd9e5ed7a4e2f9?v=...
                                     └──────────── 이 32자가 DB ID ────────────┘
   ```

2. `notion.so/` 뒤, `?v=` 앞의 **32자 16진수 문자열**이 데이터베이스 ID입니다.
   (워크스페이스 이름 뒤에 붙은 부분. 하이픈이 있어도/없어도 동작합니다)

3. 어떤 ID가 실제로 접근 가능한지 확실치 않으면, 파이썬에서
   `rag_agent.notion_loader.discover_data_sources()`로 (ID, 제목) 목록을 확인할 수 있습니다.

## 4단계. .env 설정

프로젝트 루트에서:

```powershell
Copy-Item .env.example .env
```

`.env` 파일을 열어 값을 채웁니다:

```
OPENAI_API_KEY=sk-...          # OpenAI API 키
NOTION_TOKEN=ntn_...           # 1단계에서 복사한 시크릿
NOTION_DATABASE_ID=auto        # 자동 발견(권장) 또는 특정 ID들(쉼표 구분)
```

> 💡 **여러 DB를 지정하는 경우** 쉼표로 구분: `NOTION_DATABASE_ID=id1,id2,id3`
> 어느 방식이든 **각 DB에 2단계(Integration 연결)가 되어 있어야** 합니다.
> 연결 안 된 DB는 404가 나며, 해당 DB만 건너뛰고 나머지는 수집됩니다.

## 5단계. 수집 실행

```powershell
python scripts/ingest.py
```

각 페이지 제목이 출력되며 로드되고, 마지막에 색인 통계와 검증용 검색 결과가 표시되면 성공입니다.

## 자주 발생하는 오류

| 오류 | 원인 | 해결 |
|---|---|---|
| `401 unauthorized` | 토큰이 잘못됨 | 시크릿을 다시 복사 (`ntn_` 시작 확인) |
| `404 object_not_found` | DB에 Integration 미연결 | 2단계 다시 수행 |
| `400 validation_error` | DB ID 형식 오류 | 32자 hex인지 확인 (`?v=` 뒤 값을 붙이지 않았는지) |
| 페이지 0개 로드 | 데이터베이스가 비어있음 | DB에 페이지(행)를 추가 |
