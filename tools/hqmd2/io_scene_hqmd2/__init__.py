# In The Line Of Fire - HQMD2 import/export for Blender
#
# This program is free software: you can redistribute it and/or modify it under
# the terms of the GNU General Public License as published by the Free Software
# Foundation, either version 3 of the License, or (at your option) any later
# version.
#
# A replacement for the lost Blender exporter used to make the game's models.
# The file format itself lives in hqmd2.py, which does not depend on Blender.

bl_info = {
    "name": "HQMD2 format (In The Line Of Fire)",
    "description": "Import/export the 16-bit MD2 variant used by the In The Line Of Fire engine",
    "version": (1, 0, 0),
    "blender": (2, 80, 0),
    "location": "File > Import-Export",
    "category": "Import-Export",
}

import os
import struct

import bpy
from bpy.props import BoolProperty, IntProperty, StringProperty
from bpy_extras.io_utils import ExportHelper, ImportHelper
from mathutils import Vector

from . import hqmd2


# ----------------------------------------------------------------------------
# Export
# ----------------------------------------------------------------------------

def _material_image_size(obj):
    """Size of the first image texture used by the object's materials."""
    for slot in obj.material_slots:
        mat = slot.material
        if mat and mat.use_nodes and mat.node_tree:
            for node in mat.node_tree.nodes:
                if node.type == 'TEX_IMAGE' and node.image and node.image.size[0]:
                    return tuple(node.image.size), node.image.name
    return None, None


def _evaluated_frame(context, obj, apply_transform):
    depsgraph = context.evaluated_depsgraph_get()
    obj_eval = obj.evaluated_get(depsgraph)
    me = obj_eval.to_mesh()
    try:
        n = len(me.vertices)
        co = [0.0] * (3 * n)
        me.vertices.foreach_get("co", co)
        if apply_transform:
            mat = obj_eval.matrix_world.copy()
            verts = []
            for i in range(n):
                p = mat @ Vector((co[3 * i], co[3 * i + 1], co[3 * i + 2]))
                verts.append((p.x, p.y, p.z))
        else:
            verts = [(co[3 * i], co[3 * i + 1], co[3 * i + 2]) for i in range(n)]

        me.calc_loop_triangles()
        uv_layer = me.uv_layers.active
        tris = []
        for tri in me.loop_triangles:
            uvs = [tuple(uv_layer.data[l].uv) if uv_layer else (0.0, 0.0) for l in tri.loops]
            tris.append((tuple(tri.vertices), uvs))
        return verts, tris, uv_layer is not None
    finally:
        obj_eval.to_mesh_clear()


class ExportHQMD2(bpy.types.Operator, ExportHelper):
    """Export the active mesh, animated over a frame range, as HQMD2"""
    bl_idname = "export_scene.hqmd2"
    bl_label = "Export HQMD2"
    bl_options = {'PRESET'}

    filename_ext = ".md2"
    filter_glob: StringProperty(default="*.md2;*.MD2", options={'HIDDEN'})

    use_scene_range: BoolProperty(
        name="Scene Frame Range",
        description="Export the scene's frame range instead of the range below",
        default=True)
    frame_start: IntProperty(name="Start Frame", default=1)
    frame_end: IntProperty(name="End Frame", default=1)
    apply_transform: BoolProperty(
        name="Apply Object Transform",
        description="Bake the object's location, rotation and scale into the vertices",
        default=True)
    skin_width: IntProperty(
        name="Skin Width", min=0, max=4096, default=0,
        description="Texture width used for texture coordinates (0 = from material, else 256)")
    skin_height: IntProperty(
        name="Skin Height", min=0, max=4096, default=0,
        description="Texture height used for texture coordinates (0 = from material, else 256)")
    skin_name: StringProperty(
        name="Skin Name", default="",
        description="Skin name stored in the file (the game does not use it). "
                    "Empty = material image name")

    def execute(self, context):
        obj = context.active_object
        if obj is None or obj.type != 'MESH':
            self.report({'ERROR'}, "Select a mesh object to export")
            return {'CANCELLED'}

        scene = context.scene
        if self.use_scene_range:
            start, end = scene.frame_start, scene.frame_end
        else:
            start, end = self.frame_start, self.frame_end
        if end < start:
            self.report({'ERROR'}, "End frame is before start frame")
            return {'CANCELLED'}

        size, image_name = _material_image_size(obj)
        width = self.skin_width or (size[0] if size else 256)
        height = self.skin_height or (size[1] if size else 256)

        model = hqmd2.Model()
        model.skin_width, model.skin_height = width, height
        model.skins = [self.skin_name or image_name or obj.name]

        saved_frame = scene.frame_current
        try:
            for f in range(start, end + 1):
                scene.frame_set(f)
                verts, tris, has_uv = _evaluated_frame(context, obj, self.apply_transform)

                if f == start:
                    if not tris:
                        self.report({'ERROR'}, "The mesh has no faces")
                        return {'CANCELLED'}
                    if not has_uv:
                        self.report({'WARNING'}, "The mesh has no UV map; texture coordinates set to 0")
                    st_index = {}
                    for v, uvs in tris:
                        st = []
                        for u, w in uvs:
                            key = (int(round(u * width)), int(round((1.0 - w) * height)))
                            if key not in st_index:
                                st_index[key] = len(model.texcoords)
                                model.texcoords.append(key)
                            st.append(st_index[key])
                        # Blender is counter-clockwise, MD2 is clockwise
                        model.triangles.append(((v[0], v[2], v[1]), (st[0], st[2], st[1])))
                    num_verts = len(verts)
                elif len(verts) != num_verts:
                    self.report({'ERROR'},
                                "Frame %d has %d vertices but frame %d has %d: the topology must "
                                "not change during the animation (check modifiers)"
                                % (f, len(verts), start, num_verts))
                    return {'CANCELLED'}

                model.frames.append(hqmd2.Frame("frame%03d" % (f - start), verts))
        finally:
            scene.frame_set(saved_frame)

        try:
            hqmd2.write(self.filepath, model)
        except (ValueError, OSError, struct.error) as e:
            self.report({'ERROR'}, str(e))
            return {'CANCELLED'}

        self.report({'INFO'}, "Exported %d frames, %d vertices, %d triangles to %s"
                    % (len(model.frames), num_verts, len(model.triangles),
                       os.path.basename(self.filepath)))
        return {'FINISHED'}


