from PyQt5 import QtGui, QtCore, QtWidgets
from matplotlib.figure import Figure
from matplotlib.gridspec import GridSpec
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from collections import OrderedDict
from functools import partial
import subprocess
import sys
import argparse
import pickle


from .axpositioning import *


"""
Gui elements

- AxpositioningEditor
- AxPositionFieldBox
...
"""


class AxPositioningEditor(QtWidgets.QMainWindow):

    position_dict = OrderedDict([
        ('ll', 'lower left'),
        ('ul', 'upper left'),
        ('ur', 'upper right'),
        ('lr', 'lower right'),
        ('c', 'center')])

    @classmethod
    def from_figaspect(cls, aspect, bounds=()):
        fig = Figure(figsize=(6, 6/aspect))
        return cls(fig, bounds=bounds)

    @classmethod
    def create_shape(cls, m, n, fig=None, figsize=None, figaspect=None):
        if fig is None:
            fig = Figure(figsize=figsize or (6, 6/(figaspect or 1)))

        bounds = []
        margin = .05
        boxmargin = .05
        bw = (1 - 2 * margin) / n
        bh = (1 - 2 * margin) / m
        for i in range(m): # rows
            for j in range(n): # cols
                bounds.append((margin + j * bw + boxmargin,
                               margin + i * bh + boxmargin,
                               bw - 2 * boxmargin,
                               bh - 2 * boxmargin))
        return cls(fig, bounds=bounds)


    def __init__(self, fig, bounds=()):
        super().__init__()
        self.anchor = 'c'
        w, h = fig.get_size_inches()
        self.figure = fig
        self.canvas = FigureCanvas(self.figure)
        self.canvas.setFixedSize(400, 400 / (w / h))

        self.canvas.mpl_connect('button_release_event', self.draw_axes)
        self.pointing_axes = False

        self.create_axes(bounds)
        self.build()

    def get_bounds(self):
        bounds = []
        for n, a in self.axes.items():
            bounds.append(a.bounds)
        return bounds

    def pycode_bounds(self):
        boundstr = ''
        for n, a in self.axes.items():
            kwargs = dict(zip(['xll', 'yll', 'w', 'h'], a.bounds), name=n)
            boundstr += '    ({xll:.3f}, {yll:.3f}, {w:.3f}, {h:.3f})  # {name}\n'.format(**kwargs)
        return 'bounds = [\n'+boundstr+']'

    def draw_axes(self, event):
        if self.pointing_axes:
            x, y = self.figure.transFigure.inverted().transform((event.x, event.y))
            self.add_axes_at_position(x, y)
            self.pointing_axes = False

    def build(self):
        w = QtWidgets.QWidget()
        self.setCentralWidget(w)
        self.layout = QtWidgets.QHBoxLayout(w)
        self.layout.setSpacing(5)

        canvas_layout = QtWidgets.QVBoxLayout()
        self.layout.addLayout(canvas_layout)
        canvas_layout.addWidget(self.canvas)
        canvas_layout.addItem(QtWidgets.QSpacerItem(
            0, 0, QtWidgets.QSizePolicy.Maximum, QtWidgets.QSizePolicy.Expanding))

        self.edit_axes_layout = QtWidgets.QVBoxLayout()
        self.layout.addLayout(self.edit_axes_layout)

        self.layout.addItem(QtWidgets.QSpacerItem(0, 0, QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Maximum))

        self.position_group = QtWidgets.QGroupBox()
        self.edit_axes_layout.addWidget(self.position_group)
        group_layout = QtWidgets.QVBoxLayout(self.position_group)
        radio_buttons = dict()
        for pos, name in self.position_dict.items():
            radio_buttons[pos] = rw = QtWidgets.QRadioButton(name)
            rw.clicked.connect(partial(self.update_anchor, pos))
            group_layout.addWidget(rw)

        self.axfields = AxPositionFieldBox(self.axes)
        self.axfields.setFixedWidth(400)
        self.axfields.changed.connect(self.draw)
        self.axfields.deleted.connect(self.delete_axes)
        self.edit_axes_layout.addWidget(self.axfields)

        self.add_axes_button = AddAxesButton()
        self.add_axes_button.setFlat(True)
        self.add_axes_button.clicked.connect(self.add_axes_clicked)
        self.edit_axes_layout.addWidget(self.add_axes_button)

        self.edit_axes_layout.addItem(QtWidgets.QSpacerItem(
            0, 0, QtWidgets.QSizePolicy.Maximum, QtWidgets.QSizePolicy.Expanding))

        radio_buttons[self.anchor].click()

    def add_axes_clicked(self):
        w = NewAxesDialog(self.figure)
        w.show()
        w.exec()
        data = w.value.copy()
        w.deleteLater()
        self.pointing_axes = data.pop('click', False)
        try:
            for bnd in data['bounds']:
                self.add_axes(bnd)
        except KeyError:
            pass

    def add_axes_at_position(self, x, y):
        return self.add_axes([x - .2, y - .2, .4, .4])

    def add_axes(self, bounds, n=None):
        if n is None:
            axnames = list(self.axes.keys())
            for i in range(50):
                n = chr(65 + i)
                if n not in axnames:
                    break
            else:
                raise ValueError('could not find unique axis name')

        self.axes[n] = PositioningAxes(self.figure, bounds, anchor=self.anchor)
        self.draw(posfields=True)

    def update_anchor(self, pos, clicked):
        if clicked:
            for name, a in self.axes.items():
                a.set_anchor_point(pos)
                self.anchor = pos
        self.draw()
        self.axfields.update_fields()

    def create_axes(self, bounds):
        self.axes = OrderedDict()
        for i, bnd in enumerate(bounds):
            a = PositioningAxes(self.figure, bnd, anchor=self.anchor)
            self.axes[chr(65 + i)] = a

        self.draw()

    def draw(self, posfields=False):
        self.figure.clear()
        for name, a in self.axes.items():
            a.format_placeholder(name)
            self.figure.add_axes(a)
        self.canvas.draw_idle()

        if posfields:
            self.axfields.clear()
            self.axfields.fill()

    def delete_axes(self, axeditor):
        self.axfields.clear()
        self.axes.pop(axeditor.name)
        axeditor.deleteLater()
        self.axfields.fill(self.axes)
        self.draw()


