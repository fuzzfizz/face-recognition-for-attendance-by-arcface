import 'package:flutter/foundation.dart';
import 'package:shared_preferences/shared_preferences.dart';

import 'package:app_face_capture/core/constants/api_constants.dart';
import 'package:app_face_capture/data/repositories/face_repository.dart';

class SettingsViewModel extends ChangeNotifier {
  final FaceRepository _repository;
  
  String _serverUrl = ApiConstants.baseUrl;

  SettingsViewModel({FaceRepository? repository})
      : _repository = repository ?? FaceRepository();

  String get serverUrl => _serverUrl;

  bool _isAdminAuthenticated = false;
  bool get isAdminAuthenticated => _isAdminAuthenticated;

  void authenticateAdmin(bool authenticated) {
    _isAdminAuthenticated = authenticated;
    notifyListeners();
  }

  /// Load settings from SharedPreferences.
  Future<void> load() async {
    final prefs = await SharedPreferences.getInstance();
    _serverUrl = prefs.getString('server_url') ?? ApiConstants.baseUrl;
    notifyListeners();
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
