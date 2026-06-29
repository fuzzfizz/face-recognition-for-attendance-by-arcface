import 'dart:io';
import 'package:flutter_test/flutter_test.dart';
import 'package:mocktail/mocktail.dart';

import 'package:app_face_capture/core/constants/storage_constants.dart';
import 'package:app_face_capture/data/models/registration_response.dart';
import 'package:app_face_capture/data/models/registration_status.dart';
import 'package:app_face_capture/data/repositories/face_repository.dart';
import 'package:app_face_capture/data/services/face_api_service.dart';
import 'package:app_face_capture/data/services/supabase_storage_service.dart';

class MockFaceApiService extends Mock implements FaceApiService {}
class MockSupabaseStorageService extends Mock implements SupabaseStorageService {}

void main() {
  group('FaceRepository Tests', () {
    late MockFaceApiService mockApiService;
    late MockSupabaseStorageService mockSupabaseService;
    late FaceRepository repository;

    setUp(() {
      mockApiService = MockFaceApiService();
      mockSupabaseService = MockSupabaseStorageService();
      repository = FaceRepository(
        apiService: mockApiService,
        supabaseService: mockSupabaseService,
      );
    });

    test('uploadPhotos with viaServer routes to FaceApiService', () async {
      final fakeResponse = RegistrationResponse(
        message: 'Success',
        studentId: 'S001',
        status: 'pending',
      );

      when(() => mockApiService.register(any(), any()))
          .thenAnswer((_) async => fakeResponse);

      final files = [File('dummy1.jpg')];
      final response = await repository.uploadPhotos('S001', files, UploadMethod.viaServer);

      expect(response, fakeResponse);
      verify(() => mockApiService.register('S001', files)).called(1);
      verifyZeroInteractions(mockSupabaseService);
    });

    test('uploadPhotos with directSupabase routes to SupabaseStorageService', () async {
      final fakeResponse = RegistrationResponse(
        message: 'Direct success',
        studentId: 'S001',
        status: 'completed',
      );

      when(() => mockSupabaseService.uploadPhotos(any(), any()))
          .thenAnswer((_) async => fakeResponse);

      final files = [File('dummy1.jpg')];
      final response = await repository.uploadPhotos('S001', files, UploadMethod.directSupabase);

      expect(response, fakeResponse);
      verify(() => mockSupabaseService.uploadPhotos('S001', files)).called(1);
      verifyZeroInteractions(mockApiService);
    });

    test('checkStatus with directSupabase returns completed immediately without api call', () async {
      final status = await repository.checkStatus('S001', method: UploadMethod.directSupabase);

      expect(status.status, 'completed');
      expect(status.studentId, 'S001');
      verifyZeroInteractions(mockApiService);
    });

    test('checkStatus with viaServer routes to FaceApiService', () async {
      final fakeStatus = RegistrationStatus(
        studentId: 'S001',
        status: 'pending',
        message: 'queued',
      );

      when(() => mockApiService.checkStatus(any()))
          .thenAnswer((_) async => fakeStatus);

      final status = await repository.checkStatus('S001', method: UploadMethod.viaServer);

      expect(status, fakeStatus);
      verify(() => mockApiService.checkStatus('S001')).called(1);
    });
  });
}
