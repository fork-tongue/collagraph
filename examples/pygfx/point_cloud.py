import random

import pygfx as gfx

from collagraph import h

sphere_geom = gfx.sphere_geometry(radius=0.5)
materials = {
    "default": gfx.MeshPhongMaterial(color=[1, 1, 1], pick_write=True),
    "selected": gfx.MeshPhongMaterial(color=[1, 0, 0], pick_write=True),
    "hovered": gfx.MeshPhongMaterial(color=[1, 0.6, 0], pick_write=True),
    "other": gfx.MeshPhongMaterial(color=[1, 0, 0.5], pick_write=True),
}


def rand_point():
    return (
        random.randint(-20, 20),
        random.randint(-20, 20),
        random.randint(-20, 20),
    )


def point(index, selected, hovered, set_selected, set_hovered):
    material = (
        "selected"
        if index == selected
        else "hovered" if index == hovered else "default"
    )
    return h(
        "Mesh",
        {
            "geometry": sphere_geom,
            "material": materials[material],
            "local.position": positions[index],
            "key": index,
            "on_click": lambda event: set_selected(index),
            "on_pointer_move": lambda event: set_hovered(index),
        },
    )


positions = []


def PointCloud(props):
    global positions

    def set_hovered(index):
        props["hovered"] = index

    def set_selected(index):
        if props.get("selected", -1) == index:
            props["selected"] = -1
        else:
            props["selected"] = index

    selected = props.get("selected", -1)
    hovered = props.get("hovered", -1)
    number_of_points = props.get("count", 50)

    if len(positions) > number_of_points:
        positions = positions[:number_of_points]
    elif len(positions) < number_of_points:
        positions.extend(
            [rand_point() for _ in range(number_of_points - len(positions))]
        )

    return h(
        "Group",
        {},
        *[
            point(i, selected, hovered, set_selected, set_hovered)
            for i in range(number_of_points)
        ],
    )
