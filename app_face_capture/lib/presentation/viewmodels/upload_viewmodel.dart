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
      _state = UploadState.success;
      notifyListeners();
    } catch (e) {
      _state = UploadState.failed;
      _errorMessage = e.toString();
      notifyListeners();
    }
  }

  @override
  void dispose() {
    _repository.dispose();
    super.dispose();
  }
}


