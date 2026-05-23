#!/usr/bin/env python3
"""Extract monthly intern-report PPTX decks into AI-readable Markdown and JSON.

The script intentionally avoids copying source PPTX binaries into the repository.
It reads Office Open XML directly, including slide text, speaker notes, image
relationships, image dimensions, and best-effort English OCR from embedded media.
"""

from __future__ import annotations

import hashlib
import json
import os
import posixpath
import re
import shutil
import subprocess
import sys
import zipfile
from dataclasses import dataclass
from datetime import date
from io import BytesIO
from pathlib import Path, PurePosixPath
from typing import Iterable
from xml.etree import ElementTree as ET

from PIL import Image


NS = {
    "a": "http://schemas.openxmlformats.org/drawingml/2006/main",
    "p": "http://schemas.openxmlformats.org/presentationml/2006/main",
    "r": "http://schemas.openxmlformats.org/officeDocument/2006/relationships",
    "rel": "http://schemas.openxmlformats.org/package/2006/relationships",
}

REPO_ROOT = Path(__file__).resolve().parents[3]
OUTPUT_DIR = Path(__file__).resolve().parent
SCRATCH_DIR = OUTPUT_DIR / ".ocr-scratch"
TODAY = os.environ.get("SOURCE_DATE", date.today().isoformat())


@dataclass(frozen=True)
class DeckSource:
    slug: str
    period: str
    title: str
    source_path: Path
    source_role: str
    narrative_spine: list[str]
    project_crosswalk: list[str]
    reuse_notes: list[str]


SOURCES = [
    DeckSource(
        slug="2026-01-intern-report-jiang-haohua",
        period="2026-01",
        title="2026年01月实习生汇报（兼年终总结）：并行组装整体刚度矩阵算法调研及实现",
        source_path=Path(
            "/Users/haohua_jiang/Documents/Intern_Peking University_supu/"
            "2026年01月实习生汇报/2026年01月实习生汇报-江浩华.pptx"
        ),
        source_role="GPU/CPU 并行组装前期问题定义、算法调研和早期原型材料。",
        narrative_spine=[
            "从自研有限元软件的整体刚度矩阵组装效率瓶颈切入：串行组装、COO 到 CSR 转换、缺少硬件平台优化。",
            "把并行组装拆成可比较的算法族：图着色法、直接累加/Addto/原子操作、区域分解/线程私有或子域策略。",
            "用有限元组装流程解释为什么写入冲突和稀疏矩阵存储格式是核心矛盾。",
            "沉淀早期实现思路：先用相对小的原型验证正确性、冲突规避和 OpenMP/CPU 并行可行性。",
            "报告后段切到 ANSYS APDL 仿真案例，属于同期实习内容，但不是当前 CPU 组装主线的主要技术来源。",
        ],
        project_crosswalk=[
            "`docs/requirements/cpu-parallel-stiffness-assembly-design.md` 的研究背景部分已经引用这份 2026-01 月报；本文件是它的逐页来源补全。",
            "图着色法对应当前 `coloring` backend；Addto/直接累加对应当前 `atomic` 类路线；区域分解/私有缓冲思想对应当前 `private_csr`、`row_owner` 等 CPU 主线实现。",
            "GPU slides 属于历史探索和对比背景；当前仓库范围仍以 CPU 并行组装和可复现实验平台为主。",
            "ANSYS APDL 案例只说明同期实习工作量，不应进入当前 CPU benchmark 结论链。",
        ],
        reuse_notes=[
            "适合复用为项目背景、研究动机、算法族 taxonomy 和从 GPU/原型向 CPU 主线迁移的历史依据。",
            "不应直接复用其中的早期性能判断作为当前结论；当前仓库的 benchmark 和 2026-04/05 结果优先级更高。",
        ],
    ),
    DeckSource(
        slug="2026-04-intern-report-jiang-haohua-version5",
        period="2026-04",
        title="2026年04月实习生汇报：整体刚度矩阵并行组装算法",
        source_path=Path(
            "/Users/haohua_jiang/Documents/Intern_Peking University_supu/"
            "2026年04月实习生汇报/2026年04月实习生汇报-江浩华_version5.pptx"
        ),
        source_role="CPU 多线程主线转向后的汇报版本，包含真实工程网格、算法框架、正确性/效率/内存结果与阶段判断。",
        narrative_spine=[
            "承接前期 GPU 探索，但明确本月重点转为 CPU 多线程可复现实验和算法对比。",
            "先交代实验对象和代码结构，再解释组装原理，避免把图表结果脱离有限元组装流程展示。",
            "用真实工程网格 physics_tet4 结果组织证据：正确性、效率和内存占用是三个并列验收维度。",
            "从结果回到阶段判断：当前不是只追最高加速比，而是要选出能在真实网格上继续优化的 CPU 算法主线。",
            "后续工作落在 row_owner、private_csr、atomic 等实现的性能分析、内存解释和跨平台复现实验。",
        ],
        project_crosswalk=[
            "本 deck 的 CPU-first 叙事与当前仓库 README、需求文档和 `cpu_parallel_stiffness_assembly` 主线一致。",
            "真实工程网格 `3d-WindTurbineHub.inp`、`physics_tet4`、正确性/效率/内存三维度，对应当前 `results/2026-04-22`、`results/2026-04-28-*` 和后续 2026-05 result reports。",
            "Slide 12 的阶段判断可作为 2026-04 汇报时刻的决策快照；若与 2026-05 benchmark 或 cross-platform reports 冲突，以后者为准。",
            "本 deck 可为 mentor next-steps、weekly meeting Beamer 和 project-long-term-beamer 提供讲述顺序，但不应覆盖最新 source index 中的 result evidence。",
        ],
        reuse_notes=[
            "适合复用为当前仓库 CPU-first 叙事、真实网格实验上下文、图表解释和 mentor/weekly Beamer 的历史来源。",
            "图表数值若与仓库 results 目录冲突，以仓库中最新 CSV/JSON/报告为准；本文件负责记录汇报叙事，不替代 benchmark source of truth。",
        ],
    ),
]


