# spiralizer
Generate spiral (aka vase-mode, aka spiralize outer contour) g-code for smooth printing.

*Attention*: This is alpha level software that has not been extensively tested. It might put your house on fire. No warrenty is given. Only use if you know exactly what the generated g-code does.

## Credit
This software was inspired and partially copied from Alessandro Zomparelli's [gcode-exporter](https://github.com/alessandro-zomparelli/gcode-exporter) and Heinz Löpmeier's [nozzleboss](https://github.com/Heinz-Loepmeier/nozzleboss).

## Usage
0. Install the add-on like you install a blender add-on, either by ziping up the content of the repo and using this file in the installation dialog or by adding a directory with `addons/spiralizer` to custom script paths.
1. Generate a mesh from scratch that will produce one closed edge loop when cut horizontally (eg. Spheres, Cubes, etc). Results of the subsurface division modifier are not supported as it's not trivial to walk their the edge loops generated when being cut with a plane.
2. Set up printer parameters like feed rates and extrusion height and width. Select "Mesh" as toolpath type.
3. Generate slices by selecting your prepared model in object mode and pressing "Slice".
4. Select generated slice object and press "Spiralize" to generate a spiral path object in the "Results" collection.
5. Create two text objects in scripting layout. One start and one end g-code. Select them in Start and End-gcode fields. Make sure that the start g-code begins in absolute E-axis mode.
6. Move the spiral in edit mode to where you want to have it on your build plate.
7. Select the spiral object and press "Export Gcode" button. This generates your g-code and puts it in the selected directory.
8. *Important*: Double check the generated g-code before printing.
9. Print and enjoy!

## TODO
* Control temperature from UI
* Color changes
* Print from from blender
* Automatic subdivision
* Modulate flow rate by painting
* Modulate speed by painting (maybe)
* Support several objects on one plate
* Export properly in nozzleboss quad-strip and gcode-exporter curve format.