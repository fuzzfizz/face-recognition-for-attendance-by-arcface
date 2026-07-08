class StorageConstants {
  static const String registrationPathPrefix = 'registrations';

  static String imagePath(String studentId, String uuid) =>
      '$registrationPathPrefix/$studentId/$uuid.jpg';
}
