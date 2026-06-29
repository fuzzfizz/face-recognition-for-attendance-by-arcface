import 'package:go_router/go_router.dart';
import 'package:app_face_capture/presentation/views/home_screen.dart';
import 'package:app_face_capture/presentation/views/capture_screen.dart';
import 'package:app_face_capture/presentation/views/review_screen.dart';
import 'package:app_face_capture/presentation/views/upload_screen.dart';

final GoRouter appRouter = GoRouter(
  initialLocation: '/',
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
        final studentId = state.extra as String;
        return CaptureScreen(studentId: studentId);
      },
    ),
    GoRoute(
      path: '/review',
      name: 'review',
      builder: (context, state) {
        final args = state.extra as Map<String, dynamic>;
        return ReviewScreen(
          studentId: args['studentId'] as String,
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
          imagePaths: List<String>.from(args['imagePaths'] as List),
        );
      },
    ),
  ],
);
