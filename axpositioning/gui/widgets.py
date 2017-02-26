from PyQt5 import QtWidgets, QtCore
from functools import partial
from matplotlib.gridspec import GridSpec


__all__ = ['AxesPositionsWidget', 'NumField', 'IntField', 'MultiIntField', 'FloatField', 'AddAxesWidget']

def hline():
    f = QtWidgets.QFrame()
    f.setFrameShape(QtWidgets.QFrame.HLine)
    f.setFrameShadow(QtWidgets.QFrame.Sunken)
    return f


class AxesPositionsWidget(QtWidgets.QTableWidget):

    """
    table of axes positions

    signals:
    - changed(axes_name, attr_name, value)
    - deleted(axes_name)
    """

    changed = QtCore.pyqtSignal(str, str, object)
    deleted = QtCore.pyqtSignal(str)
    selected = QtCore.pyqtSignal(str, bool)

    def __init__(self, axes):
        super().__init__()
        self.build()
        self.fill(axes)

    def build(self):
        pass

    def fill(self, axes):
        """fill the table based on the given axes position objects"""
        headers = ['', 'X', 'Y', 'Width', 'Height', 'Aspect']
        widths = [20, 45, 45, 45, 45, 45]
        self.setColumnCount(len(headers))
        self.setShowGrid(False)
        for i, w in enumerate(widths):
            self.setColumnWidth(i, w)
        self.setHorizontalHeaderLabels(headers)

        self.setRowCount(len(axes))
        names = []
        for i, (k, v) in enumerate(axes.items()):
            f = QtWidgets.QCheckBox()
            f.setChecked(v._selected)
            f.stateChanged.connect(partial(self.selected.emit, k))
            self.setCellWidget(i, 0, f)
            for j, attr in enumerate(('x', 'y', 'w', 'h', 'aspect')):
                f = FloatField(getattr(v, attr))
                f.changed.connect(partial(self.changed.emit, k, attr))
                self.setCellWidget(i, j+1, f)

            self.setRowHeight(i, 25)

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
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.layout.setSpacing(5)
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
        self.axes_added.emit(data)

    def add_at_click(self):
        data = dict(w=self.posfields['w'].value(),
                    h=self.posfields['h'].value())
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



