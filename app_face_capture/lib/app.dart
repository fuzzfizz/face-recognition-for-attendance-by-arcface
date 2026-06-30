import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'package:app_face_capture/routing/app_router.dart';
import 'package:app_face_capture/core/theme/app_theme.dart';
import 'package:app_face_capture/presentation/viewmodels/settings_viewmodel.dart';
import 'package:app_face_capture/presentation/viewmodels/admin_viewmodel.dart';

class App extends StatelessWidget {
  const App({super.key});

  @override
  Widget build(BuildContext context) {
    return MultiProvider(
      providers: [
        ChangeNotifierProvider(
          create: (_) => SettingsViewModel()..load(),
        ),
        ChangeNotifierProvider(
          create: (_) => AdminViewModel(),
        ),
      ],
      child: MaterialApp.router(
        title: 'Face Capture',
        routerConfig: appRouter,
        theme: AppTheme.lightTheme,
      ),
    );
  }
}
