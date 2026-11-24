"""Emkay on a fixed screen — product shots in the emkay-capsule render style.
Usage: python3 scene.py <shot> <out.png> [samples] [rx] [ry]
Shots: tablet, phone, laptop, pi. Needs Blender 4.x/5.x as a Python module (pip install bpy)."""
import bpy, math, sys, os
from mathutils import Vector

HERE = os.path.dirname(os.path.abspath(__file__))
SCR = os.path.join(HERE, "screens")
SHOT, OUT = sys.argv[1], sys.argv[2]
SAMPLES = int(sys.argv[3]) if len(sys.argv) > 3 else 64
RX = int(sys.argv[4]) if len(sys.argv) > 4 else 1000
RY = int(sys.argv[5]) if len(sys.argv) > 5 else 1250

bpy.ops.wm.read_factory_settings(use_empty=True)
sc = bpy.context.scene
sc.render.engine = "CYCLES"
sc.cycles.device = "CPU"
sc.cycles.samples = SAMPLES
sc.cycles.use_denoising = True
sc.render.resolution_x, sc.render.resolution_y = RX, RY
sc.view_settings.exposure = -0.6
try:
    sc.view_settings.view_transform = "AgX"
    sc.view_settings.look = "AgX - Base Contrast"
except Exception:
    sc.view_settings.view_transform = "Filmic"


# ---------- materials ----------
def mat(name, color, rough, metal=0.0, coat=0.0):
    m = bpy.data.materials.new(name); m.use_nodes = True
    b = m.node_tree.nodes["Principled BSDF"]
    b.inputs["Base Color"].default_value = (*color, 1)
    b.inputs["Roughness"].default_value = rough
    b.inputs["Metallic"].default_value = metal
    if coat and "Coat Weight" in b.inputs:
        b.inputs["Coat Weight"].default_value = coat
        b.inputs["Coat Roughness"].default_value = 0.03
    return m, b


def noisy(m, b, scale=30, amount=0.06, bump=0.02):
    """Subtle colour variation + bump, so surfaces don't look CG-flat."""
    nt = m.node_tree
    tc = nt.nodes.new("ShaderNodeTexCoord")
    nz = nt.nodes.new("ShaderNodeTexNoise"); nz.inputs["Scale"].default_value = scale
    nt.links.new(tc.outputs["Object"], nz.inputs["Vector"])
    base = b.inputs["Base Color"].default_value[:]
    mix = nt.nodes.new("ShaderNodeMix"); mix.data_type = "RGBA"
    mix.inputs["Factor"].default_value = amount
    mix.inputs[6].default_value = base
    mix.inputs[7].default_value = (0, 0, 0, 1)
    nt.links.new(nz.outputs["Fac"], mix.inputs["Factor"])
    mul = nt.nodes.new("ShaderNodeMath"); mul.operation = "MULTIPLY"; mul.inputs[1].default_value = amount * 2
    nt.links.new(nz.outputs["Fac"], mul.inputs[0])
    nt.links.new(mul.outputs[0], mix.inputs["Factor"])
    nt.links.new(mix.outputs[2], b.inputs["Base Color"])
    if bump:
        bp = nt.nodes.new("ShaderNodeBump"); bp.inputs["Strength"].default_value = bump
        nz2 = nt.nodes.new("ShaderNodeTexNoise"); nz2.inputs["Scale"].default_value = scale * 20
        nt.links.new(tc.outputs["Object"], nz2.inputs["Vector"])
        nt.links.new(nz2.outputs["Fac"], bp.inputs["Height"])
        nt.links.new(bp.outputs["Normal"], b.inputs["Normal"])
    return m


def wood(name, c1, c2, scale=3.0):
    m, b = mat(name, c1, 0.45, coat=0.2)
    nt = m.node_tree
    tc = nt.nodes.new("ShaderNodeTexCoord")
    mp = nt.nodes.new("ShaderNodeMapping"); mp.inputs["Scale"].default_value = (1, 18, 1)
    wv = nt.nodes.new("ShaderNodeTexWave"); wv.inputs["Scale"].default_value = scale
    wv.inputs["Distortion"].default_value = 6; wv.inputs["Detail"].default_value = 4
    nt.links.new(tc.outputs["Object"], mp.inputs["Vector"]); nt.links.new(mp.outputs["Vector"], wv.inputs["Vector"])
    mix = nt.nodes.new("ShaderNodeMix"); mix.data_type = "RGBA"
    mix.inputs[6].default_value = (*c1, 1); mix.inputs[7].default_value = (*c2, 1)
    nt.links.new(wv.outputs["Fac"], mix.inputs["Factor"])
    nt.links.new(mix.outputs[2], b.inputs["Base Color"])
    return m


