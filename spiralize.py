import bpy
import bmesh
import math
import mathutils
import os
from itertools import pairwise

def get_slice_idx(me, idx):
    return me.attributes['slice_idx'].data[idx].value

def get_layer_verts(me, bm, layer_idx):
    "Returns all verts in bmesh bm belonging to layer layer_idx"
    return [v for v in bm.verts if get_slice_idx(me, v.index) == layer_idx]

def find_closest_v(kd, layer_idxs, v):
    "Find vert in layer closes to v"
    co, idx, dist =  kd.find(v.co, filter = lambda v_idx: v_idx in layer_idxs)
    return co, idx

def next_ev(at_e, at_v):
    """
    Return next edge (next_e) and vert (next_v) given current edge and vert. Vert lags behind edge.
    ( at_v ) ----->---- at_e ----->----- ( next_v ) ------>----- next_e ----->----- ( ... )
    """
    edges = at_v.link_edges
    if len(edges) == 2:
        if edges[0] != at_e:
            edge = edges[0]
        else:
            edge = edges[1]
        return [edge, edge.other_vert(at_v)]
    else:
        return [None, at_v]

def find_edge_in_same_direction(co0, v1):
    "Find edge starting at v1 going in direction v0->v1"
    e1 = v1.link_edges[0]
    continue_to_1 = e1.other_vert(v1)
    e2 = v1.link_edges[1]
    continue_to_2 = e2.other_vert(v1)

    to_1 = (continue_to_1.co - co0).length
    to_2 = (continue_to_2.co - co0).length

    if to_1 < to_2:
        return e1
    else: 
        return e2
    
def polygon_direction(v_0, e_idx):
    """
    Determine if a polygon is clockwise (>0) or counter-clockwise (<0) when following v_0.link_edges[e_idx].
    https://stackoverflow.com/questions/1165647/how-to-determine-if-a-list-of-polygon-points-are-in-clockwise-order
    """
    s = 0
    v = v_0
    v_next = v_0.link_edges[e_idx].other_vert(v)
    while True:
        s = s + (v_next.co.x - v.co.x) * (v_next.co.y - v.co.y)
        v_next = v_next.link_edges[e_idx].other_vert(v_next)
        v = v_next

        if v == v_0:
            return s

