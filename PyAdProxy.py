# -*- coding: UTF-8 -*-
# Copyright (C) 2004, 2007.  Joshua P. MacDonald
#
#  This program is free software; you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published by
#  the Free Software Foundation; either version 2 of the License, or
#  (at your option) any later version.
#
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with this program; if not, write to the Free Software
#  Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA

import sys
reload(sys)
sys.setdefaultencoding('utf-8')

__version__ = '0.0.2.1'

__doc__ = ur"""python广告过滤代理(PyAdProxy) V """ + __version__ + """

授权协议：GPL2
维护者：GameXG(GamexG@Gmail.Com)
项目主页：http://code.google.com/p/pyadproxy/

将浏览器的代理服务器设置为127.0.0.1:8080就可以使用
本广告过滤代理。

本软件使用 wowowow(foulife@gmail.com) 维护的 ChinaList(
Adblock Plus 格式) 广告列表.

注意：目前不支持元素隐藏和白名单

如果需要也可以轻易的添加其他的 Adblock Plus 格式的广告列表。

感谢 wowowow(foulife@gmail.com) 无私维护 ChinaList 列表。
"""


import BaseHTTPServer
import SocketServer
import select
import socket
from urlparse import urlparse
from urlparse import urlunparse
import urllib
import re


class Adblock(object):
    """广告过滤类
"""
    def isAd(self,url):
        for c in self.b_re_list:
            if ( c['re'].search(url) != None) :
                return False            
        for c in self.ad_re_list:
            if ( c['re'].search(url) != None) :
                return True
        return False
    

    
    def __init__(self):
        re_line_end = re.compile('\r\n')
        re_asterisk = re.compile(r'\*') #re.compile(r'([^\\])\*')
        re_question_mark = re.compile(r'\?') #re.compile(r'([^\\])\?')
        re_metacharacter = re.compile(r'(\\|\.|\^|\$|\+|\{|\[|\]|\||\(|\))')
        re_end = re.compile(r'\\\|$')
        
        #{'file':'','line':'','re':''}
        self.ad_re_list = []
        self.b_re_list = [{'re':re.compile('url\?url=')},{'re':re.compile('jumpurl=')},]

        
        ad_source_list = ({'name':'adblock-chinalist','url':'http://adblock-chinalist.googlecode.com/svn/trunk/adblock.txt'},)
        
        for c_list in ad_source_list:
            txt = re_line_end.sub('\n', (urllib.urlopen(c_list['url'],proxies={})).read())
            ad_lines = txt.split('\n')
            #去除选项、空白行、注释、版本、白名单和隐藏
            ad_lines = [((c.split('$'))[0]) for c in ad_lines if ((len(c)!=0) and ((c[0] in ('!','[','@',)) == False) and (c.find('#') < 0))]
            b_lines = [ ((c[3]== '|') and (((c[3:]).split('$'))[0]) or (((c[2:]).split('$'))[0])) for c in ad_lines if ((len(c)!=0) and (c[0:2]=='@@'))]
            #追加正则表达式
            self.ad_re_list += [{'re':re.compile(c[1:-1])} for c in ad_lines if(c[0]=='/' and c[-1]=='/')]
            self.b_re_list += [{'re':re.compile(c[1:-1])} for c in b_lines if(c[0]=='/' and c[-1]=='/')]
            #追加普通匹配(转换元字符、转换*和?)
            self.ad_re_list += [{'re':re.compile(re_question_mark.sub(r'.',re_asterisk.sub(r'.*',re_end.sub(r'$',re_metacharacter.sub(r'\\\1',c)))))} for c in ad_lines if(c[0]!='/' or c[-1]!='/')]
            self.b_re_list += [{'re':re.compile(re_question_mark.sub(r'.',re_asterisk.sub(r'.*',re_end.sub(r'$',re_metacharacter.sub(r'\\\1',c)))))} for c in b_lines if(c[0]!='/' or c[-1]!='/')]
            



