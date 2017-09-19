#!/usr/bin/env Python  
#coding: utf-8  

import os,time,sys
# 文件加密
import gnupg
## 照片文件信息提取
#from PIL import Image
#from PIL.ExifTags import TAGS
# 对象存储文件上传
import qcloud_cos
from baidupan.baidupan import BaiduPan

# leancloud database
import leancloud
from leancloud import Object
from leancloud import GeoPoint
from leancloud import Query
import exifread

import argparse

import logging
import ConfigParser

alread_upload_count = 0
upload_count = 0
dupdate_count = 0
bucketname = u'photo'
photocount = 0
baiduprefixpath = u'/apps/digit_album'

latitude = ''
longitude = ''
imagemake = ''
imagemodel = ''
imagelength = ''
imagewidth = ''
photodatetime = ''
imageTAGs = ''
photodatetime_exif = ''

import struct
# 支持文件类型 
# 用16进制字符串的目的是可以知道文件头是多少字节 
# 各种文件头的长度不一样，少则2字符，长则8字符 
def typeJPEG(): 
  return { 
    "FFD8FF": "JPEG"} 
    
def typeList(): 
  return { 
    "FFD8FF": "JPEG",
    "89504E47": "PNG",
    "424D": "BMP"} 
   
# 字节码转16进制字符串 
def bytes2hex(bytes): 
  num = len(bytes) 
  hexstr = u"" 
  for i in range(num): 
    t = u"%x" % bytes[i] 
    if len(t) % 2: 
      hexstr += u"0"
    hexstr += t 
  return hexstr.upper() 
   
# 检查是否是JPEG 文件
def isjpgtype(filename): 
  binfile = open(filename, 'rb') # 必需二制字读取 
  tl = typeJPEG() 
  ftype = 'unknown'
  result = 0
  for hcode in tl.keys(): 
    numOfBytes = len(hcode) / 2 # 需要读多少字节 
    binfile.seek(0) # 每次读取都要回到文件头，不然会一直往后读取 
    hbytes = struct.unpack_from("B"*numOfBytes, binfile.read(numOfBytes)) # 一个 "B"表示一个字节 
    f_hcode = bytes2hex(hbytes) 
    if f_hcode == hcode: 
      ftype = tl[hcode] 
      result = 1
      break
  binfile.close() 
  return result  
  
# 检查是否是Photo 文件
def isphototype(filename): 
  binfile = open(filename, 'rb') # 必需二制字读取 
  tl = typeList() 
  ftype = 'unknown'
  result = 0
  for hcode in tl.keys(): 
    numOfBytes = len(hcode) / 2 # 需要读多少字节 
    binfile.seek(0) # 每次读取都要回到文件头，不然会一直往后读取 
    hbytes = struct.unpack_from("B"*numOfBytes, binfile.read(numOfBytes)) # 一个 "B"表示一个字节 
    f_hcode = bytes2hex(hbytes) 
    if f_hcode == hcode: 
      ftype = tl[hcode] 
      result = 1
      break
  binfile.close() 
  return result                  

## 获取文件时间
## 如果是JPEG, 获取拍摄时间； 如果不是，只能用文件修改时间
#def getphototime(filename):
#	photodatetime = ""
#	filemtime = time.strftime("%Y:%m:%d %H:%M:%S",time.localtime(os.path.getmtime(filename)))
#	if isjpgtype(filename):
#		img = Image.open(filename)
#		if hasattr( img, '_getexif' ):
#				exifinfo = img._getexif()
#				if exifinfo != None:
#						for tag, value in exifinfo.items():
#								decoded = TAGS.get(tag, tag)
#								for case in switch(decoded):
#									if case('DateTime'):
#										photodatetime = value
#										break;
#						if photodatetime == "":
##							print filename
#							photodatetime = filemtime
#				else:   # exifinfo == None
#						photodatetime = filemtime
##						print filename + ": jpg no EXIF " + photodatetime
#		else:  # hasattr
#			print filename + ": jpg no attr "
#	else:   # not jpg
#		photodatetime = filemtime
##		print filename + ": " + "not jpg " + photodatetime
#	return photodatetime

