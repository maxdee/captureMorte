#-- camLapse.py -- Module to capture and compile pictures incrementaly into a time lapse
#-- each "project" sits in a directory, all pictures video and config are stored there.
#-- frames are taken, saved with the a date and time code, then added to a timelapse.


#!/usr/bin/python
from mplayer import Player, Step
import xml.etree.ElementTree as ET
#from lxml import etree as ET
import subprocess
import os.path
import time
from datetime import datetime
import serial
from serial.tools import list_ports
from sys import stdout


class camlapse(object):
	
 
	def __init__(self, pf): # inits with a file name, if it exists, loads the project, else makes a new one

		pDir = os.path.dirname(os.path.realpath(__file__))+'/'+pf

		subprocess.call("killall PTPCamera", shell=True)

		self.player = Player()
		self.pname = pf
		self.WEEK_FPH = [1,24,60,120,360,720,1440,2880,5760,11520,23040,46080,86400,86400]

		self.lastFrame = datetime.now()
		self.spf = 1
		self.fph = 1
		self.videoSpeed = 1.0
		self.currentVideoSpeed = 0.009

		if os.path.isdir(pDir):
			print "Loading project : %s" % (pf)
			self.loadProject(pf)
		else:
			print "New project : %s" % (pf)
			self.newProject(pf)

	#---------------------------------------------------------------------------
	# Saving and loading
	#---------------------------------------------------------------------------
	def newProject(self, pf):
		# create project folder and support subfolders
		self.projectDir = os.path.dirname(os.path.realpath(__file__))+'/'+pf
		self.pictureDir = self.projectDir+'/'+'pictures'
		self.videoDir = self.projectDir+'/'+'videos'
		self.tmpDir = self.projectDir+'/'+'tmp'
		cmd = 'mkdir ' + self.projectDir
		subprocess.call(cmd, shell=True)
		cmd = 'mkdir ' + self.pictureDir
		subprocess.call(cmd, shell=True)
		cmd = 'mkdir ' + self.videoDir
		subprocess.call(cmd, shell=True)
		cmd = 'mkdir ' + self.tmpDir
		subprocess.call(cmd, shell=True)

		self.frameIndex = 0

		self.startTime = datetime.now()
		self.newXML()

		# do enough to have the first video
		self.doLapse()
		self.doLapse()
		self.doLapse()
		# begin video playback
		self.startVideoPlayback()


	def loadProject(self, pf):

		self.projectDir = pf
		self.pname = pf
		self.pictureDir = self.projectDir+'/'+'pictures'
		self.videoDir = self.projectDir+'/'+'videos'
		self.tmpDir = self.projectDir+'/'+'tmp'
		self.loadXML()

		path, dirs, files = os.walk(self.pictureDir).next()
		self.frameIndex = len(files) + 1
		# begin video playback
		self.startVideoPlayback()

	def saveVideo(self, saveFolder):
		return True # create a copy of the video file to a specific directory

	#---------------------------------------------------------------------------
	# File Management
	#---------------------------------------------------------------------------
	def getPhotoFile(self, id):
		return self.pictureDir+'/'+'%s_photo_%d.jpg' % (self.pname,id)

	def getVideoFile(self):
		return self.videoDir+'/'+'%s_video.mpg' % (self.pname)

	def getVideoFrameFile(self):
		return self.tmpDir+'/'+'%s_videoFrame.mpg' % (self.pname)

	def getXMLfile(self):
		return self.projectDir+'/'+'%s_data.xml' % (self.pname)

	#---------------------------------------------------------------------------
	# XML parts
	#---------------------------------------------------------------------------
	def newXML(self):
		root = ET.Element("clProject")
		sd = ET.SubElement(root, "time")
		sd.set('startTime', self.startTime.strftime("%Y-%m-%d %H:%M:%S"))
		fi = ET.SubElement(root,"stats")
		fi.set('frameCount', str(self.frameIndex))
		self.tree = ET.ElementTree(root)
		self.tree.write(self.getXMLfile())# , pretty_print=True)

	def loadXML(self):
		self.tree = ET.parse(self.getXMLfile())
		sd = self.tree.find('time')
		self.startTime = datetime.strptime(sd.get('startTime'),"%Y-%m-%d %H:%M:%S")

	def updateXML(self):
		#fi = self.tree()
		self.tree.write(self.getXMLfile())#, pretty_print=True)

	#---------------------------------------------------------------------------
	# Camera control
	#---------------------------------------------------------------------------

	def takePhoto(self, id):
		if not os.path.isfile(self.getPhotoFile(id)):
			cmd = 'gphoto2 --quiet --filename %s --capture-image-and-download' % (self.getPhotoFile(id))
			subprocess.call(cmd, shell=True)

	#---------------------------------------------------------------------------
	# Video process
	#---------------------------------------------------------------------------

	def makeVideoFrame(self, id):
		if os.path.isfile(self.getVideoFrameFile()):
			cmd = 'rm '+ self.getVideoFrameFile()
			subprocess.call(cmd, shell=True)
		cmd = 'ffmpeg -loglevel panic -f image2 -i %s -r 25 %s' % (self.getPhotoFile(id), self.getVideoFrameFile())
		subprocess.call(cmd, shell=True)


	def addFrameToVideo(self):
		if not os.path.isfile(self.getVideoFrameFile()):
			cmd = 'mv %s %s' % (self.getVideoFrameFile(), self.getVideoFile()) #if no video exists create one
		else:
			cmd = 'cat %s >> %s' % (self.getVideoFrameFile(), self.getVideoFile())
		subprocess.call(cmd, shell=True)


	#---------------------------------------------------------------------------
	# Video Playback
	#---------------------------------------------------------------------------
	def startVideoPlayback(self):
		self.player.loadfile(self.getVideoFile())
		print "Video File Loaded"
		self.player.pause()
		self.player.fullscreen = 1
		self.player.loop = 0
		self.updateVideo()

	def updateVideo(self):
		self.getPlaybackSpeed()
		if self.videoSpeed > 0.01: # fast enough for mplayer to do the playback
			if self.videoSpeed - self.currentVideoSpeed > 0.0001:
				self.player.pause(0)
				self.player.speed = self.videoSpeed
				self.currentVideoSpeed = self.videoSpeed
				print "Video speed updated"
		else: # step the frames
			self.stepVideo()

	def stepVideo(self):
		td = datetime.now() - self.lastFrame
		if td.seconds > self.spf:
			self.player.pause(0)
			self.player.frame_step()
			self.lastFrame = datetime.now()


	def getPlaybackSpeed(self):
		total = self.getWeek() # 3.5 weeks
		weeks = int(total)
		lrp = total - weeks
		if weeks < len(self.WEEK_FPH)-1:
			a = self.WEEK_FPH[weeks]
			b = self.WEEK_FPH[weeks+1]
			self.fph = self.lerp(a,b,lrp)
		else: self.fph = self.WEEK_FPH[len(self.WEEK_FPH)-1]
		self.spf = 3600/self.fph # seconds per frame
		self.videoSpeed = self.fph/float(90000)  # speed scaler for 25fps


	def lerp(self, a, b, l):
		return a+((b-a)*l)

	#---------------------------------------------------------------------------
	# time stuff
	#---------------------------------------------------------------------------

	def getWeek(self): #return interger of the week!
		td = datetime.now() - self.startTime
		return (td.days/7)+float(td.seconds)/604800
		# number of weeks + current week progress seconds in a week 604800


	#---------------------------------------------------------------------------
	# Accesors
	#---------------------------------------------------------------------------

	def getFrameCount(self):
		return self.frameIndex

	def getTimeElapsed(self):
		return True # calculate and return months/days h:m:s elapsed

	def printStartTime(self):
		print self.startTime

	#---------------------------------------------------------------------------
	# Modifiers
	#---------------------------------------------------------------------------


	#---------------------------------------------------------------------------
	# main Loops
	#---------------------------------------------------------------------------
	def main(self):
		while True:
			self.doLapse()
			self.updateVideo()


	def doLapse(self):
		self.takePhoto(self.frameIndex)
		self.makeVideoFrame(self.frameIndex)
		self.addFrameToVideo()
		self.frameIndex += 1



