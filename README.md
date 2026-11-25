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

## Installer app and automatic updates

`updater/` is **PG Watchface**, a tiny Wear OS 6 app that installs and updates the face through
Google's Watch Face Push API. It ships the current face as its default, then checks this repo's
latest GitHub Release every few hours (or on "Check now") and updates the face in place.
Pushed faces must use the package `app.pg.watchface.watchfacepush.<name>` and carry a validation
token from Google's `validator-push-cli` (`tools/push_token.sh`).

## CI

Every push to `main` generates and validates the face, builds and signs it, creates its Watch Face
Push token, builds the installer, and publishes a release `face-<versionCode>` with
`RainComb.apk`, `RainComb_token.txt` and `PgWatchface-installer.apk`.
Signing uses the repository secrets `KEYSTORE_B64`, `KEYSTORE_PROPERTIES` (face) and
`UPDATER_KEYSTORE_B64`, `UPDATER_PROPERTIES` (installer). Fonts are subset for size
(`tools/subset_fonts.sh`, originals in `tools/fonts-src/`).

Fonts: Inter and Outfit, SIL Open Font License.
