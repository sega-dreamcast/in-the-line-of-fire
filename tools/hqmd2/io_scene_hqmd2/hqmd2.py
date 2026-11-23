#!/usr/bin/env python3
"""
HQMD2 - the "high quality" MD2 variant used by In The Line Of Fire.

This module has no Blender dependency: it is used by the Blender add-on in this
folder and can also be run on its own as a command line tool.

Format
------
HQMD2 is the Quake II MD2 format ("IDP2", version 8) with one change: each
frame vertex is three little-endian unsigned 16-bit coordinates (6 bytes) instead
of three unsigned bytes plus a normal index (4 bytes). There are no normals.

    header      17 x int32       (same fields as MD2)
    skins       num_skins     x char[64]
    texcoords   num_st        x { int16 s, t }          (pixels in the skin)
    triangles   num_tris      x { uint16 vertex[3], st[3] }
    frames      num_frames    x {
                    float scale[3]
                    float translate[3]
                    char  name[16]
                    num_vertices x { uint16 x, y, z }
                }

    position = coordinate * scale + translate

The only way to tell an HQMD2 from a standard MD2 is the header's framesize:
40 + 6 * num_vertices for HQMD2, 40 + 4 * num_vertices for MD2.

Conventions observed in the game's models (and reproduced by write()):
  * Each frame's bounding box always includes the origin, so translate is
    min(0, minimum) and scale is (max(0, maximum) - translate) / 65535.
  * Triangles are wound clockwise (the MD2 convention; Blender is
    counter-clockwise).
  * t is measured from the top of the skin.
  * There are no GL commands (num_glcmds = 0).

Command line
------------
    python hqmd2.py info  MODEL.MD2
    python hqmd2.py check MODEL.MD2 [...]           read/write round trip test
    python hqmd2.py convert IN.MD2 OUT.MD2          MD2 or HQMD2 -> HQMD2
    python hqmd2.py obj  MODEL.MD2 OUT.OBJ [--frame N]
"""

import struct
import sys

MD2_IDENT = 844121161  # "IDP2"
MD2_VERSION = 8
HEADER = struct.Struct("<17i")
FRAME_HEADER_SIZE = 40
HQ_MAX = 65535


class Frame:
    """One animation frame.

    `vertices` holds decoded float positions. `raw` keeps the quantized data
    read from a file (scale, translate, coordinates) so an unmodified frame is
    written back bit for bit; it is cleared whenever `vertices` is replaced.
    """

    def __init__(self, name, vertices, raw=None):
        self.name = name
        self.vertices = vertices
        self.raw = raw


class Model:
    def __init__(self):
        self.skin_width = 256
        self.skin_height = 256
        self.skins = []        # list of bytes (64) or str
        self.texcoords = []    # list of (s, t) ints
        self.triangles = []    # list of ((v0, v1, v2), (st0, st1, st2)), clockwise
        self.frames = []       # list of Frame
        self.hq = True         # format the model was read from

    @property
    def num_vertices(self):
        return len(self.frames[0].vertices) if self.frames else 0


def _cstr(raw):
    return raw.split(b"\0", 1)[0].decode("latin-1")


