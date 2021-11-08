from tkinter import *
import tkinter.messagebox
from PIL import Image, ImageTk
import socket, threading, sys, traceback, os
import time

from RtpPacket import RtpPacket

CACHE_FILE_NAME = "cache-"
CACHE_FILE_EXT = ".jpg"

class Client:
	INIT = 0
	READY = 1
	PLAYING = 2
	state = INIT
	
	SETUP = 0
	PLAY = 1
	PAUSE = 2
	TEARDOWN = 3

	finish_setup = True
	
	# Initiation..
	def __init__(self, master, serveraddr, serverport, rtpport, filename):
		self.master = master
		self.master.protocol("WM_DELETE_WINDOW", self.handler)
		self.createWidgets()
		self.serverAddr = serveraddr
		self.serverPort = int(serverport)
		self.rtpPort = int(rtpport)
		self.fileName = filename
		self.rtspSeq = 0
		self.sessionId = 0
		self.requestSent = -1
		self.teardownAcked = 0
		self.connectToServer()
		self.frameNbr = 0
		self.rtpSocket = socket.socket(socket.AF_INET,socket.SOCK_DGRAM)
		
	# THIS GUI IS JUST FOR REFERENCE ONLY, STUDENTS HAVE TO CREATE THEIR OWN GUI 	
	def createWidgets(self):
		"""Build GUI."""
		
		# Create Play button		
		self.start = Button(self.master, width=20, padx=3, pady=3)
		self.start["text"] = "Play"
		self.start["command"] = self.playMovie
		self.start.grid(row=1, column=1, padx=2, pady=2)
		
		# Create Pause button			
		self.pause = Button(self.master, width=20, padx=3, pady=3)
		self.pause["text"] = "Pause"
		self.pause["command"] = self.pauseMovie
		self.pause.grid(row=1, column=2, padx=2, pady=2)
		
		# Create Teardown button
		self.teardown = Button(self.master, width=20, padx=3, pady=3)
		self.teardown["text"] = "Teardown"
		self.teardown["command"] =  self.exitClient
		self.teardown.grid(row=1, column=3, padx=2, pady=2)
		
		# Create a label to display the movie
		self.label = Label(self.master, height=19)
		self.label.grid(row=0, column=0, columnspan=4, sticky=W+E+N+S, padx=5, pady=5) 
	
	def exitClient(self):
		"""Teardown button handler."""
	#TODO
		#if self.state != self.INIT:
		self.sendRtspRequest(self.TEARDOWN)	

			# Close window	
		self.master.destroy() 

			# Delete cache
		os.remove(CACHE_FILE_NAME + str(self.sessionId) + CACHE_FILE_EXT) # Delete the cache image from video


	def pauseMovie(self):
		"""Pause button handler."""
	#TODO	
		if self.state == self.PLAYING:
			self.sendRtspRequest(self.PAUSE)
	
	def playMovie(self):
		"""Play button handler."""
	#TODO
		if self.state == self.INIT:
			self.finish_setup = False
			self.sendRtspRequest(self.SETUP)
		
		while not self.finish_setup: pass

		if self.state == self.READY:
			# Create a new thread to listen for RTP packets
			threading.Thread(target=self.listenRtp).start()
			self.playEvent = threading.Event()
			self.playEvent.clear()

			self.sendRtspRequest(self.PLAY)
	
	def listenRtp(self):		
		"""Listen for RTP packets."""
		#TODO
		while True:
			try:
				data = self.rtpSocket.recv(20480)

				if data:
					rtpPacket = RtpPacket()
					rtpPacket.decode(data)

					current_Frame_Number = rtpPacket.seqNum()
					print("Current Frame " + str(current_Frame_Number))

					if current_Frame_Number > self.frameNbr:
						self.frameNbr = current_Frame_Number
						self.updateMovie(self.writeFrame(rtpPacket.getPayload()))
			except:
				if self.playEvent.isSet():
					break
				
				# If already sent teardown request -> close the rtpsocket
				if self.teardownAcked == 1:
					self.rtpSocket.shutdown(socket.SHUT_RDWR)
					self.rtpSocket.close()
					break
					
	def writeFrame(self, data):
		"""Write the received frame to a temp image file. Return the image file."""
	#TODO
		cache = CACHE_FILE_NAME + str(self.sessionId) + CACHE_FILE_EXT
		file = open(cache, "wb")
		file.write(data)
		file.close()

		return cache
	
	def updateMovie(self, imageFile):
		"""Update the image file as video frame in the GUI."""
	#TODO
		image = ImageTk.PhotoImage(Image.open(imageFile))
		self.label.configure(image = image, height = 288)
		self.label.image = image
		
	def connectToServer(self):
		"""Connect to the Server. Start a new RTSP/TCP session."""
	#TODO
		self.rtspSocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
		try:
			server_address = (self.serverAddr, self.serverPort)
			self.rtspSocket.connect(server_address)
		except:
			tkinter.messagebox.showwarning('Connection Failed', 'Connection to \'%s\' failed' %self.serverAddr)
	
	def sendRtspRequest(self, requestCode):
		"""Send RTSP request to the server."""	
		#-------------
		# TO COMPLETE
		#-------------

		# SETUP 
		if requestCode == self.SETUP and self.state == self.INIT:
			threading.Thread(target = self.recvRtspReply).start()

			# Init sequence number
			self.rtspSeq = 1

			# Create and send request
			request = "SETUP " + str(self.fileName) + " RTSP/1.0\nCSeq: " + str(self.rtspSeq) + "\nTransport: RTP/UDP; client_port= " + str(self.rtpPort) 
			self.rtspSocket.send(request.encode("utf-8"))

			self.requestSent = self.SETUP

			print("\nRequest: " + request + "\n")


		# PLAY
		elif requestCode == self.PLAY and self.state == self.READY:
			# Update sequence number
			self.rtspSeq += 1

			# Create and send request
			request = "PLAY " + str(self.fileName) + " RTSP/1.0\nCSeq: " + str(self.rtspSeq) + "\nSession: " + str(self.sessionId)
			self.rtspSocket.send(request.encode("utf-8"))

			self.requestSent = self.PLAY

			print("\nRequest: " + request + "\n")


		# PAUSE
		elif requestCode == self.PAUSE and self.state == self.PLAYING:
			# Update sequence number
			self.rtspSeq += 1

			# Create and send request
			request = "PAUSE " + str(self.fileName) + " RTSP/1.0\nCSeq: " + str(self.rtspSeq) + "\nSession: " + str(self.sessionId)
			self.rtspSocket.send(request.encode("utf-8"))
			
			self.requestSent = self.PAUSE

			print("\nRequest: " + request + "\n")


		# TEARDOWN
		elif requestCode == self.TEARDOWN and not self.state == self.INIT:
			# Update sequence number
			self.rtspSeq += 1

			# Create and send request
			request = "TEARDOWN " + str(self.fileName) + " RTSP/1.0\nCSeq: " + str(self.rtspSeq) + "\nSession: " + str(self.sessionId)
			self.rtspSocket.send(request.encode("utf-8"))
			
			self.requestSent = self.TEARDOWN

			print("\nRequest: " + request + "\n")
		else:
			return
	
	def recvRtspReply(self):
		"""Receive RTSP reply from the server."""
		#TODO
		while True:
			rtsp_reply = self.rtspSocket.recv(1024)

			if rtsp_reply:
				self.parseRtspReply(rtsp_reply.decode("utf-8"))

			if self.requestSent == self.TEARDOWN:
				self.rtspSocket.shutdown(socket.SHUT_RDWR)
				self.rtspSocket.close()
				break
	
	def parseRtspReply(self, data):
		"""Parse the RTSP reply from the server."""
		#TODO
		print("--------------" + 'Data received--------------\n' + data)
		mess = data.split('\n')
		seq = int(mess[1].split(' ')[1])

		# Check whether the sequence number equal to RTSP request
		if seq == self.rtspSeq:
			session = int(mess[2].split(' ')[1])

			# New session
			if self.sessionId == 0:
				self.sessionId = session
			
			# Check whether session receive is the same as RTSP sessionId
			if self.sessionId == session:
				if (int(mess[0].split(' ')[1])) == 200:
					if self.requestSent == self.SETUP:

						# Update RTSP state
						self.state = self.READY
						
						# Open port
						self.openRtpPort()
						self.finish_setup = True

					elif self.requestSent == self.PLAY:
						# Update RTSP state
						self.state = self.PLAYING
					
					elif self.requestSent == self.PAUSE:
						# Update RTSP state
						self.state = self.READY

						# The play thread exits. A new thread is created on resume.
						self.playEvent.set()

					elif self.requestSent == self.TEARDOWN:
						# Update RTSP state
						self.state = self.INIT

						# Turn on the teardown flag
						self.teardownAcked = 1
	
	def openRtpPort(self):
		"""Open RTP socket binded to a specified port."""
		#-------------
		# TO COMPLETE
		#-------------
		# Create a new datagram socket to receive RTP packets from the server
		# self.rtpSocket = ...
		# Set the timeout value of the socket to 0.5sec
		# ...
		self.rtpSocket.settimeout(0.5)

		try:
			server_address = (self.serverAddr,self.rtpPort)
			self.rtpSocket.bind(server_address)
		except:
			tkinter.messagebox.showwarning("Can't bind", "Can't bind to PORT %d" %self.rtpPort)

	def handler(self):
		"""Handler on explicitly closing the GUI window."""
		#TODO
		self.pauseMovie()
		if tkinter.messagebox.askokcancel("Quit client?", "Are you sure to quit?"):
			self.exitClient()
		else: 
			self.playMovie()