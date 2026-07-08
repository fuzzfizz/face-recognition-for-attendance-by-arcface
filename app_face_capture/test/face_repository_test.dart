import 'dart:io';
import 'package:flutter_test/flutter_test.dart';
import 'package:mocktail/mocktail.dart';

import 'package:app_face_capture/data/models/registration_response.dart';
import 'package:app_face_capture/data/models/registration_status.dart';
import 'package:app_face_capture/data/repositories/face_repository.dart';
import 'package:app_face_capture/data/services/face_api_service.dart';

class MockFaceApiService extends Mock implements FaceApiService {}

void main() {
  group('FaceRepository Tests', () {
    late MockFaceApiService mockApiService;
    late FaceRepository repository;

    setUp(() {
      mockApiService = MockFaceApiService();
      repository = FaceRepository(
        apiService: mockApiService,
      );
    });

    test('uploadPhotos routes to FaceApiService', () async {
      final fakeResponse = RegistrationResponse(
        message: 'Success',
        studentId: 'S001',
        status: 'pending',
      );

      when(() => mockApiService.register(any(), any(), any()))
          .thenAnswer((_) async => fakeResponse);

      final files = [File('dummy1.jpg')];
      final response = await repository.uploadPhotos('S001', 'John Doe', files);

      expect(response, fakeResponse);
      verify(() => mockApiService.register('S001', 'John Doe', files)).called(1);
    });

    test('checkStatus routes to FaceApiService', () async {
      final fakeStatus = RegistrationStatus(
        studentId: 'S001',
        status: 'pending',
        message: 'queued',
      );

      when(() => mockApiService.checkStatus(any()))
          .thenAnswer((_) async => fakeStatus);

      final status = await repository.checkStatus('S001');

      expect(status, fakeStatus);
      verify(() => mockApiService.checkStatus('S001')).called(1);
    });
  });
}
