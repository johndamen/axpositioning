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

    def __init__(self, figsize, bounds=(), dpi=None):
        super().__init__()
        self.anchor = 'c'

        w, h = figsize
        self.figure = Figure(figsize=(w, h))

        if dpi is None:
            dpi = 800 / w
            self.figure.set_dpi(dpi)

        self.set_axes(bounds)
        self.build()
        self.canvas.mpl_connect('button_release_event', self.draw_axes)
        self.pointing_axes = False

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
            self.add_axes_at_position(x, y)
            self.pointing_axes = False
            # clear the message widget
            self.set_message(None)

    def add_axes_clicked(self):
        """handle clicking the 'Add Axes' button"""

        # open a dialog
        w = NewAxesDialog(self.figure)
        w.show()
        w.exec()
        data = w.value.copy()
        w.deleteLater()

        # enable clicking for new axes if defined
        self.pointing_axes = data.pop('click', False)
        if self.pointing_axes:
            self.set_message('click in the figure to add an axes at that location')

        # create axes from specified bounds
        try:
            for bnd in data['bounds']:
                self.add_axes(bnd)
        except KeyError:
            pass

    def add_axes_at_position(self, x, y):
        """add axes at specified location in Figure coordinates"""
        return self.add_axes([x - .2, y - .2, .4, .4])

    def add_axes(self, bounds, n=None):
        """
        add an axes from specified bounds
        :param bounds: bounds as (x, y, w, h)
        :param n: name of the axes
        """
        if n is None:
            n = self.next_axes_name()

        self.axes[n] = PositioningAxes(self.figure, bounds, anchor=self.anchor)
        self.draw(posfields=True)

    def set_axes(self, bounds):
        """set several axes from a list of bounds"""
        self.axes = OrderedDict()
        for bnd in bounds:
            name = self.next_axes_name()
            a = PositioningAxes(self.figure, bnd, anchor=self.anchor)
            self.axes[name] = a

    def next_axes_name(self):
        """generate a new unique axes name"""
        axnames = list(self.axes.keys())
        for i in range(50):
            n = chr(65 + i)
            if n not in axnames:
                return n
        raise ValueError('could not find unique axis name')

    def build(self):
        """build the widget"""
        self.setMinimumWidth(500)
        self.setMinimumHeight(400)
        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)
        self.msg_label = QtWidgets.QLabel()
        self.msg_label.setContentsMargins(5, 5, 5, 5)
        layout.addWidget(self.msg_label)
        content_layout = QtWidgets.QHBoxLayout()
        content_layout.setContentsMargins(0, 0, 0, 0)
        layout.addLayout(content_layout)

        self.build_figure(content_layout)
        self.build_tools(content_layout)

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

        # create layout
        tools_layout = QtWidgets.QVBoxLayout()
        tools_layout.setContentsMargins(0, 0, 0, 0)
        layout.addLayout(tools_layout)

        # create anchors
        anchor_layout = QtWidgets.QVBoxLayout()
        radio_set = QtWidgets.QButtonGroup()
        radio_set.setExclusive(True)
        for pos, name in self.position_dict.items():
            w = QtWidgets.QRadioButton(name)
            if pos == self.anchor:
                w.setChecked(True)
            w.clicked.connect(partial(self.update_anchor, pos))
            radio_set.addButton(w)
            anchor_layout.addWidget(w)
        tools_layout.addLayout(anchor_layout)

        # create add axes button
        add_axes_button = QtWidgets.QPushButton('Add axes')
        add_axes_button.clicked.connect(self.add_axes_clicked)
        tools_layout.addWidget(add_axes_button)

        # create table for axes positions
        self.axtable = AxesPositionsWidget(self.axes)
        self.axtable.setFixedWidth(300)
        self.axtable.changed.connect(self.set_ax_position)
        self.axtable.deleted.connect(self.delete_axes)
        tools_layout.addWidget(self.axtable)

    def set_ax_position(self, axname, attr, value):
        """
        set the position of an axes from the attribute name
        :param axname: name of the axes
        :param attr: name of the position attribute
        :param value: value of the position attribute
        """
        ax = self.axes[axname]
        setattr(ax, attr, value)
        self.draw()

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

    def delete_axes(self, name):
        """delete an axes from the editor"""
        self.axes.pop(name)
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
        headers = ['X', 'X', 'Width', 'Height', 'Aspect', 'Actions']
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

        gridform = QtWidgets.QFormLayout()
        self.fields = dict()
        for k, spec in self.FIELD_SPEC.items():
            self.fields[k] = f = spec['cls'](spec['value'])
            gridform.addRow(k, f)
        self.layout.addLayout(gridform)

        self.grid_button = QtWidgets.QPushButton('Add from grid')
        self.grid_button.clicked.connect(self.add_from_grid)
        self.layout.addWidget(self.grid_button)

        hline = QtWidgets.QFrame()
        hline.setFrameShape(QtWidgets.QFrame.HLine)
        hline.setFrameShadow(QtWidgets.QFrame.Sunken)
        self.layout.addWidget(hline)

        self.click_button = QtWidgets.QPushButton('Click in axes')
        self.click_button.clicked.connect(self.click_axes)
        self.layout.addWidget(self.click_button)

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

    import argparse

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