def read(path):
    with open(path, "rb") as f:
        data = f.read()

    if len(data) < HEADER.size:
        raise ValueError("%s: file too small" % path)

    (ident, version, skin_w, skin_h, frame_size, num_skins, num_verts, num_st,
     num_tris, _num_glcmds, num_frames, ofs_skins, ofs_st, ofs_tris, ofs_frames,
     _ofs_glcmds, _ofs_end) = HEADER.unpack_from(data, 0)

    if ident != MD2_IDENT or version != MD2_VERSION:
        raise ValueError("%s: not an MD2 file (bad ident or version)" % path)

    if frame_size == FRAME_HEADER_SIZE + 6 * num_verts:
        hq = True
    elif frame_size == FRAME_HEADER_SIZE + 4 * num_verts:
        hq = False
    else:
        raise ValueError("%s: frame size %d matches neither MD2 nor HQMD2 for %d vertices"
                         % (path, frame_size, num_verts))

    if ofs_frames + num_frames * frame_size > len(data):
        raise ValueError("%s: file is truncated (%d bytes, frames need %d)"
                         % (path, len(data), ofs_frames + num_frames * frame_size))

    m = Model()
    m.hq = hq
    m.skin_width, m.skin_height = skin_w, skin_h
    m.skins = [data[ofs_skins + 64 * i: ofs_skins + 64 * (i + 1)] for i in range(num_skins)]
    st = struct.unpack_from("<%dh" % (2 * num_st), data, ofs_st)
    m.texcoords = [(st[2 * i], st[2 * i + 1]) for i in range(num_st)]
    tris = struct.unpack_from("<%dH" % (6 * num_tris), data, ofs_tris)
    m.triangles = [(tuple(tris[6 * i:6 * i + 3]), tuple(tris[6 * i + 3:6 * i + 6]))
                   for i in range(num_tris)]

    for i in range(num_frames):
        o = ofs_frames + i * frame_size
        scale = struct.unpack_from("<3f", data, o)
        translate = struct.unpack_from("<3f", data, o + 12)
        name = _cstr(data[o + 24:o + 40])
        if hq:
            c = struct.unpack_from("<%dH" % (3 * num_verts), data, o + 40)
        else:
            b = data[o + 40:o + 40 + 4 * num_verts]
            c = [b[4 * v + k] for v in range(num_verts) for k in range(3)]
        verts = [tuple(c[3 * v + k] * scale[k] + translate[k] for k in range(3))
                 for v in range(num_verts)]
        raw = (scale, translate, tuple(c), data[o + 24:o + 40]) if hq else None
        m.frames.append(Frame(name, verts, raw))

    return m


def quantize(vertices):
    """Return (scale, translate, coords) for a frame, using the game's convention
    of a bounding box that includes the origin."""
    scale, translate = [], []
    for k in range(3):
        lo = min(0.0, min(v[k] for v in vertices))
        hi = max(0.0, max(v[k] for v in vertices))
        s = (hi - lo) / HQ_MAX
        # Round-trip through float32 so encoding uses the values the game reads
        s = struct.unpack("<f", struct.pack("<f", s))[0]
        lo = struct.unpack("<f", struct.pack("<f", lo))[0]
        scale.append(s)
        translate.append(lo)
    coords = []
    for v in vertices:
        for k in range(3):
            q = round((v[k] - translate[k]) / scale[k]) if scale[k] else 0
            coords.append(min(HQ_MAX, max(0, q)))
    return tuple(scale), tuple(translate), tuple(coords)


def _skin_bytes(skin):
    if isinstance(skin, bytes):
        return skin[:64].ljust(64, b"\0")
    return skin.encode("latin-1")[:63].ljust(64, b"\0")


def _name_bytes(name):
    return name.encode("latin-1")[:15].ljust(16, b"\0")


def write(path, m):
    """Write `m` as an HQMD2 file."""
    if not m.frames:
        raise ValueError("model has no frames")
    num_verts = m.num_vertices
    for i, fr in enumerate(m.frames):
        if len(fr.vertices) != num_verts:
            raise ValueError("frame %d has %d vertices, frame 0 has %d"
                             % (i, len(fr.vertices), num_verts))
    if num_verts > 0xFFFF or len(m.texcoords) > 0xFFFF:
        raise ValueError("too many vertices or texture coordinates for MD2 (max 65535)")

    frame_size = FRAME_HEADER_SIZE + 6 * num_verts
    ofs_skins = HEADER.size
    ofs_st = ofs_skins + 64 * len(m.skins)
    ofs_tris = ofs_st + 4 * len(m.texcoords)
    ofs_frames = ofs_tris + 12 * len(m.triangles)
    ofs_end = ofs_frames + frame_size * len(m.frames)

    out = bytearray()
    out += HEADER.pack(MD2_IDENT, MD2_VERSION, m.skin_width, m.skin_height, frame_size,
                       len(m.skins), num_verts, len(m.texcoords), len(m.triangles),
                       0, len(m.frames), ofs_skins, ofs_st, ofs_tris, ofs_frames,
                       ofs_end, ofs_end)
    for skin in m.skins:
        out += _skin_bytes(skin)
    for s, t in m.texcoords:
        out += struct.pack("<2h", s, t)
    for v, st in m.triangles:
        out += struct.pack("<6H", *(tuple(v) + tuple(st)))
    for fr in m.frames:
        if fr.raw is not None:
            scale, translate, coords, name = fr.raw
        else:
            scale, translate, coords = quantize(fr.vertices)
            name = _name_bytes(fr.name)
        out += struct.pack("<3f", *scale) + struct.pack("<3f", *translate) + name
        out += struct.pack("<%dH" % len(coords), *coords)

    assert len(out) == ofs_end
    with open(path, "wb") as f:
        f.write(out)


