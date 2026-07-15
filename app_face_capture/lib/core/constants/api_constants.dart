class ApiConstants {
  static const String baseUrl = String.fromEnvironment(
    'BASE_URL',
    defaultValue: '',
  );
  static const String register = '/register';
  static const String registerStatus = '/register/status';
  static const String trainNow = '/train-now';
  static const String verify = '/verify/face_recognition';
  static const String logs = '/logs';
  static const String health = '/';

  // App constants
  static const int requiredPhotos = 1;
  static const int maxPhotosPerUpload = 3;
  static const double faceConfidenceThreshold = 0.8;

  static const String adminPin = String.fromEnvironment(
    'ADMIN_PIN',
    defaultValue: '1234',
  );
  static const String adminApiKey = String.fromEnvironment(
    'ADMIN_API_KEY',
    defaultValue: '',
  );
}
