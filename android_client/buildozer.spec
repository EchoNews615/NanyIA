[app]
title = NanyIA Mobile
package.name = nanyia
package.domain = org.nany
source.dir = .
source.include_exts = py,png,jpg,kv,atlas
version = 0.4
requirements = python3==3.11.9,kivy==2.3.0,requests
orientation = portrait
android.permissions = INTERNET,RECORD_AUDIO,FOREGROUND_SERVICE,WAKE_LOCK
services = nanyia_service:service.py

# Use recent p4a for Python 3.12 host compatibility (avoids removed 'imp' module issues).
p4a.branch = master

# Keep modern NDK to avoid legacy fallback (r17c) on Codespaces.
android.ndk = 25b

[buildozer]
log_level = 2
warn_on_root = 1
