#!/usr/bin/env python3
"""
Verify PDF page orientation (portrait or landscape) for each page.
Usage: python verify_pdf_orientation.py <path_to_pdf>
"""

import sys


def get_orientation(width, height):
    if width > height:
        return "Landscape"
    elif height > width:
        return "Portrait"
    else:
        return "Square"


def verify_pdf_orientation(reader, pdf_path: str) -> None:
    total_pages = len(reader.pages)
    print(f"File: {pdf_path}")
    print(f"Total pages: {total_pages}\n")

    orientations = {"Portrait": 0, "Landscape": 0, "Square": 0}

    for i, page in enumerate(reader.pages, start=1):
        width = float(page.mediabox.width)
        height = float(page.mediabox.height)

        # Account for page rotation
        rotation = page.get("/Rotate", 0) or 0
        if rotation in (90, 270):
            width, height = height, width

        orientation = get_orientation(width, height)
        orientations[orientation] += 1

        print(f"  Page {i:>4}: {orientation:<10}  ({width:.1f} x {height:.1f} pts)")

    print(f"\nSummary:")
    for name, count in orientations.items():
        if count:
            print(f"  {name}: {count} page(s)")

    dominant = max(orientations, key=orientations.get)
    print(f"\nOverall orientation: {dominant}")


def main() -> None:
    if len(sys.argv) != 2:
        print(f"Usage: python {sys.argv[0]} <path_to_pdf>")
        sys.exit(1)

    try:
        import pypdf
    except ImportError:
        print("pypdf not found. Install it with: pip install pypdf")
        sys.exit(1)

    pdf_path = sys.argv[1]
    try:
        reader = pypdf.PdfReader(pdf_path)
    except FileNotFoundError:
        print(f"Error: File not found: {pdf_path}")
        sys.exit(1)
    except Exception as e:
        print(f"Error reading PDF: {e}")
        sys.exit(1)

    verify_pdf_orientation(reader, pdf_path)


if __name__ == "__main__":
    main()
