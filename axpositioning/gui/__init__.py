try:
    from PyQt5 import QtWidgets, QtCore
except ImportError:
    from PyQt4 import QtGui as QtWidgets, QtCore
import sys
import subprocess
import pickle
from matplotlib.figure import Figure
from .main import AxPositioningEditor


__all__ = ['position_axes_gui', 'position_axes_gui_subprocess', 'adjust_figure_layout']


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
        app.exec_()
        return w.as_dict()
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
        if line.startswith('FIG:'):
            figsize = tuple(map(float, line[4:].strip().split(',')))
        else:
            newbounds.append([float(v) for v in line.strip().split(',')])
    return figsize, newbounds


def adjust_figure_layout(fig, **kwargs):
    axes = fig.get_axes()
    bounds = [a.get_position().bounds for a in axes]

    figsize, newbounds = position_axes_gui_subprocess(fig.get_size_inches(), bounds)

    fig.set_size_inches(*figsize)

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
