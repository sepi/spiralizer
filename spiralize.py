import bpy
import bmesh
import mathutils

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

def spiralize(context, rotation_direction, default_extrusion_height, default_extrusion_width, toolpath_type, filament_change_layers):
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
    read_layer_idx = 1
    spiral_turn_idx = 0
    v_start_layer = get_layer_verts(me, bm, read_layer_idx)[0] # random vertex on starting layer

    # determine edge to follow for wanted direction
    # wanted_rotation_direction = 1 if rotation_direction == 'CW' else -1
    # print("Rotating in direction 1=cw, -1=ccw: ", wanted_rotation_direction)
    # try:
    #     rot_dir0 = polygon_direction(v_start_layer, 0)
    #     if rot_dir0 * wanted_rotation_direction > 0:
    #         wanted_edge_idx = 0
    #     else:
    #         wanted_edge_idx = 1
    #     e_0 = v_start_layer.link_edges[wanted_edge_idx]
    # except IndexError: # happens when layer is a single vertex for example
    #     e_0 = None
    e_0 = v_start_layer.link_edges[0]

    # Work
    interp_vs = [] # interpolated vertices
    interp_es = [] # interpolated edges
    extrusion_heights = []
    extrusion_widths = []

    interp_co = v_start_layer.co
    e = e_0 # start in previously determined direction
    vert_idx = 0
    read_layer_idx = 1
    spiral_turn_idx = 0
    ramp_mode = None
    thickness_mode = None
    print_phase = None
    print_subphase = None
    read_layer_idx_delta = None
    extrusion_height = default_extrusion_height
    extrusion_width = default_extrusion_width

    # Count layers
    read_layer_count = obj.data['spiralizer_slice_count']

    # Progress bar
    wm = context.window_manager
    wm.progress_begin(0, read_layer_count)
            
    # TODO: Inset by half extrusion_width.
    # TODO: maybe loop until read_layer_count instead.
    while True:
        # print_phase  print_subphase
        # ---------------------------
        # BOTTOM       FLAT
        # BOTTOM       RAMP_UP
        # SPIRAL       SPIRAL
        # ...
        # SPIRAL       SPIRAL
        # FILAMENT_CH. RAMP_DOWN
        # FILAMENT_CH. RAMP_UP
        # SPIRAL       SPIRAL
        # ...
        # SPIRAL       SPIRAL
        # TOP          RAMP_DOWN
        if spiral_turn_idx == 0:
            print_phase = 'BOTTOM'
            print_subphase = 'FLAT'
            read_layer_idx_delta = 0
        elif print_phase == 'BOTTOM' and print_subphase == 'FLAT':
            print_subphase = 'RAMP_UP'
            read_layer_idx_delta = 1
        elif print_phase == 'BOTTOM' and print_subphase == 'RAMP_UP':
            print_phase = 'SPIRAL'
            print_subphase = 'SPIRAL'
            read_layer_idx_delta = 1
        elif read_layer_idx in filament_change_layers and ramp_mode == 'SPIRAL':
            print_phase = 'FILAMENT_CHANGE'
            print_subphase = 'RAMP_DOWN'
            read_layer_idx_delta = 0
        elif print_phase == 'FILAMENT_CHANGE' and print_subphase == 'RAMP_DOWN':
            print_subphase = 'RAMP_UP'
            read_layer_idx_delta = 1
        elif print_phase == 'FILAMENT_CHANGE' and print_subphase == 'RAMP_UP':
            print_phase = 'SPIRAL'
            print_subphase = 'SPIRAL'
            read_layer_idx_delta = 1
        elif read_layer_idx == read_layer_count-1 and read_layer_idx_delta == 1:
            print_phase = 'TOP'
            print_subphase = 'RAMP_DOWN'
            read_layer_idx_delta = 0
        elif read_layer_idx == read_layer_count-1 and read_layer_idx_delta == 0:
            break
            
        # Determine process params
        if print_subphase == 'FLAT':
            ramp_mode = 'FLAT'
            thickness_mode = 'CONSTANT'
        elif print_subphase == 'RAMP_UP':
            ramp_mode = 'SPIRAL'
            thickness_mode = 'UP'
        elif print_subphase == 'RAMP_DOWN':
            ramp_mode = 'FLAT'
            thickness_mode = 'DOWN'
        elif print_subphase == 'SPIRAL':
            ramp_mode = 'SPIRAL'
            thickness_mode = 'CONSTANT'
        else:
            raise RuntimeError("Bug: Unknown subphase")

        cur_layer = get_layer_verts(me, bm, read_layer_idx)
        next_layer = get_layer_verts(me, bm, read_layer_idx+read_layer_idx_delta)
        next_layer_idxs = {v.index for v in next_layer}
        verts_in_layer = len(cur_layer)

        print(f"read_layer_idx: {read_layer_idx}, spiral_turn_idx: {spiral_turn_idx}")
        print(f"print_phase: {print_phase}, print_subphase: {print_subphase}")
        print(f"ramp_mode: {ramp_mode}, thick._mode: {thickness_mode}, rlid: {read_layer_idx_delta}")
        print("verts in layer", verts_in_layer)

        v = v_start_layer # for this layer
        e = find_edge_in_same_direction(interp_co, v_start_layer)
            
        for i in range(verts_in_layer):
            alpha = i / (verts_in_layer+0) # 0 at beginning of layer, 1 at end

            # Find corresponding point in next_layer
            higher_v_co, higher_v_idx = find_closest_v(kd, next_layer_idxs, v)
            if higher_v_co is None:
                break

            # How to interpolate between this and next layer?
            if ramp_mode == 'FLAT':
                lerp_factor = 0.0 # Use bottom
            elif ramp_mode == 'SPIRAL':
                lerp_factor = alpha
            else:
                raise RuntimeError("Bug: unknown ramp_mode")

            # Toolhead position
            interp_co = v.co.lerp(higher_v_co, lerp_factor)
            interp_vs.append((interp_co.x, interp_co.y, interp_co.z))
            interp_es.append((vert_idx, vert_idx+1))

            # Extrusion amount control
            if thickness_mode == 'UP':
                extrusion_height = alpha * default_extrusion_height
            elif thickness_mode == 'DOWN':
                extrusion_height = (1-alpha) * default_extrusion_height
            elif thickness_mode == 'CONSTANT':
                extrusion_height = default_extrusion_height
            else:
                raise RuntimeError("Bug: unknown thickness_mode")
                
            extrusion_heights.append(extrusion_height)
            extrusion_widths.append(extrusion_width)

            # Advance to next edge and vertex
            [e, v] = next_ev(e, v)
            vert_idx = vert_idx + 1

        print("starting new layer at idx", higher_v_idx)
        wm.progress_update(read_layer_idx)

        # Progress to next layer
        try:
            # Find the corresponding v on next_layer to use as new start
            _, higher_v_idx = find_closest_v(kd, next_layer_idxs, v_start_layer)
            v_start_layer = bm.verts[higher_v_idx] # vertex where we start to iterate

            spiral_turn_idx = spiral_turn_idx + 1
            read_layer_idx = read_layer_idx + read_layer_idx_delta

        except (IndexError, AttributeError):
            break

    wm.progress_end()

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
    new_obj.data['spiralizer_object_type'] = 'SPIRAL'
    col = bpy.data.collections['Results']
    col.objects.link(new_obj)
    print("done")


class SpiralizeOperator(bpy.types.Operator):
    """Spiralize the selected objects which shall be the result of a slice operation."""
    bl_idname = "spiralizer.spiralize"
    bl_label = "Spiralize object"

    @classmethod
    def poll(cls, context):
        return context.object is not None and context.mode in {'OBJECT'} and context.active_object.data.get('spiralizer_object_type', None) == 'SLICES'
    
    def execute(self, context):
        props = context.scene.spiralizer_settings
        filament_change_layers = []
        for fcl in props.filament_change_layers.split(","):
            try:
                filament_change_layers.append(int(fcl.strip()))
            except ValueError:
                pass
            
        spiralize(context, props.rotation_direction,
                  props.extrusion_height, props.extrusion_width,
                  props.toolpath_type, filament_change_layers)
        return {'FINISHED'}

