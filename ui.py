import bpy

class spiralizer_settings(bpy.types.PropertyGroup):
    extrusion_height : bpy.props.FloatProperty(name="Extrusion height",
                                               default=0.1,
                                               soft_min=0.01, soft_max=0.5)
    extrusion_width : bpy.props.FloatProperty(name="Extrusion width",
                                              default=0.1,
                                              soft_min=0.2, soft_max=1.1)
    rotation_direction : bpy.props.EnumProperty(name="Rotation direction",
                                                items=(('CW', 'Clockwise', ""),
                                                       ('CCW', 'Couter-clockwise', "")))
    toolpath_type : bpy.props.EnumProperty(name="Toolpath type",
                                           items=(('CURVE', 'Curve', ""),
                                                  ('MESH', 'Mesh', ""),
                                                  ('NOZZLEBOSS', 'Nozzleboss Mesh', "")))

class SlicePanel(bpy.types.Panel):
    bl_idname = "OBJECT_PT_spiralizer"
    bl_category = "Spiralizer"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_label = "Spiralizer"
    
    @classmethod
    def poll(cls, context):
        try: return context.object.type in ('MESH')
        except: return False
    
    def draw(self, context):
        props = context.scene.spiralizer_settings
        
        layout = self.layout
        col = layout.column(align=True)
        row1 = col.row()
        row1.prop(props, 'extrusion_height')

        row12 = col.row()
        row1.prop(props, 'extrusion_width')
        
        row2 = col.row()
        row2.prop(props, 'rotation_direction')

        row2 = col.row()
        row2.prop(props, 'toolpath_type')
        
        row2 = col.row()
        row2.operator('spiralizer.slice')
        
        row3 = col.row()
        row3.operator('spiralizer.spiralize')
