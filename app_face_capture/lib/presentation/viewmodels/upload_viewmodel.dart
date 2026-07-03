import 'dart:io';
import 'package:flutter/foundation.dart';
import 'package:app_face_capture/core/constants/storage_constants.dart';
import 'package:app_face_capture/data/repositories/face_repository.dart';
import 'package:app_face_capture/data/models/registration_status.dart';

enum UploadState { idle, uploading, success, failed }

class UploadViewModel extends ChangeNotifier {
  final FaceRepository _repository;
  final String studentId;
  final String studentName;
  final List<String> _imagePaths;
  final UploadMethod method;

  UploadState _state = UploadState.idle;
  int _uploadedCount = 0;
  String? _errorMessage;
  List<FaceValidationResult> _validationResults = [];

  UploadViewModel({
    required FaceRepository repository,
    required this.studentId,
    required this.studentName,
    required List<String> imagePaths,
    required this.method,
  })  : _repository = repository,
        _imagePaths = List.from(imagePaths);

  UploadState get state => _state;
  bool get isUploading => _state == UploadState.uploading;
  bool get isSuccess => _state == UploadState.success;
  bool get isFailed => _state == UploadState.failed;
  int get uploadedCount => _uploadedCount;
  List<String> get imagePaths => List.unmodifiable(_imagePaths);
  int get totalCount => _imagePaths.length;
  double get progress => totalCount > 0 ? _uploadedCount / totalCount : 0.0;
  String? get errorMessage => _errorMessage;
  List<FaceValidationResult> get validationResults => _validationResults;

  Future<void> startUpload() async {
    _state = UploadState.uploading;
    _uploadedCount = 0;
    _errorMessage = null;
    _validationResults = [];
    notifyListeners();

    try {
      final files = _imagePaths.map((p) => File(p)).toList();
      await _repository.uploadPhotos(studentId, studentName, files, method);
      _uploadedCount = _imagePaths.length;
      _state = UploadState.success;
      notifyListeners();
    } on FaceVerificationException catch (e) {
      _state = UploadState.failed;
      _errorMessage = e.message;
      _validationResults = e.results;
      notifyListeners();
    } catch (e) {
      _state = UploadState.failed;
      _errorMessage = e.toString();
      notifyListeners();
    }
  }

  void replacePhoto(int index, String newPath) {
    if (index >= 0 && index < _imagePaths.length) {
      _imagePaths[index] = newPath;
      notifyListeners();
    }
  }

  @override
  void dispose() {
    _repository.dispose();
    super.dispose();
  }
}
