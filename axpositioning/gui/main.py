from collections import OrderedDict
from functools import partial
from matplotlib.figure import Figure

from PyQt5 import QtWidgets, QtCore, QtGui
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas

from .model import AxesSet
from .widgets import *


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
        ('S', 'lower center'),
        ('N', 'top center'),
        ('W', 'left center'),
        ('E', 'right center'),
        ('SW', 'lower left'),
        ('NW', 'upper left'),
        ('NE', 'upper right'),
        ('SE', 'lower right'),
        ('C', 'center')])

    click_axes_data = dict(w=.3, h=.3)

    def __init__(self, figsize, bounds=(), anchor='C', dpi=None):
        super().__init__()

        w, h = figsize
        self.figure = Figure(figsize=(w, h))

        if dpi is None:
            dpi = 800 / max(w, h)
            self.figure.set_dpi(dpi)

        self.axes = AxesSet(self.figure, bounds, anchor)
        self.build()
        self.canvas.mpl_connect('button_release_event', self.draw_axes)
        self.pointing_axes = False

    def build(self):
        """build the widget"""
        self.setMinimumWidth(600)
        self.setMinimumHeight(350)
        layout = QtWidgets.QHBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)

        figure_layout = QtWidgets.QVBoxLayout()
        layout.addLayout(figure_layout)
        self.build_figure(figure_layout)
        self.build_tools(layout)

        self.msg_label = QtWidgets.QLabel()
        self.msg_label.setContentsMargins(5, 5, 5, 5)
        figure_layout.addWidget(self.msg_label)

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
        tools_widget.setFixedWidth(350)
        layout.addWidget(tools_widget)

        aw = QtWidgets.QWidget()
        anchor_layout = QtWidgets.QVBoxLayout(aw)
        radio_set = QtWidgets.QButtonGroup()
        radio_set.setExclusive(True)
        for pos, name in self.position_dict.items():
            w = QtWidgets.QRadioButton(name)
            if pos == self.axes.anchor:
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
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(5)

        # main buttons
        button_layout = QtWidgets.QHBoxLayout()
        button_layout.setContentsMargins(0, 0, 0, 0)
        clear_figure_button = QtWidgets.QPushButton('Clear figure')
        clear_figure_button.clicked.connect(self.clear_figure)
        button_layout.addWidget(clear_figure_button)
        select_all_button = QtWidgets.QPushButton('Select all')
        select_all_button.clicked.connect(self.select_all_axes)
        button_layout.addWidget(select_all_button)
        select_none_button = QtWidgets.QPushButton('Clear selection')
        select_none_button.clicked.connect(self.select_none_axes)
        button_layout.addWidget(select_none_button)
        layout.addLayout(button_layout)

        # actions
        action_layout = QtWidgets.QHBoxLayout()
        layout.addLayout(action_layout)
        action_layout.addItem(QtWidgets.QSpacerItem(
            0, 0,
            QtWidgets.QSizePolicy.Expanding,
            QtWidgets.QSizePolicy.Maximum))
        action_layout.addWidget(QtWidgets.QLabel('Actions'))
        self.actions_dropdown = QtWidgets.QComboBox()
        self.actions_dropdown.addItems(sorted(self.axes_actions.keys()))
        action_layout.addWidget(self.actions_dropdown)
        execute_action_button = QtWidgets.QPushButton('Apply')
        execute_action_button.clicked.connect(self.execute_current_action)
        action_layout.addWidget(execute_action_button)

        self.axtable = AxesPositionsWidget(self.axes)
        self.axtable.changed.connect(self.set_ax_position)
        self.axtable.deleted.connect(self.delete_axes)
        self.axtable.selected.connect(self.select_axes)
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

    # ---------
    # edit axes
    # ---------

    def draw_axes(self, event):
        """create an axes at the click location if self.pointing_axes is enabled"""
        if self.pointing_axes:
            x, y = self.figure.transFigure.inverted().transform((event.x, event.y))
            a = self.add_axes_at_position(x, y, **self.click_axes_data)
            self.pointing_axes = False
            # clear the message widget
            self.set_message(None)

    def click_new_axes(self, data):
        self.pointing_axes = True
        self.set_message('Click in the figure to place a new axes at that position')
        self.click_axes_data = data

    def add_axes_at_position(self, x, y, w=.4, h=.4, n=None, draw=True):
        """add axes at specified location in Figure coordinates"""

        self.axes.add(x, y, w, h, apply_anchor=True)

        if draw:
            self.draw(posfields=True)

    def add_axes(self, bounds, draw=True):
        self.axes.add(*bounds)

        if draw:
            self.draw(posfields=True)

    def set_axes(self, bounds, draw=True):
        """set several axes from a list of bounds"""

        for bnd in bounds:
            self.axes.add(*bnd)

        if draw:
            self.draw(posfields=True)

    def set_ax_position(self, axname, attr, value):
        """
        set the position of an axes from the attribute name
        :param axname: name of the axes
        :param attr: name of the position attribute
        :param value: value of the position attribute
        """
        self.axes.set_property(str(axname), attr, value)
        self.draw(posfields=True)

    def delete_axes(self, name, redraw=True):
        """delete an axes from the editor"""
        self.axes.pop(str(name))
        if redraw:
            self.draw(posfields=True)

    # -----------
    #  update gui
    # -----------

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

    def update_anchor(self, pos, clicked, redraw=True):
        """set the position reference anchor of the axes to a new location"""
        if clicked:
            for name, a in self.axes.items():
                a.set_anchor(pos)
            self.axes.anchor = pos
        if redraw:
            self.draw(posfields=True)

    # ------------------------------------
    # selecting axes and executing actions
    # ------------------------------------

    def execute_current_action(self):
        if not self.axes.any_selected():
            return
        action = self.actions_dropdown.currentText()
        fn = getattr(self, self.axes_actions[str(action)])
        fn(self.axes.selected_names, self.axes.selected)

    def select_axes(self, key, b=True):
        self.axes.select(str(key), b)
        self.draw()

    def clear_figure(self):
        self.figure.clear()
        for k in list(self.axes.keys()):
            self.delete_axes(k, redraw=False)
        self.draw(posfields=True)

    def select_all_axes(self):
        self.axes.select_all()
        self.draw(posfields=True)

    def select_none_axes(self):
        self.axes.select_none()
        self.draw(posfields=True)

    # --------------
    # Define actions
    # --------------
    axes_actions = {
        'delete': 'delete_axes_objects',
        'align X': 'axes_equal_x',
        'align Y': 'axes_equal_y',
        'equal width': 'axes_equal_w',
        'equal height': 'axes_equal_h',
        'equal aspect': 'axes_equal_aspect',
        'join': 'axes_join',
        'split': 'axes_split'
    }

    def delete_axes_objects(self, names, axes, redraw=True):
        for n in names:
            self.axes.pop(n)
        if redraw:
            self.draw(posfields=True)

    def axes_equal_x(self, names, axes, redraw=True):
        x = axes.pop(0).x
        for a in axes:
            a.x = x
        if redraw:
            self.draw(posfields=True)

    def axes_equal_y(self, names, axes, redraw=True):
        y = axes.pop(0).y
        for a in axes:
            a.y = y
        if redraw:
            self.draw(posfields=True)

    def axes_equal_w(self, names, axes, redraw=True):
        w = axes.pop(0).w
        for a in axes:
            a.w = w
        if redraw:
            self.draw(posfields=True)

    def axes_equal_h(self, names, axes, redraw=True):
        h = axes.pop(0).h
        for a in axes:
            a.h = h
        if redraw:
            self.draw(posfields=True)

    def axes_equal_aspect(self, names, axes, redraw=True):
        A = axes.pop(0).aspect
        for a in axes:
            a.aspect = A
        if redraw:
            self.draw(posfields=True)

    def axes_join(self, names, axes, redraw=True):
        """join axes within bounding box of all selected axes"""

        # store anchor
        anchor = self.axes.anchor

        # update anchor to lower left during processing
        self.update_anchor('SW', True, redraw=False)

        # determine bounding box
        xll = min(a.x for a in axes)
        yll = min(a.y for a in axes)
        xur = max(a.x + a.w for a in axes)
        yur = max(a.y + a.h for a in axes)

        # redefine first axes position to bounding box
        axes[0].set_position((xll, yll, xur-xll, yur-yll))

        # delete other axes
        self.delete_axes_objects(names[1:], axes[1:], redraw=False)

        # update the anchor to the original
        self.update_anchor(anchor, True, redraw=redraw)

    def axes_split(self, names, axes, redraw=True):
        """
        split axes in two parts based on a given ratio
        """
        def show_error(msg):
            m = QtWidgets.QMessageBox()
            m.setText(msg)
            m.exec()

        # create dialog to input ratio, spacing and h/v split
        dialog = SplitDialog()
        if dialog.exec() != QtWidgets.QDialog.Accepted:
            return
        ratio, spacing, horizontal = dialog.get_data()

        if ratio < 0 or ratio > 1:
            show_error('ratio must be between 0 and 1')
            return

        for a in axes:
            try:
                new_bounds = a.split(ratio, spacing, wsplit=horizontal)
            except ValueError as e:
                show_error(str(e))
                return
            else:
                # create 2nd axes and copy selected state
                new_ax = self.axes.add(*new_bounds, anchor=a.get_anchor())
                new_ax._selected = a._selected

        if redraw:
            self.draw(posfields=True)


