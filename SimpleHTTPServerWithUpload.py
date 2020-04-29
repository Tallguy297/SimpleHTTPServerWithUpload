#!/usr/bin/env python3
 
"""Simple HTTP Server With Upload.

This module builds on http.server by implementing the standard GET
and HEAD requests in a fairly straightforward manner.

see: https://gist.github.com/UniIsland/3346170
"""
 
 
__version__ = "0.1"
__all__ = ["SimpleHTTPRequestHandler"]
__author__ = "bones7456"
__home_page__ = "https://gist.github.com/UniIsland/3346170"
 
import os
import posixpath
import http.server
import socketserver
import urllib.request, urllib.parse, urllib.error
import html
import shutil
import mimetypes
import re
import argparse
import base64

from io import BytesIO

def fbytes(B):
   'Return the given bytes as a human friendly KB, MB, GB, or TB string'
   B = float(B)
   KB = float(1024)
   MB = float(KB ** 2) # 1,048,576
   GB = float(KB ** 3) # 1,073,741,824
   TB = float(KB ** 4) # 1,099,511,627,776

   if B < KB:
      return '{0} {1}'.format(B,'Bytes' if 0 == B > 1 else 'Byte')
   elif KB <= B < MB:
      return '{0:.2f} KB'.format(B/KB)
   elif MB <= B < GB:
      return '{0:.2f} MB'.format(B/MB)
   elif GB <= B < TB:
      return '{0:.2f} GB'.format(B/GB)
   elif TB <= B:
      return '{0:.2f} TB'.format(B/TB)

