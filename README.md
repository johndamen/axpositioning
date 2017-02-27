# Various utilities related to axes positioning
Correctly positioning axes in matplotlib can be a long and iterative process. 
Using the graphical interface utility `axpositioning.adjust_axes(fig)` can ease the process.

![positions](screenshots/axes_positions.png)

![add axes](screenshots/add_axes.png)

## Features
1. Move and resize existing axes
2. Join, split and align axes
2. Change the used reference point of an axes bounds when editing
3. Create new axes by manually defining the position and size, clicking in the figure or using GridSpec settings
4. Preview the updated positions of the empty axes during editing
5. Close to update the axes positions of the original figure

## Examples

Run from the command line

```bash
python -m axpositioning
```

Adjust axes using gui in script

```python
from matplotlib import pyplot as plt
import axpositioning

fig = plt.figure()
ax = fig.subplot(111)
ax.plot([0, 1], [0, 1])

axpositioning.adjust_axes(fig)

plt.show()
```

Adjust axes position using anchors and plotutils.PositioningAxes

```python
from matplotlib import pyplot as plt
import axpositioning

fig = plt.figure()
ax = fig.add_axes([.1, .1, .8, .8])
p = axpositioning.PositioningAxes.from_axes(fig, ax, anchor='C')

p.set_anchor('C')
print(p.x, p.y)

p.set_anchor('SW')
print(p.x, p.y)

p.set_anchor('NE')
print(p.x, p.y)
```