def spiralize(context, rotation_direction, default_extrusion_height, default_extrusion_width, toolpath_type):
    print("Spiralize start")
    
    # Get mesh from object
    obj_orig = context.object
    depsgraph = context.evaluated_depsgraph_get()
    obj = obj_orig.evaluated_get(depsgraph) # eval in order to make geometry nodes happen

    me = obj.data

    # Construct a BMesh, used for querying neighboring vertices and edges
    bm = bmesh.new()
    bm.from_mesh(me)
    bm.verts.ensure_lookup_table()

    # Build a kd-tree for finding close vertices
    # This is used to find the closest vertex layer on top of current layer
    kd = mathutils.kdtree.KDTree(len(me.vertices))
    for i, v in enumerate(bm.verts):
        kd.insert(v.co, i)
    kd.balance()

    # Initialize variables for layer iterations
    layer_0 = get_layer_verts(me, bm, 0)
    v_0 = layer_0[0]

    # determine edge to follow for wanted direction
    wanted_rotation_direction = 1 if rotation_direction == 'CW' else -1
    print("Rotating in direction 1=cw, -1=ccw: ", wanted_rotation_direction)
    try:
        rot_dir0 = polygon_direction(v_0, 0)
        if rot_dir0 * wanted_rotation_direction > 0:
            wanted_edge_idx = 0
        else:
            wanted_edge_idx = 1
        e_0 = v_0.link_edges[wanted_edge_idx]
    except IndexError: # happens when layer is a single vertex for example
        e_0 = None

    layer_1 = get_layer_verts(me, bm, 1)

    # Work
    interp_vs = [] # interpolated vertices
    interp_es = [] # interpolated edges
    extrusion_heights = []
    extrusion_widths = []

    v_start_layer = v_0 # start with some random vertex in layer 0
    prev_interp_co = v_0.co # initialize previous interpolation coordinate to v_0.co
    e = e_0 # start in previously determined direction
    vert_idx = 0
    layer_idx = 0
    ramp_mode = 'FLAT'
    extrusion_height = default_extrusion_height
    extrusion_width = default_extrusion_width

    # Count layers
    layer_idx_max = 0
    while True:
        vs = get_layer_verts(me, bm, layer_idx_max)
        if len(vs) == 0:
            layer_idx_max = layer_idx_max - 1
            break
        else:
            layer_idx_max = layer_idx_max + 1

    # TODO: Inset by half extrusion_width.
    # TODO: maybe loop until layer_idx_max instead.
    while True:
        cur_layer = get_layer_verts(me, bm, layer_idx)
        next_layer = get_layer_verts(me, bm, layer_idx+1)
        next_layer_idxs = {v.index for v in next_layer}
        verts_in_layer = len(cur_layer)
        higher_v_idx = None # last found v idx in higher layer
        interp_co = None

        # FLAT
        # RAMP_UP
        # SPIRAL
        # ...
        # SPIRAL
        # RAMP_DOWN
        if layer_idx == 0 and ramp_mode == 'FLAT':
            ramp_mode = 'FLAT'
        elif layer_idx == 1 and ramp_mode == 'FLAT':
            ramp_mode = 'RAMP_UP'
        elif ramp_mode == 'RAMP_UP':
            ramp_mode = 'SPIRAL'
        elif layer_idx == layer_idx_max-1 and ramp_mode == 'SPIRAL':
            ramp_mode = 'RAMP_DOWN'
        
        print(f"layer_idx: {layer_idx}, ramp_mode: {ramp_mode}")
        print("verts in layer", verts_in_layer)

        v = v_start_layer # for this layer
        
        for i in range(verts_in_layer):
            alpha = i / (verts_in_layer+0) # 0 at beginning of layer, 1 at end

            # Find point one up
            higher_v_co, higher_v_idx = find_closest_v(kd, next_layer_idxs, v)
            if higher_v_co is None:
                break

            # How to interpolate between this and next layer?
            if ramp_mode == 'FLAT':
                lerp_factor = 1.0 # Use top curve
            elif ramp_mode == 'RAMP_DOWN':
                lerp_factor = 0.0 # Use bottom curve
            else:
                lerp_factor = alpha


            # Toolhead position
            prev_interp_co = interp_co
            interp_co = v.co.lerp(higher_v_co, lerp_factor)
            interp_vs.append((interp_co.x, interp_co.y, interp_co.z))
            interp_es.append((vert_idx, vert_idx+1))

            # Extrusion amount control
            if ramp_mode == 'RAMP_UP':
                extrusion_height = alpha * default_extrusion_height
            elif ramp_mode == 'RAMP_DOWN':
                extrusion_height = (1-alpha) * default_extrusion_height
            else:
                extrusion_height = default_extrusion_height
            extrusion_heights.append(extrusion_height)
            extrusion_widths.append(extrusion_width)

            # Advance to next edge and vertex
            [e, v] = next_ev(e, v)
            vert_idx = vert_idx + 1

        print("starting new layer at idx", higher_v_idx)
        
        try:
            next_layer = get_layer_verts(me, bm, layer_idx+1)
            next_layer_idxs = {v.index for v in next_layer}
            higher_v_co, higher_v_idx = find_closest_v(kd, next_layer_idxs, v_start_layer)
            v_start_layer = bm.verts[higher_v_idx]
            e = find_edge_in_same_direction(prev_interp_co, v_start_layer)
            layer_idx = layer_idx + 1
        except (IndexError, AttributeError):
            break

    # Create the geometry bearing objects: Either a MESH or a CURVE
    result_name = obj.name+'_spiral'
    if toolpath_type == 'MESH':
        new_geo = bpy.data.meshes.new(name=result_name)
        interp_es.pop() # Else there is one too many edges goint to nowhere
        new_geo.from_pydata(interp_vs, interp_es, [])

        # Set custom attributes
        attribute = new_geo.attributes.new(name="extrusion_height", type="FLOAT", domain="POINT")
        attribute.data.foreach_set("value", extrusion_heights)

        attribute = new_geo.attributes.new(name="extrusion_width", type="FLOAT", domain="POINT")
        attribute.data.foreach_set("value", extrusion_widths)

    elif toolpath_type == 'NOZZLEBOSS':
        vs = []
        fs = []

        # Top vertices of strip
        for v in interp_vs:
            vs.append(v)

        # Bottom vertices of strip
        v_count = len(interp_vs)
        for i, v in enumerate(interp_vs):
            v_below = (v[0],
                       v[1],
                       v[2] - extrusion_heights[i])
            vs.append(v_below)


            fs.append((i, i+1, v_count+i+1, v_count+i))
            
        fs.pop()
        new_geo = bpy.data.meshes.new(name=result_name)
        new_geo.validate(verbose=True)
        new_geo.from_pydata(vs, [], fs)

    elif toolpath_type == 'CURVE':
        new_geo = bpy.data.curves.new(name=result_name, type='CURVE')
        new_geo.dimensions = '3D'
        new_geo.twist_mode = 'Z_UP' # used so we can set the up position on curve easily
        new_geo.bevel_depth = 0.5 # This is the radius that vertex radius will be multiplied with to get the curve radius
        sp = new_geo.splines.new(type='POLY')
        sp.points.add(len(interp_vs)-1)
        for i in range(len(interp_vs)):
            p = sp.points[i]
            p.co.x = interp_vs[i][0]
            p.co.y = interp_vs[i][1]
            p.co.z = interp_vs[i][2]
            p.radius = extrusion_heights[i] / 2


    new_obj = bpy.data.objects.new(new_geo.name, new_geo)
    col = bpy.data.collections['Results']
    col.objects.link(new_obj)
    print("done")


class SpiralizeOperator(bpy.types.Operator):
    """Spiralize the selected objects which shall be the result of a slice operation."""
    bl_idname = "spiralizer.spiralize"
    bl_label = "Spiralize object"

    @classmethod
    def poll(cls, context):
        return context.active_object is not None
    
    def execute(self, context):
        props = context.scene.spiralizer_settings
        spiralize(context, props.rotation_direction,
                  props.extrusion_height, props.extrusion_width,
                  props.toolpath_type)
        return {'FINISHED'}

def export(context, gcode_directory, start_gcode, end_gcode):
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
        export_file.write(f"G0 X{co.x} Y{co.y} Z{co.z}\n")

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
            l_in = volume_out / (math.pi * (1.75/2)**2) # length of filament going in

            e = e + l_in
            export_file.write(f"G1 X{co.x} Y{co.y} Z{co.z} E{e}\n")

            l_last = v
            h_last = h
            w_last = w
    
        # Write end gcode
        try:
            for line in bpy.data.texts[start_gcode].lines:
                export_file.write(line.body + '\n')
        except:
            pass
    
    
class GcodeExportOperator(bpy.types.Operator):
    bl_idname = "spiralizer.gcode_export"
    bl_label = "Export Gcode"
    bl_description = ("Export selected mesh")
    bl_options = {'REGISTER', 'UNDO'}
    
    @classmethod
    def poll(cls, context):
        return context.active_object is not None

    def execute(self, context):
        props = context.scene.spiralizer_settings
        export(context, props.gcode_directory, props.start_gcode, props.end_gcode)
        return {'FINISHED'}
