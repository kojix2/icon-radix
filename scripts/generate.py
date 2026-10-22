#!/usr/bin/env python3
"""Generate Crystal icons from a Radix Icons ZIP (requires librsvg and Cairo)."""

import argparse
import base64
import ctypes as c
from ctypes.util import find_library
import os
from pathlib import Path
import re
import tempfile
import zipfile

SVG = re.compile(r"[^/]+/packages/radix-icons/icons/([a-z0-9-]+)\.svg\Z")


def bind(library, name, result, *args):
    function = getattr(c.CDLL(find_library(library) or library), name)
    function.restype, function.argtypes = result, args
    return function


ptr, integer = c.c_void_p, c.c_int
new_handle = bind("rsvg-2", "rsvg_handle_new_from_data", ptr, c.c_char_p, c.c_size_t, ptr)
render_document = bind("rsvg-2", "rsvg_handle_render_document", integer, ptr, ptr, ptr, ptr)
new_surface = bind("cairo", "cairo_image_surface_create", ptr, integer, integer, integer)
new_context = bind("cairo", "cairo_create", ptr, ptr)
write_png = bind("cairo", "cairo_surface_write_to_png", integer, ptr, c.c_char_p)
destroy_context = bind("cairo", "cairo_destroy", None, ptr)
destroy_surface = bind("cairo", "cairo_surface_destroy", None, ptr)
unref = bind("gobject-2.0", "g_object_unref", None, ptr)


class Rectangle(c.Structure):
    _fields_ = [(field, c.c_double) for field in ("x", "y", "width", "height")]


def rasterize(svg, name):
    handle = new_handle(svg, len(svg), None)
    if not handle:
        raise ValueError(f"Cannot parse SVG: {name}")
    surface = new_surface(0, 15, 15)  # CAIRO_FORMAT_ARGB32
    context = new_context(surface)
    try:
        viewport = Rectangle(0, 0, 15, 15)
        if not render_document(handle, context, c.byref(viewport), None):
            raise ValueError(f"Cannot render SVG: {name}")
        with tempfile.NamedTemporaryFile(suffix=".png") as file:
            if write_png(surface, os.fsencode(file.name)):
                raise ValueError(f"Cannot encode PNG: {name}")
            png = Path(file.name).read_bytes()
        if png[:8] != b"\x89PNG\r\n\x1a\n" or png[16:24] != bytes.fromhex("0000000f0000000f"):
            raise ValueError(f"Invalid PNG: {name}")
        return png
    finally:
        destroy_context(context)
        destroy_surface(surface)
        unref(handle)


def generate(archive, output, check=False):
    with zipfile.ZipFile(archive) as source:
        icons = sorted((match[1], path) for path in source.namelist()
                       if (match := SVG.fullmatch(path)))
        if not icons:
            raise ValueError("No Radix SVG icons found in source archive")
        rows = []
        names = set()
        for name, path in icons:
            identifier = ''.join(part.capitalize() for part in name.split('-'))
            if identifier in names:
                raise ValueError(f"Conflicting Crystal identifier: {identifier}")
            names.add(identifier)
            png = rasterize(source.read(path), name)
            rows.append(f"{identifier}\t{base64.b64encode(png).decode()}\n")
    result = ''.join(rows)
    groups = output.parent / "groups.txt"
    if check:
        if output.read_text() != result or groups.read_text() != "icons\n":
            raise ValueError("Generated data is out of date")
        print(f"OK: {len(icons)} icons, data file matches")
    else:
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(result)
        groups.write_text("icons\n")
        print(f"Generated {len(icons)} icons: {output}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("archive", type=Path)
    parser.add_argument("--output", type=Path, default=Path(__file__).resolve().parents[1] / "src/data/icons.tsv")
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    generate(args.archive, args.output, args.check)
