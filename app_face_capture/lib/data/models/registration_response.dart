class RegistrationResponse {
  final String message;
  final String studentId;
  final String status;

  RegistrationResponse({
    required this.message,
    required this.studentId,
    required this.status,
  });

  factory RegistrationResponse.fromJson(Map<String, dynamic> json) {
    return RegistrationResponse(
      message: json['message'] as String,
      studentId: json['student_id'] as String,
      status: json['status'] as String,
    );
  }
}
