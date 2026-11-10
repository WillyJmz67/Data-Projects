# Kotlin Serialization
-keepattributes *Annotation*, InnerClasses
-dontwarn kotlinx.serialization.**

-keepclassmembers class kotlinx.serialization.json.** {
    *** Companion;
}

-keepclasseswithmembers class kotlinx.serialization.json.** {
    kotlinx.serialization.KSerializer serializer(...);
}

-keep,includedescriptorclasses class org.openshelf.reader.**$$serializer { *; }

-keepclassmembers class org.openshelf.reader.** {
    *** Companion;
}

-keepclasseswithmembers class org.openshelf.reader.** {
    kotlinx.serialization.KSerializer serializer(...);
}

# Modelos serializables
-keep class org.openshelf.reader.domain.model.** { *; }
-keepclassmembers class org.openshelf.reader.domain.model.** { *; }

# Room
-keep class * extends androidx.room.RoomDatabase
-keep @androidx.room.Entity class *

# OkHttp
-dontwarn okhttp3.**
-dontwarn okio.**
-keep class okhttp3.** { *; }
-keep interface okhttp3.** { *; }

# Coil
-dontwarn coil.**
