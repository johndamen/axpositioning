from matplotlib.axes import Axes
from matplotlib.transforms import Bbox


class PositioningAxes(Axes):

    """
    Class for editing axes position
    """

    @classmethod
    def from_axes(cls, fig, a, **kwargs):
        return cls(fig, a.get_position().bounds, **kwargs)

    def __init__(self, fig, bounds, lock_aspect=False, anchor='C', **kwargs):
        super(PositioningAxes, self).__init__(fig, bounds, **kwargs)
        self._locked_aspect = lock_aspect
        self.set_anchor(anchor)

    def set_anchor(self, a):
        """ensure tuple of anchor position and set using Axes.set_anchor"""
        if a in Bbox.coefs:
            a = Bbox.coefs[a]
        self._anchor = a

    @property
    def bounds(self):
        """returns (xll, yll, w, h)"""
        return self._position.bounds
    @bounds.setter
    def bounds(self, v):
        """set new bounds"""
        self.set_position(v)

    def x2xll(self, x):
        """convert x position to xll based on anchor"""
        return x - self.w * self.get_anchor()[0]

    def xll2x(self, xll):
        """convert xll to x position based on anchor"""
        return xll + self.w * self.get_anchor()[0]

    def y2yll(self, y):
        """convert y position to yll based on anchor"""
        return y - self.h * self.get_anchor()[1]

    def yll2y(self, yll):
        """convert yll to y position based on anchor"""
        return yll + self.h * self.get_anchor()[1]

    @property
    def x(self):
        """x position as xll corrected for the anchor"""
        return self.xll2x(self.bounds[0])
    @x.setter
    def x(self, x):
        """reset the bounds with a new x value"""
        _, yll, w, h = self.bounds
        xll = self.x2xll(x)
        self.bounds = xll, yll, w, h

    @property
    def y(self):
        return self.yll2y(self.bounds[1])
    @y.setter
    def y(self, y):
        """reset the bounds with a new y value"""
        xll, _, w, h = self.bounds
        yll = self.y2yll(y)
        self.bounds = xll, yll, w, h

    @property
    def w(self):
        """width of the axes"""
        return self.bounds[2]
    @w.setter
    def w(self, w):
        """
        reset the bounds with a new width value
        the xll is corrected based on the anchor
        if the aspect ratio is locked, the height and yll are also adjusted
        """
        xll, yll, w0, h = self.bounds

        # adjust horizontal position based on anchor
        xll += self.get_anchor()[0] * (w0 - w)

        # adjust height if aspect is locked
        if self._locked_aspect:
            h0, h = h, w / self.axaspect
            # adjust vertical position based on anchor
            yll += self.get_anchor()[1] * (h0 - h)
        self.bounds = xll, yll, w, h

    @property
    def h(self):
        """height of the axes"""
        return self.bounds[3]
    @h.setter
    def h(self, h):
        """
        reset the bounds with a new height value
        the yll is corrected based on the anchor
        if the aspect ratio is locked, the width and xll are also adjusted
        """
        xll, yll, w, h0 = self.bounds

        # adjust vertical position based on anchor
        yll += self.get_anchor()[1] * (h0 - h)

        # adjust width if aspect is locked
        if self._locked_aspect:
            w0, w = w, h * self.axaspect
            # adjust horizontal position based on anchor
            xll += self.get_anchor()[0] * (w0 - w)
        self.bounds = xll, yll, w, h

    @property
    def figaspect(self):
        """aspect ratio of the figure"""
        fw, fh = self.figure.get_size_inches()
        return fw/fh

    @property
    def axaspect(self):
        """aspect ratio of the axes"""
        return self.figaspect / self.aspect

    @property
    def aspect(self):
        """real aspect ratio of figure and axes together"""
        _, _, aw, ah = self.bounds
        return self.figaspect * (aw/ah)
    @aspect.setter
    def aspect(self, v):
        self.set_aspect_ratio(v)

    def lock_aspect(self, b):
        """keep the aspect fixed"""
        self._locked_aspect = b

    def set_aspect_ratio(self, A, fix_height=False):
        """set the aspect ratio by adjusting width or height"""
        axaspect = A / self.figaspect

        if fix_height:
            self.w = self.h * axaspect
        else:
            self.h = self.w / axaspect

    def format_placeholder(self, label=''):
        """
        format the axes with no ticks and a simple label in the center
        the anchor point is shown as a blue circle
        """
        self.set_xticks([])
        self.set_yticks([])
        self.set_xlim(-1, 1)
        self.set_ylim(-1, 1)
        self.text(.1, .9, label, ha='left', va='top', transform=self.transAxes, zorder=2)

        ax, ay = self.get_anchor()
        self.scatter([ax], [ay], marker='+', transform=self.transAxes, color=(.9, .1, .1), s=50, clip_on=False, zorder=1)

    def __str__(self):
        return '<{} {}>'.format(self.__class__.__qualname__, self.bounds)

    @classmethod
    def from_position(cls, fig, x, y, w, h, anchor):
        """
        accounts for anchor when setting the bounds from the position
        """
        # TODO: incorporate in __init__ using apply_anchor=True
        o = cls(fig, [x, y, w, h], anchor=anchor)
        o.x, o.y, o.w, o.h = x, y, w, h
        return o
