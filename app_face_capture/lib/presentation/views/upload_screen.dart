import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import 'package:provider/provider.dart';
import 'package:app_face_capture/core/constants/storage_constants.dart';
import 'package:app_face_capture/data/repositories/face_repository.dart';
import 'package:app_face_capture/presentation/viewmodels/settings_viewmodel.dart';
import 'package:app_face_capture/presentation/viewmodels/upload_viewmodel.dart';

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
      return Column(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          const Icon(Icons.error_rounded, size: 96, color: Colors.red),
          const SizedBox(height: 24),
          Text(
            'Registration Failed',
            style: Theme.of(
              context,
            ).textTheme.headlineSmall?.copyWith(fontWeight: FontWeight.bold),
          ),
          const SizedBox(height: 8),
          Text(
            viewModel.errorMessage ?? 'An unknown error occurred.',
            style: Theme.of(context).textTheme.bodyMedium,
            textAlign: TextAlign.center,
          ),
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
                  icon: const Icon(Icons.refresh),
                  label: const Text('Retry'),
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
