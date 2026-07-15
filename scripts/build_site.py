#!/usr/bin/env python3
"""Build the responsive postcard site into the dist directory."""

from __future__ import annotations

import argparse
import html
import json
import re
import shutil
from pathlib import Path
from urllib.parse import quote

from convert_heic import convert_heic_images

ROOT_DIRECTORY = Path(__file__).resolve().parents[1]
DEFAULT_SOURCE_DIRECTORY = ROOT_DIRECTORY / "src"
DEFAULT_OUTPUT_DIRECTORY = ROOT_DIRECTORY / "dist"
JPEG_EXTENSIONS = {".jpg", ".jpeg"}


def natural_sort_key(value: str) -> list[object]:
    """Sort filenames naturally so 2 appears before 10."""
    return [
        int(part) if part.isdigit() else part.casefold()
        for part in re.split(r"(\d+)", value)
    ]


def load_config(config_path: Path) -> dict[str, str]:
    with config_path.open("r", encoding="utf-8") as stream:
        config = json.load(stream)

    required_fields = {
        "title",
        "description",
        "heroText",
        "redditThreadUrl",
        "siteUrl",
        "dispatchDate",
        "senderCountry",
        "availabilityNote",
        "randomRequestText",
        "addressPrivacyText",
    }
    missing_fields = sorted(required_fields.difference(config))
    if missing_fields:
        raise ValueError(
            "Missing required site.json field(s): " + ", ".join(missing_fields)
        )

    return {key: str(value) for key, value in config.items()}


def find_jpeg_images(image_directory: Path) -> list[Path]:
    return sorted(
        (
            path
            for path in image_directory.rglob("*")
            if path.is_file() and path.suffix.lower() in JPEG_EXTENSIONS
        ),
        key=lambda path: natural_sort_key(
            str(path.relative_to(image_directory)).replace("\\", "/")
        ),
    )


def make_section_id(relative_path: Path, index: int) -> str:
    value = relative_path.with_suffix("").as_posix().casefold()
    slug = re.sub(r"[^a-z0-9]+", "-", value).strip("-")
    return f"postcard-{index}-{slug or 'image'}"


def render_postcard_sections(
    image_paths: list[Path],
    source_image_directory: Path,
    output_image_directory: Path,
) -> str:
    if not image_paths:
        return (
            '<div class="empty-state">'
            "No postcard photos have been added yet. Add HEIC or JPG files to "
            "<code>src/images</code> and run the build again."
            "</div>"
        )

    sections: list[str] = []

    for index, source_path in enumerate(image_paths, start=1):
        relative_path = source_path.relative_to(source_image_directory)
        destination_path = output_image_directory / relative_path
        destination_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source_path, destination_path)

        # The heading deliberately uses the exact filename stem supplied by the user.
        heading = source_path.stem
        escaped_heading = html.escape(heading)
        image_url = "images/" + quote(relative_path.as_posix(), safe="/")
        section_id = make_section_id(relative_path, index)

        sections.append(
            "\n".join(
                [
                    f'<section class="postcard-card" id="{section_id}">',
                    f'  <h3 class="postcard-card__heading">{escaped_heading}</h3>',
                    (
                        '  <a class="postcard-card__image-link" '
                        f'href="{image_url}" target="_blank" rel="noopener" '
                        f'aria-label="Open {escaped_heading} at full size">'
                    ),
                    (
                        '    <img class="postcard-card__image" '
                        f'src="{image_url}" alt="{escaped_heading}" '
                        'loading="lazy" decoding="async">'
                    ),
                    "  </a>",
                    "</section>",
                ]
            )
        )

    return "\n".join(sections)


def render_template(template: str, values: dict[str, str]) -> str:
    output = template
    for key, value in values.items():
        output = output.replace("{{" + key + "}}", value)

    unresolved = sorted(set(re.findall(r"{{([A-Z0-9_]+)}}", output)))
    if unresolved:
        raise ValueError(
            "Unresolved template placeholder(s): " + ", ".join(unresolved)
        )

    return output


def build_site(
    source_directory: Path,
    output_directory: Path,
    *,
    convert_heic: bool = True,
    overwrite_converted_images: bool = False,
) -> int:
    source_directory = source_directory.resolve()
    output_directory = output_directory.resolve()
    image_directory = source_directory / "images"

    if convert_heic:
        convert_heic_images(
            image_directory,
            overwrite=overwrite_converted_images,
        )

    config = load_config(source_directory / "site.json")
    template = (source_directory / "template.html").read_text(encoding="utf-8")
    image_paths = find_jpeg_images(image_directory)

    if output_directory.exists():
        shutil.rmtree(output_directory)
    output_directory.mkdir(parents=True)

    sections = render_postcard_sections(
        image_paths,
        image_directory,
        output_directory / "images",
    )
    image_count = len(image_paths)
    count_label = f"{image_count} photo" + ("" if image_count == 1 else "s")

    escaped_values = {
        "TITLE": html.escape(config["title"]),
        "DESCRIPTION": html.escape(config["description"]),
        "HERO_TEXT": html.escape(config["heroText"]),
        "REDDIT_THREAD_URL": html.escape(config["redditThreadUrl"], quote=True),
        "SITE_URL": html.escape(config["siteUrl"], quote=True),
        "DISPATCH_DATE": html.escape(config["dispatchDate"]),
        "SENDER_COUNTRY": html.escape(config["senderCountry"]),
        "AVAILABILITY_NOTE": html.escape(config["availabilityNote"]),
        "RANDOM_REQUEST_TEXT": html.escape(config["randomRequestText"]),
        "ADDRESS_PRIVACY_TEXT": html.escape(config["addressPrivacyText"]),
        "IMAGE_COUNT_LABEL": count_label,
        "SECTIONS": sections,
    }

    rendered_html = render_template(template, escaped_values)
    (output_directory / "index.html").write_text(rendered_html, encoding="utf-8")
    shutil.copy2(source_directory / "styles.css", output_directory / "styles.css")
    shutil.copy2(source_directory / "favicon.svg", output_directory / "favicon.svg")
    (output_directory / ".nojekyll").write_text("", encoding="utf-8")

    print(f"Built {image_count} postcard section(s) into {output_directory}")
    return image_count


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build the postcard website.")
    parser.add_argument(
        "--source",
        type=Path,
        default=DEFAULT_SOURCE_DIRECTORY,
        help="Source directory (default: src).",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT_DIRECTORY,
        help="Output directory (default: dist).",
    )
    parser.add_argument(
        "--skip-heic-conversion",
        action="store_true",
        help="Do not convert HEIC/HEIF files before building.",
    )
    parser.add_argument(
        "--overwrite-converted-images",
        action="store_true",
        help="Replace JPG files previously converted from HEIC/HEIF.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_arguments()
    try:
        build_site(
            args.source,
            args.output,
            convert_heic=not args.skip_heic_conversion,
            overwrite_converted_images=args.overwrite_converted_images,
        )
    except (FileNotFoundError, RuntimeError, ValueError, json.JSONDecodeError) as exc:
        print(f"Build failed: {exc}")
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
