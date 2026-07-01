import 'dart:io';
import 'package:flutter/foundation.dart';
import 'package:app_face_capture/core/constants/storage_constants.dart';
import 'package:app_face_capture/data/repositories/face_repository.dart';

enum UploadState { idle, uploading, checking, success, failed }

class UploadViewModel extends ChangeNotifier {
  final FaceRepository _repository;
  final String studentId;
  final String studentName;
  final List<String> imagePaths;
  final UploadMethod method;

  UploadState _state = UploadState.idle;
  int _uploadedCount = 0;
  String? _errorMessage;

  UploadViewModel({
    required FaceRepository repository,
    required this.studentId,
    required this.studentName,
    required this.imagePaths,
    required this.method,
  }) : _repository = repository;

  UploadState get state => _state;
  bool get isUploading => _state == UploadState.uploading;
  bool get isChecking => _state == UploadState.checking;
  bool get isSuccess => _state == UploadState.success;
  bool get isFailed => _state == UploadState.failed;
  int get uploadedCount => _uploadedCount;
  int get totalCount => imagePaths.length;
  double get progress => totalCount > 0 ? _uploadedCount / totalCount : 0.0;
  String? get errorMessage => _errorMessage;

  Future<void> startUpload() async {
    _state = UploadState.uploading;
    _uploadedCount = 0;
    _errorMessage = null;
    notifyListeners();

    try {
      final files = imagePaths.map((p) => File(p)).toList();
      await _repository.uploadPhotos(studentId, studentName, files, method);
      _uploadedCount = imagePaths.length;
      notifyListeners();

      // Move to checking state - TRAINING IS NOW ADMIN-ONLY
      _state = UploadState.checking;
      notifyListeners();

      // Training is admin-only, user workflow ends with status checking

      // Poll for status - Training is admin-only, user workflow ends with status checking
      await _pollStatus();
    } catch (e) {
      _state = UploadState.failed;
      _errorMessage = e.toString();
      notifyListeners();
    }
  }

  Future<void> _pollStatus() async {
    const maxAttempts = 30;
    const delay = Duration(seconds: 2);

    for (var i = 0; i < maxAttempts; i++) {
      await Future.delayed(delay);
      try {
        final status = await _repository.checkStatus(studentId, method: method);
        if (status.isCompleted) {
          _state = UploadState.success;
          notifyListeners();
          return;
        }
        if (status.isFailed) {
          _errorMessage = status.message;
          _state = UploadState.failed;
          notifyListeners();
          return;
        }
      } catch (e) {
        // Continue polling on network errors
      }
    }

    _errorMessage = 'Status check timed out. Please check later.';
    _state = UploadState.failed;
    notifyListeners();
  }

  @override
  void dispose() {
    _repository.dispose();
    super.dispose();
  }
}


