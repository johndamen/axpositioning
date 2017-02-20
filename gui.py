from collections import OrderedDict
import subprocess
import sys
import pickle
from functools import partial
from matplotlib.figure import Figure
from matplotlib.gridspec import GridSpec
import warnings

# try PyQt5, otherwise use PyQt4
try:
    from PyQt5 import QtWidgets, QtCore
    from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
except ImportError as e:
    warnings.warn('Could not import PyQt5, attempting PyQt4', ImportWarning)
    from PyQt4 import QtGui as QtWidgets, QtCore
    from matplotlib.backends.backend_qt4agg import FigureCanvasQTAgg as FigureCanvas

from .axpositioning import PositioningAxes


def hline():
    f = QtWidgets.QFrame()
    f.setFrameShape(QtWidgets.QFrame.HLine)
    f.setFrameShadow(QtWidgets.QFrame.Sunken)
    return f


class AxPositioningEditor(QtWidgets.QWidget):
    """
    main widget for editing axes positions

    Example:
    >>>from matplotlib import pyplot as plt
    >>>fig = plt.figure()
    >>>w, h = fig.get_size_inches()
    >>>AxPositioningEditor((w, h), bounds=[])

    """

    position_dict = OrderedDict([
        ('ll', 'lower left'),
        ('ul', 'upper left'),
        ('ur', 'upper right'),
        ('lr', 'lower right'),
        ('c', 'center')])

    click_axes_data = dict(w=.3, h=.3)

    def __init__(self, figsize, bounds=(), dpi=None):
        super().__init__()
        self.anchor = 'c'

        w, h = figsize
        self.figure = Figure(figsize=(w, h))

        if dpi is None:
            dpi = 800 / max(w, h)
            self.figure.set_dpi(dpi)

        self.set_axes(bounds, reset=True, draw=False)
        self.build()
        self.canvas.mpl_connect('button_release_event', self.draw_axes)
        self.pointing_axes = False

    def build(self):
        """build the widget"""
        self.setMinimumWidth(600)
        self.setMinimumHeight(350)
        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)
        content_layout = QtWidgets.QHBoxLayout()
        content_layout.setContentsMargins(0, 0, 0, 0)
        layout.addLayout(content_layout)

        self.build_figure(content_layout)
        self.build_tools(content_layout)

        self.msg_label = QtWidgets.QLabel()
        self.msg_label.setContentsMargins(5, 5, 5, 5)
        layout.addWidget(self.msg_label)

        self.draw()

        self.set_message(None)

    def build_figure(self, layout):
        """build the figure area"""
        figure_scroll_area = QtWidgets.QScrollArea()

        self.canvas = FigureCanvas(self.figure)
        figure_scroll_area.setWidget(self.canvas)
        layout.addWidget(figure_scroll_area)

    def build_tools(self, layout):
        """build the tools area"""

        tools_widget = QtWidgets.QTabWidget()
        tools_widget.setFixedWidth(330)
        layout.addWidget(tools_widget)

        aw = QtWidgets.QWidget()
        anchor_layout = QtWidgets.QVBoxLayout(aw)
        radio_set = QtWidgets.QButtonGroup()
        radio_set.setExclusive(True)
        for pos, name in self.position_dict.items():
            w = QtWidgets.QRadioButton(name)
            if pos == self.anchor:
                w.setChecked(True)
            w.clicked.connect(partial(self.update_anchor, pos))
            radio_set.addButton(w)
            anchor_layout.addWidget(w)
        anchor_layout.addItem(QtWidgets.QSpacerItem(
            0, 0,
            QtWidgets.QSizePolicy.Maximum,
            QtWidgets.QSizePolicy.Expanding))
        tools_widget.addTab(aw, 'Anchors')

        w = QtWidgets.QWidget()
        layout = QtWidgets.QVBoxLayout(w)
        clear_all_button = QtWidgets.QPushButton('Clear all')
        clear_all_button.clicked.connect(self.clear_all)
        layout.addWidget(clear_all_button)
        self.axtable = AxesPositionsWidget(self.axes)
        self.axtable.changed.connect(self.set_ax_position)
        self.axtable.deleted.connect(self.delete_axes)
        layout.addWidget(self.axtable)
        tools_widget.addTab(w, 'Positions')

        w = AddAxesWidget(self.figure)
        w.newbounds.connect(self.set_axes)
        w.axes_added.connect(lambda x: self.add_axes_at_position(**x))
        w.click_axes.connect(self.click_new_axes)
        tools_widget.addTab(w, 'Add axes')

    def get_bounds(self):
        """returns a list of axes bounds as [(x, y, w, h)]"""
        bounds = []
        for n, a in self.axes.items():
            bounds.append(a.bounds)
        return bounds

    def draw_axes(self, event):
        """create an axes at the click location if self.pointing_axes is enabled"""
        if self.pointing_axes:
            x, y = self.figure.transFigure.inverted().transform((event.x, event.y))
            print('drawing at', x, y, file=sys.stderr)
            self.add_axes_at_position(x, y, **self.click_axes_data)
            self.pointing_axes = False
            # clear the message widget
            self.set_message(None)

    def click_new_axes(self, data):
        self.pointing_axes = True
        self.click_axes_data = data

    def add_axes_at_position(self, x, y, w=.4, h=.4, n=None, draw=True):
        """add axes at specified location in Figure coordinates"""

        if n is None:
            n = self.next_axes_name()

        self.axes[n] = PositioningAxes.from_position(
            self.figure, x, y, w, h, anchor=self.anchor)

        if draw:
            self.draw(posfields=True)

    def add_axes(self, bounds, n=None, draw=True):
        """
        add an axes from specified bounds
        :param bounds: bounds as (x, y, w, h)
        :param n: name of the axes
        """
        if n is None:
            n = self.next_axes_name()

        self.axes[n] = PositioningAxes(self.figure, bounds, anchor=self.anchor)

        if draw:
            self.draw(posfields=True)

    def set_axes(self, bounds, reset=False, draw=True):
        """set several axes from a list of bounds"""
        if reset:
            self.axes = OrderedDict()

        for bnd in bounds:
            self.add_axes(bnd, draw=False)

        if draw:
            self.draw(posfields=True)

    def next_axes_name(self):
        """generate a new unique axes name"""
        axnames = list(self.axes.keys())
        for i in range(50):
            n = chr(65 + i)
            if n not in axnames:
                return n
        raise ValueError('could not find unique axis name')

    def clear_all(self):
        self.figure.clear()
        for k in list(self.axes.keys()):
            self.delete_axes(k, redraw=False)
        self.draw(posfields=True)

    def set_ax_position(self, axname, attr, value):
        """
        set the position of an axes from the attribute name
        :param axname: name of the axes
        :param attr: name of the position attribute
        :param value: value of the position attribute
        """
        ax = self.axes[str(axname)]
        setattr(ax, str(attr), value)
        self.draw(posfields=True)

    def set_message(self, msg, level='INFO'):
        """
        set a message in the message window
        hide the messages if msg is None
        :param msg: message text
        :param level: level (see logging levels) of the message
        """
        if msg is None:
            self.msg_label.setText('')
            self.msg_label.hide()
        else:
            self.msg_label.show()

        styles = dict(
            DEBUG='background-color: rgb(100, 250, 100)',
            INFO='',
            WARNING='background-color: rgb(250, 230, 150)',
            ERROR='background-color: rgb(255, 150, 100)',
        )
        self.msg_label.setStyleSheet(styles[level])
        self.msg_label.setText(msg)

    def add_message(self, msg):
        """add to the end of the message (keep formatting)"""
        txt = self.msg_label.text()
        self.msg_label.setText(txt+'\n'+msg)

    def draw(self, posfields=False):
        """redraw the contents"""
        self.figure.clear()
        for name, a in self.axes.items():
            a.format_placeholder(name)
            self.figure.add_axes(a)
        self.canvas.draw_idle()

        if posfields:
            self.axtable.clear()
            self.axtable.fill(self.axes)

    def update_anchor(self, pos, clicked):
        """set the position reference anchor of the axes to a new location"""
        if clicked:
            for name, a in self.axes.items():
                a.set_anchor_point(pos)
                self.anchor = pos
        self.draw(posfields=True)

    def delete_axes(self, name, redraw=True):
        """delete an axes from the editor"""
        self.axes.pop(str(name))
        if redraw:
            self.draw(posfields=True)


