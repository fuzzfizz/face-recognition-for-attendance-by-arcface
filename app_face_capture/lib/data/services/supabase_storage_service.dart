import 'dart:io';
import 'package:supabase_flutter/supabase_flutter.dart';
import 'package:uuid/uuid.dart';

import 'package:app_face_capture/core/constants/storage_constants.dart';
import 'package:app_face_capture/core/constants/api_constants.dart';
import 'package:app_face_capture/data/models/registration_response.dart';

class SupabaseStorageService {
  final SupabaseClient _supabaseClient;
  final Uuid _uuid = const Uuid();

  SupabaseStorageService({SupabaseClient? client})
      : _supabaseClient = client ?? Supabase.instance.client;

  /// Uploads photos directly to Supabase Storage.
  /// Generates a UUID for each file name.
  /// Throws an Exception if any of the uploads fail.
  Future<RegistrationResponse> uploadPhotos(String studentId, List<File> images) async {
    int successCount = 0;
    final totalCount = images.length;

    for (var image in images) {
      final uuidStr = _uuid.v4();
      final path = StorageConstants.imagePath(studentId, uuidStr);

      try {
        await _supabaseClient.storage.from(StorageConstants.bucketName).upload(
              path,
              image,
              fileOptions: const FileOptions(
                contentType: 'image/jpeg',
                upsert: true,
              ),
            );
        successCount++;
      } catch (e) {
        // Log or handle error if needed, but we proceed to count successes
      }
    }

    if (successCount < totalCount) {
      throw Exception('$successCount/$totalCount images uploaded successfully');
    }

    return RegistrationResponse(
      message: 'Images uploaded directly to Supabase Storage successfully',
      studentId: studentId,
      status: 'completed',
    );
  }

  /// Initializes Supabase Client SDK.
  static Future<void> initialize() async {
    if (ApiConstants.supabaseUrl.isNotEmpty && ApiConstants.supabaseAnonKey.isNotEmpty) {
      await Supabase.initialize(
        url: ApiConstants.supabaseUrl,
        anonKey: ApiConstants.supabaseAnonKey,
      );
    }
  }
}
