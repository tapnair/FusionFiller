import adsk.core
import adsk.fusion
import traceback
import math
import collections

from adsk.fusion import BRepFaces
from .Fusion360Utilities.Fusion360Utilities import AppObjects, combine_feature
from .Fusion360Utilities.Fusion360CommandBase import Fusion360CommandBase


Point = collections.namedtuple("Point", ["x", "y"])


def pointy_hex_corner(center, size, i):
    angle_deg = 60 * i - 30
    angle_rad = math.pi / 180 * angle_deg
    return adsk.core.Point3D.create(center.x + size * math.cos(angle_rad),
                                    center.y + size * math.sin(angle_rad), 0)


# Alternate Feature Method, cut
def hex_sketch(center, input_size, height, thickness):
    # Get the root component of the active design.
    ao = AppObjects()

    gap = thickness / math.sqrt(3)

    size = input_size - gap

    # Create a new sketch on the xy plane.
    sketches = ao.root_comp.sketches
    xy_plane = ao.root_comp.xYConstructionPlane
    sketch = sketches.add(xy_plane)

    # Draw two connected lines.
    lines = sketch.sketchCurves.sketchLines

    start_point = pointy_hex_corner(center, size, 0)
    previous_point = start_point
    first = True

    for corner in range(1, 6):
        new_point = pointy_hex_corner(center, size, corner)
        line = lines.addByTwoPoints(previous_point, new_point)
        if first:
            start_point = line.startSketchPoint
            first = False
        previous_point = line.endSketchPoint

    line = lines.addByTwoPoints(previous_point, start_point)

    # Get the profile defined by the circle.
    prof = sketch.profiles.item(0)

    # Create the extrusion.
    # extrudes = ao.root_comp.features.extrudeFeatures
    # extrude_feature = extrudes.addSimple(prof, height, adsk.fusion.FeatureOperations.CutFeatureOperation)
    # return extrude_feature

    return prof


def hex_extrude(prof, height):

    ao = AppObjects()
    extrude_features = ao.root_comp.features.extrudeFeatures

    # Create an extrusion that goes through all entities
    extrude_input = extrude_features.createInput(prof, adsk.fusion.FeatureOperations.NewBodyFeatureOperation)

    # Create an extent definition of through-all type.
    # extent_all = adsk.fusion.ThroughAllExtentDefinition.create()
    # extrude_input.setOneSideExtent(extent_all, adsk.fusion.ExtentDirections.NegativeExtentDirection)

    extrude_input.setSymmetricExtent(height, False)

    # extrude_input.participantBodies = target_body

    # Create the extrusion
    extrude_feature = extrude_features.add(extrude_input)

    return extrude_feature


def hex_pattern(extrude_collection, x_qty, x_space, y_qty, y_space):

    ao = AppObjects()
    pattern_features = ao.root_comp.features.rectangularPatternFeatures

    x_axis = ao.root_comp.xConstructionAxis
    y_axis = ao.root_comp.yConstructionAxis

    pattern_type = adsk.fusion.PatternDistanceType.SpacingPatternDistanceType

    pattern_input = pattern_features.createInput(extrude_collection, x_axis, x_qty,
                                                 adsk.core.ValueInput.createByReal(x_space), pattern_type)
    pattern_input.directionTwoEntity = y_axis
    pattern_input.distanceTwo = adsk.core.ValueInput.createByReal(y_space * 1.5)
    pattern_input.quantityTwo = y_qty
    pattern_input.isSymmetricInDirectionOne = True
    pattern_input.isSymmetricInDirectionTwo = True

    pattern_feature = ao.root_comp.features.rectangularPatternFeatures.add(pattern_input)

    return pattern_feature


def second_hex_body(size, hex_body, core_body, x_space, y_space):
    ao = AppObjects()

    copy_collection = adsk.core.ObjectCollection.create()
    copy_collection.add(hex_body)

    copy_body_feature = ao.root_comp.features.copyPasteBodies.add(copy_collection)
    hex_body_2 = copy_body_feature.bodies[0]

    move_collection = adsk.core.ObjectCollection.create()
    move_collection.add(hex_body_2)

    transform = adsk.core.Matrix3D.create()
    transform.translation = adsk.core.Vector3D.create(x_space / 2, .75 * y_space, 0)

    move_input = ao.root_comp.features.moveFeatures.createInput(move_collection, transform)
    ao.root_comp.features.moveFeatures.add(move_input)

    return hex_body_2

