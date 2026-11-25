# pg-watchface (Rain Comb)

A two-tone Watch Face Format (WFF v2) watch face for Wear OS, built for a Galaxy Watch5.

- **Main screen:** date; sky, temperature and one alert (rain soon, UV, rain chance); time;
  next calendar event; sleep (mornings) or steps, plus heart rate; an 8-hour forecast "comb"
  along the bottom edge, replaced by tomorrow's forecast in the evening.
- **Always-on:** minimal analog face with the date.

## Layout

| Path | What |
|---|---|
| `tools/make_face.py` | Generates `proj/res/raw/watchface.xml` and `strings.xml` |
| `tools/validate.py` | Checks the XML against Google's WFF schema |
| `proj/` | Android resources, manifest and `build.sh` (aapt2 + apksigner, no Gradle) |
| `tools/make_preview.py` | Turns a watch screenshot into the face-picker thumbnail `preview.png` |
| `deploy.sh` | Local: generate, validate, build, install on the watch over Wi-Fi, screenshot |

Test switches for `deploy.sh`: `RC_SHIFT=<hours>` (layout behaves as if it were later) and
`RC_FAKE=rain_soon|uv_later|rain_pct` (fixed worst-case weather).

## CI

Every push builds a signed APK (Actions → run → Artifacts). Signing uses the repository secrets
`KEYSTORE_B64` and `KEYSTORE_PROPERTIES`, so every build installs as an update.

Fonts: Inter and Outfit, SIL Open Font License.
