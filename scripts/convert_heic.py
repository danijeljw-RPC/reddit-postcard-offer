#!/usr/bin/env python3
"""Convert HEIC/HEIF images under src/images to colour-managed JPEG files."""

from __future__ import annotations

import argparse
from io import BytesIO
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


def flatten_to_rgb(image):
    """Return an RGB image, flattening transparency onto white when required."""
    from PIL import Image

    if image.mode == "RGB":
        return image

    if image.mode in {"RGBA", "LA"} or "transparency" in image.info:
        rgba = image.convert("RGBA")
        background = Image.new("RGB", rgba.size, "white")
        background.paste(rgba, mask=rgba.getchannel("A"))
        return background

    return image.convert("RGB")


def convert_to_srgb(image, source_icc_profile: bytes | None):
    """Convert image pixels to sRGB and return the image plus sRGB ICC bytes."""
    from PIL import ImageCms

    image = flatten_to_rgb(image)
    srgb_profile = ImageCms.createProfile("sRGB")
    srgb_profile_bytes = ImageCms.ImageCmsProfile(srgb_profile).tobytes()

    if not source_icc_profile:
        # pillow-heif/libheif has already decoded the HEIF colour data to RGB.
        # Embedding sRGB prevents browsers and image viewers from guessing.
        return image, srgb_profile_bytes

    try:
        input_profile = ImageCms.ImageCmsProfile(BytesIO(source_icc_profile))
        image = ImageCms.profileToProfile(
            image,
            input_profile,
            srgb_profile,
            renderingIntent=0,  # Perceptual
            outputMode="RGB",
        )
        return image, srgb_profile_bytes
    except (OSError, ValueError, ImageCms.PyCMSError) as exc:
        # Better to retain the original profile than silently reinterpret its
        # pixel values as sRGB and visibly desaturate the image.
        print(f"Warning: ICC conversion failed ({exc}); preserving source profile.")
        return image, source_icc_profile


def convert_heic_images(
    source_directory: Path,
    *,
    quality: int = 95,
    overwrite: bool = False,
) -> list[Path]:
    """Convert each HEIC/HEIF image to a colour-managed JPG beside the source."""
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

        with Image.open(source) as source_image:
            source_image.load()
            source_icc_profile = source_image.info.get("icc_profile")

            image = ImageOps.exif_transpose(source_image)
            image, output_icc_profile = convert_to_srgb(
                image,
                source_icc_profile,
            )

            exif = image.getexif()
            save_options: dict[str, object] = {
                "format": "JPEG",
                "quality": quality,
                "subsampling": 0,
                "optimize": True,
                "progressive": True,
                "icc_profile": output_icc_profile,
            }

            if exif:
                save_options["exif"] = exif.tobytes()

            target.parent.mkdir(parents=True, exist_ok=True)
            image.save(target, **save_options)

        converted.append(target)
        print(
            "Converted "
            f"{source.relative_to(source_directory)} -> "
            f"{target.relative_to(source_directory)}"
        )

    return converted


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Convert all HEIC/HEIF files under a directory to colour-managed JPG files."
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
        default=95,
        choices=range(1, 101),
        metavar="1-100",
        help="JPEG quality (default: 95).",
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
