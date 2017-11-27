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
import pickle
import gzip
import scipy.io as sio

# Handle ctrl-c
signal.signal(signal.SIGINT, signal.SIG_DFL)

class AppForm(QMainWindow):
    def __init__(self):
        QMainWindow.__init__(self, None)
        self.setWindowTitle('LaserScan Labeler')

        self.points = None
        self.dragging = None
        self.play_timer = None
        self.circles = CircleRegionManager()

        self.path = None  # Save file path
        self.data = None
        self.create_menu()
        self.create_main_frame()
        self.setChildrenFocusPolicy(Qt.NoFocus)

        self.on_draw()

    def create_menu(self):        
        self.file_menu = self.menuBar().addMenu("&File")
        
        save_file_action = self.create_action("&Save",
            shortcut="Ctrl+S", slot=self.save, 
            tip="Save a label file")
        save_as_action = self.create_action("&Save As...",
            shortcut="Ctrl+Shift+S", slot=self.save, 
            tip="Save a label file to another path")
        load_file_action = self.create_action("&Open...",
            shortcut="Ctrl+O", slot=self.open, 
            tip="Open a label file")
        export_action = self.create_action("&Export",
            shortcut="Ctrl+E", slot=self.export, 
            tip="Export labeled data")
        quit_action = self.create_action("&Quit", slot=self.close, 
            shortcut="Ctrl+Q", tip="Close the application")
        
        self.add_actions(self.file_menu, 
            (load_file_action, None, save_file_action, save_as_action, None, export_action, None, quit_action))

    def save(self):
        print "Save!"
        if self.path is None:
            self.save_as()
        else:
            self.save_file(self.path)

    def save_as(self):
        print "Save as!"
        file_choices = "LSL (*.lsl)|*.lsl"
        path = unicode(QFileDialog.getSaveFileName(self, 
                        'Save file', '', 
                        file_choices))
        if not path.endswith(".lsl"):
            path = path + ".lsl"
        self.path = path
        self.save_file(path)
        print path

    def save_file(self, path):
        with gzip.open(path, 'wb') as f:
            pickle.dump([path, self.data, self.circles], f)

    def open(self):
        print "Open!"
        file_choices = "LSL or BAG (*.lsl *.bag);; LSL (*.lsl);; BAG (*.bag)"
        path = unicode(QFileDialog.getOpenFileName(self, 
                        'Open bag or lsl file', '', file_choices))
        
        if path.endswith(".lsl"):
            self.path = path
            with gzip.open(path, 'rb') as f:
                self.circles.cleanup()
                path, self.data, self.circles = pickle.load(f)
        else: 
            self.data = BagLoader(path, None)
            self.circles.cleanup()
            self.circles = CircleRegionManager()
            

        # Set the UI elements that depend on data or need resetting
        self.spinbox.setValue(0)
        self.spinbox.setMaximum(len(self.data.data)-1)
        self.ax_p.set_rmax(self.data.range_max)
        self.ax_p.set_rticks(np.arange(0,self.data.range_max+1, 1.0))  # less radial ticks

        # Open window
        self.show()

        # Re-render everything
        self.on_draw()


    def export(self):
        """ Export labeled data as a mat file
        """
        print "export start"

        # Get the save path
        file_choices = "mat (*.mat)"
        path = unicode(QFileDialog.getSaveFileName(self, 
                        'Export mat', '', 
                        file_choices))
        if not path.endswith(".mat"):
            path = path + ".mat"

        # Get all data into a dict
        data = {'range_max': self.data.range_max, 'theta': self.data.theta}
        data['scans'] = self.data.data
        data['classes'] = []
        for i in range(len(self.data.data)):
            data['classes'].append(self.circles.get_classes(self.data, i))

        # Save data dict
        sio.savemat(path, data)
        print "export done"
        

    def add_actions(self, target, actions):
        for action in actions:
            if action is None:
                target.addSeparator()
            else:
                target.addAction(action)

    def create_action(  self, text, slot=None, shortcut=None, 
                        icon=None, tip=None, checkable=False, 
                        signal="triggered()"):
        action = QAction(text, self)
        if icon is not None:
            action.setIcon(QIcon(":/%s.png" % icon))
        if shortcut is not None:
            action.setShortcut(shortcut)
        if tip is not None:
            action.setToolTip(tip)
            action.setStatusTip(tip)
        if slot is not None:
            self.connect(action, SIGNAL(signal), slot)
        if checkable:
            action.setCheckable(True)
        return action


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

    def scroll(self, event):
        
        delta = 0.1/self.data.range_max
        if event.button == "down":
            delta = -delta  # invert
        print delta
        target = self.circles.get_patch_index(event.xdata, event.ydata)
        if target is not None:
            index = self.spinbox.value()
            self.circles.current[target].resize(delta, index)
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

        if self.data is None:  # Don't get ahead of ourselves
            return

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
        self.ax_p.set_rlabel_position(0)  # get radial labels away from plotted line
        self.ax_p.grid(True)
        self.ax_p.autoscale(False)

        # Patch
        self.circles.render(self.ax_c)

        # Render initial values
        self.lines, = self.ax_p.plot([0], [0],'r-')
        
        # Bind the 'pick' event for clicking on one of the bars
        #
        # self.canvas.mpl_connect('pick_event', self.on_pick)
        self.canvas.mpl_connect('button_press_event', self.press)
        self.canvas.mpl_connect('motion_notify_event', self.motion)
        self.canvas.mpl_connect('button_release_event', self.release)
        self.canvas.mpl_connect('scroll_event', self.scroll)
        
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
        self.spinbox.setRange(0, 0)
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
    app = QApplication(sys.argv)
    form = AppForm()
    form.show()
    app.exec_()

if __name__ == "__main__":
    main()
