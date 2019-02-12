import bpy
from mathutils import Euler

import os
import random
from math import pi
import struct

def hex2rgb(hex):
    int_tuple = struct.unpack("BBB", bytes.fromhex(hex))
    return tuple([val/255 for val in int_tuple]) 


def render_brick(brick_file_path: str, n: int, render_folder: str, background_file_path: str, debug):
    """Renders n images of a given .dat file

    :param brick_file_path: location of .dat file
    :param n: number of images to render
    :param render_folder: output directory
    :param background_file_path: path to list of background images
    :return: Saves generated images to render_folder
    """

    # load config file for blender settings
    with open(os.path.join(os.path.dirname(__file__), "config.json"), "r") as f:
        cfg = json.load(f)

    # remove all elements in scene
    bpy.ops.object.select_by_layer()
    bpy.ops.object.delete(use_global=False)

    # create world
    world = bpy.data.worlds.new("World")
    world.use_sky_paper = True
    bpy.context.scene.world = world

    # create camera
    bpy.ops.object.add(type="CAMERA")
    cam = bpy.context.object
    bpy.context.scene.camera = cam

    # create light
    bpy.ops.object.lamp_add(type="SUN", radius=1, view_align=False, location=(0, -1, 0), rotation=(pi/2, 0, 0))

    # create object
    bpy.ops.import_scene.importldraw(filepath=brick_file_path)
    bpy.data.objects.remove(bpy.data.objects["LegoGroundPlane"])

    # after loading brick, move camera position
    cam.location = (0, -1, 0)
    cam.rotation_euler = Euler((pi/2, 0, 0), "XYZ")

    # brick selection
    for obj in bpy.data.objects:
        if obj.name.endswith(".dat"):
            brick = obj
            break

    # render and image settings
    if not os.path.exists(render_folder):
        os.mkdir(render_folder)
    bpy.context.scene.render.engine = "BLENDER_RENDER"
    rnd = bpy.data.scenes["Scene"].render
    rnd.resolution_x = cfg["width"]
    rnd.resolution_y = cfg["height"]
    rnd.resolution_percentage = 100
    bpy.context.scene.render.image_settings.file_format = "JPEG"
    bpy.context.scene.render.image_settings.color_mode = "RGB"
    bpy.context.scene.render.image_settings.quality = cfg["jpeg_compression"]


    # list of possible background images
    if background_file_path:
        images = []
        valid_ext = [".jpg", ".png"]
        for f in os.listdir(background_file_path):
            ext = os.path.splitext(f)[1]
            if ext.lower() in valid_ext:
                images.append(os.path.join(background_file_path, f))

    debug_list = []
    r = cfg["rotation_intervals"]
    for i in range(n):
        # brick settings
        brick_scale_factor = random.uniform(cfg['zoom_min'], cfg['zoom_max'])
        brick_rotx = random.choice([random.uniform(r['1_low'], r['1_high']), random.uniform(r['2_low'], r['2_high']),
                                    random.uniform(r['3_low'], r['3_high']), random.uniform(r['4_low'], r['4_high'])])
        brick_roty = random.choice([random.uniform(r['1_low'], r['1_high']), random.uniform(r['2_low'], r['2_high']),
                                    random.uniform(r['3_low'], r['3_high']), random.uniform(r['4_low'], r['4_high'])])
        brick_rotz = random.choice([random.uniform(r['1_low'], r['1_high']), random.uniform(r['2_low'], r['2_high']),
                                    random.uniform(r['3_low'], r['3_high']), random.uniform(r['4_low'], r['4_high'])])
        brick_posx = random.gauss(cfg['pos_mean'], cfg['pos_sigma'])
        brick_posz = random.gauss(cfg['pos_mean'], cfg['pos_sigma'])
        brick_posy = 0.0  # due to scaling
        
        brick.scale = (brick_scale_factor, brick_scale_factor, brick_scale_factor)
        brick.location = (brick_posx, brick_posy, brick_posz)
        brick.rotation_euler = (brick_rotx, brick_roty, brick_rotz)

        # set color
        color = hex2rgb(random.choice(cfg["color"]))

        debug_list.append({
            "brick_posx": brick_posx,
            "brick_posy": brick_posy,
            "brick_posz": brick_posz,
            "brick_rotx": brick_rotx,
            "brick_roty": brick_roty,
            "brick_rotz": brick_rotz,
            "brick_scale_factor": brick_scale_factor,
            "color": color
        }, )


        if brick.active_material:
            brick.active_material.diffuse_color = color
        else:  # brick consists of more than one parts
            for obj in brick.children:
                if len(obj.material_slots) == 0:
                    bpy.context.scene.objects.active = obj
                    bpy.ops.object.material_slot_add()
                obj.material_slots[0].material = bpy.data.materials["Material"]
                obj.active_material.diffuse_color = color

        if background_file_path:
            # select random background image
            bg_image = random.choice(images)
            image = bpy.data.images.load(bg_image)

            # set background image
            tex = bpy.data.textures.new(bg_image, "IMAGE")
            tex.image = image
            slot = world.texture_slots.add()
            slot.texture = tex
            slot.use_map_horizon = True

        # render image
        rnd.filepath = os.path.join(render_folder, str(i) + ".jpg")
        bpy.ops.render.render(write_still=True)

        # remove current background
        world.texture_slots.clear(0)

    if debug:
        with open(os.path.join(render_folder, "debug.json"), "w") as fd:
            json.dump(debug_list, fd, indent=2)


if __name__ == '__main__':

    # check whether script is opened in blender
    import sys, json, argparse
    if bpy.context.space_data:
        cwd = os.path.dirname(bpy.context.space_data.text.filepath)
    else:
        cwd = os.path.dirname(os.path.abspath(__file__))

    # get folder of script and add current working directory to path
    sys.path.append(cwd)


    # add python script arguments
    argv = sys.argv
    if "--" not in argv:
        argv = []
    else:
        argv = argv[argv.index("--") + 1:]  # get all after first --

    # when --help or no args are given
    usage_text = (
        "Run blender in background mode with this script on linux:"
        + " blender -b -P " + __file__ + "-- [options] "
        + "or with /Applications/Blender/blender.app/Contents/MacOS/blender -b -p " + __file__ + "-- [options]"
        + "on MacOS"
    )

    parser = argparse.ArgumentParser(description=usage_text)
    parser.add_argument(
        "-i", "--input_file_path", dest="input", type=str, required=True, help="Input folder for 3d models"
    )

    parser.add_argument(
        "-b", "--background_files_path", dest="background", type=str, required=False, help="Input folder for "
                                                                                           "background images"
    )

    parser.add_argument(
        "-n", "--images_per_brick", dest="number", type=int, required=False, default=1, help="Number of bricks to "
                                                                                             "render"
    )

    parser.add_argument(
          "-s", "--save", dest="save", type=str, required=False, default="./", help="Output folder"
    )

    parser.add_argument(
          "--debug", action="store_true"
    )

    args = parser.parse_args(argv)
    if not argv:
        parser.print_help()
        sys.exit(-1)


    # finally render image(s)
    render_brick(args.input, args.number, args.save, args.background, args.debug)