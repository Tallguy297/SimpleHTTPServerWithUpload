#!/usr/bin/env bash

## Restore Database...
rm -f -R 0777 /home/kodi/
cp -v -f -r ../kodicfg/. /home/
chmod -f -R 0777 /home/kodi/
