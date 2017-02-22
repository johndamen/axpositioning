import argparse
from .gui import position_axes_gui


p = argparse.ArgumentParser()
p.add_argument('-W', '--width', dest='width', nargs='?', default=8)
p.add_argument('-H', '--height', dest='height', nargs='?', default=7)

if __name__ == '__main__':
    kw = vars(p.parse_args())
    bounds = position_axes_gui(
        (kw.pop('width'), kw.pop('height')),
        [], **kw)

    items = ['('+\
             ', '.join('{:.2f}'.format(v) for v in bnd)\
             +')'
             for bnd in bounds]
    print('[{}]'.format(',\n '.join(items)))