import 'package:flutter_test/flutter_test.dart';
import 'package:mocktail/mocktail.dart';

import 'package:app_face_capture/core/constants/api_constants.dart';
import 'package:app_face_capture/data/services/face_api_service.dart';
import 'package:app_face_capture/presentation/viewmodels/admin_viewmodel.dart';

class MockFaceApiService extends Mock implements FaceApiService {}

void main() {
  group('AdminViewModel Tests', () {
    late MockFaceApiService mockApiService;
    late AdminViewModel viewModel;

    setUp(() {
      mockApiService = MockFaceApiService();
      viewModel = AdminViewModel(apiService: mockApiService);
    });

    test('initial values are correct', () {
      expect(viewModel.authenticated, false);
      expect(viewModel.result, null);
    });

    test('authenticate with correct PIN sets authenticated to true', () {
      final result = viewModel.authenticate(ApiConstants.adminPin);

      expect(result, true);
      expect(viewModel.authenticated, true);
      expect(viewModel.result, null);
    });

    test('authenticate with incorrect PIN sets authenticated to false and returns error', () {
      final result = viewModel.authenticate('wrong_pin');

      expect(result, false);
      expect(viewModel.authenticated, false);
      expect(viewModel.result, 'Incorrect PIN');
    });

    test('logout resets authentication state', () {
      viewModel.authenticate(ApiConstants.adminPin);
      expect(viewModel.authenticated, true);

      viewModel.logout();
      expect(viewModel.authenticated, false);
      expect(viewModel.result, null);
    });
  });
}
