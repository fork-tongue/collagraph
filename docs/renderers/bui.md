# BUI Renderer

The `BuiRenderer` maps template tags to the components of
[BUI](https://github.com/ppmpreetham/BUI): Blender's user interface as a
standalone library. Every element is a node of BUI's C kit, so layout, input
handling and drawing all follow Blender's look and interaction rules (drag
number fields to scrub them, type `2*pi` into a number field, Ctrl+Z, ...).

!!! note
    BUI (the `blenderui` package) is licensed under GPL-2.0-or-later.

## Setup

```sh
pip install collagraph[bui]
```

## Running

```sh
uv run collagraph --renderer bui examples/bui/counter.cgx
```

Or programmatically:

```python
import collagraph as cg

renderer = cg.BuiRenderer()
gui = cg.Collagraph(renderer=renderer)
gui.render(MyComponent, None)
renderer.run()  # Runs BUI's event loop until all windows are closed
```

Every top-level element opens in its own window. Use a `<window>` element to
control the title and size of the window; any other top-level element is
wrapped in a default window:

```html
<window title="Counter" :size="(300, 160)">
  <label>Count: {{ count }}</label>
  <row>
    <button @click="bump">Bump</button>
    <button @click="reset" :enabled="count > 0">Reset</button>
  </row>
</window>
```

## Available Elements

Tags map to the classes in `blenderui.components` (case-insensitive, hyphens
and underscores removed), so `<number-slider>`, `<numberslider>` and
`<NumberSlider>` all create a `NumberSlider`:

| Tag | Component |
|-----|-----------|
| `<window>` | Top-level window (a column) with `title` and `size` |
| `<column>`, `<row>`, `<box>`, `<grid>`, `<split>` | Layouts |
| `<panel>` | Collapsible panel (use the `title` attribute) |
| `<tabs>`, `<side-tabs>`, `<sidebar>`, `<scroll-view>` | Containers |
| `<label>`, `<separator>`, `<spacer>`, `<progress-bar>` | Static widgets |
| `<button>`, `<icon-button>`, `<toggle>`, `<checkbox>` | Buttons and booleans |
| `<number-field>`, `<number-slider>`, `<vector-field>` | Numbers |
| `<text-field>`, `<search-field>`, `<hotkey-field>` | Text |
| `<dropdown>`, `<enum-row>`, `<color-swatch>` | Choices and colors |

Most other components (views, menus, editors) are available as well. Some
short aliases are available too: `<number>`, `<slider>`, `<enum>`,
`<progress>`, `<scroll>` and `<swatch>`.

Custom components can be registered with `register_element`:

```python
from blenderui import components as bc


@cg.BuiRenderer.register_element("fancy-row")
class FancyRow(bc.Row): ...
```

## Attributes

Attributes are set as Python properties of the component when it has one
(`text`, `label`, `value`, `enabled`, `visible`, `items`, `collapsed`, ...),
and otherwise as properties of the kit node (`min`, `max`, `step`, `icon`,
`bold`, `text_align`, `padding`, `spacing`, `rows`, ...). Kebab-case
attribute names are converted to snake case.

```html
<number-slider label="Scale" :value="scale" :min="0" :max="10" />
<label text="Title" bold text-align="center" />
```

Setting `value` from a template does not emit a `change` event.

## Text Content

Text inside an element sets its text: the `text` of labels, buttons and
progress bars, or the `label` of value components such as checkboxes:

```html
<label>Count: {{ count }}</label>
<checkbox :value="smooth">Smooth</checkbox>
```

## Events

Event names map to the `on_<event>` callbacks of the components:

```html
<button @click="apply" />
<number-slider @change="set_scale" />  <!-- called with the new value -->
<panel @toggle="on_toggle" />           <!-- called with the collapsed state -->
<window @close="on_close" />            <!-- return False to keep the window open -->
```

## Headless Rendering

With `BuiRenderer(headless=True)`, no windows are opened. The top-level
windows are available as `renderer.windows`; each has a kit context (`ctx`)
that can be driven with input, and a `render()` method that renders it into a
`buipy.Raster`. This is useful for tests and screenshots:

```python
renderer = cg.BuiRenderer(headless=True)
gui = cg.Collagraph(renderer=renderer, event_loop_type=cg.EventLoopType.SYNC)
gui.render(Counter, None)

window = renderer.windows[0]
window.render()  # Lays out the window
label, row = window.children
x, y, w, h = row.children[0].rect
window.ctx.press(x + w // 2, y + h // 2, 0)
window.ctx.release(x + w // 2, y + h // 2, 0)
assert label.text == "Count: 1"
```

## Event Loop

BUI runs its own event loop (a native window, or a Tk window). The renderer
schedules the updates of collagraph on that loop, so multiple state changes
are batched into a single update. Hot reloading is not supported with this
renderer yet.

## Examples

```sh
uv run collagraph --renderer bui examples/bui/counter.cgx
uv run collagraph --renderer bui examples/bui/properties.cgx
```
