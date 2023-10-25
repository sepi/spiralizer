bl_info = {
    "name": "Spiralizer",
    "author": "Raffael Mancini",
    "version": (0, 1),
    "blender": (2, 80, 0),
    "location": "View3D > Tools > Spiralizer",
    "description": "Creates a spiral mesh along a manifold object to be exported as G-Code",
    "category": "Object"
}

import bpy

from . import slice, spiralize, export, ui

classes = [
    slice.SliceOperator,
    spiralize.SpiralizeOperator,
    export.GcodeExportOperator,
    ui.SlicePanel,
    ui.spiralizer_settings
]
    
def register():
    for cls in classes:
        bpy.utils.register_class(cls)
    bpy.types.Scene.spiralizer_settings = bpy.props.PointerProperty(type=ui.spiralizer_settings)
    
def unregister():
    for cls in classes:
        bpy.utils.unregister_class(cls)

if __name__ == "__main__":
    register()
