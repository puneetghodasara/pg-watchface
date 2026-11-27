package app.pg.watchface

import android.content.Context
import androidx.work.Constraints
import androidx.work.CoroutineWorker
import androidx.work.ExistingPeriodicWorkPolicy
import androidx.work.NetworkType
import androidx.work.PeriodicWorkRequestBuilder
import androidx.work.WorkManager
import androidx.work.WorkerParameters
import java.util.concurrent.TimeUnit

/** Background check for a new release, at the cadence chosen in the app, only when online. */
class UpdateWorker(context: Context, params: WorkerParameters) : CoroutineWorker(context, params) {
    override suspend fun doWork(): Result =
        runCatching { Updater.checkAndUpdate(applicationContext, interactive = false) }
            .fold({ Result.success() }, {
                UpdateSettings.recordCheck(applicationContext, "Failed: ${it.message}")
                Result.retry()
            })

    companion object {
        private const val WORK = "face-update"

        /** Applies the current settings: schedules at the chosen cadence, or cancels when auto-update is off. */
        fun schedule(context: Context) {
            val wm = WorkManager.getInstance(context)
            if (!UpdateSettings.isEnabled(context)) {
                wm.cancelUniqueWork(WORK)
                return
            }
            val request = PeriodicWorkRequestBuilder<UpdateWorker>(UpdateSettings.hours(context).toLong(), TimeUnit.HOURS)
                .setConstraints(Constraints.Builder().setRequiredNetworkType(NetworkType.CONNECTED).build())
                .build()
            // UPDATE keeps the existing schedule but applies a changed cadence.
            wm.enqueueUniquePeriodicWork(WORK, ExistingPeriodicWorkPolicy.UPDATE, request)
        }
    }
}
