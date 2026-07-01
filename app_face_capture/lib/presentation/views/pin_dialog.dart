import 'package:flutter/material.dart';
import 'package:app_face_capture/core/constants/api_constants.dart';

class PinInputDialog extends StatefulWidget {
  const PinInputDialog({super.key});

  @override
  State<PinInputDialog> createState() => _PinInputDialogState();
}

class _PinInputDialogState extends State<PinInputDialog> {
  final _controller = TextEditingController();
  final _formKey = GlobalKey<FormState>();
  bool _isIncorrect = false;

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return AlertDialog(
      title: const Text('Admin Authentication'),
      content: Form(
        key: _formKey,
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            const Text('Please enter the Admin PIN to proceed:'),
            const SizedBox(height: 16),
            TextFormField(
              controller: _controller,
              obscureText: true,
              keyboardType: TextInputType.number,
              decoration: const InputDecoration(
                labelText: 'Admin PIN',
                border: OutlineInputBorder(),
              ),
              validator: (val) {
                if (val == null || val.isEmpty) return 'PIN required';
                if (val != ApiConstants.adminPin) {
                  setState(() => _isIncorrect = true);
                  return 'Incorrect PIN';
                }
                return null;
              },
            ),
            if (_isIncorrect) ...[
              const SizedBox(height: 8),
              const Text('Incorrect PIN. Try again.', style: TextStyle(color: Colors.red)),
            ],
          ],
        ),
      ),
      actions: [
        TextButton(
          onPressed: () => Navigator.of(context).pop(false),
          child: const Text('Cancel'),
        ),
        FilledButton(
          onPressed: () {
            if (_formKey.currentState!.validate()) {
              Navigator.of(context).pop(true);
            }
          },
          child: const Text('Unlock'),
        ),
      ],
    );
  }
}
