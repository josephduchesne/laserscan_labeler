# -*- coding: utf-8 -*- 
"""
python qt_labeler.py BAG_PATH TOPIC_NAME
"""
import sys, os, random
from PyQt4.QtCore import *
import signal
from PyQt4.QtGui import *

import numpy as np
import matplotlib
from bag_loader import BagLoader
from circle_region import *
from matplotlib.backends.backend_qt4agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure

# Handle ctrl-c
signal.signal(signal.SIGINT, signal.SIG_DFL)

class AppForm(QMainWindow):
    def __init__(self, data):
        QMainWindow.__init__(self, None)
        self.setWindowTitle('LaserScan Labeler')

        self.points = None
        self.dragging = None
        self.play_timer = None
        self.circles = CircleRegionManager()

        self.data = data
        self.create_main_frame()
        self.setChildrenFocusPolicy(Qt.NoFocus)

        self.on_draw()

    def press(self, event):
        print event, event.inaxes
        print "press", event.xdata, event.ydata, event

        self.dragging = self.circles.get_patch_index(event.xdata, event.ydata)
        if self.dragging is not None:
            if event.button == 3:
                self.circles.delete(self.dragging)
                self.dragging = None
            elif event.button == 2:
                self.circles.current[self.dragging].end = None
                self.dragging = None
            else:
                index = self.spinbox.value()
                self.circles.current[self.dragging].move(event.xdata, event.ydata, index)
        else: # Create new region!
            self.circles.create(event.xdata, event.ydata)
        self.on_draw()

    def motion(self, event):
        if self.dragging is not None:
            index = self.spinbox.value()
            self.circles.current[self.dragging].move(event.xdata, event.ydata, index)
            self.on_draw()

    def release(self, event):
        print "release", event.xdata, event.ydata
        self.dragging = None
    
    def setChildrenFocusPolicy (self, policy):
        def recursiveSetChildFocusPolicy (parentQWidget):
            for childQWidget in parentQWidget.findChildren(QWidget):
                childQWidget.setFocusPolicy(policy)
                recursiveSetChildFocusPolicy(childQWidget)
        recursiveSetChildFocusPolicy(self)

    def on_draw(self):
        """ Redraws the figure
        """
        index = self.spinbox.value()
        self.circles.set_index(index)
        # Filter out max range points of "no return"
        data_filtered = [r if r<self.data.range_max else None for r in self.data.data[index]]
        colors = self.circles.get_colors(self.data)
        idx = np.array(self.data.data[index]) < self.data.range_max
        self.lines.set_data(self.data.theta, data_filtered)
        if self.points is not None:
            self.points.remove()
        self.points = self.ax_p.scatter(self.data.theta[idx], self.data.data[index][idx], 3, colors[idx], zorder=5)
        
        self.circles.render(self.ax_c)
        
        self.canvas.draw()

    def prev(self, event):
        mods = QApplication.keyboardModifiers()
        if bool(mods & Qt.ShiftModifier):
            self.spinbox.setValue(self.spinbox.value()-10)
        else:
            self.spinbox.setValue(self.spinbox.value()-1)

    def play(self, event):
        if self.play_timer is None:
            self.play_timer = QTimer()
            self.play_timer.timeout.connect(self.next)
            self.play_timer.start(100)
        else:
            if self.play_timer.isActive():
                self.play_timer.stop()
            else:
                self.play_timer.start()
        if self.play_timer.isActive():
            self.play_button.setText(u"⏸")
        else:
            self.play_button.setText(u"▶")

        print "Play"

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Left:
            self.prev(event)
        elif event.key() == Qt.Key_Right:
            self.next(event)
        elif event.key() == Qt.Key_Space:
            self.play(event)

    def next(self, *args):
        mods = QApplication.keyboardModifiers()
        if bool(mods & Qt.ShiftModifier):
            self.spinbox.setValue(self.spinbox.value()+10)
        else:
            self.spinbox.setValue(self.spinbox.value()+1)

    def valueChanged(self, value):
        self.on_draw()
        print value
    
    def create_main_frame(self):
        self.main_frame = QWidget()
        
        # Create the figure
        self.fig = Figure()
        self.canvas = FigureCanvas(self.fig)
        self.canvas.setParent(self.main_frame)

        # Create axes

        # the polar axis:
        rect = [0,0,1,1]
        self.ax_p = self.fig.add_axes(rect, polar=True, frameon=False, aspect=1)
        self.ax_c = self.fig.add_axes(rect, aspect=1, frameon=False)

        # Set up the cartesian plot
        self.ax_c.get_xaxis().set_visible(False)
        self.ax_c.get_yaxis().set_visible(False)


        # Set up the polar polot
        self.ax_p.set_rlabel_position(-22.5)  # get radial labels away from plotted line
        self.ax_p.grid(True)
        self.ax_p.autoscale(False)

        # Patch
        self.circles.render(self.ax_c)

        # Render initial values
        self.lines, = self.ax_p.plot(self.data.theta, self.data.data[0],'r-')
        self.ax_p.set_rmax(self.data.range_max)
        self.ax_p.set_rticks(np.arange(0,self.data.range_max+1, 1.0))  # less radial ticks
        
        # Bind the 'pick' event for clicking on one of the bars
        #
        # self.canvas.mpl_connect('pick_event', self.on_pick)
        self.canvas.mpl_connect('button_press_event', self.press)
        self.canvas.mpl_connect('motion_notify_event', self.motion)
        self.canvas.mpl_connect('button_release_event', self.release)
        
        # GUI controls
        # 
        
        self.prev_button = QPushButton(u"🡰")
        self.prev_button.clicked.connect(self.prev)

        self.play_button = QPushButton(u"▶")
        self.play_button.clicked.connect(self.play)

        self.next_button = QPushButton(u"🡲")
        self.next_button.clicked.connect(self.next)
        
        spinbox_label = QLabel('Scan #')
        self.spinbox = QSpinBox()
        self.spinbox.setRange(0, self.data.length-1)
        self.spinbox.setValue(0)
        self.spinbox.valueChanged.connect(self.valueChanged)
        self.spinbox.setFocusPolicy(Qt.NoFocus)
        
        #
        # Button layout
        # 
        hbox = QHBoxLayout()
        
        for w in [  self.prev_button, self.play_button, self.next_button,
                    spinbox_label, self.spinbox]:
            hbox.addWidget(w)
            hbox.setAlignment(w, Qt.AlignVCenter)
        
        vbox = QVBoxLayout()
        vbox.addWidget(self.canvas)
        # vbox.addWidget(self.mpl_toolbar)
        vbox.addLayout(hbox)
        
        self.main_frame.setLayout(vbox)
        self.setCentralWidget(self.main_frame)


def main():
    if len(sys.argv) != 3:
        print "Invalid argument count!"
        print "Usage\n\t%s BAGFILE TOPIC\n\t%s foo.bag /scan" % (sys.argv[0], sys.argv[0])
        exit()
    data = BagLoader(sys.argv[1], sys.argv[2])

    app = QApplication(sys.argv)
    form = AppForm(data)
    form.show()
    app.exec_()

if __name__ == "__main__":
    main()
