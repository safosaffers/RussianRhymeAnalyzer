plugins {
    id("com.android.application")
    id("kotlin-android")
    // Плагин Flutter подключается после Android и Kotlin.
    id("dev.flutter.flutter-gradle-plugin")
}

android {
    namespace = "com.rhymer.rhymer"
    compileSdk = flutter.compileSdkVersion
    ndkVersion = flutter.ndkVersion

    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_17
        targetCompatibility = JavaVersion.VERSION_17
    }

    kotlinOptions {
        jvmTarget = JavaVersion.VERSION_17.toString()
    }

    defaultConfig {
        applicationId = "com.rhymer.rhymer"
        minSdk = flutter.minSdkVersion
        targetSdk = flutter.targetSdkVersion
        versionCode = flutter.versionCode
        versionName = flutter.versionName
    }

    buildTypes {
        release {
            // Локальная сборка; для публикации нужен отдельный ключ подписи.
            signingConfig = signingConfigs.getByName("debug")
        }
    }
}

flutter {
    source = "../.."
}
