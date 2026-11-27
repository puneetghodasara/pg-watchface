package app.pg.watchface

import android.app.PendingIntent
import android.content.BroadcastReceiver
import android.content.Context
import android.content.Intent
import android.content.pm.PackageInstaller
import android.util.Log
import java.io.File

/**
 * Installs a newer build of this app over itself with the platform PackageInstaller.
 *
 * An app updating itself may skip the confirmation dialog (USER_ACTION_NOT_REQUIRED plus the
 * UPDATE_PACKAGES_WITHOUT_USER_ACTION permission). If the system still wants a tap, the prompt is
 * shown only when the update was started from the app screen; background checks just remember it.
 */
object SelfInstaller {
    private const val PREFS = "self_update"
    private const val KEY_WAITING = "waiting_version"
    private const val KEY_RESULT = "last_result"
    const val EXTRA_INTERACTIVE = "interactive"
    const val EXTRA_VERSION = "version"

    fun currentVersion(context: Context): Long =
        context.packageManager.getPackageInfo(context.packageName, 0).longVersionCode

    private fun prefs(context: Context) = context.getSharedPreferences(PREFS, Context.MODE_PRIVATE)

    fun awaitingConfirmation(context: Context): Long = prefs(context).getLong(KEY_WAITING, 0)

    fun lastResult(context: Context): String? = prefs(context).getString(KEY_RESULT, null)

    internal fun record(context: Context, result: String, waitingVersion: Long = 0) {
        prefs(context).edit().putString(KEY_RESULT, result).putLong(KEY_WAITING, waitingVersion).apply()
    }

    fun install(context: Context, apk: File, version: Long, interactive: Boolean) {
        val installer = context.packageManager.packageInstaller
        val params = PackageInstaller.SessionParams(PackageInstaller.SessionParams.MODE_FULL_INSTALL).apply {
            setAppPackageName(context.packageName)
            setRequireUserAction(PackageInstaller.SessionParams.USER_ACTION_NOT_REQUIRED)
            setSize(apk.length())
        }
        val sessionId = installer.createSession(params)
        installer.openSession(sessionId).use { session ->
            session.openWrite("base.apk", 0, apk.length()).use { out ->
                apk.inputStream().use { it.copyTo(out) }
                session.fsync(out)
            }
            val intent = Intent(context, InstallResultReceiver::class.java)
                .putExtra(EXTRA_INTERACTIVE, interactive)
                .putExtra(EXTRA_VERSION, version)
            // Mutable: the installer adds the status extras to this intent.
            val pending = PendingIntent.getBroadcast(
                context, sessionId, intent, PendingIntent.FLAG_UPDATE_CURRENT or PendingIntent.FLAG_MUTABLE
            )
            session.commit(pending.intentSender)
        }
    }
}

/** Receives the outcome of a self-update session. On success this process is replaced, so nothing runs after. */
class InstallResultReceiver : BroadcastReceiver() {
    override fun onReceive(context: Context, intent: Intent) {
        val status = intent.getIntExtra(PackageInstaller.EXTRA_STATUS, PackageInstaller.STATUS_FAILURE)
        val version = intent.getLongExtra(SelfInstaller.EXTRA_VERSION, 0)
        when (status) {
            PackageInstaller.STATUS_PENDING_USER_ACTION -> {
                val confirm = intent.getParcelableExtra(Intent.EXTRA_INTENT, Intent::class.java)
                if (intent.getBooleanExtra(SelfInstaller.EXTRA_INTERACTIVE, false) && confirm != null) {
                    SelfInstaller.record(context, "App update $version: confirm on screen")
                    context.startActivity(confirm.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK))
                } else {
                    SelfInstaller.record(context, "App update $version waiting: open the app to finish", version)
                }
            }
            PackageInstaller.STATUS_SUCCESS -> SelfInstaller.record(context, "App updated to $version")
            else -> {
                val msg = intent.getStringExtra(PackageInstaller.EXTRA_STATUS_MESSAGE) ?: "status $status"
                Log.w(Updater.TAG, "Self-update to $version failed: $msg")
                SelfInstaller.record(context, "App update $version failed: $msg")
            }
        }
    }
}
