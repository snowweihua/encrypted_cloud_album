#  encrypted_cloud_album
a private album based on tencent/baidu qcloud_cos and leancloud

This is a mini program to satisfy with my personal requirement: how to store my photoes on cloud without security warning and also provide fast searching.Then I use tencent qcound_cos (cloud object storage) for photo files storage, leancloud for photo information database, and GnuPG for photo files encryption.

File path structure: /Year/Month/

File date source priority: file name > EXIF info > file modify time

How To Use

==========

1.Install GnuPG, import your keys.

2.Copy GnuPG home path and key name into program

3.Install qcloud_cos, leancloud, gnupg, exifread in python

4.Command
usage: cloud_album.py [-h] [-dc] [-du] [-fc] [-fu] [-bd] photofiles [photofiles ...]

positional arguments:

  photofiles      photo files directory or file
  

optional arguments:

  -h, --help      show this help message and exit
  
  -dc, --dcheck   database check only
  
  -du, --dupdate  database check and update
  
  -fc, --fcheck   file storage check only
  
  -fu, --fupload  file storage check and upload
  
  -bd, --baiduyun baidu yun storage
  
  
