#!/usr/bin/env python3
"""Render and audit every page of the XA-202609 competition PDF.

The audit is intentionally lightweight: pages are rendered one at a time at
144 dpi, basic clipping/blank-page indicators are recorded, and 2x2 contact
sheets are emitted for human visual inspection.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
from pathlib import Path

import fitz
from PIL import Image, ImageDraw, ImageFont


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def threshold_bbox(gray: Image.Image, cutoff: int = 248) -> tuple[int, int, int, int] | None:
    mask = gray.point(lambda value: 255 if value < cutoff else 0, mode="1")
    return mask.getbbox()


def edge_ink_fraction(gray: Image.Image, cutoff: int = 248, border: int = 3) -> float:
    width, height = gray.size
    regions = (
        gray.crop((0, 0, width, border)),
        gray.crop((0, height - border, width, height)),
        gray.crop((0, border, border, height - border)),
        gray.crop((width - border, border, width, height - border)),
    )
    total = sum(region.width * region.height for region in regions)
    ink = sum(sum(region.histogram()[:cutoff]) for region in regions)
    return ink / total if total else 0.0


def make_contact_sheet(
    thumbnails: list[tuple[int, Image.Image]], output: Path, sheet_index: int
) -> None:
    cell_width, cell_height = 620, 900
    label_height, padding = 34, 14
    sheet = Image.new("RGB", (cell_width * 2, cell_height * 2), "#d9dde3")
    draw = ImageDraw.Draw(sheet)
    font = ImageFont.load_default(size=20)
    for slot, (page_number, image) in enumerate(thumbnails):
        row, column = divmod(slot, 2)
        x0, y0 = column * cell_width, row * cell_height
        draw.rectangle(
            (x0 + padding, y0 + padding, x0 + cell_width - padding, y0 + cell_height - padding),
            fill="white",
        )
        draw.text((x0 + padding + 8, y0 + padding + 5), f"Page {page_number:02d}", fill="black", font=font)
        available = (cell_width - 2 * padding, cell_height - 2 * padding - label_height)
        preview = image.copy()
        preview.thumbnail(available, Image.Resampling.LANCZOS)
        px = x0 + (cell_width - preview.width) // 2
        py = y0 + padding + label_height + (available[1] - preview.height) // 2
        sheet.paste(preview, (px, py))
    sheet.save(output, dpi=(144, 144), optimize=True)


def audit(pdf_path: Path, output_dir: Path, dpi: int = 144) -> dict[str, object]:
    output_dir.mkdir(parents=True, exist_ok=True)
    document = fitz.open(pdf_path)
    scale = dpi / 72.0
    rows: list[dict[str, object]] = []
    pending_thumbnails: list[tuple[int, Image.Image]] = []
    contact_sheets: list[str] = []

    for index, page in enumerate(document):
        page_number = index + 1
        pixmap = page.get_pixmap(matrix=fitz.Matrix(scale, scale), alpha=False)
        page_path = output_dir / f"page_{page_number:02d}.png"
        pixmap.save(page_path)
        with Image.open(page_path) as rendered:
            rgb = rendered.convert("RGB")
            gray = rgb.convert("L")
            histogram = gray.histogram()
            pixels = gray.width * gray.height
            ink_fraction = sum(histogram[:248]) / pixels
            bbox = threshold_bbox(gray)
            if bbox is None:
                margins = (gray.width, gray.height, gray.width, gray.height)
            else:
                left, top, right, bottom = bbox
                margins = (left, top, gray.width - right, gray.height - bottom)
            edge_fraction = edge_ink_fraction(gray)
            status = "pass"
            reasons: list[str] = []
            if ink_fraction < 0.002:
                status = "review"
                reasons.append("near_blank")
            if edge_fraction > 0:
                status = "review"
                reasons.append("ink_at_page_edge")
            if min(margins) < 8:
                status = "review"
                reasons.append("content_margin_below_8px")
            rows.append(
                {
                    "page": page_number,
                    "width_px": gray.width,
                    "height_px": gray.height,
                    "ink_fraction": round(ink_fraction, 6),
                    "edge_ink_fraction": round(edge_fraction, 8),
                    "left_margin_px": margins[0],
                    "top_margin_px": margins[1],
                    "right_margin_px": margins[2],
                    "bottom_margin_px": margins[3],
                    "status": status,
                    "reason": ";".join(reasons) if reasons else "none",
                    "png": page_path.name,
                }
            )
            preview = rgb.copy()
            preview.thumbnail((580, 830), Image.Resampling.LANCZOS)
            pending_thumbnails.append((page_number, preview))

        if len(pending_thumbnails) == 4 or page_number == document.page_count:
            sheet_number = len(contact_sheets) + 1
            sheet_path = output_dir / f"contact_sheet_{sheet_number:02d}.png"
            make_contact_sheet(pending_thumbnails, sheet_path, sheet_number)
            contact_sheets.append(sheet_path.name)
            pending_thumbnails = []

    csv_path = output_dir / "page_metrics.csv"
    with csv_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)

    page_rect = document[0].rect if document.page_count else fitz.Rect()
    manifest: dict[str, object] = {
        "pdf": str(pdf_path.as_posix()),
        "pdf_sha256": sha256(pdf_path),
        "pdf_bytes": pdf_path.stat().st_size,
        "pdf_format": document.metadata.get("format"),
        "pages": document.page_count,
        "page_size_points": [round(page_rect.width, 3), round(page_rect.height, 3)],
        "render_dpi": dpi,
        "review_pages": [row["page"] for row in rows if row["status"] != "pass"],
        "contact_sheets": contact_sheets,
        "page_metrics": rows,
    }
    manifest_path = output_dir / "visual_qa_manifest.json"
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    markdown = [
        "# XA-202609 PDF visual QA",
        "",
        f"- PDF SHA256: `{manifest['pdf_sha256']}`",
        f"- Pages: {document.page_count}",
        f"- Render: {dpi} dpi; every page rendered",
        f"- Automated review pages: {manifest['review_pages'] or 'none'}",
        "- Contact sheets require human visual inspection before delivery.",
        "",
        "| page | ink | edge ink | margins L/T/R/B (px) | status |",
        "|---:|---:|---:|---|---|",
    ]
    for row in rows:
        margins = "/".join(
            str(row[key])
            for key in ("left_margin_px", "top_margin_px", "right_margin_px", "bottom_margin_px")
        )
        markdown.append(
            f"| {row['page']} | {row['ink_fraction']:.4f} | {row['edge_ink_fraction']:.6f} | "
            f"{margins} | {row['status']} |"
        )
    (output_dir / "VISUAL_QA.md").write_text("\n".join(markdown) + "\n", encoding="utf-8")
    document.close()
    return manifest


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--pdf", type=Path, default=Path("submission_competition/main.pdf"))
    parser.add_argument("--output-dir", type=Path, default=Path("submission_competition/pdf_qa"))
    parser.add_argument("--dpi", type=int, default=144)
    args = parser.parse_args()
    manifest = audit(args.pdf.resolve(), args.output_dir.resolve(), dpi=args.dpi)
    print(
        json.dumps(
            {
                "pages": manifest["pages"],
                "review_pages": manifest["review_pages"],
                "pdf_sha256": manifest["pdf_sha256"],
                "output_dir": str(args.output_dir),
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
