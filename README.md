# laserscan_labeler
Tool for labeling laser scan data from ROS bags

## Prereqs
On Ubuntu 16.04 (should work on other ubuntu versions, just replace 'kinetic' with 'indigo' etc.:
* `sudo apt-get install python-qt4 python-rosbag ros-kinetic-std-msgs python-numpy python-scipy`

## Usage
To get started run:

`python src/qt_labeler.py`

Then open a bag file containing laser scans. 

### Marking regions
- Click empty space to create a new label region
- Click and drag a region to move it
  - Clicking a region start or end moves the start/end to the new location
  - Clicking a region middle (blue or green) split the region at the current frame
- Regions are interpolated linearly between start and end pose
- Using the scroll wheel over a region enlarges or shrinks the region radius
- Middle clicking a region deletes the end of the region (making it extend to the end of the data)
- Right clicking a region deletes it (moving the end to the previous frame)

### Region color codes
- Teal: Region start frame
- Blue: Region middle frame
- Green: Region goes to end of data
- Red: Region end frame

### Time travel
- Use the buttons to move forward/backward in time (or arrow keys left/right)
- Press space to play/pause the data

## Output format
The output is in the form of a matlab/octave/scipy.io compatible mat file. To load it in python use (scipy.io.loadmat[https://docs.scipy.org/doc/scipy/reference/tutorial/io.html].

Entries:
N=number of scans, C=number of returns per scan

- range_max - float - the max range of the laser scan message
- theta - float array[C] - the angular offset of each point
- scans - float array[N,C]  - the input data - X in typical ML problems
- classes - float array[N,C] - the labeled data - Y in typical ML problems

## Caveats
* The app automatically grabs the first laster scan topic it finds. To run it on other topics, filter out the topic you want using `rosbag filter`
* The app currently only offers binary labeling (0=default, 1=in a marked region)