def screen_mat(img, strength=3.4):
    m, b = mat("screen_" + os.path.basename(img), (0.0, 0.0, 0.0), 0.12, coat=0.35)
    nt = m.node_tree
    tex = nt.nodes.new("ShaderNodeTexImage")
    tex.image = bpy.data.images.load(img)
    tex.extension = "EXTEND"
    nt.links.new(tex.outputs["Color"], b.inputs["Emission Color"])
    b.inputs["Emission Strength"].default_value = strength
    return m


# ---------- geometry helpers ----------
def rbox(name, size, m, loc=(0, 0, 0), rot=(0, 0, 0), bevel=0.003, segs=6):
    bpy.ops.mesh.primitive_cube_add(size=1, location=loc, rotation=[math.radians(a) for a in rot])
    o = bpy.context.object; o.name = name
    o.scale = size
    bpy.ops.object.transform_apply(scale=True)
    if bevel:
        md = o.modifiers.new("bev", "BEVEL"); md.width = bevel; md.segments = segs
        md.limit_method = "NONE"
    o.data.materials.append(m)
    bpy.ops.object.shade_smooth()
    return o


def cyl(name, r, h, m, loc=(0, 0, 0), rot=(0, 0, 0), bevel=0.002, verts=64):
    bpy.ops.mesh.primitive_cylinder_add(radius=r, depth=h, vertices=verts, location=loc,
                                        rotation=[math.radians(a) for a in rot])
    o = bpy.context.object; o.name = name
    if bevel:
        md = o.modifiers.new("bev", "BEVEL"); md.width = bevel; md.segments = 4; md.limit_method = "ANGLE"
    o.data.materials.append(m)
    bpy.ops.object.shade_smooth()
    return o


def plane(name, w, h, m, loc, rot):
    bpy.ops.mesh.primitive_plane_add(size=1, location=loc, rotation=[math.radians(a) for a in rot])
    o = bpy.context.object; o.name = name
    o.scale = (w, h, 1); bpy.ops.object.transform_apply(scale=True)
    o.data.materials.append(m)
    return o


def parent(children, p):
    for c in children:
        c.parent = p


def device(name, w, h, d, body_m, img, bezel, radius, loc, rot):
    """Flat slab device (phone/tablet/display). Local: x=width, z=height, -y=front."""
    bpy.ops.object.empty_add(location=loc, rotation=[math.radians(a) for a in rot])
    root = bpy.context.object; root.name = name
    body = rbox(name + "_body", (w, d, h), body_m, bevel=radius, segs=10)
    glass = rbox(name + "_glass", (w - 0.0006, 0.0008, h - 0.0006), black_glass,
                 loc=(0, -d / 2 - 0.0001, 0), bevel=radius * 0.95, segs=10)
    scr = plane(name + "_screen", w - 2 * bezel, h - 2 * bezel, screen_mat(img),
                loc=(0, -d / 2 - 0.0007, 0), rot=(90, 0, 0))
    parent([body, glass, scr], root)
    return root


def camera(loc, target, lens=60, fstop=2.8, focus=None):
    cd = bpy.data.cameras.new("cam"); cd.lens = lens
    cam = bpy.data.objects.new("cam", cd); sc.collection.objects.link(cam); sc.camera = cam
    cam.location = loc
    d = Vector(target) - Vector(loc)
    cam.rotation_euler = d.to_track_quat("-Z", "Y").to_euler()
    cd.dof.use_dof = True; cd.dof.aperture_fstop = fstop
    cd.dof.focus_distance = focus or d.length


def area(loc, target, size, energy, color=(1, 0.96, 0.9)):
    ld = bpy.data.lights.new("area", "AREA"); ld.size = size; ld.energy = energy; ld.color = color
    lo = bpy.data.objects.new("area", ld); sc.collection.objects.link(lo); lo.location = loc
    lo.rotation_euler = (Vector(target) - Vector(loc)).to_track_quat("-Z", "Y").to_euler()


def world(color=(0.85, 0.82, 0.78), strength=0.35):
    w = bpy.data.worlds.new("w"); sc.world = w; w.use_nodes = True
    bg = w.node_tree.nodes["Background"]
    bg.inputs["Color"].default_value = (*color, 1); bg.inputs["Strength"].default_value = strength


