import bpy

class spiralizer_settings(bpy.types.PropertyGroup):
    extrusion_height : bpy.props.FloatProperty(name="Extrusion height",
                                               default=0.1,
                                               soft_min=0.01, soft_max=0.5)
    extrusion_width : bpy.props.FloatProperty(name="Extrusion width",
                                              default=0.1,
                                              soft_min=0.2, soft_max=1.1)

    extrusion_feed_rate_black: bpy.props.IntProperty(name="Feed rate black (mm/s)",
                                                     default=10,
                                                     soft_min=5, soft_max=200)

    extrusion_feed_rate_white: bpy.props.IntProperty(name="Feed rate white [default.] (mm/s)",
                                                     default=40,
                                                     soft_min=5, soft_max=200)

    extrusion_feed_rate_map: bpy.props.StringProperty(
        name="Feed rate weightmap - grayscale of vertex color gets mapped feedrate black and white speeds",
        default="Feedrate"
    )
    
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
        row = col.row()
        row.prop(props, 'extrusion_height')
        row.prop(props, 'extrusion_width')

        row = col.row()
        row.prop(props, 'extrusion_feed_rate_white')

        row = col.row()
        row.prop(props, 'extrusion_feed_rate_black')

        if hasattr(context.active_object, 'data'):
            data = context.active_object.data
            row = col.row()
            row.prop_search(props, "extrusion_feed_rate_map", data,
                            "color_attributes", text="Feed rate")

        row = col.row()
        row.prop(props, 'travel_feed_rate')
        
        row = col.row()
        row.prop(props, 'rotation_direction')

        row = col.row()
        row.prop(props, 'toolpath_type')
        
        row = col.row()
        row.operator('spiralizer.slice')

        row = col.row()
        row.prop(props, 'filament_change_layers')
        
        row = col.row()
        row.operator('spiralizer.spiralize')

        col.separator()
        col.label(text='Export', icon='TEXT')
        col.prop_search(props, 'start_gcode', bpy.data, 'texts')
        col.prop_search(props, 'end_gcode', bpy.data, 'texts')
        col.prop_search(props, 'filament_change_gcode', bpy.data, 'texts')
        col.prop(props, 'gcode_directory')
        col.prop(props, 'z_offset')
        
        row = col.row(align=True)
        row.scale_y = 2.0
        row.operator('spiralizer.gcode_export')
