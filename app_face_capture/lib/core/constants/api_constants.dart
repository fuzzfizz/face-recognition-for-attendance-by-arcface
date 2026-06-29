class ApiConstants {
  static const String baseUrl = 'http://10.0.2.2:8000'; // Android emulator localhost
  static const String register = '/register';
  static const String registerStatus = '/register/status';
  static const String trainNow = '/train-now';
  static const String verify = '/verify';
  static const String logs = '/logs';
  static const String health = '/';
  
  // App constants
  static const int requiredPhotos = 10;
  static const int maxPhotosPerUpload = 3;
  static const double faceConfidenceThreshold = 0.8;
}
