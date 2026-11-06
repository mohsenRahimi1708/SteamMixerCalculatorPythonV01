# Kotlinx serialization and Retrofit/Room keep their metadata.
-keepattributes *Annotation*, InnerClasses, Signature, Exceptions
-dontwarn kotlinx.serialization.**
-keep class com.steamcalc.domain.** { *; }
-keep,includedescriptorclasses class com.steamcalc.domain.**$$serializer { *; }
-keepclassmembers class com.steamcalc.domain.** { *** Companion; }
-keepclasseswithmembers class com.steamcalc.domain.** { kotlinx.serialization.KSerializer serializer(...); }
-keep class * extends androidx.room.RoomDatabase { *; }
-dontwarn okhttp3.**
-dontwarn okio.**