# ---------- shared materials ----------
black_glass = mat("bglass", (0.002, 0.002, 0.003), 0.08, coat=0.5)[0]
alu = noisy(*mat("alu", (0.62, 0.63, 0.65), 0.32, metal=1.0), scale=200, amount=0.02, bump=0.004)
dark_alu = noisy(*mat("dalu", (0.06, 0.065, 0.07), 0.35, metal=0.8), scale=200, amount=0.02, bump=0.004)
plastic_w = noisy(*mat("plw", (0.78, 0.77, 0.75), 0.4), scale=80, amount=0.03, bump=0.01)
plastic_b = noisy(*mat("plb", (0.02, 0.02, 0.022), 0.45), scale=80, amount=0.05, bump=0.01)
wall_m = noisy(*mat("wall", (0.55, 0.52, 0.48), 0.9), scale=6, amount=0.05, bump=0.05)
ceramic = mat("ceramic", (0.85, 0.84, 0.80), 0.25, coat=0.6)[0]
sage = mat("sage", (0.30, 0.38, 0.30), 0.6)[0]
leaf = mat("leaf", (0.06, 0.16, 0.06), 0.5)[0]
stone = noisy(*mat("stone", (0.80, 0.79, 0.76), 0.25, coat=0.4), scale=12, amount=0.12, bump=0.02)
oak = wood("oak", (0.42, 0.27, 0.15), (0.30, 0.18, 0.09))
light_oak = wood("loak", (0.62, 0.46, 0.30), (0.50, 0.35, 0.21))


def plant(x, y, z, s=1.0):
    cyl("pot", 0.055 * s, 0.11 * s, ceramic, loc=(x, y, z + 0.055 * s), bevel=0.004)
    for i in range(9):
        a = i * 40
        bpy.ops.mesh.primitive_uv_sphere_add(radius=0.04 * s, location=(x + 0.03 * s * math.cos(math.radians(a)),
                                             y + 0.03 * s * math.sin(math.radians(a)), z + (0.14 + 0.02 * (i % 3)) * s))
        o = bpy.context.object; o.scale = (1.0, 0.35, 1.6)
        o.rotation_euler = (math.radians(25), math.radians(25 * ((i % 3) - 1)), math.radians(a))
        o.data.materials.append(leaf); bpy.ops.object.shade_smooth()


def mug(x, y, z, m):
    cyl("mug", 0.04, 0.095, m, loc=(x, y, z + 0.0475), bevel=0.003)
    bpy.ops.mesh.primitive_torus_add(major_radius=0.025, minor_radius=0.007,
                                     location=(x + 0.045, y, z + 0.05), rotation=(math.radians(90), 0, 0))
    bpy.context.object.data.materials.append(m); bpy.ops.object.shade_smooth()


# ---------- shots ----------
def shot_tablet():
    """Tablet mounted on a kitchen wall, landscape."""
    world((0.9, 0.86, 0.8), 0.4)
    plane("wall", 4, 3, wall_m, (0, 0.02, 1.3), (90, 0, 0))
    rbox("counter", (3, 0.65, 0.04), stone, loc=(0, -0.3, 0.9), bevel=0.004)
    rbox("cabinet", (3, 0.6, 0.88), plastic_w, loc=(0, -0.28, 0.44), bevel=0.002)
    device("tablet", 0.25, 0.158, 0.007, alu, f"{SCR}/tablet_land.png", 0.011, 0.012,
           (0, 0.012, 1.32), (0, 0, 0))
    rbox("mount", (0.07, 0.012, 0.05), plastic_b, loc=(0, 0.018, 1.32), bevel=0.003)
    plant(-0.3, -0.12, 0.92, 1.3)
    mug(0.2, -0.3, 0.92, sage)
    rbox("board", (0.32, 0.02, 0.24), light_oak, loc=(0.42, -0.02, 1.04), rot=(-8, 0, 0), bevel=0.006)
    camera((0.42, -1.3, 1.28), (0.06, 0, 1.13), lens=50, fstop=2.4, focus=1.37)
    area((-1.9, -0.5, 2.3), (0, 0, 1.1), 1.6, 520)
    area((1.8, -0.8, 1.9), (0, 0, 1.1), 2.0, 140, (0.85, 0.9, 1.0))


