import 'dart:io';
import 'package:flutter_test/flutter_test.dart';
import 'package:mocktail/mocktail.dart';
import 'package:supabase_flutter/supabase_flutter.dart';

import 'package:app_face_capture/data/services/supabase_storage_service.dart';

class MockSupabaseClient extends Mock implements SupabaseClient {}
class MockSupabaseStorageClient extends Mock implements SupabaseStorageClient {}
class MockStorageFileApi extends Mock implements StorageFileApi {}
class FakeFile extends Fake implements File {}

void main() {
  setUpAll(() {
    registerFallbackValue(FakeFile());
    registerFallbackValue(const FileOptions());
  });

  group('SupabaseStorageService Tests', () {
    late MockSupabaseClient mockClient;
    late MockSupabaseStorageClient mockStorage;
    late MockStorageFileApi mockFileApi;
    late SupabaseStorageService service;

    setUp(() {
      mockClient = MockSupabaseClient();
      mockStorage = MockSupabaseStorageClient();
      mockFileApi = MockStorageFileApi();

      when(() => mockClient.storage).thenReturn(mockStorage);
      when(() => mockStorage.from(any())).thenReturn(mockFileApi);

      service = SupabaseStorageService(client: mockClient);
    });

    test('uploadPhotos success uploads all photos and returns completed', () async {
      when(() => mockFileApi.upload(
            any(),
            any(),
            fileOptions: any(named: 'fileOptions'),
          )).thenAnswer((_) async => 'uploaded_path');

      final files = [File('dummy1.jpg'), File('dummy2.jpg')];
      final response = await service.uploadPhotos('student_123', files);

      expect(response.status, 'completed');
      expect(response.studentId, 'student_123');
      verify(() => mockFileApi.upload(
            any(),
            any(),
            fileOptions: any(named: 'fileOptions'),
          )).called(2);
    });

    test('uploadPhotos partial failure throws exception', () async {
      int callCount = 0;
      when(() => mockFileApi.upload(
            any(),
            any(),
            fileOptions: any(named: 'fileOptions'),
          )).thenAnswer((_) async {
        callCount++;
        if (callCount == 2) {
          throw Exception('Upload error');
        }
        return 'uploaded_path';
      });

      final files = [File('dummy1.jpg'), File('dummy2.jpg')];

      expect(
        () => service.uploadPhotos('student_123', files),
        throwsA(isA<Exception>().having(
          (e) => e.toString(),
          'description',
          contains('1/2 images uploaded successfully'),
        )),
      );
    });
  });
}
