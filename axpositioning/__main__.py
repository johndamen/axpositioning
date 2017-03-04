import argparse
from .gui import position_axes_gui


p = argparse.ArgumentParser()
p.add_argument('-W', '--width', dest='width', nargs='?', default=8)
p.add_argument('-H', '--height', dest='height', nargs='?', default=6)

if __name__ == '__main__':
    kw = vars(p.parse_args())
    data = position_axes_gui(
        (kw.pop('width'), kw.pop('height')),
        [], **kw)
    w, h = data['figsize']
    print('figsize: {}, {}'.format(w, h))
    items = ['('+\
             ', '.join('{:.2f}'.format(v) for v in bnd)\
             +')'
             for bnd in data['bounds']]
    print('[{}]'.format(',\n '.join(items)))