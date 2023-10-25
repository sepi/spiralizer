import bpy
import math
import os

def mms_to_mmmin(mms):
    return mms*60.0
    
def export(context, gcode_directory, start_gcode, end_gcode, travel_feed_rate, extrusion_feed_rate):
    if gcode_directory == '':
        directory = '//' + os.path.splitext(bpy.path.basename(bpy.context.blend_data.filepath))[0]
    else:
        directory = gcode_directory
    if '.gcode' not in directory: directory += '.gcode'
    path = bpy.path.abspath(directory)
    with open(path, 'w') as export_file:
        # Write start gcode
        try:
            for line in bpy.data.texts[start_gcode].lines:
                export_file.write(line.body + '\n')
        except:
            pass

        # Get mesh from object
        obj_orig = context.object
        depsgraph = context.evaluated_depsgraph_get()
        obj = obj_orig.evaluated_get(depsgraph) # eval in order to make geometry nodes happen
        me = obj.data

        # Go to first point
        co = me.vertices[0].co
        export_file.write(f"G0 X{co.x} Y{co.y} Z{co.z} F{mms_to_mmmin(travel_feed_rate)}\n")

        # Init export loop
        v_last = me.vertices[0]
        h_last = me.attributes['extrusion_height'].data[0].value
        w_last = me.attributes['extrusion_width'].data[0].value
        e = 0 # Accumulate extrusion coordinate
        for i in range(1, len(me.vertices)):
            v = me.vertices[i]
            co = v.co

            # Extrusion params
            h = me.attributes['extrusion_height'].data[i].value
            w = me.attributes['extrusion_width'].data[i].value
            l_out = (v.co - v_last.co).length # length of material going out
            volume_out = l_out * h * w # volume going out
            l_in = volume_out / (math.pi * (1.75/2)**2) # length of filamgent going in
            e = e + l_in

            # Write that line
            export_file.write(f"G1 X{co.x} Y{co.y} Z{co.z} E{e} F{mms_to_mmmin(extrusion_feed_rate)}\n")

            l_last = v
            h_last = h
            w_last = w
            v_last = v
    
        # Write end gcode
        try:
            for line in bpy.data.texts[start_gcode].lines:
                export_file.write(line.body + '\n')
        except:
            pass
    return path
    
class GcodeExportOperator(bpy.types.Operator):
    bl_idname = "spiralizer.gcode_export"
    bl_label = "Export Gcode"
    bl_description = ("Export selected mesh")
    bl_options = {'REGISTER', 'UNDO'}
    
    @classmethod
    def poll(cls, context):
        return context.object is not None and context.mode in {'OBJECT'} and context.active_object.data.get('spiralizer_object_type', None) == 'SPIRAL'

    def execute(self, context):
        props = context.scene.spiralizer_settings
        path = export(context, props.gcode_directory, props.start_gcode, props.end_gcode,
                      props.travel_feed_rate, props.extrusion_feed_rate)
        self.report({'INFO'}, f"Successfully wrote g-code to {path}.")
        return {'FINISHED'}