# 检查并创建目录
def cos_check_create_folder(path):
	path = '/' + path + '/'
	path = unicode(path, "utf-8")
	if args.baiduyun :
		i = 0
		while i<5 :
			print baiduprefixpath+path
			stat_folder_ret = baiduyundisk.meta(baiduprefixpath+path)
			if stat_folder_ret is None :
				i = i + 1
				print baiduyundisk.quota()
			else :
				stat_folder_ret = eval(stat_folder_ret)
				break
		if i is 5 :
			logger.error("Connection aborted")
			return 0
			
		logger.debug(stat_folder_ret)
#		print stat_folder_ret
		stat_folder_ret_list = stat_folder_ret.get(u'list',0)
		logger.debug(stat_folder_ret_list)
#		print stat_folder_ret_list
		if stat_folder_ret_list != 0 :
			logger.debug("already have folder: " + path)
		else :
			logger.debug("have no folder,create it : " + baiduprefixpath + path)
			create_folder_ret = eval(baiduyundisk.mkdir(baiduprefixpath+path))
			create_folder_ret_path = create_folder_ret.get(u'path',0)
			if create_folder_ret_path != baiduprefixpath + path:		
				logger.error("create folder fail,message: " + 	str(create_folder_ret))
				return 0
			else:
				logger.info("success create new folder: " + baiduprefixpath+path)
	else :
		request = qcloud_cos.cos_request.StatFolderRequest(bucketname, path)
		stat_folder_ret = cos_client.stat_folder(request)
		logger.debug(stat_folder_ret)
		stat_folder_ret_message = stat_folder_ret.get(u'message',0)
		if stat_folder_ret_message == u'SUCCESS':
			logger.debug("already have folder: " + path)
		if stat_folder_ret_message == u'ERROR_CMD_COS_INDEX_ERROR':    # 没有这个目录
			request = qcloud_cos.cos_request.CreateFolderRequest(bucketname, path)
			create_folder_ret = cos_client.create_folder(request)
			create_folder_ret_message = create_folder_ret.get(u'message',0)
			if create_folder_ret_message != u'SUCCESS':		
				logger.error("create folder fail,message: " + 	stat_folder_ret_message)
				return 0
			else:
				logger.info("success create new folder: " + path)
	return 1

# 检查文件
def cos_check_file(remotefilename):
	try:
		remotefilename = unicode(remotefilename, "utf-8")
	except:
		remotefilename = unicode(remotefilename, "gbk")
		
	if args.baiduyun :
		stat_file_ret = eval(baiduyundisk.meta(baiduprefixpath+remotefilename))
	
		logger.debug( stat_file_ret )
		stat_file_ret_list = stat_file_ret.get(u'list',0)
		logger.debug( stat_file_ret_list )
		if stat_file_ret_list != 0 :
			logger.info( "baiduyun already have file: " + remotefilename )
			return 1
		else:
			logger.info( "baiduyun have no file: " + remotefilename )
			return 0
	else :
		request = qcloud_cos.cos_request.StatFileRequest(bucketname, remotefilename)
		stat_file_ret = cos_client.stat_file(request)
	
	#	print stat_file_ret
		stat_file_ret_message = stat_file_ret.get(u'message',0)
		if stat_file_ret_message == u'SUCCESS':
			logger.info( "cos already have file: " + remotefilename )
			return 1
		else:
			logger.info( "cos have no file: " + remotefilename )
			return 0

# 上传文件
def cos_upload_file(remotefilename, localfilename):
	try:
		remotefilename = unicode(remotefilename, "utf-8")
	except:
		remotefilename = unicode(remotefilename, "gbk")
	try:
		localfilename = unicode(localfilename, "utf-8")
	except:
		localfilename = unicode(localfilename, "gbk")
	
	if args.baiduyun :
		localfilename = localfilename.replace('\\','/')
		logger.info( "uploading file :" + remotefilename)
		upload_file_ret = baiduyundisk.upload(filename=localfilename,path=baiduprefixpath+remotefilename)
		logger.info(upload_file_ret)
		logger.info( "finish upload file :" + remotefilename )
