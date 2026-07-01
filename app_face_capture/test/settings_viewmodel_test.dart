import 'package:flutter_test/flutter_test.dart';
import 'package:mocktail/mocktail.dart';
import 'package:shared_preferences/shared_preferences.dart';

import 'package:app_face_capture/core/constants/storage_constants.dart';
import 'package:app_face_capture/core/constants/api_constants.dart';
import 'package:app_face_capture/data/repositories/face_repository.dart';
import 'package:app_face_capture/presentation/viewmodels/settings_viewmodel.dart';

class MockFaceRepository extends Mock implements FaceRepository {}

void main() {
  group('SettingsViewModel Tests', () {
    late MockFaceRepository mockRepository;
    late SettingsViewModel viewModel;

    setUp(() {
      mockRepository = MockFaceRepository();
      viewModel = SettingsViewModel(repository: mockRepository);
    });

    test('load retrieves default values when SharedPreferences is empty', () async {
      SharedPreferences.setMockInitialValues({});
      await viewModel.load();

      expect(viewModel.uploadMethod, UploadMethod.viaServer);
      expect(viewModel.serverUrl, ApiConstants.baseUrl);
    });

    test('load retrieves saved values correctly', () async {
      SharedPreferences.setMockInitialValues({
        'upload_method': UploadMethod.directSupabase.index,
        'server_url': 'http://my-server.com',
      });
      await viewModel.load();

      expect(viewModel.uploadMethod, UploadMethod.directSupabase);
      expect(viewModel.serverUrl, 'http://my-server.com');
    });

    test('setUploadMethod updates value and persists to SharedPreferences', () async {
      SharedPreferences.setMockInitialValues({});
      await viewModel.load();

      await viewModel.setUploadMethod(UploadMethod.directSupabase);
      expect(viewModel.uploadMethod, UploadMethod.directSupabase);

      final prefs = await SharedPreferences.getInstance();
      expect(prefs.getInt('upload_method'), UploadMethod.directSupabase.index);
    });

    test('setServerUrl updates value and persists to SharedPreferences', () async {
      SharedPreferences.setMockInitialValues({});
      await viewModel.load();

      await viewModel.setServerUrl('http://new-url.com');
      expect(viewModel.serverUrl, 'http://new-url.com');

      final prefs = await SharedPreferences.getInstance();
      expect(prefs.getString('server_url'), 'http://new-url.com');
    });

    test('checkServerHealth delegates to repository', () async {
      when(() => mockRepository.checkServerHealth()).thenAnswer((_) async => true);

      final result = await viewModel.checkServerHealth();

      expect(result, true);
      verify(() => mockRepository.checkServerHealth()).called(1);
    });
  });
}
