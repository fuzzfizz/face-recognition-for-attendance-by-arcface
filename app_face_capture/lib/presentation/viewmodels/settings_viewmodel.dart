import 'package:flutter/foundation.dart';
import 'package:shared_preferences/shared_preferences.dart';

import 'package:app_face_capture/core/constants/storage_constants.dart';
import 'package:app_face_capture/core/constants/api_constants.dart';
import 'package:app_face_capture/data/repositories/face_repository.dart';

class SettingsViewModel extends ChangeNotifier {
  final FaceRepository _repository;
  
  UploadMethod _uploadMethod = UploadMethod.viaServer;
  String _serverUrl = ApiConstants.baseUrl;

  SettingsViewModel({FaceRepository? repository})
      : _repository = repository ?? FaceRepository();

  UploadMethod get uploadMethod => _uploadMethod;
  String get serverUrl => _serverUrl;

  /// Load settings from SharedPreferences.
  Future<void> load() async {
    final prefs = await SharedPreferences.getInstance();
    final methodIndex = prefs.getInt('upload_method');
    if (methodIndex != null && methodIndex >= 0 && methodIndex < UploadMethod.values.length) {
      _uploadMethod = UploadMethod.values[methodIndex];
    } else {
      _uploadMethod = UploadMethod.viaServer;
    }
    
    _serverUrl = prefs.getString('server_url') ?? ApiConstants.baseUrl;
    notifyListeners();
  }

  /// Sets and persists the UploadMethod.
  Future<void> setUploadMethod(UploadMethod method) async {
    _uploadMethod = method;
    notifyListeners();
    final prefs = await SharedPreferences.getInstance();
    await prefs.setInt('upload_method', method.index);
  }

  /// Sets and persists the Server URL.
  Future<void> setServerUrl(String url) async {
    _serverUrl = url;
    notifyListeners();
    final prefs = await SharedPreferences.getInstance();
    await prefs.setString('server_url', url);
  }

  /// Test server connection health.
  Future<bool> checkServerHealth() async {
    return await _repository.checkServerHealth();
  }
}
