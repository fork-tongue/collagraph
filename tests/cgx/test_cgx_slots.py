import collagraph as cg


def test_cgx_slots_named_default_content():
    from tests.data.slots.template_empty import Template

    gui = cg.Collagraph(cg.DictRenderer(), event_loop_type=cg.EventLoopType.SYNC)
    container = {"type": "root"}
    gui.render(cg.h(Template), container)

    container = container["children"][0]
    assert container["type"] == "widget"

    header, content, footer = container["children"]

    assert header["type"] == "header"
    assert header["children"][0]["type"] == "label"
    assert header["children"][0]["attrs"]["text"] == "default header"

    assert content["type"] == "content"
    assert content["children"][0]["type"] == "label"
    assert content["children"][0]["attrs"]["text"] == "default content"

    assert footer["type"] == "footer"
    assert footer["children"][0]["type"] == "label"
    assert footer["children"][0]["attrs"]["text"] == "default footer"


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

    assert footer["type"] == "footer"
    assert footer["children"][0]["type"] == "label"
    assert footer["children"][0]["attrs"]["text"] == "footer content"
