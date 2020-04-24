#!/bin/bash
cp -v -f SimpleHTTPServerWithUpload.py /bin
cp -v -f SimpleHTTPServerWithUpload.sh /bin
cp -v -f SimpleHTTPServerWithUpload.service /lib/systemd/system
chmod -v +x /bin/SimpleHTTPServerWithUpload.py
chmod -v +x /bin/SimpleHTTPServerWithUpload.sh
chmod -v 644 /lib/systemd/system/SimpleHTTPServerWithUpload.service
systemctl enable SimpleHTTPServerWithUpload
exit