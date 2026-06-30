import 'package:flutter/material.dart';
import 'package:app_face_capture/data/services/supabase_storage_service.dart';
import 'app.dart';

void main() async {
  WidgetsFlutterBinding.ensureInitialized();
  await SupabaseStorageService.initialize();
  runApp(const App());
}
