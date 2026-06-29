import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import 'package:app_face_capture/presentation/viewmodels/admin_viewmodel.dart';

class AdminScreen extends StatefulWidget {
  const AdminScreen({super.key});

  @override
  State<AdminScreen> createState() => _AdminScreenState();
}

class _AdminScreenState extends State<AdminScreen> {
  final _pinController = TextEditingController();
  final _formKey = GlobalKey<FormState>();

  @override
  void dispose() {
    _pinController.dispose();
    super.dispose();
  }

  void _handleUnlock(AdminViewModel model) {
    if (_formKey.currentState!.validate()) {
      final success = model.authenticate(_pinController.text);
      if (success) {
        _pinController.clear();
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Admin Portal'),
        actions: [
          if (context.watch<AdminViewModel>().authenticated)
            IconButton(
              icon: const Icon(Icons.logout),
              onPressed: () {
                context.read<AdminViewModel>().logout();
              },
            ),
        ],
      ),
      body: Consumer<AdminViewModel>(
        builder: (context, model, child) {
          if (!model.authenticated) {
            return Center(
              child: SingleChildScrollView(
                padding: const EdgeInsets.all(24.0),
                child: Form(
                  key: _formKey,
                  child: Column(
                    mainAxisAlignment: MainAxisAlignment.center,
                    children: [
                      const Icon(
                        Icons.admin_panel_settings,
                        size: 80,
                        color: Colors.blueGrey,
                      ),
                      const SizedBox(height: 16),
                      const Text(
                        'Administrator Authentication Required',
                        style: TextStyle(
                          fontSize: 18,
                          fontWeight: FontWeight.bold,
                        ),
                        textAlign: TextAlign.center,
                      ),
                      const SizedBox(height: 24),
                      TextFormField(
                        controller: _pinController,
                        obscureText: true,
                        keyboardType: TextInputType.number,
                        decoration: const InputDecoration(
                          labelText: 'Enter Admin PIN',
                          border: OutlineInputBorder(),
                          prefixIcon: Icon(Icons.lock_outline),
                        ),
                        validator: (value) {
                          if (value == null || value.isEmpty) {
                            return 'Please enter the admin PIN';
                          }
                          return null;
                        },
                      ),
                      const SizedBox(height: 16),
                      if (model.result == 'Incorrect PIN')
                        const Padding(
                          padding: EdgeInsets.only(bottom: 16.0),
                          child: Text(
                            'Incorrect PIN. Please try again.',
                            style: TextStyle(color: Colors.red),
                          ),
                        ),
                      SizedBox(
                        width: double.infinity,
                        height: 48,
                        child: ElevatedButton(
                          onPressed: () => _handleUnlock(model),
                          child: const Text('Unlock'),
                        ),
                      ),
                    ],
                  ),
                ),
              ),
            );
          }

          // Authenticated view
          return Padding(
            padding: const EdgeInsets.all(24.0),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.stretch,
              children: [
                const Card(
                  child: Padding(
                    padding: EdgeInsets.all(16.0),
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(
                          'Model Training Control',
                          style: TextStyle(
                            fontSize: 18,
                            fontWeight: FontWeight.bold,
                          ),
                        ),
                        SizedBox(height: 8),
                        Text(
                          'Direct Supabase Storage uploads do not trigger model training automatically. Press the button below to process all pending registrations and update the ArcFace embeddings model.',
                          style: TextStyle(color: Colors.black54),
                        ),
                      ],
                    ),
                  ),
                ),
                const SizedBox(height: 24),
                if (model.isLoading)
                  const Center(
                    child: Column(
                      children: [
                        CircularProgressIndicator(),
                        SizedBox(height: 16),
                        Text('Triggering training on backend server...'),
                      ],
                    ),
                  )
                else
                  SizedBox(
                    height: 54,
                    child: ElevatedButton.icon(
                      style: ElevatedButton.styleFrom(
                        backgroundColor: Colors.blueGrey.shade800,
                        foregroundColor: Colors.white,
                      ),
                      onPressed: () => model.triggerTraining(),
                      icon: const Icon(Icons.model_training),
                      label: const Text(
                        'Trigger Model Training Now',
                        style: TextStyle(fontSize: 16, fontWeight: FontWeight.bold),
                      ),
                    ),
                  ),
                const SizedBox(height: 24),
                if (model.result != null && model.result != 'Incorrect PIN')
                  Container(
                    padding: const EdgeInsets.all(16),
                    decoration: BoxDecoration(
                      color: model.result!.contains('success')
                          ? Colors.green.shade50
                          : Colors.red.shade50,
                      borderRadius: BorderRadius.circular(8),
                      border: Border.all(
                        color: model.result!.contains('success')
                            ? Colors.green.shade200
                            : Colors.red.shade200,
                      ),
                    ),
                    child: Text(
                      model.result!,
                      style: TextStyle(
                        color: model.result!.contains('success')
                            ? Colors.green.shade900
                            : Colors.red.shade900,
                        fontWeight: FontWeight.w500,
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
