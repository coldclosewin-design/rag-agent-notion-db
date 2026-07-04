"""Notion 데이터베이스에서 페이지를 로드하여 Document로 변환한다.

흐름: DB query(페이지 목록) → 각 페이지의 블록 트리 조회 → Markdown 텍스트로 변환.
셋업 방법은 docs/00-notion-setup.md 참고.
"""

from notion_client import Client
from notion_client.errors import APIResponseError
from langchain_core.documents import Document

from rag_agent import config

# Notion 블록 타입 → Markdown 접두사
_HEADING_PREFIX = {"heading_1": "# ", "heading_2": "## ", "heading_3": "### "}
_LIST_PREFIX = {"bulleted_list_item": "- ", "numbered_list_item": "1. ", "to_do": "- [ ] "}


def _rich_text_to_plain(rich_text: list[dict]) -> str:
    """rich_text 배열의 조각들을 하나의 문자열로 이어 붙인다."""
    return "".join(part.get("plain_text", "") for part in rich_text)


def _block_to_markdown(block: dict) -> str:
    """블록 하나를 Markdown 한 줄(또는 여러 줄)로 변환한다. 미지원 타입은 빈 문자열."""
    block_type = block["type"]
    payload = block.get(block_type, {})
    text = _rich_text_to_plain(payload.get("rich_text", []))

    if block_type in _HEADING_PREFIX:
        return _HEADING_PREFIX[block_type] + text
    if block_type in _LIST_PREFIX:
        return _LIST_PREFIX[block_type] + text
    if block_type == "paragraph":
        return text
    if block_type == "quote":
        return "> " + text
    if block_type == "code":
        language = payload.get("language", "")
        return f"```{language}\n{text}\n```"
    if block_type == "divider":
        return "---"
    return ""


def _fetch_blocks_markdown(client: Client, block_id: str, depth: int = 0) -> list[str]:
    """블록 트리를 재귀적으로 순회하며 Markdown 줄 목록을 만든다 (페이지네이션 처리)."""
    lines: list[str] = []
    cursor = None
    while True:
        response = client.blocks.children.list(block_id=block_id, start_cursor=cursor)
        for block in response["results"]:
            line = _block_to_markdown(block)
            if line:
                lines.append("  " * depth + line)
            if block.get("has_children"):
                lines.extend(_fetch_blocks_markdown(client, block["id"], depth + 1))
        if not response.get("has_more"):
            break
        cursor = response["next_cursor"]
    return lines


def _page_title(page: dict) -> str:
    """페이지 속성에서 title 타입 속성을 찾아 제목을 추출한다."""
    for prop in page["properties"].values():
        if prop["type"] == "title":
            return _rich_text_to_plain(prop["title"]) or "제목 없음"
    return "제목 없음"


def _property_to_text(prop: dict) -> str:
    """속성 하나를 사람이 읽을 수 있는 문자열로 변환한다. 미지원 타입은 빈 문자열."""
    prop_type = prop["type"]
    value = prop.get(prop_type)
    if value is None:
        return ""
    if prop_type == "rich_text":
        return _rich_text_to_plain(value)
    if prop_type in ("select", "status"):
        return value.get("name", "")
    if prop_type == "multi_select":
        return ", ".join(opt.get("name", "") for opt in value)
    if prop_type == "number":
        return str(value)
    if prop_type == "checkbox":
        return "예" if value else "아니오"
    if prop_type == "date":
        start, end = value.get("start", ""), value.get("end")
        return f"{start}~{end}" if end else start
    if prop_type in ("url", "email", "phone_number"):
        return str(value)
    if prop_type == "people":
        return ", ".join(p.get("name", "") for p in value if p.get("name"))
    return ""


def _page_properties_markdown(page: dict) -> str:
    """title 외의 속성들을 '- 속성명: 값' 목록으로 변환한다.

    Quote/단어장처럼 내용이 본문이 아니라 속성(컬럼)에 들어 있는 DB가 많으므로,
    속성을 텍스트에 포함해야 검색 가능한 내용이 된다.
    """
    lines = []
    for name, prop in page["properties"].items():
        if prop["type"] == "title":
            continue  # 제목은 별도 처리
        text = _property_to_text(prop)
        if text:
            lines.append(f"- {name}: {text}")
    return "\n".join(lines)


def discover_data_sources(client: Client) -> list[tuple[str, str]]:
    """이 Integration이 접근 가능한 모든 데이터 소스의 (id, 제목) 목록을 반환한다.

    URL에서 ID를 손으로 복사하면 실제 데이터 소스 ID와 다른 값(뷰 ID 등)을
    집는 실수가 잦으므로, search API로 직접 발견하는 것이 안전하다.
    """
    sources: list[tuple[str, str]] = []
    cursor = None
    while True:
        response = client.search(start_cursor=cursor)
        for result in response["results"]:
            if result["object"] in ("database", "data_source"):
                title = _rich_text_to_plain(result.get("title", []))
                sources.append((result["id"], title or "(제목 없음)"))
        if not response.get("has_more"):
            break
        cursor = response["next_cursor"]
    return sources


