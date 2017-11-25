import numpy as np
from matplotlib.collections import PatchCollection
import matplotlib.patches as mpatches

class CircleRegionManager():
    def __init__(self):
        self.regions = [CircleRegion(0.5, 0.5, 0.1), CircleRegion(0.2, 0.3, 0.05, 1, 4)]
        self.set_index(0)
        self.p = None

    def render(self, ax):
        patches = []

        for i in range(len(self.current)):
            patches.append(self.current[i].render(self.index))

        if self.p is not None:
            self.p.remove()
        self.p = PatchCollection(patches, alpha=0.4, match_original=True)
        ax.add_collection(self.p)

    def filter_list(self):
        """
        Return the list of regions that are active at this time period
        """
        return [r for r in self.regions if r.start<=self.index and (r.end is None or r.end>self.index)]

    def set_index(self, i):
        self.index = i
        self.current = self.filter_list()

    def get_patch_index(self, x, y):
        for i in range(len(self.current)):
            if self.current[i].contains(x,y, self.index):
                return i
        return None

    def create(self, x, y, r=0.1):
        self.regions.append(CircleRegion(x,y,r,self.index))
        self.filter_list()

    def delete(self, current_offset):
        self.current[current_offset].end = self.index
        # Todo: remove zero length entries!
        self.filter_list()

    def get_colors(self, data):
        cartesian = data.get_cartesian(self.index)
        colors = []
        for i in range(len(cartesian)):
            if self.get_patch_index(*cartesian[i]) is None:
                colors.append('r')
            else:
                colors.append('b')
        return np.array(colors)

class CircleRegion():

    def __init__(self, x,y, r, start=0, end=None):
        self.start = start
        self.end = end
        
        self.x = np.array([x,x])
        self.y = np.array([y,y])
        self.r = np.array([r,r])

    def interp(self, frac, a, b):
        return (1-frac)*a + frac*b

    def xyr(self, index):
        if self.end is None or self.start == self.end:
            return self.x[0], self.y[0], self.r[0]
        # Get fractional position between start and end
        i = (float(index)-self.start)/(self.end-self.start-1)
        return self.interp(i, *self.x),self.interp(i, *self.y),self.interp(i, *self.r)

    def contains(self, px, py, index):
        x,y,r = self.xyr(index)
        return (px-x)**2 + (py-y)**2 <= r**2

    def render(self, index):
        x,y,r = self.xyr(index)
        c = mpatches.Circle((x, y), r, ec="none", color=(0,0,1))  # Blue default region
        if index == self.start:  # Teal, region start
            c.set_color((0,1,1))
        elif self.end is None:  # Neverending region green
            c.set_color((0,1,0))
        elif index == self.end-1:  # Last frame, red
            c.set_color((1,0,0))
        return c

    def move(self, x, y, index):
        if index == self.start:  # start point
            self.x[0] = x
            self.y[0] = y
        elif self.end is not None and index == self.end -1:  # end
            self.x[1] = x
            self.y[1] = y
        else:
            print "TODO!"
            
