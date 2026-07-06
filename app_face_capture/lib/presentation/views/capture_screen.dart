import 'dart:async';
import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import 'package:provider/provider.dart';
import 'package:camera/camera.dart';
import 'package:app_face_capture/core/constants/api_constants.dart';
import 'package:app_face_capture/presentation/viewmodels/capture_viewmodel.dart';
import 'package:app_face_capture/presentation/widgets/camera_preview_widget.dart';
import 'package:app_face_capture/presentation/widgets/photo_grid_widget.dart';
import 'package:app_face_capture/presentation/widgets/capture_button.dart';
import 'package:app_face_capture/presentation/widgets/face_guide_overlay.dart';

class CaptureScreen extends StatefulWidget {
  final String studentId;
  final String studentName;

  const CaptureScreen({
    super.key,
    required this.studentId,
    required this.studentName,
  });

  @override
  State<CaptureScreen> createState() => _CaptureScreenState();
}

class _CaptureScreenState extends State<CaptureScreen> {
  CameraController? _cameraController;
  bool _isInitializing = true;
  bool _isTakingPicture = false;

  // Countdown state variables
  bool _isPreparing = true;
  int _countdownSeconds = 3;
  Timer? _countdownTimer;

  @override
  void initState() {
    super.initState();
    _initCamera();
  }

  Future<void> _initCamera() async {
    try {
      final cameras = await availableCameras();
      if (cameras.isEmpty) {
        if (mounted) setState(() {
          _isInitializing = false;
          _isPreparing = false;
        });
        return;
      }

      final frontCamera = cameras.firstWhere(
        (c) => c.lensDirection == CameraLensDirection.front,
        orElse: () => cameras.first,
      );

      _cameraController = CameraController(
        frontCamera,
        ResolutionPreset.high,
        enableAudio: false,
      );
      await _cameraController!.initialize();
      if (mounted) {
        _startPreparationCountdown();
      }
    } catch (e) {
      debugPrint('Camera init error: $e');
      if (mounted) setState(() => _isPreparing = false);
    } finally {
      if (mounted) setState(() => _isInitializing = false);
    }
  }

  void _startPreparationCountdown() {
    _countdownTimer = Timer.periodic(const Duration(seconds: 1), (timer) {
      if (!mounted) {
        timer.cancel();
        return;
      }
      setState(() {
        if (_countdownSeconds > 1) {
          _countdownSeconds--;
        } else {
          _isPreparing = false;
          timer.cancel();
        }
      });
    });
  }

