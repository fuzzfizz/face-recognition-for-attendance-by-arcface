import 'dart:io';
import 'package:app_face_capture/data/models/registration_response.dart';
import 'package:app_face_capture/data/models/registration_status.dart';
import 'package:app_face_capture/data/services/face_api_service.dart';
import 'package:app_face_capture/core/constants/api_constants.dart';

class FaceRepository {
  final FaceApiService _apiService;

  FaceRepository({FaceApiService? apiService})
      : _apiService = apiService ?? FaceApiService();

  Future<RegistrationResponse> uploadPhotos(String studentId, List<File> images) async {
    final batches = _batchImages(images, ApiConstants.maxPhotosPerUpload);
    RegistrationResponse? lastResponse;

    for (final batch in batches) {
      lastResponse = await _apiService.register(studentId, batch);
    }

    return lastResponse!;
  }

  Future<RegistrationStatus> checkStatus(String studentId) async {
    return await _apiService.checkStatus(studentId);
  }

  Future<bool> checkServerHealth() async {
    return await _apiService.healthCheck();
  }

  List<List<File>> _batchImages(List<File> images, int batchSize) {
    final batches = <List<File>>[];
    for (var i = 0; i < images.length; i += batchSize) {
      final end = (i + batchSize > images.length) ? images.length : i + batchSize;
      batches.add(images.sublist(i, end));
    }
    return batches;
  }

  void dispose() {
    _apiService.dispose();
  }
}
