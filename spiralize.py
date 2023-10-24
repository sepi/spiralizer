import bpy
import bmesh
import math
import mathutils
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

    #cur_layer = layer_0 # verts in current layer
    #next_layer = layer_1 # verts in next layer
    #verts_in_layer = len(layer_1)

    v = v_0 # start with some random vertex in layer 0
    prev_interp_co = v_0.co # initialize previous interpolation coordinate to v_0.co
    e = e_0 # start in previously determined direction
    vert_idx = 0
    layer_idx = 0
    ramp_mode = 'FLAT'
    extrusion_height = default_extrusion_height
    extrusion_width = default_extrusion_width

    layer_idx_max = 0
    while True:
        vs = get_layer_verts(me, bm, layer_idx_max)
        if len(vs) == 0:
            layer_idx_max = layer_idx_max - 1
            break
        else:
            layer_idx_max = layer_idx_max + 1

    # TODO: Inset by half extrusion_width.
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

        for i in range(verts_in_layer+1):
            alpha = i / (verts_in_layer+0) # 0 at beginning of layer, 1 at end
            if ramp_mode == 'FLAT':
                lerp_factor = 1.0 # Use top curve
            elif ramp_mode == 'RAMP_DOWN':
                lerp_factor = 0.0 # Use bottom curve
            else:
                lerp_factor = alpha
            higher_v_co, higher_v_idx = find_closest_v(kd, next_layer_idxs, v)
            if higher_v_co is None:
                break
            prev_interp_co = interp_co
            interp_co = v.co.lerp(higher_v_co, lerp_factor)
            [e, v] = next_ev(e, v)
            interp_vs.append((interp_co.x, interp_co.y, interp_co.z))
            interp_es.append((vert_idx, vert_idx+1))
            if ramp_mode == 'RAMP_UP':
                extrusion_height = alpha * default_extrusion_height
            elif ramp_mode == 'RAMP_DOWN':
                extrusion_height = (1-alpha) * default_extrusion_height
            else:
                extrusion_height = default_extrusion_height
            extrusion_heights.append(extrusion_height)
            extrusion_widths.append(extrusion_width)
            
            vert_idx = vert_idx + 1

        print("starting new layer at idx", higher_v_idx)
        
        try:
            # if first_layer:
            #     first_layer = False
            #     v = v_0
            # else:
            v = bm.verts[higher_v_idx]
            layer_idx = layer_idx + 1
            e = find_edge_in_same_direction(prev_interp_co, v)
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
        es = []
        fs = []

        v0 = interp_vs[0]
        vs.append(v0)
        v_below = (v0[0], v0[1], v0[2] - extrusion_heights[0])
        vs.append(v_below)

        for v_, v_next_ in pairwise(enumerate(interp_vs)):
            i, v = v_
            i_next, v_next = v_next_
            
            # Append two vertices, top and bottom
            vs.append(v_next)
            v_next_below = (v_next[0],
                            v_next[1],
                            v_next[2] - extrusion_heights[i+1])
            vs.append(v_next_below)

            # es.append((ti+1, ti+3))
            # es.append((ti+3, ti+2))
            # es.append((ti+2, ti))
            i = i*2
            i_next = i_next*2
            fs.append((i, i+1, i_next+1, i_next))

            # if i >= 2:
            #     fs.pop()
            #     break

        fs.pop()
        print(vs, es, fs)
        new_geo = bpy.data.meshes.new(name=result_name)
        new_geo.validate(verbose=True)
        new_geo.from_pydata(vs, es, fs)

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
