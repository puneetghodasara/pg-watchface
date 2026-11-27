# WorkManager's database is created by reflection; R8 must keep the generated constructors.
-keep class * extends androidx.room.RoomDatabase { <init>(); }
-keep class androidx.work.impl.** { *; }
-keep class * extends androidx.work.ListenableWorker { <init>(...); }
