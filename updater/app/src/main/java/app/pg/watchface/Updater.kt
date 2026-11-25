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
 * Checks the latest GitHub release, updates the face through Watch Face Push, then updates this app itself.
 *
 * Release contract (made by the CI workflow): tag "face-<versionCode>", assets
 * "RainComb.apk", "RainComb_token.txt" (Watch Face Push validation token),
 * "PgWatchface-installer.apk" (this app) and "release.json" ({"face": n, "installer": n}).
 */
object Updater {
    const val TAG = "PgWatchface"
    private const val LATEST = "https://api.github.com/repos/puneetghodasara/pg-watchface/releases/latest"
    const val FACE_PACKAGE = "app.pg.watchface.watchfacepush.raincomb"

    /** [interactive]: started from the app screen, so a system install prompt may be shown. */
    suspend fun checkAndUpdate(context: Context, interactive: Boolean): String = withContext(Dispatchers.IO) {
        val release = JSONObject(httpText(LATEST))
        val tag = release.getString("tag_name")
        val assets = mutableMapOf<String, String>()
        val list = release.getJSONArray("assets")
        for (i in 0 until list.length()) {
            val a = list.getJSONObject(i)
            assets[a.getString("name")] = a.getString("browser_download_url")
        }
        val face = updateFace(context, tag, assets)
        // Last: a successful self-update restarts this process.
        val app = runCatching { updateSelf(context, assets, interactive) }
            .getOrElse { Log.w(TAG, "App update failed", it); "App update failed: ${it.message}" }
        log("$face\n$app")
    }

    private suspend fun updateFace(context: Context, tag: String, assets: Map<String, String>): String {
        val remoteVersion = tag.removePrefix("face-").toLongOrNull() ?: return "Latest release '$tag' is not a face release"
        val apkUrl = assets["RainComb.apk"]
        val tokenUrl = assets["RainComb_token.txt"]
        if (apkUrl == null || tokenUrl == null) return "Release $tag is missing its face files"

        val manager = WatchFacePushManagerFactory.createWatchFacePushManager(context)
        val installed = manager.listWatchFaces().installedWatchFaceDetails
            .firstOrNull { it.packageName == FACE_PACKAGE }
        if (installed != null && installed.versionCode.toLong() >= remoteVersion) return "Face up to date ($remoteVersion)"

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
        return if (installed == null) "Face installed ($remoteVersion)" else "Face updated to $remoteVersion"
    }

    private fun updateSelf(context: Context, assets: Map<String, String>, interactive: Boolean): String {
        val current = SelfInstaller.currentVersion(context)
        val infoUrl = assets["release.json"] ?: return "App $current (release has no app version)"
        val apkUrl = assets["PgWatchface-installer.apk"] ?: return "App $current (release has no app)"
        val remote = JSONObject(httpText(infoUrl)).optLong("installer", 0)
        if (remote <= current) return "App up to date ($current)"
        // In the background, don't download again for a version that is already waiting for a tap.
        if (!interactive && SelfInstaller.awaitingConfirmation(context) == remote) {
            return "App update $remote waiting: open the app to finish"
        }
        val apk = File(context.cacheDir, "app.apk")
        download(apkUrl, apk)
        SelfInstaller.install(context, apk, remote, interactive)
        apk.delete()
        return "Updating app to $remote…"
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
