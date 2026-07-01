import 'package:flutter/foundation.dart';

import 'package:app_face_capture/core/constants/api_constants.dart';
import 'package:app_face_capture/data/services/face_api_service.dart';

class AdminViewModel extends ChangeNotifier {
  bool _authenticated = false;
  String? _result;

  AdminViewModel({FaceApiService? apiService});

  bool get authenticated => _authenticated;
  String? get result => _result;

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

  /// Reset the authentication state.
  void logout() {
    _authenticated = false;
    _result = null;
    notifyListeners();
  }
}
