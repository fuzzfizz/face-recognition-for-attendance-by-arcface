import 'package:flutter/material.dart';
import 'package:app_face_capture/routing/app_router.dart';
import 'package:app_face_capture/core/theme/app_theme.dart';

class App extends StatelessWidget {
  const App({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp.router(
      title: 'Face Capture',
      routerConfig: appRouter,
      theme: AppTheme.lightTheme,
    );
  }
}
