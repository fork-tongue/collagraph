# PySide6 Renderer

The `PySideRenderer` maps template tags to [PySide6](https://doc.qt.io/qtforpython-6/) (Qt for Python) widgets.

## Setup

```sh
pip install collagraph[pyside]
```

```python
import collagraph as cg
from PySide6 import QtWidgets

app = QtWidgets.QApplication()
gui = cg.Collagraph(renderer=cg.PySideRenderer())
gui.render(MyComponent, app)
app.exec()
```

## Available Elements

Template tags map to Qt widget classes. There are common short names available:

| Tag | Qt Class |
|-----|----------|
| `<window>` | `QMainWindow` |
| `<widget>` | `QWidget` |
| `<button>` | `QPushButton` |
| `<label>` | `QLabel` |
| `<lineedit>` | `QLineEdit` |
| `<textedit>` | `QTextEdit` |
| `<checkbox>` | `QCheckBox` |
| `<radiobutton>` | `QRadioButton` |
| `<combobox>` | `QComboBox` |
| `<slider>` | `QSlider` |
| `<spinbox>` | `QSpinBox` |
| `<progressbar>` | `QProgressBar` |
| `<groupbox>` | `QGroupBox` |
| `<tabwidget>` | `QTabWidget` |
| `<scrollarea>` | `QScrollArea` |
| `<dock>` | `QDockWidget` |
| `<toolbar>` | `QToolBar` |
| `<menubar>` | `QMenuBar` |
| `<menu>` | `QMenu` |
| `<action>` | `QAction` |
| `<statusbar>` | `QStatusBar` |
| `<treeview>` | `QTreeView` |
| `<treewidget>` | `QTreeWidget` |
| `<treewidgetitem>` | `QTreeWidgetItem` |
| `<dialogbuttonbox>` | `QDialogButtonBox` |

### Name Lookup from Qt Modules

Beyond the short names above, you can use **any class** from `QtWidgets`, `QtGui`, `QtCore`, or `QtCore.Qt` directly by name. Tag names in templates must be lower-case (the lookup is case-insensitive):

```html
<qlabel :text="content" />
<qcalendarwidget @selection_changed="on_date" />
```

You can also use dot notation for nested types:

```html
<widget :layout="{'type': 'QBoxLayout.Direction.TopToBottom'}" />
```

This means you rarely need to call `register_element()` -- most Qt classes are available out of the box.

## Attributes

Attributes map to setter methods on the Qt widget. The attribute name is converted from kebab-case to the appropriate Qt method:

```html
<label text="Hello" />        <!-- calls setText("Hello") -->
<window title="My App" />     <!-- calls setWindowTitle("My App") -->
<button enabled="false" />    <!-- calls setEnabled(False) -->
```

Dynamic attributes use Python expressions:

```html
<label :text="f'Count: {count}'" />
<slider :value="self.state['position']" />
```

## Layouts

Child widgets are laid out using layout elements:

```html
<widget layout="hbox">      <!-- QHBoxLayout -->
  <button text="Left" />
  <button text="Right" />
</widget>

<widget layout="vbox">      <!-- QVBoxLayout -->
  <label text="Top" />
  <label text="Bottom" />
</widget>

<widget layout="grid">      <!-- QGridLayout -->
  <label text="A" row="0" column="0" />
  <label text="B" row="0" column="1" />
</widget>

<widget layout="form">      <!-- QFormLayout -->
  <label text="Name:" />
  <lineedit />
</widget>
```

## Events

Events map to Qt signals. Use the signal name in snake_case:

```html
<button @clicked="handle_click" />
<lineedit @text_edited="handle_text" />
<slider @value_changed="handle_value" />
<combobox @current_index_changed="handle_index" />
```

## Registering Custom Elements

You can register additional Qt classes:

```python
from PySide6 import QtWidgets
from collagraph.renderers.pyside_renderer import PySideRenderer

PySideRenderer.register_element("calendar", QtWidgets.QCalendarWidget)
```

Then use in templates:

```html
<calendar @selection_changed="on_date" />
```
