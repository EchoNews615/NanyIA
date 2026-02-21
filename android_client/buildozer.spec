[app]
title = NanyIA Mobile
package.name = nanyia
package.domain = org.nany
source.dir = .
source.include_exts = py,png,jpg,kv,atlas
version = 0.2
requirements = python3,kivy,requests
orientation = portrait
android.permissions = INTERNET,RECORD_AUDIO,FOREGROUND_SERVICE,WAKE_LOCK
services = nanyia_service:service.py

[buildozer]
log_level = 2
warn_on_root = 1
