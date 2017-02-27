from PyQt5 import QtWidgets, QtCore, QtGui
from matplotlib.gridspec import GridSpec


__all__ = ['AxesPositionsWidget', 'NumField', 'IntField', 'MultiIntField', 'FloatField', 'AddAxesWidget', 'SplitDialog']

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

    changed = QtCore.pyqtSignal(int, str, object)
    selected = QtCore.pyqtSignal(str, bool)
    moved = QtCore.pyqtSignal(list, int)  # row indices, new row index
    invalid_value = QtCore.pyqtSignal(int, int, str)

    COLUMN_ATTRS = ('_selected', 'x', 'y', 'w', 'h', 'aspect')
    COLUMN_TYPES = (bool, float, float, float, float, float)
    COLUMN_NAMES = ('', 'X', 'Y', 'Width', 'Height', 'Aspect')

    def __init__(self, axes):
        super().__init__()
        self.build()
        self.fill(axes)
        self.last_drop_row = None
        self.cellChanged.connect(self.changed_item)

    def build(self):
        self.setDragEnabled(True)
        self.setAcceptDrops(True)
        self.setDragDropOverwriteMode(False)
        self.horizontalHeader().setSectionsMovable(True)
        self.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)

    def fill(self, axes):
        """fill the table based on the given axes position objects"""

        widths = [30, 50, 50, 50, 50, 50]
        self.setColumnCount(len(self.COLUMN_NAMES))
        self.setShowGrid(False)
        for i, w in enumerate(widths):
            self.setColumnWidth(i, w)
        self.setHorizontalHeaderLabels(self.COLUMN_NAMES)

        self.setRowCount(len(axes))
        names = []
        self.blockSignals(True)
        for i, (k, v) in enumerate(axes.items()):
            for j, attr in enumerate(self.COLUMN_ATTRS):
                coltype = self.COLUMN_TYPES[j]
                flags = QtCore.Qt.ItemIsEnabled | QtCore.Qt.ItemIsSelectable | QtCore.Qt.ItemIsDragEnabled
                if coltype is bool:
                    f = QtWidgets.QTableWidgetItem()
                    f.setFlags(flags | QtCore.Qt.ItemIsUserCheckable)
                    f.setCheckState(QtCore.Qt.Checked if v._selected else QtCore.Qt.Unchecked)
                elif coltype is float:
                    f = QtWidgets.QTableWidgetItem('{:.3f}'.format(getattr(v, attr)))
                    f.setFlags(flags | QtCore.Qt.ItemIsEditable)
                self.setItem(i, j, f)
            self.setRowHeight(i, 25)

            names.append(k)
        self.setVerticalHeaderLabels(names)
        self.blockSignals(False)

    def changed_item(self, row, col):
        item = self.item(row, col)
        valtype = self.COLUMN_TYPES[col]
        if valtype is bool:
            value = item.checkState() == QtCore.Qt.Checked
        elif valtype is float:
            try:
                value = float(item.text())
            except ValueError as e:
                print(e)
                self.invalid_value.emit(row, col, self.COLUMN_ATTRS[col])
        else:
            raise ValueError('unknown value type')
        self.changed.emit(row, self.COLUMN_ATTRS[col], value)


    def dropMimeData(self, row, col, mimeData, action):
        self.last_drop_row = row
        return True

    def dropEvent(self, event):
        sender = event.source()
        super().dropEvent(event)
        if sender is self:
            if self.last_drop_row is None:
                return
            event.accept()
            rows = sorted(set([int(ind.row()) for ind in self.selectedIndexes()]))
            self.moved.emit(rows, int(self.last_drop_row))


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

        pos_width=0.8,
        pos_height=0.8,
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


class SplitDialog(QtWidgets.QDialog):

    data = dict(ratio=0.5, spacing=0.1, horizontal=True)

    def __init__(self):
        super().__init__()
        layout = QtWidgets.QFormLayout(self)
        self.fields = dict()

        f = QtWidgets.QLineEdit()
        f.setText('{:.3f}'.format(self.data['ratio']))
        v = QtGui.QDoubleValidator(0, 1, 3)
        f.setValidator(v)
        self.fields['ratio'] = f
        layout.addRow('Ratio', f)

        f = QtWidgets.QLineEdit()
        f.setText('{:.3f}'.format(self.data['spacing']))
        v = QtGui.QDoubleValidator(0, 1, 3)
        f.setValidator(v)
        self.fields['spacing'] = f
        layout.addRow('Spacing', f)

        f = QtWidgets.QCheckBox()
        f.setChecked(self.data['horizontal'])
        self.fields['horizontal'] = f
        layout.addRow('Horizontal', f)

        b = QtWidgets.QPushButton('Split')
        b.clicked.connect(self.accept)
        layout.addRow('', b)

    def get_data(self):
        ratio = float(self.fields['ratio'].text())
        spacing = float(self.fields['spacing'].text())
        horizontal = bool(self.fields['horizontal'].isChecked())

        self.data['ratio'] = ratio
        self.data['spacing'] = spacing
        self.data['horizontal'] = horizontal

        return ratio, spacing, horizontal


