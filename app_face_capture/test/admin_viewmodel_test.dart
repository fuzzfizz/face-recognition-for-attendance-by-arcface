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
      expect(viewModel.isLoading, false);
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

    test('triggerTraining when not authenticated returns early with message', () async {
      await viewModel.triggerTraining();

      expect(viewModel.result, 'Unauthorized. Please authenticate first.');
      verifyZeroInteractions(mockApiService);
    });

    test('triggerTraining success updates result message', () async {
      viewModel.authenticate(ApiConstants.adminPin);

      when(() => mockApiService.triggerTraining()).thenAnswer((_) async {});

      await viewModel.triggerTraining();

      expect(viewModel.result, 'Training triggered successfully!');
      expect(viewModel.isLoading, false);
      verify(() => mockApiService.triggerTraining()).called(1);
    });

    test('triggerTraining failure updates result message with error', () async {
      viewModel.authenticate(ApiConstants.adminPin);

      when(() => mockApiService.triggerTraining()).thenThrow(Exception('Backend error'));

      await viewModel.triggerTraining();

      expect(viewModel.result, contains('Failed to trigger training'));
      expect(viewModel.result, contains('Backend error'));
      expect(viewModel.isLoading, false);
      verify(() => mockApiService.triggerTraining()).called(1);
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
