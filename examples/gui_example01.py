import numpy as np
from matplotlib import pyplot as plt

from axpositioning import adjust_figure_layout

fig = plt.figure(figsize=(6, 6))
ax = fig.add_subplot(2,2,3)
x = np.linspace(0, 1, 100)
ax.plot(x, np.sin(5*x), 'r-')

ax = fig.add_subplot(2,2,1)
ax.scatter(np.random.random(100), np.random.random(100), lw=0, color='k')
ax = fig.add_subplot(2,2,2)
ax.pcolormesh(
    np.arange(20),
    np.arange(20),
    np.random.rand(20, 20),
    cmap='inferno')

adjust_figure_layout(fig)

plt.show()