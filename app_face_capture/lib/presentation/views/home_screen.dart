import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import 'package:provider/provider.dart';
import 'package:app_face_capture/core/constants/api_constants.dart';
import 'package:app_face_capture/data/repositories/face_repository.dart';
import 'package:app_face_capture/presentation/views/pin_dialog.dart';
import 'package:app_face_capture/presentation/viewmodels/settings_viewmodel.dart';
import 'package:app_face_capture/presentation/viewmodels/admin_viewmodel.dart';
import 'package:app_face_capture/data/models/registration_status.dart';

class HomeScreen extends StatefulWidget {
  const HomeScreen({super.key});

  @override
  State<HomeScreen> createState() => _HomeScreenState();
}

class _HomeScreenState extends State<HomeScreen> {
  final _studentIdController = TextEditingController();
  final _studentNameController = TextEditingController();
  final _formKey = GlobalKey<FormState>();

  bool _isCheckingStatus = false;

  void _showStatusDialog(BuildContext context, {required String studentId, RegistrationStatus? status, String? errorMessage}) {
    final theme = Theme.of(context);
    
    // Determine status details
    String title = 'Status Check';
    IconData icon = Icons.info_outline;
    Color iconColor = theme.colorScheme.primary;
    String mainMessage = '';
    String subMessage = '';
    bool showRegisterButton = false;

    if (errorMessage != null) {
      if (errorMessage.contains('404')) {
        title = 'No Record Found';
        icon = Icons.person_off_rounded;
        iconColor = Colors.orange.shade700;
        mainMessage = 'No registration found for student ID: $studentId';
        subMessage = 'This student has not submitted any face registration photos yet.';
        showRegisterButton = true;
      } else {
        title = 'Status Check Error';
        icon = Icons.error_outline_rounded;
        iconColor = Colors.red;
        mainMessage = 'Could not retrieve status';
        subMessage = errorMessage;
      }
    } else if (status != null) {
      if (status.status == 'completed') {
        title = 'Registration Complete';
        icon = Icons.check_circle_rounded;
        iconColor = Colors.green.shade700;
        mainMessage = 'Face recognition is active!';
        subMessage = 'The student is fully registered and can check in using the kiosk devices.';
      } else if (status.status == 'pending') {
        title = 'Training in Progress';
        icon = Icons.hourglass_top_rounded;
        iconColor = Colors.blue.shade700;
        mainMessage = 'Pending AI training';
        subMessage = status.message;
      } else {
        title = 'Status: ${status.status.toUpperCase()}';
        icon = Icons.info_rounded;
        iconColor = Colors.grey.shade700;
        mainMessage = status.message;
      }
    }

    showDialog(
      context: context,
      builder: (context) => Dialog(
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(20)),
        child: Padding(
          padding: const EdgeInsets.all(24.0),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              Icon(icon, size: 64, color: iconColor),
              const SizedBox(height: 16),
              Text(
                title,
                style: theme.textTheme.titleLarge?.copyWith(fontWeight: FontWeight.bold),
                textAlign: TextAlign.center,
              ),
              const SizedBox(height: 12),
              Text(
                'Student ID: $studentId',
                style: theme.textTheme.bodyMedium?.copyWith(
                  fontWeight: FontWeight.w500,
                  color: Colors.grey.shade600,
                ),
              ),
              const SizedBox(height: 16),
              Text(
                mainMessage,
                style: theme.textTheme.bodyLarge?.copyWith(fontWeight: FontWeight.w600),
                textAlign: TextAlign.center,
              ),
              if (subMessage.isNotEmpty) ...[
                const SizedBox(height: 8),
                Text(
                  subMessage,
                  style: theme.textTheme.bodyMedium?.copyWith(color: Colors.grey.shade600),
                  textAlign: TextAlign.center,
                ),
              ],
              const SizedBox(height: 24),
              Row(
                mainAxisAlignment: MainAxisAlignment.end,
                children: [
                  if (showRegisterButton) ...[
                    OutlinedButton(
                      onPressed: () {
                        Navigator.of(context).pop();
                        _studentIdController.text = studentId;
                      },
                      child: const Text('Register Now'),
                    ),
                    const SizedBox(width: 8),
                  ],
                  FilledButton(
                    onPressed: () => Navigator.of(context).pop(),
                    child: const Text('Dismiss'),
                  ),
                ],
              )
            ],
          ),
        ),
      ),
    );
  }

  void _checkStatus() async {
    final studentId = _studentIdController.text.trim();
    if (studentId.isEmpty) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Please enter a Student ID to check status.')),
      );
      return;
    }

    setState(() => _isCheckingStatus = true);
    try {
      final settingsViewModel = context.read<SettingsViewModel>();
      final repository = FaceRepository();
      final status = await repository.checkStatus(
        studentId,
        method: settingsViewModel.uploadMethod,
      );
      if (mounted) {
        _showStatusDialog(context, studentId: studentId, status: status);
      }
    } catch (e) {
      if (mounted) {
        _showStatusDialog(context, studentId: studentId, errorMessage: e.toString());
      }
    } finally {
      if (mounted) {
        setState(() => _isCheckingStatus = false);
      }
    }
  }

  @override
  void dispose() {
    _studentIdController.dispose();
    _studentNameController.dispose();
    super.dispose();
  }

  void _navigateToSettings() async {
    final settingsViewModel = context.read<SettingsViewModel>();
    if (settingsViewModel.isAdminAuthenticated) {
      context.push('/settings');
      return;
    }
    final authenticated = await showDialog<bool>(
      context: context,
      builder: (context) => const PinInputDialog(),
    );
    if (authenticated == true && mounted) {
      context.read<SettingsViewModel>().authenticateAdmin(true);
      context.push('/settings');
    }
  }

  void _navigateToAdmin() async {
    final settingsViewModel = context.read<SettingsViewModel>();
    if (settingsViewModel.isAdminAuthenticated) {
      context.read<AdminViewModel>().authenticate(ApiConstants.adminPin);
      context.push('/admin');
      return;
    }
    final authenticated = await showDialog<bool>(
      context: context,
      builder: (context) => const PinInputDialog(),
    );
    if (authenticated == true && mounted) {
      context.read<SettingsViewModel>().authenticateAdmin(true);
      context.read<AdminViewModel>().authenticate(ApiConstants.adminPin);
      context.push('/admin');
    }
  }

  void _startCapture() {
    if (_formKey.currentState!.validate()) {
      context.pushNamed(
        'capture',
        extra: {
          'studentId': _studentIdController.text.trim(),
          'studentName': _studentNameController.text.trim(),
        },
      );
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Face Capture'),
        actions: [
          IconButton(
            icon: const Icon(Icons.settings),
            onPressed: _navigateToSettings,
          ),
        ],
      ),
      body: Center(
        child: ConstrainedBox(
          constraints: const BoxConstraints(maxWidth: 400),
          child: Padding(
            padding: const EdgeInsets.all(24.0),
            child: Form(
              key: _formKey,
              child: Column(
                mainAxisAlignment: MainAxisAlignment.center,
                crossAxisAlignment: CrossAxisAlignment.stretch,
                children: [
                  GestureDetector(
                    onLongPress: _navigateToAdmin,
                    child: Icon(
                      Icons.face_retouching_natural,
                      size: 80,
                      color: Theme.of(context).colorScheme.primary,
                    ),
                  ),
                  const SizedBox(height: 16),
                  Text(
                    'Face Registration',
                    style: Theme.of(context).textTheme.headlineMedium,
                    textAlign: TextAlign.center,
                  ),
                  const SizedBox(height: 8),
                  Text(
                    'Capture ${ApiConstants.requiredPhotos} photos for face registration',
                    style: Theme.of(
                      context,
                    ).textTheme.bodyLarge?.copyWith(color: Colors.grey[600]),
                    textAlign: TextAlign.center,
                  ),
                  const SizedBox(height: 32),
                  TextFormField(
                    controller: _studentIdController,
                    decoration: const InputDecoration(
                      labelText: 'Student ID',
                      hintText: 'e.g. 6600001',
                      prefixIcon: Icon(Icons.badge),
                      border: OutlineInputBorder(),
                    ),
                    keyboardType: TextInputType.text,
                    textInputAction: TextInputAction.next,
                    validator: (value) {
                      if (value == null || value.trim().isEmpty) {
                        return 'Please enter a student ID';
                      }
                      return null;
                    },
                  ),
                  const SizedBox(height: 16),
                  TextFormField(
                    controller: _studentNameController,
                    decoration: const InputDecoration(
                      labelText: 'Student Name',
                      prefixIcon: Icon(Icons.person),
                      border: OutlineInputBorder(),
                    ),
                    keyboardType: TextInputType.text,
                    textInputAction: TextInputAction.done,
                    onFieldSubmitted: (_) => _startCapture(),
                    validator: (value) {
                      if (value == null || value.trim().isEmpty) {
                        return 'Please enter student name';
                      }
                      return null;
                    },
                  ),
                  const SizedBox(height: 24),
                  Row(
                    children: [
                      Expanded(
                        child: OutlinedButton.icon(
                          onPressed: _isCheckingStatus ? null : _checkStatus,
                          icon: _isCheckingStatus
                              ? const SizedBox(
                                  width: 16,
                                  height: 16,
                                  child: CircularProgressIndicator(
                                    strokeWidth: 2,
                                  ),
                                )
                              : const Icon(Icons.search),
                          label: const Text('Check Status'),
                          style: OutlinedButton.styleFrom(
                            padding: const EdgeInsets.symmetric(vertical: 16),
                          ),
                        ),
                      ),
                      const SizedBox(width: 16),
                      Expanded(
                        child: FilledButton.icon(
                          onPressed: _startCapture,
                          icon: const Icon(Icons.camera_alt),
                          label: const Text('Start Capture'),
                          style: FilledButton.styleFrom(
                            padding: const EdgeInsets.symmetric(vertical: 16),
                          ),
                        ),
                      ),
                    ],
                  ),
                ],
              ),
            ),
          ),
        ),
      ),
    );
  }
}