def _resolve_data_source_ids(client: Client, database_id: str) -> list[str]:
    """데이터베이스 ID를 데이터 소스 ID 목록으로 변환한다.

    Notion API 2025-09-03부터 데이터베이스는 하나 이상의 '데이터 소스'를 가지며,
    페이지 조회는 데이터 소스 단위로 한다. URL에서 얻는 ID는 보통 데이터베이스 ID이므로
    여기서 소스 ID로 해석한다. (이미 데이터 소스 ID라면 그대로 사용)
    """
    try:
        db = client.databases.retrieve(database_id=database_id)
        sources = [ds["id"] for ds in db.get("data_sources", [])]
        return sources or [database_id]
    except APIResponseError:
        return [database_id]


def _load_single_database(
    client: Client, database_id: str, resolve: bool = True
) -> list[Document]:
    """데이터베이스 하나의 모든 페이지를 Document 리스트로 로드한다.

    resolve=False 면 ID를 이미 데이터 소스 ID로 간주한다 (auto 모드 — 해석 불필요).
    """
    # 1. 데이터 소스별로 모든 페이지 조회 (페이지네이션)
    source_ids = (
        _resolve_data_source_ids(client, database_id) if resolve else [database_id]
    )
    pages: list[dict] = []
    for ds_id in source_ids:
        cursor = None
        while True:
            response = client.data_sources.query(data_source_id=ds_id, start_cursor=cursor)
            pages.extend(response["results"])
            if not response.get("has_more"):
                break
            cursor = response["next_cursor"]

    # 2. 각 페이지의 본문을 Markdown으로 변환
    docs: list[Document] = []
    for page in pages:
        title = _page_title(page)
        print(f"  페이지 로드 중: {title}")
        properties = _page_properties_markdown(page)
        body = "\n".join(_fetch_blocks_markdown(client, page["id"]))
        content = "\n\n".join(part for part in (f"# {title}", properties, body) if part).strip()
        docs.append(
            Document(
                page_content=content,
                metadata={
                    "title": title,
                    "source": page.get("url", ""),
                    "last_edited": page.get("last_edited_time", ""),
                    "database_id": database_id,
                },
            )
        )
    return docs


def load_notion_database() -> list[Document]:
    """설정된 모든 Notion DB(쉼표 구분 가능)의 페이지를 로드하여 합친다."""
    if not config.NOTION_TOKEN or not config.NOTION_DATABASE_IDS:
        raise ValueError(
            "NOTION_TOKEN 과 NOTION_DATABASE_ID 가 .env 에 설정되어야 합니다.\n"
            "여러 DB는 쉼표로 구분: NOTION_DATABASE_ID=id1,id2\n"
            "Integration에 연결된 모든 DB를 자동 수집하려면: NOTION_DATABASE_ID=auto\n"
            "셋업 방법: docs/00-notion-setup.md"
        )

    client = Client(auth=config.NOTION_TOKEN)

    # auto 모드: 접근 가능한 데이터 소스를 자동 발견 (이미 소스 ID이므로 해석 불필요)
    auto_mode = config.NOTION_DATABASE_IDS == ["auto"]
    if auto_mode:
        discovered = discover_data_sources(client)
        print(f"자동 발견된 데이터 소스: {len(discovered)}개")
        for ds_id, title in discovered:
            print(f"  - {title}")
        target_ids = [ds_id for ds_id, _ in discovered]
    else:
        target_ids = config.NOTION_DATABASE_IDS

    docs: list[Document] = []
    failed: list[tuple[str, str]] = []
    for db_id in target_ids:
        print(f"데이터베이스 로드 시작: {db_id}")
        try:
            docs.extend(_load_single_database(client, db_id, resolve=not auto_mode))
        except APIResponseError as e:
            # 한 DB 실패(주로 Integration 미연결 404)가 전체를 막지 않도록 건너뛴다
            failed.append((db_id, str(e)))
            print(f"  [건너뜀] {db_id}: {e}")

    print(
        f"\nNotion에서 총 {len(docs)}개 페이지 로드 완료 "
        f"(성공 DB {len(target_ids) - len(failed)}/{len(target_ids)}개)"
    )
    if failed:
        print("\n⚠️ 로드 실패한 데이터베이스 (Notion에서 '연결(Connections)'에 Integration을 추가했는지 확인):")
        for db_id, _ in failed:
            print(f"  - {db_id}")
        print("   해결 방법: docs/00-notion-setup.md 2단계 참고")
    return docs
