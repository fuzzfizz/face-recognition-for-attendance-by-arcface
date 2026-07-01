import 'dart:io';
import 'package:app_face_capture/data/models/registration_response.dart';
import 'package:app_face_capture/data/models/registration_status.dart';
import 'package:app_face_capture/data/services/face_api_service.dart';
import 'package:app_face_capture/data/services/supabase_storage_service.dart';
import 'package:app_face_capture/core/constants/api_constants.dart';
import 'package:app_face_capture/core/constants/storage_constants.dart';

class FaceRepository {
  final FaceApiService _apiService;
  final SupabaseStorageService _supabaseService;

  FaceRepository({
    FaceApiService? apiService,
    SupabaseStorageService? supabaseService,
  })  : _apiService = apiService ?? FaceApiService(),
        _supabaseService = supabaseService ?? SupabaseStorageService();

  Future<RegistrationResponse> uploadPhotos(
    String studentId,
    String studentName,
    List<File> images,
    UploadMethod method,
  ) async {
    if (method == UploadMethod.directSupabase) {
      await _supabaseService.upsertUser(studentId, studentName);
      return await _supabaseService.uploadPhotos(studentId, images);
    } else {
      final batches = _batchImages(images, ApiConstants.maxPhotosPerUpload);
      RegistrationResponse? lastResponse;

      for (final batch in batches) {
        lastResponse = await _apiService.register(studentId, studentName, batch);
      }

      return lastResponse!;
    }
  }

  Future<RegistrationStatus> checkStatus(
    String studentId, {
    UploadMethod method = UploadMethod.viaServer,
  }) async {
    if (method == UploadMethod.directSupabase) {
      return RegistrationStatus(
        studentId: studentId,
        status: 'completed',
        message: 'Images uploaded directly. Training must be triggered by an admin.',
      );
    }
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