#		time.sleep(10)
		try :
			upload_file_ret = eval(upload_file_ret)
		except :
			logger.info( "upload file, fail: " + remotefilename)
			return 0
		upload_file_ret_list = upload_file_ret.get(u'path',0)
		if upload_file_ret_list != 0 :
			logger.debug(upload_file_ret_list)
			logger.info( "success upload file: " + remotefilename )
			return 1
	else :
		request = qcloud_cos.cos_request.UploadFileRequest(bucketname, remotefilename, localfilename)
		i = 0
		while i<10:
			i += 1
			upload_file_ret = cos_client.upload_file(request)
	
			upload_file_ret_message = upload_file_ret.get(u'message',0)
			if upload_file_ret_message == u'SUCCESS':		
				logger.info( "success upload file: " + remotefilename )
				break
			else:
				if upload_file_ret_message == u'ERROR_CMD_COS_FILE_EXIST':
					break
				else:
					logger.error( "upload file fail,message: " + 	upload_file_ret_message	)
					continue
		if i == 10:
			return 0
		else:
			return 1
			

# 查询info
def leancloud_check_info(filename):
	try:
		filename = unicode(filename, "utf-8")
	except:
		filename = unicode(filename, "gbk")
	PictureDB = leancloud.Object.extend('PictureDB')()
	query = leancloud.Query('PictureDB')
	query.equal_to('FileName',filename)

#	findresult = query.find()
	findcount = query.count()
#	print findresult
#	print findcount
	if findcount == 0:
		logger.debug( 'leancloud have no entry of ' + filename )
		return 0
	else:
		logger.info( 'leancloud have entry of ' + filename )
		return 1

# 查询并更新info
def leancloud_check_and_update_info(filename):
	global latitude,longitude,imagemake,imagemodel,imagelength,imagewidth,photodatetime,dupdate_count
	updated = 0
	try:
		filename = unicode(filename, "utf-8")
	except:
		filename = unicode(filename, "gbk")
	PictureDB = leancloud.Object.extend('PictureDB')()
	query = leancloud.Query('PictureDB')
	query.equal_to('FileName',filename)

	findcount = query.count()
	if findcount == 0:
		logger.info( 'leancloud have no entry of ' + filename )
		return 0
	else:
		logger.info( 'leancloud have entry of ' + filename )
	findresult = query.first()
	photodatetime_0 = findresult.get('DateTime')
	if photodatetime_0 != photodatetime:
		updated = 1
		logger.info( "need update DateTime from " + photodatetime_0 + " to " + photodatetime )
		findresult.set('DateTime', photodatetime)
	imagemodel_0 = findresult.get('Model')
	imagemodel_1 = imagemake + ' ' + imagemodel
	if imagemodel_0 != imagemodel_1:
		updated = 1
		logger.info( "need update Model from " + imagemodel_0 + " to " + imagemodel_1 )
		findresult.set('Model', imagemodel_1)  
	filesize_0 = findresult.get('FileSize')
	if filesize_0 != filesize:
		updated = 1
		logger.info( "need update FileSize from " + filesize_0 + " to " + filesize )
		findresult.set('FileSize', filesize)
	imagewidth_0 = findresult.get('ImageWidth')
	if imagewidth_0 != imagewidth:
		updated = 1
		logger.info( "need update ImageWidth from " + imagewidth_0 + " to " + imagewidth )
		findresult.set('ImageWidth', imagewidth)
	imagelength_0 = findresult.get('ImageLength')
	if imagelength_0 != imagelength:
		updated = 1
		logger.info( "need update ImageLength from " + imagelength_0 + " to " + imagelength )
		findresult.set('ImageLength', imagelength)
	latitude_0 = findresult.get('GPSLatitude')
	if latitude_0 != latitude:
		updated = 1
		logger.info( "need update GPSLatitude from " + latitude_0 + " to " + latitude )
		findresult.set('GPSLatitude', latitude)
	longitude_0 = findresult.get('GPSLongitude')
	if longitude_0 != longitude:
		updated = 1
		logger.info( "need update GPSLongitude from " + longitude_0 + " to " + longitude )
		findresult.set('GPSLongitude', longitude)