class AxPositionFieldBox(QtWidgets.QGroupBox):

    changed = QtCore.pyqtSignal()
    deleted = QtCore.pyqtSignal(object)

    def __init__(self, axes):
        super().__init__()
        if not isinstance(axes, dict):
            raise TypeError('axes not a dict instance')
        self.axes = axes
        self.axfields = dict()

        self.layout = QtWidgets.QVBoxLayout(self)
        self.layout.setSpacing(5)
        self.layout.setContentsMargins(0, 0, 0, 0)

        self.fill()

    def clear(self):
        """
        clear all content from the position fields
        refill using .fill(axes) method
        """
        for i in reversed(range(self.layout.count())):
            w = self.layout.itemAt(i).widget()
            w.setParent(None)
            w.deleteLater()
        assert self.layout.count() == 0
        self.axes = OrderedDict()
        self.axfields = dict()

    def fill(self, axes=None):
        """
        fill when empty
        :param axes: list of PositioningAxes objects
        :return:
        """
        if axes is not None:
            self.axes = axes

        for n in sorted(self.axes.keys()):
            a = self.axes[n]
            self.axfields[n] = w = AxPositionField(n, a)
            w.changed.connect(self.changed.emit)
            w.deleted.connect(self.deleted.emit)
            self.layout.addWidget(w)

    def update_fields(self):
        for name, f in self.axfields.items():
            f.update_fields()


class AddAxesButton(QtWidgets.QPushButton):

    def __init__(self):
        super().__init__('Add new axes')
        self.setFlat(True)


class AxPositionField(QtWidgets.QWidget):

    """
    Widget class for editing PositioningAxes fields
    """

    changed = QtCore.pyqtSignal()
    deleted = QtCore.pyqtSignal(object)

    def __init__(self, name, a):
        if not isinstance(a, PositioningAxes):
            raise TypeError('invalid axes type; not an instance of AxesPositioner')
        self.name = name
        self.ax = a
        super().__init__()
        self.build()

    def build(self):
        self.layout = QtWidgets.QHBoxLayout(self)
        self.layout.setSpacing(5)
        self.layout.setContentsMargins(0, 0, 0, 0)
        label = QtWidgets.QLabel(self.name+': ')
        self.layout.addWidget(label)

        self.fields = dict()
        for n in 'xywh':
            self.fields[n] = f = LabeledFloatField(n, getattr(self.ax, n))
            f.changed.connect(partial(self.update_axes_pos, n))
            self.layout.addWidget(f)

        self.fields['aspect'] = f = LabeledFloatField('A', self.ax.aspect)
        f.changed.connect(partial(self.update_axes_aspect, 'aspect'))
        self.layout.addWidget(f)

        self.delete_button = QtWidgets.QPushButton('x')
        self.delete_button.setFlat(True)
        self.delete_button.clicked.connect(self.delete_axes)
        self.layout.addWidget(self.delete_button)

    def delete_axes(self):
        self.deleted.emit(self)

    def update_axes_aspect(self, n, v):
        self.ax.set_aspect_ratio(v)
        self.update_fields()
        self.changed.emit()

    def update_axes_pos(self, n, v):
        setattr(self.ax, n, v)
        self.update_fields()
        self.changed.emit()

    def update_fields(self):
        for n, f in self.fields.items():
            f.set_value(getattr(self.ax, n))

    def deleteLater(self):
        for i in reversed(range(self.layout.count())):
            w = self.layout.itemAt(i).widget()
            w.setParent(None)
            w.deleteLater()


