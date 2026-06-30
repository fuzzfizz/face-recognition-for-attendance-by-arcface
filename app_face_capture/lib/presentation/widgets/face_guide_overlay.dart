import 'package:flutter/material.dart';

class FaceGuideOverlay extends StatelessWidget {
  const FaceGuideOverlay({super.key});

  @override
  Widget build(BuildContext context) {
    return CustomPaint(
      painter: _FaceGuidePainter(),
      child: const Align(
        alignment: Alignment.bottomCenter,
        child: Padding(
          padding: EdgeInsets.only(bottom: 16.0),
          child: Text(
            'Position your face inside the oval',
            style: TextStyle(
              color: Colors.white,
              fontSize: 14,
              shadows: [Shadow(color: Colors.black, blurRadius: 4)],
            ),
          ),
        ),
      ),
    );
  }
}

class _FaceGuidePainter extends CustomPainter {
  @override
  void paint(Canvas canvas, Size size) {
    final paint = Paint()
      ..color = Colors.white.withOpacity(0.8)
      ..style = PaintingStyle.stroke
      ..strokeWidth = 2.5;

    final ovalRect = Rect.fromCenter(
      center: Offset(size.width / 2, size.height * 0.45),
      width: size.width * 0.65,
      height: size.height * 0.55,
    );

    // Draw semi-transparent dark overlay with oval cutout
    final overlayPaint = Paint()
      ..color = Colors.black.withOpacity(0.4)
      ..style = PaintingStyle.fill;

    final fullRect = Rect.fromLTWH(0, 0, size.width, size.height);
    final path = Path()
      ..addRect(fullRect)
      ..addOval(ovalRect)
      ..fillType = PathFillType.evenOdd;

    canvas.drawPath(path, overlayPaint);

    // Draw oval border
    canvas.drawOval(ovalRect, paint);

    // Draw corner indicators
    _drawCornerArc(canvas, ovalRect, paint);
  }

  void _drawCornerArc(Canvas canvas, Rect ovalRect, Paint paint) {
    final cornerPaint = Paint()
      ..color = Colors.white
      ..style = PaintingStyle.stroke
      ..strokeWidth = 3.5
      ..strokeCap = StrokeCap.round;

    // Top-left
    canvas.drawArc(
      Rect.fromCenter(
        center: Offset(ovalRect.left + 20, ovalRect.top + 20),
        width: 40,
        height: 40,
      ),
      3.14,
      1.57,
      false,
      cornerPaint,
    );

    // Top-right
    canvas.drawArc(
      Rect.fromCenter(
        center: Offset(ovalRect.right - 20, ovalRect.top + 20),
        width: 40,
        height: 40,
      ),
      -1.57,
      1.57,
      false,
      cornerPaint,
    );

    // Bottom-left
    canvas.drawArc(
      Rect.fromCenter(
        center: Offset(ovalRect.left + 20, ovalRect.bottom - 20),
        width: 40,
        height: 40,
      ),
      1.57,
      1.57,
      false,
      cornerPaint,
    );

    // Bottom-right
    canvas.drawArc(
      Rect.fromCenter(
        center: Offset(ovalRect.right - 20, ovalRect.bottom - 20),
        width: 40,
        height: 40,
      ),
      0,
      1.57,
      false,
      cornerPaint,
    );
  }

  @override
  bool shouldRepaint(covariant CustomPainter oldDelegate) => false;
}