#	print findcount
	if updated == 1:
		findresult.save()
		dupdate_count = dupdate_count + 1
	else:
		logger.debug('not need update')
	return 1

def parse_gps(titude):
	first_number = titude.split(',')[0]
	print first_number
	if '/' in first_number:
		first_number_parent = first_number.split('/')[0]
		first_number_child = first_number.split('/')[1]
		if float(first_number_child) == 0:
			first_number_result = 0
		else:
			first_number_result = float(first_number_parent) / float(first_number_child)
	else:
		first_number_result = float(first_number)
		
	second_number = titude.split(',')[1]
	if '/' in second_number:
		second_number_parent = second_number.split('/')[0]
		second_number_child = second_number.split('/')[1]
		if float(second_number_child) == 0:
			second_number_result = 0
		else:
			second_number_result = float(second_number_parent) / float(second_number_child)
	else:
		second_number_result = float(second_number)

	third_number = titude.split(',')[2]
	if '/' in third_number:
		third_number_parent = third_number.split('/')[0]
		third_number_child = third_number.split('/')[1]
		if float(third_number_child) == 0:
			third_number_result = 0
		else:
			third_number_result = float(third_number_parent) / float(third_number_child)
	else:
		third_number_result = float(third_number)

	return first_number_result + second_number_result/60 + third_number_result/3600
  
def getExif(filename):
	global latitude,longitude,imagemake,imagemodel,imagelength,imagewidth,photodatetime_exif
	fd = open(filename, 'rb')
	tags = exifread.process_file(fd, details=False)  #Don’t process makernote tags, don’t extract the thumbnail image
	fd.close()
	if tags == {}:
		logger.info('no EXIF')
		latitude = ''
		longitude = ''
		imagemake = ''
		imagemodel = ''
		imagelength = ''
		imagewidth = ''
		photodatetime_exif = ''
	else :
		logger.debug(tags)
		if 'GPS GPSLatitude' in tags:
			latitude = tags['GPS GPSLatitude'].printable[1:-1]
			logger.info('GPS GPSLatitude: ' + latitude)
#			latitude = parse_gps(latitudeStr)
#			print latitude
		if 'GPS GPSLongitude' in tags:
			longitude = tags['GPS GPSLongitude'].printable[1:-1]
			logger.info( 'GPS GPSLongitude: ' + longitude )
#			longitude = parse_gps(longitudeStr)
#			print longitude
		if 'Image Make' in tags:
			imagemake = tags['Image Make'].printable
			logger.info( 'Image Make: ' + imagemake )
		if 'Image Model' in tags:
			imagemodel = tags['Image Model'].printable
			logger.info( 'Image Model: ' + imagemodel )
		if 'EXIF ExifImageLength' in tags:
			imagelength = tags['EXIF ExifImageLength'].printable
			logger.info( 'EXIF ExifImageLength: ' + imagelength )
		if 'EXIF ExifImageWidth' in tags:
			imagewidth = tags['EXIF ExifImageWidth'].printable
			logger.info( 'EXIF ExifImageWidth: ' + imagewidth)
		if 'Image ImageLength' in tags:
			imagelength = tags['Image ImageLength'].printable
			logger.info( 'Image ImageLength: ' + imagelength)
		if 'Image ImageWidth' in tags:
			imagewidth = tags['Image ImageWidth'].printable
			logger.info( 'Image ImageWidth: ' + imagewidth )
		if 'Image DateTime' in tags:
			photodatetime_exif = tags['Image DateTime'].printable
			logger.info( 'Image DateTime: ' + photodatetime_exif )

# 创建info
def leancloud_create_info(filename):
	try:
		filename = unicode(filename, "utf-8")
	except:
		filename = unicode(filename, "gbk")
	PictureDB = Object.extend('PictureDB')()
	PictureDB.set('FileName', filename)
	PictureDB.set('DateTime', photodatetime)
	PictureDB.set('Model', imagemake + ' ' + imagemodel)  
	PictureDB.set('FileSize', filesize)  
	PictureDB.set('ImageWidth', imagewidth)  
	PictureDB.set('ImageLength', imagelength)  
	PictureDB.set('GPSLatitude', latitude)  
	PictureDB.set('GPSLongitude', longitude)  
	PictureDB.save()

	logger.info( 'create entry of ' + filename )