class NumField(QtWidgets.QLineEdit):

    changed = QtCore.pyqtSignal(int)

    def __init__(self, v, width=45):
        super().__init__()
        self.val = self.cast(v)
        self.set_value(v)
        self.setFixedWidth(width)
        self.editingFinished.connect(self.check_change)
        self.last_valid = self.val

    def cast(self, v):
        return int(v)

    def format(self, v):
        return str(v)

    def check_change(self):
        """
        check if value is changed
        update value and emit changed signal if field text is different from
        the formatted value
        """

        # compare content to value
        if self.text() == self.format(self.val):
            return
        else:
            # update value
            try:
                self.val = self.cast(self.text())
            except ValueError:
                self.set_value(self.last_valid)
                raise

            # emit signal when casting was successful
            self.last_valid = self.val
            self.changed.emit(self.val)

    def value(self):
        """return the value after checking for change"""
        self.check_change()
        return self.val

    def set_value(self, v):
        """set a value as a float and update field"""
        self.val = self.cast(v)
        self.setText(self.format(self.val))


class IntField(NumField):

    castfn = int
    changed = QtCore.pyqtSignal(int)

    def format(self, v):
        return str(v)

class MultiIntField(IntField):

    changed = QtCore.pyqtSignal(tuple)

    def __init__(self, v, width=60):
        super().__init__(v, width=width)

    def format(self, v):
        return ', '.join(map(str, v))

    def cast(self, v):
        if isinstance(v, tuple):
            return v
        elif isinstance(v, str):
            return tuple(IntField.cast(self, v.strip()) for v in v.split(','))
        else:
            raise ValueError('invalid value type {}'.format(type(v)))


class FloatField(NumField):

    fmt = '{:.3f}'
    changed = QtCore.pyqtSignal(float)

    def __init__(self, v, fmt=None, **kw):
        super().__init__(v, **kw)
        if fmt is not None:
            self.fmt = fmt

    def format(self, v):
        return self.fmt.format(v)

    def cast(self, v):
        return float(v)


class LabeledFloatField(QtWidgets.QWidget):

    changed = QtCore.pyqtSignal(float)

    def __init__(self, name, v, **kwargs):
        super().__init__()
        l = QtWidgets.QHBoxLayout(self)
        l.setSpacing(3)
        l.setContentsMargins(0, 0, 0, 0)
        self.label = QtWidgets.QLabel(name)
        l.addWidget(self.label)
        self.value_field = FloatField(v, **kwargs)
        l.addWidget(self.value_field)
        self.value_field.changed.connect(self.changed.emit)

    def value(self):
        return self.value_field.value()

    def set_value(self, v):
        return self.value_field.set_value(v)

    def deleteLater(self):
        self.value_field.deleteLater()
        self.label.deleteLater()
        super().deleteLater()


