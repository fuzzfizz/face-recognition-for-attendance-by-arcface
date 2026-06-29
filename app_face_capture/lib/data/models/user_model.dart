class UserModel {
  final String studentId;
  final String? name;
  final DateTime? createdAt;

  UserModel({required this.studentId, this.name, this.createdAt});

  factory UserModel.fromJson(Map<String, dynamic> json) {
    return UserModel(
      studentId: json['student_id'] as String,
      name: json['name'] as String?,
      createdAt: json['created_at'] != null
          ? DateTime.parse(json['created_at'] as String)
          : null,
    );
  }

  Map<String, dynamic> toJson() {
    return {
      'student_id': studentId,
      if (name != null) 'name': name,
    };
  }
}