#/////////////////////////////////////////////////////////////////////
#/////////////////////////////////////////////////////////////////////
#///////////////   flashlight!   /////////////////////////////////////
#/////////////////////////////////////////////////////////////////////
#/////////////////////////////////////////////////////////////////////


class flashLight(object):
    def __init__(self):
        self.maxBright = 254;   
        self.minBright = 20; 
        device = "/foo/"
        # find the arduino
        ports = list(list_ports.comports())
        for x in ports:
            info = x[2].split()
            for y in info:
                if y == "VID:PID=2341:0043" or y == "VID:PID=2341:43":  # linux and mac device id
                    device = x[0]

        self.connected = False
        if device == "/foo":
            print "PROBLEM : Arduino not found, cannot control lights!"
            time.sleep(2)
            self.connected = False
        else :
            self.duino = serial.Serial(device, 9600)
            time.sleep(1) # give it a moment
            self.connected = True
            self.setBright(250)

# add a warning if arduino gets unconnected!

    def sendCommand(self, cmd):
        if self.connected:
            self.duino.write(chr(cmd))

    def setBright(self, bf): 
        self.sendCommand(bf)

    def triggerFlash(self):
        self.sendCommand(255)

    def closePort(self):
        self.duino.close()




if __name__ == '__main__':
		
	TITLE = (
		"   _____         _               _____         _       ",
		"  |     |___ ___| |_ _ _ ___ ___|     |___ ___| |_ ___ ",
		"  |   --| .'| . |  _| | |  _| -_| | | | . |  _|  _| -_|",
		"  |_____|__,|  _|_| |___|_| |___|_|_|_|___|_| |_| |___|",
		"            |_|                 maxD/robocutStudio 2014"
		)

	MINUTES = 1

	for i in range(0,100):
		print(" ")

	for i in TITLE:
		print(i)
		time.sleep(0.3)

	print(" ")
	print(" ")

	print("Existing projects : ")
	subprocess.call('echo */', shell=True)

	print(" ")
	print(" ")

	pname = raw_input("Enter project name : ") or "default_project"

	print pname

	fl = flashLight()
	cl = camlapse(pname)

	time.sleep(1)

	while True:
		for i in range(1,254):
			fl.setBright(i)
			cl.updateVideo()
			info = "\r %% %d Frames : %d  FPH : %d" % (100*(i/254.0),cl.frameIndex,cl.fph)
			stdout.write(info)
			stdout.flush()
			time.sleep(float(MINUTES*60)/254)
		cl.doLapse()
		fl.triggerFlash()



