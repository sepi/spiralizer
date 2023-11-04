import bpy

class spiralizer_settings(bpy.types.PropertyGroup):
    extrusion_height : bpy.props.FloatProperty(name="Extrusion height",
                                               default=0.1,
                                               soft_min=0.01, soft_max=0.5)
    extrusion_width : bpy.props.FloatProperty(name="Extrusion width",
                                              default=0.1,
                                              soft_min=0.2, soft_max=1.1)

    extrusion_feed_rate: bpy.props.IntProperty(name="Extrusion feed rate (mm/s)",
                                               default=20,
                                               soft_min=5, soft_max=200)
    travel_feed_rate : bpy.props.FloatProperty(name="Travel feed rate (mm/s)",
                                               default=100,
                                               soft_min=5, soft_max=200)

    rotation_direction : bpy.props.EnumProperty(name="Rotation direction",
                                                items=(('CW', 'Clockwise', ""),
                                                       ('CCW', 'Couter-clockwise', "")))
    toolpath_type : bpy.props.EnumProperty(name="Toolpath type",
                                           items=(('CURVE', 'Curve', ""),
                                                  ('MESH', 'Mesh', ""),
                                                  ('NOZZLEBOSS', 'Nozzleboss Mesh', "")))

    filament_change_layers : bpy.props.StringProperty(name="Filament change layers",
                                                      default="")

    z_offset : bpy.props.FloatProperty(name="Z-Offset (mm)",
                                       default=0.2,
                                       soft_min=0, soft_max=0.8)

    gcode_directory : bpy.props.StringProperty(
        name="File", default="", subtype='FILE_PATH',
        description = 'Destination directory.\nIf missing, the .blend-file directory will be used'
    )
    start_gcode : bpy.props.StringProperty(
        name="Start g-code", default='',
        description="Text block for starting g-code"
    )
    filament_change_gcode : bpy.props.StringProperty(
        name="Filament ch. g-code", default='',
        description="Text block inserted when filament changed"
    )
    end_gcode : bpy.props.StringProperty(
        name="End g-code", default='',
        description="Text block for end g-code"
    )


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
        row1.prop(props, 'extrusion_width')

        row13 = col.row()
        row13.prop(props, 'extrusion_feed_rate')
        row13.prop(props, 'travel_feed_rate')
        
        row2 = col.row()
        row2.prop(props, 'rotation_direction')

        row2 = col.row()
        row2.prop(props, 'toolpath_type')
        
        row2 = col.row()
        row2.operator('spiralizer.slice')

        row = col.row()
        row.prop(props, 'filament_change_layers')
        
        row3 = col.row()
        row3.operator('spiralizer.spiralize')

        col.separator()
        col.label(text='Export', icon='TEXT')
        col.prop_search(props, 'start_gcode', bpy.data, 'texts')
        col.prop_search(props, 'end_gcode', bpy.data, 'texts')
        col.prop_search(props, 'filament_change_gcode', bpy.data, 'texts')
        col.prop(props, 'gcode_directory')
        col.prop(props, 'z_offset')
        
        row4 = col.row(align=True)
        row4.scale_y = 2.0
        row4.operator('spiralizer.gcode_export')
