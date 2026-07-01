import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:app_face_capture/presentation/views/pin_dialog.dart';
import 'package:app_face_capture/core/constants/api_constants.dart';

void main() {
  group('PinInputDialog Tests', () {
    testWidgets('shows validation error when unlocking empty PIN', (WidgetTester tester) async {
      bool? result;
      await tester.pumpWidget(MaterialApp(
        home: Scaffold(
          body: Builder(
            builder: (context) => ElevatedButton(
              onPressed: () async {
                result = await showDialog<bool>(
                  context: context,
                  builder: (context) => const PinInputDialog(),
                );
              },
              child: const Text('Open'),
            ),
          ),
        ),
      ));

      await tester.tap(find.text('Open'));
      await tester.pumpAndSettle();

      expect(find.text('Admin Authentication'), findsOneWidget);

      await tester.tap(find.text('Unlock'));
      await tester.pumpAndSettle();

      expect(find.text('PIN required'), findsOneWidget);
      expect(result, isNull);
    });

    testWidgets('shows validation error and extra hint when unlocking incorrect PIN', (WidgetTester tester) async {
      bool? result;
      await tester.pumpWidget(MaterialApp(
        home: Scaffold(
          body: Builder(
            builder: (context) => ElevatedButton(
              onPressed: () async {
                result = await showDialog<bool>(
                  context: context,
                  builder: (context) => const PinInputDialog(),
                );
              },
              child: const Text('Open'),
            ),
          ),
        ),
      ));

      await tester.tap(find.text('Open'));
      await tester.pumpAndSettle();

      await tester.enterText(find.byType(TextFormField), 'wrong_pin');
      await tester.tap(find.text('Unlock'));
      await tester.pumpAndSettle();

      expect(find.text('Incorrect PIN'), findsOneWidget);
      expect(find.text('Incorrect PIN. Try again.'), findsOneWidget);
      expect(result, isNull);
    });

    testWidgets('returns true when correct PIN is entered', (WidgetTester tester) async {
      bool? result;
      await tester.pumpWidget(MaterialApp(
        home: Scaffold(
          body: Builder(
            builder: (context) => ElevatedButton(
              onPressed: () async {
                result = await showDialog<bool>(
                  context: context,
                  builder: (context) => const PinInputDialog(),
                );
              },
              child: const Text('Open'),
            ),
          ),
        ),
      ));

      await tester.tap(find.text('Open'));
      await tester.pumpAndSettle();

      await tester.enterText(find.byType(TextFormField), ApiConstants.adminPin);
      await tester.tap(find.text('Unlock'));
      await tester.pumpAndSettle();

      expect(find.byType(PinInputDialog), findsNothing);
      expect(result, isTrue);
    });

    testWidgets('returns false when cancelled', (WidgetTester tester) async {
      bool? result;
      await tester.pumpWidget(MaterialApp(
        home: Scaffold(
          body: Builder(
            builder: (context) => ElevatedButton(
              onPressed: () async {
                result = await showDialog<bool>(
                  context: context,
                  builder: (context) => const PinInputDialog(),
                );
              },
              child: const Text('Open'),
            ),
          ),
        ),
      ));

      await tester.tap(find.text('Open'));
      await tester.pumpAndSettle();

      await tester.tap(find.text('Cancel'));
      await tester.pumpAndSettle();

      expect(find.byType(PinInputDialog), findsNothing);
      expect(result, isFalse);
    });
  });
}
