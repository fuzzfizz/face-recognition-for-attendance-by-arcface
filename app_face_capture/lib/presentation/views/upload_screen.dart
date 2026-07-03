import 'dart:io';
import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import 'package:provider/provider.dart';
import 'package:path/path.dart' as p;
import 'package:app_face_capture/core/constants/storage_constants.dart';
import 'package:app_face_capture/data/repositories/face_repository.dart';
import 'package:app_face_capture/presentation/viewmodels/settings_viewmodel.dart';
import 'package:app_face_capture/presentation/viewmodels/upload_viewmodel.dart';
import 'package:app_face_capture/data/models/registration_status.dart';

class UploadScreen extends StatelessWidget {
  final String studentId;
  final String studentName;
  final List<String> imagePaths;

  const UploadScreen({
    super.key,
    required this.studentId,
    required this.studentName,
    required this.imagePaths,
  });

  @override
  Widget build(BuildContext context) {
    final settingsViewModel = context.read<SettingsViewModel>();
    return ChangeNotifierProvider(
      create: (_) => UploadViewModel(
        repository: FaceRepository(),
        studentId: studentId,
        studentName: studentName,
        imagePaths: imagePaths,
        method: settingsViewModel.uploadMethod,
      )..startUpload(),
      child: Consumer<UploadViewModel>(
        builder: (context, viewModel, _) {
          return PopScope(
            canPop: viewModel.isSuccess || viewModel.isFailed,
            child: Scaffold(
              appBar: AppBar(
                title: Text(_appBarTitle(viewModel)),
                automaticallyImplyLeading:
                    viewModel.isSuccess || viewModel.isFailed,
              ),
              body: Center(
                child: ConstrainedBox(
                  constraints: const BoxConstraints(maxWidth: 400),
                  child: Padding(
                    padding: const EdgeInsets.all(24.0),
                    child: Column(
                      mainAxisAlignment: MainAxisAlignment.center,
                      children: [
                        _buildMethodBadge(viewModel),
                        const SizedBox(height: 24),
                        Expanded(child: _buildBody(context, viewModel)),
                      ],
                    ),
                  ),
                ),
              ),
            ),
          );
        },
      ),
    );
  }

  Widget _buildMethodBadge(UploadViewModel viewModel) {
    final isViaServer = viewModel.method == UploadMethod.viaServer;
    return Chip(
      avatar: Icon(
        isViaServer ? Icons.dns_outlined : Icons.cloud_done_outlined,
        size: 16,
        color: isViaServer ? Colors.blue.shade900 : Colors.teal.shade900,
      ),
      label: Text(
        isViaServer ? 'Method: Via Server' : 'Method: Direct Supabase',
        style: TextStyle(
          color: isViaServer ? Colors.blue.shade900 : Colors.teal.shade900,
          fontWeight: FontWeight.bold,
          fontSize: 12,
        ),
      ),
      backgroundColor: isViaServer ? Colors.blue.shade50 : Colors.teal.shade50,
      side: BorderSide(
        color: isViaServer ? Colors.blue.shade200 : Colors.teal.shade200,
      ),
    );
  }

  String _appBarTitle(UploadViewModel viewModel) {
    if (viewModel.isUploading) return 'Uploading...';
    if (viewModel.isSuccess) return 'Success';
    if (viewModel.isFailed) return 'Failed';
    return 'Upload';
  }

  String _getPromptText(int count) {
    switch (count) {
      case 0:
        return 'Look straight at the camera (Neutral)';
      case 1:
        return 'Smile naturally';
      case 2:
        return 'Turn your head slightly to the left';
      case 3:
        return 'Turn your head slightly to the right';
      case 4:
        return 'Tilt your head slightly up';
      case 5:
        return 'Tilt your head slightly down';
      case 6:
        return 'If wearing glasses or mask, please remove them';
      case 7:
        return 'Blink your eyes once';
      case 8:
        return 'Show a different expression (e.g. surprised)';
      case 9:
        return 'Final look straight at the camera';
      default:
        return 'Look straight at the camera';
    }
  }

  Widget _buildBody(BuildContext context, UploadViewModel viewModel) {
    if (viewModel.isUploading) {
      return Column(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          const CircularProgressIndicator(),
          const SizedBox(height: 24),
          Text(
            'Uploading photos...',
            style: Theme.of(context).textTheme.titleMedium,
          ),
          const SizedBox(height: 16),
          LinearProgressIndicator(value: viewModel.progress),
          const SizedBox(height: 8),
          Text(
            '${viewModel.uploadedCount} / ${viewModel.totalCount} photos',
            style: Theme.of(context).textTheme.bodyMedium,
          ),
        ],
      );
    }

