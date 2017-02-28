from .__init__ import *


if __name__ == '__main__':
    import argparse
    import sys

    parser = argparse.ArgumentParser()
    parser.add_argument('--width', '-W', default=8, type=float)
    parser.add_argument('--height', '-H', default=6, type=float)
    parser.add_argument('--stream-bounds', dest='stream_bounds', action='store_true')

    kw = vars(parser.parse_args())
    figsize = kw.pop('width'), kw.pop('height')
    if kw.pop('stream_bounds', False):
        if sys.version_info[0] == 3:
            bounds = pickle.Unpickler(sys.stdin.buffer).load()
        else:
            bounds = pickle.Unpickler(sys.stdin).load()
    else:
        bounds = []

    bounds = position_axes_gui(figsize, bounds)
    for bnd in bounds:
        print(','.join(map(str, bnd)))