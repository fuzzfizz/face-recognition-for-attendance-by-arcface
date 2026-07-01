import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import 'package:provider/provider.dart';
import 'package:app_face_capture/core/constants/api_constants.dart';
import 'package:app_face_capture/presentation/views/pin_dialog.dart';
import 'package:app_face_capture/presentation/viewmodels/settings_viewmodel.dart';
import 'package:app_face_capture/presentation/viewmodels/admin_viewmodel.dart';

class HomeScreen extends StatefulWidget {
  const HomeScreen({super.key});

  @override
  State<HomeScreen> createState() => _HomeScreenState();
}

class _HomeScreenState extends State<HomeScreen> {
  final _studentIdController = TextEditingController();
  final _studentNameController = TextEditingController();
  final _formKey = GlobalKey<FormState>();

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
                  FilledButton.icon(
                    onPressed: _startCapture,
                    icon: const Icon(Icons.camera_alt),
                    label: const Text('Start Capture'),
                    style: FilledButton.styleFrom(
                      padding: const EdgeInsets.symmetric(vertical: 16),
                    ),
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
