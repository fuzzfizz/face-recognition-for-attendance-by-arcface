import 'package:flutter/foundation.dart';

import 'package:app_face_capture/core/constants/api_constants.dart';
import 'package:app_face_capture/data/services/face_api_service.dart';

class AdminViewModel extends ChangeNotifier {
  final FaceApiService _apiService;

  bool _authenticated = false;
  String? _result;
  bool _isLoading = false;

  AdminViewModel({FaceApiService? apiService})
      : _apiService = apiService ?? FaceApiService();

  bool get authenticated => _authenticated;
  String? get result => _result;
  bool get isLoading => _isLoading;

  /// Authenticate the administrator using the PIN.
  bool authenticate(String pin) {
    if (pin == ApiConstants.adminPin) {
      _authenticated = true;
      _result = null;
      notifyListeners();
      return true;
    } else {
      _authenticated = false;
      _result = 'Incorrect PIN';
      notifyListeners();
      return false;
    }
  }

  /// Triggers the backend training pipeline.
  Future<void> triggerTraining() async {
    if (!_authenticated) {
      _result = 'Unauthorized. Please authenticate first.';
      notifyListeners();
      return;
    }

    _isLoading = true;
    _result = null;
    notifyListeners();

    try {
      await _apiService.triggerTraining();
      _result = 'Training triggered successfully!';
    } catch (e) {
      _result = 'Failed to trigger training: ${e.toString()}';
    } finally {
      _isLoading = false;
      notifyListeners();
    }
  }

  /// Reset the authentication state.
  void logout() {
    _authenticated = false;
    _result = null;
    notifyListeners();
  }
}
