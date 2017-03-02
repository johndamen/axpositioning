from .__init__ import *
import pickle
import sys


if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument('--width', '-W', default=8, type=float)
    parser.add_argument('--height', '-H', default=6, type=float)
    parser.add_argument('--stream-bounds', dest='stream_bounds', action='store_true')

    kw = vars(parser.parse_args())
    figsize = kw.pop('width'), kw.pop('height')
    if kw.pop('stream_bounds', False):
        bounds = pickle.Unpickler(sys.stdin.buffer).load()
    else:
        bounds = []

    data = position_axes_gui(figsize, bounds)
    print('FIG:'+','.join('{:.2f}'.format(s) for s in data['figsize']))
    for bnd in data['bounds']:
        print(','.join(map(str, bnd)))