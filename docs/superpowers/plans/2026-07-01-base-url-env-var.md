# Base URL Env Var Configuration Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Modify `ApiConstants.baseUrl` to be configured from the environment compile-time variable `BASE_URL` with an empty default value.

**Architecture:** Replace the hardcoded `baseUrl` string value in `ApiConstants` with `String.fromEnvironment`.

**Tech Stack:** Flutter / Dart

## Global Constraints

- Must use `String.fromEnvironment` with name `'BASE_URL'` and `defaultValue: ''`.
- Must remain a `static const String` to ensure compile-time constant property.

---

### Task 1: Update ApiConstants.baseUrl

**Files:**
- Modify: `app_face_capture/lib/core/constants/api_constants.dart:1-5`
- Test: none (configuration change, verified via compile/build check)

- [ ] **Step 1: Replace hardcoded baseUrl with String.fromEnvironment**

Replace the hardcoded definition of `baseUrl` in [api_constants.dart](file:///D:/AIproject/app_face_capture/lib/core/constants/api_constants.dart):
```dart
class ApiConstants {
  static const String baseUrl = String.fromEnvironment(
    'BASE_URL',
    defaultValue: '',
  );
  static const String register = '/register';
```

- [ ] **Step 2: Commit the change**

Run:
```bash
git add app_face_capture/lib/core/constants/api_constants.dart
git commit -m "feat: use environment variable for baseUrl"
```
