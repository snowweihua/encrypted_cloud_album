#!/usr/bin/env Python  
#coding: utf-8  
  
from  cloud_album_ui import Ui_MainWindow  
from PyQt4.QtCore import *  
from PyQt4.QtGui import   *  

try:
    _fromUtf8 = QString.fromUtf8
except AttributeError:
    def _fromUtf8(s):
        return s

try:
    _encoding = QApplication.UnicodeUTF8
    def _translate(context, text, disambig):
        return QApplication.translate(context, text, disambig, _encoding)
except AttributeError:
    def _translate(context, text, disambig):
        return QApplication.translate(context, text, disambig)

import sys,os,time
import gnupg
## 照片文件信息提取
#from PIL import Image
#from PIL.ExifTags import TAGS
# 对象存储文件上传
import qcloud_cos
# leancloud database
import leancloud
from leancloud import Object
from leancloud import GeoPoint
from leancloud import Query
import exifread

import argparse

import logging

import ConfigParser

import urllib

import threading
  
class processorThread(QThread):
	processSignal = pyqtSignal()

	def __init__(self):
		QThread.__init__(self)
		self.moveToThread(self)

	def run(self):
		while 1 :
 			self.processSignal.emit()
			time.sleep(20)

class slaveWindow(QDialog):
     
	def __init__(self,parent=None):  
		super(slaveWindow,self).__init__(parent)  
		self.resize(300,300)
#		self.move(200,200)

		self.textedit = QTextEdit()
		buttonbox = QDialogButtonBox(parent=self)
		buttonbox.setOrientation(Qt.Horizontal)
		buttonbox.setStandardButtons(QDialogButtonBox.Cancel|QDialogButtonBox.Ok)
		buttonbox.accepted.connect(self.accept)
		buttonbox.rejected.connect(self.reject)

		layout = QVBoxLayout()
		layout.addWidget(QLabel(u'Please input comment here:'))
		layout.addWidget(self.textedit)
		layout.addWidget(buttonbox)

		self.setLayout(layout)

	def text(self):
		return self.textedit.toPlainText()

class Window(QMainWindow,Ui_MainWindow):  
     
	def __init__(self,parent=None):  
		super(Window,self).__init__(parent)  
		self.setupUi(self)  
		QObject.connect(self.pushButton_prev, SIGNAL("clicked()"), self.change_pb_prev)  
		QObject.connect(self.pushButton_next, SIGNAL("clicked()"), self.change_pb_next) 
		QObject.connect(self.pushButton_auto, SIGNAL("clicked()"), self.change_pb_auto)  
		QObject.connect(self.pushButton_myrating, SIGNAL("clicked()"), self.change_pb_myrating) 
		QObject.connect(self.pushButton_comment, SIGNAL("clicked()"), self.change_pb_comment)  
		QObject.connect(self.pushButton_delete, SIGNAL("clicked()"), self.change_pb_delete) 
		QObject.connect(self.comboBox_viewtype,SIGNAL('activated(int)'), self.onActivatedViewtype)

		self.current_viewtype = 1 # 2 - Best Love Only, 1 - Normal, 0 - All
		self.comboBox_viewtype.setCurrentIndex(self.current_viewtype)

#		self.label.setScaledContents(True) 
#		self.label.resize(self.widget.size())
#		self.label.setSizePolicy(QSizePolicy.Ignored,QSizePolicy.Ignored)  
#		self.setCentralWidget(self.label) 
		self.dateedit_start.setDisplayFormat('yyyy MM dd')
		self.qdate_start=QDate(2003, 7, 1)
		self.dateedit_start.setDate(self.qdate_start)
		self.dateedit_start.dateChanged.connect(self.startDateChanged)

		self.dateedit_end.setDisplayFormat('yyyy MM dd')
#		self.qdate_end=QDate.currentDate()
		self.qdate_end=QDate(2005, 10, 1)
		self.dateedit_end.setDate(self.qdate_end)
		self.dateedit_end.dateChanged.connect(self.endDateChanged)
#		self.currentyear = self.qdate_start.year()
#		self.currentmonth = self.qdate_start.month()
		self.label_dbinfo.setWordWrap(True)