def get_file_info(totalfilename,filename):
	global photodatetime,photodatetime_exif,photocount
	program_end = time.clock()  
	logger.info( '%d,run %f m' %(photocount,(program_end - program_start)/60) )
	logger.info( filename )
	filesize = os.path.getsize(totalfilename)
	(shotname,extension) = os.path.splitext(filename)
	getExif(totalfilename)

	# 获取文件时间作为目录
#	photodatetime = getphototime(totalfilename)
	try:
		photodatetime = time.strftime("%Y:%m:%d %H:%M:%S",time.strptime(shotname,"%Y-%m-%d %H.%M.%S"))  #GT-5570
		logger.info( "From filename " + photodatetime )
	except:
		try:
			photodatetime = time.strftime("%Y:%m:%d %H:%M:%S",time.strptime(shotname,"%Y%m%d_%H%M%S")) #i9100
			logger.info( "From filename " + photodatetime )
		except:
			try:
				photodatetime = time.strftime("%Y:%m:%d %H:%M:%S",time.strptime(shotname,"IMG_%Y%m%d_%H%M%S")) #M812
				logger.info( "From filename " + photodatetime )
			except:
				if photodatetime_exif == '' or photodatetime_exif == "0000:00:00 00:00:00":
						photodatetime = time.strftime("%Y:%m:%d %H:%M:%S",time.localtime(os.path.getmtime(totalfilename)))
						logger.info( "From modifytime " + photodatetime )
				else:
					photodatetime = photodatetime_exif
					logger.info( "From EXIF " + photodatetime )

#	print filename + ": " + photodatetime
	timeArray = time.strptime(photodatetime, "%Y:%m:%d %H:%M:%S")
	photodateYear = time.strftime("%Y", timeArray)
	photodateMonth = time.strftime("%m", timeArray)
#	print filename + ": " + photodatetime + ": " + photodateYear + ": " + photodateMonth
	photodateYearMonth = photodateYear + '/' + photodateMonth
	remotefilename = '/' + photodateYearMonth + '/' + filename + '.gpg'
	return (filesize, photodateYear, photodateYearMonth, remotefilename)