    if (viewModel.isSuccess) {
      return Column(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          const Icon(Icons.check_circle_rounded, size: 96, color: Colors.green),
          const SizedBox(height: 24),
          Text(
            'Registration Successful!',
            style: Theme.of(
              context,
            ).textTheme.headlineSmall?.copyWith(fontWeight: FontWeight.bold),
            textAlign: TextAlign.center,
          ),
          const SizedBox(height: 8),
          Text(
            'Student: $studentName ($studentId)',
            style: Theme.of(context).textTheme.bodyLarge,
          ),
          const SizedBox(height: 8),
          Text(
            'Upload successful! Your photos are queued for processing.',
            style: Theme.of(context).textTheme.bodyMedium?.copyWith(color: Colors.grey[600]),
            textAlign: TextAlign.center,
          ),
          const SizedBox(height: 32),
          FilledButton.icon(
            onPressed: () => context.goNamed('home'),
            icon: const Icon(Icons.home),
            label: const Text('Back to Home'),
            style: FilledButton.styleFrom(
              padding: const EdgeInsets.symmetric(horizontal: 32, vertical: 16),
            ),
          ),
        ],
      );
    }

    if (viewModel.isFailed) {
      final hasValidationErrors = viewModel.validationResults.isNotEmpty;
      return Column(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          Icon(
            hasValidationErrors ? Icons.warning_amber_rounded : Icons.error_rounded,
            size: 64,
            color: hasValidationErrors ? Colors.orange : Colors.red,
          ),
          const SizedBox(height: 16),
          Text(
            hasValidationErrors ? 'Verification Issue' : 'Registration Failed',
            style: Theme.of(context).textTheme.headlineSmall?.copyWith(
                  fontWeight: FontWeight.bold,
                ),
          ),
          const SizedBox(height: 8),
          Text(
            hasValidationErrors
                ? 'Some photos did not pass face validation. Please retake the failed photos.'
                : (viewModel.errorMessage ?? 'An unknown error occurred.'),
            style: Theme.of(context).textTheme.bodyMedium,
            textAlign: TextAlign.center,
          ),
          const SizedBox(height: 16),
          if (hasValidationErrors)
            Expanded(
              child: GridView.builder(
                padding: const EdgeInsets.symmetric(vertical: 8),
                gridDelegate: const SliverGridDelegateWithFixedCrossAxisCount(
                  crossAxisCount: 2,
                  crossAxisSpacing: 12,
                  mainAxisSpacing: 12,
                  childAspectRatio: 0.85,
                ),
                itemCount: viewModel.imagePaths.length,
                itemBuilder: (context, index) {
                  final localPath = viewModel.imagePaths[index];
                  final filename = p.basename(localPath);

                  final results =
                      viewModel.validationResults.where((r) => r.filename == filename);
                  final result = results.isNotEmpty ? results.first : null;
                  final passed = result?.passed ?? false;
                  final errorMsg = result?.error ?? 'Unknown error';

                  return Card(
                    clipBehavior: Clip.antiAlias,
                    elevation: 2,
                    child: Stack(
                      fit: StackFit.expand,
                      children: [
                        Image.file(
                          File(localPath),
                          fit: BoxFit.cover,
                        ),
                        if (result != null && !passed)
                          Container(
                            color: Colors.black.withOpacity(0.4),
                          ),
                        Positioned(
                          top: 8,
                          left: 8,
                          child: Container(
                            padding: const EdgeInsets.symmetric(
                              horizontal: 8,
                              vertical: 4,
                            ),
                            decoration: BoxDecoration(
                              color: result == null
                                  ? Colors.grey
                                  : (passed ? Colors.green : Colors.red),
                              borderRadius: BorderRadius.circular(8),
                            ),
                            child: Text(
                              result == null
                                  ? 'Unchecked'
                                  : (passed ? 'Passed' : 'Failed'),
                              style: const TextStyle(
                                color: Colors.white,
                                fontSize: 10,
                                fontWeight: FontWeight.bold,
                              ),
                            ),
                          ),
                        ),
                        if (result != null && !passed)
                          Positioned(
                            bottom: 8,
                            left: 8,
                            right: 8,
                            child: Column(
                              mainAxisSize: MainAxisSize.min,
                              children: [
                                Container(
                                  padding: const EdgeInsets.symmetric(
                                    horizontal: 6,
                                    vertical: 4,
                                  ),
                                  decoration: BoxDecoration(
                                    color: Colors.black54,
                                    borderRadius: BorderRadius.circular(4),
                                  ),
                                  child: Text(
                                    errorMsg,
                                    maxLines: 1,
                                    overflow: TextOverflow.ellipsis,
                                    style: const TextStyle(
                                      color: Colors.white70,
                                      fontSize: 10,
                                    ),
                                  ),
                                ),
                                const SizedBox(height: 6),
                                SizedBox(
                                  width: double.infinity,
                                  child: ElevatedButton.icon(
                                    style: ElevatedButton.styleFrom(
                                      padding: EdgeInsets.zero,
                                      backgroundColor: Colors.white,
                                      foregroundColor: Colors.red.shade900,
                                      textStyle: const TextStyle(
                                        fontSize: 11,
                                        fontWeight: FontWeight.bold,
                                      ),
                                    ),
                                    onPressed: () async {
                                      final prompt = _getPromptText(index);
                                      final newPath =
                                          await context.pushNamed<String>(
                                        'single_capture',
                                        extra: {'prompt': prompt},
                                      );
                                      if (newPath != null) {
                                        viewModel.replacePhoto(index, newPath);
                                      }
                                    },
                                    icon: const Icon(Icons.camera_alt, size: 14),
                                    label: const Text('Retake'),
                                  ),
                                ),
                              ],
                            ),
                          ),
                      ],
                    ),
                  );
                },
              ),
            )
          else
            const SizedBox(height: 32),
          Row(
            children: [
              Expanded(
                child: OutlinedButton(
                  onPressed: () => context.goNamed('home'),
                  child: const Text('Cancel'),
                ),
              ),
              const SizedBox(width: 16),
              Expanded(
                child: FilledButton.icon(
                  onPressed: () => viewModel.startUpload(),
                  icon: Icon(
                    hasValidationErrors ? Icons.cloud_upload : Icons.refresh,
                  ),
                  label: Text(hasValidationErrors ? 'Re-upload' : 'Retry'),
                ),
              ),
            ],
          ),
        ],
      );
    }

    return const SizedBox.shrink();
  }
}
