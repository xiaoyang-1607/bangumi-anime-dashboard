"""自动下载最新 Bangumi Archive 并安全更新榜单数据文件。"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from datetime import datetime, timezone
import json
import os
from pathlib import Path, PurePosixPath
import re
import shutil
import tempfile
import time
from typing import Any, Sequence
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen
from zipfile import BadZipFile, ZipFile

import pandas as pd

from config import (
    ANIME_CLEANED_FILE,
    BANGUMI_APP_DATA_DIR,
    DATA_METADATA_FILE,
    GAME_CLEANED_FILE,
    JSONL_FILE_NAME,
)
from main import generate_files


ARCHIVE_RELEASE_API = "https://api.github.com/repos/bangumi/Archive/releases/latest"
ARCHIVE_NAME_PATTERN = re.compile(
    r"^dump-(?P<timestamp>\d{4}-\d{2}-\d{2}\.\d{6}Z)\.zip$"
)
DOWNLOAD_CHUNK_SIZE = 1024 * 1024
USER_AGENT = "bangumi-anime-dashboard-data-updater/1.0"


@dataclass(frozen=True)
class ArchiveAsset:
    asset_id: int
    name: str
    url: str
    size: int
    created_at: str = ""
    updated_at: str = ""

    @property
    def timestamp(self) -> datetime:
        match = ARCHIVE_NAME_PATTERN.fullmatch(self.name)
        if match is None:
            raise ValueError(f"不是受支持的归档文件名：{self.name}")
        return datetime.strptime(match.group("timestamp"), "%Y-%m-%d.%H%M%SZ").replace(
            tzinfo=timezone.utc
        )


def _headers(token: str | None = None) -> dict[str, str]:
    headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": USER_AGENT,
        "X-GitHub-Api-Version": "2022-11-28",
    }
    if token:
        headers["Authorization"] = f"Bearer {token}"
    return headers


def request_json(url: str, token: str | None = None) -> Any:
    request = Request(url, headers=_headers(token))
    try:
        with urlopen(request, timeout=60) as response:
            return json.load(response)
    except (HTTPError, URLError, TimeoutError, json.JSONDecodeError) as exc:
        raise RuntimeError(f"GitHub API 请求失败：{url} ({exc})") from exc


def select_latest_asset(assets: Sequence[dict[str, Any]]) -> ArchiveAsset:
    """从 release 资源中选出时间戳最新的完整 zip 归档。"""
    candidates: list[ArchiveAsset] = []
    for raw in assets:
        name = str(raw.get("name", ""))
        if ARCHIVE_NAME_PATTERN.fullmatch(name) is None:
            continue
        url = str(raw.get("browser_download_url", ""))
        if not url:
            continue
        candidates.append(
            ArchiveAsset(
                asset_id=int(raw.get("id", 0)),
                name=name,
                url=url,
                size=int(raw.get("size", 0)),
                created_at=str(raw.get("created_at", "")),
                updated_at=str(raw.get("updated_at", "")),
            )
        )
    if not candidates:
        raise RuntimeError("Bangumi Archive release 中没有匹配的 dump-*.zip")
    return max(candidates, key=lambda asset: asset.timestamp)


def fetch_latest_asset(
    api_url: str = ARCHIVE_RELEASE_API, token: str | None = None
) -> ArchiveAsset:
    release = request_json(api_url, token)
    assets_url = release.get("assets_url") if isinstance(release, dict) else None
    if not assets_url:
        assets = release.get("assets", []) if isinstance(release, dict) else []
        return select_latest_asset(assets)

    assets: list[dict[str, Any]] = []
    page = 1
    while True:
        query = urlencode({"per_page": 100, "page": page})
        batch = request_json(f"{assets_url}?{query}", token)
        if not isinstance(batch, list):
            raise RuntimeError("GitHub release assets 响应格式无效")
        assets.extend(batch)
        if len(batch) < 100:
            break
        page += 1
    return select_latest_asset(assets)


def download_asset(asset: ArchiveAsset, destination: Path, token: str | None = None) -> None:
    """流式下载归档，校验字节数，并在网络失败时有限重试。"""
    partial = destination.with_suffix(destination.suffix + ".part")
    for attempt in range(1, 4):
        downloaded = 0
        try:
            request = Request(asset.url, headers=_headers(token))
            with urlopen(request, timeout=120) as response, partial.open("wb") as target:
                while chunk := response.read(DOWNLOAD_CHUNK_SIZE):
                    target.write(chunk)
                    downloaded += len(chunk)
                    if downloaded % (64 * DOWNLOAD_CHUNK_SIZE) < DOWNLOAD_CHUNK_SIZE:
                        print(f"已下载 {downloaded / 1024 / 1024:.0f} MiB")
            if asset.size and downloaded != asset.size:
                raise RuntimeError(
                    f"下载大小不一致：预期 {asset.size} 字节，实际 {downloaded} 字节"
                )
            partial.replace(destination)
            return
        except (HTTPError, URLError, TimeoutError, OSError, RuntimeError) as exc:
            partial.unlink(missing_ok=True)
            if attempt == 3:
                raise RuntimeError(f"归档下载失败（已重试 3 次）：{exc}") from exc
            print(f"[WARN] 下载失败，第 {attempt} 次重试：{exc}")
            time.sleep(2**attempt)


def extract_subject_jsonl(archive_path: Path, output_path: Path) -> None:
    """只从 zip 中提取 subject.jsonlines，避免解压不需要的大文件。"""
    try:
        with ZipFile(archive_path) as archive:
            matches = [
                item
                for item in archive.infolist()
                if not item.is_dir()
                and PurePosixPath(item.filename).name == JSONL_FILE_NAME
            ]
            if len(matches) != 1:
                raise RuntimeError(
                    f"归档内应有且仅有一个 {JSONL_FILE_NAME}，实际找到 {len(matches)} 个"
                )
            output_path.parent.mkdir(parents=True, exist_ok=True)
            with archive.open(matches[0]) as source, output_path.open("wb") as target:
                shutil.copyfileobj(source, target, length=DOWNLOAD_CHUNK_SIZE)
    except BadZipFile as exc:
        raise RuntimeError(f"下载文件不是有效 ZIP：{archive_path}") from exc
    if not output_path.is_file() or output_path.stat().st_size == 0:
        raise RuntimeError(f"提取后的 {JSONL_FILE_NAME} 为空")


def read_metadata(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}


def _record_count(path: Path) -> int:
    return len(pd.read_excel(path, engine="openpyxl", usecols=["id"]))


def update_latest_data(
    output_dir: Path,
    *,
    force: bool = False,
    api_url: str = ARCHIVE_RELEASE_API,
    token: str | None = None,
) -> bool:
    """更新数据；已经处理过同一资源时返回 False。"""
    output_dir = output_dir.expanduser().resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    metadata_path = output_dir / DATA_METADATA_FILE
    latest = fetch_latest_asset(api_url, token)
    current = read_metadata(metadata_path)
    required_files = [
        output_dir / ANIME_CLEANED_FILE,
        output_dir / GAME_CLEANED_FILE,
    ]
    if (
        not force
        and current.get("archive_asset_id") == latest.asset_id
        and current.get("archive_name") == latest.name
        and all(path.is_file() for path in required_files)
    ):
        print(f"数据已经来自最新归档：{latest.name}")
        return False

    print(f"发现归档：{latest.name}（{latest.size / 1024 / 1024:.1f} MiB）")
    with tempfile.TemporaryDirectory(prefix=".bangumi-update-", dir=output_dir) as temp:
        work_dir = Path(temp)
        archive_path = work_dir / latest.name
        dump_dir = work_dir / "dump"
        staged_output = work_dir / "output"
        download_asset(latest, archive_path, token)
        extract_subject_jsonl(archive_path, dump_dir / JSONL_FILE_NAME)
        generated = generate_files(dump_dir, staged_output)
        generated_by_name = {path.name: path for path in generated}
        for name in (ANIME_CLEANED_FILE, GAME_CLEANED_FILE):
            generated_by_name[name].replace(output_dir / name)

    metadata = {
        "archive_asset_id": latest.asset_id,
        "archive_name": latest.name,
        "archive_url": latest.url,
        "archive_created_at": latest.created_at,
        "archive_updated_at": latest.updated_at,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "anime_records": _record_count(output_dir / ANIME_CLEANED_FILE),
        "game_records": _record_count(output_dir / GAME_CLEANED_FILE),
    }
    temporary_metadata = metadata_path.with_suffix(".json.tmp")
    temporary_metadata.write_text(
        json.dumps(metadata, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    temporary_metadata.replace(metadata_path)
    print(
        f"[OK] 更新完成：动画 {metadata['anime_records']:,} 条，"
        f"游戏 {metadata['game_records']:,} 条"
    )
    return True


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="下载最新 Bangumi Archive 并更新榜单")
    parser.add_argument(
        "--output-dir", type=Path, default=BANGUMI_APP_DATA_DIR, help="数据输出目录"
    )
    parser.add_argument("--force", action="store_true", help="即使归档未变化也重新生成")
    parser.add_argument(
        "--api-url", default=ARCHIVE_RELEASE_API, help="用于测试或镜像的 release API"
    )
    return parser


def run(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        update_latest_data(
            args.output_dir,
            force=args.force,
            api_url=args.api_url,
            token=os.environ.get("GITHUB_TOKEN"),
        )
    except (RuntimeError, OSError, ValueError) as exc:
        print(f"[ERROR] {exc}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(run())
