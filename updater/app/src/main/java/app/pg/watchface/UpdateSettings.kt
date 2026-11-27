package app.pg.watchface

import android.content.Context
import java.text.DateFormat
import java.util.Date

/** Auto-update on/off, how often to check, and when the last check ran. */
object UpdateSettings {
    private const val PREFS = "auto_update"
    private const val KEY_ENABLED = "enabled"
    private const val KEY_HOURS = "hours"
    private const val KEY_LAST_CHECK = "last_check"
    private const val KEY_LAST_RESULT = "last_check_result"

    /** Choices offered on the screen; WorkManager's minimum interval is 15 minutes. */
    val CADENCES_HOURS = listOf(1, 3, 6, 12, 24)
    private const val DEFAULT_HOURS = 3

    private fun prefs(context: Context) = context.getSharedPreferences(PREFS, Context.MODE_PRIVATE)

    fun isEnabled(context: Context) = prefs(context).getBoolean(KEY_ENABLED, true)

    fun setEnabled(context: Context, enabled: Boolean) {
        prefs(context).edit().putBoolean(KEY_ENABLED, enabled).apply()
        UpdateWorker.schedule(context)
    }

    fun hours(context: Context): Int =
        prefs(context).getInt(KEY_HOURS, DEFAULT_HOURS).takeIf { it in CADENCES_HOURS } ?: DEFAULT_HOURS

    /** Moves to the next cadence in the list (wrapping) and reschedules. Returns the new value. */
    fun nextHours(context: Context): Int {
        val next = CADENCES_HOURS[(CADENCES_HOURS.indexOf(hours(context)) + 1) % CADENCES_HOURS.size]
        prefs(context).edit().putInt(KEY_HOURS, next).apply()
        UpdateWorker.schedule(context)
        return next
    }

    fun recordCheck(context: Context, result: String) {
        prefs(context).edit()
            .putLong(KEY_LAST_CHECK, System.currentTimeMillis())
            .putString(KEY_LAST_RESULT, result.lineSequence().firstOrNull() ?: result)
            .apply()
    }

    /** e.g. "Last check: Nov 26, 10:42 PM · Face up to date (…)", or null before the first check. */
    fun lastCheckLine(context: Context): String? {
        val at = prefs(context).getLong(KEY_LAST_CHECK, 0)
        if (at == 0L) return null
        val time = DateFormat.getDateTimeInstance(DateFormat.MEDIUM, DateFormat.SHORT).format(Date(at))
        val result = prefs(context).getString(KEY_LAST_RESULT, null)
        return "Last check: $time" + (result?.let { "\n$it" } ?: "")
    }
}
