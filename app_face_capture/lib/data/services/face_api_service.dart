import 'dart:convert';
import 'dart:io';
import 'package:http/http.dart' as http;
import 'package:app_face_capture/core/constants/api_constants.dart';
import 'package:app_face_capture/data/models/registration_response.dart';
import 'package:app_face_capture/data/models/registration_status.dart';

class FaceApiService {
  final http.Client _client;

  FaceApiService({http.Client? client}) : _client = client ?? http.Client();

  String get _baseUrl => ApiConstants.baseUrl;

  Future<RegistrationResponse> register(String studentId, String studentName, List<File> images) async {
    final uri = Uri.parse('$_baseUrl${ApiConstants.register}');
    final request = http.MultipartRequest('POST', uri);
    request.fields['student_id'] = studentId;
    request.fields['name'] = studentName;

    for (final image in images) {
      request.files.add(await http.MultipartFile.fromPath('files', image.path));
    }

    final streamedResponse = await request.send();
    final response = await http.Response.fromStream(streamedResponse);

    if (response.statusCode == 200) {
      final json = jsonDecode(response.body) as Map<String, dynamic>;
      return RegistrationResponse.fromJson(json);
    } else {
      throw Exception('Registration failed: ${response.statusCode} ${response.body}');
    }
  }

  Future<RegistrationStatus> checkStatus(String studentId) async {
    final uri = Uri.parse('$_baseUrl${ApiConstants.registerStatus}/$studentId');
    final response = await _client.get(uri);

    if (response.statusCode == 200) {
      final json = jsonDecode(response.body) as Map<String, dynamic>;
      return RegistrationStatus.fromJson(json);
    } else {
      throw Exception('Status check failed: ${response.statusCode}');
    }
  }

  /// Admin-only API. Only admins should trigger model training.
  /// The client app for regular users must NOT call this endpoint or expose it
  /// in normal user flows. Authorization must be enforced on the backend.
  Future<void> triggerTraining() async {
    final uri = Uri.parse('$_baseUrl${ApiConstants.trainNow}');
    final response = await _client.post(
      uri,
      headers: {
        'X-Admin-Key': ApiConstants.adminApiKey,
      },
    );

    if (response.statusCode != 200) {
      throw Exception('Training trigger failed: ${response.statusCode}');
    }
  }

  Future<bool> healthCheck() async {
    try {
      final uri = Uri.parse('$_baseUrl${ApiConstants.health}');
      final response = await _client.get(uri);
      return response.statusCode == 200;
    } catch (e) {
      return false;
    }
  }

  void dispose() {
    _client.close();
  }
}