#		self.checkBox_bestloveonly.toggled.connect(self.bestloveonlySetValue)

		#cloud album
		self.cp = ConfigParser.SafeConfigParser()
		self.cp.read('cloud_album.conf')

		logging.basicConfig( #filename = "D:\\tmp\\cloud_album_log.txt",
						level=logging.WARNING, 
						format='%(asctime)s %(levelname)s %(message)s',
						datefmt='%Y:%m:%d %H:%M:%S',
						filemode='w')   
						       
		self.logger = logging.getLogger('mylogger')

		self.gpgkeyname = self.cp.get('gnupg','keyname')
		self.gpg = gnupg.GPG(gnupghome=self.cp.get('gnupg','home'))
		self.passphrase = self.cp.get('gnupg','passphrase')

		appid = int(self.cp.get('cos','appid'))
		secretid = unicode(self.cp.get('cos','secretid'), "utf-8")
		secretkey = unicode(self.cp.get('cos','secretkey'), "utf-8")
		
		self.cos_client = qcloud_cos.CosClient(appid,secretid,secretkey)
		self.bucketname = unicode(self.cp.get('cos','bucketname'), "utf-8")
		self.file_folder_ret_data_context = None
		self.file_folder_ret_data_has_more = True

		leancloud.init(self.cp.get('leancloud','appid'), self.cp.get('leancloud','appkey'))
		self.pictureDB = leancloud.Object.extend('PictureDB')()
		self.query = leancloud.Query('PictureDB')


		self.logger.setLevel(logging.INFO)
		self.first_run_flag = 1
		self.all_path_list = []
		self.scan_all_path()
		print self.all_path_list
		self.all_path_list_count = len(self.all_path_list)
		print self.all_path_list_count
		self.current_index = 0
		self.order = 2 # 0 -- next, 1 -- prev, 2 -- N/A
		self.view_count_in_folder = 0
		self.auto_flag = False # False: stop, True: auto
		self.myratingStr=['NotLove','Normal','Love']

		self.processThread = processorThread()
		self.processThread.processSignal.connect(self.auto_show_slot,Qt.QueuedConnection)
		self.processThread.start()
	
	def bestloveonlySetValue(self,value):
		self.bestloveonly_flag = value

	def startDateChanged(self,date):
		self.qdate_start = date

	def endDateChanged(self,date):
		self.qdate_end = date

	def onActivatedViewtype(self,index):
		self.current_viewtype = index

    # 检查目录
	def cos_check_folder(self):
#		path = '/' + path + '/'
		self.current_path = unicode(self.current_path, "utf-8")
		self.request = qcloud_cos.cos_request.StatFolderRequest(self.bucketname, self.current_path)
		stat_folder_ret = self.cos_client.stat_folder(self.request)
		self.logger.debug(stat_folder_ret)
		stat_folder_ret_message = stat_folder_ret.get(u'message',0)
		if stat_folder_ret_message == u'SUCCESS':
			self.logger.debug("already have folder: " + self.current_path)
		if stat_folder_ret_message == u'ERROR_CMD_COS_INDEX_ERROR':    # 没有这个目录
			self.logger.error("don't have this folder: " + self.current_path)
			return 0
		return 1

	def scan_all_path(self):
		yearstart = self.qdate_start.year()
		yearend = self.qdate_end.year()
		monthstart = self.qdate_start.month()
		monthend = self.qdate_end.month()
		scanyear = yearstart
		scanmonth = monthstart
		while ( scanyear <= yearend ) :
			self.current_path = '/' + str(scanyear) + '/'
			if self.cos_check_folder():
				while ((scanyear==yearend and scanmonth <= monthend) or
						(scanyear < yearend and scanmonth <= 12) ):
					month_str = "%02d" %scanmonth
					self.current_path = '/' + str(scanyear) + '/' + month_str + '/'
					print self.current_path
					if self.cos_check_folder():
						self.all_path_list.append(self.current_path)
					if (scanmonth == 12 ):
						scanmonth = 1
						break
					else:
						scanmonth = scanmonth + 1
			scanyear = scanyear + 1


	def dl_decrypt_show(self,order):
		self.view_count_in_folder = self.view_count_in_folder + 1
		self.current_path = self.all_path_list[self.current_index -1]
		self.request = qcloud_cos.cos_request.ListFolderRequest(self.bucketname, self.current_path)
		self.request.set_num(1)
		self.request.set_order(self.order)
		if self.file_folder_ret_data_has_more == True:
#			print "set_context:" + self.file_folder_ret_data_context
			if self.file_folder_ret_data_context != None :
				self.request.set_context(self.file_folder_ret_data_context)

		self.file_folder_ret = self.cos_client.list_folder(self.request)
		print self.file_folder_ret
		file_folder_ret_message = self.file_folder_ret.get(u'message',0)
		if file_folder_ret_message != u'SUCCESS':
			return False

		file_folder_ret_data = self.file_folder_ret.get(u'data',0)
		self.file_folder_ret_data_context = file_folder_ret_data.get(u'context','not found')
		print "context:" + self.file_folder_ret_data_context
		self.file_folder_ret_data_has_more = file_folder_ret_data.get(u'has_more','not found')
		print self.file_folder_ret_data_has_more

		infos = file_folder_ret_data.get(u'infos',0)
#		if infos == [] :  # do next->pre when first files in folder
#			self.change_pb_prev()
#			return False

		access_url = infos[0].get(u'access_url',0)
		try:
			self.filename = urllib.unquote(access_url).decode('utf8').split('/')[-1]  
		except:
			self.filename = self.file_folder_ret_data_context.split('|')[0]  

		#get leancloud db info
		self.query.equal_to('FileName',self.current_path+self.filename)
		self.findcount = self.query.count()
		if self.findcount != 1 :
			print "findcount !=1" + str(self.findcount)
			info_str = "No found in leancloud database"
		else:
			self.findresult = self.query.first()
			self.db_myrating = self.findresult.get('MyRating')
			self.db_datetime = self.findresult.get('DateTime')
			self.db_model = self.findresult.get('Model')
			self.db_filesize = self.findresult.get('FileSize')
			self.db_imagewidth = self.findresult.get('ImageWidth')
			self.db_imagelength = self.findresult.get('ImageLength')
			self.db_latitude = self.findresult.get('GPSLatitude')
			self.db_longitude = self.findresult.get('GPSLongitude')
			self.db_comment = self.findresult.get('comment')
	#		print "old myrating: %d" %self.currentmyrating
			info_str = "FileSize: %d; DateTime: %s; Model: %s; Resolution: %s*%s; GPS: %s,%s; MyRating: %s; Comment: %s" %(self.db_filesize, self.db_datetime, self.db_model, self.db_imagewidth, self.db_imagelength, self.db_latitude, self.db_longitude, self.myratingStr[self.db_myrating+1], self.db_comment)

		if self.db_myrating + 1 < self.current_viewtype :
			self.logger.debug( "do not show this photo:" + self.filename )
			return

		self.label_dbinfo.setText(_translate("MainWindow", info_str, None))

		#download file 
#		print "debug 1"
		urllib.urlretrieve(access_url, self.filename)