def write_obj(path, m, frame=0):
    """Write one frame as Wavefront OBJ (for inspection in any 3D tool)."""
    fr = m.frames[frame]
    with open(path, "w") as f:
        f.write("# %s frame %d (%s)\n" % (path, frame, fr.name))
        for v in fr.vertices:
            f.write("v %.6f %.6f %.6f\n" % v)
        for s, t in m.texcoords:
            f.write("vt %.6f %.6f\n" % (s / m.skin_width, 1.0 - t / m.skin_height))
        for (a, b, c), (sa, sb, sc) in m.triangles:
            # MD2 is clockwise, OBJ is counter-clockwise
            f.write("f %d/%d %d/%d %d/%d\n" % (a + 1, sa + 1, c + 1, sc + 1, b + 1, sb + 1))


def _cmd_info(args):
    m = read(args[0])
    print("format:     %s" % ("HQMD2 (16-bit vertices)" if m.hq else "MD2 (8-bit vertices)"))
    print("skin:       %dx%d %s" % (m.skin_width, m.skin_height,
                                    [_cstr(s) if isinstance(s, bytes) else s for s in m.skins]))
    print("vertices:   %d" % m.num_vertices)
    print("texcoords:  %d" % len(m.texcoords))
    print("triangles:  %d" % len(m.triangles))
    print("frames:     %d" % len(m.frames))
    if m.frames:
        print("first/last: %r / %r" % (m.frames[0].name, m.frames[-1].name))


def _cmd_check(args):
    import os
    import tempfile
    failed = 0
    for path in args:
        try:
            m = read(path)
        except ValueError as e:
            print("SKIP  %s" % e)
            continue
        fd, tmp = tempfile.mkstemp(suffix=".md2")
        os.close(fd)
        try:
            # 1. Unmodified HQMD2 frames must be written back byte for byte
            write(tmp, m)
            same = m.hq and open(tmp, "rb").read() == open(path, "rb").read()
            # 2. Re-quantizing decoded positions must stay within one step
            worst = 0.0
            for fr in m.frames:
                fr.raw = None
            write(tmp, m)
            m2 = read(tmp)
            for f1, f2 in zip(m.frames, m2.frames):
                scale = quantize(f1.vertices)[0]
                for a, b in zip(f1.vertices, f2.vertices):
                    for k in range(3):
                        if scale[k]:
                            worst = max(worst, abs(a[k] - b[k]) / scale[k])
            ok = (same or not m.hq) and worst <= 0.5 + 1e-3
            failed += not ok
            print("%s  %s  %s  byte-identical=%s  max error=%.3f steps"
                  % ("OK  " if ok else "FAIL", "HQ " if m.hq else "STD", path,
                     same if m.hq else "n/a", worst))
        finally:
            os.remove(tmp)
    return 1 if failed else 0


def _cmd_convert(args):
    m = read(args[0])
    write(args[1], m)
    print("wrote %s (%d frames, %d vertices)" % (args[1], len(m.frames), m.num_vertices))


def _cmd_obj(args):
    frame = 0
    if "--frame" in args:
        i = args.index("--frame")
        frame = int(args[i + 1])
        args = args[:i] + args[i + 2:]
    m = read(args[0])
    write_obj(args[1], m, frame)
    print("wrote %s (frame %d of %d)" % (args[1], frame, len(m.frames)))


def main(argv):
    commands = {"info": (_cmd_info, 1), "check": (_cmd_check, 1),
                "convert": (_cmd_convert, 2), "obj": (_cmd_obj, 2)}
    if len(argv) < 2 or argv[1] not in commands or len(argv) - 2 < commands[argv[1]][1]:
        print(__doc__.split("Command line\n------------\n", 1)[1].rstrip())
        return 2
    return commands[argv[1]][0](argv[2:]) or 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