class ProxyHandler (BaseHTTPServer.BaseHTTPRequestHandler):
    rbufsize = 0
    server_version = "PyAdProxy/" + __version__
    error_message_format = """\
<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Strict//EN" 
 "http://www.w3.org/TR/xhtml1/DTD/xhtml1-strict.dtd">     
<head>
<meta http-equiv="Content-Type" content="text/html; charset=UTF-8" /> 
<title>错误响应</title>
</head>
<body>
<h1>错误响应</h1>
<p>错误代码 %(code)d.
<p>说明: %(message)s.
<p>错误代码说明: %(code)s = %(explain)s.
</body>
"""

    
    def _read_write(self,soc,c):
        '''转发接收内容'''
        count = 0
        while 1:
            count += 1

            ins,_,exs = select.select([soc,c], [], [soc,c],10)

            if exs:
                break
            if ins:
                for i in ins:
                    if i == soc:
                        out = c
                    else:
                        out = soc
                    b = i.recv(8192)
                    if b:
                        out.sendall(b)
                        count = 0
            else:
                #超时
                break
            if count > 30: break
        
    
    def do_GET(self):
        global ad
        url = urlparse(self.path)
        if ad.isAd(self.path):
            print u'过滤广告\r\n%s' % self.path
            self.send_error(404,u'过滤广告')
            return
        soc = socket.socket(socket.AF_INET, socket.SOCK_STREAM)        
        try:soc.connect((url.hostname,80 or url.port))
        except socket.error,err:
            # 连接服务器失败
            try: msg = err[1]
            except: msg = err
            self.send_error(404, msg)
            return          
        soc.sendall('%s %s %s\r\n' % (
                            self.command,
                            urlunparse(('', '', url.path, url.params, url.query, '')),
                            self.request_version
                          ))
        self.headers['Connection'] = 'close'
        del self.headers['Proxy-Connection']
        for kv in self.headers.items():
            soc.sendall('%s:%s\r\n' % kv)
        soc.sendall('\r\n')
        self._read_write(soc,self.connection)
        
        soc.close()
        self.connection.close()

    def do_CONNECT(self):
        i = self.path.find(':')
        if i>=0:
            host_port = self.path[:i],int(self.path[i+1:])
        else:
            host_port = self.path,80
            
        soc = socket.socket(socket.AF_INET, socket.SOCK_STREAM)        
        try:soc.connect(host_port)
        except socket.error,err:
            # 连接服务器失败
            try: msg = err[1]
            except: msg = err
            self.send_error(404, msg)
            return
        self.wfile.write(self.protocol_version +
                         " 200 Connection established\r\n")
        self.wfile.write("Proxy-agent: %s\r\n" % self.version_string())
        self.wfile.write("\r\n")
        self._read_write(soc,self.connection)
        

        
    do_HEAD = do_GET
    do_POST = do_GET
    do_PUT  = do_GET
    do_DELETE=do_GET
    
    def log_message(self, format, *args):
        pass






class ThreadingHTTPServer (SocketServer.ThreadingMixIn,
                           BaseHTTPServer.HTTPServer): pass


def main():
    print u'PyAdProxy %s(GPL2授权协议) 正在启动' % __version__
    
    print u'开始下载并处理广告列表...'
    global ad
    ad = Adblock()
    
    print u'开始启动代理...'
    
    #监听地址
    server_address = ('127.0.0.1', 8080)
    ProxyHandler.protocol_version = "HTTP/1.0"
    httpd = ThreadingHTTPServer(server_address, ProxyHandler)
    
    sa = httpd.socket.getsockname()
    print u"代理服务器工作在 %s:%d" % (sa[0],sa[1])
    print u'将浏览器的代理服务器设置为 %s:%d 即可使用本广告过滤代理。\r\n' % (sa[0],sa[1])
    httpd.serve_forever()



if __name__ == "__main__":
    if len(sys.argv) > 1:
        print __doc__
        sys.exit()
    main()