def shot_phone():
    """Phone upright on a stand on a nightstand, evening."""
    world((0.55, 0.5, 0.45), 0.18)
    plane("wall", 4, 3, wall_m, (0, 0.35, 1.0), (90, 0, 0))
    rbox("stand_top", (0.9, 0.5, 0.03), oak, loc=(0, 0.05, 0.6), bevel=0.004)
    # simple wooden phone stand
    rbox("stand_base", (0.09, 0.075, 0.014), light_oak, loc=(0, 0.004, 0.622), bevel=0.004)
    rbox("stand_back", (0.07, 0.012, 0.11), light_oak, loc=(0, 0.03, 0.67), rot=(-14, 0, 0), bevel=0.003)
    device("phone", 0.072, 0.155, 0.008, dark_alu, f"{SCR}/portrait.png",
           0.002, 0.009, (0, 0.006, 0.702), (-14, 0, 0))
    # lamp
    cyl("lamp_base", 0.06, 0.02, ceramic, loc=(0.3, 0.17, 0.625))
    cyl("lamp_stem", 0.006, 0.3, alu, loc=(0.3, 0.17, 0.78), bevel=0)
    shade_m = mat("shade", (0.95, 0.85, 0.65), 0.8)[0]
    bpy.ops.mesh.primitive_cone_add(radius1=0.12, radius2=0.08, depth=0.16, location=(0.3, 0.17, 0.95))
    bpy.context.object.data.materials.append(shade_m)
    ld = bpy.data.lights.new("bulb", "POINT"); ld.energy = 40; ld.color = (1, 0.75, 0.45); ld.shadow_soft_size = 0.05
    lo = bpy.data.objects.new("bulb", ld); sc.collection.objects.link(lo); lo.location = (0.3, 0.17, 0.92)
    rbox("book", (0.16, 0.22, 0.025), sage, loc=(-0.24, 0.05, 0.628), rot=(0, 0, 12), bevel=0.002)
    rbox("book2", (0.15, 0.21, 0.02), mat("red", (0.45, 0.12, 0.08), 0.6)[0], loc=(-0.24, 0.05, 0.65), rot=(0, 0, 4), bevel=0.002)
    camera((-0.2, -0.6, 0.8), (0.05, 0.02, 0.7), lens=60, fstop=3.2, focus=(Vector((-0.2,-0.6,0.8))-Vector((0,-0.01,0.71))).length)
    area((-0.8, -0.7, 1.4), (0, 0, 0.7), 1.0, 70, (1, 0.9, 0.8))


def laptop(name, loc, rot_z, img, w=0.32, dpt=0.22, open_deg=105):
    bpy.ops.object.empty_add(location=loc, rotation=(0, 0, math.radians(rot_z)))
    root = bpy.context.object
    base = rbox(name + "_base", (w, dpt, 0.016), dark_alu, loc=(0, 0, 0.008), bevel=0.005, segs=8)
    kb = rbox(name + "_kb", (w * 0.86, dpt * 0.42, 0.0015), plastic_b, loc=(0, 0.02, 0.0162), bevel=0.001)
    pad = rbox(name + "_pad", (w * 0.36, dpt * 0.28, 0.001), mat("pad", (0.09, 0.095, 0.1), 0.3)[0],
               loc=(0, -dpt * 0.3, 0.0162), bevel=0.001)
    bpy.ops.object.empty_add(location=(0, dpt / 2 - 0.004, 0.016))
    hinge = bpy.context.object
    hinge.rotation_euler = (math.radians(-(open_deg - 90)), 0, 0)
    lid_h = dpt - 0.01
    lid = device(name + "_lid", w, lid_h, 0.007, dark_alu, img, 0.012, 0.005, (0, 0, lid_h / 2), (0, 0, 0))
    lid.parent = hinge
    parent([base, kb, pad, hinge], root)
    return root


def shot_laptop():
    """An old laptop on the kitchen table."""
    world((0.88, 0.85, 0.8), 0.45)
    plane("wall", 5, 3, wall_m, (0, 0.9, 1.2), (90, 0, 0))
    rbox("table", (1.6, 1.0, 0.04), light_oak, loc=(0, 0.1, 0.74), bevel=0.004)
    laptop("lap", (0, 0.12, 0.76), 0, f"{SCR}/laptop.png")
    mug(0.32, 0.0, 0.76, ceramic)
    plant(-0.36, 0.3, 0.76, 1.0)
    bpy.ops.mesh.primitive_uv_sphere_add(radius=0.035, location=(0.26, 0.28, 0.795))
    bpy.context.object.data.materials.append(mat("apple", (0.55, 0.08, 0.05), 0.35, coat=0.6)[0]); bpy.ops.object.shade_smooth()
    # window light from the left
    area((-1.6, -0.2, 1.5), (0, 0.1, 0.8), 1.8, 420)
    area((1.2, -1.3, 1.6), (0, 0.1, 0.8), 1.8, 90, (0.85, 0.9, 1.0))
    camera((0.42, -0.95, 1.08), (0.0, 0.18, 0.86), lens=55, fstop=2.4)


