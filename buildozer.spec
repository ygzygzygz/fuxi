[app]

title = 复习库
package.name = quizreviewer
package.domain = org.example
source.dir = .
source.include_exts = py,png,jpg,kv,atlas
version = 0.1

requirements = python3,kivy
orientation = portrait
osx.python_version = 3
osx.kivy_version = 2.3.1
fullscreen = 0

android.api = 34
android.ndk = 25b
android.sdk = 24

android.add_assets = ./*.txt,./*.kv

android.permissions = INTERNET
android.icon = %(source.dir)s/icon.png
android.add_launcher_icon = True

android.buildtools_version = 34.0.0
android.use_aapt2 = True

android.sdk_path =
android.ndk_path =

[buildozer]

log_level = 2
warn_on_root = 1