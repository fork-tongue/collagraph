import collagraph as cg


def test_cgx_slots_named_fallback():
    from tests.data.slots.template_empty import Template

    gui = cg.Collagraph(cg.DictRenderer(), event_loop_type=cg.EventLoopType.SYNC)
    container = {"type": "root"}
    gui.render(cg.h(Template), container)

    container = container["children"][0]
    assert container["type"] == "widget"

    header, content, footer = container["children"]

    assert header["type"] == "header"
    assert header["children"][0]["type"] == "label"
    assert header["children"][0]["attrs"]["text"] == "header fallback"

    assert content["type"] == "content"
    assert content["children"][0]["type"] == "label"
    assert content["children"][0]["attrs"]["text"] == "content fallback"
    assert len(content["children"]) == 1

    assert footer["type"] == "footer"
    assert footer["children"][0]["type"] == "label"
    assert footer["children"][0]["attrs"]["text"] == "footer fallback"


def test_cgx_slots_named():
    from tests.data.slots.template import Template

    gui = cg.Collagraph(cg.DictRenderer(), event_loop_type=cg.EventLoopType.SYNC)
    container = {"type": "root"}
    gui.render(cg.h(Template), container)

    container = container["children"][0]
    assert container["type"] == "widget"

    header, content, footer = container["children"]

    assert header["type"] == "header"
    assert header["children"][0]["type"] == "label"
    assert header["children"][0]["attrs"]["text"] == "header content"

    assert content["type"] == "content"
    assert content["children"][0]["type"] == "label"
    assert content["children"][0]["attrs"]["text"] == "content"
    assert content["children"][1]["attrs"]["text"] == "even more content"
    assert len(content["children"]) == 2

    assert footer["type"] == "footer"
    assert footer["children"][0]["type"] == "label"
    assert footer["children"][0]["attrs"]["text"] == "footer content"


def test_cgx_slots_partial_no_fallback():
    from tests.data.slots.template_partial import Template

    gui = cg.Collagraph(cg.DictRenderer(), event_loop_type=cg.EventLoopType.SYNC)
    container = {"type": "root"}
    gui.render(cg.h(Template), container)

    container = container["children"][0]
    assert container["type"] == "widget"

    header, content, footer = container["children"]

    assert header["type"] == "header"
    assert header["children"][0]["type"] == "label"
    assert header["children"][0]["attrs"]["text"] == "header content"

    assert content["type"] == "content"
    assert "children" not in content

    assert footer["type"] == "footer"
    assert footer["children"][0]["type"] == "label"
    assert footer["children"][0]["attrs"]["text"] == "footer content"


def test_cgx_slots_implicit_default_slot_name():
    from tests.data.slots.template_implicit_default_slot_name import Template

    gui = cg.Collagraph(cg.DictRenderer(), event_loop_type=cg.EventLoopType.SYNC)
    container = {"type": "root"}
    gui.render(cg.h(Template), container)

    container = container["children"][0]
    assert container["type"] == "widget"

    header, content, footer = container["children"]

    assert header["type"] == "header"
    assert header["children"][0]["type"] == "label"
    assert header["children"][0]["attrs"]["text"] == "header content"

    assert content["type"] == "content"
    assert content["children"][0]["type"] == "label"
    assert content["children"][0]["attrs"]["text"] == "content"
    assert content["children"][1]["attrs"]["text"] == "even more content"
    assert len(content["children"]) == 2

    assert footer["type"] == "footer"
    assert footer["children"][0]["type"] == "label"
    assert footer["children"][0]["attrs"]["text"] == "footer content"


def test_cgx_slots_implicit_default_slot():
    from tests.data.slots.template_implicit_default_slot import Template

    gui = cg.Collagraph(cg.DictRenderer(), event_loop_type=cg.EventLoopType.SYNC)
    container = {"type": "root"}
    gui.render(cg.h(Template), container)

    container = container["children"][0]
    assert container["type"] == "widget"

    header, content, footer = container["children"]

    assert header["type"] == "header"
    assert header["children"][0]["type"] == "label"
    assert header["children"][0]["attrs"]["text"] == "header content"

    assert content["type"] == "content"
    assert content["children"][0]["type"] == "label"
    assert content["children"][0]["attrs"]["text"] == "content"
    assert content["children"][1]["attrs"]["text"] == "even more content"
    assert len(content["children"]) == 2

    assert footer["type"] == "footer"
    assert footer["children"][0]["type"] == "label"
    assert footer["children"][0]["attrs"]["text"] == "footer content"


def test_cgx_slots_tree():
    from tests.data.slots.tree import Tree

    gui = cg.Collagraph(cg.DictRenderer(), event_loop_type=cg.EventLoopType.SYNC)
    container = {"type": "container"}
    gui.render(cg.h(Tree), container)

    container = container["children"][0]
    assert container["type"] == "root"

    a, c = container["children"]

    assert a["type"] == "node"
    assert a["attrs"]["name"] == "a"

    assert c["type"] == "node"
    assert c["attrs"]["name"] == "c"

    assert a["children"][0]["type"] == "node"
    assert a["children"][0]["attrs"]["name"] == "b"


def test_cgx_slots_icw_functional_component():
    from tests.data.slots.tree_functional import Tree

    gui = cg.Collagraph(cg.DictRenderer(), event_loop_type=cg.EventLoopType.SYNC)
    container = {"type": "container"}
    gui.render(cg.h(Tree), container)

    container = container["children"][0]
    assert container["type"] == "root"

    a, c = container["children"]

    assert a["type"] == "node"
    assert a["attrs"]["name"] == "a"

    assert c["type"] == "node"
    assert c["attrs"]["name"] == "c"

    assert a["children"][0]["type"] == "node"
    assert a["children"][0]["attrs"]["name"] == "b"