class SimpleHTTPRequestHandler(http.server.BaseHTTPRequestHandler):
 
    """Simple HTTP request handler with GET/HEAD/POST commands.

    This serves files from the current directory and any of its
    subdirectories.  The MIME type for files is determined by
    calling the .guess_type() method. And can reveive file uploaded
    by client.

    The GET/HEAD/POST requests are identical except that the HEAD
    request omits the actual contents of the file.

    """
 
    server_version = "SimpleHTTPWithUpload/" + __version__
 
    def do_GET(self):
        """Serve a GET request."""
        f = self.send_head()
        if f:
            self.copyfile(f, self.wfile)
            f.close()
 
    def do_HEAD(self):
        """Serve a HEAD request."""
        f = self.send_head()
        if f:
            f.close()
 
    def do_POST(self):
        """Serve a POST request."""
        r, info = self.deal_post_data()
        print((r, info, "by: ", self.client_address))
        f = BytesIO()
        f.write(b'<!DOCTYPE html PUBLIC "-//W3C//DTD HTML 3.2 Final//EN">')
        f.write(b"<html>\n<title>Upload Result Page</title>\n")
        f.write(b"<body>\n<h2>Upload Result Page</h2>\n")
        f.write(b"<hr>\n")
        if r:
            f.write(b"<strong>Success:</strong>")
        else:
            f.write(b"<strong>Failed:</strong>")
        f.write(info.encode())
        f.write(("<br><a href=\"%s\">back</a>" % self.headers['referer']).encode())
        f.write(b"<hr><small>Powered By: bones7456, check new version at ")
        f.write(b"<a href=\"https://gist.github.com/UniIsland/3346170\">")
        f.write(b"here</a>.</small></body>\n</html>\n")
        length = f.tell()
        f.seek(0)
        self.send_response(200)
        self.send_header("Content-type", "text/html")
        self.send_header("Content-Length", str(length))
        self.end_headers()
        if f:
            self.copyfile(f, self.wfile)
            f.close()

    def deal_post_data(self):
        uploaded_files = []   
        content_type = self.headers['content-type']
        if not content_type:
            return (False, "Content-Type header doesn't contain boundary")
        boundary = content_type.split("=")[1].encode()
        remainbytes = int(self.headers['content-length'])
        line = self.rfile.readline()
        remainbytes -= len(line)
        if not boundary in line:
            return (False, "Content NOT begin with boundary")
        while remainbytes > 0:
            line = self.rfile.readline()
            remainbytes -= len(line)
            fn = re.findall(r'Content-Disposition.*name="file"; filename="(.*)"', line.decode())
            if not fn:
                return (False, "Can't find out file name...")
            path = self.translate_path(self.path)
            fn = os.path.join(path, fn[0])
            line = self.rfile.readline()
            remainbytes -= len(line)
            line = self.rfile.readline()
            remainbytes -= len(line)
            try:
                out = open(fn, 'wb')
            except IOError:
                return (False, "Can't create file to write, do you have permission to write?")
            else:
                with out:                    
                    preline = self.rfile.readline()
                    remainbytes -= len(preline)
                    while remainbytes > 0:
                        line = self.rfile.readline()
                        remainbytes -= len(line)
                        if boundary in line:
                            preline = preline[0:-1]
                            if preline.endswith(b'\r'):
                                preline = preline[0:-1]
                            out.write(preline)
                            uploaded_files.append(fn)
                            break
                        else:
                            out.write(preline)
                            preline = line
        return (True, "File '%s' upload success!" % ",".join(uploaded_files))
 
    def send_head(self):
        """Common code for GET and HEAD commands.

        This sends the response code and MIME headers.

        Return value is either a file object (which has to be copied
        to the outputfile by the caller unless the command was HEAD,
        and must be closed by the caller under all circumstances), or
        None, in which case the caller has nothing further to do.

        """
        path = self.translate_path(self.path)
        f = None
        if os.path.isdir(path):
            if not self.path.endswith('/'):
                # redirect browser - doing basically what apache does
                self.send_response(301)
                self.send_header("Location", self.path + "/")
                self.end_headers()
                return None
            for index in "index.html", "index.htm":
                index = os.path.join(path, index)
                if os.path.exists(index):
                    path = index
                    break
            else:
                return self.list_directory(path)
        ctype = self.guess_type(path)
        try:
            # Always read in binary mode. Opening files in text mode may cause
            # newline translations, making the actual size of the content
            # transmitted *less* than the content-length!
            f = open(path, 'rb')
        except IOError:
            self.send_error(404, "File not found")
            return None
        self.send_response(200)
        self.send_header("Content-type", ctype)
        fs = os.fstat(f.fileno())
        self.send_header("Content-Length", str(fs[6]))
        self.send_header("Last-Modified", self.date_time_string(fs.st_mtime))
        self.end_headers()
        return f
 


    def list_directory(self, path):
        """Helper to produce a directory listing (absent index.html).

        Return value is either a file object, or None (indicating an
        error).  In either case, the headers are sent, making the
        interface the same as for send_head().

        """
        try:
            list = os.listdir(path)
        except os.error:
            self.send_error(404, "No permission to list directory")
            return None
        list.sort(key=lambda a: a.lower())
        f = BytesIO()
        displaypath = html.escape(urllib.parse.unquote(self.path))
        f.write(b'<!DOCTYPE html PUBLIC "-//W3C//DTD HTML 3.2 Final//EN">')
        f.write(("<html>\n<title>Directory listing for %s</title>\n" % displaypath).encode())
        f.write(b'<style type="text/css">\n')
        f.write(b'a { text-decoration: none; }\n')
        f.write(b'a:link { text-decoration: none; font-weight: bold; color: #0000ff; }\n')
        f.write(b'a:visited { text-decoration: none; font-weight: bold; color: #0000ff; }\n')
        f.write(b'a:active { text-decoration: none; font-weight: bold; color: #0000ff; }\n')
        f.write(b'a:hover { text-decoration: none; font-weight: bold; color: #ff0000; }\n')
        f.write(b'table {\n  border-collapse: separate;\n}\n')
        f.write(b'th, td {\n  padding:0px 10px;\n}\n')
        f.write(b'</style>\n')
        f.write(("<body>\n<h2>Directory listing for %s</h2>\n" % displaypath).encode())
        f.write(b"<hr>\n")
        f.write(b"<form ENCTYPE=\"multipart/form-data\" method=\"post\">")
        f.write(b"<input name=\"file\" type=\"file\" multiple/>")
        f.write(b"<input type=\"submit\" value=\"upload\"/></form>\n")
        f.write(b"<hr>\n")
        f.write(b'<table>\n')
        f.write(b'<tr><td><img src="data:image/gif;base64,R0lGODlhGAAYAMIAAP///7+/v7u7u1ZWVTc3NwAAAAAAAAAAACH+RFRoaXMgaWNvbiBpcyBpbiB0aGUgcHVibGljIGRvbWFpbi4gMTk5NSBLZXZpbiBIdWdoZXMsIGtldmluaEBlaXQuY29tACH5BAEAAAEALAAAAAAYABgAAANKGLrc/jBKNgIhM4rLcaZWd33KJnJkdaKZuXqTugYFeSpFTVpLnj86oM/n+DWGyCAuyUQymlDiMtrsUavP6xCizUB3NCW4Ny6bJwkAOw==" alt="[PARENTDIR]" width="24" height="24"></td><td><a href="../" >Parent Directory</a></td></tr>\n')
        for name in list:
            dirimage = 'data:image/gif;base64,R0lGODlhGAAYAMIAAP///7+/v7u7u1ZWVTc3NwAAAAAAAAAAACH+RFRoaXMgaWNvbiBpcyBpbiB0aGUgcHVibGljIGRvbWFpbi4gMTk5NSBLZXZpbiBIdWdoZXMsIGtldmluaEBlaXQuY29tACH5BAEAAAEALAAAAAAYABgAAANdGLrc/jAuQaulQwYBuv9cFnFfSYoPWXoq2qgrALsTYN+4QOg6veFAG2FIdMCCNgvBiAxWlq8mUseUBqGMoxWArW1xXYXWGv59b+WxNH1GV9vsNvd9jsMhxLw+70gAADs='
            fullname = os.path.join(path, name)
            displayname = linkname = name
            fsize = os.path.getsize(fullname)
            fsize = fbytes(fsize)
            # Append / for directories or @ for symbolic links
            if os.path.isdir(fullname):
                dirimage = 'data:image/gif;base64,R0lGODlhGAAYAMIAAP///+jNlr+/v6KXfm5SG2lPGjc3NwAAACH+RFRoaXMgaWNvbiBpcyBpbiB0aGUgcHVibGljIGRvbWFpbi4gMTk5NSBLZXZpbiBIdWdoZXMsIGtldmluaEBlaXQuY29tACH5BAEAAAIALAAAAAAYABgAAANjKLrc/jDKSau9WJbN9y1BKIZFVQzjOHRdsw1wDIMpyYAFke9ELa4Lmm9IWBkUwqHPiFQSmYKkU1U4Rqe1YrWJTUGlWK0VjP12R2Jubx1guwPQqGxOj22DrLzeujD4/4CBgAoJADs='
                displayname = name + "/"
                linkname = name + "/"
                fsize = ''
            if os.path.islink(fullname):
                dirimage = 'data:image/gif;base64,R0lGODlhGAAYAPf/AJaWlpqampubm5ycnJ2dnZ6enp+fn6CgoKGhoaKioqOjo6SkpKWlpaampqioqKmpqaqqqqurq6ysrK2tra6urq+vr7CwsLGxsbKysrOzs7S0tLW1tba2tre3t7i4uLm5ubq6uru7u7y8vL29vb6+vr+/v8LCwsPDw8bGxtDQ0NTU1NXV1dbW1tfX19jY2Nra2tzc3N3d3eDg4OHh4eLi4uPj4+Tk5OXl5efn5+np6erq6uvr6+zs7O7u7u/v7/Dw8PHx8fLy8vPz8/T09PX19fb29vf39/j4+Pr6+vv7+/39/f7+/v///wAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAACwAAAAAGAAYAAAI/wCZCBxIsKDBgwgLrsigwUXChEVGYNBwIYKIJA8LFunwocKGDA8ieMg4kAiHDxRmCGyhIAEKkhtR2iCYYYEAkiNQ3ijYIQGAjDkuVFBJsIcBAhcyttCgoSCQBQcUFMn44gIFEiwE/oAqIAfJIREeQLDAZIeCAwO8IuQRowYSIxQgBFhAoQBatQaFiLCQoQIFCxEMREUwoAEPhEA0dMQwQSwCIEFYpKCR8IfiCjWYgJCr4AhJyx13CFRhQYECGBmRcKwgmmAEBCsyltBQQUfBGwUG4MjoYMOIgjsSIJBAskGGEAR3IEhw4AdJExIeyBCIY/kBHySZLNEwgcGGDQYQNBbPLpAIBgULEhB4AIQ8wRMFBIhQ4j4gADs='
                displayname = name + "@"
            if name.endswith(('.bmp','.gif','.jpg','.png')):
                dirimage = name
            if name.endswith(('.avi','.mpg')):
                dirimage = 'data:image/gif;base64,R0lGODlhGAAYAMIAAP///7+/v7u7u1ZWVTc3NwAAAAAAAAAAACH+RFRoaXMgaWNvbiBpcyBpbiB0aGUgcHVibGljIGRvbWFpbi4gMTk5NSBLZXZpbiBIdWdoZXMsIGtldmluaEBlaXQuY29tACH5BAEAAAEALAAAAAAYABgAAANvGLrc/jAuQqu99BEh8OXE4GzdYJ4mQIZjNXAwp7oj+MbyKjY6ntstyg03E9ZKPoEKyLMll6UgAUCtVi07xspTYWptqBOUxXM9scfQ2Ttx+sbZifmNbiLpbEUPHy1TrIB1Xx1cFHkBW4VODmGNjQ4JADs='
            if name.endswith(('.idx','.srt','.sub')):
                dirimage = 'data:image/gif;base64,R0lGODlhGAAYAPf/AAAbDiAfDSoqHjQlADs+J3sxJ0BALERHMk5LN1pSPUZHRk9NQU1OR05ZUFBRRFVXTVdYTVtVQFlVRFtbSF5bTVZWUltbUFlZVFtcVlxdWl5eWl1gWmBiV2FiXWNhXGRjXWlpYmtqZ2xtZmxsaG5ubHJva3Jzb3J0bHN0b3Z5dHd8eXh4dX18dXx/dnt8e31+eahMP4JdWIdnZox4cpVoYKJkXrxqablwcNA6Otg7O/8AAPwHB/0GBvgODvsMDPMbG/ceHvkSEuYqKvYqKvU2NvM6OvQ6OsFQUNVbW8N4eNd0duNeXu9aWvFUVOVqau1jY+1mZu5mZuh5eYSFgIWGgYaFgIiGgYqKiY6LioyMiY2NiYyMio2OiI6OjZCSjZSQi5OSkJGUkpSVk5WVlJWVlZiZlpiZmJ6emp2dnZSko6GhnKGhoKOjoaKnoqSkpKSmpKWmpaampqqrqKurqKqrqq2sqq6urrSyrrCwsLa3tb63tbi4t7q6ur+/vsCbm96Li9iUlMqursmwr9KwsN69veSCguiMjOiOjuaQkOWVleaXmOGfn+aYmOaamuebm+adneecnOeenuiQkOWgoOWsrOasrOWxseW2tue3t+e8vOi+vsHBwcfHx8jIxs7Mx8nJyMvLy8zMy83NzM7Pzs/Pz9PR0dTU1NXV1dXW1tbW1tfX19bb29jY2NnZ2djb29ra2tvb2tvb29za2tzc3N3d3d7e3t/f3+bCwufDw+fGxuTJyejCwujHx+nHx+vPz+rT0+rU1OrX1+vX1+rY2Ojf3+Hh4eLi4uPj4+Hn5+Tk5OXl5ebm5ufn5+nn5+jo6Onp6erp6evr6+zs7PDn5/Dq6vDt7fHv7/Lu7vPu7vPv7/Dw8PHx8fLy8vPz8/Tx8fbz8/T09PX19fX39/b29vj39/j4+Pn4+Pn5+fr5+fr6+vv7+/z7+/z8/P39/f7+/v/+/v///wAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAACwAAAAAGAAYAAAI/wDhCRxIsKDBgwgTZis00F27hAbRNSpSaSC7ZM6ePQsXjdmzZekKUpOio0lBVShjJXvYjp07gsEm/dLhqKC2aNG2LesES13BXJTg4dLBi2C7kPDSyQFTRY26c8akZbolkJGOaQTZFTO2LA8KCCA+zDFTp4aggVCCmCtYrJUxNiI4nAjh4o2HGW1CrhvCxGC5cOVqvcCgQQUWGRtanOkG75qOQwXbhWvZ7lOZMIGSsJjihY5AYTowFWRnipUtT6BGWIARY8IXPc1eXtIxrKC7cqJCjdJCIcIBAwRoaLqU6IkRHthGnwPzoEGKDBISMHDAZWAvHUTWjaa1J42NAgAELMBAMGCNwHbWekQxqA4VMkBKSokZE8AKtHLpjuHxo0OSQXfuLKJIOHdc0IECFaxgQivpxHGDDpYc9McS5oBTAhxUbNHFFX2I4Q4fR+iwi0GPCCGLK6rYgQYJWZDhBil7cMMJDjpAAg85L8ETCRDVqAONMuGMA0446rDjEzzi5KDDD4j48g48huxAyCqtODNZOeWcM85DAxEDzDcE+YDEK5u0EostbZ2SyizsQASPE4PAo4466TxVZzptuqmLN266GRAAOw=='
            if name.endswith('.iso'):
                dirimage = 'data:image/png;base64,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'
            # Note: a link to a directory displays with @ and links with /
            f.write(('<tr><td><img src="%s" width="24" height="24"></td><td><a href="%s">%s</a></td><td style="text-align:right; font-weight: bold; color:#FF0000">%s</td></tr>\n'
                    % ( dirimage, urllib.parse.quote(linkname), html.escape(displayname) , fsize )).encode())
        f.write(b"</table><hr>\n</body>\n</html>\n")
        length = f.tell()
        f.seek(0)
        self.send_response(200)
        self.send_header("Content-type", "text/html")
        self.send_header("Content-Length", str(length))
        self.end_headers()
        return f

    def translate_path(self, path):
        """Translate a /-separated PATH to the local filename syntax.

        Components that mean special things to the local file system
        (e.g. drive or directory names) are ignored.  (XXX They should
        probably be diagnosed.)

        """
        # abandon query parameters
        path = path.split('?',1)[0]
        path = path.split('#',1)[0]
        path = posixpath.normpath(urllib.parse.unquote(path))
        words = path.split('/')
        words = [_f for _f in words if _f]
        path = os.getcwd()
        for word in words:
            drive, word = os.path.splitdrive(word)
            head, word = os.path.split(word)
            if word in (os.curdir, os.pardir): continue
            path = os.path.join(path, word)
        return path
 
    def copyfile(self, source, outputfile):
        """Copy all data between two file objects.

        The SOURCE argument is a file object open for reading
        (or anything with a read() method) and the DESTINATION
        argument is a file object open for writing (or
        anything with a write() method).

        The only reason for overriding this would be to change
        the block size or perhaps to replace newlines by CRLF
        -- note however that this the default server uses this
        to copy binary data as well.

        """
        shutil.copyfileobj(source, outputfile)
 
    def guess_type(self, path):
        """Guess the type of a file.

        Argument is a PATH (a filename).

        Return value is a string of the form type/subtype,
        usable for a MIME Content-type header.

        The default implementation looks the file's extension
        up in the table self.extensions_map, using application/octet-stream
        as a default; however it would be permissible (if
        slow) to look inside the data to make a better guess.

        """
 
        base, ext = posixpath.splitext(path)
        if ext in self.extensions_map:
            return self.extensions_map[ext]
        ext = ext.lower()
        if ext in self.extensions_map:
            return self.extensions_map[ext]
        else:
            return self.extensions_map['']
 
    if not mimetypes.inited:
        mimetypes.init() # try to read system mime.types
    extensions_map = mimetypes.types_map.copy()
    extensions_map.update({
        '': 'application/octet-stream', # Default
        '.py': 'text/plain',
        '.c': 'text/plain',
        '.h': 'text/plain',
        })
 
parser = argparse.ArgumentParser()
parser.add_argument('--bind', '-b', default='', metavar='ADDRESS',
                        help='Specify alternate bind address '
                             '[default: all interfaces]')
parser.add_argument('port', action='store',
                        default=8000, type=int,
                        nargs='?',
                        help='Specify alternate port [default: 8000]')
args = parser.parse_args()

PORT = args.port
BIND = args.bind
HOST = BIND

if HOST == '':
	HOST = 'localhost'

Handler = SimpleHTTPRequestHandler

with socketserver.TCPServer((BIND, PORT), Handler) as httpd:
	serve_message = "Serving HTTP on {host} port {port} (http://{host}:{port}/) ..."
	print(serve_message.format(host=HOST, port=PORT))
	httpd.serve_forever()