  Future<void> _capturePhoto(CaptureViewModel viewModel) async {
    if (_isPreparing) return;
    if (_cameraController == null ||
        !_cameraController!.value.isInitialized ||
        _isTakingPicture)
      return;

    setState(() => _isTakingPicture = true);
    try {
      final file = await _cameraController!.takePicture();
      viewModel.addPhoto(file.path);

      if (viewModel.isComplete && mounted) {
        context.goNamed(
          'review',
          extra: {
            'studentId': widget.studentId,
            'studentName': widget.studentName,
            'imagePaths': viewModel.capturedPaths.toList(),
          },
        );
      }
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(
          context,
        ).showSnackBar(SnackBar(content: Text('Failed to capture photo: $e')));
      }
    } finally {
      if (mounted) setState(() => _isTakingPicture = false);
    }
  }

  @override
  void dispose() {
    _countdownTimer?.cancel();
    _cameraController?.dispose();
    super.dispose();
  }

  String _getPromptText(int count, int total) {
    if (_isPreparing) {
      return 'Get ready...';
    }
    if (count >= total) {
      return 'All photos captured!';
    }
    return 'Capturing photo ${count + 1} of $total';
  }

  @override
  Widget build(BuildContext context) {
    return ChangeNotifierProvider(
      create: (_) =>
          CaptureViewModel(requiredPhotos: ApiConstants.requiredPhotos),
      child: Consumer<CaptureViewModel>(
        builder: (context, viewModel, _) {
          return Scaffold(
            backgroundColor: Colors.black,
            appBar: AppBar(
              backgroundColor: Colors.black,
              foregroundColor: Colors.white,
              title: Text('Student: ${widget.studentId}'),
              actions: [
                Center(
                  child: Padding(
                    padding: const EdgeInsets.only(right: 16.0),
                    child: Container(
                      padding: const EdgeInsets.symmetric(
                        horizontal: 12,
                        vertical: 4,
                      ),
                      decoration: BoxDecoration(
                        color: viewModel.isComplete
                            ? Colors.green
                            : Theme.of(context).colorScheme.primary,
                        borderRadius: BorderRadius.circular(12),
                      ),
                      child: Text(
                        '${viewModel.capturedCount}/${viewModel.requiredPhotos}',
                        style: const TextStyle(
                          color: Colors.white,
                          fontWeight: FontWeight.bold,
                        ),
                      ),
                    ),
                  ),
                ),
              ],
            ),
            body: Column(
              children: [
                // Camera preview area
                Expanded(
                  flex: 3,
                  child: _isInitializing
                      ? const Center(
                          child: CircularProgressIndicator(color: Colors.white),
                        )
                      : _cameraController != null &&
                            _cameraController!.value.isInitialized
                      ? Stack(
                          fit: StackFit.expand,
                          children: [
                            CameraPreviewWidget(controller: _cameraController!),
                            FaceGuideOverlay(
                              guideText: _getPromptText(viewModel.capturedCount, viewModel.requiredPhotos),
                            ),
                            if (_isPreparing)
                              Positioned.fill(
                                child: Container(
                                  color: Colors.black.withOpacity(0.6),
                                  child: Center(
                                    child: Column(
                                      mainAxisAlignment: MainAxisAlignment.center,
                                      children: [
                                        Text(
                                          '$_countdownSeconds',
                                          style: const TextStyle(
                                            color: Colors.white,
                                            fontSize: 72,
                                            fontWeight: FontWeight.bold,
                                          ),
                                        ),
                                        const SizedBox(height: 16),
                                        const Text(
                                          'Get ready! Align your face in the frame.',
                                          style: TextStyle(
                                            color: Colors.white,
                                            fontSize: 16,
                                            fontWeight: FontWeight.w500,
                                          ),
                                        ),
                                      ],
                                    ),
                                  ),
                                ),
                              ),
                            if (!_isPreparing)
                              Positioned(
                                top: 16,
                                left: 16,
                                right: 16,
                                child: Container(
                                  padding: const EdgeInsets.symmetric(
                                    horizontal: 16,
                                    vertical: 12,
                                  ),
                                  decoration: BoxDecoration(
                                    color: Colors.black.withOpacity(0.7),
                                    borderRadius: BorderRadius.circular(12),
                                    border: Border.all(color: Colors.white24),
                                  ),
                                  child: Column(
                                    mainAxisSize: MainAxisSize.min,
                                    children: [
                                      Text(
                                        'INSTRUCTION',
                                        style: TextStyle(
                                          color: Colors.grey.shade400,
                                          fontSize: 10,
                                          fontWeight: FontWeight.bold,
                                          letterSpacing: 1.5,
                                        ),
                                      ),
                                      const SizedBox(height: 4),
                                      Text(
                                        _getPromptText(viewModel.capturedCount, viewModel.requiredPhotos),
                                        textAlign: TextAlign.center,
                                        style: const TextStyle(
                                          color: Colors.white,
                                          fontSize: 16,
                                          fontWeight: FontWeight.bold,
                                        ),
                                      ),
                                    ],
                                  ),
                                ),
                              ),

                          ],
                        )
                      : const Center(
                          child: Text(
                            'Camera not available',
                            style: TextStyle(color: Colors.white),
                          ),
                        ),
                ),

                // Progress bar
                LinearProgressIndicator(
                  value: viewModel.progress,
                  backgroundColor: Colors.grey[800],
                  color: viewModel.isComplete ? Colors.green : null,
                ),

                // Thumbnail strip
                if (viewModel.capturedCount > 0)
                  SizedBox(
                    height: 100,
                    child: PhotoGridWidget(
                      imagePaths: viewModel.capturedPaths,
                      onRemove: (index) => viewModel.removePhoto(index),
                    ),
                  ),

                // Capture button
                Padding(
                  padding: const EdgeInsets.symmetric(vertical: 16.0),
                  child: CaptureButton(
                    isEnabled: !_isPreparing && !viewModel.isComplete && !_isTakingPicture,
                    onPressed: () => _capturePhoto(viewModel),
                  ),
                ),
              ],
            ),
          );
        },
      ),
    );
  }
}
