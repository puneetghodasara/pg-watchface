package app.pg.watchface

import android.app.Activity
import android.content.pm.PackageManager
import android.os.Bundle
import android.view.Gravity
import android.widget.Button
import android.widget.LinearLayout
import android.widget.TextView
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.MainScope
import kotlinx.coroutines.cancel
import kotlinx.coroutines.launch

/** One screen: status line and a "Check now" button. Updates otherwise run in the background. */
class MainActivity : Activity() {
    private val scope: CoroutineScope = MainScope()
    private lateinit var status: TextView

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        status = TextView(this).apply { gravity = Gravity.CENTER; textSize = 14f; setPadding(32, 0, 32, 16) }
        val button = Button(this).apply { text = "Check now"; setOnClickListener { check() } }
        setContentView(LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            gravity = Gravity.CENTER
            addView(status)
            addView(button)
        })

        UpdateWorker.schedule(this)
        val perm = "com.google.wear.permission.SET_PUSHED_WATCH_FACE_AS_ACTIVE"
        if (checkSelfPermission(perm) != PackageManager.PERMISSION_GRANTED) requestPermissions(arrayOf(perm), 1)
        check()
    }

    private fun check() {
        val last = SelfInstaller.lastResult(this)?.let { "\n$it" } ?: ""
        status.text = "App ${SelfInstaller.currentVersion(this)}$last\nChecking GitHub…"
        scope.launch {
            val msg = runCatching { Updater.checkAndUpdate(applicationContext, interactive = true) }
                .getOrElse { "Failed: ${it.message}" }
            launch(Dispatchers.Main) { status.text = msg }
        }
    }

    override fun onDestroy() {
        scope.cancel()
        super.onDestroy()
    }
}