#		print "debug 2"
		de_filename=self.filename.split('.')[0] + '.' + self.filename.split('.')[1]
		print de_filename


		#decrypt file
		with open(self.filename, 'rb') as f:
			status = self.gpg.decrypt_file(f, passphrase=self.passphrase, output = de_filename)   
			if status.ok != True:
				self.logger.error( "gpg decryption fail" + self.filename )

		#show photo
		self.image=QImage(de_filename)
		self.label.setPixmap(QPixmap.fromImage(self.image).scaled(self.label.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation))  

		os.remove(self.filename)
		os.remove(de_filename)

	def change_pb_prev(self):  
		print "view count " + str(self.view_count_in_folder)
		print "index " + str(self.current_index)
		print "order " + str(self.order)

		if (self.first_run_flag == 1 ):
			self.first_run_flag = 0
			self.order = 1
			self.current_index = self.all_path_list_count

		if self.order == 0 : #change from pb_next
			self.order = 1
			if self.view_count_in_folder == 1 :
				self.file_folder_ret_data_has_more = False
			else:
				self.file_folder_ret_data_has_more = True
			if 	self.current_index == self.all_path_list_count + 1 :
				self.current_index = self.all_path_list_count

		if self.file_folder_ret_data_has_more == False:
			self.file_folder_ret_data_context = None
			if self.current_index > 0:
				self.current_index = self.current_index - 1
				self.view_count_in_folder = 0

		if self.current_index == 0 :
			self.logger.info("Head, no more picture")
			return False
			
		self.dl_decrypt_show(1)

          

	def change_pb_next(self):  
		self.logger.debug("view count " + str(self.view_count_in_folder))
		self.logger.debug( "index " + str(self.current_index))
		self.logger.debug( "order " + str(self.order))

		if (self.first_run_flag == 1):
			self.first_run_flag = 0
			self.order = 0
			self.current_index = 1

		if self.order == 1 : #change from pb_prev
			self.order = 0
			if self.view_count_in_folder == 1 :
				self.file_folder_ret_data_has_more = False
			else:
				self.file_folder_ret_data_has_more = True
			if self.current_index == 0:
				self.current_index = self.current_index + 1

		if self.file_folder_ret_data_has_more == False:
			self.file_folder_ret_data_context = None
			if self.current_index < self.all_path_list_count + 1 :
				self.current_index = self.current_index + 1
				self.view_count_in_folder = 0

		if (self.current_index > self.all_path_list_count):
			self.logger.info("Tail, no more picture")
			return False

		self.dl_decrypt_show(0)
		
	@pyqtSlot()
	def auto_show_slot(self):
		if not self.auto_flag :
			return
		self.change_pb_next()
		if (self.current_index > self.all_path_list_count):
			self.logger.info("Tail, recycle again")
			self.current_index = 1

	def change_pb_auto(self):  
			self.auto_flag = not self.auto_flag
			if self.auto_flag :
				self.logger.info("auto show is running")
				self.pushButton_prev.setEnabled(False)
				self.pushButton_next.setEnabled(False)
				self.pushButton_auto.setText(_translate("MainWindow", "Stop", None))
			else:
				self.logger.info("auto show stop")
				self.pushButton_prev.setEnabled(True)
				self.pushButton_next.setEnabled(True)
				self.pushButton_auto.setText(_translate("MainWindow", "Auto", None))


	def change_pb_myrating(self):  
		myrating = QMessageBox(self)
		myrating.setWindowTitle("My Rating")
		lovebutton = myrating.addButton(self.tr("Love"),QMessageBox.ActionRole)
		notlovebutton = myrating.addButton(self.tr("NotLove"),QMessageBox.ActionRole)
		cancelbutton = myrating.addButton("cancel",QMessageBox.ActionRole)
		myrating.setText("Please rating this photo: %s \nCurrent myrating: %s" %(self.current_path+self.filename, self.myratingStr[self.db_myrating+1]))
		myrating.exec_()

		button = myrating.clickedButton()
		newmyrating = 0
		if button == lovebutton :
			print "love rating"
			newmyrating = 1
		elif button == notlovebutton :
			print "notlove rating"
			newmyrating = -1
		else :
			return
		
		if self.findcount != 0 :
			self.findresult.set('MyRating',newmyrating)
			self.findresult.save()
		


	def change_pb_comment(self):  
		comment = slaveWindow()
		comment.show()
		if comment.exec_():
			print comment.text()
			if self.findcount != 0 :
				self.findresult.set('comment',comment.text())
				self.findresult.save()


	def change_pb_delete(self):  
		if self.auto_flag :
			QMessageBox.information(self,"Information",self.tr("Auto view mode, can't delete photo, please turn to manual mode"))
			return

		confirm=QMessageBox.question(self,"Confirm",self.tr("Are you sure to delete this photo"+self.current_path+self.filename), QMessageBox.Ok|QMessageBox.Cancel, QMessageBox.Cancel)
		if confirm == QMessageBox.Ok :
			print "Delete photo:"+self.current_path+self.filename
		elif confirm == QMessageBox.Cancel :
			print "Don't delete"
		else :
			return
  
  
if __name__ == '__main__':  
          
    app = QApplication(sys.argv)  
    form = Window()  
    form.show()  
    app.exec_()       

