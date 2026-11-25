package app.pg.watchface

import android.content.Context
import android.os.ParcelFileDescriptor
import android.util.Log
import androidx.wear.watchfacepush.WatchFacePushManagerFactory
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import org.json.JSONObject
import java.io.File
import java.net.HttpURLConnection
import java.net.URL

/**
 * Checks the latest GitHub release of the face and installs or updates it through Watch Face Push.
 *
 * Release contract (made by the CI workflow): tag "face-<versionCode>", assets
 * "RainComb.apk" and "RainComb_token.txt" (Watch Face Push validation token).
 */
object Updater {
    private const val TAG = "PgWatchface"
    private const val LATEST = "https://api.github.com/repos/puneetghodasara/pg-watchface/releases/latest"
    const val FACE_PACKAGE = "app.pg.watchface.watchfacepush.raincomb"

    suspend fun checkAndUpdate(context: Context): String = withContext(Dispatchers.IO) {
        val manager = WatchFacePushManagerFactory.createWatchFacePushManager(context)

        val release = JSONObject(httpText(LATEST))
        val tag = release.getString("tag_name")
        val remoteVersion = tag.removePrefix("face-").toLongOrNull()
            ?: return@withContext log("Latest release '$tag' is not a face release")
        var apkUrl: String? = null
        var tokenUrl: String? = null
        val assets = release.getJSONArray("assets")
        for (i in 0 until assets.length()) {
            val a = assets.getJSONObject(i)
            when (a.getString("name")) {
                "RainComb.apk" -> apkUrl = a.getString("browser_download_url")
                "RainComb_token.txt" -> tokenUrl = a.getString("browser_download_url")
            }
        }
        if (apkUrl == null || tokenUrl == null) return@withContext log("Release $tag is missing its files")

        val installed = manager.listWatchFaces().installedWatchFaceDetails
            .firstOrNull { it.packageName == FACE_PACKAGE }
        if (installed != null && installed.versionCode.toLong() >= remoteVersion) {
            return@withContext log("Up to date ($remoteVersion)")
        }

        val apk = File(context.cacheDir, "face.apk")
        download(apkUrl, apk)
        val token = httpText(tokenUrl).trim()
        ParcelFileDescriptor.open(apk, ParcelFileDescriptor.MODE_READ_ONLY).use { fd ->
            if (installed == null) {
                val details = manager.addWatchFace(fd, token)
                runCatching { manager.setWatchFaceAsActive(details.slotId) }
                    .onFailure { Log.w(TAG, "Could not make the face active", it) }
            } else {
                manager.updateWatchFace(installed.slotId, fd, token)
            }
        }
        apk.delete()
        log(if (installed == null) "Installed $remoteVersion" else "Updated to $remoteVersion")
    }

    private fun log(msg: String): String {
        Log.i(TAG, msg)
        return msg
    }

    private fun open(url: String): HttpURLConnection {
        var u = URL(url)
        repeat(5) {
            val c = u.openConnection() as HttpURLConnection
            c.instanceFollowRedirects = false
            c.connectTimeout = 15_000
            c.readTimeout = 30_000
            c.setRequestProperty("User-Agent", "pg-watchface-updater")
            c.setRequestProperty("Accept", "application/vnd.github+json, application/octet-stream")
            if (c.responseCode in 300..399) {
                u = URL(u, c.getHeaderField("Location"))
                c.disconnect()
            } else {
                if (c.responseCode != 200) error("HTTP ${c.responseCode} for $u")
                return c
            }
        }
        error("Too many redirects for $url")
    }

    private fun httpText(url: String): String = open(url).inputStream.use { it.readBytes().decodeToString() }

    private fun download(url: String, to: File) = open(url).inputStream.use { input ->
        to.outputStream().use { input.copyTo(it) }
    }
}
