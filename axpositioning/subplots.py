import numpy as np
from matplotlib import pyplot as plt


def hsubplots(figwidth, shape, hpad=0, vpad=0, box=(0, 0, 1, 1), ax_aspect=1):
    """
    calculate axes positions for a fixed width
    figure height is dependent on the subplot axes and spacings

    :param figwidth: width in inches of figure to build
    :param shape: (rows, cols)
    :param hpad: horizontal padding
    :param vpad: vertical padding
    :param box: (xll, yll, xur, yur)
    :param ax_aspect: aspect of individual axes
    :return: figsize (w, h), axpositions (3D array)
             positions are returned as a 3D array of row, col, subplot box

    >>>from matplotlib import pyplot as plt
    >>>figsize, positions = hsubplots(10, (2, 3), box=(.05, .05, .95, .95))
    >>>fig = plt.figure(figsize=figsize)
    >>>for i, rowpos in enumerate(positions):
    >>>    for j, pos in enumerate(rowpos):
    >>>        fig.add_axes(pos)
    >>>plt.show()
    """
    m, n = shape

    box = np.array(box)

    axwidth = (box[2] - box[0] - hpad * (n - 1)) / n
    axheight = (box[3] - box[1] - vpad * (m - 1)) / m
    figheight = figwidth * (axwidth / axheight) * ax_aspect

    axpos = []
    for i in range(m):  # rows
        axpos.append([])
        for j in range(n):  # cols
            x = box[0] + j * axwidth + j * hpad
            y = box[1] + i * axheight + i * vpad
            axpos[-1].append([x, y, axwidth, axheight])

    return (figwidth, figheight), np.array(axpos[::-1])


def xyshared_plots(shape, axes, datasets, plotfn, xlabel, ylabel, labels=False, labeldict=None):
    m, n = shape

    if labels == '1A':
        labels = [str(i + 1) + chr(65 + j) for i in range(m) for j in range(n)]
    elif labels == 'A1':
        labels = [chr(65 + i) + str(j + 1) for i in range(m) for j in range(n)]
    elif labels == 'A':
        labels = [chr(65 + i * n + j) for i in range(m) for j in range(n)]

    for mi in range(m):
        for ni in range(n):
            # calculate flat index
            i = mi * n + ni

            # get axes and dataset for this index
            ax = axes[i]
            d = datasets[i]

            # plot dataset on axes
            r = plotfn(ax, d)

            # apply label annotation
            if isinstance(labels, list):
                ax.plot([.1], [.9], 'ko',
                        markersize=labeldict.pop('boxsize', 17),
                        markerfacecolor='w',
                        transform=ax.transAxes)
                ax.text(.1, .9, labels[i],
                        ha='center', va='center', transform=ax.transAxes,
                        **(labeldict or {}))

            # apply ticks and axlabels
            if mi == (m - 1):
                ax.set_xlabel(xlabel)
            else:
                ax.set_xticklabels([])

            if ni == 0:
                ax.set_ylabel(ylabel)
            else:
                ax.set_yticklabels([])
    return r


if __name__ == '__main__':
    from matplotlib import pyplot as plt
    figsize, positions = hsubplots(10, (3, 3), hpad=.05, vpad=.05, box=(.08, .07, .9, .95))
    fig = plt.figure(figsize=figsize)
    for i, rowpos in enumerate(positions):
        for j, pos in enumerate(rowpos):
            ax = fig.add_axes(pos)
    plt.show()


    def plotter(ax, dataset):
        r = ax.scatter(dataset['x'], dataset['y'], c=dataset['z'], cmap='inferno', lw=0)
        ax.set_xticks([0, .5, 1])
        ax.set_yticks([0, .5, 1])
        ax.set_xlim(-.1, 1.1)
        ax.set_ylim(-.1, 1.1)
        return r

    figsize, positions = hsubplots(10, (3, 3), hpad=.01, vpad=.01, box=(.08, .07, .9, .95))
    fig = plt.figure(figsize=figsize)
    cax = fig.add_axes([.91, .07, .02, .88])
    axes = []
    datasets = []
    labels = []

    m, n = positions.shape[:2]
    for i, rowpos in enumerate(positions):
        for j, pos in enumerate(rowpos):
            ax = fig.add_axes(pos)
            axes.append(ax)
            datasets.append(dict(x=np.random.rand(100), y=np.random.rand(100), z=np.random.rand(100)))
            labels.append(chr(65 + i * n + j))
    c = xyshared_plots((m, n), axes, datasets, plotter, 'xlabel', 'ylabel', labels='A1')
    plt.colorbar(c, cax=cax).set_label('z')
    plt.show()

