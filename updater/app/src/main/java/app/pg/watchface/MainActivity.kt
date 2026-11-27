package app.pg.watchface

import android.app.Activity
import android.content.pm.PackageManager
import android.os.Bundle
import android.view.Gravity
import android.widget.Button
import android.widget.CheckBox
import android.widget.LinearLayout
import android.widget.ScrollView
import android.widget.TextView
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.MainScope
import kotlinx.coroutines.cancel
import kotlinx.coroutines.launch

/**
 * Status, "Check now", and the auto-update settings: on/off and how often to check.
 * Scrolls, so it fits the round screen.
 */
class MainActivity : Activity() {
    private val scope: CoroutineScope = MainScope()
    private lateinit var status: TextView
    private lateinit var lastCheck: TextView
    private lateinit var cadence: Button

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        val pad = (resources.displayMetrics.widthPixels * 0.12).toInt()

        status = TextView(this).apply { gravity = Gravity.CENTER; textSize = 14f }
        val checkNow = Button(this).apply { text = "Check now"; setOnClickListener { check() } }
        val auto = CheckBox(this).apply {
            text = "Auto-update"
            isChecked = UpdateSettings.isEnabled(context)
            setOnCheckedChangeListener { _, on ->
                UpdateSettings.setEnabled(context, on)
                refreshSettings()
            }
        }
        cadence = Button(this).apply {
            setOnClickListener { UpdateSettings.nextHours(context); refreshSettings() }
        }
        lastCheck = TextView(this).apply { gravity = Gravity.CENTER; textSize = 12f; alpha = 0.7f }

        val column = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            gravity = Gravity.CENTER_HORIZONTAL
            setPadding(pad, pad, pad, pad)
            addView(status)
            addView(checkNow)
            addView(auto)
            addView(cadence)
            addView(lastCheck)
        }
        setContentView(ScrollView(this).apply { addView(column) })

        refreshSettings()
        UpdateWorker.schedule(this)
        val perm = "com.google.wear.permission.SET_PUSHED_WATCH_FACE_AS_ACTIVE"
        if (checkSelfPermission(perm) != PackageManager.PERMISSION_GRANTED) requestPermissions(arrayOf(perm), 1)
        check()
    }

    private fun refreshSettings() {
        val on = UpdateSettings.isEnabled(this)
        cadence.text = "Check every ${UpdateSettings.hours(this)} h"
        cadence.isEnabled = on
        cadence.alpha = if (on) 1f else 0.4f
        lastCheck.text = UpdateSettings.lastCheckLine(this) ?: ""
    }

    private fun check() {
        val last = SelfInstaller.lastResult(this)?.let { "\n$it" } ?: ""
        status.text = "App ${SelfInstaller.currentVersion(this)}$last\nChecking GitHub…"
        scope.launch {
            val msg = runCatching { Updater.checkAndUpdate(applicationContext, interactive = true) }
                .getOrElse { "Failed: ${it.message}".also { m -> UpdateSettings.recordCheck(applicationContext, m) } }
            launch(Dispatchers.Main) {
                status.text = msg
                refreshSettings()
            }
        }
    }

    override fun onDestroy() {
        scope.cancel()
        super.onDestroy()
    }
}
