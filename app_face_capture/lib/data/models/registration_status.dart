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