CHROME_PATTERNS = [
    re.compile(r"^\d+$"),
    re.compile(r"^20\d{2}/\d{1,2}/\d{1,2}$"),
    re.compile(r"^Regular Report$", re.I),
    re.compile(r"^报告人[:：]"),
    re.compile(r"^合作导师[:：]"),
]


def qn(tag: str) -> str:
    prefix, name = tag.split(":", 1)
    return f"{{{NS[prefix]}}}{name}"


def normalize_target(base_dir: str, target: str) -> str:
    return posixpath.normpath(PurePosixPath(base_dir).joinpath(target).as_posix())


def relationship_map(zf: zipfile.ZipFile, rel_path: str) -> dict[str, dict[str, str]]:
    if rel_path not in zf.namelist():
        return {}
    root = ET.fromstring(zf.read(rel_path))
    return {
        rel.attrib["Id"]: {
            "type": rel.attrib.get("Type", ""),
            "target": rel.attrib.get("Target", ""),
            "target_mode": rel.attrib.get("TargetMode", ""),
        }
        for rel in root
    }


def presentation_slide_order(zf: zipfile.ZipFile) -> list[str]:
    pres = ET.fromstring(zf.read("ppt/presentation.xml"))
    rels = relationship_map(zf, "ppt/_rels/presentation.xml.rels")
    slides: list[str] = []
    for slide_id in pres.findall(".//p:sldIdLst/p:sldId", NS):
        rid = slide_id.attrib.get(qn("r:id"))
        if not rid or rid not in rels:
            continue
        target = rels[rid]["target"]
        slides.append(normalize_target("ppt", target))
    return slides


def paragraph_texts(root: ET.Element) -> list[str]:
    lines: list[str] = []
    for paragraph in root.findall(".//a:p", NS):
        runs = [t.text or "" for t in paragraph.findall(".//a:t", NS)]
        text = "".join(runs).strip()
        if text:
            lines.append(text)
    return dedupe_keep_order(lines)


