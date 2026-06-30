import 'package:flutter/material.dart';

class CaptureButton extends StatelessWidget {
  final bool isEnabled;
  final VoidCallback onPressed;

  const CaptureButton({
    super.key,
    required this.isEnabled,
    required this.onPressed,
  });

  @override
  Widget build(BuildContext context) {
    return GestureDetector(
      onTap: isEnabled ? onPressed : null,
      child: AnimatedContainer(
        duration: const Duration(milliseconds: 150),
        width: 72,
        height: 72,
        decoration: BoxDecoration(
          shape: BoxShape.circle,
          color: isEnabled ? Colors.white : Colors.grey,
          border: Border.all(
            color: isEnabled ? Colors.white70 : Colors.grey.shade600,
            width: 4,
          ),
          boxShadow: isEnabled
              ? [
                  BoxShadow(
                    color: Colors.white.withOpacity(0.3),
                    blurRadius: 12,
                    spreadRadius: 2,
                  ),
                ]
              : null,
        ),
        child: Center(
          child: AnimatedContainer(
            duration: const Duration(milliseconds: 150),
            width: 56,
            height: 56,
            decoration: BoxDecoration(
              shape: BoxShape.circle,
              color: isEnabled ? Colors.white : Colors.grey.shade400,
            ),
          ),
        ),
      ),
    );
  }
}
