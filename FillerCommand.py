import adsk.core
import adsk.fusion
import traceback
import math
import collections

from adsk.fusion import BRepFaces
from .Fusion360Utilities.Fusion360Utilities import AppObjects, combine_feature
from .Fusion360Utilities.Fusion360CommandBase import Fusion360CommandBase


Point = collections.namedtuple("Point", ["x", "y"])


def start_sketch(z):
    ao = AppObjects()
    # Get construction planes
    planes = ao.root_comp.constructionPlanes
    xy_plane = ao.root_comp.xYConstructionPlane
    plane_input = planes.createInput()
    offset_value = adsk.core.ValueInput.createByReal(z)
    plane_input.setByOffset(xy_plane, offset_value)
    sketch_plane = planes.add(plane_input)

    sketches = ao.root_comp.sketches
    sketch = sketches.add(sketch_plane)

    return sketch


# Alternate Feature Method, cut
def circle_sketch(center, input_size, gap):
    spoke = (input_size / 2) - gap

    sketch = start_sketch(center.z)

    sketch_circles = sketch.sketchCurves.sketchCircles
    circle_point = adsk.core.Point3D.create(center.x, center.y, 0)
    sketch_circles.addByCenterRadius(circle_point, spoke)
    prof = sketch.profiles.item(0)

    return prof


# Defines points of a shape
def pointy_shape_corner(center, size, i, offset, sides):
    angle_deg = (360 / sides) * i - offset
    angle_rad = math.pi / 180 * angle_deg
    return adsk.core.Point3D.create(center.x + size * math.cos(angle_rad),
                                    center.y + size * math.sin(angle_rad),
                                    0)


# Generic Poly Shape
def shape_sketch(center, input_size, gap, sides, offset):

    spoke = (input_size / 2) - gap

    sketch = start_sketch(center.z)
    lines = sketch.sketchCurves.sketchLines

    start_point = pointy_shape_corner(center, spoke, 0, offset, sides)
    previous_point = start_point
    first = True

    for corner in range(1, sides):
        new_point = pointy_shape_corner(center, spoke, corner, offset, sides)
        line = lines.addByTwoPoints(previous_point, new_point)
        if first:
            start_point = line.startSketchPoint
            first = False
        previous_point = line.endSketchPoint

    lines.addByTwoPoints(previous_point, start_point)

    # Get the profile defined by the shape
    prof = sketch.profiles.item(0)

    return prof


def shape_extrude(prof, height):
    ao = AppObjects()

    extrude_features = ao.root_comp.features.extrudeFeatures
    extrude_input = extrude_features.createInput(prof, adsk.fusion.FeatureOperations.NewBodyFeatureOperation)
    extrude_input.setSymmetricExtent(height, True)
    extrude_feature = extrude_features.add(extrude_input)

    return extrude_feature


# Generic pattern in X Y Directions
def cut_pattern(extrude_collection, x_qty, d1_space, y_qty, d2_space):

    ao = AppObjects()
    pattern_features = ao.root_comp.features.rectangularPatternFeatures

    x_axis = ao.root_comp.xConstructionAxis
    y_axis = ao.root_comp.yConstructionAxis

    pattern_type = adsk.fusion.PatternDistanceType.SpacingPatternDistanceType

    pattern_input = pattern_features.createInput(extrude_collection, x_axis, x_qty, d1_space, pattern_type)
    pattern_input.directionTwoEntity = y_axis
    pattern_input.distanceTwo = d2_space
    pattern_input.quantityTwo = y_qty
    pattern_input.isSymmetricInDirectionOne = True
    pattern_input.isSymmetricInDirectionTwo = True

    pattern_feature = ao.root_comp.features.rectangularPatternFeatures.add(pattern_input)

    return pattern_feature