def pi_board(loc, rot_z):
    pcb = mat("pcb", (0.02, 0.22, 0.08), 0.35, coat=0.5)[0]
    bpy.ops.object.empty_add(location=loc, rotation=(0, 0, math.radians(rot_z)))
    root = bpy.context.object
    parts = [rbox("pcb", (0.085, 0.056, 0.0016), pcb, bevel=0.001)]
    for i in range(2):
        parts.append(rbox(f"usb{i}", (0.013, 0.017, 0.015), alu, loc=(0.035, -0.018 + i * 0.019, 0.008), bevel=0.0008))
    parts.append(rbox("eth", (0.016, 0.021, 0.013), alu, loc=(0.034, 0.019, 0.007), bevel=0.0008))
    parts.append(rbox("soc", (0.014, 0.014, 0.0012), mat("soc", (0.6, 0.6, 0.62), 0.2, metal=1)[0], loc=(-0.01, 0, 0.0014), bevel=0.0005))
    parts.append(rbox("hdr", (0.05, 0.005, 0.008), plastic_b, loc=(-0.01, 0.024, 0.005), bevel=0.0005))
    parent(parts, root)


def shot_pi():
    """Small display on a desk stand + a Pi and a USB mic puck."""
    world((0.85, 0.85, 0.86), 0.35)
    plane("wall", 4, 3, wall_m, (0, 0.6, 1.2), (90, 0, 0))
    rbox("desk", (1.4, 0.9, 0.035), oak, loc=(0, 0.1, 0.72), bevel=0.004)
    # display (7" class) in a black case, tilted back on a foot
    device("disp", 0.194, 0.124, 0.02, plastic_b, f"{SCR}/pi.png", 0.012, 0.004,
           (0, 0.1, 0.82), (-12, 0, 0))
    rbox("foot", (0.08, 0.09, 0.008), plastic_b, loc=(0, 0.13, 0.742), bevel=0.003)
    rbox("leg", (0.03, 0.012, 0.09), plastic_b, loc=(0, 0.135, 0.785), rot=(-12, 0, 0), bevel=0.003)
    pi_board((0.15, 0.07, 0.7385), 18)
    # small desktop USB microphone: round foot, short stem, mesh head
    grille = mat("grille", (0.10, 0.10, 0.11), 0.55, metal=0.7)[0]
    cyl("mic_foot", 0.035, 0.012, dark_alu, loc=(-0.17, -0.02, 0.744), bevel=0.004)
    cyl("mic_stem", 0.006, 0.05, dark_alu, loc=(-0.17, -0.02, 0.775), bevel=0)
    cyl("mic_head", 0.014, 0.045, grille, loc=(-0.17, -0.02, 0.82), bevel=0.006)
    # cable from mic to pi (simple curve)
    cv = bpy.data.curves.new("cable", "CURVE"); cv.dimensions = "3D"; cv.bevel_depth = 0.0018
    sp = cv.splines.new("BEZIER"); sp.bezier_points.add(2)
    pts = [(-0.14, -0.02, 0.741), (0.0, -0.05, 0.7395), (0.12, 0.06, 0.7405)]
    for p, c in zip(sp.bezier_points, pts):
        p.co = c; p.handle_left_type = p.handle_right_type = "AUTO"
    co = bpy.data.objects.new("cable", cv); sc.collection.objects.link(co); cv.materials.append(plastic_b)
    plant(0.32, 0.3, 0.7375, 1.0)
    mug(-0.33, 0.2, 0.7375, sage)
    area((-1.2, -0.9, 1.6), (0, 0.1, 0.8), 1.5, 260)
    area((1.3, -0.6, 1.2), (0, 0.1, 0.8), 1.5, 110, (0.85, 0.9, 1.0))
    camera((0.12, -0.62, 1.0), (0.0, 0.06, 0.79), lens=45, fstop=2.8)


{"tablet": shot_tablet, "phone": shot_phone, "laptop": shot_laptop, "pi": shot_pi}[SHOT]()
sc.render.filepath = OUT
bpy.ops.render.render(write_still=True)
