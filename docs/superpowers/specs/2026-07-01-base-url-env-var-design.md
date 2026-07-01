# Design Spec: Environment-based Base URL Configuration

Change the hardcoded API base URL in the Flutter application to be dynamically configured at compile-time via Dart environment variables.

## Background
Currently, the API base URL is hardcoded to a specific IP address:
```dart
static const String baseUrl = 'http://34.124.240.7:8000';
```
To enable more flexible builds (development, staging, production) and avoid committing environment-specific configurations to source control, we want to load this value from Dart environment variables, mirroring how Supabase URLs are configured.

## Design
We will replace the hardcoded string literal with a `String.fromEnvironment` call.

### Target File
* [api_constants.dart](file:///D:/AIproject/app_face_capture/lib/core/constants/api_constants.dart)

### Changes
Modify `ApiConstants.baseUrl` definition:
```dart
static const String baseUrl = String.fromEnvironment(
  'BASE_URL',
  defaultValue: '',
);
```

## Compilation and Usage
When building or running the application, define the `BASE_URL` using `--dart-define` or `--dart-define-from-file`:
```bash
flutter run --dart-define=BASE_URL=http://34.124.240.7:8000
```
