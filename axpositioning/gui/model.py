from ..axpositioning import PositioningAxes


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
                v.set_color('r')
                v.set_linewidth(2)
            else:
                v.set_color('k')
                v.set_linewidth(1)

        ax, ay = self.get_anchor()
        self.scatter([ax], [ay], marker='+', transform=self.transAxes, color=(.9, .1, .1), s=50, clip_on=False, zorder=1)