class AxesPositionsWidget(QtWidgets.QTableWidget):

    """
    table of axes positions

    signals:
    - changed(axes_name, attr_name, value)
    - deleted(axes_name)
    """

    changed = QtCore.pyqtSignal(str, str, object)
    deleted = QtCore.pyqtSignal(str)

    def __init__(self, axes):
        super().__init__()
        self.build()
        self.fill(axes)

    def build(self):
        pass

    def fill(self, axes):
        """fill the table based on the given axes position objects"""
        headers = ['X', 'Y', 'Width', 'Height', 'Aspect', 'Actions']
        widths = [45, 45, 45, 45, 45, 50]
        self.setColumnCount(len(headers))
        self.setShowGrid(False)
        for i, w in enumerate(widths):
            self.setColumnWidth(i, w)
        self.setHorizontalHeaderLabels(headers)

        self.setRowCount(len(axes))
        names = []
        for i, (k, v) in enumerate(axes.items()):
            for j, attr in enumerate(('x', 'y', 'w', 'h', 'aspect')):
                f = FloatField(getattr(v, attr))
                f.changed.connect(partial(self.changed.emit, k, attr))
                self.setCellWidget(i, j, f)

            self.delete_button = QtWidgets.QPushButton('x')
            self.delete_button.setFlat(True)
            self.delete_button.clicked.connect(partial(self.deleted.emit, k))
            self.setCellWidget(i, j+1, self.delete_button)

            names.append(k)
        self.setVerticalHeaderLabels(names)


