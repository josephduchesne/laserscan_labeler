import numpy as np
from matplotlib.collections import PatchCollection
import matplotlib.patches as mpatches

class CircleRegionManager():
    def __init__(self):
        self.regions = [CircleRegion(self, 0.5, 0.5, 0.1, 0, 4), CircleRegion(self, 0.5, 0.5, 0.1, 4, 7)]
        self.set_index(0)
        self.p = None

    def render(self, ax):
        patches = []

        for i in range(len(self.current)):
            patches.append(self.current[i].render(self.index))

        if self.p is not None:
            self.p.remove()
            self.p = None
        if len(patches)>0:
            self.p = PatchCollection(patches, alpha=0.4, match_original=True)
            ax.add_collection(self.p)

    def filter_list(self):
        """
        Return the list of regions that are active at this time period
        """
        # Update indices
        for i in range(len(self.regions)):
            self.regions[i].index = i
        # Return
        return [r for r in self.regions if r.start<=self.index and (r.end is None or r.end>self.index)]

    def get_next_region(self, index):
        """
        If the next region is a direct continuation of the current one
        return it. Otherwise, return None
        """
        if index < len(self.regions)-1:
            r1 = self.regions[index]
            r2 = self.regions[index+1]
            if r1.x[1] == r2.x[0] and r1.y[1] == r2.y[0] and r1.r[1] == r2.r[0] and r1.end == r2.start:
                return index+1
        return None

    def get_prev_region(self, index):
        """
        If the prev region is a direct continuation of the current one
        return it. Otherwise, return None
        """
        if index > 0:
            r1 = self.regions[index-1]
            r2 = self.regions[index]
            if r1.x[1] == r2.x[0] and r1.y[1] == r2.y[0] and r1.r[1] == r2.r[0] and r1.end == r2.start:
                return index-1
        return None


    def set_index(self, i):
        self.index = i
        self.current = self.filter_list()

    def get_patch_index(self, x, y):
        for i in range(len(self.current)):
            if self.current[i].contains(x,y, self.index):
                return i
        return None

    def create(self, x, y, r=0.1):
        self.regions.append(CircleRegion(self, x,y,r,self.index))
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

    def insert(self, i, x, y, r, start=0, end=None):
        self.regions.insert(i, CircleRegion(self, x,y,r, start, end))
        self.current = self.filter_list()
        return self.regions[i]

class CircleRegion():

    def __init__(self, manager, x, y, r, start=0, end=None):
        self.start = start
        self.end = end
        self.manager = manager
        
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
        """
        This function's a bit of a mess
        It operates in 3 modes:
        - Move start (and end of previous segment if "connected")
        - Move end (and beginning of next segment if "connected")
        - Move middle (splitting the current region into two new regions)
        """
        if index == self.start:  # start of region
            prev_region = self.manager.get_prev_region(self.index)
            if prev_region is None:
                self.x[0] = x
                self.y[0] = y
            else:  # Also move previous point
                self.manager.regions[prev_region].x[1] = self.x[0] = x
                self.manager.regions[prev_region].y[1] = self.y[0] = y
        elif self.end is not None and index == self.end -1:  # end of region
            next_region = self.manager.get_next_region(self.index)
            if next_region is None:
                self.x[1] = x
                self.y[1] = y
            else:  # Also move previous point
                self.manager.regions[next_region].x[0] = self.x[1] = x
                self.manager.regions[next_region].y[0] = self.y[1] = y
        else: # In the middle of a region. split here!
            print "Splitting series!", index, self.start, self.end
            cx,cy,cr = self.xyr(index)  # Get values
            # Insert new region after this one
            new_region = self.manager.insert(self.index+1, cx,cy,cr, index+1, self.end)
            # Update new region end x,y,r, by copying existing values over
            new_region.x[1] = self.x[1]
            new_region.y[1] = self.y[1]
            new_region.r[1] = self.r[1]
            # Update this region end to intermediate position
            self.x[1] = cx
            self.y[1] = cy
            self.r[1] = cr
            self.end = index+1  # This segment ends last frame
            print self, new_region

    def resize(self, delta, index):
        """
        This function's a bit of a mess like the previous one
        It operates in 3 modes:
        - Resize start (and end of previous segment if "connected")
        - Resize end (and beginning of next segment if "connected")
        - Resize middle (splitting the current region into two new regions)
        """
        if index == self.start:  # start of region
            prev_region = self.manager.get_prev_region(self.index)
            r = max(abs(delta), self.r[0] + delta)
            if prev_region is None:
                self.r[0] = r
            else:  # Also move previous point
                self.manager.regions[prev_region].r[1] = self.r[0] = r
        elif self.end is not None and index == self.end -1:  # end of region
            next_region = self.manager.get_next_region(self.index)
            r = max(abs(delta), self.r[1] + delta)
            if next_region is None:
                self.r[1] = r
            else:  # Also move previous point
                self.manager.regions[next_region].r[0] = self.r[1] = r
        else: # In the middle of a region. split here!
            print "Splitting series!", index, self.start, self.end
            cx,cy,cr = self.xyr(index)  # Get values
            # Insert new region after this one
            new_region = self.manager.insert(self.index+1, cx,cy,cr, index+1, self.end)
            # Update new region end x,y,r, by copying existing values over
            new_region.x[1] = self.x[1]
            new_region.y[1] = self.y[1]
            new_region.r[1] = self.r[1]
            # Update this region end to intermediate position
            self.x[1] = cx
            self.y[1] = cy
            self.r[1] = cr
            self.end = index+1  # This segment ends last frame
            print self, new_region
            
            
