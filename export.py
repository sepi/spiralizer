import bpy
import math
import os

def mms_to_mmmin(mms):
    return int(mms*60.0)

ARG_SORT = {
    'F': 1,
    'X': 2,
    'Y': 3,
    'Z': 4,
    'E': 5,
}
def code(opcode, **kwargs):
    """Generate a g-code line"""
    if "co" in kwargs:
        kwargs["x"] = kwargs["co"].x
        kwargs["y"] = kwargs["co"].y
        kwargs["z"] = kwargs["co"].z
        del kwargs["co"]
    args = sorted(kwargs.items(), key=lambda it: ARG_SORT[it[0].upper()])
    arg_strs = []
    for arg, val in args:
        arg_strs.append(arg.upper() + str(val))
    return " ".join([opcode.upper()] + arg_strs)

def write_code(stream, opcode, **kwargs):
    """Write a g-code line to stream ended by newline"""
    stream.write(code(opcode, **kwargs) + "\n");

def offset_z(co, dz):
    co.z = co.z + dz
    return co
    
def export(context, gcode_directory, start_gcode, end_gcode, travel_feed_rate, extrusion_feed_rate, z_offset):
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
        z0 = co.z
        dz = z_offset - z0
        write_code(export_file, "G0", co=offset_z(co, dz+0.1), f=mms_to_mmmin(travel_feed_rate))
        write_code(export_file, "G1", z=z_offset, f=mms_to_mmmin(extrusion_feed_rate))

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

            # Write that line  F{mms_to_mmmin(extrusion_feed_rate)}
            write_code(export_file, "G1", co=offset_z(co, dz), e=e)

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
                      props.travel_feed_rate, props.extrusion_feed_rate, props.z_offset)
        self.report({'INFO'}, f"Successfully wrote g-code to {path}.")
        return {'FINISHED'}
