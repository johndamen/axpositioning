from collections import OrderedDict
from ..axpositioning import PositioningAxes
import numpy as np


class GuiPositioningAxes(PositioningAxes):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._selected = False

    def format_placeholder(self, label=''):
        """
        format the axes with no ticks and a simple label in the center
        the anchor point is shown as a blue circle
        """
        self.set_xticks([])
        self.set_yticks([])
        self.set_xlim(-1, 1)
        self.set_ylim(-1, 1)
        self.set_facecolor('none')
        self.text(.05, .95, label, ha='left', va='top', transform=self.transAxes, zorder=2)

        for v in self.spines.values():
            if self._selected:
                v.set_color((.2, .2, .8))
                v.set_linewidth(2)
            else:
                v.set_color('k')
                v.set_linewidth(1)

        ax, ay = self.get_anchor()
        self.scatter([ax], [ay],
                     marker='+',
                     transform=self.transAxes,
                     color=(.9, .1, .1),
                     s=50,
                     clip_on=False,
                     zorder=10)
        self.scatter([ax], [ay],
                     marker='o',
                     transform=self.transAxes,
                     facecolors='none',
                     edgecolors=(.9, .1, .1),
                     lw=1,
                     s=50,
                     clip_on=False,
                     zorder=10)

    def get_guides(self):
        pnts = list(map(float, self.get_position().get_points().flatten()))
        x = pnts[::2]
        y = pnts[1::2]

        xc = sum(x)/2
        yc = sum(y)/2
        return set(x), set(y), set([xc]), set([yc])

    def plot_guides(self, x, y, xc, yc, color='g', ccolor='y', lw=1, relative=True):
        kw = dict(transform=self.figure.transFigure, clip_on=False)
        labelkw = kw.copy()
        labelkw['size'] = 9
        if relative:
            labelfmt = '{:.3f}'
        else:
            labelfmt = '{:.0f}'

        w, h = self.figure.get_size_inches()
        dpi = self.figure.get_dpi()

        lx = list(x) + list(xc)
        xcolors = [color]*len(x)+[ccolor]*len(xc)
        for vx, c in zip(lx, xcolors):
            if relative:
                label = labelfmt.format(vx).lstrip('0')
            else:
                label = labelfmt.format(vx * w * dpi)
            self.plot([vx, vx], [0, 1], color=c, lw=lw, **kw)
            self.text(vx, 0.01, label, ha='center', va='bottom', **labelkw)
            self.text(vx, 0.99, label, ha='center', va='top', **labelkw)

        ly = list(y) + list(yc)
        ycolors = [color] * len(y) + [ccolor] * len(yc)
        for vy, c in zip(ly, ycolors):
            if relative:
                label = labelfmt.format(vy).lstrip('0')
            else:
                label = labelfmt.format(vy * h * dpi)
            self.plot([0, 1], [vy, vy], color=c, lw=lw, **kw)
            self.text(0.01, vy, label, ha='left', va='center', **labelkw)
            self.text(0.99, vy, label, ha='right', va='center', **labelkw)


class AxesSet(OrderedDict):

    def __init__(self, fig, bounds, anchor='C'):
        self.figure = fig
        self.anchor = anchor
        super().__init__()
        for bnd in bounds:
            self.add(*bnd)

    def add(self, x, y, w, h, anchor=None, apply_anchor=False):
        if anchor is None:
            anchor = self.anchor

        n = self.next_axes_name()

        if apply_anchor:
            a = GuiPositioningAxes.from_position(self.figure, x, y, w, h, anchor=anchor)
        else:
            a = GuiPositioningAxes(self.figure, (x, y, w, h), anchor=anchor)
        self[n] = a

        return a

    def plot_guides(self, selected=True, relative=True):
        x = set()
        y = set()
        xc = set()
        yc = set()
        a = None
        for a in self.values():
            if selected and not a._selected:
                continue
            ax, ay, axc, ayc = a.get_guides()
            x |= ax
            y |= ay
            xc |= axc
            yc |= ayc
        if a is not None:
            a.plot_guides(x, y, xc, yc, relative=relative)

    def bounds(self):
        return [a.bounds for a in self.values()]

    def set_property(self, axname, attr, value):
        a = self[axname]
        setattr(a, attr, value)

    def next_axes_name(self):
        """generate a new unique axes name"""
        axnames = list(self.keys())
        for i in range(50):
            n = chr(65 + i)
            if n not in axnames:
                return n
        raise ValueError('could not find unique axis name')

    def select(self, name, b=True):
        self[name]._selected = bool(b)

    def select_all(self):
        for k in self.keys():
            self.select(k, True)

    def select_none(self):
        for k in self.keys():
            self.select(k, False)

    def map(self, fn, selected=False):
        for a in self.values():
            if selected and not a._selected:
                continue
            fn(a)

    @property
    def names(self):
        return list(self.keys())

    def change_order(self, newnames):
        if set(self.names) ^ set(newnames):
            raise ValueError('moved names do not match current axes names')

        data = dict()
        for k in self.names:
            data[k] = self.pop(k)
        assert not self
        for name in newnames:
            self[name] = data.pop(name)
        assert not data

    @property
    def selected(self):
        return [a for a in self.values() if a._selected]

    @property
    def selected_names(self):
        return [k for k, a in self.items() if a._selected]

    def any_selected(self):
        for v in self.values():
            if v._selected:
                return True
        return False
