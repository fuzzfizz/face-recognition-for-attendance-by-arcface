import 'package:flutter_test/flutter_test.dart';
import 'package:mocktail/mocktail.dart';
import 'package:fake_async/fake_async.dart';

import 'package:app_face_capture/data/models/registration_response.dart';
import 'package:app_face_capture/data/repositories/face_repository.dart';
import 'package:app_face_capture/presentation/viewmodels/upload_viewmodel.dart';

class MockFaceRepository extends Mock implements FaceRepository {}

void main() {
  group('UploadViewModel Tests', () {
    late MockFaceRepository mockRepository;
    late UploadViewModel viewModel;

    setUp(() {
      mockRepository = MockFaceRepository();
      viewModel = UploadViewModel(
        repository: mockRepository,
        studentId: 'S001',
        studentName: 'John Doe',
        imagePaths: ['dummy_path.jpg'],
      );
      
      when(() => mockRepository.dispose()).thenAnswer((_) {});
    });

    test('initial state is idle', () {
      expect(viewModel.state, UploadState.idle);
      expect(viewModel.isUploading, false);
      expect(viewModel.isSuccess, false);
      expect(viewModel.isFailed, false);
      expect(viewModel.uploadedCount, 0);
      expect(viewModel.progress, 0.0);
    });

    test('startUpload success transitions: uploading -> success', () {
      fakeAsync((async) {
        final fakeResponse = RegistrationResponse(
          message: 'Success',
          studentId: 'S001',
          status: 'pending',
        );

        when(() => mockRepository.uploadPhotos(any(), any(), any()))
            .thenAnswer((_) async => fakeResponse);

        viewModel.startUpload();
        
        async.elapse(const Duration(seconds: 1));

        expect(viewModel.state, UploadState.success);
        expect(viewModel.uploadedCount, 1);
        expect(viewModel.progress, 1.0);
        
        verify(() => mockRepository.uploadPhotos('S001', 'John Doe', any())).called(1);
        verifyNever(() => mockRepository.checkStatus(any()));
      });
    });

    test('startUpload upload failure sets state to failed', () {
      fakeAsync((async) {
        when(() => mockRepository.uploadPhotos(any(), any(), any()))
            .thenThrow(Exception('Connection error'));

        viewModel.startUpload();
        
        async.elapse(const Duration(seconds: 1));

        expect(viewModel.state, UploadState.failed);
        expect(viewModel.errorMessage, contains('Connection error'));
        verify(() => mockRepository.uploadPhotos('S001', 'John Doe', any())).called(1);
        verifyNever(() => mockRepository.checkStatus(any()));
      });
    });
  });
}
