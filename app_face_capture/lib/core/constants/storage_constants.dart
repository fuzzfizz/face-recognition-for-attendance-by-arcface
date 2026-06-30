enum UploadMethod { viaServer, directSupabase }

class StorageConstants {
  static const String bucketName = 'face-images';
  static const String registrationPathPrefix = 'registrations';

  static String imagePath(String studentId, String uuid) =>
      '$registrationPathPrefix/$studentId/$uuid.jpg';
}
