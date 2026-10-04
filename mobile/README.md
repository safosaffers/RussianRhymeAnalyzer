# rhymer

Android poetry editor: one text field, rhyme highlights while typing, offline.

```sh
flutter pub get
flutter run
flutter analyze
flutter test
flutter build apk --debug
```

Run commands from `mobile/`. Flutter 3.41+ and Android SDK required.
APK: `build/app/outputs/flutter-apk/app-debug.apk`.

- `rhyme_detector.dart` and `phonetics.dart`: Dart port of the desktop Yukawa detector, with its default parameters.
- `rhyme_controller.dart`: background colors inside the editable text, preserving keyboard composition.
- `main.dart`: single-field UI; analysis after a 180 ms typing pause, in a worker isolate. Stale results are discarded.

Like the desktop Yukawa mode, highlights show syllable similarity, including
within a line; they do not guarantee stressed end rhymes. RPST is not included.
Text is kept in memory only. No accounts, server, or runtime packages.
