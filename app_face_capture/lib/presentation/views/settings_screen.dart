import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import 'package:app_face_capture/core/constants/storage_constants.dart';
import 'package:app_face_capture/presentation/viewmodels/settings_viewmodel.dart';

class SettingsScreen extends StatefulWidget {
  const SettingsScreen({super.key});

  @override
  State<SettingsScreen> createState() => _SettingsScreenState();
}

class _SettingsScreenState extends State<SettingsScreen> {
  final _formKey = GlobalKey<FormState>();
  late TextEditingController _urlController;

  @override
  void initState() {
    super.initState();
    final model = context.read<SettingsViewModel>();
    _urlController = TextEditingController(text: model.serverUrl);
  }

  @override
  void dispose() {
    _urlController.dispose();
    super.dispose();
  }

  Future<void> _testConnection(SettingsViewModel model) async {
    // Show loading
    ScaffoldMessenger.of(context).showSnackBar(
      const SnackBar(content: Text('Testing connection...'), duration: Duration(seconds: 1)),
    );

    final healthy = await model.checkServerHealth();

    if (mounted) {
      ScaffoldMessenger.of(context).clearSnackBars();
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text(healthy ? 'Connection successful!' : 'Connection failed.'),
          backgroundColor: healthy ? Colors.green : Colors.red,
        ),
      );
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Settings'),
      ),
      body: Consumer<SettingsViewModel>(
        builder: (context, model, child) {
          return Form(
            key: _formKey,
            child: ListView(
              padding: const EdgeInsets.all(16.0),
              children: [
                Card(
                  child: Padding(
                    padding: const EdgeInsets.all(16.0),
                    // Upload method section
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        const Text(
                          'Upload Method',
                          style: TextStyle(
                            fontSize: 16,
                            fontWeight: FontWeight.bold,
                          ),
                        ),
                        const SizedBox(height: 8),
                        RadioListTile<UploadMethod>(
                          title: const Text('Via Server'),
                          subtitle: const Text('Upload photos to the server which processes and registers them immediately.'),
                          value: UploadMethod.viaServer,
                          groupValue: model.uploadMethod,
                          onChanged: (val) {
                            if (val != null) model.setUploadMethod(val);
                          },
                        ),
                        RadioListTile<UploadMethod>(
                          title: const Text('Direct Supabase Storage'),
                          subtitle: const Text('Upload photos directly to Supabase Storage. Model training must be triggered manually.'),
                          value: UploadMethod.directSupabase,
                          groupValue: model.uploadMethod,
                          onChanged: (val) {
                            if (val != null) model.setUploadMethod(val);
                          },
                        ),
                        if (model.uploadMethod == UploadMethod.directSupabase) ...[
                          const SizedBox(height: 12),
                          const ContainerNote(),
                        ],
                      ],
                    ),
                  ),
                ),
                const SizedBox(height: 16),
                Card(
                  child: Padding(
                    padding: const EdgeInsets.all(16.0),
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        const Text(
                          'Backend Server URL',
                          style: TextStyle(
                            fontSize: 16,
                            fontWeight: FontWeight.bold,
                          ),
                        ),
                        const SizedBox(height: 8),
                        TextFormField(
                          controller: _urlController,
                          decoration: const InputDecoration(
                            labelText: 'Server Base URL',
                            hintText: 'http://10.0.2.2:8000',
                            border: OutlineInputBorder(),
                          ),
                          validator: (value) {
                            if (value == null || value.trim().isEmpty) {
                              return 'Please enter a URL';
                            }
                            return null;
                          },
                          onChanged: (value) {
                            if (_formKey.currentState!.validate()) {
                              model.setServerUrl(value.trim());
                            }
                          },
                        ),
                        const SizedBox(height: 16),
                        ElevatedButton.icon(
                          onPressed: () => _testConnection(model),
                          icon: const Icon(Icons.swap_horiz),
                          label: const Text('Test Connection'),
                        ),
                      ],
                    ),
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

class ContainerNote extends StatelessWidget {
  const ContainerNote({super.key});

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.all(12.0),
      decoration: BoxDecoration(
        color: Colors.amber.shade50,
        borderRadius: BorderRadius.circular(8),
        border: Border.all(color: Colors.amber.shade200),
      ),
      child: Row(
        children: [
          Icon(Icons.warning_amber_rounded, color: Colors.amber.shade800),
          const SizedBox(width: 8),
          const Expanded(
            child: Text(
              'Images uploaded directly. Training must be triggered by an admin.',
              style: TextStyle(fontSize: 13, color: Colors.black87),
            ),
          ),
        ],
      ),
    );
  }
}
