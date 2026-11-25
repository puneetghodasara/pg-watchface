#!/bin/bash
# Validates proj/dist/RainComb.apk with Google's Watch Face Push validator, writes proj/dist/RainComb_token.txt,
# and bundles the face + token into the updater app as its default watch face.
set -e
cd "$(dirname "$0")/.."
JAR=tools/bin/validator-push-cli.jar
[ -f $JAR ] || { mkdir -p tools/bin; curl -sSL -o $JAR https://dl.google.com/android/maven2/com/google/android/wearable/watchface/validator/validator-push-cli/1.1.0-alpha01/validator-push-cli-1.1.0-alpha01.jar; }
J=java; [ -x jdk/Contents/Home/bin/java ] && J=jdk/Contents/Home/bin/java
OUT=$($J -jar $JAR --apk_path=proj/dist/RainComb.apk --package_name=app.pg.watchface 2>&1)
TOKEN=$(echo "$OUT" | sed -n 's/.*generated token: //p' | tr -d '[:space:]')
[ -n "$TOKEN" ] || { echo "$OUT"; echo "Watch Face Push validation FAILED"; exit 1; }
echo -n "$TOKEN" > proj/dist/RainComb_token.txt
mkdir -p updater/app/src/main/assets updater/app/src/main/res/values
cp proj/dist/RainComb.apk updater/app/src/main/assets/default_watchface.apk
printf '<?xml version="1.0" encoding="utf-8"?>\n<resources>\n  <string name="default_wf_token" translatable="false">%s</string>\n</resources>\n' "$TOKEN" > updater/app/src/main/res/values/token.xml
echo "token ok: $TOKEN"
