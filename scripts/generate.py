#!/usr/bin/env python3
"""Generate Crystal icons from the pinned Radix ZIP (requires librsvg and Cairo)."""

import argparse
import base64
import ctypes as c
from ctypes.util import find_library
import hashlib
import os
from pathlib import Path
import re
import tempfile
import zipfile

SOURCE_SHA256 = "6d4567f85dcb3bf6a773fae1c6d42a4ad5a75b59f8ddac0936205c30c28f1000"
SOURCE_COMMIT = "112af91ad275a63c3a29b0da2588342af74ef9bf"
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


def generate(archive, output, check=False, allow_different_source=False):
    digest = hashlib.sha256(archive.read_bytes()).hexdigest()
    if digest != SOURCE_SHA256 and not allow_different_source:
        raise ValueError(f"Source archive SHA-256 mismatch: {digest}; expected {SOURCE_SHA256}")
    with zipfile.ZipFile(archive) as zip_file:
        icons = sorted((match[1], path) for path in zip_file.namelist()
                       if (match := SVG.fullmatch(path)))
        if not icons:
            raise ValueError("No Radix SVG icons found in source archive")
        lines = [
            "# Generated from radix-ui/icons (MIT). Do not edit manually.",
            f"# Upstream commit: {'UPDATED_SOURCE_CHECK_REQUIRED' if allow_different_source else SOURCE_COMMIT}",
            f"# Source archive SHA-256: {digest}",
            'require "base64"', 'require "crimage"', '', 'module Icon', '  module Radix',
            '    # Shared CrImage image constants. Copy before modifying.',
            '    private def self.decode_png(encoded : String)',
            '      CrImage.read(IO::Memory.new(Base64.decode(encoded)))', '    end', '',
        ]
        identifiers = set()
        for name, path in icons:
            identifier = ''.join(part.capitalize() for part in name.split('-'))
            if identifier in identifiers:
                raise ValueError(f"Conflicting Crystal identifier: {identifier}")
            identifiers.add(identifier)
            png = rasterize(zip_file.read(path), name)
            lines += [f"    # {name} (15x15)",
                      f'    {identifier} = decode_png("{base64.b64encode(png).decode()}")']
    result = '\n'.join(lines + ['  end', 'end', ''])
    if check:
        if output.read_text() != result:
            raise ValueError("Generated file is out of date")
        print(f"OK: {len(icons)} icons, generated file matches")
    else:
        output.write_text(result)
        print(f"Generated {len(icons)} icons: {output}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("archive", type=Path)
    parser.add_argument("--output", type=Path, default=Path(__file__).resolve().parents[1] / "src/icon/radix.cr")
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--allow-different-source", action="store_true")
    args = parser.parse_args()
    generate(args.archive, args.output, args.check, args.allow_different_source)