class NewAxesDialog(QtWidgets.QDialog):

    FIELD_SPEC = OrderedDict()
    FIELD_SPEC['nrows']  = dict(cls=IntField, value=1)
    FIELD_SPEC['ncols']  = dict(cls=IntField, value=1)
    FIELD_SPEC['index']    = dict(cls=MultiIntField, value=(0,))
    FIELD_SPEC['left']   = dict(cls=FloatField, value=0.1)
    FIELD_SPEC['bottom'] = dict(cls=FloatField, value=0.1)
    FIELD_SPEC['right']  = dict(cls=FloatField, value=0.9)
    FIELD_SPEC['top']    = dict(cls=FloatField, value=0.9)
    FIELD_SPEC['wspace'] = dict(cls=FloatField, value=0.05)
    FIELD_SPEC['hspace'] = dict(cls=FloatField, value=0.05)

    def __init__(self, figure):
        super().__init__()
        self.layout = QtWidgets.QVBoxLayout(self)
        self.click_button = QtWidgets.QPushButton('Click in axes')
        self.click_button.clicked.connect(self.click_axes)
        self.layout.addWidget(self.click_button)

        hline = QtWidgets.QFrame()
        hline.setFrameShape(QtWidgets.QFrame.HLine)
        hline.setFrameShadow(QtWidgets.QFrame.Sunken)
        self.layout.addWidget(hline)

        gridform = QtWidgets.QFormLayout()
        self.fields = dict()
        for k, spec in self.FIELD_SPEC.items():
            self.fields[k] = f = spec['cls'](spec['value'])
            gridform.addRow(k, f)
        self.layout.addLayout(gridform)

        hline = QtWidgets.QFrame()
        hline.setFrameShape(QtWidgets.QFrame.HLine)
        hline.setFrameShadow(QtWidgets.QFrame.Sunken)
        self.layout.addWidget(hline)

        self.grid_button = QtWidgets.QPushButton('Add from grid')
        self.grid_button.clicked.connect(self.add_from_grid)
        self.layout.addWidget(self.grid_button)

        self.figure = figure
        self.value = dict()

    def click_axes(self):
        self.value['click'] = True
        self.accept()

    def add_from_grid(self):
        data = dict()
        for k, f in self.fields.items():
            try:
                v = f.value()
            except ValueError as e:
                msg = QtWidgets.QMessageBox()
                msg.setText('Invalid value for {}: {}'.format(k, e))
                msg.exec()
                return
            self.FIELD_SPEC[k]['value'] = v
            if k in ('nrows', 'ncols', 'left', 'right', 'top', 'bottom', 'wspace', 'hspace'):
                data[k] = v

        gs = GridSpec(**data)
        self.value['bounds'] = []

        I = self.fields['index'].value()
        if isinstance(I, int):
            I = (I,)
        if isinstance(I, tuple):
            for i in I:
                try:
                    bnd = gs[i].get_position(self.figure).bounds
                except IndexError as e:
                    msg = QtWidgets.QMessageBox()
                    msg.setText('Invalid grid index: {}'.format(e))
                    msg.exec()
                    return
                self.value['bounds'].append(bnd)
        else:
            raise TypeError('invalid index type')
        self.accept()


def position_axes_gui(figsize, bounds, **kwargs):
    """
    open gui to set axes positions
    :param figsize: tuple of width and height
    :param bounds: list of axes bounds
    :param kwargs: ...
    :return: list of new bounds
    """
    if isinstance(figsize, Figure):
        figsize = figsize.get_size_inches()
    app = QtWidgets.QApplication([])
    w = AxPositioningEditor(Figure(figsize=figsize), bounds, **kwargs)
    w.show()

    try:
        app.exec()
        return w.get_bounds()
    finally:
        w.deleteLater()


def position_axes_gui_subprocess(figsize, bounds):
    """
    open gui in new subprocess and retrieve the results over stdout
    :param figsize: figure size
    :param bounds: list of axes bounds
    :return: new bounds
    """
    cmd = [sys.executable, '-m', __name__, '--stream-bounds', '-W', str(figsize[0]), '-H', str(figsize[1])]
    p = subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE)
    pickler = pickle.Pickler(p.stdin)
    pickler.dump(bounds)
    p.stdin.close()
    p.wait()
    out = p.stdout.read()

    newbounds = []
    for line in out.decode('utf-8').splitlines():
        if not line:
            continue
        newbounds.append([float(v) for v in line.strip().split(',')])
    return newbounds


def adjust_axes(fig, **kwargs):
    axes = fig.get_axes()
    bounds = [a.get_position().bounds for a in axes]

    newbounds = position_axes_gui_subprocess((8, 6), bounds)

    for a in axes[len(newbounds):]:
        fig.delaxes(a)

    assert len(fig.get_axes()) <= len(newbounds)

    for i, bnd in enumerate(newbounds):
        try:
            ax = axes[i]
        except IndexError:
            ax = fig.add_axes(bnd)
        else:
            ax.set_position(list(bnd))



if __name__ == '__main__':
    """
    this code is used when calling this script from position_axes_gui_subprocess()
    """

    parser = argparse.ArgumentParser()
    parser.add_argument('--width', '-W', default=12, type=int)
    parser.add_argument('--height', '-H', default=8, type=int)
    parser.add_argument('--stream-bounds', dest='stream_bounds', action='store_true')

    kw = vars(parser.parse_args())
    figsize = kw.pop('width'), kw.pop('height')
    if kw.pop('stream_bounds', False):
        bounds = pickle.Unpickler(sys.stdin.buffer).load()
    else:
        bounds = []

    bounds = position_axes_gui(figsize, bounds)
    for bnd in bounds:
        print(','.join(map(str, bnd)))
