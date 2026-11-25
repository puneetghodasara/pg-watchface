#!/bin/zsh
# Generate -> validate -> build -> install on the watch -> activate -> screenshot.
# Usage: ./deploy.sh [screenshot-name]     (RC_SHIFT=<h> ./deploy.sh  to test other times of day)
set -e
cd "$(dirname "$0")"; R=$PWD
ADB="$R/platform-tools/adb -s ${WATCH:-192.168.1.78:44767}"
.venv/bin/python tools/make_face.py proj
.venv/bin/python tools/validate.py tools/wff-spec/third_party/wff/specification/documents/2/watchface.xsd proj/res/raw/watchface.xml
proj/build.sh >/dev/null
$=ADB install -r proj/dist/RainComb.apk | tail -1
$=ADB shell am broadcast -a com.google.android.wearable.app.DEBUG_SURFACE --es operation set-watchface --es watchFaceId app.raincomb.watchface | tail -1
$=ADB shell input keyevent KEYCODE_WAKEUP; sleep 4
$=ADB exec-out screencap -p > "shots/${1:-latest}.png"; echo "shots/${1:-latest}.png"
