# HQMD2 tools

The game's models (`data/MODELS/**/*.MD2`) use a custom variant of the Quake II MD2
format with 16-bit vertex positions. The original Blender exporter was lost, so these
tools were rebuilt from the engine's loader (`src/md2/md2.c`) and the shipped models.

- `io_scene_hqmd2/`: a Blender add-on that imports and exports HQMD2.
- `io_scene_hqmd2/hqmd2.py`: the file format as a plain Python module. It doesn't need
  Blender and also works as a command line tool.

## Blender add-on

Works with Blender 2.80 and later.

1. Zip the `io_scene_hqmd2` folder, so the zip contains `io_scene_hqmd2/__init__.py`.
2. In Blender, install the zip:
   - Blender 4.2 and later: *Edit > Preferences > Get Extensions*, then *Install from Disk...*
     in the drop-down menu at the top right.
   - Blender 2.80 to 4.1: *Edit > Preferences > Add-ons > Install...*, then enable
     "HQMD2 format (In The Line Of Fire)".

### Exporting

Select one mesh object and use *File > Export > HQMD2 - In The Line Of Fire (.md2)*.
Each frame of the range is exported with every modifier applied (an Armature
modifier, for example), so the animation comes out as it plays in the viewport.

- **Scene Frame Range / Start / End**: which frames to export. File frame 0 is the first
  frame of the range.
- **Apply Object Transform**: bake location, rotation and scale into the vertices.
- **Skin Width / Height**: the texture size used to store texture coordinates. Leave them
  at 0 to use the size of the first image texture in the object's material, or 256 if
  there is none. Every model in the game uses 256x256.

The vertex count has to stay the same in every frame, so avoid modifiers that change
topology during the animation, such as Decimate or Remesh.

### Importing

*File > Import > HQMD2 - In The Line Of Fire (.md2)* loads an HQMD2 file, or a standard
MD2 file. The first frame becomes the mesh, with its UV map. With **Import Animation**
on, each frame becomes a shape key, keyed so file frame N plays at scene frame
Start + N.

Exporting an imported model gives back the same triangles, texture coordinates and
vertex positions, to within the 16-bit precision. That makes it possible to edit the
game's existing models.

## Command line

```
python tools/hqmd2/io_scene_hqmd2/hqmd2.py info  MODEL.MD2
python tools/hqmd2/io_scene_hqmd2/hqmd2.py check MODEL.MD2 [...]
python tools/hqmd2/io_scene_hqmd2/hqmd2.py convert IN.MD2 OUT.MD2
python tools/hqmd2/io_scene_hqmd2/hqmd2.py obj  MODEL.MD2 OUT.OBJ [--frame N]
```

- `info` shows a model's header details.
- `check` reads each file and writes it back, verifying that unmodified frames come
  back byte for byte and that re-quantized frames stay within half a step.
- `convert` writes a standard MD2 (or HQMD2) as HQMD2. For example, `ROBBER/LOD_01.MD2`
  and `LOD_02.MD2` are standard 8-bit MD2 files.
- `obj` writes one frame as a Wavefront OBJ, to view it in any 3D tool.

## File format

HQMD2 is MD2 (`IDP2`, version 8, little-endian) with one change: each frame vertex is
three `uint16` coordinates (6 bytes), with no normal index. The only way to tell it
apart from a standard MD2 is the header's `framesize`: 40 + 6 x `num_vertices`
(standard MD2 uses 40 + 4 x `num_vertices`).

```
header      17 x int32                 same fields as MD2
skins       num_skins x char[64]       not used by the game
texcoords   num_st x { int16 s, t }    pixels; t measured from the top of the skin
triangles   num_tris x { uint16 vertex[3], st[3] }
frames      num_frames x {
                float scale[3], translate[3]
                char  name[16]          not used by the game
                num_vertices x { uint16 x, y, z }
            }

position = coordinate * scale + translate
```

Conventions found in the shipped models, which the exporter follows:

- Each frame's bounding box always includes the origin: `translate = min(0, min)` and
  `scale = (max(0, max) - translate) / 65535`, per axis.
- Triangles are wound clockwise, the MD2 convention. Blender uses counter-clockwise,
  so the add-on swaps the order on import and export.
- There are no GL commands (`num_glcmds = 0`), and no vertex normals.
- Positions are written in Blender's coordinate system, unchanged, as the common Blender
  MD2 exporters do. Whatever axes the original exporter used, a model imported from
  the game and exported again comes back in the same space.

The back-face culling precomputation for the first-person hands and weapons, mentioned
in the main README, isn't stored in the file. The engine computes it when it loads
those models with `DCE_LoadHQMD2Clip()`. Any exported model works with it.

The original exporter also wrote some details that the game ignores: duplicate
texture coordinates, the skin name `SkinBitMap:::...`, and `FRAME 000......` as every
frame's name. This add-on writes only the texture coordinates that are actually used,
the image name, and `frame000`, `frame001`, and so on.

Four files in `data/MODELS` can't be read, because their `framesize` matches neither
format: `BLOOD/BLOOD.MD2`, `ENEMY/HK_USP.MD2`, `ROBBER/CLOWN_HK_USP.MD2` and
`ROBBER/LOD_00.MD2`. The game doesn't load any of them.
