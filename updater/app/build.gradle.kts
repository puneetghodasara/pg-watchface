import java.util.Properties

plugins {
    id("com.android.application")
}

// Watch Face Push needs Wear OS 6 (API 36).
android {
    namespace = "app.pg.watchface"
    compileSdk = 36

    val keyProps = Properties().apply {
        val f = rootProject.file("signing/updater.properties")
        if (f.exists()) f.inputStream().use { load(it) }
    }
    signingConfigs {
        create("updater") {
            storeFile = rootProject.file("signing/updater.jks")
            storePassword = keyProps.getProperty("storePassword")
            keyAlias = "updater"
            keyPassword = keyProps.getProperty("storePassword")
        }
    }

    defaultConfig {
        applicationId = "app.pg.watchface"
        minSdk = 36
        targetSdk = 36
        // CI passes -PversionCode = minutes since 1970 of the last commit touching updater/,
        // so the app only offers itself as an update when its own code changed.
        val code = (project.findProperty("versionCode") as String?)?.toInt() ?: 1
        versionCode = code
        versionName = "1.$code"
    }
    buildTypes {
        release {
            isMinifyEnabled = true
            isShrinkResources = true
            proguardFiles(getDefaultProguardFile("proguard-android-optimize.txt"), "proguard-rules.pro")
            signingConfig = signingConfigs.getByName("updater")
        }
    }
    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_17
        targetCompatibility = JavaVersion.VERSION_17
    }
}

dependencies {
    implementation("androidx.wear.watchfacepush:watchfacepush:1.0.0")
    implementation("androidx.work:work-runtime-ktx:2.10.5")
    implementation("org.jetbrains.kotlinx:kotlinx-coroutines-android:1.10.2")
}
