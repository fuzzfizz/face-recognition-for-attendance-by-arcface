import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import 'package:provider/provider.dart';
import 'package:app_face_capture/presentation/viewmodels/settings_viewmodel.dart';
import 'package:app_face_capture/presentation/views/home_screen.dart';
import 'package:app_face_capture/presentation/views/capture_screen.dart';
import 'package:app_face_capture/presentation/views/review_screen.dart';
import 'package:app_face_capture/presentation/views/upload_screen.dart';
import 'package:app_face_capture/presentation/views/settings_screen.dart';
import 'package:app_face_capture/presentation/views/admin_screen.dart';

final GoRouter appRouter = GoRouter(
  initialLocation: '/',
  redirect: (context, state) {
    final settingsModel = context.read<SettingsViewModel>();
    final path = state.uri.path;
    
    if ((path == '/admin' || path == '/settings') && !settingsModel.isAdminAuthenticated) {
      return '/'; // Redirect to home if not unlocked
    }
    return null;
  },
  routes: [
    GoRoute(
      path: '/',
      name: 'home',
      builder: (context, state) => const HomeScreen(),
    ),
    GoRoute(
      path: '/capture',
      name: 'capture',
      builder: (context, state) {
        final args = state.extra as Map<String, dynamic>;
        return CaptureScreen(
          studentId: args['studentId'] as String,
          studentName: args['studentName'] as String,
        );
      },
    ),
    GoRoute(
      path: '/review',
      name: 'review',
      builder: (context, state) {
        final args = state.extra as Map<String, dynamic>;
        return ReviewScreen(
          studentId: args['studentId'] as String,
          studentName: args['studentName'] as String,
          imagePaths: List<String>.from(args['imagePaths'] as List),
        );
      },
    ),
    GoRoute(
      path: '/upload',
      name: 'upload',
      builder: (context, state) {
        final args = state.extra as Map<String, dynamic>;
        return UploadScreen(
          studentId: args['studentId'] as String,
          studentName: args['studentName'] as String,
          imagePaths: List<String>.from(args['imagePaths'] as List),
        );
      },
    ),
    GoRoute(
      path: '/settings',
      name: 'settings',
      builder: (context, state) => const SettingsScreen(),
    ),
    GoRoute(
      path: '/admin',
      name: 'admin',
      builder: (context, state) => const AdminScreen(),
    ),
  ],
);
