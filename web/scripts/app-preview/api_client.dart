import 'dart:convert';
import 'package:http/http.dart' as http;
import '../preview_data.dart';
class ApiClient {
  static Future<http.Response> get(String path, {bool withAuth=true}) async => PreviewData.request('GET', path, {});
  static Future<http.Response> post(String path, {Map<String,dynamic>? body, bool withAuth=true}) async => PreviewData.request('POST', path, body ?? {});
  static Future<http.Response> put(String path, {Map<String,dynamic>? body, bool withAuth=true}) async => PreviewData.request('PUT', path, body ?? {});
  static Future<http.Response> delete(String path, {bool withAuth=true}) async => PreviewData.request('DELETE', path, {});
}
