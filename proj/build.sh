#!/bin/bash
# Builds dist/RainComb.apk from res/ + AndroidManifest.xml (generate res/raw/watchface.xml first).
# Local: uses the tools in the project root. CI: set BUILD_TOOLS and ANDROID_JAR.
set -e
cd "$(dirname "$0")"; T="$(cd .. && pwd)"
BT="${BUILD_TOOLS:-$T/android-15}"; JAR="${ANDROID_JAR:-$T/android-35/android.jar}"
[ -d "$T/jdk/Contents/Home" ] && export JAVA_HOME="$T/jdk/Contents/Home"
rm -rf build && mkdir -p build dist
# versionCode = minutes since 1970, so every build installs as an update
V=$(( $(date +%s) / 60 ))
sed -E "s/android:versionCode=\"[0-9]+\"/android:versionCode=\"$V\"/" AndroidManifest.xml > build/AndroidManifest.xml
"$BT/aapt2" compile --dir res -o build/res.zip
"$BT/aapt2" link -o build/unsigned.apk -I "$JAR" --manifest build/AndroidManifest.xml build/res.zip
"$BT/zipalign" -f -p 4 build/unsigned.apk build/aligned.apk
source signing/keystore.properties
"$BT/apksigner" sign --ks signing/raincomb.jks --ks-key-alias raincomb --ks-pass "pass:$storePassword" --out dist/RainComb.apk build/aligned.apk
echo "built dist/RainComb.apk (versionCode $V)"