def create_core_body(input_body, input_shell_thickness):
    ao = AppObjects()

    # Shell Main body
    shell_features = ao.root_comp.features.shellFeatures
    input_collection = adsk.core.ObjectCollection.create()
    input_collection.add(input_body)
    shell_input = shell_features.createInput(input_collection)
    shell_input.insideThickness = input_shell_thickness
    shell_feature = shell_features.add(shell_input)

    # Offset internal faces 0
    shell_faces = shell_feature.faces
    tools = adsk.core.ObjectCollection.create()
    for face in shell_faces:
        tools.add(face)
    distance = adsk.core.ValueInput.createByReal(0)
    offset_features = ao.root_comp.features.offsetFeatures
    offset_input = offset_features.createInput(tools, distance,
                                               adsk.fusion.FeatureOperations.NewBodyFeatureOperation)
    offset_feature = offset_features.add(offset_input)

    # Boundary FIll
    offset_tools = adsk.core.ObjectCollection.create()
    for body in offset_feature.bodies:
        offset_tools.add(body)

    boundary_fills = ao.root_comp.features.boundaryFillFeatures
    boundary_fill_input = boundary_fills.createInput(offset_tools,
                                                     adsk.fusion.FeatureOperations.NewBodyFeatureOperation)
    cell = boundary_fill_input.bRepCells.item(0)
    cell.isSelected = True
    boundary_fill = boundary_fills.add(boundary_fill_input)

    core_body = boundary_fill.bodies[0]
    return core_body


