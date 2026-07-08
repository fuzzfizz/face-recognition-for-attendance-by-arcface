import 'package:flutter/foundation.dart';

class CaptureViewModel extends ChangeNotifier {
  final int _requiredPhotos;
  final List<String> _capturedPaths = [];

  CaptureViewModel({int requiredPhotos = 1})
    : _requiredPhotos = requiredPhotos;

  List<String> get capturedPaths => List.unmodifiable(_capturedPaths);
  int get capturedCount => _capturedPaths.length;
  int get requiredPhotos => _requiredPhotos;
  bool get isComplete => _capturedPaths.length >= _requiredPhotos;
  double get progress => _capturedPaths.length / _requiredPhotos;

  void addPhoto(String path) {
    if (!isComplete) {
      _capturedPaths.add(path);
      notifyListeners();
    }
  }

  void removePhoto(int index) {
    if (index >= 0 && index < _capturedPaths.length) {
      _capturedPaths.removeAt(index);
      notifyListeners();
    }
  }

  void replacePhoto(int index, String newPath) {
    if (index >= 0 && index < _capturedPaths.length) {
      _capturedPaths[index] = newPath;
      notifyListeners();
    }
  }

  void clearPhotos() {
    _capturedPaths.clear();
    notifyListeners();
  }
}