def dedupe_keep_order(values: Iterable[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        if value not in seen:
            seen.add(value)
            result.append(value)
    return result


def is_chrome(text: str) -> bool:
    stripped = text.strip()
    return any(pattern.search(stripped) for pattern in CHROME_PATTERNS)


def content_lines(lines: Iterable[str]) -> list[str]:
    return [line for line in lines if not is_chrome(line)]


def infer_title(lines: list[str]) -> str:
    candidates = content_lines(lines)
    if not candidates:
        return lines[0] if lines else ""
    return candidates[0]


def shape_blocks(root: ET.Element) -> list[dict[str, object]]:
    blocks: list[dict[str, object]] = []
    for shape in root.findall(".//p:sp", NS) + root.findall(".//p:graphicFrame", NS):
        texts = paragraph_texts(shape)
        if not texts:
            continue
        props = shape.find(".//p:cNvPr", NS)
        blocks.append(
            {
                "name": props.attrib.get("name", "") if props is not None else "",
                "descr": props.attrib.get("descr", "") if props is not None else "",
                "text": texts,
            }
        )
    return blocks


def slide_notes(zf: zipfile.ZipFile, slide_path: str) -> tuple[str | None, list[str]]:
    rel_path = f"ppt/slides/_rels/{Path(slide_path).name}.rels"
    rels = relationship_map(zf, rel_path)
    for rel in rels.values():
        if rel["type"].endswith("/notesSlide"):
            note_path = normalize_target("ppt/slides", rel["target"])
            if note_path in zf.namelist():
                return note_path, content_lines(paragraph_texts(ET.fromstring(zf.read(note_path))))
    return None, []


def slide_media(zf: zipfile.ZipFile, slide_path: str, root: ET.Element, ocr_tool: str | None) -> list[dict[str, object]]:
    rel_path = f"ppt/slides/_rels/{Path(slide_path).name}.rels"
    rels = relationship_map(zf, rel_path)
    used_rids: set[str] = set()
    media_items: list[dict[str, object]] = []

    for pic in root.findall(".//p:pic", NS):
        props = pic.find(".//p:cNvPr", NS)
        blip = pic.find(".//a:blip", NS)
        rid = blip.attrib.get(qn("r:embed")) if blip is not None else None
        if not rid or rid not in rels:
            continue
        used_rids.add(rid)
        media_items.append(media_record(zf, slide_path, rid, rels[rid], props, ocr_tool))

    for blip in root.findall(".//a:blip", NS):
        rid = blip.attrib.get(qn("r:embed"))
        if not rid or rid in used_rids or rid not in rels:
            continue
        used_rids.add(rid)
        media_items.append(media_record(zf, slide_path, rid, rels[rid], None, ocr_tool))

    return media_items


def media_record(
    zf: zipfile.ZipFile,
    slide_path: str,
    rid: str,
    rel: dict[str, str],
    props: ET.Element | None,
    ocr_tool: str | None,
) -> dict[str, object]:
    target_path = normalize_target(posixpath.dirname(slide_path), rel["target"])
    record: dict[str, object] = {
        "rid": rid,
        "target": target_path,
        "name": props.attrib.get("name", "") if props is not None else "",
        "descr": props.attrib.get("descr", "") if props is not None else "",
        "type": rel["type"],
    }
    if target_path in zf.namelist():
        data = zf.read(target_path)
        record["sha256_12"] = hashlib.sha256(data).hexdigest()[:12]
        try:
            with Image.open(BytesIO(data)) as image:
                record["width_px"] = image.width
                record["height_px"] = image.height
                record["format"] = image.format or ""
        except Exception as exc:  # pragma: no cover - defensive metadata path
            record["image_error"] = str(exc)
        ocr_text = ocr_image(data, target_path, record, ocr_tool)
        if ocr_text:
            record["ocr_eng_best_effort"] = ocr_text
    return record


def ocr_image(data: bytes, target_path: str, record: dict[str, object], ocr_tool: str | None) -> str:
    if not ocr_tool:
        return ""
    width = int(record.get("width_px") or 0)
    height = int(record.get("height_px") or 0)
    if width < 240 or height < 120:
        return ""
    suffix = Path(target_path).suffix or ".png"
    SCRATCH_DIR.mkdir(parents=True, exist_ok=True)
    image_path = SCRATCH_DIR / f"ocr-{hashlib.sha1(data).hexdigest()[:12]}{suffix}"
    image_path.write_bytes(data)
    try:
        proc = subprocess.run(
            [ocr_tool, str(image_path), "stdout", "-l", "eng", "--psm", "6"],
            text=True,
            capture_output=True,
            timeout=30,
            check=False,
        )
    except Exception:
        return ""
    text = clean_ocr(proc.stdout)
    if not useful_ocr(text):
        return ""
    return text


def clean_ocr(text: str) -> str:
    lines = []
    for raw in text.splitlines():
        line = re.sub(r"\s+", " ", raw).strip()
        if line:
            lines.append(line)
    return "\n".join(lines[:30])


def useful_ocr(text: str) -> bool:
    compact = re.sub(r"\s+", "", text)
    if len(compact) < 18:
        return False
    alnum = sum(ch.isalnum() for ch in compact)
    return alnum / max(len(compact), 1) > 0.45


def extract_deck(source: DeckSource, ocr_tool: str | None) -> dict[str, object]:
    if not source.source_path.exists():
        raise FileNotFoundError(source.source_path)
    with zipfile.ZipFile(source.source_path) as zf:
        slide_paths = presentation_slide_order(zf)
        slides = []
        for index, slide_path in enumerate(slide_paths, start=1):
            root = ET.fromstring(zf.read(slide_path))
            visible_text = paragraph_texts(root)
            notes_path, notes = slide_notes(zf, slide_path)
            slides.append(
                {
                    "slide_number": index,
                    "slide_path": slide_path,
                    "notes_path": notes_path,
                    "title_or_claim": infer_title(visible_text),
                    "visible_text": visible_text,
                    "content_text": content_lines(visible_text),
                    "speaker_notes": notes,
                    "shape_blocks": shape_blocks(root),
                    "media": slide_media(zf, slide_path, root, ocr_tool),
                }
            )
        return {
            "slug": source.slug,
            "period": source.period,
            "title": source.title,
            "source_path": str(source.source_path),
            "source_role": source.source_role,
            "source_size_bytes": source.source_path.stat().st_size,
            "extracted_on": TODAY,
            "slide_count": len(slides),
            "slides_with_notes": sum(1 for slide in slides if slide["speaker_notes"]),
            "media_count": sum(len(slide["media"]) for slide in slides),
            "narrative_spine": source.narrative_spine,
            "project_crosswalk": source.project_crosswalk,
            "reuse_notes": source.reuse_notes,
            "slides": slides,
        }


def md_escape(text: str) -> str:
    return re.sub(r"\s*\n\s*", " / ", text).replace("|", "\\|")


def bullet_lines(lines: Iterable[str]) -> str:
    values = [line for line in lines if line.strip()]
    if not values:
        return "- None extracted."
    return "\n".join(f"- {line}" for line in values)


def code_block(lines: Iterable[str]) -> str:
    values = [line for line in lines if line.strip()]
    if not values:
        return "None extracted."
    return "\n".join(values)


def render_deck_markdown(deck: dict[str, object]) -> str:
    slides = deck["slides"]
    lines: list[str] = [
        f"# {deck['title']}",
        "",
        "> AI-readable extraction of an existing monthly intern-report PPTX. The raw PPTX is not copied into this repository.",
        "",
        "## Metadata",
        "",
        f"- Period: `{deck['period']}`",
        f"- Source path: `{deck['source_path']}`",
        f"- Source role: {deck['source_role']}",
        f"- Extracted on: `{deck['extracted_on']}`",
        f"- Slides: `{deck['slide_count']}`",
        f"- Slides with speaker notes: `{deck['slides_with_notes']}`",
        f"- Embedded media references: `{deck['media_count']}`",
        "",
        "## AI Reading Guide",
        "",
        "- Start with the narrative spine below to understand the deck's argument.",
        "- Use the slide table for fast retrieval.",
        "- Use the slide-level sections for exact visible text, speaker notes, and media metadata.",
        "- OCR is best-effort English-only from embedded images; Chinese text in images may not be captured.",
        "- Treat benchmark numbers here as report context; current repository CSV/JSON/result reports remain the source of truth.",
        "",
        "## Narrative Spine",
        "",
        bullet_lines(deck["narrative_spine"]),
        "",
        "## Reuse Boundary",
        "",
        bullet_lines(deck["reuse_notes"]),
        "",
        "## Project Crosswalk",
        "",
        bullet_lines(deck["project_crosswalk"]),
        "",
        "## Slide Index",
        "",
        "| Slide | Inferred title / claim | Visible content lines | Notes lines | Media |",
        "| ---: | --- | ---: | ---: | ---: |",
    ]
    for slide in slides:
        lines.append(
            "| {num} | {title} | {text_count} | {notes_count} | {media_count} |".format(
                num=slide["slide_number"],
                title=md_escape(slide["title_or_claim"]),
                text_count=len(slide["content_text"]),
                notes_count=len(slide["speaker_notes"]),
                media_count=len(slide["media"]),
            )
        )

    lines += ["", "## Slide-Level Extraction", ""]
    for slide in slides:
        lines += [
            f"### Slide {slide['slide_number']}: {slide['title_or_claim'] or 'Untitled'}",
            "",
            f"- Slide XML: `{slide['slide_path']}`",
        ]
        if slide["notes_path"]:
            lines.append(f"- Notes XML: `{slide['notes_path']}`")
        if slide["media"]:
            lines.append(f"- Media count: `{len(slide['media'])}`")
        lines += [
            "",
            "#### Visible Text",
            "",
            "```text",
            code_block(slide["visible_text"]),
            "```",
            "",
            "#### Speaker Notes",
            "",
            "```text",
            code_block(slide["speaker_notes"]),
            "```",
            "",
        ]
        if slide["media"]:
            lines += [
                "#### Embedded Media",
                "",
                "| Target | Name / alt text | Size | OCR excerpt |",
                "| --- | --- | --- | --- |",
            ]
            for media in slide["media"]:
                name = " / ".join(
                    part for part in [str(media.get("name", "")), str(media.get("descr", ""))] if part
                )
                size = ""
                if media.get("width_px") and media.get("height_px"):
                    size = f"{media['width_px']}x{media['height_px']} {media.get('format', '')}".strip()
                ocr = str(media.get("ocr_eng_best_effort", "")).replace("\n", " / ")
                if len(ocr) > 180:
                    ocr = ocr[:177] + "..."
                lines.append(
                    "| `{target}` | {name} | {size} | {ocr} |".format(
                        target=media.get("target", ""),
                        name=md_escape(name or "-"),
                        size=md_escape(size or "-"),
                        ocr=md_escape(ocr or "-"),
                    )
                )
            lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def render_readme(decks: list[dict[str, object]]) -> str:
    lines = [
        "# Monthly Intern Report Source Deck Extracts",
        "",
        "This directory stores AI-readable extracts of monthly intern-report slide decks that are directly relevant to the current CPU parallel global stiffness assembly project.",
        "",
        "## Repository Existence Check",
        "",
        "A repository search found only partial references before this directory was added:",
        "",
        "- `docs/requirements/cpu-parallel-stiffness-assembly-design.md` mentioned the 2026-01 monthly report as historical background.",
        "- 2026-04 benchmark/result assets existed under `parallel_global_stiffness_assembly/cpu_parallel_stiffness_assembly/results/`, but not the detailed PPT narrative.",
        "- No raw PPTX copy or slide-level AI-readable extraction for the two requested Jiang Haohua monthly reports was present in the repository.",
        "",
        "The raw PPTX files remain outside this repository to respect the repository scope rule that excludes one-off slide binaries. The durable project context is kept here as Markdown and JSON.",
        "",
        "## Extracted Decks",
        "",
        "| Period | AI-readable file | Slides | Notes slides | Media refs | Source path |",
        "| --- | --- | ---: | ---: | ---: | --- |",
    ]
    for deck in decks:
        md_name = f"{deck['slug']}.md"
        lines.append(
            "| {period} | [`{md}`]({md}) | {slides} | {notes} | {media} | `{source}` |".format(
                period=deck["period"],
                md=md_name,
                slides=deck["slide_count"],
                notes=deck["slides_with_notes"],
                media=deck["media_count"],
                source=deck["source_path"],
            )
        )

    lines += [
        "",
        "## File Format",
        "",
        "- `*.md`: human- and AI-readable narrative spine, reuse boundary, slide index, exact visible text, speaker notes, embedded-media metadata, and best-effort OCR snippets.",
        "- `manifest.json`: machine-readable extraction with one object per deck and one record per slide.",
        "- `extract_monthly_report_pptx.py`: repeatable extractor for these source decks.",
        "",
        "## Regeneration",
        "",
        "Run from the repository root:",
        "",
        "```bash",
        "\"/Users/haohua_jiang/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3\" \\",
        "  docs/context/monthly-intern-reports/extract_monthly_report_pptx.py",
        "```",
        "",
        "The extractor uses Office Open XML directly and does not require PowerPoint or LibreOffice. If `tesseract` is available, it also performs best-effort English OCR on embedded images.",
        "",
        "## Use In Current Project",
        "",
        "- Use the 2026-01 deck to understand the original problem framing and algorithm-family taxonomy.",
        "- Use the 2026-04 deck to understand the CPU-first pivot, real engineering mesh result narrative, and report-time interpretation of correctness, efficiency, and memory evidence.",
        "- Use current `results/`, `docs/requirements/`, and `reports/` files for up-to-date benchmark facts.",
        "",
    ]
    return "\n".join(lines)


def write_outputs(decks: list[dict[str, object]]) -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    (OUTPUT_DIR / "manifest.json").write_text(
        json.dumps({"generated_on": TODAY, "decks": decks}, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    for deck in decks:
        (OUTPUT_DIR / f"{deck['slug']}.md").write_text(render_deck_markdown(deck), encoding="utf-8")
    (OUTPUT_DIR / "README.md").write_text(render_readme(decks), encoding="utf-8")


def main() -> int:
    ocr_tool = shutil.which("tesseract")
    if SCRATCH_DIR.exists():
        shutil.rmtree(SCRATCH_DIR)
    try:
        decks = [extract_deck(source, ocr_tool) for source in SOURCES]
        write_outputs(decks)
    finally:
        if SCRATCH_DIR.exists():
            shutil.rmtree(SCRATCH_DIR)
    print(f"Wrote {len(SOURCES)} deck extracts to {OUTPUT_DIR}")
    for source in SOURCES:
        print(f"- {source.slug}.md")
    return 0


if __name__ == "__main__":
    sys.exit(main())
