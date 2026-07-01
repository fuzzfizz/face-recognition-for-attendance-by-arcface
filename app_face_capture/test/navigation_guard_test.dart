import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:provider/provider.dart';
import 'package:go_router/go_router.dart';
import 'package:mocktail/mocktail.dart';
import 'package:shared_preferences/shared_preferences.dart';

import 'package:app_face_capture/routing/app_router.dart';
import 'package:app_face_capture/presentation/viewmodels/settings_viewmodel.dart';
import 'package:app_face_capture/presentation/viewmodels/admin_viewmodel.dart';
import 'package:app_face_capture/presentation/views/home_screen.dart';
import 'package:app_face_capture/data/repositories/face_repository.dart';

class MockFaceRepository extends Mock implements FaceRepository {}

void main() {
  setUp(() {
    SharedPreferences.setMockInitialValues({});
  });

  group('Navigation and Route Guarding Tests', () {
    testWidgets('redirects /settings and /admin to home when not authenticated', (WidgetTester tester) async {
      final mockRepo = MockFaceRepository();
      final settingsViewModel = SettingsViewModel(repository: mockRepo);
      final adminViewModel = AdminViewModel();

      await tester.pumpWidget(
        MultiProvider(
          providers: [
            ChangeNotifierProvider<SettingsViewModel>.value(value: settingsViewModel),
            ChangeNotifierProvider<AdminViewModel>.value(value: adminViewModel),
          ],
          child: MaterialApp.router(
            routerConfig: appRouter,
          ),
        ),
      );

      await tester.pumpAndSettle();

      // We should start at HomeScreen (home)
      expect(find.byType(HomeScreen), findsOneWidget);

      // Try direct navigation to /settings via appRouter
      appRouter.go('/settings');
      await tester.pumpAndSettle();

      // Should be redirected back to home (HomeScreen)
      expect(find.byType(HomeScreen), findsOneWidget);

      // Try direct navigation to /admin via appRouter
      appRouter.go('/admin');
      await tester.pumpAndSettle();

      // Should be redirected back to home (HomeScreen)
      expect(find.byType(HomeScreen), findsOneWidget);
    });

    testWidgets('allows /settings and /admin access when authenticated', (WidgetTester tester) async {
      final mockRepo = MockFaceRepository();
      final settingsViewModel = SettingsViewModel(repository: mockRepo);
      final adminViewModel = AdminViewModel();

      settingsViewModel.authenticateAdmin(true);

      await tester.pumpWidget(
        MultiProvider(
          providers: [
            ChangeNotifierProvider<SettingsViewModel>.value(value: settingsViewModel),
            ChangeNotifierProvider<AdminViewModel>.value(value: adminViewModel),
          ],
          child: MaterialApp.router(
            routerConfig: appRouter,
          ),
        ),
      );

      await tester.pumpAndSettle();

      // Go to settings directly
      appRouter.go('/settings');
      await tester.pumpAndSettle();

      // We should not be on HomeScreen, should navigate to Settings Screen (since we are authenticated)
      expect(find.byType(HomeScreen), findsNothing);

      // Go to admin directly
      appRouter.go('/admin');
      await tester.pumpAndSettle();

      // We should not be on HomeScreen, should navigate to Admin Screen (since we are authenticated)
      expect(find.byType(HomeScreen), findsNothing);
    });
  });
}
