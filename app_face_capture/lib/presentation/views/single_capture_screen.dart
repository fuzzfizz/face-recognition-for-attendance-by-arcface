import 'package:flutter/material.dart';
import 'package:camera/camera.dart';
import 'package:app_face_capture/presentation/widgets/camera_preview_widget.dart';
import 'package:app_face_capture/presentation/widgets/face_guide_overlay.dart';
import 'package:app_face_capture/presentation/widgets/capture_button.dart';

class SingleCaptureScreen extends StatefulWidget {
  final String prompt;

  const SingleCaptureScreen({
    super.key,
    required this.prompt,
  });

  @override
  State<SingleCaptureScreen> createState() => _SingleCaptureScreenState();
}

class _SingleCaptureScreenState extends State<SingleCaptureScreen> {
  CameraController? _cameraController;
  bool _isInitializing = true;
  bool _isTakingPicture = false;

  @override
  void initState() {
    super.initState();
    _initCamera();
  }

  Future<void> _initCamera() async {
    try {
      final cameras = await availableCameras();
      if (cameras.isEmpty) {
        if (mounted) setState(() => _isInitializing = false);
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
    } catch (e) {
      debugPrint('Camera init error: $e');
    } finally {
      if (mounted) setState(() => _isInitializing = false);
    }
  }

  Future<void> _capturePhoto() async {
    if (_cameraController == null ||
        !_cameraController!.value.isInitialized ||
        _isTakingPicture) {
      return;
    }

    setState(() => _isTakingPicture = true);
    try {
      final file = await _cameraController!.takePicture();
      if (mounted) {
        Navigator.of(context).pop(file.path);
      }
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('Failed to capture photo: $e')),
        );
      }
    } finally {
      if (mounted) setState(() => _isTakingPicture = false);
    }
  }

  @override
  void dispose() {
    _cameraController?.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: Colors.black,
      appBar: AppBar(
        backgroundColor: Colors.black,
        foregroundColor: Colors.white,
        title: const Text('Retake Photo'),
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
                            guideText: widget.prompt,
                          ),
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
                                    'RETAKE INSTRUCTION',
                                    style: TextStyle(
                                      color: Colors.grey.shade400,
                                      fontSize: 10,
                                      fontWeight: FontWeight.bold,
                                      letterSpacing: 1.5,
                                    ),
                                  ),
                                  const SizedBox(height: 4),
                                  Text(
                                    widget.prompt,
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

          // Capture button
          Padding(
            padding: const EdgeInsets.symmetric(vertical: 24.0),
            child: CaptureButton(
              isEnabled: !_isTakingPicture,
              onPressed: _capturePhoto,
            ),
          ),
        ],
      ),
    );
  }
}