# Class for a Fusion 360 Command
# Place your program logic here
# Delete the line that says "pass" for any method you want to use
class FillerCommand(Fusion360CommandBase):
    # Run whenever a user makes any change to a value or selection in the addin UI
    # Commands in here will be run through the Fusion processor and changes will be reflected in  Fusion graphics area
    def on_preview(self, command: adsk.core.Command, inputs: adsk.core.CommandInputs, args, input_values):
        pass

    # Run after the command is finished.
    # Can be used to launch another command automatically or do other clean up.
    def on_destroy(self, command: adsk.core.Command, inputs: adsk.core.CommandInputs, reason, input_values):
        pass

    # Run when any input is changed.
    # Can be used to check a value and then update the add-in UI accordingly
    def on_input_changed(self, command: adsk.core.Command, inputs: adsk.core.CommandInputs, changed_input,
                         input_values):
        pass

    # Run when the user presses OK
    # This is typically where your main program logic would go
    def on_execute(self, command: adsk.core.Command, inputs: adsk.core.CommandInputs, args, input_values):

        # Get a reference to all relevant application objects in a dictionary
        ao = AppObjects()

        # Get the values from the user input
        input_size = input_values['size_input']
        input_shell_thickness = input_values['shell_input']
        input_rib_thickness = input_values['rib_input']
        all_selections = input_values['selection_input']

        start_body = adsk.fusion.BRepBody.cast(all_selections[0])
        bounding_box = start_body.boundingBox
        start_volume = start_body.volume

        # Create Core Body of input body
        create_core_body(start_body, input_shell_thickness)

        # Define that the extent is a distance extent of 5 cm.
        height = adsk.core.ValueInput.createByReal(10)

        x_space = math.sqrt(3) * input_size
        y_space = 2 * input_size

        extent_vector = bounding_box.maxPoint.asVector()
        extent_vector.subtract(bounding_box.minPoint.asVector())

        x_qty_raw = math.ceil(extent_vector.x / x_space)
        y_qty_raw = math.ceil(extent_vector.y / y_space)
        x_qty = adsk.core.ValueInput.createByReal(x_qty_raw)
        y_qty = adsk.core.ValueInput.createByReal(y_qty_raw)


        # ao.ui.messageBox("Extrudes 1")

        prof_1 = hex_sketch(adsk.core.Point3D.create(0, 0, 0), input_size, height, input_rib_thickness)
        prof_2 = hex_sketch(adsk.core.Point3D.create(x_space / 2, .75 * y_space, 0), input_size, height, input_rib_thickness)

        # extrude_1 = hex_extrude(prof_1, height, [core_body])
        # extrude_2 = hex_extrude(prof_2, height, [core_body])

        extrude_1 = hex_extrude(prof_1, height)
        extrude_2 = hex_extrude(prof_2, height)

        # for x in range(0, x_qty):
        #     for y in range(0, y_qty):
        #
        #         center_1 = adsk.core.Point3D.create(x * x_space, 1.5 * y * y_space, 0)
        #         center_2 = adsk.core.Point3D.create(x_space * (x + .5), 1.5 * y_space * y + .75 * y_space, 0)
        #
        #         prof_1 = hex_sketch(center_1, input_size, height, thickness)
        #         prof_2 = hex_sketch(center_2, input_size, height, thickness)
        #
        #         extrude_1 = hex_extrude(prof_1, height, [core_body])
        #         extrude_2 = hex_extrude(prof_2, height, [core_body])

        extrude_cut_collection = adsk.core.ObjectCollection.create()
        extrude_cut_collection.add(extrude_1.bodies[0])
        extrude_cut_collection.add(extrude_2.bodies[0])

        # ao.ui.messageBox("Pattern 1")

        pattern_feature = hex_pattern(extrude_cut_collection, x_qty, x_space, y_qty, y_space)

        # ao.ui.messageBox("Collection 1")

        hex_tools = adsk.core.ObjectCollection.create()
        hex_tools.add(extrude_1.bodies[0])
        hex_tools.add(extrude_2.bodies[0])

        # for count in range(0, 50):
        #     hex_tools.add(pattern_feature.bodies[count])

        # hex_body = draw_hex(adsk.core.Point3D.create(0, 0, 0), input_size, height, thickness)
        # hex_tools = pattern_hex(input_size, hex_body)
        # hex_tools = pattern_hex(input_size, hex_body, core_body)

        for count in range(ao.design.rootComponent.bRepBodies.count - 200, ao.design.rootComponent.bRepBodies.count):
            hex_tools.add(ao.design.rootComponent.bRepBodies[count])
        # ao.ui.messageBox("Combine 1")

        combine_features = ao.root_comp.features.combineFeatures

        hex_combine_input = combine_features.createInput(core_body, hex_tools)
        hex_combine_input.operation = adsk.fusion.FeatureOperations.CutFeatureOperation
        combine_features.add(hex_combine_input)

        # for body in pattern_feature.bodies:
        #     # Create InterferenceInput
        #     check = adsk.core.ObjectCollection.create()
        #     check.add(body)
        #     check.add(core_body)
        #     interference_input = ao.design.createInterferenceInput(check)
        #     results = ao.design.analyzeInterference(interference_input)
        #
        #     if results.count > 0:
        #         hex_tools = adsk.core.ObjectCollection.create()
        #         hex_tools.add(body)
        #         hex_combine_input = combine_features.createInput(core_body, hex_tools)
        #         hex_combine_input.operation = adsk.fusion.FeatureOperations.CutFeatureOperation
        #         combine_features.add(hex_combine_input)

        # ao.ui.messageBox("Combine 2")
        #
        final_combine_collection = adsk.core.ObjectCollection.create()
        final_combine_collection.add(core_body)
        final_combine_input = combine_features.createInput(the_first_selection, final_combine_collection)
        final_combine_input.operation = adsk.fusion.FeatureOperations.JoinFeatureOperation
        combine_features.add(final_combine_input)


    # Run when the user selects your command icon from the Fusion 360 UI
    # Typically used to create and display a command dialog box
    # The following is a basic sample of a dialog UI
    def on_create(self, command: adsk.core.Command, inputs: adsk.core.CommandInputs):

        ao = AppObjects()
        # ao.ui.messageBox("Test")
        # Create a default value using a string
        default_size = adsk.core.ValueInput.createByString('.5 in')
        default_shell = adsk.core.ValueInput.createByString('.3 in')
        default_rib = adsk.core.ValueInput.createByString('.1 in')
        ao = AppObjects()

        # Create a few inputs in the UI
        inputs.addValueInput('size_input', 'Size (Major Diameter)', ao.units_manager.defaultLengthUnits, default_size)
        inputs.addValueInput('shell_input', 'Shell Thickness (Outer Wall)', ao.units_manager.defaultLengthUnits, default_shell)
        inputs.addValueInput('rib_input', 'Rib Thickness', ao.units_manager.defaultLengthUnits, default_rib)

        # inputs.addBoolValueInput('bool_input', '***Sample***Checked', True)
        # inputs.addStringValueInput('string_input', '***Sample***String Value', 'Default value')
        selection = inputs.addSelectionInput('selection_input', '***Sample***Selection', 'Select Something')
        selection.addSelectionFilter("SolidBodies")
        selection..setSelectionLimits(1, 1)