def create_core_body_new(input_body, input_shell_thickness):
    ao = AppObjects()

    core_body = input_body.copyToComponent(input_body.parentComponent)

    # Shell Main body
    shell_features = ao.root_comp.features.shellFeatures
    input_collection = adsk.core.ObjectCollection.create()
    input_collection.add(input_body)
    shell_input = shell_features.createInput(input_collection)
    shell_input.insideThickness = adsk.core.ValueInput.createByReal(input_shell_thickness)
    shell_feature = shell_features.add(shell_input)

    adsk.terminate()

    # # Offset internal faces 0
    # shell_faces = shell_feature.faces
    # tools = adsk.core.ObjectCollection.create()
    # for face in shell_faces:
    #     tools.add(face)
    # distance = adsk.core.ValueInput.createByReal(-0.5 * input_shell_thickness)
    # offset_features = ao.root_comp.features.offsetFeatures
    # offset_input = offset_features.createInput(tools, distance,
    #                                            adsk.fusion.FeatureOperations.NewBodyFeatureOperation)
    # offset_feature = offset_features.add(offset_input)
    #
    # # Boundary FIll
    # offset_tools = adsk.core.ObjectCollection.create()
    # for body in offset_feature.bodies:
    #     offset_tools.add(body)
    #
    # boundary_fills = ao.root_comp.features.boundaryFillFeatures
    # boundary_fill_input = boundary_fills.createInput(offset_tools,
    #                                                  adsk.fusion.FeatureOperations.NewBodyFeatureOperation)
    # cell = boundary_fill_input.bRepCells.item(0)
    # cell.isSelected = True
    # boundary_fill = boundary_fills.add(boundary_fill_input)
    # core_body = boundary_fill.bodies[0]
    #
    # # Remove extra surface
    # remove_features = ao.root_comp.features.removeFeatures
    # for body in offset_feature.bodies:
    #     remove_features.add(body)

    return core_body


def create_core_body(input_body, input_shell_thickness):
    ao = AppObjects()

    core_body_new = input_body.copyToComponent(input_body.parentComponent)

    # Shell Main body
    shell_features = ao.root_comp.features.shellFeatures
    input_collection = adsk.core.ObjectCollection.create()
    input_collection.add(input_body)
    shell_input = shell_features.createInput(input_collection)
    shell_input.insideThickness = adsk.core.ValueInput.createByReal(input_shell_thickness)
    shell_feature = shell_features.add(shell_input)

    # # Offset internal faces 0
    # shell_faces = shell_feature.faces
    # tools = adsk.core.ObjectCollection.create()
    # for face in shell_faces:
    #     tools.add(face)
    # distance = adsk.core.ValueInput.createByReal(-1.0 * input_shell_thickness)
    # offset_features = ao.root_comp.features.offsetFeatures
    # offset_input = offset_features.createInput(tools, distance,
    #                                            adsk.fusion.FeatureOperations.NewBodyFeatureOperation)
    # offset_feature = offset_features.add(offset_input)
    #
    # # Boundary FIll
    # offset_tools = adsk.core.ObjectCollection.create()
    # for body in offset_feature.bodies:
    #     offset_tools.add(body)
    #
    # boundary_fills = ao.root_comp.features.boundaryFillFeatures
    # boundary_fill_input = boundary_fills.createInput(offset_tools,
    #                                                  adsk.fusion.FeatureOperations.NewBodyFeatureOperation)
    # cell = boundary_fill_input.bRepCells.item(0)
    # cell.isSelected = True
    # boundary_fill = boundary_fills.add(boundary_fill_input)
    # core_body = boundary_fill.bodies[0]
    #
    # # Remove extra surface
    # remove_features = ao.root_comp.features.removeFeatures
    # for body in offset_feature.bodies:
    #     remove_features.add(body)

    return core_body_new
    # return core_body