#def main():
if __name__ == '__main__':  
	
	program_start = time.clock()  
	parser = argparse.ArgumentParser()
	parser.add_argument('-dc','--dcheck', dest='dcheck', help='database check only',action='store_true')
	parser.add_argument('-du','--dupdate', dest='dupdate', help='database check and update',action='store_true')
	parser.add_argument('-fc','--fcheck', dest='fcheck', help='file storage check only',action='store_true')
	parser.add_argument('-fu','--fupload', dest='fupload', help='file storage check and upload',action='store_true')
	parser.add_argument('-bd','--baiduyun', dest='baiduyun', help='baidu yun storage',action='store_true')
	parser.add_argument('photofiles', nargs = '+', help='photo files directory or file' )
	args = parser.parse_args()
	

	# CRITICAL > ERROR > WARNING > INFO > DEBUG > NOTSET
	logging.basicConfig( #filename = "D:\\tmp\\cloud_album_log.txt",
						level=logging.WARNING, 
						format='%(asctime)s %(levelname)s %(message)s',
						datefmt='%Y:%m:%d %H:%M:%S',
						filemode='w')   
						       
	logger = logging.getLogger('mylogger')
	
	cp = ConfigParser.SafeConfigParser()
	cp.read('cloud_album.conf')
	
	gpgkeyname = cp.get('gnupg','keyname')
	gpg = gnupg.GPG(gnupghome=cp.get('gnupg','home'))
	
	appid = int(cp.get('cos','appid'))
	secretid = unicode(cp.get('cos','secretid'), "utf-8")
	secretkey = unicode(cp.get('cos','secretkey'), "utf-8")
	
	cos_client = qcloud_cos.CosClient(appid,secretid,secretkey)
	
	access_token = unicode(cp.get('baiduyun','access_token'), "utf-8")
	baiduyundisk = BaiduPan(access_token)
	
	leancloud.init(cp.get('leancloud','appid'), cp.get('leancloud','appkey'))
	logger.setLevel(logging.INFO)
	
	#print args.photofiles
	if os.path.isfile(args.photofiles[0]):
		totalfilename = args.photofiles[0]
		p,photofile=os.path.split(totalfilename)
		if not isphototype(totalfilename):
			logger.error( 'Not photo : ' + photofile )
			sys.exit(0)
	
		(filesize, photodateYear, photodateYearMonth, remotefilename) = get_file_info(totalfilename, photofile)
	
		# 目录检查并创建
		if not cos_check_create_folder(photodateYear):
			sys.exit(0)
		if not cos_check_create_folder(photodateYearMonth):
			sys.exit(0)
		#检查加密文件是否已经上传
		gpgoutput = totalfilename + '.gpg'
		if not cos_check_file(remotefilename):
			# 加密文件
			with open(totalfilename,'rb') as f:
				status = gpg.encrypt_file(f, recipients=[gpgkeyname],output = gpgoutput)   
				if status.ok != True:
					logger.error( "gpg encryption fail" + totalfilename )
					sys.exit(0)       
				#上传已加密文件 
				if not cos_upload_file(remotefilename, gpgoutput):
					sys.exit(0)  # 上传失败，中断程序
				else:
					upload_count = upload_count + 1
				#删除加密文件
				os.remove(gpgoutput)
	
		# check database
		if not leancloud_check_info(remotefilename):  # 如果没有查询到纪录，则创建纪录
			leancloud_create_info(remotefilename)
			
		sys.exit(0)
	
	#root = "e:\\photo\\20150222_i9100\\"
	photocount = 0
	if not os.path.isdir(args.photofiles[0]):
		logger.error('Error parameter:not path')
		sys.exit(0)
		
	for photofile in os.listdir(args.photofiles[0]):
		totalfilename = args.photofiles[0]
		totalfilename = os.path.join(totalfilename,photofile)
		if os.path.isfile(totalfilename):
			if not isphototype(totalfilename):
				logger.error('Not photo : ' + photofile)
				continue
		
			photocount += 1
			(filesize, photodateYear, photodateYearMonth, remotefilename) = get_file_info(totalfilename, photofile)
	
			# 目录检查并创建
			if not cos_check_create_folder(photodateYear):
				break;
			if not cos_check_create_folder(photodateYearMonth):
				break;
			
			# check database only
			if args.dcheck:
				leancloud_check_info(remotefilename)
				continue
			# check and update database
			if args.dupdate:
				if not leancloud_check_and_update_info(remotefilename):	
					leancloud_create_info(remotefilename)
				continue
				
			#检查加密文件是否已经上传
			gpgoutput = totalfilename + '.gpg'
			if not cos_check_file(remotefilename):
				if args.fcheck:
					continue
				# 加密文件
				with open(totalfilename,'rb') as f:
					status = gpg.encrypt_file(f, recipients=[gpgkeyname],output = gpgoutput)   
					if status.ok != True:
						logger.error( "gpg encryption fail" + totalfilename )
						break;       
					#上传已加密文件 
					if not cos_upload_file(remotefilename, gpgoutput):
						break;  # 上传失败，中断程序
					else:
						upload_count = upload_count + 1
					#删除加密文件
					os.remove(gpgoutput)
			else:
				alread_upload_count = alread_upload_count + 1
			if args.fupload:
				continue
			# check database
			if not leancloud_check_info(remotefilename):  # 如果没有查询到纪录，则创建纪录
				leancloud_create_info(remotefilename)
	
					
							
	
	logger.info( "photocount: %d" %photocount )
	logger.info( "upload_count: %d" %upload_count )
	logger.info( "dupdate_count: %d" %dupdate_count )
	logger.info( "already_upload_count: %d" %alread_upload_count)
	program_end = time.clock()  
	logger.info( "Program run %f m " %((program_end - program_start)/60) )        
