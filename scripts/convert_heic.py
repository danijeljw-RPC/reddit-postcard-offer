#!/usr/bin/env python3
"""Convert HEIC/HEIF images under src/images to JPEG files."""

from __future__ import annotations

import argparse
from pathlib import Path
HEIC_EXTENSIONS = {".heic", ".heif"}


def find_heic_images(source_directory: Path) -> list[Path]:
    """Return HEIC/HEIF files recursively in a predictable order."""
    return sorted(
        (
            path
            for path in source_directory.rglob("*")
            if path.is_file() and path.suffix.lower() in HEIC_EXTENSIONS
        ),
        key=lambda path: str(path.relative_to(source_directory)).casefold(),
    )


def convert_heic_images(
    source_directory: Path,
    *,
    quality: int = 92,
    overwrite: bool = False,
) -> list[Path]:
    """Convert each HEIC/HEIF image to a JPG beside the source image."""
    source_directory = source_directory.resolve()
    if not source_directory.exists():
        raise FileNotFoundError(f"Image directory does not exist: {source_directory}")

    sources = find_heic_images(source_directory)
    if not sources:
        print(f"No HEIC/HEIF files found under {source_directory}")
        return []

    try:
        from PIL import Image, ImageOps
        from pillow_heif import register_heif_opener
    except ImportError as exc:
        raise RuntimeError(
            "HEIC conversion dependencies are missing. "
            "Run: python -m pip install -r requirements.txt"
        ) from exc

    register_heif_opener()
    converted: list[Path] = []

    for source in sources:
        target = source.with_suffix(".jpg")

        if target.exists() and not overwrite:
            print(f"Skipping existing file: {target.relative_to(source_directory)}")
            continue

        with Image.open(source) as image:
            image = ImageOps.exif_transpose(image)
            if image.mode != "RGB":
                image = image.convert("RGB")

            target.parent.mkdir(parents=True, exist_ok=True)
            image.save(
                target,
                format="JPEG",
                quality=quality,
                optimize=True,
                progressive=True,
            )

        converted.append(target)
        print(
            "Converted "
            f"{source.relative_to(source_directory)} -> "
            f"{target.relative_to(source_directory)}"
        )

    return converted


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Convert all HEIC/HEIF files under a directory to JPG."
    )
    parser.add_argument(
        "source_directory",
        nargs="?",
        type=Path,
        default=Path("src/images"),
        help="Directory containing HEIC files (default: src/images).",
    )
    parser.add_argument(
        "--quality",
        type=int,
        default=92,
        choices=range(1, 101),
        metavar="1-100",
        help="JPEG quality (default: 92).",
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Replace JPG files that already exist.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_arguments()
    try:
        converted = convert_heic_images(
            args.source_directory,
            quality=args.quality,
            overwrite=args.overwrite,
        )
    except (FileNotFoundError, RuntimeError) as exc:
        print(f"Error: {exc}")
        return 1

    print(f"HEIC conversion complete: {len(converted)} file(s) created.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
