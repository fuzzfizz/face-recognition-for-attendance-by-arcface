class RegistrationStatus {
  final String studentId;
  final String status;
  final String message;

  RegistrationStatus({
    required this.studentId,
    required this.status,
    required this.message,
  });

  factory RegistrationStatus.fromJson(Map<String, dynamic> json) {
    return RegistrationStatus(
      studentId: json['student_id'] as String,
      status: json['status'] as String,
      message: json['message'] as String,
    );
  }

  bool get isCompleted => status == 'completed';
  bool get isFailed => status == 'failed';
  bool get isPending => status == 'pending';
}

class FaceValidationResult {
  final String filename;
  final bool passed;
  final String? error;

  FaceValidationResult({
    required this.filename,
    required this.passed,
    this.error,
  });

  factory FaceValidationResult.fromJson(Map<String, dynamic> json) {
    return FaceValidationResult(
      filename: json['filename'] as String,
      passed: json['passed'] as bool,
      error: json['error'] as String?,
    );
  }
}

class FaceVerificationException implements Exception {
  final String message;
  final List<FaceValidationResult> results;

  FaceVerificationException({
    required this.message,
    required this.results,
  });

  @override
  String toString() => message;
}