# Class for the Fusion 360 Command
class FillerCommand(Fusion360CommandBase):

    # TODO some simple graphic preview for scale / size reference
    def on_preview(self, command: adsk.core.Command, inputs: adsk.core.CommandInputs, args, input_values):
        pass

    # Run when command is executed
    def on_execute(self, command: adsk.core.Command, inputs: adsk.core.CommandInputs, args, input_values):
        ao = AppObjects()

        # Get the values from the user input
        infill_type = input_values['type_input']
        body_type = input_values['body_type_input']
        input_size = input_values['size_input']
        input_shell_thickness = input_values['shell_input']
        input_rib_thickness = input_values['rib_input']
        all_selections = input_values['selection_input']

        start_body = adsk.fusion.BRepBody.cast(all_selections[0])
        start_volume = start_body.volume
        start_body_count = ao.design.rootComponent.bRepBodies.count

        base_feature = ao.root_comp.features.baseFeatures.add()

        base_feature.startEdit()

        # General bounding box
        bounding_box = start_body.boundingBox
        extent_vector = bounding_box.maxPoint.asVector()
        extent_vector.subtract(bounding_box.minPoint.asVector())

        mid_vector = extent_vector.copy()
        mid_vector.scaleBy(.5)
        mid_vector.add(bounding_box.minPoint.asVector())

        height_raw = extent_vector.z * 1.1
        height = adsk.core.ValueInput.createByReal(height_raw)

        # Hex specific
        if infill_type == "Hex":
            gap = input_rib_thickness / math.sqrt(3)
            sides = 6
            offset = 30
            x_space = math.sqrt(3) * input_size / 4
            y_space = 3 * input_size / 4

        # Square specific
        elif infill_type == "Square":
            gap = input_rib_thickness * math.sqrt(2) / 2
            sides = 4
            offset = 0
            x_space = input_size / 2
            y_space = input_size / 2

        # Triangle specific
        elif infill_type == "Triangle":
            gap = input_rib_thickness
            sides = 3
            offset = 60
            x_space = input_size / 4
            y_space = math.sqrt(3) * input_size / 4

        # Circle specific
        elif infill_type == "Circle":
            gap = input_rib_thickness / 2
            x_space = input_size / 2
            y_space = math.sqrt(3) * input_size / 2

        else:
            return

        cp_1 = mid_vector.asPoint()
        cp_2 = adsk.core.Point3D.create(cp_1.x + x_space, cp_1.y + y_space, cp_1.z)

        if infill_type in ['Square', 'Hex']:
            prof_1 = shape_sketch(cp_1, input_size, gap, sides, offset)
            prof_2 = shape_sketch(cp_2, input_size, gap, sides, offset)

        elif infill_type in ['Triangle']:
            cp_3 = adsk.core.Point3D.create(cp_1.x + input_size, cp_1.y, cp_1.z)
            cp_4 = adsk.core.Point3D.create(cp_1.x + (3 * x_space), cp_1.y + y_space, cp_1.z)
            prof_1 = shape_sketch(cp_1, input_size, gap, sides, 0)
            prof_2 = shape_sketch(cp_2, input_size, gap, sides, offset)
            prof_3 = shape_sketch(cp_3, input_size, gap, sides, offset)
            prof_4 = shape_sketch(cp_4, input_size, gap, sides, 0)

        elif infill_type in ['Circle']:
            prof_1 = circle_sketch(cp_1, input_size, gap)
            prof_2 = circle_sketch(cp_2, input_size, gap)
        else:
            return

        d1_space = adsk.core.ValueInput.createByReal(x_space * 2)
        d2_space = adsk.core.ValueInput.createByReal(y_space * 2)

        x_qty_raw = math.ceil(extent_vector.x / d1_space.realValue) + 4
        y_qty_raw = math.ceil(extent_vector.y / d2_space.realValue) + 4

        x_qty = adsk.core.ValueInput.createByReal(x_qty_raw)
        y_qty = adsk.core.ValueInput.createByReal(y_qty_raw)

        extrude_cut_collection = []
        extrude_1 = shape_extrude(prof_1, height)
        extrude_2 = shape_extrude(prof_2, height)

        extrude_cut_collection.append(extrude_1.bodies[0])
        extrude_cut_collection.append(extrude_2.bodies[0])

        if infill_type in ['Triangle']:
            d1_space = adsk.core.ValueInput.createByReal(3 * input_size / 2)
            x_qty = adsk.core.ValueInput.createByReal(x_qty_raw / 2)

            extrude_3 = shape_extrude(prof_3, height)
            extrude_4 = shape_extrude(prof_4, height)
            extrude_cut_collection.append(extrude_3.bodies[0])
            extrude_cut_collection.append(extrude_4.bodies[0])

        tbm = adsk.fusion.TemporaryBRepManager.get()

        trans_core = tbm.copy(start_body)

        pattern_list = []

        for body in extrude_cut_collection:
            trans = tbm.copy(body)
            pattern_list.append(trans)
            body.deleteMe()

        for x_int in range(int(x_qty.realValue) * 2):

            x_val = x_int * d1_space.realValue - x_qty.realValue * d1_space.realValue

            for y_int in range(int(y_qty.realValue) * 2):
                y_val = y_int * d2_space.realValue - y_qty.realValue * d2_space.realValue

                trans_matrix = adsk.core.Matrix3D.create()
                trans_matrix.translation = adsk.core.Vector3D.create(x_val, y_val, 0)
                for body in pattern_list:
                    trans_tool = tbm.copy(body)
                    tbm.transform(trans_tool, trans_matrix)
                    tbm.booleanOperation(trans_core, trans_tool, adsk.fusion.BooleanTypes.DifferenceBooleanType)

        # ao.ui.messageBox("volume:   " + str(trans_core.volume))

        if body_type == "Create Shell":
            # Shell Main body
            # ao.root_comp.bRepBodies.add(trans_core, base_feature)
            base_feature.finishEdit()

            shell_features = ao.root_comp.features.shellFeatures
            input_collection = adsk.core.ObjectCollection.create()
            input_collection.add(start_body)
            shell_input = shell_features.createInput(input_collection)
            shell_input.insideThickness = adsk.core.ValueInput.createByReal(input_shell_thickness)
            shell_feature = shell_features.add(shell_input)

            trans_shell = tbm.copy(start_body)

            # start_body.deleteMe()
            # shell_feature.deleteMe()

            base_feature.startEdit()

            tbm.booleanOperation(trans_shell, trans_core, adsk.fusion.BooleanTypes.UnionBooleanType)

            ao.root_comp.bRepBodies.add(trans_shell, base_feature)
        else:
            ao.root_comp.bRepBodies.add(trans_core, base_feature)

        base_feature.finishEdit()

        final_volume = start_body.volume
        ao.ui.messageBox(
            'The final percentage infill is:  {0:.2g}% \n'.format(100 * final_volume / start_volume)
        )

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
        inputs.addValueInput('size_input', 'Size (Major Diameter)',
                             ao.units_manager.defaultLengthUnits, default_size)
        inputs.addValueInput('shell_input', 'Shell Thickness (Outer Wall)',
                             ao.units_manager.defaultLengthUnits, default_shell)
        inputs.addValueInput('rib_input', 'Rib Thickness',
                             ao.units_manager.defaultLengthUnits, default_rib)

        # inputs.addBoolValueInput('bool_input', '***Sample***Checked', True)
        # inputs.addStringValueInput('string_input', '***Sample***String Value', 'Default value')
        selection = inputs.addSelectionInput('selection_input', 'Body for Infill', 'Select a solid body')
        selection.addSelectionFilter("SolidBodies")
        selection.setSelectionLimits(1, 1)

        drop_down_input = inputs.addDropDownCommandInput('type_input', 'Infill Style',
                                                         adsk.core.DropDownStyles.TextListDropDownStyle)
        drop_down_input.listItems.add('Hex', True)
        drop_down_input.listItems.add('Square', False)
        drop_down_input.listItems.add('Triangle', False)
        drop_down_input.listItems.add('Circle', False)

        radio = inputs.addRadioButtonGroupCommandInput("body_type_input", "Infill Type")
        radio.listItems.add("Create Shell", True)
        radio.listItems.add("Direct Cut", False)

