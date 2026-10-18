import 'dart:async';
import 'dart:convert';

import 'package:http/http.dart' as http;

class ApiException implements Exception {
  ApiException(this.status, this.message);
  final int status;
  final String message;
  @override
  String toString() => message;
}

class ApiClient {
  ApiClient(this.baseUrl, [this.token]);

  String baseUrl;
  String? token;

  Uri _uri(String path) {
    final base = baseUrl.trim().replaceAll(RegExp(r'/+$'), '');
    return Uri.parse('$base$path');
  }

  Map<String, String> get _headers => {
        'Content-Type': 'application/json',
        if (token != null) 'Authorization': 'Bearer $token',
      };

  Future<dynamic> _handle(Future<http.Response> request) async {
    http.Response r;
    try {
      r = await request.timeout(const Duration(seconds: 20));
    } on TimeoutException {
      throw ApiException(0, 'The server took too long to respond.');
    } catch (e) {
      throw ApiException(0, 'Could not reach the server. Check the server address and your connection.');
    }
    dynamic body;
    if (r.bodyBytes.isNotEmpty) {
      try {
        body = jsonDecode(utf8.decode(r.bodyBytes));
      } catch (_) {
        body = null;
      }
    }
    if (r.statusCode >= 200 && r.statusCode < 300) return body;

    var msg = 'Request failed (${r.statusCode}).';
    if (body is Map && body['detail'] != null) {
      final d = body['detail'];
      if (d is String) {
        msg = d;
      } else if (d is List) {
        msg = d.map((e) => e is Map ? (e['msg'] ?? e).toString() : e.toString()).join('; ');
      }
    }
    throw ApiException(r.statusCode, msg);
  }

  Future<Map<String, dynamic>> getConfig() async =>
      Map<String, dynamic>.from(await _handle(http.get(_uri('/config'), headers: _headers)));

  Future<String> register(Map<String, dynamic> payload) async {
    final res = await _handle(http.post(_uri('/auth/register'), headers: _headers, body: jsonEncode(payload)));
    return res['token'] as String;
  }

  Future<String> login(String username, String password) async {
    final res = await _handle(http.post(_uri('/auth/login'),
        headers: _headers, body: jsonEncode({'username': username, 'password': password})));
    return res['token'] as String;
  }

  Future<Map<String, dynamic>> checkin({
    required String day,
    required Map<String, double> hours,
    required String moodText,
  }) async {
    final res = await _handle(http.post(_uri('/checkin'),
        headers: _headers, body: jsonEncode({'day': day, 'hours': hours, 'mood_text': moodText})));
    return Map<String, dynamic>.from(res);
  }

  Future<List<dynamic>> history({int days = 30}) async {
    final res = await _handle(http.get(_uri('/history?days=$days'), headers: _headers));
    return (res['entries'] as List<dynamic>);
  }

  Future<List<dynamic>> listAssessments() async {
    final res = await _handle(http.get(_uri('/assessments'), headers: _headers));
    return (res['instruments'] as List<dynamic>);
  }

  Future<Map<String, dynamic>> getAssessment(String name) async =>
      Map<String, dynamic>.from(await _handle(http.get(_uri('/assessments/$name'), headers: _headers)));

  Future<Map<String, dynamic>> submitAssessment(String name, List<int> answers) async =>
      Map<String, dynamic>.from(await _handle(
          http.post(_uri('/assessments/$name'), headers: _headers, body: jsonEncode({'answers': answers}))));
}
