import bpy
import math

def slice(context, dz):
    """Cuts a mesh in slices of dz height"""
    ob = context.object
    original_name = ob.name
    original_ob = bpy.data.objects[original_name]
    
    # Get extent in Z direction
    z_min = math.inf
    z_max = -math.inf
    for v in original_ob.data.vertices:
        v_world = original_ob.matrix_world @ v.co
        if v_world.z > z_max:
            z_max = v_world.z
        if v_world.z < z_min:
            z_min = v_world.z

    N = math.ceil((z_max - z_min) / dz)
    
    # Prepare empty mesh to put result vertices
    mesh_data = bpy.data.meshes.new(name="spiralizer_result")
    result_ob = bpy.data.objects.new(name="spiralizer_result", object_data=mesh_data)
    result_ob.data['spiralizer_object_type'] = 'SLICES'
    result_ob.data['spiralizer_slice_count'] = N
    
    # prerequisit for selection
    context.view_layer.active_layer_collection.collection.objects.link(result_ob)    

    # progress display
    wm = bpy.context.window_manager
    wm.progress_begin(0, N)
    
    for i in range(N):
        print(f"Slicing {i}/{N}")
        wm.progress_update(i)
        
        # Select original object
        for o in bpy.context.scene.collection.objects:
            o.select_set(False)
        original_ob.select_set(True)
        context.view_layer.objects.active = original_ob

        # Create working copy of object
        if bpy.ops.object.duplicate.poll():
            bpy.ops.object.duplicate()    
        context.object.name = 'slicer_working_copy'
        working_copy_ob = bpy.data.objects['slicer_working_copy']
    
        # Go into edit mode
        if bpy.ops.object.mode_set.poll():
            bpy.ops.object.mode_set(mode='EDIT')

        # Bisect to keep only one slice of slicer_working_copy    
        if bpy.ops.mesh.bisect.poll():
            z = z_min + i*dz
            bpy.ops.mesh.bisect(plane_co=(0, 0, z), plane_no=(0, 0, 1), 
                                use_fill=True, clear_inner=True, clear_outer=True)
        
        if bpy.ops.object.mode_set.poll():
            bpy.ops.object.mode_set(mode='OBJECT')
        
        # Needs to be done in object mode    
        # create slice_idx attr and set to current slice index
        mesh = working_copy_ob.data
        slice_idx_attr = mesh.attributes.new(name="slice_idx", type="INT", domain="POINT")
        attr_values = [i for idx in range(len(mesh.vertices))]
        slice_idx_attr.data.foreach_set("value", attr_values)    

        # Select working copy and result
        working_copy_ob.select_set(True)
        result_ob.select_set(True)
        context.view_layer.objects.active = result_ob
    
        # Join working copy data into result
        if bpy.ops.object.join.poll():
            bpy.ops.object.join()

    wm.progress_end()

class SliceOperator(bpy.types.Operator):
    """Slices the selected model along the z-axis"""
    bl_idname = "spiralizer.slice"
    bl_label = "Slice object"

    @classmethod
    def poll(cls, context):
        return context.object is not None and context.mode in {'OBJECT'} and context.active_object.data.get('spiralizer_object_type', None) == None
    
#    def invoke(self, context, event):
#        return context.window_manager.invoke_props_dialog(self)
    
    def execute(self, context):
        props = context.scene.spiralizer_settings
        slice(context, props.extrusion_height)
        return {'FINISHED'}