# ----------------------------------------------------------------------------
# Import
# ----------------------------------------------------------------------------

class ImportHQMD2(bpy.types.Operator, ImportHelper):
    """Import an HQMD2 (or standard MD2) model, with its frames as animated shape keys"""
    bl_idname = "import_scene.hqmd2"
    bl_label = "Import HQMD2"
    bl_options = {'PRESET', 'UNDO'}

    filename_ext = ".md2"
    filter_glob: StringProperty(default="*.md2;*.MD2", options={'HIDDEN'})

    import_animation: BoolProperty(
        name="Import Animation",
        description="Create one shape key per frame, keyed so frame N of the file plays "
                    "at scene frame Start + N",
        default=True)
    frame_start: IntProperty(name="Start Frame", default=1)
    set_scene_range: BoolProperty(
        name="Set Scene Frame Range",
        description="Set the scene frame range to the imported animation",
        default=True)

    def execute(self, context):
        try:
            model = hqmd2.read(self.filepath)
        except (ValueError, OSError) as e:
            self.report({'ERROR'}, str(e))
            return {'CANCELLED'}

        name = os.path.splitext(os.path.basename(self.filepath))[0]
        frame0 = model.frames[0].vertices
        # MD2 is clockwise, Blender is counter-clockwise
        faces = [(v[0], v[2], v[1]) for v, _st in model.triangles]

        me = bpy.data.meshes.new(name)
        me.from_pydata(frame0, [], faces)
        uv = me.uv_layers.new(name="UVMap")
        w, h = float(model.skin_width or 256), float(model.skin_height or 256)
        for poly, (_v, st) in zip(me.polygons, model.triangles):
            for loop, si in zip(poly.loop_indices, (st[0], st[2], st[1])):
                s, t = model.texcoords[si]
                uv.data[loop].uv = (s / w, 1.0 - t / h)
        me.validate(clean_customdata=False)
        me.update()

        obj = bpy.data.objects.new(name, me)
        context.collection.objects.link(obj)
        for o in context.selected_objects:
            o.select_set(False)
        obj.select_set(True)
        context.view_layer.objects.active = obj

        if self.import_animation and len(model.frames) > 1:
            obj.shape_key_add(name="Basis", from_mix=False)
            start = self.frame_start
            for i, fr in enumerate(model.frames):
                key = obj.shape_key_add(name="frame%03d" % i, from_mix=False)
                key.data.foreach_set("co", [c for v in fr.vertices for c in v])
                for f, value in ((start + i - 1, 0.0), (start + i, 1.0), (start + i + 1, 0.0)):
                    key.value = value
                    key.keyframe_insert("value", frame=f)
            key_action = me.shape_keys.animation_data.action
            for fc in _fcurves(key_action):
                for kp in fc.keyframe_points:
                    kp.interpolation = 'LINEAR'
            if self.set_scene_range:
                context.scene.frame_start = start
                context.scene.frame_end = start + len(model.frames) - 1
            context.scene.frame_set(start)

        self.report({'INFO'}, "Imported %s: %d frames, %d vertices, %d triangles (%s)"
                    % (name, len(model.frames), model.num_vertices, len(model.triangles),
                       "HQMD2" if model.hq else "MD2"))
        return {'FINISHED'}


def _fcurves(action):
    """F-curves of an action (Blender 4.4+ layered actions keep them in channelbags)."""
    if hasattr(action, "fcurves") and len(action.fcurves):
        return list(action.fcurves)
    curves = []
    for layer in getattr(action, "layers", []):
        for strip in layer.strips:
            for bag in getattr(strip, "channelbags", []):
                curves.extend(bag.fcurves)
    return curves


# ----------------------------------------------------------------------------
# Registration
# ----------------------------------------------------------------------------

def menu_export(self, context):
    self.layout.operator(ExportHQMD2.bl_idname, text="HQMD2 - In The Line Of Fire (.md2)")


def menu_import(self, context):
    self.layout.operator(ImportHQMD2.bl_idname, text="HQMD2 - In The Line Of Fire (.md2)")


classes = (ExportHQMD2, ImportHQMD2)


def register():
    for cls in classes:
        bpy.utils.register_class(cls)
    bpy.types.TOPBAR_MT_file_export.append(menu_export)
    bpy.types.TOPBAR_MT_file_import.append(menu_import)


def unregister():
    bpy.types.TOPBAR_MT_file_import.remove(menu_import)
    bpy.types.TOPBAR_MT_file_export.remove(menu_export)
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)


if __name__ == "__main__":
    register()
