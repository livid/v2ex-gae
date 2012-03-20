# -*- coding: utf8 -*-
import httplib
import md5 as imd5
import base64
import time
import re


METADATA_PREFIX = 'x-upyun-meta-'
DL = '/'


def md5(src):
    m1 = imd5.new()   
    m1.update(src)   
    dest1 = m1.hexdigest() 
    return dest1

def md5file(fobj):
    m = imd5.new()
    while True:
        d = fobj.read(8096)
        if not d:
            break
        m.update(d)
    fobj.seek(0)
    return m.hexdigest()


def merge_meta(headers, metadata):
     final_headers = headers.copy()
     for k in metadata.keys():
        final_headers[METADATA_PREFIX + k] = metadata[k]
     return final_headers

class UpYunException(Exception):
    '''Raised when a Yupoo method fails.

    More specific details will be included in the exception message
    when thrown.
    ''' 

#目录条目类
class FolderItem(object):
    def __init__(self, filename, filetype, size, number):
        self.filename = filename
        self.filetype = filetype
        self.size = size
        self.number = number


class UpYun(object):
    def __init__(self, bucket, username, password):
        self.thehost = 'v0.api.upyun.com'
        self.username = username
        self.password = password
        self.bucket = bucket
        self.upAuth = False
        self.debug = False
        self._tmp_info = None
        self.content_md5 = ''
        self.file_secret = ''

    #版本
    def version(self):
        return '1.0.1'

    #设置待上传文件的 Content-MD5 值（如又拍云服务端收到的文件MD5值与用户设置的不一致，将回报 406 Not Acceptable 错误）
    def setContentMD5(self, vaule):
        self.content_md5 = vaule

    #设置待上传文件的 访问密钥（注意：仅支持图片空！，设置密钥后，无法根据原文件URL直接访问，需带 URL 后面加上 （缩略图间隔标志符+密钥） 进行访问）
    #如缩略图间隔标志符为 ! ，密钥为 bac，上传文件路径为 /folder/test.jpg ，那么该图片的对外访问地址为： http://空间域名/folder/test.jpg!bac
    def setFileSecret(self, vaule):
        self.file_secret = vaule

    #设定api所调用的域名,包括电信,联通,网通,移动,铁通和自动选择
    def setApiDomain(self,thehost):
        self.thehost = thehost

    #设定是否使用又拍签名
    def setAuthType(self,upAuth):
        self.upAuth = upAuth

    def getList(self, path='', headers={}, metadata={}):
        resp = self._net_worker( 'GET', DL+self.bucket+DL+path, '', headers, metadata)
        return resp

    def delete(self, path, headers={}, metadata={}):
        resp = self._net_worker('DELETE',DL+self.bucket+DL+path, '',headers,metadata)
        return resp
     
    #获取空间占用大小
    def getBucketUsage(self, path='', headers={}, metadata={}):
        resp = self.getList(path+'?usage', headers, metadata)
        try:
            resp = int(resp.read()) 
        except Exception, e:
            resp = None
        return resp
    
    #获取某个目录的空间占用大小
    #path目录路径
    def getFolderUsage(self, path='', headers={}, metadata={}):
        resp = self.getBucketUsage(path, headers, metadata)
        return resp
    
    #新建目录
    #path目录路径
    #[auto] 是否自动创建父级目录（最多10级）
    def mkDir(self, path, auto=False, headers={}, metadata={}):
        headers['folder'] = 'create'
        if auto == True :
            headers['mkdir'] = 'true'
        resp = self._net_worker('POST', DL+self.bucket+DL+path, '', headers, metadata)
        if resp.status == 200 :
            return True
        else :
            return False

    #删除目录
    #path目录路径
    def rmDir(self, path, headers={}, metadata={}):
        resp = self.delete(path,headers,metadata)
        if resp.status == 200 :
            return True
        else :
            return False
    
    #读取目录,返回FolderItem
    #path目录路径
    def readDir(self, path='', headers={}, metadata={}):
        resp = self.getList(path, headers, metadata)
        if resp.status == 200 :
            result = re.sub('\t', '\/', resp.read())
            result = re.sub('\n', '\/', result)
            b = result.split('\/')
            i=0
            fis = []
            while i+1<len(b):
                fi = FolderItem(b[i],b[i+1],b[i+2],b[i+3])
                fis.append(fi)
                i+=4    
            return fis
        else :
            return False
        
    #上传文件
    #data 要上传的文件数据
    #path 远程文件的位置
    #[auto] 是否自动创建父级目录（最多10级）
    def writeFile(self, path, data, auto = False, headers={}, metadata={}):
        if auto == True :
            headers['mkdir'] = 'true'
        if type(data) != file :
            headers['Content-Length'] = len(data)
        resp = self._net_worker('PUT',DL+self.bucket+DL+path, data,headers,metadata)
        self._tmp_info = None
        if resp.status == 200 :
            self._tmp_info = {}
            self._tmp_info['x-upyun-width'] = resp.getheader('x-upyun-width')
            self._tmp_info['x-upyun-height'] = resp.getheader('x-upyun-height')
            self._tmp_info['x-upyun-frames'] = resp.getheader('x-upyun-frames')
            self._tmp_info['x-upyun-file-type'] = resp.getheader('x-upyun-file-type')
            return True
        else :
            return False

    #获取上传文件后的信息（仅图片空间有返回数据）
    #key 信息字段名（x-upyun-width、x-upyun-height、x-upyun-frames、x-upyun-file-type）
    #return value or NULL
    def getWritedFileInfo(self, key):
        if self._tmp_info != None and self._tmp_info['x-upyun-width'] :
            return self._tmp_info[key]
        return None
    #读取文件
    #path 所要读取文件地远程路径
    def readFile(self, path, headers={}, metadata={}):
        resp = self.getList(path, headers, metadata)
        if resp.status == 200 :
            return resp.read()
        else :
            return None

    #删除文件
    #path 所要删除文件地远程路径
    def deleteFile(self, path, headers={}, metadata={}):
        resp = self.delete(path,headers,metadata)
        if resp.status == 200 :
            return True
        else :
            return False

    #获取文件信息
    #path 文件的远程路径
    #返回格式为 {'date': unix time, 'type': file | folder, 'size': file size} 或 None
    def getFileInfo(self, path, headers={}, metadata={}):
        resp = self._net_worker( 'HEAD', DL+self.bucket+DL+path, '', headers, metadata)
        if resp.status == 200 :
            rs = {}
            rs['type'] = resp.getheader('x-upyun-file-type')
            rs['size'] = resp.getheader('x-upyun-file-size')
            rs['date'] = resp.getheader('x-upyun-file-date')
            return rs
        else : 
            return None
    
    def _net_worker(self, method, path, data='', headers={}, metadata={}):
        connection = httplib.HTTPConnection(self.thehost)

        if self.content_md5 != '':
            headers['Content-MD5'] = self.content_md5
            self.content_md5 = ''

        if self.file_secret != '':
            headers['Content-Secret'] = self.file_secret
            self.file_secret = ''

        final_headers = merge_meta(headers, metadata)

        if self.upAuth:
            self._add_upyun_auth_header(final_headers,method,path)
        else :
            self._basicAuth(final_headers,self.username,self.password) 

        connection.request(method, path , data, final_headers)

        resp = connection.getresponse()                                                                 
        if self.debug and resp.status != 200 and method != "HEAD" :
            raise UpYunException(u'ERROR: Code:%d,Message:%s'%(resp.status,resp.read()))
        return resp

    #又拍签名认证
    def _add_upyun_auth_header(self, headers, method, uri):
        headers['Date'] = time.strftime("%a, %d %b %Y %X GMT", time.gmtime())
        if 'Content-Length' in headers:
            scr = md5(method+'&'+uri+'&'+headers['Date']+'&'
                      +str(headers['Content-Length'])+'&'+md5(self.password))
        else :
            scr = md5(method+'&'+uri+'&'+headers['Date']+'&'
                      +'0'+'&'+md5(self.password))

        headers['Authorization'] = "UpYun %s:%s" % (self.username, scr)
 
     
    def _basicAuth(self,headers, username, password):
        encode = base64.encodestring(username+':'+password)
        headers['Authorization'] = "Basic %s" % encode.strip()