class NumField(QtWidgets.QLineEdit):

    changed = QtCore.pyqtSignal(int)
    error = QtCore.pyqtSignal(str)

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
            content = self.text()
            try:
                self.val = self.cast(content)
            except ValueError as e:
                self.set_value(self.last_valid)
                self.error.emit('invalid value: {!r}'.format(content))

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
            if ':' in v:
                if ',' in v:
                    raise ValueError('cannot combine range with individual items')
                start, end = v.split(':', 1)
                return tuple(range(IntField.cast(self, start.strip()),
                                   IntField.cast(self, end.strip())))
            else:
                return tuple(IntField.cast(self, v.strip()) for v in v.split(','))
        else:
            raise ValueError('invalid value type {}'.format(type(v)))


class FloatField(NumField):

    changed = QtCore.pyqtSignal(float)

    def __init__(self, v, fmt='{:.3f}', **kw):
        self.fmt = fmt
        super().__init__(v, **kw)

    def format(self, v):
        return self.fmt.format(v)

    def cast(self, v):
        return float(v)


class AddAxesWidget(QtWidgets.QWidget):

    VALUES = dict(
        nrows=1,
        ncols=1,
        index=(0,),
        left=0.1,
        right=0.9,
        bottom=0.1,
        top=0.9,
        hspace=0.05,
        wspace=0.05,

        pos_width=0.4,
        pos_height=0.4,
        pos_x=.5,
        pos_y=.5
    )

    newbounds = QtCore.pyqtSignal(list)
    axes_added = QtCore.pyqtSignal(dict)
    click_axes = QtCore.pyqtSignal(dict)

    def __init__(self, figure):
        super().__init__()
        self.figure = figure

        self.layout = QtWidgets.QVBoxLayout(self)
        self.build_posform()
        self.layout.addWidget(hline())
        self.build_gridform()

        self.layout.addItem(QtWidgets.QSpacerItem(
            0, 0,
            QtWidgets.QSizePolicy.Maximum,
            QtWidgets.QSizePolicy.Expanding))

    def build_gridform(self):
        layout = QtWidgets.QHBoxLayout()
        self.layout.addLayout(layout)
        self.layout.setContentsMargins(0, 0, 0, 0)

        gridform_left = QtWidgets.QFormLayout()
        gridform_left.setSpacing(3)
        layout.addLayout(gridform_left)

        gridform_right = QtWidgets.QFormLayout()
        gridform_right.setSpacing(3)
        layout.addLayout(gridform_right)

        self.gridfields = dict()

        self.gridfields['nrows'] = f = IntField(self.VALUES['nrows'])
        gridform_left.addRow('rows', f)

        self.gridfields['ncols'] = f = IntField(self.VALUES['ncols'])
        gridform_left.addRow('columns', f)

        self.gridfields['index'] = f = MultiIntField(self.VALUES['index'])
        gridform_left.addRow('indices', f)

        self.all_checkbox = f = QtWidgets.QCheckBox('all')
        f.stateChanged.connect(self.checked_all)
        f.setChecked(False)
        gridform_left.addRow('', f)


        self.gridfields['left'] = f = FloatField(self.VALUES['left'])
        gridform_right.addRow('left', f)

        self.gridfields['bottom'] = f = FloatField(self.VALUES['bottom'])
        gridform_right.addRow('bottom', f)

        self.gridfields['right'] = f = FloatField(self.VALUES['right'])
        gridform_right.addRow('right', f)

        self.gridfields['top'] = f = FloatField(self.VALUES['top'])
        gridform_right.addRow('top', f)

        self.gridfields['wspace'] = f = FloatField(self.VALUES['wspace'])
        gridform_right.addRow('wspace', f)

        self.gridfields['hspace'] = f = FloatField(self.VALUES['hspace'])
        gridform_right.addRow('hspace', f)

        button_layout = QtWidgets.QHBoxLayout()
        self.layout.addLayout(button_layout)

        self.grid_button = QtWidgets.QPushButton('Add from grid')
        self.grid_button.setFixedWidth(200)
        self.grid_button.clicked.connect(self.add_from_grid)
        button_layout.addWidget(self.grid_button)

    def build_posform(self):
        layout = QtWidgets.QHBoxLayout()
        self.layout.addLayout(layout)
        self.layout.setContentsMargins(0, 0, 0, 0)

        posform_left = QtWidgets.QFormLayout()
        posform_left.setSpacing(3)
        layout.addLayout(posform_left)

        posform_right = QtWidgets.QFormLayout()
        posform_right.setSpacing(3)
        layout.addLayout(posform_right)


        self.posfields = dict()

        self.posfields['w'] = f = FloatField(self.VALUES['pos_width'])
        posform_left.addRow('width', f)

        self.posfields['h'] = f = FloatField(self.VALUES['pos_height'])
        posform_left.addRow('height', f)

        self.posfields['x'] = f = FloatField(self.VALUES['pos_x'])
        posform_right.addRow('x', f)

        self.posfields['y'] = f = FloatField(self.VALUES['pos_y'])
        posform_right.addRow('y', f)


        button_layout = QtWidgets.QHBoxLayout()
        self.layout.addLayout(button_layout)

        self.pos_button = QtWidgets.QPushButton('Add')
        self.pos_button.clicked.connect(self.add_at_pos)
        button_layout.addWidget(self.pos_button)

        self.click_button = QtWidgets.QPushButton('Click in figure')
        self.click_button.clicked.connect(self.add_at_click)
        button_layout.addWidget(self.click_button)

    def checked_all(self, b):
        if b:
            self.gridfields['index'].setDisabled(True)
        else:
            self.gridfields['index'].setDisabled(False)

    def add_at_pos(self):
        data = dict(w=self.posfields['w'].value(),
                    h=self.posfields['h'].value(),
                    x=self.posfields['x'].value(),
                    y=self.posfields['y'].value())
        print(data)
        self.axes_added.emit(data)

    def add_at_click(self):
        data = dict(w=self.posfields['w'].value(),
                    h=self.posfields['h'].value())
        print(data)
        self.click_axes.emit(data)

    def add_from_grid(self):
        data = dict()
        for k, f in self.gridfields.items():
            try:
                v = f.value()
            except ValueError as e:
                msg = QtWidgets.QMessageBox()
                msg.setText('Invalid value for {}: {}'.format(k, e))
                msg.exec()
                return
            self.VALUES[k] = v
            if k in ('nrows', 'ncols', 'left', 'right', 'top', 'bottom', 'wspace', 'hspace'):
                data[k] = v

        gs = GridSpec(**data)
        bounds = []

        if self.all_checkbox.isChecked():
            I = tuple(range(data['nrows'] * data['ncols']))
        else:
            I = self.gridfields['index'].value()

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
                bounds.append(bnd)
        else:
            raise TypeError('invalid index type')

        self.newbounds.emit(bounds)


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
    w = AxPositioningEditor(figsize, bounds, **kwargs)
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

    newbounds = position_axes_gui_subprocess(fig.get_size_inches(), bounds)

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

    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument('--width', '-W', default=8, type=float)
    parser.add_argument('--height', '-H', default=6, type=float)
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

