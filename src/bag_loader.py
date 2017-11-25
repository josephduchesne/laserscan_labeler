import rosbag
import numpy as np
import math

class BagLoader():

    def __init__(self, bag_path, topic_name):
        bag = rosbag.Bag(bag_path)

        self.data = []
        self.data_all = []
        self.theta = None
        for topic,msg,t in bag.read_messages(topics=[topic_name]):
            if self.theta is None:
                self.range_max = msg.range_max
                self.theta = np.arange(msg.angle_min, msg.angle_max+msg.angle_increment, msg.angle_increment)
            self.data.append(np.array(msg.ranges))
        bag.close()
        self.length = len(self.data)
        print "Loaded %d laser scan messages" % self.length
    
    def get_cartesian(self, index):
        """
        Return the scaled cartesian on a scale of 0-1,0-1 where .5,.5c is 0,0r
        """
        output = []
        for i in range(len(self.theta)):
            x = math.cos(self.theta[i])*self.data[index][i]/self.range_max/2+0.5
            y = math.sin(self.theta[i])*self.data[index][i]/self.range_max/2+0.5
            output.append([x,y])
        return output
