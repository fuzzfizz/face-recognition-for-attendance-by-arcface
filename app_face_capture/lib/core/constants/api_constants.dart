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

  // Supabase and Admin Constants
  static const String supabaseUrl = String.fromEnvironment('SUPABASE_URL', defaultValue: '');
  static const String supabaseAnonKey = String.fromEnvironment('SUPABASE_ANON_KEY', defaultValue: '');
  static const String adminPin = String.fromEnvironment('ADMIN_PIN', defaultValue: '1234');
  static const String adminApiKey = String.fromEnvironment('ADMIN_API_KEY', defaultValue: '');
}
