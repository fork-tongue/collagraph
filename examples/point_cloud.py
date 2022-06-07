import random

import pygfx as gfx

from collagraph import h

sphere_geom = gfx.sphere_geometry(radius=0.5)
materials = {
    "default": gfx.MeshPhongMaterial(color=[1, 1, 1]),
    "selected": gfx.MeshPhongMaterial(color=[1, 0, 0]),
    "hovered": gfx.MeshPhongMaterial(color=[1, 0.6, 0]),
    "other": gfx.MeshPhongMaterial(color=[1, 0, 0.5]),
}


def PointCloud(props):
    random.seed(0)

    def set_hovered(index):
        props["hovered"] = index

    def set_selected(index):
        if props.get("selected", -1) == index:
            props["selected"] = -1
        else:
            props["selected"] = index

    def random_point(index, selected, hovered):
        material = materials["default"]
        if index == selected:
            material = materials["selected"]
        elif index == hovered:
            material = materials["hovered"]
        return h(
            "Mesh",
            {
                "geometry": sphere_geom,
                "material": material,
                "position": [
                    random.randint(-10, 10),
                    random.randint(-10, 10),
                    random.randint(-10, 10),
                ],
                "key": index,
                "on_click": lambda event: set_selected(index),
                "on_pointer_move": lambda event: set_hovered(index),
            },
        )

    selected = props.get("selected", -1)
    hovered = props.get("hovered", -1)
    number_of_points = props.get("count", 50)

    return h(
        "Group",
        {},
        *[random_point(i, selected, hovered) for i in range(number_of_points)],
    )
